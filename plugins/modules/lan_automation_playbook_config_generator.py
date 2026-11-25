#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Capture LAN automation settings before replacing physical devices."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: lan_automation_playbook_config_generator
short_description: Generate LAN automation configuration for replacement devices
description:
  - Captures LAN automation configuration before existing devices are deleted
    from Cisco Catalyst Center and replaced with new physical devices.
  - Combines current inventory and site assignments with historical LAN
    automation sessions to preserve hostnames, management IPs, and sites.
  - Generates a YAML variable file compatible with
    M(cisco.catalystcenter.lan_automation_workflow_manager).
  - Replaces each device serial number with an IP-specific placeholder that
    must be edited before replaying the configuration.
version_added: '2.14.0'
extends_documentation_fragment:
  - cisco.catalystcenter.workflow_manager_params
author:
  - Vivek Raj Penke (@vpenke)
options:
  catalystcenter_version:
    description: Cisco Catalyst Center API version used by the SDK.
    type: str
    default: '2.3.7.9'
    aliases: [dnac_version]
  state:
    description: Gather existing configuration without modifying Catalyst Center.
    type: str
    choices: [gathered]
    default: gathered
  config:
    description: Devices and site scope to capture before replacement.
    type: dict
    required: true
    suboptions:
      ip_address_list:
        description: Non-empty list of current device management IPv4 addresses.
        type: list
        elements: str
        required: true
      site_name_hierarchy:
        description:
          - Full site hierarchy, for example C(Global/Region/Building).
          - Each device must currently belong to this site or a descendant.
          - Each device's exact current site is preserved in the generated file.
        type: str
        required: true
  isis_domain_pwd:
    description:
      - Optional IS-IS domain password to include in every generated session.
      - May be supplied through an Ansible Vault variable.
      - The status API does not return this password. When omitted, add it to
        the generated file before replay if the original session used one.
      - A supplied value is written to the local file in plaintext. New or
        rewritten files have owner-only permissions; use Ansible Vault to encrypt them
        when retaining secrets.
    type: str
  file_path:
    description:
      - Output YAML variable file. Parent directories are created as needed.
      - Defaults to C(lan_automation_playbook_config_YYYY-MM-DD_HH-MM-SS.yml)
        in the current working directory.
    type: path
  file_mode:
    description:
      - C(overwrite) replaces the destination with the generated configuration.
      - C(append) adds distinct configuration entries to its C(config) list,
        preserving a single YAML document suitable for C(include_vars).
      - Identical entries are skipped. Conflicting entries for the same
        management IP are rejected; use overwrite to regenerate them.
      - Existing files are compared by YAML content to avoid unnecessary writes.
    type: str
    choices: [overwrite, append]
    default: overwrite
requirements:
  - catalystcentersdk >= 3.2.3.0.0
  - python >= 3.12
  - PyYAML
notes:
  - Requires Catalyst Center version 2.3.7.9 or later.
  - Run before deleting the old devices. Current inventory supplies the
    hostname, serial number, management IP, and exact site assignment.
  - Serial numbers identify historical sessions, preventing an old session
    for a different physical device at the same IP from being selected.
  - The most recent stopped, inactive session in the device's site ancestry
    with evidence that it discovered the device is selected. Ambiguous or
    incomplete data causes failure before any file is written.
  - Primary and peer seeds, seed interfaces, and IP pools must remain available.
    Replacing seed devices is outside this module's scope.
  - Devices are grouped by source session, with at most 50 devices per entry.
    Generated entries use C(launch_and_wait=true) to permit sequential replay.
  - Preserves supported session options, including multicast, IS-IS-to-BGP
    redistribution, hostname prefix, discovery level, and a nonzero timeout.
  - Individual physical-link IP addresses, fabric roles, provisioning, and
    host-port configuration are not captured by this module.
  - Check mode gathers and validates data and predicts local file changes,
    without creating files or directories. Catalyst Center is never modified.
  - SDK methods used are
    C(lan_automation.lan_automation_status),
    C(lan_automation.lan_automation_active_sessions),
    C(devices.get_network_device_by_ip), and
    C(site_design.get_site_assigned_network_device).
  - Paths used are GET /dna/intent/api/v1/lan-automation/status,
    GET /dna/intent/api/v1/lan-automation/sessions,
    GET /dna/intent/api/v1/network-device/ip-address/{ipAddress}, and
    GET /dna/intent/api/v1/networkDevices/{id}/assignedToSite.
