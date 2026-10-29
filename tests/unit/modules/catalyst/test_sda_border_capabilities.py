# Copyright (c) 2026 Cisco and/or its affiliates.
# Licensed under the Apache License, Version 2.0.
"""Regress mixed L2/L3 capture, capability-only preparation, and handoff gating."""

from copy import deepcopy
from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.cisco.catalystcenter.plugins.module_utils.sda_border_capabilities import (
    capability_config,
    normalize_border_types,
    required_border_types,
)
from ansible_collections.cisco.catalystcenter.plugins.modules.sda_fabric_devices_playbook_config_generator import (
    SdaFabricDevicesPlaybookGenerator,
)
from ansible_collections.cisco.catalystcenter.plugins.modules.sda_fabric_devices_workflow_manager import (
    FabricDevices,
)


class TestBorderCapabilityIntent(TestCase):
    def setUp(self):
        self.source = {
            "device_ip": "204.1.2.2",
            "device_roles": ["BORDER_NODE"],
            "borders_settings": {
                "layer3_settings": {"local_autonomous_system_number": "65001"},
                "layer2_handoff": [{"interface_name": "GigabitEthernet1/0/10"}],
            },
        }

    def test_legacy_intent_uses_captured_handoffs_without_modifying_manifest(self):
        original = deepcopy(self.source)
        base = deepcopy(self.source)
        del base["borders_settings"]["layer2_handoff"]
        enriched = capability_config(base, self.source)
        self.assertEqual(enriched["borders_settings"]["border_types"], ["LAYER_2", "LAYER_3"])
        self.assertEqual(self.source, original)
        self.assertNotIn("border_types", base["borders_settings"])

    def test_explicit_captured_capabilities_survive_without_handoffs(self):
        del self.source["borders_settings"]["layer2_handoff"]
        self.source["borders_settings"]["border_types"] = ["LAYER_3", "LAYER_2"]
        self.assertEqual(required_border_types(self.source), ["LAYER_2", "LAYER_3"])

    def test_conflicting_explicit_replacement_is_rejected(self):
        target = deepcopy(self.source)
        target["borders_settings"]["border_types"] = ["LAYER_3"]
        with self.assertRaisesRegex(ValueError, "differs"):
            capability_config(target, self.source)

    def test_explicit_types_must_include_handoff_requirements(self):
        self.source["borders_settings"]["border_types"] = ["LAYER_3"]
        with self.assertRaisesRegex(ValueError, "all configured"):
            required_border_types(self.source)

    def test_invalid_types_fail_closed(self):
        for value in (None, [], "LAYER_2", ["UNKNOWN"], ["LAYER_2", "LAYER_2"], [2]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_border_types(value)

    def test_non_border_does_not_gain_border_settings(self):
        config = {"device_roles": ["CONTROL_PLANE_NODE"]}
        self.assertEqual(required_border_types(config), [])
        self.assertEqual(capability_config(config), config)

    def test_generator_preserves_live_types_without_handoffs(self):
        generator = SdaFabricDevicesPlaybookGenerator.__new__(SdaFabricDevicesPlaybookGenerator)
        generator.log = Mock()
        generator.pprint = repr
        raw = {
            "device_ip": "204.1.2.11",
            "device_config": {
                "deviceRoles": ["BORDER_NODE"],
                "borderDeviceSettings": {
                    "borderTypes": ["LAYER_3", "LAYER_2"],
                    "layer3Settings": {"localAutonomousSystemNumber": "65001"},
                },
            },
        }
        result = generator._transform_single_device(raw)
        self.assertEqual(result["borders_settings"]["border_types"], ["LAYER_3", "LAYER_2"])
        self.assertNotIn("layer2_handoff", result["borders_settings"])
        del raw["device_config"]["borderDeviceSettings"]["borderTypes"]
        result = generator._transform_single_device(raw)
        self.assertNotIn("border_types", result["borders_settings"])


class TestBorderCapabilityManager(TestCase):
    def setUp(self):
        self.manager = FabricDevices.__new__(FabricDevices)
        self.manager.log = Mock()
        self.manager.validate_device_roles = Mock()
        self.manager.validate_local_autonomous_system_number = Mock()
        self.manager.status = "success"
        self.manager.max_timeout = 0
        self.manager.params = {"catalystcenter_task_poll_interval": 1}
        self.manager.check_return_status = Mock(side_effect=self.check_status)
        self.current = {
            "networkDeviceId": "new-uuid",
            "fabricId": "fabric-id",
            "deviceRoles": ["BORDER_NODE"],
            "borderDeviceSettings": {
                "borderTypes": ["LAYER_3"],
                "layer3Settings": {
                    "localAutonomousSystemNumber": "65001",
                    "isDefaultExit": True,
                    "importExternalRoutes": True,
                },
            },
        }
        self.manager.have = {"fabric_devices": [{
            "exists": True, "id": "fabric-device-id", "device_details": self.current,
        }]}
        self.config = {
            "device_ip": "204.1.2.11",
            "device_roles": ["BORDER_NODE"],
            "borders_settings": {"border_types": ["LAYER_3", "LAYER_2"]},
        }

    def check_status(self):
        if self.manager.status == "failed":
            raise RuntimeError(self.manager.msg)
        return self.manager

    def build(self):
        return self.manager.get_device_params("fabric-id", "new-uuid", self.config, 0)

    def test_explicit_capability_only_payload_requires_update_and_preserves_l3(self):
        desired = self.build()
        self.assertEqual(desired["borderDeviceSettings"]["borderTypes"], ["LAYER_2", "LAYER_3"])
        self.assertEqual(desired["borderDeviceSettings"]["layer3Settings"], self.current["borderDeviceSettings"]["layer3Settings"])
        self.assertTrue(self.manager.requires_update(self.current, desired, self.manager.get_obj_params("fabricDevices")))
        self.assertNotIn("layer2_handoff", desired)

    def test_module_input_validation_preserves_capability_only_intent(self):
        self.manager.config = [{"fabric_devices": {"fabric_name": "site", "device_config": [self.config]}}]
        self.manager.validate_input()
        self.assertEqual(self.manager.status, "success")
        self.assertEqual(self.manager.validated_config[0]["fabric_devices"]["device_config"][0]["borders_settings"]["border_types"],
                         ["LAYER_3", "LAYER_2"])

    def test_existing_roles_can_be_omitted_for_capability_only_update(self):
        del self.config["device_roles"]
        self.assertEqual(self.build()["borderDeviceSettings"]["borderTypes"], ["LAYER_2", "LAYER_3"])

    def test_legacy_handoffs_add_required_l2_to_existing_l3(self):
        self.config["borders_settings"] = {"layer2_handoff": [{"interface_name": "GigabitEthernet2/0/10"}]}
        self.assertEqual(self.build()["borderDeviceSettings"]["borderTypes"], ["LAYER_2", "LAYER_3"])

    def test_legacy_payload_retains_existing_capabilities(self):
        self.current["borderDeviceSettings"]["borderTypes"] = ["LAYER_3", "LAYER_2"]
        self.config["borders_settings"] = {"layer3_settings": {"local_autonomous_system_number": "65001"}}
        self.assertEqual(self.build()["borderDeviceSettings"]["borderTypes"], ["LAYER_2", "LAYER_3"])
        self.assertFalse(self.manager.requires_update(self.current, self.build(), self.manager.get_obj_params("fabricDevices")))

    def test_explicit_conflicting_handoffs_are_rejected(self):
        self.config["borders_settings"].update(border_types=["LAYER_3"], layer2_handoff=[{"interface_name": "Gi2/0/10"}])
        with self.assertRaisesRegex(RuntimeError, "all configured"):
            self.build()

    def test_l2_only_capability_is_included_in_api_payload(self):
        self.config["borders_settings"] = {"border_types": ["LAYER_2"]}
        self.manager.have["fabric_devices"][0] = {"exists": False, "device_details": None}
        self.assertEqual(self.build()["borderDeviceSettings"], {"borderTypes": ["LAYER_2"]})

    def run_handoffs(self, observed_types, explicit=True, has_handoffs=True):
        desired = self.build()
        self.manager.response = []
        self.manager.result = {}
        self.manager.fabric_devices_obj_params = self.manager.get_obj_params("fabricDevices")
        self.manager.want = {"fabric_devices": [{"device_details": desired}]}
        if has_handoffs:
            self.manager.want["fabric_devices"][0].update({
                "l2_handoff_details": [{"interfaceName": "GigabitEthernet2/0/10"}],
                "ip_l3_handoff_details": [{"interfaceName": "GigabitEthernet2/0/11"}],
                "sda_l3_handoff_details": {"transitId": "sda-transit"},
            })
        observed = deepcopy(self.current)
        observed["borderDeviceSettings"]["borderTypes"] = observed_types
        events = []
        self.manager.bulk_update_fabric_devices = Mock(side_effect=lambda *args: events.append("update") or self.manager)
        self.manager.bulk_add_fabric_devices = Mock(return_value=self.manager)
        self.manager.fabric_device_exists = Mock(side_effect=lambda *args: events.append("readback") or {
            "exists": True, "device_details": observed,
        })
        for method in ("update_l2_handoff", "update_ip_l3_handoff", "update_sda_l3_handoff"):
            setattr(self.manager, method, Mock(side_effect=lambda *args, name=method: events.append(name)))
        config = deepcopy(self.config)
        if not explicit:
            del config["borders_settings"]["border_types"]
        self.manager.update_fabric_devices({"fabric_name": "site", "device_config": [config]})
        return events

    def test_device_update_and_readback_precede_every_handoff(self):
        self.assertEqual(self.run_handoffs(["LAYER_3", "LAYER_2"]), [
            "update", "readback", "update_l2_handoff", "update_sda_l3_handoff", "update_ip_l3_handoff",
        ])

    def test_stale_missing_and_invalid_readback_block_all_handoffs(self):
        for types in (["LAYER_3"], None, [], ["UNKNOWN"]):
            with self.subTest(types=types):
                self.manager.status = "success"
                with self.assertRaises(RuntimeError):
                    self.run_handoffs(types)
                self.manager.update_l2_handoff.assert_not_called()
                self.manager.update_ip_l3_handoff.assert_not_called()
                self.manager.update_sda_l3_handoff.assert_not_called()

    def test_explicit_preparation_requires_readback_even_without_handoffs(self):
        with self.assertRaises(RuntimeError):
            self.run_handoffs(["LAYER_3"], has_handoffs=False)

    def test_legacy_handoff_submission_is_also_guarded(self):
        with self.assertRaises(RuntimeError):
            self.run_handoffs(["LAYER_3"], explicit=False)

    def test_readback_polls_until_types_are_visible(self):
        desired = self.build()
        self.manager.max_timeout = 10
        ready = deepcopy(self.current)
        ready["borderDeviceSettings"]["borderTypes"] = ["LAYER_3", "LAYER_2"]
        self.manager.fabric_device_exists = Mock(side_effect=[
            {"exists": False, "device_details": None},
            {"exists": True, "device_details": self.current},
            {"exists": True, "device_details": ready},
        ])
        with patch("time.sleep"):
            self.manager.wait_for_border_capabilities(desired, "204.1.2.11").check_return_status()
        self.assertEqual(self.manager.fabric_device_exists.call_count, 3)
