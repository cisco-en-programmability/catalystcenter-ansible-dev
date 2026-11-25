# Copyright (c) 2026 Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Execute the two-phase role against an offline Catalyst Center action backend.

The temporary collection contains the real role and filters, but every Catalyst
Center action is replaced. Builtin Ansible tasks, persistence, conditionals,
templating, and retries still execute through ansible-playbook.
"""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
ROLE = "switch_refresh_sda_fabric_edge_same_ip"
PREFIX = ROLE + "_"
SITE = "Global/Region/Building"
IPS = ["192.0.2.10", "192.0.2.11"]
PLAYBOOK = os.environ.get("ANSIBLE_PLAYBOOK") or shutil.which("ansible-playbook")
if not PLAYBOOK:
    candidate = Path(sys.executable).parent / "ansible-playbook"
    PLAYBOOK = str(candidate) if candidate.exists() else None

pytestmark = pytest.mark.skipif(PLAYBOOK is None, reason="ansible-playbook is required for offline role integration")

MODULES = (
    "network_device_info", "sda_provision_device_info", "sda_fabric_devices_info", "lan_automation_sessions_info",
    "sites_info", "sda_fabric_sites_info", "sda_fabric_zones_info",
    "inventory_playbook_config_generator", "provision_playbook_config_generator",
    "sda_fabric_devices_playbook_config_generator",
    "sda_host_port_onboarding_playbook_config_generator",
    "sda_host_port_migration_playbook_config_generator", "inventory_workflow_manager",
    "provision_workflow_manager", "sda_fabric_devices_workflow_manager",
    "sda_host_port_onboarding_workflow_manager", "fabric_devices_info_workflow_manager",
    "lan_automation_workflow_manager",
    "lan_automation_playbook_config_generator", "discovery_workflow_manager",
    "swim_workflow_manager",
)


BACKEND = r'''
from copy import deepcopy
import json
import os
from pathlib import Path
import yaml


def _ips(args):
    config = args.get("config", [])
    if config and isinstance(config, list) and "tagging_details" in config[0]:
        return []
    if isinstance(config, dict):
        if "ip_address_list" in config:
            return config["ip_address_list"]
        filters = config.get("component_specific_filters", {})
        if "global_filters" in config:
            return config["global_filters"]["devices"]
        if "wired" in filters:
            return filters["wired"][0]["management_ip_address"]
        if "fabric_devices" in filters:
            return [entry["device_ip"] for entry in filters["fabric_devices"]]
        entries = filters.get("port_assignments", filters.get("port_channels", []))
        if entries and "source_device_ip" in entries[0]:
            return [entry["source_device_ip"] for entry in entries]
        return list(dict.fromkeys(ip for entry in entries for ip in entry["device_ips"]))
    if config and "fabric_devices" in config[0]:
        return [entry["device_ip"] for group in config for entry in group["fabric_devices"]["device_config"]]
    if config and "lan_automation" in config[0]:
        return [entry["device_management_ip_address"] for group in config
                for entry in group["lan_automation"]["discovery_devices"]]
    return list(dict.fromkeys(ip for entry in config for ip in (
        entry.get("ip_address_list") or [entry.get("management_ip_address", entry.get("ip_address"))])))


def _mapped(config, ports):
    results = {}
    for component, entries in config["component_specific_filters"].items():
        for entry in entries:
            source = ports.get(entry["source_device_ip"], {})
            ip = entry["destination_device_ip"]
            target = results.setdefault(ip, {"ip_address": ip,
                "fabric_site_name_hierarchy": entry["fabric_site_name_hierarchy"]})
            remaps = {pair["source_interface_name"].lower(): pair["destination_interface_name"]
                      for pair in entry.get("interface_mappings", [])}
            mapped = []
            for original in source.get(component, []):
                item = deepcopy(original)
                names = ([item["interface_name"]] if component == "port_assignments" else item["interface_names"])
                names = [remaps.get(name.lower(), name) for name in names
                         if not entry.get("only_mapped_interfaces") or name.lower() in remaps]
                if names:
                    item["interface_name" if component == "port_assignments" else "interface_names"] = (
                        names[0] if component == "port_assignments" else names)
                    mapped.append(item)
            if mapped:
                target[component] = mapped
    return [entry for entry in results.values() if entry.get("port_assignments") or entry.get("port_channels")]


def execute(module, args):
    # Real modules receive serialized native values. Recent Ansible controllers
    # attach provenance tags to action arguments that PyYAML cannot serialize.
    args = json.loads(json.dumps(args))
    path = Path(os.environ["EDGE_SAME_IP_TEST_STATE"])
    state = json.loads(path.read_text())
    call = {"module": module, "args": deepcopy(args)}
    state["calls"].append(call)
    try:
        result = {"changed": False}
        if module == "network_device_info":
            devices = list(state["devices"].values())
            if "managementIpAddress" in args:
                devices = [d for d in devices if d["managementIpAddress"] in args["managementIpAddress"]]
            if "serialNumber" in args:
                wanted = set(args["serialNumber"])
                devices = [d for d in devices if wanted.intersection(d["serialNumber"].split(","))]
            if "id" in args:
                devices = [d for d in devices if d["id"] == args["id"]]
            result["catalystcenter_response"] = {"response": devices}
        elif module == "sda_fabric_devices_info":
            # Match the SDK contract, and keep memberships independent from
            # inventory so deleting a device cannot hide a stale fabric row.
            if not isinstance(args.get("fabricId"), str) or not args["fabricId"].strip():
                raise TypeError("fabricId must be a non-empty string")
            if state.get("reject_fabric_queries"):
                raise TypeError("Injected fabric-query contract failure")
            result["catalystcenter_response"] = {"response": [
                deepcopy(row) for row in state["fabric_memberships"].values()
                if row["fabricId"] == args["fabricId"] and row["networkDeviceId"] == args.get("networkDeviceId")]}
        elif module == "sites_info":
            result["catalystcenter_response"] = {"response": state.get("site_rows", [
                {"id": "site-1", "nameHierarchy": "Global/Region/Building"}])}
        elif module in ("sda_fabric_sites_info", "sda_fabric_zones_info"):
            if state.get("fabric_lookup_failed"):
                raise RuntimeError("Injected fabric-site lookup failure")
            default = [{"id": "fabric-1", "siteId": "site-1"}] if module == "sda_fabric_sites_info" else []
            rows = state.get("fabric_sites" if module == "sda_fabric_sites_info" else "fabric_zones", default)
            result["catalystcenter_response"] = {"response": [
                row for row in rows if row.get("siteId") == args.get("siteId")]}
        elif module == "sda_provision_device_info":
            ip = args["deviceManagementIpAddress"]
            result["catalystcenter_response"] = {
                "status": "success" if ip in state["provisioned"] else "failed",
                "deviceManagementIpAddress": ip,
                "siteNameHierarchy": state["provisioned"].get(ip, ""),
            }
        elif module == "lan_automation_sessions_info":
            result["catalystcenter_response"] = {"response": {
                "activeSessionIds": [], "activeSessions": "0", "maxSupportedCount": "5"}}
        elif module == "fabric_devices_info_workflow_manager":
            entries = []
            for group in args["config"]:
                for query in group["fabric_devices"]:
                    ips = query.get("device_identifier", [{}])[0].get("ip_address", list(state["devices"]))
                    for ip in ips:
                        if ip in state["fabric"]:
                            entries.append({"device_ip": ip, "fabric_details": [{
                                "networkDeviceId": state["devices"][ip]["id"],
                                "fabricId": "fabric-1", "deviceRoles": state["fabric"][ip]}]})
            result.update(status="success", response=(
                [[{"fabric_info": entries}]] if entries else ["No fabric devices found for the given filters."]))
        elif module.endswith("_playbook_config_generator"):
            ips = _ips(args)
            call["targets"] = ips
            if module == "lan_automation_playbook_config_generator":
                if state.get("missing_lan_history") or set(ips).intersection(state.get("missing_lan_history_for", [])):
                    raise RuntimeError("No stopped LAN automation session found")
                payload = [{"lan_automation": {
                    "discovered_device_site_name_hierarchy": args["config"]["site_name_hierarchy"],
                    "primary_device_management_ip_address": state.get("lan_seed", "198.51.100.10"),
                    "primary_device_interface_names": ["GigabitEthernet1/0/1", "GigabitEthernet1/0/2"],
                    "ip_pools": [{"ip_pool_name": "LAN_MAIN", "ip_pool_role": "MAIN_POOL"}],
                    "discovery_devices": [{
                        "device_management_ip_address": ip,
                        "device_serial_number": "REPLACE_WITH_SERIAL_FOR_" + ip.replace(".", "_"),
                        "device_host_name": state["devices"][ip]["hostname"],
                        "device_site_name_hierarchy": state["provisioned"][ip],
                    } for ip in ips],
                    "launch_and_wait": True,
                }}]
            elif module == "inventory_playbook_config_generator":
                payload = [{"ip_address_list": [ip], "role": state["devices"][ip]["role"]} for ip in ips]
            elif module == "provision_playbook_config_generator":
                payload = [{"management_ip_address": ip, "site_name_hierarchy": state["provisioned"][ip],
                            "provisioning": True, "force_provisioning": False} for ip in ips]
            elif module == "sda_fabric_devices_playbook_config_generator":
                filters = args["config"]["component_specific_filters"]["fabric_devices"]
                payload = [{"fabric_devices": {"fabric_name": filters[0]["fabric_name"],
                    "device_config": [{"device_ip": ip, "device_roles": state["fabric"][ip]} for ip in ips]}}]
            elif module == "sda_host_port_migration_playbook_config_generator":
                payload = _mapped(args["config"], state["ports"])
            else:
                # The real onboarding generator concatenates component exports;
                # it does not combine assignments and channels for the same IP.
                payload = [
                    {"ip_address": ip, "fabric_site_name_hierarchy": state["ports"][ip]["fabric_site_name_hierarchy"],
                     component: deepcopy(state["ports"][ip][component])}
                    for component in ("port_assignments", "port_channels")
                    for ip in ips if state["ports"].get(ip, {}).get(component)
                ]
                duplicate = state.get("duplicate_host_component")
                if duplicate:
                    payload.append(deepcopy(next(entry for entry in payload if duplicate in entry)))
            Path(args["file_path"]).write_text(yaml.safe_dump({"config": payload}, sort_keys=False))
            result.update(changed=True, status="success")
        else:
            ips = _ips(args)
            call["targets"] = ips
            failure = state.get("failure", {})
            fail = (failure.get("module") == module and failure.get("state") == args.get("state")
                    and failure.get("remaining", 0) > 0)
            apply_ips = ips[:1] if fail else ips
            if module == "swim_workflow_manager":
                for entry in args["config"]:
                    if set(entry) - {"import_image_details", "tagging_details"}:
                        raise AssertionError("Unexpected device image operation")
                    if not fail:
                        state.setdefault("golden_images", []).append(deepcopy(entry["tagging_details"]))
            elif module == "lan_automation_workflow_manager":
                for group in args["config"]:
                    for device in group["lan_automation"]["discovery_devices"]:
                        ip = device["device_management_ip_address"]
                        if ip in apply_ips:
                            # Model Catalyst Center/device DNS behavior: the
                            # configured domain is appended to the LAN hostname.
                            domain = state["domains_by_ip"][ip]
                            hostname = device["device_host_name"] + ("." + domain if domain else "")
                            if ip == next(iter(state["domains_by_ip"])):
                                fault = state.get("replacement_hostname_fault")
                                if fault == "duplicate_domain":
                                    hostname += "." + domain
                                elif fault == "wrong_domain":
                                    hostname = device["device_host_name"] + ".other.test"
                                elif fault == "short_only":
                                    hostname = device["device_host_name"]
                            state["devices"][ip] = {
                                "managementIpAddress": ip, "id": "new-uuid-" + ip.rsplit(".", 1)[1],
                                "instanceUuid": "new-uuid-" + ip.rsplit(".", 1)[1],
                                "serialNumber": device["device_serial_number"],
                                "hostname": hostname, "role": "UNKNOWN",
                                "family": "Switches and Hubs", "collectionStatus": "Managed",
                                "managementState": "Managed", "reachabilityStatus": "Reachable",
                                "inventoryStatusDetail": "<status><general code='SUCCESS'/></status>",
                            }
            elif module == "discovery_workflow_manager":
                for ip in apply_ips:
                    if ip not in state.get("prepared_devices", {}):
                        raise RuntimeError("Replacement device was not prepared for discovery")
                    state["devices"][ip] = deepcopy(state["prepared_devices"][ip])
            elif module == "inventory_workflow_manager":
                for entry in args["config"]:
                    for ip in entry["ip_address_list"]:
                        if ip in apply_ips:
                            if args["state"] == "deleted":
                                state["devices"].pop(ip, None)
                            else:
                                state["devices"][ip]["role"] = entry["role"]
            elif module == "provision_workflow_manager":
                for entry in args["config"]:
                    ip = entry["management_ip_address"]
                    if ip in apply_ips:
                        if args["state"] == "deleted":
                            state["provisioned"].pop(ip, None)
                            if state.get("unprovision_deletes_inventory"):
                                state["devices"].pop(ip, None)
                        else:
                            state["provisioned"][ip] = entry["site_name_hierarchy"]
            elif module == "sda_fabric_devices_workflow_manager":
                for group in args["config"]:
                    for entry in group["fabric_devices"]["device_config"]:
                        ip = entry["device_ip"]
                        if ip in apply_ips:
                            if args["state"] == "deleted":
                                state["fabric"].pop(ip, None)
                                if not state.get("keep_stale_fabric_memberships"):
                                    state["fabric_memberships"].pop(state["devices"][ip]["id"], None)
                            else:
                                state["fabric"][ip] = entry["device_roles"]
                                uuid = state["devices"][ip]["id"]
                                state["fabric_memberships"][uuid] = {
                                    "networkDeviceId": uuid, "fabricId": "fabric-1", "deviceRoles": entry["device_roles"]}
            elif module == "sda_host_port_onboarding_workflow_manager":
                for entry in args["config"]:
                    ip = entry["ip_address"]
                    if ip not in apply_ips:
                        continue
                    if args["state"] == "merged":
                        state["ports"][ip] = deepcopy(entry)
                    else:
                        current = state["ports"].get(ip, {})
                        names = {item["interface_name"].lower() for item in entry.get("port_assignments", [])}
                        channels = {tuple(sorted(name.lower() for name in item["interface_names"]))
                                    for item in entry.get("port_channels", [])}
                        current["port_assignments"] = [item for item in current.get("port_assignments", [])
                            if item["interface_name"].lower() not in names]
                        current["port_channels"] = [item for item in current.get("port_channels", [])
                            if tuple(sorted(name.lower() for name in item["interface_names"])) not in channels]
                        state["ports"][ip] = current if current["port_assignments"] or current["port_channels"] else {}
            else:
                raise AssertionError("Unexpected test action: " + module)
            result["changed"] = True
            if fail:
                failure["remaining"] -= 1
                result.update(failed=True, msg="Injected partial workflow failure")
        path.write_text(json.dumps(state))
        return result
    except Exception as exc:
        path.write_text(json.dumps(state))
        return {"failed": True, "msg": "Offline backend: " + repr(exc)}
'''


def _batch():
    return {
        "name": "two-edges", "fabric_site_name_hierarchy": SITE,
        "onboarding_method": "lan_automation",
        "new_devices": {"device_ips": IPS, "lan_automation_config": [{"lan_automation": {
            "discovered_device_site_name_hierarchy": SITE,
            "primary_device_management_ip_address": "198.51.100.10",
            "primary_device_interface_names": ["GigabitEthernet1/0/1", "GigabitEthernet1/0/2"],
            "ip_pools": [{"ip_pool_name": "LAN_MAIN", "ip_pool_role": "MAIN_POOL"}],
            "discovery_devices": [{"device_serial_number": "NEW-SERIAL-" + ip.rsplit(".", 1)[1],
                                   "device_management_ip_address": ip} for ip in IPS],
            "launch_and_wait": True,
        }}]},
        "device_mapping": [{"management_ip": ip, "interface_migration": {
            "only_mapped": False,
            "port_assignments": [{"source": "GigabitEthernet1/0/5", "destination": "GigabitEthernet1/0/10"}],
            "port_channels": [{"source": "GigabitEthernet1/0/47", "destination": "TenGigabitEthernet1/1/1"}],
        }} for ip in IPS],
    }


def _generated_batch(method="lan_automation"):
    value = _batch()
    value.pop("new_devices")
    value["onboarding_method"] = method
    for mapping in value["device_mapping"]:
        mapping["replacement_serial_number"] = "NEW-SERIAL-" + mapping["management_ip"].rsplit(".", 1)[1]
    return value


def _prepare_discovery_replacements(case, wrong_serial=False):
    state = case.state()
    state["prepared_devices"] = deepcopy(_initial_state()["devices"])
    for ip, device in state["prepared_devices"].items():
        suffix = ip.rsplit(".", 1)[1]
        device.update(id="new-uuid-" + suffix, instanceUuid="new-uuid-" + suffix,
                      serialNumber="WRONG" if wrong_serial else "NEW-SERIAL-" + suffix, role="UNKNOWN")
    case.save_state(state)


def _initial_state():
    devices, ports = {}, {}
    for ip in IPS:
        suffix = ip.rsplit(".", 1)[1]
        devices[ip] = {
            "managementIpAddress": ip, "id": "old-uuid-" + suffix,
            "instanceUuid": "old-uuid-" + suffix, "serialNumber": "OLD-SERIAL-" + suffix,
            "hostname": "edge-" + suffix + ".example.test", "role": "ACCESS",
            "family": "Switches and Hubs", "collectionStatus": "Managed",
            "managementState": "Managed", "reachabilityStatus": "Reachable",
        }
        ports[ip] = {
            "ip_address": ip, "fabric_site_name_hierarchy": SITE,
            "port_assignments": [{"interface_name": "GigabitEthernet1/0/5",
                                  "data_vlan_name": "DATA", "security_group_name": "Employees",
                                  "authentication_template_name": "Closed Authentication"}],
            "port_channels": [{"interface_names": ["GigabitEthernet1/0/47", "GigabitEthernet1/0/48"],
                               "protocol": "LACP", "connected_device_type": "TRUNKING_DEVICE"}],
        }
    return {
        "devices": devices,
        "domains_by_ip": {ip: device["hostname"].partition(".")[2] for ip, device in devices.items()},
        "ports": ports,
        "fabric": {ip: ["EDGE_NODE"] for ip in IPS},
        "fabric_memberships": {
            device["id"]: {
                "networkDeviceId": device["id"],
                "fabricId": "fabric-1",
                "deviceRoles": ["EDGE_NODE"],
            }
            for device in devices.values()
        },
        "provisioned": {ip: SITE + "/Floor" + str(index + 1) for index, ip in enumerate(IPS)},
        "calls": [],
    }


class OfflineRole:
    def __init__(self, directory, baseline=None):
        self.directory = directory
        self.state_path = directory / "controller.json"
        self.snapshots = directory / "snapshots"
        self.collection_root = directory / "collections"
        collection = self.collection_root / "ansible_collections" / "cisco" / "catalystcenter"
        collection.mkdir(parents=True)
        shutil.copytree(ROOT / "roles" / ROLE, collection / "roles" / ROLE)
        for child_role in ("lan_automation_config_generator", "discovery"):
            shutil.copytree(ROOT / "roles" / child_role, collection / "roles" / child_role)
        (collection / "plugins" / "filter").mkdir(parents=True)
        shutil.copy(ROOT / "plugins" / "filter" / (ROLE + ".py"), collection / "plugins" / "filter")
        for kind in ("action", "modules", "module_utils"):
            (collection / "plugins" / kind).mkdir(parents=True, exist_ok=True)
            (collection / "plugins" / kind / "__init__.py").write_text("")
        (collection / "plugins" / "module_utils" / "same_ip_test_backend.py").write_text(BACKEND)
        for module in MODULES:
            (collection / "plugins" / "modules" / (module + ".py")).write_text("DOCUMENTATION = ''\n")
            (collection / "plugins" / "action" / (module + ".py")).write_text(
                "from ansible.plugins.action import ActionBase\n"
                "from ansible_collections.cisco.catalystcenter.plugins.module_utils.same_ip_test_backend import execute\n"
                "class ActionModule(ActionBase):\n"
                "    def run(self, tmp=None, task_vars=None):\n"
                "        result = super().run(tmp, task_vars)\n"
                "        result.update(execute(" + repr(module) + ", self._task.args))\n"
                "        return result\n")
        self.batch = _batch()
        if baseline:
            state = baseline.state()
            state["calls"] = []
            shutil.copytree(baseline.snapshots, self.snapshots)
        else:
            state = _initial_state()
        self.save_state(state)
        self.play = directory / "play.yml"
        self.play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "roles": ["cisco.catalystcenter." + ROLE],
        }]))
        self.env = os.environ.copy()
        self.env.update({
            "ANSIBLE_COLLECTIONS_PATH": str(self.collection_root),
            "ANSIBLE_COLLECTIONS_PATHS": str(self.collection_root),
            "ANSIBLE_LOCAL_TEMP": str(directory / "ansible-local"),
            "ANSIBLE_REMOTE_TEMP": str(directory / "ansible-remote"),
            "ANSIBLE_CONFIG": str(directory / "ansible.cfg"),
            "ANSIBLE_NOCOLOR": "1", "ANSIBLE_HOST_KEY_CHECKING": "False",
            "ANSIBLE_RETRY_FILES_ENABLED": "False", "ANSIBLE_STDOUT_CALLBACK": "default",
            "PYTHONPATH": str(self.collection_root),
            "EDGE_SAME_IP_TEST_STATE": str(self.state_path),
        })
        (directory / "ansible.cfg").write_text("[defaults]\ninterpreter_python = " + sys.executable + "\n")

    def state(self):
        return json.loads(self.state_path.read_text())

    def save_state(self, state):
        self.state_path.write_text(json.dumps(state))

    @property
    def manifest_path(self):
        return self.snapshots / "two-edges" / "manifest.json"

    def manifest(self):
        return json.loads(self.manifest_path.read_text())

    def run(self, phase, success=True, extra=None):
        variables = {
            "catalystcenter_host": "offline-controller.example.test",
            "catalystcenter_username": "offline", "catalystcenter_password": "offline",
            PREFIX + "phase": phase, PREFIX + "snapshot_dir": str(self.snapshots),
            PREFIX + "batches": [self.batch], PREFIX + "timeout": 2,
            PREFIX + "poll_interval": 1, PREFIX + "lan_automation_timeout": 2,
            PREFIX + "lan_automation_poll_interval": 1,
        }
        variables.update(extra or {})
        variables_path = self.directory / "vars.json"
        variables_path.write_text(json.dumps(variables))
        result = subprocess.run([PLAYBOOK, "-i", "localhost,", str(self.play),
                                 "-e", "@" + str(variables_path)], env=self.env,
                                cwd=str(self.directory), capture_output=True, text=True,
                                timeout=180, check=False)
        if success:
            assert result.returncode == 0, result.stdout[-16000:] + result.stderr[-4000:]
        else:
            assert result.returncode != 0, "Expected role execution to fail\n" + result.stdout
        assert not (self.snapshots / ".lock").exists(), "Task failures must release the snapshot lock"
        return result


@pytest.fixture(scope="module")
def captured(tmp_path_factory):
    case = OfflineRole(tmp_path_factory.mktemp("same-ip-captured"))
    case.run("capture_and_remove")
    assert case.manifest()["stage"] == "awaiting_ip_release"
    return case


def _mutations(calls):
    return [call for call in calls if call["module"].endswith("_workflow_manager")
            and call["module"] != "fabric_devices_info_workflow_manager"]


def _legacy_manifest(manifest, stage="fabric_removed", index=2):
    """Model the checksum produced by the original role, before fabric IDs."""
    legacy = deepcopy(manifest)
    legacy.update(schema_version=1, stage=stage, stage_index=index)
    legacy.pop("fabric_id", None)
    fields = ("schema_version", "controller", "fingerprint", "name", "site", "ips",
              "serial_by_ip", "old_devices", "payloads", "hashes")
    content = json.dumps({key: legacy[key] for key in fields}, sort_keys=True,
                         separators=(",", ":"), ensure_ascii=True)
    legacy["capture_checksum"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return legacy


def test_capture_passes_complete_batch_and_preserves_original_and_mapped_ports(captured):
    manifest = captured.manifest()
    assert captured.state()["devices"] == {}
    assert len(manifest["old_devices"]) == 2
    assert manifest["schema_version"] == 2
    assert manifest["fabric_id"] == "fabric-1"
    exported = yaml.safe_load((captured.snapshots / "two-edges" / "cleanup.yml").read_text())["config"]
    assert len(exported) == 2 * len(IPS)
    assert all(sum(entry["ip_address"] == ip for entry in exported) == 2 for ip in IPS)
    assert len(manifest["payloads"]["cleanup"]) == len(IPS)
    assert all(entry.get("port_assignments") and entry.get("port_channels") for entry in manifest["payloads"]["cleanup"])
    assert manifest["payloads"]["cleanup"][0]["port_assignments"][0]["interface_name"] == "GigabitEthernet1/0/5"
    assert manifest["payloads"]["restore"][0]["port_assignments"][0]["interface_name"] == "GigabitEthernet1/0/10"
    assert manifest["payloads"]["restore"][0]["port_channels"][0]["interface_names"] == [
        "TenGigabitEthernet1/1/1", "GigabitEthernet1/0/48"]
    calls = captured.state()["calls"]
    generators = [call for call in calls if call["module"].endswith("_playbook_config_generator")
                  and not call["args"]["file_path"].endswith("verify_ports.yml")]
    assert len(generators) == 5
    assert all(set(call["targets"]) == set(IPS) for call in generators)
    mutations = _mutations(calls)
    assert [call["module"] for call in mutations] == [
        "sda_host_port_onboarding_workflow_manager", "sda_fabric_devices_workflow_manager",
        "provision_workflow_manager", "inventory_workflow_manager"]
    assert all(set(call["targets"]) == set(IPS) for call in mutations)
    assert mutations[0]["args"]["config"] == manifest["payloads"]["cleanup"]
    fabric_queries = [call for call in calls if call["module"] == "sda_fabric_devices_info"]
    assert fabric_queries
    assert all(call["args"]["fabricId"] == "fabric-1" for call in fabric_queries)
    assert {call["args"]["networkDeviceId"] for call in fabric_queries} == {item["uuid"] for item in manifest["old_devices"]}
    first_mutation = calls.index(mutations[0])
    assert any(call["module"] == "sda_fabric_devices_info" for call in calls[:first_mutation])
    assert captured.manifest_path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("component", ["port_assignments", "port_channels"])
def test_duplicate_component_interfaces_fail_capture_before_teardown(tmp_path, component):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch("discovery")
    state = case.state()
    state["duplicate_host_component"] = component
    case.save_state(state)
    case.run("capture_and_remove", success=False)
    assert set(case.state()["devices"]) == set(IPS)
    assert _mutations(case.state()["calls"]) == []
    assert not case.manifest_path.exists()


def test_restore_bulk_stages_from_snapshot_and_refuse_teardown_afterwards(captured, tmp_path):
    case = OfflineRole(tmp_path, baseline=captured)
    original = case.manifest()
    case.run("restore")
    final = case.manifest()
    state = case.state()
    assert final["stage"] == "complete"
    assert final["payloads"] == original["payloads"]
    assert final["hashes"] == original["hashes"]
    assert state["provisioned"] == {ip: SITE + "/Floor" + str(index + 1) for index, ip in enumerate(IPS)}
    mutations = _mutations(state["calls"])
    assert [call["module"] for call in mutations] == [
        "lan_automation_workflow_manager", "inventory_workflow_manager", "provision_workflow_manager",
        "sda_fabric_devices_workflow_manager", "sda_host_port_onboarding_workflow_manager"]
    assert all(set(call["targets"]) == set(IPS) for call in mutations)
    assert all(call["args"]["state"] == "merged" for call in mutations)
    assert mutations[-1]["args"]["config"] == original["payloads"]["restore"]
    assert all(not call["module"].endswith("_playbook_config_generator")
               or call["module"] == "sda_host_port_onboarding_playbook_config_generator" for call in state["calls"])
    devices = mutations[0]["args"]["config"][0]["lan_automation"]["discovery_devices"]
    assert [device["device_host_name"] for device in devices] == ["edge-10", "edge-11"]
    assert [device["device_site_name_hierarchy"] for device in devices] == [SITE + "/Floor1", SITE + "/Floor2"]
    count = len(state["calls"])
    case.run("restore")
    assert case.manifest()["stage"] == "complete"
    assert _mutations(case.state()["calls"][count:]) == []
    count = len(case.state()["calls"])
    case.run("capture_and_remove", success=False)
    assert _mutations(case.state()["calls"][count:]) == []


def test_partial_removal_resumes_without_recapturing_or_deleting_replacements(tmp_path):
    case = OfflineRole(tmp_path)
    state = case.state()
    state["failure"] = {"module": "inventory_workflow_manager", "state": "deleted", "remaining": 1}
    case.save_state(state)
    case.run("capture_and_remove", success=False)
    first = case.manifest()
    assert first["stage"] == "fabric_removed"
    assert set(case.state()["devices"]) == {IPS[1]}
    count = len(case.state()["calls"])
    case.run("capture_and_remove")
    final = case.manifest()
    assert final["stage"] == "awaiting_ip_release"
    assert final["payloads"] == first["payloads"]
    assert final["old_devices"] == first["old_devices"]
    resumed = case.state()["calls"][count:]
    assert not any(call["module"].endswith("_playbook_config_generator") for call in resumed)
    assert all(call["targets"] == [IPS[1]] for call in _mutations(resumed))


def test_partial_restore_resumes_without_relaunching_lan_or_recapturing(captured, tmp_path):
    case = OfflineRole(tmp_path, baseline=captured)
    state = case.state()
    state["failure"] = {"module": "sda_fabric_devices_workflow_manager", "state": "merged", "remaining": 1}
    case.save_state(state)
    case.run("restore", success=False)
    first = case.manifest()
    assert first["stage"] == "provisioned"
    count = len(case.state()["calls"])
    case.run("restore")
    assert case.manifest()["stage"] == "complete"
    assert case.manifest()["payloads"] == first["payloads"]
    resumed = case.state()["calls"][count:]
    assert not any(call["module"] == "lan_automation_workflow_manager" for call in resumed)
    assert all(not call["module"].endswith("_playbook_config_generator")
               or call["module"] == "sda_host_port_onboarding_playbook_config_generator" for call in resumed)
    assert all(call["args"].get("state") != "deleted" for call in _mutations(resumed))


def test_interrupted_lan_with_incomplete_collection_can_resume(captured, tmp_path):
    case = OfflineRole(tmp_path, baseline=captured)
    manifest = case.manifest()
    manifest.update(stage="restore_started", stage_index=5)
    case.manifest_path.write_text(json.dumps(manifest))
    state = case.state()
    state["devices"][IPS[0]] = {"managementIpAddress": IPS[0], "serialNumber": "NEW-SERIAL-10"}
    case.save_state(state)
    case.run("restore")
    assert case.manifest()["stage"] == "complete"
    lan_calls = [call for call in _mutations(case.state()["calls"])
                 if call["module"] == "lan_automation_workflow_manager"]
    assert len(lan_calls) == 1
    assert set(lan_calls[0]["targets"]) == set(IPS)


@pytest.mark.parametrize("wrong", ["serial", "uuid"])
def test_restore_rejects_wrong_physical_identity_before_mutations(captured, tmp_path, wrong):
    case = OfflineRole(tmp_path, baseline=captured)
    # Model an interrupted launch after the durable restoration boundary, so
    # the replacement identity guard itself must reject the unexpected device.
    manifest = case.manifest()
    manifest.update(stage="restore_started", stage_index=5)
    case.manifest_path.write_text(json.dumps(manifest))
    state = case.state()
    record = deepcopy(_initial_state()["devices"][IPS[0]])
    record["serialNumber"] = "WRONG-SERIAL" if wrong == "serial" else "NEW-SERIAL-10"
    record["id"] = "unexpected-uuid" if wrong == "serial" else "old-uuid-10"
    state["devices"][IPS[0]] = record
    case.save_state(state)
    case.run("restore", success=False)
    assert _mutations(case.state()["calls"]) == []


@pytest.mark.parametrize("tamper", ["payload", "controller", "input"])
def test_restore_rejects_changed_snapshot_or_inputs_before_controller_calls(captured, tmp_path, tamper):
    case = OfflineRole(tmp_path, baseline=captured)
    extra = None
    if tamper == "payload":
        manifest = case.manifest()
        manifest["payloads"]["restore"][0]["port_assignments"][0]["data_vlan_name"] = "TAMPERED"
        case.manifest_path.write_text(json.dumps(manifest))
    elif tamper == "controller":
        extra = {"catalystcenter_host": "another-controller.example.test"}
    else:
        case.batch["device_mapping"][0]["interface_migration"]["port_assignments"][0]["destination"] = "GigabitEthernet1/0/20"
    case.run("restore", success=False, extra=extra)
    assert case.state()["calls"] == []


def test_unprovisioning_that_already_deletes_inventory_skips_redundant_delete(tmp_path):
    case = OfflineRole(tmp_path)
    state = case.state()
    state["unprovision_deletes_inventory"] = True
    case.save_state(state)
    case.run("capture_and_remove")
    assert case.manifest()["stage"] == "awaiting_ip_release"
    assert not any(call["module"] == "inventory_workflow_manager" and call["args"]["state"] == "deleted"
                   for call in case.state()["calls"])


@pytest.mark.parametrize("phase", ["capture_and_remove", "restore"])
def test_legacy_snapshots_resolve_fabric_after_old_inventory_deletion(captured, tmp_path, phase):
    case = OfflineRole(tmp_path, baseline=captured)
    legacy = _legacy_manifest(case.manifest(), *(('awaiting_ip_release', 4) if phase == "restore" else ('fabric_removed', 2)))
    case.manifest_path.write_text(json.dumps(legacy))
    assert case.state()["devices"] == {}
    case.run(phase)
    final = case.manifest()
    assert final["stage"] == ("complete" if phase == "restore" else "awaiting_ip_release")
    assert final["schema_version"] == 1
    assert "fabric_id" not in final
    assert final["capture_checksum"] == legacy["capture_checksum"]
    assert final["payloads"] == legacy["payloads"]
    calls = case.state()["calls"]
    assert any(call["module"] == "sites_info" and call["args"]["nameHierarchy"] == SITE for call in calls)
    assert any(call["module"] == "sda_fabric_sites_info" and call["args"]["siteId"] == "site-1" for call in calls)
    assert all(call["args"]["fabricId"] == "fabric-1" for call in calls if call["module"] == "sda_fabric_devices_info")
    assert not any(call["module"].endswith("_playbook_config_generator")
                   and not call["args"]["file_path"].endswith("verify_ports.yml") for call in calls)
    if phase == "capture_and_remove":
        assert _mutations(calls) == []


def test_stale_uuid_membership_blocks_legacy_recovery_even_without_inventory(captured, tmp_path):
    case = OfflineRole(tmp_path, baseline=captured)
    legacy = _legacy_manifest(case.manifest())
    case.manifest_path.write_text(json.dumps(legacy))
    state = case.state()
    uuid = legacy["old_devices"][0]["uuid"]
    state["fabric_memberships"][uuid] = {"networkDeviceId": uuid, "fabricId": "fabric-1", "deviceRoles": ["EDGE_NODE"]}
    case.save_state(state)
    case.run("capture_and_remove", success=False)
    assert case.state()["devices"] == {}
    assert case.manifest()["stage"] == "fabric_removed"
    assert _mutations(case.state()["calls"]) == []
    state = case.state()
    state["fabric_memberships"].clear()
    case.save_state(state)
    case.run("capture_and_remove")
    assert case.manifest()["stage"] == "awaiting_ip_release"
    assert case.manifest()["capture_checksum"] == legacy["capture_checksum"]


def test_fabric_query_contract_is_checked_before_old_device_mutations(tmp_path):
    case = OfflineRole(tmp_path)
    state = case.state()
    state["reject_fabric_queries"] = True
    case.save_state(state)
    case.run("capture_and_remove", success=False)
    assert set(case.state()["devices"]) == set(IPS)
    assert case.manifest()["stage"] == "captured"
    assert _mutations(case.state()["calls"]) == []


@pytest.mark.parametrize("failure", ["api_error", "missing", "ambiguous"])
def test_unresolvable_fabric_fails_before_capturing_or_removing_devices(tmp_path, failure):
    case = OfflineRole(tmp_path)
    state = case.state()
    if failure == "api_error":
        state["fabric_lookup_failed"] = True
    elif failure == "missing":
        state["fabric_sites"] = []
    else:
        state["fabric_sites"] = [{"id": "fabric-1", "siteId": "site-1"}, {"id": "fabric-2", "siteId": "site-1"}]
    case.save_state(state)
    case.run("capture_and_remove", success=False)
    calls = case.state()["calls"]
    assert _mutations(calls) == []
    assert not any(call["module"].endswith("_playbook_config_generator") for call in calls)
    assert not case.manifest_path.exists()


def test_changed_fabric_identity_cannot_retarget_a_saved_snapshot(captured, tmp_path):
    case = OfflineRole(tmp_path, baseline=captured)
    state = case.state()
    state["fabric_sites"] = [{"id": "recreated-fabric", "siteId": "site-1"}]
    case.save_state(state)
    case.run("restore", success=False)
    assert _mutations(case.state()["calls"]) == []
    assert not any(call["module"] == "sda_fabric_devices_info" for call in case.state()["calls"])
    assert case.manifest()["fabric_id"] == "fabric-1"


def test_legacy_scope_can_resolve_a_zone_without_old_inventory(captured, tmp_path):
    case = OfflineRole(tmp_path, baseline=captured)
    case.manifest_path.write_text(json.dumps(_legacy_manifest(case.manifest())))
    state = case.state()
    state["fabric_sites"] = []
    state["fabric_zones"] = [{"id": "fabric-1", "siteId": "site-1"}]
    case.save_state(state)
    case.run("capture_and_remove")
    assert case.manifest()["stage"] == "awaiting_ip_release"
    assert any(call["module"] == "sda_fabric_zones_info" for call in case.state()["calls"])
    assert _mutations(case.state()["calls"]) == []


def test_generated_lan_role_captures_once_and_restores_saved_serial_mappings(tmp_path):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch()
    case.batch["new_devices"] = {"isis_domain_pwd": "runtime-isis-before"}
    case.run("capture_and_remove")
    snapshot = case.manifest()
    assert snapshot["schema_version"] == 3
    assert snapshot["stage"] == "awaiting_ip_release"
    assert "runtime-isis" not in case.manifest_path.read_text()
    lan = snapshot["onboarding"]["config"][0]["lan_automation"]
    assert [d["device_serial_number"] for d in lan["discovery_devices"]] == [
        "NEW-SERIAL-10",
        "NEW-SERIAL-11",
    ]
    assert [d["device_site_name_hierarchy"] for d in lan["discovery_devices"]] == [
        SITE + "/Floor1",
        SITE + "/Floor2",
    ]
    capture_calls = [
        call
        for call in case.state()["calls"]
        if call["module"] == "lan_automation_playbook_config_generator"
    ]
    assert len(capture_calls) == 1
    assert capture_calls[0]["args"]["config"] == {
        "ip_address_list": IPS,
        "site_name_hierarchy": SITE,
    }
    assert not capture_calls[0]["args"].get("isis_domain_pwd")
    count = len(case.state()["calls"])
    case.batch["new_devices"]["isis_domain_pwd"] = "runtime-isis-after"
    case.run("restore")
    assert case.manifest()["stage"] == "complete"
    calls = case.state()["calls"][count:]
    assert not any(call["module"] == "lan_automation_playbook_config_generator" for call in calls)
    launch = next(call for call in calls if call["module"] == "lan_automation_workflow_manager")
    assert launch["args"]["config"][0]["lan_automation"]["isis_domain_pwd"] == "runtime-isis-after"
    assert "runtime-isis" not in case.manifest_path.read_text()


def test_lan_hostname_submission_preserves_captured_fqdn_and_completed_verification(tmp_path):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch()
    expected = "IAC-TB4-SJ-EN1-9300.cisco.com"
    state = case.state()
    state["devices"][IPS[0]]["hostname"] = expected
    state["domains_by_ip"][IPS[0]] = "cisco.com"
    case.save_state(state)
    case.run("capture_and_remove")
    captured = case.manifest()
    assert captured["old_devices"][0]["hostname"] == expected
    assert captured["onboarding"]["config"][0]["lan_automation"]["discovery_devices"][0]["device_host_name"] == expected
    case.run("restore")
    final = case.manifest()
    assert final["stage"] == "complete"
    assert case.state()["devices"][IPS[0]]["hostname"] == expected
    for field in ("old_devices", "onboarding", "fingerprint", "hashes", "capture_checksum"):
        assert final[field] == captured[field]
    launches = [call for call in case.state()["calls"] if call["module"] == "lan_automation_workflow_manager"]
    assert len(launches) == 1
    devices = launches[0]["args"]["config"][0]["lan_automation"]["discovery_devices"]
    assert devices[0]["device_host_name"] == "IAC-TB4-SJ-EN1-9300"
    assert all("." not in device["device_host_name"] for device in devices)
    count = len(case.state()["calls"])
    case.run("restore")
    assert _mutations(case.state()["calls"][count:]) == []
    state = case.state()
    state["devices"][IPS[0]]["hostname"] += ".cisco.com"
    case.save_state(state)
    count = len(state["calls"])
    case.run("restore", success=False)
    assert _mutations(case.state()["calls"][count:]) == []


@pytest.mark.parametrize("fault", ["duplicate_domain", "wrong_domain", "short_only"])
def test_hostname_convergence_blocks_lan_restoration_before_provisioning(tmp_path, fault):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch()
    case.run("capture_and_remove")
    state = case.state()
    state["replacement_hostname_fault"] = fault
    case.save_state(state)
    count = len(state["calls"])
    case.run("restore", success=False)
    assert case.manifest()["stage"] == "restore_started"
    mutations = _mutations(case.state()["calls"][count:])
    assert [call["module"] for call in mutations] == ["lan_automation_workflow_manager"]
    if fault == "duplicate_domain":
        # A retry must validate the managed replacements, without launching
        # another onboarding session to repair a DNS/hostname mismatch.
        count = len(case.state()["calls"])
        case.run("restore", success=False)
        assert _mutations(case.state()["calls"][count:]) == []
        assert case.manifest()["stage"] == "restore_started"


def test_hostname_convergence_blocks_discovery_with_a_duplicated_domain(tmp_path):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch("discovery")
    case.run("capture_and_remove")
    _prepare_discovery_replacements(case)
    state = case.state()
    state["prepared_devices"][IPS[0]]["hostname"] += ".example.test"
    case.save_state(state)
    count = len(state["calls"])
    case.run("restore", success=False)
    assert case.manifest()["stage"] == "restore_started"
    mutations = _mutations(case.state()["calls"][count:])
    assert [call["module"] for call in mutations] == ["discovery_workflow_manager"]


@pytest.mark.parametrize("multiple_sessions", [False, True])
def test_explicit_lan_config_restores_without_old_lan_history(tmp_path, multiple_sessions):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch()
    config = deepcopy(_batch()["new_devices"]["lan_automation_config"])
    lan = config[0]["lan_automation"]
    lan.pop("discovery_devices")
    lan["peer_device_management_ip_address"] = "198.51.100.11"
    lan["ip_pools"].append({"ip_pool_name": "LAN_P2P", "ip_pool_role": "PHYSICAL_LINK_POOL"})
    if multiple_sessions:
        config.append(deepcopy(config[0]))
        for index, operation in enumerate(config):
            operation["lan_automation"]["primary_device_interface_names"] = [
                "GigabitEthernet1/0/%d" % (index + 1)
            ]
            operation["lan_automation"]["discovery_devices"] = [
                {"device_management_ip_address": IPS[index]}
            ]
    case.batch["new_devices"] = {
        "lan_automation_config": config, "isis_domain_pwd": "<isis-password>"
    }
    state = case.state()
    state["missing_lan_history"] = True
    case.save_state(state)
    case.run("capture_and_remove")
    snapshot = case.manifest()
    assert snapshot["stage"] == "awaiting_ip_release"
    assert snapshot["schema_version"] == 3
    saved = snapshot["onboarding"]["config"]
    devices = [d for op in saved for d in op["lan_automation"]["discovery_devices"]]
    assert {d["device_management_ip_address"]: d["device_serial_number"] for d in devices} == {
        ip: "NEW-SERIAL-" + ip.rsplit(".", 1)[1] for ip in IPS
    }
    assert [d["device_site_name_hierarchy"] for d in devices] == [
        SITE + "/Floor1", SITE + "/Floor2"
    ]
    assert [d["device_host_name"] for d in devices] == ["edge-10", "edge-11"]
    exported = yaml.safe_load((case.manifest_path.parent / "lan_automation.yml").read_text())
    assert exported["config"] == saved
    assert "<isis-password>" not in case.manifest_path.read_text()
    assert not any(
        call["module"] == "lan_automation_playbook_config_generator"
        for call in case.state()["calls"]
    )
    count = len(case.state()["calls"])
    changed = deepcopy(case.batch)
    case.batch["new_devices"]["lan_automation_config"][0]["lan_automation"]["ip_pools"][0][
        "ip_pool_name"
    ] = "OTHER_POOL"
    case.run("restore", success=False)
    assert case.state()["calls"][count:] == []
    case.batch = changed
    case.batch["new_devices"]["isis_domain_pwd"] = "<rotated-isis-password>"
    case.run("restore")
    assert case.manifest()["stage"] == "complete"
    launches = [call for call in case.state()["calls"][count:]
                if call["module"] == "lan_automation_workflow_manager"]
    assert len(launches) == 1
    restored = deepcopy(saved)
    for operation in restored:
        operation["lan_automation"]["isis_domain_pwd"] = "<rotated-isis-password>"
    assert launches[0]["args"]["config"] == restored
    assert not any(
        call["module"] == "lan_automation_playbook_config_generator"
        for call in case.state()["calls"][count:]
    )
    count = len(case.state()["calls"])
    case.run("restore")
    assert _mutations(case.state()["calls"][count:]) == []


@pytest.mark.parametrize("invalid", [None, [], [{"lan_automation": {}}]])
def test_invalid_explicit_lan_config_fails_before_generator_or_deletion(tmp_path, invalid):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch()
    case.batch["new_devices"] = {"lan_automation_config": invalid}
    case.run("capture_and_remove", success=False)
    assert case.state()["calls"] == []
    assert set(case.state()["devices"]) == set(IPS)
    assert not case.manifest_path.exists()


@pytest.mark.parametrize("credentials", ["global", "shared", "per_device"])
def test_discovery_role_restores_prepared_devices_with_runtime_credentials(tmp_path, credentials):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch("discovery")
    if credentials != "global":
        case.batch["new_devices"] = {
            "discovery": {
                "use_global_credentials": False,
                "discovery_specific_credentials": {
                    "cli_credentials_list": [
                        {"username": "shared-user", "password": "runtime-shared-secret"}
                    ],
                    "snmp_v2_read_credential": {"community": "runtime-snmp-secret"},
                },
            }
        }
    if credentials == "per_device":
        case.batch["device_mapping"][1]["discovery"] = {
            "discovery_specific_credentials": {
                "cli_credentials_list": [
                    {"username": "device-user", "password": "runtime-device-secret"}
                ]
            }
        }
    case.run("capture_and_remove")
    assert case.manifest()["onboarding"] == {"method": "discovery", "config": []}
    assert not any(
        call["module"] == "lan_automation_playbook_config_generator"
        for call in case.state()["calls"]
    )
    _prepare_discovery_replacements(case)
    count = len(case.state()["calls"])
    case.run("restore")
    assert case.manifest()["stage"] == "complete"
    mutations = _mutations(case.state()["calls"][count:])
    assert [call["module"] for call in mutations] == [
        "discovery_workflow_manager",
        "inventory_workflow_manager",
        "provision_workflow_manager",
        "sda_fabric_devices_workflow_manager",
        "sda_host_port_onboarding_workflow_manager",
    ]
    jobs = mutations[0]["args"]["config"]
    assert [job["ip_address_list"] for job in jobs] == [[ip] for ip in IPS]
    if credentials == "global":
        assert all(job["use_global_credentials"] for job in jobs)
    elif credentials == "per_device":
        assert (
            jobs[0]["discovery_specific_credentials"]["cli_credentials_list"][0]["username"]
            == "shared-user"
        )
        assert (
            jobs[1]["discovery_specific_credentials"]["cli_credentials_list"][0]["username"]
            == "device-user"
        )
        assert (
            jobs[1]["discovery_specific_credentials"]["snmp_v2_read_credential"]["community"]
            == "runtime-snmp-secret"
        )
    assert "runtime-" not in case.manifest_path.read_text()
    count = len(case.state()["calls"])
    case.run("restore")
    assert _mutations(case.state()["calls"][count:]) == []


def test_missing_lan_history_in_later_batch_prevents_every_removal(tmp_path):
    case = OfflineRole(tmp_path)
    first, second = _generated_batch(), _generated_batch()
    first["device_mapping"] = first["device_mapping"][:1]
    second["device_mapping"] = second["device_mapping"][1:]
    second["name"] = "second-batch"
    state = case.state()
    state["missing_lan_history_for"] = [IPS[1]]
    case.save_state(state)
    result = case.run(
        "capture_and_remove", success=False, extra={PREFIX + "batches": [first, second]}
    )
    assert "No matching stopped LAN automation history was found" in result.stdout
    assert "new_devices.lan_automation_config" in result.stdout
    assert "No old devices were removed" in result.stdout
    assert set(case.state()["devices"]) == set(IPS)
    assert _mutations(case.state()["calls"]) == []
    assert case.manifest()["stage"] == "captured"


def test_generated_seed_port_conflict_blocks_every_batch_removal(tmp_path):
    case = OfflineRole(tmp_path)
    first, second = _generated_batch(), _generated_batch()
    first["device_mapping"] = first["device_mapping"][:1]
    second["device_mapping"] = second["device_mapping"][1:]
    second["name"] = "second-batch"
    case.run("capture_and_remove", success=False, extra={PREFIX + "batches": [first, second]})
    assert set(case.state()["devices"]) == set(IPS)
    assert _mutations(case.state()["calls"]) == []
    assert case.manifest()["stage"] == "captured"
    second_manifest = json.loads((case.snapshots / "second-batch" / "manifest.json").read_text())
    assert second_manifest["stage"] == "captured"
    assert sum(call["module"] == "lan_automation_playbook_config_generator" for call in case.state()["calls"]) == 2


def test_discovery_wrong_replacement_serial_blocks_provisioning(tmp_path):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch("discovery")
    case.run("capture_and_remove")
    _prepare_discovery_replacements(case, wrong_serial=True)
    count = len(case.state()["calls"])
    case.run("restore", success=False)
    assert case.manifest()["stage"] == "restore_started"
    mutations = _mutations(case.state()["calls"][count:])
    assert [call["module"] for call in mutations] == ["discovery_workflow_manager"]


def test_partial_discovery_can_resume_without_recapturing_old_devices(tmp_path):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch("discovery")
    case.run("capture_and_remove")
    _prepare_discovery_replacements(case)
    state = case.state()
    state["failure"] = {"module": "discovery_workflow_manager", "state": "merged", "remaining": 1}
    case.save_state(state)
    case.run("restore", success=False)
    assert case.manifest()["stage"] == "restore_started"
    assert set(case.state()["devices"]) == {IPS[0]}
    count = len(case.state()["calls"])
    case.run("restore")
    assert case.manifest()["stage"] == "complete"
    assert not any(
        call["module"] == "lan_automation_playbook_config_generator"
        for call in case.state()["calls"][count:]
    )


def _golden_image():
    return {"image_name": "cat9k_iosxe.17.12.04.SPA.bin",
            "device_image_family_name": "Cisco Catalyst 9300 Switch"}


def test_swim_failure_retries_before_lan_with_rotated_credentials_and_no_teardown(tmp_path):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch()
    golden = _golden_image()
    golden["import_image_details"] = {"type": "remote", "url_details": {"payload": [
        {"source_url": "https://user:swim-secret-before@images.example/" + golden["image_name"]}]}}
    case.batch["new_devices"] = {"golden_image": golden}
    controls = {PREFIX + "swim_enabled": True, PREFIX + "config_verify": False,
                "catalystcenter_debug": True, "catalystcenter_log": True}
    captured_result = case.run("capture_and_remove", extra=controls)
    assert case.manifest()["schema_version"] == 4
    assert not any(call["module"] == "swim_workflow_manager" for call in case.state()["calls"])
    state = case.state()
    state["failure"] = {"module": "swim_workflow_manager", "state": "merged", "remaining": 1}
    case.save_state(state)
    count = len(state["calls"])
    failed = case.run("restore", success=False, extra=controls)
    assert case.manifest()["stage"] == "restore_started"
    mutations = _mutations(case.state()["calls"][count:])
    assert [call["module"] for call in mutations] == ["swim_workflow_manager"]
    assert mutations[0]["args"]["config_verify"] is True
    golden["import_image_details"]["url_details"]["payload"][0]["source_url"] = (
        "https://user:swim-secret-after@mirror.example/" + golden["image_name"])
    count = len(case.state()["calls"])
    controls[PREFIX + "swim_config_verify"] = False
    restored = case.run("restore", extra=controls)
    assert case.manifest()["stage"] == "complete"
    mutations = _mutations(case.state()["calls"][count:])
    assert [call["module"] for call in mutations[:2]] == ["swim_workflow_manager", "lan_automation_workflow_manager"]
    assert all(call["args"].get("state") != "deleted" for call in mutations)
    swim = mutations[0]["args"]
    assert swim["config_verify"] is False
    assert swim["catalystcenter_debug"] is False and swim["catalystcenter_log"] is False
    assert swim["catalystcenter_host"] == "offline-controller.example.test"
    assert swim["catalystcenter_api_task_timeout"] == 2
    assert "swim-secret-after" in json.dumps(swim["config"])
    assert swim["config"][0]["tagging_details"] == dict(_golden_image(), site_name=SITE, device_role="ALL", tagging=True)
    for output in (captured_result, failed, restored):
        assert "swim-secret-" not in output.stdout + output.stderr
    assert all("swim-secret-" not in path.read_text() for path in case.snapshots.rglob("*") if path.is_file())
    count = len(case.state()["calls"])
    case.run("restore", extra=controls)
    assert _mutations(case.state()["calls"][count:]) == []


@pytest.mark.parametrize("source", ["tag_only", "CCO"])
def test_swim_tag_only_and_cco_support_generated_and_legacy_batches(tmp_path, source):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch() if source == "tag_only" else _batch()
    golden = _golden_image()
    if source == "CCO":
        golden["import_image_details"] = {"type": "CCO", "cco_image_details": {"image_name": golden["image_name"]}}
    case.batch.setdefault("new_devices", {})["golden_image"] = golden
    controls = {PREFIX + "swim_enabled": True}
    case.run("capture_and_remove", extra=controls)
    assert case.manifest()["schema_version"] == 4
    count = len(case.state()["calls"])
    case.run("restore", extra=controls)
    calls = _mutations(case.state()["calls"][count:])
    assert [call["module"] for call in calls[:2]] == ["swim_workflow_manager", "lan_automation_workflow_manager"]
    config = calls[0]["args"]["config"][0]
    if source == "CCO":
        assert config["import_image_details"]["cco_image_details"]["image_name"] == [golden["image_name"]]
    else:
        assert set(config) == {"tagging_details"}
    assert case.manifest()["stage"] == "complete"


@pytest.mark.parametrize("mode", ["disabled", "already_ready", "discovery"])
def test_swim_skips_when_lan_image_preparation_is_not_required(tmp_path, mode):
    case = OfflineRole(tmp_path)
    case.batch = _generated_batch("discovery" if mode == "discovery" else "lan_automation")
    if mode != "discovery":
        case.batch["new_devices"] = {"golden_image": _golden_image()}
    controls = {PREFIX + "swim_enabled": mode != "disabled"}
    case.run("capture_and_remove", extra=controls)
    if mode in ("already_ready", "discovery"):
        _prepare_discovery_replacements(case)
    if mode == "already_ready":
        state = case.state()
        state["devices"] = deepcopy(state["prepared_devices"])
        case.save_state(state)
        manifest = case.manifest()
        manifest.update(stage="restore_started", stage_index=5)
        case.manifest_path.write_text(json.dumps(manifest))
    count = len(case.state()["calls"])
    case.run("restore", extra=controls)
    calls = case.state()["calls"][count:]
    assert not any(call["module"] == "swim_workflow_manager" for call in calls)
    if mode == "already_ready":
        assert not any(call["module"] == "lan_automation_workflow_manager" for call in calls)
    assert case.manifest()["stage"] == "complete"


@pytest.mark.parametrize("invalid", ["missing_image", "discovery_image", "conflicting_images", "enabled_type", "verify_type"])
def test_swim_invalid_input_fails_before_any_controller_call(tmp_path, invalid):
    case = OfflineRole(tmp_path)
    first = _generated_batch("discovery" if invalid == "discovery_image" else "lan_automation")
    controls = {PREFIX + "swim_enabled": True}
    if invalid != "missing_image":
        first["new_devices"] = {"golden_image": _golden_image()}
    batches = [first]
    if invalid == "conflicting_images":
        second = deepcopy(first)
        first["device_mapping"] = first["device_mapping"][:1]
        second["device_mapping"] = second["device_mapping"][1:]
        second["name"] = "second-batch"
        second["new_devices"]["golden_image"]["image_name"] = "other.bin"
        batches.append(second)
    elif invalid == "enabled_type":
        controls[PREFIX + "swim_enabled"] = "true"
    elif invalid == "verify_type":
        controls[PREFIX + "swim_config_verify"] = "false"
    controls[PREFIX + "batches"] = batches
    case.run("capture_and_remove", success=False, extra=controls)
    assert case.state()["calls"] == []
    assert set(case.state()["devices"]) == set(IPS)