seealso:
  - module: cisco.catalystcenter.lan_automation_workflow_manager
"""

EXAMPLES = r"""
- name: Capture devices before physical replacement
  cisco.catalystcenter.lan_automation_playbook_config_generator:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_version: "2.3.7.9"
    state: gathered
    file_path: "./replacement_lan_automation.yml"
    config:
      site_name_hierarchy: Global/Region/Building
      ip_address_list:
        - "192.0.2.10"
        - "192.0.2.11"
    # Optional when the original sessions used the same IS-IS password:
    # isis_domain_pwd: "{{ vault_lan_automation_isis_domain_pwd }}"

# After capture, replace REPLACE_WITH_SERIAL_FOR_192_0_2_10 (and other
# serial placeholders) in replacement_lan_automation.yml with the new serials.
# Add isis_domain_pwd if required, then delete the old devices through your
# replacement workflow and connect the new devices in the required PnP state.
- name: Load the edited replacement configuration
  ansible.builtin.include_vars:
    file: "./replacement_lan_automation.yml"
    name: replacement_lan

- name: Onboard the new physical devices using the captured settings
  cisco.catalystcenter.lan_automation_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_version: "2.3.7.9"
    state: merged
    config: "{{ replacement_lan.config }}"
"""

RETURN = r"""
file_path:
  description: Absolute path to the generated variable file.
  returned: success
  type: str
  sample: /tmp/replacement_lan_automation.yml
generated_config:
  description: Complete configuration represented by the destination file.
  returned: success
  type: dict
  sample:
    config:
      - lan_automation:
          discovered_device_site_name_hierarchy: Global/Region/Building
          primary_device_management_ip_address: 198.51.100.10
          primary_device_interface_names: [GigabitEthernet1/0/1]
          ip_pools:
            - ip_pool_name: LAN_AUTO_MAIN
              ip_pool_role: MAIN_POOL
          discovery_devices:
            - device_serial_number: REPLACE_WITH_SERIAL_FOR_192_0_2_10
              device_host_name: access-01
              device_management_ip_address: 192.0.2.10
              device_site_name_hierarchy: Global/Region/Building
          launch_and_wait: true
response:
  description: Summary of the devices and source sessions captured in this run.
  returned: success
  type: dict
  sample:
    device_count: 1
    session_count: 1
    source_session_ids: [session-1]
