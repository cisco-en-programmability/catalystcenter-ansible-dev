# Copyright (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Exercise physical replacement capture with mocked read-only SDK calls."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import yaml
from ansible.module_utils import basic
from ansible_collections.cisco.catalystcenter.plugins.modules import (
    lan_automation_playbook_config_generator as generator,
    lan_automation_workflow_manager as workflow,
)


class ModuleExit(Exception):
    """Carry the actual Ansible module result out of main()."""


class ModuleFail(Exception):
    """Carry the actual Ansible module failure out of main()."""


class TestLanAutomationPlaybookGenerator(unittest.TestCase):
    """Verify complete captures, replay compatibility, and failure atomicity."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "capture.yml"
        self.ip = "192.0.2.10"
        self.site = "Global/Region/Building"
        self.sessions = [self.session()]
        self.active_ids = []
        self.devices = {
            self.ip: {
                "id": "device-10",
                "managementIpAddress": self.ip,
                "hostname": "current-access-10",
                "serialNumber": "OLD-SERIAL-10",
            },
            "192.0.2.11": {
                "id": "device-11",
                "managementIpAddress": "192.0.2.11",
                "hostname": "current-access-11",
                "serialNumber": "OLD-SERIAL-11",
            },
        }
        self.assignments = {
            device["id"]: {
                "deviceId": device["id"],
                "siteNameHierarchy": self.site + "/Floor1",
            }
            for device in self.devices.values()
        }
        self.sdk_patch = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter.CatalystCenterSDK"
        )
        self.sdk = self.sdk_patch.start().return_value
        self.addCleanup(self.sdk_patch.stop)
        self.sdk._exec.side_effect = self.api_response
        self.exit_patch = patch.object(basic.AnsibleModule, "exit_json", self.exit_json)
        self.exit_patch.start()
        self.addCleanup(self.exit_patch.stop)
        self.fail_patch = patch.object(basic.AnsibleModule, "fail_json", self.fail_json)
        self.fail_patch.start()
        self.addCleanup(self.fail_patch.stop)

    def session(
        self, session_id="session-1", timestamp="1730000000000", serial="OLD-SERIAL-10"
    ):
        return {
            "id": session_id,
            "creationTime": timestamp,
            "action": "STOP",
            "status": "Completed",
            "discoveredDeviceSiteNameHierarchy": "Global/Region/Building",
            "primaryDeviceManagmentIPAddress": "198.51.100.10",
            "peerDeviceManagmentIPAddress": "198.51.100.11",
            "primaryDeviceInterfaceNames": [
                "GigabitEthernet1/0/1",
                "GigabitEthernet1/0/2",
            ],
            "ipPools": [
                {"ipPoolName": "LAN_AUTO_MAIN", "ipPoolRole": "MAIN_POOL"},
                {"ipPoolName": "LAN_AUTO_P2P", "ipPoolRole": "PHYSICAL_LINK_POOL"},
            ],
            "multicastEnabled": False,
            "redistributeIsisToBgp": True,
            "discoveryLevel": 2,
            "discoveryTimeout": 40,
            "hostNamePrefix": "old-prefix",
            "discoveredDeviceList": [
                {
                    "serialNumber": serial,
                    "name": "historical-name",
                    "state": "Added to inventory",
                    "ipAddressInUseList": ["192.0.2.99", "203.0.113.2", "192.0.2.10"],
                }
            ],
        }

    def api_response(self, family, function, params, op_modifies):
        self.assertFalse(op_modifies)
        if function == "lan_automation_status":
            self.assertEqual(family, "lan_automation")
            offset, limit = params["offset"], params["limit"]
            return {
                "response": copy.deepcopy(
                    self.sessions[offset - 1 : offset - 1 + limit]
                )
            }
        if function == "lan_automation_active_sessions":
            return {
                "response": {
                    "activeSessionIds": self.active_ids,
                    "activeSessions": str(len(self.active_ids)),
                }
            }
        if function == "get_network_device_by_ip":
            self.assertEqual(family, "devices")
            return {
                "response": copy.deepcopy(self.devices.get(params["ip_address"], {}))
            }
        if function == "get_site_assigned_network_device":
            self.assertEqual(family, "site_design")
            return {"response": copy.deepcopy(self.assignments.get(params["id"], {}))}
        self.fail("Unexpected SDK call: {0}.{1}".format(family, function))

    @staticmethod
    def exit_json(*args, **kwargs):
        raise ModuleExit(kwargs)

    @staticmethod
    def fail_json(*args, **kwargs):
        raise ModuleFail(kwargs)

    def run_module(self, fail=None, **overrides):
        args = {
            "catalystcenter_host": "controller.example.test",
            "catalystcenter_username": "admin",
            "catalystcenter_password": "test-password",
            "file_path": str(self.path),
            "config": {"ip_address_list": [self.ip], "site_name_hierarchy": self.site},
        }
        args.update(overrides)
        with patch.object(basic, "_load_params", return_value=copy.deepcopy(args)):
            with self.assertRaises(
                ModuleFail if fail is not None else ModuleExit
            ) as raised:
                generator.main()
        result = raised.exception.args[0]
        if fail is not None:
            self.assertIn(fail, result["msg"])
        return result

    def read_config(self):
        return yaml.safe_load(self.path.read_text())

    def test_capture_preserves_current_identity_and_supported_session_settings(self):
        result = self.run_module()
        self.assertTrue(result["changed"])
        self.assertEqual(result["generated_config"], self.read_config())
        lan = self.read_config()["config"][0]["lan_automation"]
        self.assertEqual(
            lan["discovery_devices"],
            [
                {
                    "device_serial_number": "REPLACE_WITH_SERIAL_FOR_192_0_2_10",
                    "device_host_name": "current-access-10",
                    "device_management_ip_address": self.ip,
                    "device_site_name_hierarchy": self.site + "/Floor1",
                }
            ],
        )
        self.assertEqual(lan["primary_device_management_ip_address"], "198.51.100.10")
        self.assertEqual(lan["peer_device_management_ip_address"], "198.51.100.11")
        self.assertEqual(
            lan["primary_device_interface_names"],
            self.sessions[0]["primaryDeviceInterfaceNames"],
        )
        self.assertEqual(
            lan["ip_pools"],
            [
                {"ip_pool_name": "LAN_AUTO_MAIN", "ip_pool_role": "MAIN_POOL"},
                {"ip_pool_name": "LAN_AUTO_P2P", "ip_pool_role": "PHYSICAL_LINK_POOL"},
            ],
        )
        self.assertIs(lan["multicast_enabled"], False)
        self.assertIs(lan["redistribute_isis_to_bgp"], True)
        self.assertEqual(lan["discovery_level"], 2)
        self.assertEqual(lan["discovery_timeout"], 40)
        self.assertEqual(lan["host_name_prefix"], "old-prefix")
        self.assertIs(lan["launch_and_wait"], True)
        self.assertNotIn("isis_domain_pwd", lan)
        self.assertNotIn("OLD-SERIAL", self.path.read_text())
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_replay_is_accepted_by_workflow_manager(self):
        self.run_module()
        config = self.read_config()["config"]
        config[0]["lan_automation"]["discovery_devices"][0][
            "device_serial_number"
        ] = "NEW-SERIAL-10"
        manager = workflow.LanAutomation(
            SimpleNamespace(
                params={
                    "config": config,
                    "state": "merged",
                    "catalystcenter_version": "2.3.7.9",
                }
            )
        )
        with patch.object(manager, "get_site_details", return_value=True), patch.object(
            manager, "get_ip_details", return_value=True
        ):
            manager.validate_input().check_return_status()
            manager.get_want(manager.validated_config[0]).check_return_status()
        payload = manager.want["lan_automation"]
        self.assertEqual(payload["primaryDeviceManagmentIPAddress"], "198.51.100.10")
        self.assertEqual(
            payload["discoveryDevices"][0]["deviceSerialNumber"], "NEW-SERIAL-10"
        )
        self.assertEqual(
            payload["discoveryDevices"][0]["deviceManagementIPAddress"], self.ip
        )

    def test_paginates_and_chooses_latest_matching_serial(self):
        self.sessions = [
            self.session("unrelated-" + str(i), serial="OTHER") for i in range(10)
        ]
        self.sessions += [
            self.session("older", "900000000000"),
            self.session("newer", "1730000000000"),
        ]
        self.sessions[0] = self.session("reused-ip", "1740000000000", serial="OTHER")
        result = self.run_module()
        self.assertEqual(result["response"]["source_session_ids"], ["newer"])
        pages = [
            c.kwargs["params"]["offset"]
            for c in self.sdk._exec.call_args_list
            if c.kwargs["function"] == "lan_automation_status"
        ]
        self.assertEqual(pages, [1, 11])

    def test_multiple_requested_devices_are_grouped_and_unrequested_ones_excluded(self):
        self.sessions[0]["discoveredDeviceList"] += [
            {"serialNumber": "OLD-SERIAL-11", "state": "Added to inventory"},
            {"serialNumber": "UNREQUESTED", "state": "Added to inventory"},
        ]
        self.run_module(
            config={
                "ip_address_list": ["192.0.2.11", self.ip],
                "site_name_hierarchy": self.site,
            }
        )
        config = self.read_config()["config"]
        self.assertEqual(len(config), 1)
        devices = config[0]["lan_automation"]["discovery_devices"]
        self.assertEqual(
            [d["device_management_ip_address"] for d in devices],
            [self.ip, "192.0.2.11"],
        )
        self.assertEqual(len({d["device_serial_number"] for d in devices}), 2)

    def test_devices_in_distinct_sessions_have_distinct_entries(self):
        self.sessions.append(self.session("second", serial="OLD-SERIAL-11"))
        self.sessions[-1]["primaryDeviceManagmentIPAddress"] = "198.51.100.20"
        result = self.run_module(
            config={
                "ip_address_list": [self.ip, "192.0.2.11"],
                "site_name_hierarchy": self.site,
            }
        )
        self.assertEqual(result["response"]["session_count"], 2)
        self.assertEqual(len(self.read_config()["config"]), 2)

    def test_discovery_devices_evidence_works_without_legacy_list(self):
        self.sessions[0].pop("discoveredDeviceList")
        self.sessions[0]["discoveryDevices"] = [
            {
                "deviceSerialNumber": "OLD-SERIAL-10",
                "deviceHostName": "stale",
                "deviceManagementIPAddress": "192.0.2.99",
                "isDeviceDiscovered": True,
            }
        ]
        self.run_module()
        device = self.read_config()["config"][0]["lan_automation"]["discovery_devices"][
            0
        ]
        self.assertEqual(device["device_host_name"], "current-access-10")
        self.assertEqual(device["device_management_ip_address"], self.ip)

    def test_planned_or_deleted_devices_are_not_discovery_evidence(self):
        self.sessions[0]["discoveredDeviceList"][0]["state"] = "Deleted from inventory"
        self.sessions[0]["discoveryDevices"] = [
            {"deviceSerialNumber": "OLD-SERIAL-10", "isDeviceDiscovered": False}
        ]
        self.run_module(fail="No stopped LAN automation session")
        self.assertFalse(self.path.exists())

    def test_active_source_session_is_rejected_even_if_action_is_stop(self):
        self.active_ids = ["session-1"]
        self.run_module(fail="active or unfinished")
        self.assertFalse(self.path.exists())

    def test_unfinished_source_session_is_rejected(self):
        self.sessions[0]["action"] = "START"
        self.run_module(fail="active or unfinished")

    def test_ambiguous_latest_sessions_are_rejected(self):
        self.sessions.append(self.session("second"))
        self.run_module(fail="ambiguous")

    def test_iso_and_epoch_creation_times_are_compared_chronologically(self):
        self.sessions.append(self.session("iso-newest", "2026-11-18T10:00:00+05:30"))
        result = self.run_module()
        self.assertEqual(result["response"]["source_session_ids"], ["iso-newest"])

    def test_gmt_creation_times_choose_the_newest_session(self):
        self.sessions = [
            self.session("gmt-newest", "17 Nov 2026 21:40:05 GMT"),
            self.session("gmt-older", "30 Oct 2026 23:59:59 GMT"),
        ]
        result = self.run_module(catalystcenter_version="3.1.3.0")
        self.assertEqual(result["response"]["source_session_ids"], ["gmt-newest"])

    def test_gmt_iso_and_epoch_times_use_the_same_timezone_basis(self):
        self.sessions += [
            self.session("gmt-newest", "17 Nov 2026 21:40:05 GMT"),
            self.session("iso-older", "2026-11-18T01:00:00+05:30"),
        ]
        result = self.run_module()
        self.assertEqual(result["response"]["source_session_ids"], ["gmt-newest"])

    def test_unorderable_creation_times_are_rejected(self):
        self.sessions.append(self.session("bad-time", "unknown"))
        self.run_module(fail="invalid creationTime")

    def test_site_matching_respects_path_boundaries(self):
        self.assignments["device-10"]["siteNameHierarchy"] = self.site + "Other"
        self.run_module(fail="not assigned")

    def test_historical_session_must_be_in_current_site_ancestry(self):
        self.sessions[0]["discoveredDeviceSiteNameHierarchy"] = "Global/Unrelated"
        self.run_module(fail="No stopped LAN automation session")

    def test_missing_inventory_identity_is_rejected(self):
        self.devices[self.ip].pop("hostname")
        self.run_module(fail="Incomplete or mismatched inventory")

    def test_missing_site_assignment_is_rejected(self):
        self.assignments["device-10"].pop("siteNameHierarchy")
        self.run_module(fail="not assigned")

    def test_no_serial_match_does_not_fall_back_to_ip(self):
        self.sessions[0]["discoveredDeviceList"][0][
            "serialNumber"
        ] = "OTHER-PHYSICAL-DEVICE"
        self.run_module(fail="No stopped LAN automation session")

    def test_required_seed_and_pool_data_are_validated(self):
        for field, value, message in (
            ("primaryDeviceManagmentIPAddress", "invalid", "Invalid IPv4"),
            ("primaryDeviceInterfaceNames", [], "seed interfaces"),
            ("ipPools", [], "IP pools"),
            ("discoveryLevel", 0, "Invalid discoveryLevel"),
            ("discoveryTimeout", 1, "Invalid discoveryTimeout"),
        ):
            with self.subTest(field=field):
                self.sessions = [self.session()]
                self.sessions[0][field] = value
                self.run_module(fail=message)
                self.assertFalse(self.path.exists())

    def test_missing_optional_settings_and_zero_timeout_are_omitted(self):
        for key in ("peerDeviceManagmentIPAddress", "hostNamePrefix", "discoveryLevel"):
            self.sessions[0].pop(key)
        self.sessions[0]["discoveryTimeout"] = 0
        self.sessions[0]["routingProtocol"] = {}
        self.run_module()
        lan = self.read_config()["config"][0]["lan_automation"]
        for key in (
            "peer_device_management_ip_address",
            "host_name_prefix",
            "discovery_level",
            "discovery_timeout",
        ):
            self.assertNotIn(key, lan)

    def test_optional_isis_password_is_added_and_does_not_cause_rewrites(self):
        first = self.run_module(isis_domain_pwd="test-isis-password")
        second = self.run_module(isis_domain_pwd="test-isis-password")
        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(
            self.read_config()["config"][0]["lan_automation"]["isis_domain_pwd"],
            "test-isis-password",
        )

    def test_check_mode_does_not_create_output_directories(self):
        path = Path(self.directory.name) / "new-dir" / "capture.yml"
        result = self.run_module(_ansible_check_mode=True, file_path=str(path))
        self.assertTrue(result["changed"])
        self.assertFalse(path.parent.exists())

    def test_identical_capture_skips_writing(self):
        self.run_module()
        timestamp = self.path.stat().st_mtime_ns
        result = self.run_module()
        self.assertFalse(result["changed"])
        self.assertEqual(timestamp, self.path.stat().st_mtime_ns)

    def test_append_writes_one_replayable_document_and_is_idempotent(self):
        self.run_module()
        self.sessions = [self.session("second", serial="OLD-SERIAL-11")]
        config = {"ip_address_list": ["192.0.2.11"], "site_name_hierarchy": self.site}
        result = self.run_module(file_mode="append", config=config)
        again = self.run_module(file_mode="append", config=config)
        self.assertTrue(result["changed"])
        self.assertFalse(again["changed"])
        self.assertEqual(len(list(yaml.safe_load_all(self.path.read_text()))), 1)
        self.assertEqual(len(self.read_config()["config"]), 2)

    def test_append_rejects_conflicting_duplicate_ips_without_modifying_file(self):
        self.run_module()
        original = self.path.read_bytes()
        self.devices[self.ip]["hostname"] = "renamed"
        self.run_module(file_mode="append", fail="conflicting settings")
        self.assertEqual(self.path.read_bytes(), original)

    def test_api_failure_keeps_existing_output_intact(self):
        self.path.write_text("original content")
        self.sdk._exec.side_effect = RuntimeError("controller unavailable")
        self.run_module(fail="Unable to retrieve lan_automation_status")
        self.assertEqual(self.path.read_text(), "original content")

    def test_partial_capture_failure_never_writes_output(self):
        self.run_module(
            config={
                "ip_address_list": [self.ip, "192.0.2.99"],
                "site_name_hierarchy": self.site,
            },
            fail="inventory identity",
        )
        self.assertFalse(self.path.exists())

    def test_invalid_filters_fail_before_api_calls(self):
        for addresses, site in (
            ([], self.site),
            (["bad-ip"], self.site),
            ([self.ip, self.ip], self.site),
            ([self.ip], "Building"),
        ):
            with self.subTest(addresses=addresses, site=site):
                self.sdk._exec.reset_mock()
                self.run_module(
                    config={"ip_address_list": addresses, "site_name_hierarchy": site},
                    fail="",
                )
                self.sdk._exec.assert_not_called()

    def test_minimum_and_later_versions(self):
        self.run_module(
            catalystcenter_version="invalid", fail="four numeric components"
        )
        self.run_module(catalystcenter_version="2.3.7.6", fail="2.3.7.9 or later")
        self.sdk._exec.assert_not_called()
        for version in ("2.3.7.9", "3.1.3.0"):
            with self.subTest(version=version):
                self.run_module(catalystcenter_version=version)

    def test_failed_file_replacement_preserves_the_existing_file(self):
        self.path.write_text("original content")
        with patch.object(generator.os, "replace", side_effect=OSError("write failed")):
            self.run_module(fail="Unable to write output file")
        self.assertEqual(self.path.read_text(), "original content")
        self.assertEqual(list(self.path.parent.glob(".lan_automation_*")), [])

    def test_malformed_and_repeated_session_pages_are_rejected(self):
        self.sdk._exec.side_effect = lambda **kwargs: {"response": {}}
        self.run_module(fail="must contain a list")
        self.sessions = [self.session("session-" + str(index)) for index in range(10)]
        self.sdk._exec.side_effect = lambda **kwargs: {"response": self.sessions}
        self.run_module(fail="repeated session ID")
        self.assertFalse(self.path.exists())

    def test_unsupported_routing_cannot_silently_generate_an_isis_session(self):
        for options in ({"routingProtocol": "OSPF"}, {"ipV6Only": True}):
            with self.subTest(options=options):
                self.sessions = [self.session()]
                self.sessions[0].update(options)
                self.run_module(fail="routing options unsupported")
                self.assertFalse(self.path.exists())

    def test_large_legacy_session_is_split_into_replayable_batches(self):
        self.sessions[0]["discoveredDeviceList"] = []
        self.devices, self.assignments = {}, {}
        for index in range(1, 52):
            address, device_id, serial = (
                "192.0.2." + str(index),
                "device-" + str(index),
                "OLD-" + str(index),
            )
            self.devices[address] = {
                "id": device_id,
                "managementIpAddress": address,
                "hostname": "access-" + str(index),
                "serialNumber": serial,
            }
            self.assignments[device_id] = {
                "deviceId": device_id,
                "siteNameHierarchy": self.site,
            }
            self.sessions[0]["discoveredDeviceList"].append(
                {"serialNumber": serial, "state": "Added to inventory"}
            )
        self.run_module(
            config={
                "ip_address_list": list(self.devices),
                "site_name_hierarchy": self.site,
            }
        )
        entries = self.read_config()["config"]
        self.assertEqual(
            [len(entry["lan_automation"]["discovery_devices"]) for entry in entries],
            [50, 1],
        )
        self.assertTrue(
            all(entry["lan_automation"]["launch_and_wait"] for entry in entries)
        )


if __name__ == "__main__":
    unittest.main()
