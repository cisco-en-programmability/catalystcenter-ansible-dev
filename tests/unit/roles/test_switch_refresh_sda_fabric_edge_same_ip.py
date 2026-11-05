# Copyright (c) 2026 Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Execute the two-phase role against an offline Catalyst Center action backend.

The temporary collection contains the real role and filters, but every Catalyst
Center action is replaced. Builtin Ansible tasks, persistence, conditionals,
templating, and retries still execute through ansible-playbook.
"""

from copy import deepcopy
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
    "inventory_playbook_config_generator", "provision_playbook_config_generator",
    "sda_fabric_devices_playbook_config_generator",
    "sda_host_port_onboarding_playbook_config_generator",
    "sda_host_port_migration_playbook_config_generator", "inventory_workflow_manager",
    "provision_workflow_manager", "sda_fabric_devices_workflow_manager",
    "sda_host_port_onboarding_workflow_manager", "fabric_devices_info_workflow_manager",
    "lan_automation_workflow_manager",
)


BACKEND = r'''
from copy import deepcopy
import json
import os
from pathlib import Path
import yaml


def _ips(args):
    config = args.get("config", [])
    if isinstance(config, dict):
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
            result["catalystcenter_response"] = {"response": [
                {"networkDeviceId": device["id"], "fabricId": "fabric-1", "deviceRoles": state["fabric"][ip]}
                for ip, device in state["devices"].items()
                if ip in state["fabric"] and device["id"] == args.get("networkDeviceId")]}
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
            if module == "inventory_playbook_config_generator":
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
                payload = [deepcopy(state["ports"][ip]) for ip in ips if state["ports"].get(ip)]
            Path(args["file_path"]).write_text(yaml.safe_dump({"config": payload}, sort_keys=False))
            result.update(changed=True, status="success")
        else:
            ips = _ips(args)
            call["targets"] = ips
            failure = state.get("failure", {})
            fail = (failure.get("module") == module and failure.get("state") == args.get("state")
                    and failure.get("remaining", 0) > 0)
            apply_ips = ips[:1] if fail else ips
            if module == "lan_automation_workflow_manager":
                for group in args["config"]:
                    for device in group["lan_automation"]["discovery_devices"]:
                        ip = device["device_management_ip_address"]
                        if ip in apply_ips:
                            state["devices"][ip] = {
                                "managementIpAddress": ip, "id": "new-uuid-" + ip.rsplit(".", 1)[1],
                                "instanceUuid": "new-uuid-" + ip.rsplit(".", 1)[1],
                                "serialNumber": device["device_serial_number"],
                                "hostname": device["device_host_name"], "role": "UNKNOWN",
                                "family": "Switches and Hubs", "collectionStatus": "Managed",
                                "managementState": "Managed", "reachabilityStatus": "Reachable",
                                "inventoryStatusDetail": "<status><general code='SUCCESS'/></status>",
                            }
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
                            else:
                                state["fabric"][ip] = entry["device_roles"]
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
    return {"devices": devices, "ports": ports, "fabric": {ip: ["EDGE_NODE"] for ip in IPS},
            "provisioned": {ip: SITE + "/Floor" + str(index + 1) for index, ip in enumerate(IPS)},
            "calls": []}


class OfflineRole:
    def __init__(self, directory, baseline=None):
        self.directory = directory
        self.state_path = directory / "controller.json"
        self.snapshots = directory / "snapshots"
        self.collection_root = directory / "collections"
        collection = self.collection_root / "ansible_collections" / "cisco" / "catalystcenter"
        collection.mkdir(parents=True)
        shutil.copytree(ROOT / "roles" / ROLE, collection / "roles" / ROLE)
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
                                cwd=str(self.directory), capture_output=True, text=True, timeout=180)
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


def test_capture_passes_complete_batch_and_preserves_original_and_mapped_ports(captured):
    manifest = captured.manifest()
    assert captured.state()["devices"] == {}
    assert len(manifest["old_devices"]) == 2
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
    assert captured.manifest_path.stat().st_mode & 0o777 == 0o600


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