"""

import copy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import ipaddress
import os
import tempfile

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter import (
    CatalystCenterBase,
    catalystcenter_argument_spec,
)

try:
    import yaml
except ImportError:
    yaml = None


class LanAutomationPlaybookGenerator(CatalystCenterBase):
    """Gather device identities and transform their discovery sessions to YAML."""

    def fail_and_exit(self, msg):
        """Report capture failures without writing partial configuration."""
        self.module.fail_json(msg=msg)

    def validate_input(self):
        """Validate value constraints before fetching any configuration."""
        if self.compare_catalystcenter_versions(self.get_ccc_version(), "2.3.7.9") < 0:
            self.fail_and_exit(
                "LAN automation configuration generation requires Catalyst Center 2.3.7.9 or later."
            )
        self.site = self.config["site_name_hierarchy"].strip()
        if (self.site != "Global" and not self.site.startswith("Global/")) or any(
            not part.strip() for part in self.site.split("/")
        ):
            self.fail_and_exit(
                "site_name_hierarchy must be a full hierarchy such as Global/Region/Building."
            )
        addresses = self.config["ip_address_list"]
        if not addresses:
            self.fail_and_exit(
                "ip_address_list must contain at least one device management IP."
            )
        for address in addresses:
            self.validate_ipv4(address, "ip_address_list")
        if len(set(addresses)) != len(addresses):
            self.fail_and_exit(
                "ip_address_list must not contain duplicate management IPs."
            )
        self.addresses = sorted(addresses, key=ipaddress.IPv4Address)
        file_path = self.params.get("file_path") or datetime.now().strftime(
            "lan_automation_playbook_config_%Y-%m-%d_%H-%M-%S.yml"
        )
        self.file_path = os.path.abspath(os.path.expanduser(file_path))
        if os.path.splitext(self.file_path)[1].lower() not in (".yml", ".yaml"):
            self.fail_and_exit("file_path must have a .yml or .yaml extension.")
        return self

    def validate_ipv4(self, address, field):
        """Reject missing, malformed, and IPv6 addresses unsupported by replay."""
        try:
            ipaddress.IPv4Address(address)
        except (ValueError, TypeError, ipaddress.AddressValueError):
            self.fail_and_exit(
                "Invalid IPv4 address for {0}: {1!r}.".format(field, address)
            )

    def get_response(self, family, function, params=None):
        """Execute a read-only SDK call and require a structured response."""
        try:
            result = self.catalystcenter._exec(
                family=family, function=function, params=params or {}, op_modifies=False
            )
        except Exception as exc:
            self.fail_and_exit("Unable to retrieve {0}: {1}".format(function, exc))
        if not isinstance(result, dict) or "response" not in result:
            self.fail_and_exit("Malformed response from {0}.".format(function))
        return result["response"]

    def get_sessions(self):
        """Read the complete session history using the API's ten-entry limit."""
        sessions, seen = [], set()
        offset = 1
        while True:
            page = self.get_response(
                "lan_automation",
                "lan_automation_status",
                {"offset": offset, "limit": 10},
            )
            if not isinstance(page, list):
                self.fail_and_exit(
                    "LAN automation status response must contain a list of sessions."
                )
            for session in page:
                session_id = session.get("id") if isinstance(session, dict) else None
                if (
                    not isinstance(session_id, str)
                    or not session_id
                    or session_id in seen
                ):
                    self.fail_and_exit(
                        "LAN automation status contains a missing or repeated session ID; capture is incomplete."
                    )
                seen.add(session_id)
                sessions.append(session)
            if len(page) < 10:
                break
            offset += len(page)
        active = self.get_response("lan_automation", "lan_automation_active_sessions")
        if not isinstance(active, dict) or not isinstance(
            active.get("activeSessionIds"), list
        ):
            self.fail_and_exit("Unable to determine active LAN automation session IDs.")
        if any(not isinstance(value, str) for value in active["activeSessionIds"]):
            self.fail_and_exit("Malformed active LAN automation session IDs.")
        self.active_ids = set(active["activeSessionIds"])
        return sessions

    @staticmethod
    def is_within_site(site, parent):
        """Match complete path segments rather than similarly named sites."""
        return (
            isinstance(site, str)
            and isinstance(parent, str)
            and bool(parent)
            and (site == parent or site.startswith(parent + "/"))
        )

    def get_device(self, address):
        """Capture authoritative identity and current site before deletion."""
        device = self.get_response(
            "devices", "get_network_device_by_ip", {"ip_address": address}
        )
        if (
            not isinstance(device, dict)
            or any(
                not isinstance(device.get(key), str) or not device[key].strip()
                for key in ("id", "hostname", "serialNumber")
            )
            or device.get("managementIpAddress") != address
        ):
            self.fail_and_exit(
                "Incomplete or mismatched inventory identity for management IP {0}.".format(
                    address
                )
            )
        assignment = self.get_response(
            "site_design", "get_site_assigned_network_device", {"id": device["id"]}
        )
        if (
            not isinstance(assignment, dict)
            or assignment.get("deviceId") != device["id"]
        ):
            self.fail_and_exit(
                "Incomplete or mismatched site assignment for {0}.".format(address)
            )
        site = assignment.get("siteNameHierarchy")
        if not self.is_within_site(site, self.site):
            self.fail_and_exit(
                "Device {0} is not assigned to {1} or a descendant site (current site: {2}).".format(
                    address, self.site, site
                )
            )
        return {
            "ip": address,
            "hostname": device["hostname"],
            "site": site,
            "serials": {
                serial.strip()
                for serial in device["serialNumber"].split(",")
                if serial.strip()
            },
        }

    def session_discovered_device(self, session, device):
        """Match physical identity and actual discovery, never reused IPs alone."""
        for key, serial_key in (
            ("discoveredDeviceList", "serialNumber"),
            ("discoveryDevices", "deviceSerialNumber"),
        ):
            entries = session.get(key) or []
            if not isinstance(entries, list) or any(
                not isinstance(entry, dict) for entry in entries
            ):
                self.fail_and_exit(
                    "Malformed {0} in session {1}.".format(key, session["id"])
                )
            for entry in entries:
                if entry.get(serial_key) not in device["serials"]:
                    continue
                if (
                    key == "discoveredDeviceList"
                    and str(entry.get("state", "")).lower() == "added to inventory"
                ):
                    return True
                if (
                    key == "discoveryDevices"
                    and entry.get("isDeviceDiscovered") is True
                ):
                    return True
        return False

    def session_time(self, session):
        """Normalize epoch, ISO, and controller GMT timestamps for ordering."""
        value = session.get("creationTime")
        try:
            number = float(value)
            if number > 100000000000:
                number /= 1000
            if number > 0 and number < float("inf"):
                return number
        except (TypeError, ValueError, OverflowError):
            pass
        try:
            try:
                timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                # Catalyst Center also returns dates such as
                # "17 Nov 2026 21:40:05 GMT". Preserve the explicit timezone.
                timestamp = parsedate_to_datetime(str(value))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return timestamp.timestamp()
        except (TypeError, ValueError, OverflowError, OSError):
            self.fail_and_exit(
                "Cannot order matching sessions: session {0} has an invalid creationTime {1!r}.".format(
                    session["id"], value
                )
            )

    def select_session(self, sessions, device):
        """Choose the latest stopped source session with an unambiguous time."""
        candidates = []
        for session in sessions:
            if not self.is_within_site(
                device["site"], session.get("discoveredDeviceSiteNameHierarchy")
            ):
                continue
            if not self.session_discovered_device(session, device):
                continue
            if (
                session["id"] in self.active_ids
                or str(session.get("action", "")).upper() != "STOP"
            ):
                self.fail_and_exit(
                    "Device {0} belongs to an active or unfinished session {1}; finish it before capture.".format(
                        device["ip"], session["id"]
                    )
                )
            candidates.append(session)
        if not candidates:
            self.fail_and_exit(
                "No stopped LAN automation session with discovery evidence was found for device {0} and its current serial number/site.".format(
                    device["ip"]
                )
            )
        if len(candidates) == 1:
            return candidates[0]
        timed = [(self.session_time(session), session) for session in candidates]
        newest = max(timestamp for timestamp, _ in timed)
        latest = [session for timestamp, session in timed if timestamp == newest]
        if len(latest) != 1:
            self.fail_and_exit(
                "Multiple latest LAN automation sessions match device {0}; session history is ambiguous.".format(
                    device["ip"]
                )
            )
        return latest[0]

    def transform_session(self, session):
        """Map only settings accepted by the existing workflow manager."""
        seed = session.get("primaryDeviceManagmentIPAddress")
        self.validate_ipv4(seed, "primary seed in session " + session["id"])
        interfaces = session.get("primaryDeviceInterfaceNames")
        if (
            not isinstance(interfaces, list)
            or not interfaces
            or any(not isinstance(name, str) or not name.strip() for name in interfaces)
        ):
            self.fail_and_exit(
                "Missing or invalid primary seed interfaces in session {0}.".format(
                    session["id"]
                )
            )
        pools = session.get("ipPools")
        if (
            not isinstance(pools, list)
            or not pools
            or any(
                not isinstance(pool, dict)
                or not isinstance(pool.get("ipPoolName"), str)
                or not pool["ipPoolName"].strip()
                or pool.get("ipPoolRole") not in ("MAIN_POOL", "PHYSICAL_LINK_POOL")
                for pool in pools
            )
            or not any(pool["ipPoolRole"] == "MAIN_POOL" for pool in pools)
        ):
            self.fail_and_exit(
                "Missing or invalid IP pools in session {0}.".format(session["id"])
            )
        protocol = session.get("routingProtocol")
        if session.get("ipV6Only") or (protocol and protocol not in ("ISIS", "IS-IS")):
            self.fail_and_exit(
                "Session {0} uses routing options unsupported by lan_automation_workflow_manager.".format(
                    session["id"]
                )
            )
        result = {
            "discovered_device_site_name_hierarchy": session[
                "discoveredDeviceSiteNameHierarchy"
            ],
            "primary_device_management_ip_address": seed,
            "primary_device_interface_names": copy.deepcopy(interfaces),
            "ip_pools": [
                {"ip_pool_name": pool["ipPoolName"], "ip_pool_role": pool["ipPoolRole"]}
                for pool in pools
            ],
        }
        peer = session.get("peerDeviceManagmentIPAddress")
        if peer:
            self.validate_ipv4(peer, "peer seed in session " + session["id"])
            if peer == seed:
                self.fail_and_exit(
                    "Primary and peer seeds are identical in session {0}.".format(
                        session["id"]
                    )
                )
            result["peer_device_management_ip_address"] = peer
        for source, destination in (
            ("multicastEnabled", "multicast_enabled"),
            ("redistributeIsisToBgp", "redistribute_isis_to_bgp"),
        ):
            if session.get(source) is not None:
                if not isinstance(session[source], bool):
                    self.fail_and_exit(
                        "Invalid {0} in session {1}.".format(source, session["id"])
                    )
                result[destination] = session[source]
        for source, destination, lower, upper in (
            ("discoveryLevel", "discovery_level", 1, 5),
            ("discoveryTimeout", "discovery_timeout", 20, 10080),
        ):
            value = session.get(source)
            if value is None or (source == "discoveryTimeout" and value == 0):
                continue
            if type(value) is not int or not lower <= value <= upper:
                self.fail_and_exit(
                    "Invalid {0} in session {1}.".format(source, session["id"])
                )
            result[destination] = value
        if session.get("hostNamePrefix"):
            if not isinstance(session["hostNamePrefix"], str):
                self.fail_and_exit(
                    "Invalid hostNamePrefix in session {0}.".format(session["id"])
                )
            result["host_name_prefix"] = session["hostNamePrefix"]
        if self.params.get("isis_domain_pwd") is not None:
            result["isis_domain_pwd"] = self.params["isis_domain_pwd"]
        return result

    def generate_config(self):
        """Build the complete capture before touching the output file."""
        sessions = self.get_sessions()
        groups = {}
        for address in self.addresses:
            device = self.get_device(address)
            session = self.select_session(sessions, device)
            if session["id"] not in groups:
                groups[session["id"]] = self.transform_session(session)
                groups[session["id"]]["discovery_devices"] = []
            groups[session["id"]]["discovery_devices"].append(
                {
                    "device_serial_number": "REPLACE_WITH_SERIAL_FOR_"
                    + address.replace(".", "_"),
                    "device_host_name": device["hostname"],
                    "device_management_ip_address": address,
                    "device_site_name_hierarchy": device["site"],
                }
            )
        config = []
        for session in groups.values():
            seeds = {
                session["primary_device_management_ip_address"],
                session.get("peer_device_management_ip_address"),
            }
            if seeds.intersection(self.addresses):
                self.fail_and_exit(
                    "A requested replacement device is a primary or peer seed required by the generated configuration."
                )
            for start in range(0, len(session["discovery_devices"]), 50):
                entry = copy.deepcopy(session)
                entry["discovery_devices"] = entry["discovery_devices"][
                    start : start + 50
                ]
                entry["launch_and_wait"] = True
                config.append({"lan_automation": entry})
        self.source_session_ids = list(groups)
        return {"config": config}

    def write_config(self, generated):
        """Atomically write a replayable YAML document, respecting check mode."""
        existing = None
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, encoding="utf-8") as stream:
                    content = stream.read()
                try:
                    existing = yaml.safe_load(content)
                except yaml.YAMLError:
                    if self.params["file_mode"] == "append":
                        self.fail_and_exit(
                            "Cannot append to an invalid YAML file: " + self.file_path
                        )
        except OSError as exc:
            self.fail_and_exit(
                "Unable to read output file {0}: {1}".format(self.file_path, exc)
            )
        output = copy.deepcopy(generated)
        if self.params["file_mode"] == "append" and existing is not None:
            if (
                not isinstance(existing, dict)
                or set(existing) != {"config"}
                or not isinstance(existing["config"], list)
            ):
                self.fail_and_exit(
                    "Append requires an existing YAML document containing a config list."
                )
            output = copy.deepcopy(existing)
            for entry in generated["config"]:
                if entry not in output["config"]:
                    output["config"].append(entry)
            addresses = []
            for entry in output["config"]:
                if not isinstance(entry, dict) or not isinstance(
                    entry.get("lan_automation"), dict
                ):
                    self.fail_and_exit(
                        "Append requires LAN automation configuration entries."
                    )
                devices = entry["lan_automation"].get("discovery_devices")
                if not isinstance(devices, list) or any(
                    not isinstance(device, dict)
                    or not device.get("device_management_ip_address")
                    for device in devices
                ):
                    self.fail_and_exit(
                        "Append requires discovery_devices with management IP addresses."
                    )
                addresses.extend(
                    device["device_management_ip_address"] for device in devices
                )
            if len(set(addresses)) != len(addresses):
                self.fail_and_exit(
                    "Append would duplicate a management IP with conflicting settings; use overwrite instead."
                )
        changed = existing != output
        if changed and not self.module.check_mode:
            temporary = None
            try:
                text = (
                    "# Replace every REPLACE_WITH_SERIAL_FOR_<IP> value with the NEW device serial.\n"
                    "# Supply isis_domain_pwd before replay if the original session used one.\n"
                    "# Seeds, seed interfaces, and IP pools must remain available.\n"
                    + yaml.safe_dump(
                        output, sort_keys=False, allow_unicode=True, explicit_start=True
                    )
                )
                directory = os.path.dirname(self.file_path)
                os.makedirs(directory, exist_ok=True)
                descriptor, temporary = tempfile.mkstemp(
                    prefix=".lan_automation_", suffix=".yml", dir=directory
                )
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    stream.write(text)
                os.replace(temporary, self.file_path)
            except (OSError, yaml.YAMLError) as exc:
                self.fail_and_exit(
                    "Unable to write output file {0}: {1}".format(self.file_path, exc)
                )
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
        self.result.update(
            changed=changed,
            msg="LAN automation replacement configuration {0}. Replace the serial placeholders before replay.".format(
                "would be updated"
                if changed and self.module.check_mode
                else "updated" if changed else "is unchanged"
            ),
            file_path=self.file_path,
            generated_config=output,
            response={
                "device_count": len(self.addresses),
                "session_count": len(generated["config"]),
                "source_session_ids": self.source_session_ids,
            },
        )
        return self


