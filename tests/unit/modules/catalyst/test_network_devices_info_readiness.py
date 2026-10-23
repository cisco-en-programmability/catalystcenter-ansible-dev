# Copyright (c) 2026 Cisco and/or its affiliates.
# Licensed under the Apache License, Version 2.0 (the "License").

"""Exercise readiness timing and results without controller access or real sleeps."""

from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.cisco.catalystcenter.plugins.modules import (
    network_devices_info_workflow_manager as module,
)


class ReadinessFailure(Exception):
    """Represent the module's fail_json exit in a focused method-level test."""


class TestNetworkDevicesInfoReadiness(TestCase):
    def setUp(self):
        self.now = 0
        self.sleeps = []
        monotonic = patch.object(module.time, "monotonic", side_effect=lambda: self.now)
        monotonic.start()
        self.addCleanup(monotonic.stop)
        sleep = patch.object(module.time, "sleep", side_effect=self._sleep)
        sleep.start()
        self.addCleanup(sleep.stop)

    def _sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    @staticmethod
    def _record(ip="204.1.2.5", **updates):
        record = {
            "managementIpAddress": ip,
            "instanceUuid": "uuid-" + ip,
            "id": "uuid-" + ip,
            "collectionStatus": "Managed",
            "managementState": "Managed",
            "hostname": "border.example.test",
            "serialNumber": "SERIAL-1",
            "macAddress": "00:11:22:33:44:55",
        }
        record.update(updates)
        return record

    @staticmethod
    def _config(**updates):
        config = {
            "device_identifier": [{"ip_address": ["204.1.2.5"]}],
            "requested_info": ["device_info"],
        }
        config.update(updates)
        return config

    def _probe(self, config, snapshots):
        probe = module.NetworkDevicesInfo.__new__(module.NetworkDevicesInfo)
        probe.config = [{"network_devices": [deepcopy(config)]}]
        probe.result = {}
        probe.total_response = []
        probe.status = "success"
        probe.log = Mock()

        def check_return_status():
            if probe.status == "failed":
                raise ReadinessFailure(probe.result)
            return probe

        probe.check_return_status = check_return_status
        snapshots = list(snapshots)
        current = []

        def lookup(_config):
            nonlocal current
            if len(snapshots) > 1:
                current = snapshots.pop(0)
            else:
                current = snapshots[0]
            return {
                record["managementIpAddress"]: record["instanceUuid"]
                for record in current
            }

        def execute(**kwargs):
            return {
                "response": [
                    record
                    for record in current
                    if record["instanceUuid"] == kwargs["params"]["id"]
                ]
            }

        probe.filter_network_devices = Mock(side_effect=lookup)
        probe.catalystcenter = SimpleNamespace(_exec=Mock(side_effect=execute))
        return probe

    def test_optional_fields_preserve_lookup_defaults(self):
        for fields, timeout in (
            ({}, 120),
            ({"collectionStatus": "Managed"}, 1200),
            ({"managementState": "Managed"}, 1200),
            ({"collectionStatus": "Managed", "timeout": 45}, 45),
            ({"timeout": 75}, 75),
        ):
            with self.subTest(fields=fields):
                probe = self._probe(self._config(**fields), [[]])
                probe.validate_input()
                normalized = probe.validated_config[0]["network_devices"][0]
                self.assertEqual(normalized["timeout"], timeout)
                probe.get_want(probe.validated_config[0])

    def test_invalid_readiness_inputs_fail_validation(self):
        for fields in (
            {"collectionStatus": ""},
            {"managementState": " "},
            {"collectionStatus": None},
            {"managementState": 3},
            {"collectionStatus": "Managed", "timeout": 0},
            {"managementState": "Managed", "timeout": -1},
        ):
            with self.subTest(fields=fields):
                probe = self._probe(self._config(**fields), [[]])
                with self.assertRaises(ReadinessFailure):
                    probe.validate_input()

    def test_disabled_mode_returns_incomplete_record_without_polling(self):
        record = self._record(
            collectionStatus="In Progress", managementState="Never Managed"
        )
        probe = self._probe(self._config(), [[record]])
        probe.wait_for_device_readiness = Mock()
        probe.get_diff_gathered(probe.config[0])
        probe.wait_for_device_readiness.assert_not_called()
        self.assertEqual(probe.result["status"], "success")
        self.assertEqual(
            probe.result["response"][1][0]["device_info"][0]["device_details"], [record]
        )
        self.assertEqual(self.sleeps, [])

    def test_disabled_mode_preserves_no_matching_devices_success(self):
        probe = self._probe(self._config(), [[]])
        probe.get_diff_gathered(probe.config[0])
        self.assertEqual(probe.result["status"], "success")
        self.assertIn("No network devices found", probe.result["response"][0])
        self.assertEqual(self.sleeps, [])

    def test_only_supplied_readiness_field_is_checked(self):
        for field, other in (
            ("collectionStatus", "managementState"),
            ("managementState", "collectionStatus"),
        ):
            with self.subTest(field=field):
                config = self._config(**{field: " managed "})
                record = self._record(**{other: "Not Ready"})
                probe = self._probe(config, [[record]])
                probe.get_diff_gathered(probe.config[0])
                self.assertEqual(probe.result["status"], "success")
                self.assertEqual(self.sleeps, [])

    def test_both_fields_must_match_in_the_same_poll(self):
        probe = self._probe(
            self._config(collectionStatus="Managed", managementState="Managed"),
            [
                [self._record(collectionStatus="In Progress")],
                [self._record(managementState="Never Managed")],
                [self._record()],
            ],
        )
        probe.get_diff_gathered(probe.config[0])
        self.assertEqual(self.sleeps, [10, 10])
        returned = probe.result["response"][1][0]["device_info"][0]["device_details"][0]
        self.assertEqual(returned["collectionStatus"], "Managed")
        self.assertEqual(returned["managementState"], "Managed")
        # One detail retrieval per poll: the successful snapshot is reused.
        self.assertEqual(probe.catalystcenter._exec.call_count, 3)

    def test_readiness_uses_existing_identifier_filtering_without_nested_waits(self):
        probe = self._probe(
            self._config(
                collectionStatus="Managed", managementState="Managed", timeout=30
            ),
            [[]],
        )
        probe.filter_network_devices = (
            module.NetworkDevicesInfo.filter_network_devices.__get__(probe)
        )

        def execute(**_kwargs):
            return {
                "response": [
                    self._record(
                        collectionStatus="In Progress" if self.now < 10 else "Managed"
                    )
                ]
            }

        probe.catalystcenter._exec.side_effect = execute
        probe.validate_input()
        probe.get_want(probe.validated_config[0])
        probe.get_diff_gathered(probe.validated_config[0])
        self.assertEqual(probe.result["status"], "success")
        self.assertEqual(self.sleeps, [10])
        self.assertEqual(probe.catalystcenter._exec.call_count, 6)

    def test_default_readiness_timeout_is_1200_seconds(self):
        probe = self._probe(
            self._config(collectionStatus="Managed"),
            [[self._record(collectionStatus="In Progress")]],
        )
        with self.assertRaises(ReadinessFailure):
            probe.get_diff_gathered(probe.config[0])
        self.assertEqual(self.now, 1200)
        self.assertEqual(self.sleeps, [10] * 120)
        self.assertIn("1200 seconds", probe.result["msg"])

    def test_missing_target_messages_are_not_retained_after_readiness_succeeds(self):
        probe = self._probe(self._config(managementState="Managed", timeout=30), [[]])
        probe.filter_network_devices = (
            module.NetworkDevicesInfo.filter_network_devices.__get__(probe)
        )

        def execute(**_kwargs):
            return {"response": [] if self.now < 10 else [self._record()]}

        probe.catalystcenter._exec.side_effect = execute
        probe.get_diff_gathered(probe.config[0])
        self.assertEqual(probe.result["status"], "success")
        self.assertEqual(len(probe.result["response"]), 2)
        self.assertTrue(
            probe.result["response"][0].startswith("The network devices filtered")
        )
        self.assertEqual([delay for delay in self.sleeps if delay], [10])

    def test_timeout_lists_each_ip_and_only_its_failed_fields(self):
        probe = self._probe(
            self._config(
                collectionStatus="Managed",
                managementState="Managed",
                timeout=25,
                interval=1,
                retries=50,
                device_identifier=[{"ip_address": ["204.1.2.5", "204.1.2.6"]}],
            ),
            [
                [
                    self._record(collectionStatus="In Progress"),
                    self._record("204.1.2.6", managementState="Never Managed"),
                ]
            ],
        )
        with self.assertRaises(ReadinessFailure):
            probe.get_diff_gathered(probe.config[0])
        self.assertEqual(self.sleeps, [10, 10, 5])
        failures = probe.result["response"]["readiness_failures"]
        self.assertEqual(
            [entry["device_ip"] for entry in failures], ["204.1.2.5", "204.1.2.6"]
        )
        self.assertEqual(set(failures[0]["failed_fields"]), {"collectionStatus"})
        self.assertEqual(set(failures[1]["failed_fields"]), {"managementState"})
        self.assertIn("In Progress", probe.result["msg"])
        self.assertIn("Never Managed", probe.result["msg"])
        query = probe.filter_network_devices.call_args.args[0]
        self.assertEqual(
            (query["timeout"], query["retries"], query["interval"]), (0, 1, 0)
        )
        self.assertNotIn("collectionStatus", query)

    def test_missing_requested_ip_cannot_be_hidden_by_ready_subset(self):
        probe = self._probe(
            self._config(
                collectionStatus="Managed",
                timeout=10,
                device_identifier=[{"ip_address": ["204.1.2.5", "204.1.2.6"]}],
            ),
            [[self._record()]],
        )
        with self.assertRaises(ReadinessFailure):
            probe.get_diff_gathered(probe.config[0])
        failures = probe.result["response"]["readiness_failures"]
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["device_ip"], "204.1.2.6")
        self.assertIsNone(failures[0]["failed_fields"]["collectionStatus"]["actual"])

    def test_initially_missing_device_can_appear_before_timeout(self):
        probe = self._probe(
            self._config(managementState="Managed", timeout=20),
            [[], [self._record()]],
        )
        probe.get_diff_gathered(probe.config[0])
        self.assertEqual(probe.result["status"], "success")
        self.assertEqual(self.sleeps, [10])

    def test_previously_selected_device_cannot_disappear(self):
        probe = self._probe(
            self._config(
                collectionStatus="Managed",
                timeout=10,
                device_identifier=[],
                device_family="Switches and Hubs",
            ),
            [
                [
                    self._record(),
                    self._record("204.1.2.6", collectionStatus="In Progress"),
                ],
                [self._record()],
            ],
        )
        with self.assertRaises(ReadinessFailure):
            probe.get_diff_gathered(probe.config[0])
        self.assertEqual(
            probe.result["response"]["readiness_failures"][0]["device_ip"], "204.1.2.6"
        )

    def test_unresolved_hostname_is_reported_on_timeout(self):
        probe = self._probe(
            self._config(
                managementState="Managed",
                timeout=10,
                device_identifier=[{"hostname": ["missing.example.test"]}],
            ),
            [[]],
        )
        with self.assertRaises(ReadinessFailure):
            probe.get_diff_gathered(probe.config[0])
        failure = probe.result["response"]["readiness_failures"][0]
        self.assertEqual(failure["identifier"], {"hostname": "missing.example.test"})
        self.assertEqual(set(failure["failed_fields"]), {"managementState"})

    def test_serial_member_and_mac_identifiers_are_supported(self):
        for identifier in (
            {"serial_number": ["SERIAL-2"]},
            {"mac_address": ["0011.2233.4455"]},
        ):
            with self.subTest(identifier=identifier):
                probe = self._probe(
                    self._config(
                        collectionStatus="Managed", device_identifier=[identifier]
                    ),
                    [[self._record(serialNumber="SERIAL-1, SERIAL-2")]],
                )
                probe.get_diff_gathered(probe.config[0])
                self.assertEqual(probe.result["status"], "success")

    def test_detail_error_is_not_accepted_as_ready(self):
        probe = self._probe(
            self._config(collectionStatus="Managed", timeout=10),
            [[self._record()]],
        )
        probe.catalystcenter._exec.side_effect = RuntimeError("temporary API failure")
        with self.assertRaises(ReadinessFailure):
            probe.get_diff_gathered(probe.config[0])
        self.assertIsNone(
            probe.result["response"]["readiness_failures"][0]["failed_fields"][
                "collectionStatus"
            ]["actual"]
        )

    def test_interface_only_request_still_checks_readiness(self):
        probe = self._probe(
            self._config(collectionStatus="Managed", requested_info=["interface_info"]),
            [[self._record(collectionStatus="In Progress")], [self._record()]],
        )
        probe.get_interface_info = Mock(return_value=[{"interface_info": []}])
        probe.get_diff_gathered(probe.config[0])
        self.assertEqual(self.sleeps, [10])
        probe.get_interface_info.assert_called_once()
        self.assertEqual(probe.result["response"][1], [{"interface_info": []}])

    def test_later_entry_failure_is_not_overwritten_by_earlier_success(self):
        config = self._config(collectionStatus="Managed", timeout=10)
        probe = self._probe(
            config, [[self._record()], [self._record(collectionStatus="In Progress")]]
        )
        probe.config[0]["network_devices"].append(deepcopy(config))
        with self.assertRaises(ReadinessFailure):
            probe.get_diff_gathered(probe.config[0])
        self.assertEqual(probe.result["status"], "failed")
