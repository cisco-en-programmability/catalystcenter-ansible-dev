# Copyright (c) 2026 Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Offline planning and recovery checks for same-IP SDA edge refreshes.

These filters never contact Catalyst Center or modify their input. Workflow
payloads and saved device identities are checked before the role uses them.
"""

from copy import deepcopy
import hashlib
import ipaddress
import json
import re

from ansible.errors import AnsibleFilterError


STAGES = (
    "captured", "ports_removed", "fabric_removed", "old_inventory_absent",
    "awaiting_ip_release", "restore_started", "lan_automated", "inventory_ready",
    "provisioned", "fabric_added", "ports_restored", "complete",
)
PAYLOAD_NAMES = ("inventory", "provision", "fabric", "cleanup", "restore")
CAPTURE_FIELDS = (
    "schema_version", "controller", "fingerprint", "name", "site", "ips",
    "serial_by_ip", "old_devices", "payloads", "hashes",
)


def _fail(message):
    raise AnsibleFilterError("Same-IP edge refresh: " + message)


def _mapping(value, label, allowed=None):
    if not isinstance(value, dict):
        _fail(label + " must be a dictionary")
    if allowed is not None and set(value) - set(allowed):
        _fail(label + " contains unsupported keys: " + ", ".join(sorted(set(value) - set(allowed))))
    return value


def _list(value, label, nonempty=True):
    if not isinstance(value, list) or (nonempty and not value):
        _fail(label + " must be " + ("a non-empty list" if nonempty else "a list"))
    return value


def _string(value, label):
    if not isinstance(value, str) or not value or value != value.strip():
        _fail(label + " must be a non-empty, trimmed string")
    return value


def _ip(value, label="management IP"):
    _string(value, label)
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        _fail(label + " must be an IPv4 address")
    if address.is_unspecified or address.is_multicast or address.is_loopback:
        _fail(label + " must be a usable unicast management address")
    return value


def _serial(value):
    _string(value, "serial number")
    members = [member.strip().upper() for member in value.split(",")]
    if any(not member or not re.fullmatch(r"[A-Z0-9_-]+", member) for member in members):
        _fail("serial number must contain valid comma-separated member serials")
    if len(members) != len(set(members)):
        _fail("a serial number cannot contain duplicate stack members")
    return ",".join(sorted(members))


def _hierarchy(value, label="fabric site hierarchy"):
    _string(value, label)
    if value.split("/")[0] != "Global" or any(not part or part != part.strip() for part in value.split("/")):
        _fail(label + " must be a complete Global/... hierarchy")
    return value


def _hash(value):
    try:
        content = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError):
        _fail("input must contain JSON-compatible data")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _unique(values, label):
    if len(values) != len(set(values)):
        _fail(label + " must be unique")


def _interface_pairs(value, label):
    pairs = []
    for item in _list(value, label, nonempty=False):
        _mapping(item, label + " entry", {"source", "destination"})
        pairs.append({"source": _string(item.get("source"), label + " source"),
                      "destination": _string(item.get("destination"), label + " destination")})
    _unique([item["source"].casefold() for item in pairs], label + " source interfaces")
    _unique([item["destination"].casefold() for item in pairs], label + " destination interfaces")
    return pairs


def edge_same_ip_plan(batches):
    """Validate every batch before any capture or network mutation."""
    plans, names, addresses, serials, seed_ports = [], [], [], [], []
    batch_keys = {"name", "fabric_site_name_hierarchy", "onboarding_method", "new_devices",
                  "device_mapping", "allow_empty_host_port_config"}
    lan_keys = {"discovered_device_site_name_hierarchy", "primary_device_management_ip_address",
                "peer_device_management_ip_address", "primary_device_interface_names", "ip_pools",
                "multicast_enabled", "host_name_prefix", "redistribute_isis_to_bgp", "isis_domain_pwd",
                "discovery_level", "discovery_timeout", "discovery_devices", "launch_and_wait",
                "pnp_authorization", "device_serial_number_authorization"}
    for batch in _list(batches, "batches"):
        _mapping(batch, "batch", batch_keys)
        name = _string(batch.get("name"), "batch name")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or name in (".", ".."):
            _fail("batch name must be a safe filename containing letters, digits, dots, underscores or hyphens")
        names.append(name.casefold())
        site = _hierarchy(batch.get("fabric_site_name_hierarchy"))
        if batch.get("onboarding_method", "lan_automation") != "lan_automation":
            _fail("only lan_automation onboarding is supported")
        allow_empty = batch.get("allow_empty_host_port_config", False)
        if not isinstance(allow_empty, bool):
            _fail("allow_empty_host_port_config must be a boolean")
        new = _mapping(batch.get("new_devices"), "new_devices", {"device_ips", "lan_automation_config"})
        ips = [_ip(ip) for ip in _list(new.get("device_ips"), "new_devices.device_ips")]
        if len(ips) > 500:
            _fail("a batch supports at most 500 management IPs")
        _unique(ips, "batch management IPs")
        addresses.extend(ips)
        mappings = []
        for mapping in _list(batch.get("device_mapping"), "device_mapping"):
            _mapping(mapping, "device_mapping entry", {"management_ip", "interface_migration"})
            migration = _mapping(mapping.get("interface_migration", {}), "interface_migration",
                                 {"only_mapped", "port_assignments", "port_channels"})
            only_mapped = migration.get("only_mapped", False)
            if not isinstance(only_mapped, bool):
                _fail("interface_migration.only_mapped must be a boolean")
            assignments = _interface_pairs(migration.get("port_assignments", []), "port_assignments")
            channels = _interface_pairs(migration.get("port_channels", []), "port_channels")
            if only_mapped and not assignments and not channels:
                _fail("only_mapped requires at least one interface mapping")
            destinations = [item["destination"].casefold() for item in assignments + channels]
            _unique(destinations, "assignment/channel destination interfaces")
            mappings.append({"management_ip": _ip(mapping.get("management_ip")),
                             "interface_migration": {"only_mapped": only_mapped,
                                                     "port_assignments": assignments, "port_channels": channels}})
        if sorted(mapping["management_ip"] for mapping in mappings) != sorted(ips):
            _fail("device_mapping must cover exactly every device_ips address once")
        lan_config = deepcopy(_list(new.get("lan_automation_config"), "lan_automation_config"))
        serial_by_ip = {}
        for session in lan_config:
            _mapping(session, "LAN automation operation", {"lan_automation"})
            lan = _mapping(session.get("lan_automation"), "lan_automation", lan_keys)
            if lan.get("launch_and_wait") is not True:
                _fail("each LAN automation session requires launch_and_wait: true")
            discovered_site = _hierarchy(lan.get("discovered_device_site_name_hierarchy"), "discovery site hierarchy")
            if not (site == discovered_site or site.startswith(discovered_site + "/")):
                _fail("the discovery site must equal or be an ancestor of the fabric target")
            seed = _ip(lan.get("primary_device_management_ip_address"), "primary seed address")
            ports = [_string(port, "seed interface") for port in
                     _list(lan.get("primary_device_interface_names"), "primary_device_interface_names")]
            _unique([port.casefold() for port in ports], "seed interfaces")
            seed_ports.extend((seed, port.casefold()) for port in ports)
            if lan.get("peer_device_management_ip_address") is not None:
                peer = _ip(lan["peer_device_management_ip_address"], "peer seed address")
                if peer == seed:
                    _fail("primary and peer seed addresses must differ")
            pools = _list(lan.get("ip_pools"), "LAN IP pools")
            roles = []
            for pool in pools:
                _mapping(pool, "LAN IP pool", {"ip_pool_name", "ip_pool_role"})
                _string(pool.get("ip_pool_name"), "LAN IP pool name")
                role = pool.get("ip_pool_role")
                if role not in ("MAIN_POOL", "PHYSICAL_LINK_POOL"):
                    _fail("LAN pool role must be MAIN_POOL or PHYSICAL_LINK_POOL")
                roles.append(role)
            _unique(roles, "LAN IP pool roles")
            if "MAIN_POOL" not in roles:
                _fail("LAN automation requires a MAIN_POOL")
            for flag in ("multicast_enabled", "redistribute_isis_to_bgp", "pnp_authorization"):
                if flag in lan and not isinstance(lan[flag], bool):
                    _fail(flag + " must be a boolean")
            if "device_serial_number_authorization" in lan:
                for serial in _list(lan["device_serial_number_authorization"], "device_serial_number_authorization", nonempty=False):
                    _serial(serial)
            if "discovery_level" in lan and (not isinstance(lan["discovery_level"], int)
                                             or isinstance(lan["discovery_level"], bool)
                                             or not 1 <= lan["discovery_level"] <= 5):
                _fail("discovery_level must be an integer between 1 and 5")
            if "discovery_timeout" in lan and (not isinstance(lan["discovery_timeout"], int)
                                               or isinstance(lan["discovery_timeout"], bool)
                                               or not 20 <= lan["discovery_timeout"] <= 10080):
                _fail("discovery_timeout must be an integer between 20 and 10080 minutes")
            devices = _list(lan.get("discovery_devices"), "discovery_devices")
            if len(devices) > 50:
                _fail("a LAN automation session supports at most 50 discovery devices")
            for device in devices:
                _mapping(device, "discovery device", {"device_serial_number", "device_host_name",
                                                       "device_site_name_hierarchy", "device_management_ip_address"})
                ip = _ip(device.get("device_management_ip_address"))
                if ip not in ips or ip in serial_by_ip:
                    _fail("discovery devices must cover each batch management IP exactly once")
                serial = _serial(device.get("device_serial_number"))
                serial_by_ip[ip] = serial
                serials.extend(serial.split(","))
                if "device_site_name_hierarchy" in device:
                    device_site = _hierarchy(device["device_site_name_hierarchy"], "discovery device site")
                    if device_site != site and not device_site.startswith(site + "/"):
                        _fail("discovery device site must equal or descend from the fabric target")
                if "device_host_name" in device:
                    _string(device["device_host_name"], "discovery hostname")
        if set(serial_by_ip) != set(ips):
            _fail("LAN discovery devices must cover exactly the batch management IPs")
        cleanup = {"component_specific_filters": {"components_list": ["port_assignments", "port_channels"]}}
        for component in ("port_assignments", "port_channels"):
            cleanup["component_specific_filters"][component] = [{"fabric_site_name_hierarchy": site, "device_ips": ips}]
        restore = {"component_specific_filters": {}}
        for component in ("port_assignments", "port_channels"):
            restore["component_specific_filters"][component] = [
                {"fabric_site_name_hierarchy": site, "source_device_ip": item["management_ip"],
                 "destination_device_ip": item["management_ip"],
                 "only_mapped_interfaces": item["interface_migration"]["only_mapped"],
                 "interface_mappings": [
                     {"source_interface_name": pair["source"], "destination_interface_name": pair["destination"]}
                     for pair in item["interface_migration"][component]]}
                for item in mappings]
        plans.append({"name": name, "site": site, "ips": ips, "serial_by_ip": serial_by_ip,
                      "mappings": mappings, "lan_config": lan_config,
                      "allow_empty_host_port_config": allow_empty, "fingerprint": _hash(batch),
                      "generator_configs": {
                          "inventory": {"global_filters": {"devices": ips, "device_identifier": "ip_address"}},
                          "provision": {"component_specific_filters": {"components_list": ["wired"],
                                                                      "wired": [{"management_ip_address": ips}]}},
                          "fabric": {"component_specific_filters": {"components_list": ["fabric_devices"],
                                                                     "fabric_devices": [
                                                                         {"fabric_name": site, "device_ip": ip}
                                                                         for ip in ips]}},
                          "cleanup": cleanup, "restore": restore}})
    _unique(names, "case-insensitive batch names")
    _unique(addresses, "management IPs across batches")
    _unique(serials, "replacement serials across batches")
    _unique(seed_ports, "seed ports across LAN sessions and batches")
    if set(addresses).intersection(seed for seed, _port in seed_ports):
        _fail("a seed device cannot be an edge being refreshed")
    return plans


def edge_same_ip_devices(raw_module_result):
    """Unwrap the raw network_device_info result without treating errors as absence."""
    result = _mapping(raw_module_result, "inventory query result")
    if result.get("failed") or result.get("unreachable"):
        _fail("inventory query failed; device absence is unproven")
    response = _mapping(result.get("catalystcenter_response"), "inventory API response")
    records = _list(response.get("response"), "inventory API response records", nonempty=False)
    for record in records:
        _mapping(record, "inventory device")
    return deepcopy(records)


def _api_records(result, label):
    """Require a successful structured query before interpreting empty data."""
    _mapping(result, label + " result")
    if result.get("failed") or result.get("unreachable"):
        _fail(label + " failed; the requested state is unproven")
    response = _mapping(result.get("catalystcenter_response"), label + " API response")
    rows = _list(response.get("response"), label + " response records", nonempty=False)
    for row in rows:
        _mapping(row, label + " record")
    return rows


def edge_same_ip_site_id(result, plan):
    """Resolve an exact hierarchy without depending on old inventory records."""
    matches = [row for row in _api_records(result, "site lookup") if row.get("nameHierarchy") == plan["site"]]
    if len(matches) != 1:
        _fail("site lookup must resolve exactly one site for the saved fabric hierarchy")
    return _string(matches[0].get("id"), "site ID")


def edge_same_ip_fabric_id(result, site_id, allow_empty=False):
    """Resolve the fabric ID, which is distinct from the network hierarchy ID."""
    _string(site_id, "site ID")
    rows = _api_records(result, "fabric lookup")
    if not rows and allow_empty:
        return ""
    if len(rows) != 1 or rows[0].get("siteId") != site_id:
        _fail("fabric lookup must resolve exactly one fabric for the saved site ID")
    return _string(rows[0].get("id"), "fabric ID")


def edge_same_ip_old_fabric(result, fabric_id, device_uuid, expected_state="absent"):
    """Evaluate UUID membership independently of whether inventory still exists."""
    _string(fabric_id, "fabric ID")
    _string(device_uuid, "old device UUID")
    if expected_state not in ("present", "absent", "any"):
        _fail("old fabric expected state must be present, absent or any")
    rows = _api_records(result, "old UUID fabric lookup")
    for row in rows:
        if row.get("fabricId") != fabric_id or row.get("networkDeviceId") != device_uuid:
            _fail("old UUID fabric lookup returned a different fabric or device")
    if len(rows) > 1:
        _fail("old UUID fabric lookup returned duplicate memberships")
    if expected_state == "any":
        return True
    return bool(rows) if expected_state == "present" else not rows


def _identity(record):
    _mapping(record, "device identity")
    return {"management_ip": _ip(record.get("managementIpAddress", record.get("management_ip"))),
            "uuid": _string(record.get("id") or record.get("instanceUuid") or record.get("uuid"), "device UUID"),
            "serial_number": _serial(record.get("serialNumber", record.get("serial_number"))),
            "hostname": _string(record.get("hostname"), "device hostname")}


def _identities(records, ips, complete=True):
    identities = [_identity(record) for record in _list(records, "device records", nonempty=False)]
    found_ips = [identity["management_ip"] for identity in identities]
    _unique(found_ips, "inventory response management IPs")
    _unique([identity["uuid"] for identity in identities], "inventory response UUIDs")
    if set(found_ips) - set(ips) or (complete and set(found_ips) != set(ips)):
        _fail("inventory response does not match the requested management IP set")
    return identities


def _host_payload(config, plan, label):
    entries = _list(config, label, nonempty=not plan.get("allow_empty_host_port_config", False))
    seen = []
    normalized = []
    for entry in entries:
        _mapping(entry, label + " entry", {"ip_address", "fabric_site_name_hierarchy", "port_assignments", "port_channels"})
        ip = _ip(entry.get("ip_address"))
        if ip not in plan["ips"] or entry.get("fabric_site_name_hierarchy") != plan["site"]:
            _fail(label + " includes an unexpected device or fabric hierarchy")
        seen.append(ip)
        assignment_names, channel_names = [], []
        for assignment in _list(entry.get("port_assignments", []), label + " port assignments", nonempty=False):
            _mapping(assignment, label + " port assignment")
            assignment_names.append(_string(assignment.get("interface_name"), "assignment interface").casefold())
        for channel in _list(entry.get("port_channels", []), label + " port channels", nonempty=False):
            _mapping(channel, label + " port channel")
            channel_names.extend(_string(interface, "channel member interface").casefold() for interface in
                                 _list(channel.get("interface_names"), "channel member interfaces"))
        _unique(assignment_names, label + " assignment interfaces")
        _unique(channel_names, label + " channel member interfaces")
        # An original Catalyst Center export may represent the same member in
        # both components; the migration generator decides destination validity.
        if not assignment_names and not channel_names and not plan.get("allow_empty_host_port_config", False):
            _fail(label + " contains no host ports for a requested device")
        normalized.append(deepcopy(entry))
    _unique(seen, label + " management IPs")
    if not plan.get("allow_empty_host_port_config", False) and set(seen) != set(plan["ips"]):
        _fail(label + " must cover every requested device")
    return normalized


def _validate_payloads(plan, payloads):
    _mapping(payloads, "captured payloads", PAYLOAD_NAMES)
    if set(payloads) != set(PAYLOAD_NAMES):
        _fail("all five captured payloads are required")
    normalized = deepcopy(payloads)
    inventory = {}
    for entry in _list(payloads["inventory"], "inventory payload"):
        _mapping(entry, "inventory payload entry", {"ip_address_list", "role"})
        if entry.get("role") != "ACCESS":
            _fail("captured inventory role must be ACCESS")
        for ip in _list(entry.get("ip_address_list"), "inventory IP addresses"):
            if ip not in plan["ips"]:
                _fail("inventory payload contains an unexpected management IP")
            inventory[ip] = {"ip_address_list": [ip], "role": "ACCESS"}
    if set(inventory) != set(plan["ips"]):
        _fail("inventory payload must cover exactly every requested device")
    normalized["inventory"] = [inventory[ip] for ip in plan["ips"]]
    provision_ips = []
    for entry in _list(payloads["provision"], "provisioning payload"):
        _mapping(entry, "provisioning entry", {"management_ip_address", "site_name_hierarchy", "provisioning", "force_provisioning"})
        provision_ips.append(entry.get("management_ip_address"))
        provision_site = _hierarchy(entry.get("site_name_hierarchy"), "captured provisioning site")
        if ((provision_site != plan["site"] and not provision_site.startswith(plan["site"] + "/")) or entry.get("provisioning") is not True
                or entry.get("force_provisioning", False) is not False):
            _fail("captured wired provisioning must target the expected site without force provisioning")
    if sorted(provision_ips) != sorted(plan["ips"]):
        _fail("provisioning payload must cover exactly every requested device")
    fabric_ips = []
    for entry in _list(payloads["fabric"], "fabric payload"):
        _mapping(entry, "fabric payload entry", {"fabric_devices"})
        fabric = _mapping(entry.get("fabric_devices"), "fabric configuration", {"fabric_name", "device_config"})
        if fabric.get("fabric_name") != plan["site"]:
            _fail("captured fabric name does not match the requested site; zone capture may be unsupported")
        for device in _list(fabric.get("device_config"), "fabric device_config"):
            _mapping(device, "fabric device")
            if device.get("device_roles") != ["EDGE_NODE"]:
                _fail("only pure EDGE_NODE devices are supported by this role")
            for key, value in device.items():
                if key not in {"device_ip", "device_roles"} and value not in ({}, [], None, False):
                    _fail("edge device has unsupported fabric settings: " + key)
            fabric_ips.append(device.get("device_ip"))
    if sorted(fabric_ips) != sorted(plan["ips"]):
        _fail("fabric payload must cover exactly every requested edge device")
    normalized["cleanup"] = _host_payload(payloads["cleanup"], plan, "original host-port payload")
    normalized["restore"] = _host_payload(payloads["restore"], plan, "mapped host-port payload")
    expected = _remap_ports(normalized["cleanup"], plan["mappings"])
    if not edge_same_ip_ports_match(expected, normalized["restore"]) or not edge_same_ip_ports_match(normalized["restore"], expected):
        _fail("mapped restoration payload does not match the original configuration and interface mappings")
    return normalized


def _remap_ports(original, mappings):
    by_ip = {item["management_ip"]: item["interface_migration"] for item in mappings}
    captured_ips = {entry["ip_address"] for entry in original}
    for ip, mapping in by_ip.items():
        if ip not in captured_ips and (mapping["port_assignments"] or mapping["port_channels"]):
            _fail("a mapped source device was absent from the original capture")
    result = []
    for entry in original:
        copied = {"ip_address": entry["ip_address"], "fabric_site_name_hierarchy": entry["fabric_site_name_hierarchy"]}
        mapping = by_ip[entry["ip_address"]]
        for component in ("port_assignments", "port_channels"):
            remaps = {pair["source"].casefold(): pair["destination"] for pair in mapping[component]}
            items = []
            available = set()
            for source in entry.get(component, []):
                names = ([source["interface_name"]] if component == "port_assignments" else source["interface_names"])
                available.update(name.casefold() for name in names)
                names = [remaps.get(name.casefold(), name) for name in names
                         if not mapping["only_mapped"] or name.casefold() in remaps]
                if names:
                    item = deepcopy(source)
                    if component == "port_assignments":
                        item["interface_name"] = names[0]
                    else:
                        item["interface_names"] = names
                    items.append(item)
            if set(remaps) - available:
                _fail("a mapped source interface was absent from the original capture")
            if items:
                copied[component] = items
        if copied.get("port_assignments") or copied.get("port_channels"):
            result.append(copied)
    return result


def _validate_original_identities(identities, plan):
    """Bind each original physical device to a distinct replacement identity."""
    original_serials = [member for identity in identities for member in identity["serial_number"].split(",")]
    _unique(original_serials, "original device serials")
    replacement_serials = {member for serial in plan["serial_by_ip"].values() for member in serial.split(",")}
    if set(original_serials) & replacement_serials:
        _fail("the replacement must have different serial numbers from the original devices")


def _capture_checksum(manifest):
    """Checksum immutable capture fields separately from resumable progress."""
    # Keep the original checksum algorithm for snapshots created before the
    # fabric-ID fix. Their saved hierarchy can still resolve the ID on resume.
    fields = CAPTURE_FIELDS + ("fabric_id",) if manifest.get("schema_version") == 2 else CAPTURE_FIELDS
    return _hash({field: manifest.get(field) for field in fields})


def edge_same_ip_snapshot(plan, records, payloads, controller, fabric_id=None):
    """Freeze original identities and both original and mapped workflow payloads."""
    fabric_id = _string(fabric_id, "fabric ID")
    identities = _identities(records, plan["ips"])
    _validate_original_identities(identities, plan)
    payloads = _validate_payloads(plan, payloads)
    manifest = {"schema_version": 2, "controller": _string(controller, "controller"), "fabric_id": fabric_id,
                "fingerprint": plan["fingerprint"], "name": plan["name"], "site": plan["site"],
                "ips": deepcopy(plan["ips"]), "serial_by_ip": deepcopy(plan["serial_by_ip"]),
                "old_devices": identities, "payloads": payloads,
                "hashes": {name: _hash(payloads[name]) for name in PAYLOAD_NAMES},
                "stage": "captured", "stage_index": 0, "replacement_devices": []}
    # Reject conflicting explicit LAN site placement while the original devices
    # still exist, rather than discovering the conflict after teardown.
    edge_same_ip_lan_config(plan, manifest)
    manifest["capture_checksum"] = _capture_checksum(manifest)
    return manifest


def edge_same_ip_manifest(manifest, plan, controller):
    """Validate a persisted manifest against the current controller and input."""
    _mapping(manifest, "snapshot manifest")
    schema = manifest.get("schema_version")
    if not isinstance(schema, int) or isinstance(schema, bool) or schema not in (1, 2):
        _fail("saved manifest schema version is unsupported")
    if schema == 2:
        _string(manifest.get("fabric_id"), "saved fabric ID")
    elif "fabric_id" in manifest:
        _fail("legacy snapshots cannot contain an unprotected fabric ID")
    if manifest.get("capture_checksum") != _capture_checksum(manifest):
        _fail("saved immutable capture checksum mismatch")
    for key, expected in (("controller", controller), ("fingerprint", plan["fingerprint"]),
                          ("name", plan["name"]), ("site", plan["site"]), ("ips", plan["ips"]),
                          ("serial_by_ip", plan["serial_by_ip"])):
        if manifest.get(key) != expected:
            _fail("saved manifest " + key + " does not match this run")
    if (manifest.get("stage") not in STAGES or not isinstance(manifest.get("stage_index"), int)
            or isinstance(manifest.get("stage_index"), bool)
            or manifest.get("stage_index") != STAGES.index(manifest["stage"])):
        _fail("saved manifest stage is invalid")
    originals = _identities(manifest.get("old_devices"), plan["ips"])
    _validate_original_identities(originals, plan)
    _validate_payloads(plan, manifest.get("payloads"))
    hashes = _mapping(manifest.get("hashes"), "saved payload hashes", PAYLOAD_NAMES)
    if set(hashes) != set(PAYLOAD_NAMES) or any(hashes[name] != _hash(manifest["payloads"][name]) for name in PAYLOAD_NAMES):
        _fail("saved payload checksum mismatch")
    replacements = _identities(manifest.get("replacement_devices"), plan["ips"], complete=False)
    if manifest["stage_index"] >= STAGES.index("inventory_ready") and len(replacements) != len(plan["ips"]):
        _fail("saved replacement identities are incomplete")
    if replacements:
        edge_same_ip_identity_guard(replacements, manifest, "new")
    edge_same_ip_lan_config(plan, manifest)
    return deepcopy(manifest)


def edge_same_ip_checkpoint(manifest, stage, replacements=None):
    """Advance a durable checkpoint without allowing backward transitions."""
    if stage not in STAGES:
        _fail("unknown checkpoint stage")
    if manifest.get("stage") not in STAGES or STAGES.index(stage) < STAGES.index(manifest["stage"]):
        _fail("a saved checkpoint cannot move backwards")
    result = deepcopy(manifest)
    if replacements is not None and replacements:
        identities = _identities(replacements, manifest["ips"])
        edge_same_ip_identity_guard(identities, manifest, "new")
        result["replacement_devices"] = identities
    if STAGES.index(stage) >= STAGES.index("inventory_ready") and len(result.get("replacement_devices", [])) != len(manifest["ips"]):
        _fail("replacement identities must be saved before marking inventory ready")
    result["stage"] = stage
    result["stage_index"] = STAGES.index(stage)
    return result


def edge_same_ip_identity_guard(records, manifest, kind="old"):
    """Reject a reused IP belonging to the wrong physical device."""
    if kind not in ("old", "new"):
        _fail("identity kind must be old or new")
    found = _identities(records, manifest["ips"], complete=False)
    originals = {item["management_ip"]: item for item in manifest["old_devices"]}
    replacements = {item["management_ip"]: item for item in manifest.get("replacement_devices", [])}
    for identity in found:
        ip = identity["management_ip"]
        old = originals[ip]
        if kind == "old":
            if identity["uuid"] != old["uuid"] or identity["serial_number"] != old["serial_number"]:
                _fail("old-device identity mismatch at " + ip + "; refusing to target the replacement")
        else:
            if identity["uuid"] == old["uuid"] or identity["serial_number"] != manifest["serial_by_ip"][ip]:
                _fail("replacement identity mismatch at " + ip)
            saved = replacements.get(ip)
            if saved and (identity["uuid"] != saved["uuid"] or identity["serial_number"] != saved["serial_number"]):
                _fail("replacement identity changed after checkpoint at " + ip)
    return [identity["management_ip"] for identity in found]


def edge_same_ip_ready(raw_result, plan, manifest, required_role=""):
    """Check full replacement readiness; temporary incomplete records can retry."""
    records = edge_same_ip_devices(raw_result)
    seen, ready = [], True
    originals = {item["management_ip"]: item for item in manifest["old_devices"]}
    saved = {item["management_ip"]: item for item in manifest.get("replacement_devices", [])}
    desired_hostnames = {
        device["device_management_ip_address"]: device["device_host_name"].split(".")[0].casefold()
        for operation in edge_same_ip_lan_config(plan, manifest)
        for device in operation["lan_automation"]["discovery_devices"]
    }
    for record in records:
        ip = record.get("managementIpAddress")
        if ip not in plan["ips"] or ip in seen:
            _fail("replacement inventory query returned unexpected or duplicate IPs")
        seen.append(ip)
        if record.get("serialNumber"):
            if _serial(record["serialNumber"]) != plan["serial_by_ip"][ip]:
                _fail("unexpected serial number at replacement address " + ip)
        uuid = record.get("id") or record.get("instanceUuid")
        if uuid and uuid == originals[ip]["uuid"]:
            _fail("the original device still owns replacement address " + ip)
        if uuid and ip in saved and uuid != saved[ip]["uuid"]:
            _fail("replacement UUID changed after checkpoint at " + ip)
        if not uuid or not record.get("hostname") or not record.get("serialNumber"):
            ready = False
        hostname = record.get("hostname")
        if not isinstance(hostname, str) or hostname.split(".")[0].casefold() != desired_hostnames[ip]:
            ready = False
        if record.get("collectionStatus") != "Managed" or record.get("managementState") != "Managed":
            ready = False
        if record.get("reachabilityStatus") not in ("Reachable", "Ping Reachable"):
            ready = False
        if record.get("family") not in ("Switches and Hubs", "Routers"):
            ready = False
        if required_role and record.get("role", "").upper() != required_role.upper():
            ready = False
    return ready and set(seen) == set(plan["ips"])


def edge_same_ip_lan_config(plan, manifest):
    """Fill captured hostnames without persisting LAN secrets in the manifest."""
    config = deepcopy(plan["lan_config"])
    originals = {item["management_ip"]: item for item in manifest["old_devices"]}
    sites = {entry["management_ip_address"]: entry["site_name_hierarchy"]
             for entry in manifest["payloads"]["provision"]}
    for operation in config:
        for device in operation["lan_automation"]["discovery_devices"]:
            ip = device["device_management_ip_address"]
            device.setdefault("device_host_name", originals[ip]["hostname"].split(".")[0])
            if "device_site_name_hierarchy" in device and device["device_site_name_hierarchy"] != sites[ip]:
                _fail("discovery device site conflicts with its captured provisioning site")
            device["device_site_name_hierarchy"] = sites[ip]
    return config


def edge_same_ip_subset(config, ips, kind="host"):
    """Select only still-present devices for a batched retry operation."""
    wanted = set(ips)
    if kind == "host":
        return [deepcopy(entry) for entry in config if entry["ip_address"] in wanted
                and (entry.get("port_assignments") or entry.get("port_channels"))]
    if kind == "provision":
        return [deepcopy(entry) for entry in config if entry["management_ip_address"] in wanted]
    if kind == "inventory":
        result = []
        for entry in config:
            selected = [ip for ip in entry["ip_address_list"] if ip in wanted]
            if selected:
                copy = deepcopy(entry)
                copy["ip_address_list"] = selected
                result.append(copy)
        return result
    if kind == "fabric":
        result = []
        for entry in config:
            selected = [deepcopy(device) for device in entry["fabric_devices"]["device_config"] if device["device_ip"] in wanted]
            if selected:
                copy = deepcopy(entry)
                copy["fabric_devices"]["device_config"] = selected
                result.append(copy)
        return result
    _fail("unknown workflow payload kind")


def _ports_by_device(config):
    output = {}
    for entry in _list(config, "host-port payload", nonempty=False):
        _mapping(entry, "host-port entry")
        key = (entry.get("ip_address"), entry.get("fabric_site_name_hierarchy"))
        if key in output:
            _fail("host-port payload has duplicate device entries")
        assignments, channels = {}, {}
        for assignment in entry.get("port_assignments", []):
            name = assignment.get("interface_name", "").casefold()
            if not name or name in assignments:
                _fail("host-port payload has missing or duplicate assignment interfaces")
            copy = deepcopy(assignment)
            copy["interface_name"] = name
            assignments[name] = copy
        for channel in entry.get("port_channels", []):
            names = tuple(sorted(name.casefold() for name in channel.get("interface_names", [])))
            if not names or names in channels or len(set(names)) != len(names):
                _fail("host-port payload has missing or duplicate channel interfaces")
            copy = deepcopy(channel)
            copy["interface_names"] = list(names)
            channels[names] = copy
        if assignments or channels:
            output[key] = {"port_assignments": assignments, "port_channels": channels}
    return output


def _contains(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and _contains(value, actual[key]) for key, value in expected.items())
    if isinstance(expected, list):
        return expected == actual
    return expected == actual


def edge_same_ip_ports_match(expected, actual):
    """Compare desired port fields while allowing controller-generated defaults."""
    desired, observed = _ports_by_device(expected), _ports_by_device(actual)
    if set(desired) != set(observed):
        return False
    for key, components in desired.items():
        for component, entries in components.items():
            if set(entries) != set(observed[key][component]):
                return False
            if any(not _contains(value, observed[key][component][name]) for name, value in entries.items()):
                return False
    return True


def edge_same_ip_fabric(result, plan, expected_ips, expected_state="present"):
    """Evaluate the fabric info manager response without trusting success alone."""
    _mapping(result, "fabric query result")
    if expected_state not in ("present", "absent"):
        _fail("fabric expected state must be present or absent")
    if result.get("failed") or result.get("unreachable"):
        _fail("fabric query failed; membership is unproven")
    if not isinstance(result.get("status", "success"), str) or result.get("status", "success").lower() != "success":
        _fail("fabric query did not report success")
    if set(expected_ips) - set(plan["ips"]) or len(set(expected_ips)) != len(expected_ips):
        _fail("fabric verification IPs must be a unique subset of this batch")
    fragments = _list(result.get("response"), "fabric query response", nonempty=False)
    if fragments == ["No fabric devices found for the given filters."]:
        return expected_state == "absent"
    entries, blocks = [], 0
    for fragment in fragments:
        if isinstance(fragment, list) and len(fragment) == 1 and isinstance(fragment[0], dict) and "fabric_info" in fragment[0]:
            blocks += 1
            entries.extend(_list(fragment[0]["fabric_info"], "fabric_info", nonempty=False))
        elif not isinstance(fragment, str) or fragment == "No fabric devices found for the given filters.":
            _fail("fabric query returned a malformed response fragment")
    if blocks != 1:
        _fail("fabric query must return exactly one structured fabric_info block")
    seen = []
    for entry in entries:
        _mapping(entry, "fabric device")
        ip = _ip(entry.get("device_ip"))
        if ip not in expected_ips or ip in seen:
            _fail("fabric query returned unexpected or duplicate management IPs")
        seen.append(ip)
        details = _list(entry.get("fabric_details"), "fabric device details")
        for detail in details:
            _mapping(detail, "fabric device detail")
            if expected_state == "present" and detail.get("deviceRoles") != ["EDGE_NODE"]:
                _fail("only pure EDGE_NODE fabric membership is supported")
    if expected_state == "absent":
        return not seen
    return set(seen) == set(expected_ips)


class FilterModule:
    """Ansible's collection filter entry point."""

    def filters(self):
        return {name: globals()[name] for name in (
            "edge_same_ip_plan", "edge_same_ip_devices", "edge_same_ip_snapshot",
            "edge_same_ip_manifest", "edge_same_ip_checkpoint", "edge_same_ip_identity_guard",
            "edge_same_ip_ready", "edge_same_ip_lan_config", "edge_same_ip_subset", "edge_same_ip_ports_match",
            "edge_same_ip_fabric",
            "edge_same_ip_site_id", "edge_same_ip_fabric_id", "edge_same_ip_old_fabric",
        )}