def main():
    """Run the read-only capture and local file generation."""
    argument_spec = catalystcenter_argument_spec()
    argument_spec["catalystcenter_port"].update(type="str", default="443")
    argument_spec["catalystcenter_version"]["default"] = "2.3.7.9"
    argument_spec.update(
        catalystcenter_log={"type": "bool", "default": False, "aliases": ["dnac_log"]},
        catalystcenter_log_level={
            "type": "str",
            "default": "WARNING",
            "aliases": ["dnac_log_level"],
        },
        catalystcenter_log_file_path={
            "type": "str",
            "default": "catalystcenter.log",
            "aliases": ["dnac_log_file_path"],
        },
        catalystcenter_log_append={
            "type": "bool",
            "default": True,
            "aliases": ["dnac_log_append"],
        },
        state={"type": "str", "default": "gathered", "choices": ["gathered"]},
        file_path={"type": "path"},
        file_mode={
            "type": "str",
            "default": "overwrite",
            "choices": ["overwrite", "append"],
        },
        isis_domain_pwd={"type": "str", "no_log": True},
        config={
            "type": "dict",
            "required": True,
            "options": {
                "ip_address_list": {
                    "type": "list",
                    "elements": "str",
                    "required": True,
                },
                "site_name_hierarchy": {"type": "str", "required": True},
            },
        },
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    if yaml is None:
        module.fail_json(
            msg="PyYAML is required to generate LAN automation configuration."
        )
    version_parts = module.params["catalystcenter_version"].split(".")
    if len(version_parts) != 4 or not all(part.isdigit() for part in version_parts):
        module.fail_json(
            msg="catalystcenter_version must contain four numeric components, for example 2.3.7.9."
        )
    generator = LanAutomationPlaybookGenerator(module)
    generator.validate_input()
    generator.write_config(generator.generate_config())
    module.exit_json(**generator.result)


if __name__ == "__main__":
    main()
