# Copyright (c) 2026 Cisco and/or its affiliates.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import os
import tempfile
from unittest.mock import call, patch

import yaml

from ansible_collections.cisco.catalystcenter.plugins.modules import (
    topology_info_workflow_manager,
)

from .catalystcenter_module import (
    TestCatalystModule,
    loadPlaybookData,
    set_module_args,
)


class TestCatalystCenterTopologyInfoWorkflowManager(TestCatalystModule):
    """Unit tests for topology_info_workflow_manager."""

    module = topology_info_workflow_manager
    test_data = loadPlaybookData("topology_info_workflow_manager")

    def setUp(self):
        super(TestCatalystCenterTopologyInfoWorkflowManager, self).setUp()

        self.mock_catalystcenter_init = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils."
            "catalystcenter.CatalystCenterSDK.__init__"
        )
        self.run_catalystcenter_init = self.mock_catalystcenter_init.start()
        self.run_catalystcenter_init.return_value = None

        self.mock_catalystcenter_exec = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils."
            "catalystcenter.CatalystCenterSDK._exec"
        )
        self.run_catalystcenter_exec = self.mock_catalystcenter_exec.start()

    def tearDown(self):
        self.mock_catalystcenter_exec.stop()
        self.mock_catalystcenter_init.stop()
        super(TestCatalystCenterTopologyInfoWorkflowManager, self).tearDown()

    def load_fixtures(self, response=None, device=""):
        """Load ordered SDK responses for the current test."""

        if "gathers_all_requested_topologies" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data["site_topology"],
                self.test_data["layer_2_vlan_10"],
                self.test_data["layer_2_vlan_20"],
                self.test_data["layer_3_ospf"],
                self.test_data["layer_3_isis"],
                self.test_data["physical_topology"],
                self.test_data["network_health"],
                self.test_data["vlan_details"],
            ]
        elif "preserves_empty_api_response" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data["empty_site_topology"]
            ]
        elif "writes_json_only_when_output_is_requested" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data["site_topology"]
            ]
        elif "writes_yaml_with_default_format" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data["site_topology"]
            ]
        elif "appends_topology_snapshots" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data["site_topology"],
                self.test_data["vlan_details"],
            ]
        elif "skips_file_when_output_path_is_missing" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data["site_topology"]
            ]
        elif "reports_api_failure" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = RuntimeError(
                "topology service unavailable"
            )

    def _set_module_args(self, config, check_mode=False):
        """Set common workflow arguments for one module execution."""

        args = {
            "catalystcenter_host": "192.0.2.1",
            "catalystcenter_username": "admin",
            "catalystcenter_password": "password",
            "catalystcenter_verify": False,
            "catalystcenter_version": "2.3.7.9",
            "state": "gathered",
            "config": config,
        }
        if check_mode:
            args["_ansible_check_mode"] = True
        set_module_args(args)

    def test_gathers_all_requested_topologies_without_writing_a_file(self):
        """Gather all six categories, deduplicate selectors, and return raw envelopes."""

        self._set_module_args(self.test_data["playbook_all_topologies"])

        with patch.object(
            topology_info_workflow_manager.TopologyInfo,
            "write_topology_info_to_file",
        ) as writer:
            result = self.execute_module(changed=False, failed=False)

        expected_snapshot = {
            "site_topology": self.test_data["site_topology"],
            "layer_2_topology": {
                "Vlan10": self.test_data["layer_2_vlan_10"],
                "Vlan20": self.test_data["layer_2_vlan_20"],
            },
            "layer_3_topology": {
                "OSPF": self.test_data["layer_3_ospf"],
                "ISIS": self.test_data["layer_3_isis"],
            },
            "physical_topology": self.test_data["physical_topology"],
            "network_health": self.test_data["network_health"],
            "vlan_details": self.test_data["vlan_details"],
        }

        self.assertEqual(result["response"], [expected_snapshot])
        self.assertEqual(result["output_files"], [])
        writer.assert_not_called()
        self.assertEqual(
            self.run_catalystcenter_exec.call_args_list,
            [
                call(
                    family="topology",
                    function="get_site_topology",
                    params=None,
                    op_modifies=False,
                ),
                call(
                    family="topology",
                    function="get_topology_details",
                    params={"vlan_id": "Vlan10"},
                    op_modifies=False,
                ),
                call(
                    family="topology",
                    function="get_topology_details",
                    params={"vlan_id": "Vlan20"},
                    op_modifies=False,
                ),
                call(
                    family="topology",
                    function="get_l3_topology_details",
                    params={"topology_type": "OSPF"},
                    op_modifies=False,
                ),
                call(
                    family="topology",
                    function="get_l3_topology_details",
                    params={"topology_type": "ISIS"},
                    op_modifies=False,
                ),
                call(
                    family="topology",
                    function="get_physical_topology",
                    params={"node_type": "device"},
                    op_modifies=False,
                ),
                call(
                    family="topology",
                    function="get_overall_network_health",
                    params={"timestamp": 0},
                    op_modifies=False,
                ),
                call(
                    family="topology",
                    function="get_vlan_details",
                    params=None,
                    op_modifies=False,
                ),
            ],
        )

    def test_preserves_empty_api_response(self):
        """Legitimate empty topology results must not be collapsed to None."""

        self._set_module_args(
            [{"requested_info": ["site_topology"]}]
        )
        result = self.execute_module(changed=False, failed=False)

        self.assertEqual(
            result["response"],
            [{"site_topology": self.test_data["empty_site_topology"]}],
        )

    def test_writes_json_only_when_output_is_requested(self):
        """A valid output_file_info writes and still returns the gathered data."""

        with tempfile.TemporaryDirectory() as output_directory:
            base_path = os.path.join(output_directory, "topology_snapshot")
            self._set_module_args(
                [
                    {
                        "requested_info": ["site_topology"],
                        "output_file_info": {
                            "file_path": base_path,
                            "file_format": "json",
                            "file_mode": "w",
                            "timestamp": False,
                        },
                    }
                ]
            )

            result = self.execute_module(changed=False, failed=False)
            output_path = base_path + ".json"

            self.assertEqual(result["output_files"], [output_path])
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "r", encoding="utf-8") as output_file:
                written_data = json.load(output_file)

        self.assertEqual(
            written_data,
            {"site_topology": self.test_data["site_topology"]},
        )
        self.assertEqual(
            result["response"],
            [{"site_topology": self.test_data["site_topology"]}],
        )

    def test_writes_yaml_with_default_format(self):
        """YAML, overwrite mode, and no timestamp are the file defaults."""

        with tempfile.TemporaryDirectory() as output_directory:
            base_path = os.path.join(output_directory, "topology_snapshot")
            self._set_module_args(
                [
                    {
                        "requested_info": ["site_topology"],
                        "output_file_info": {"file_path": base_path},
                    }
                ]
            )

            result = self.execute_module(changed=False, failed=False)
            output_path = base_path + ".yaml"
            with open(output_path, "r", encoding="utf-8") as output_file:
                written_data = yaml.safe_load(output_file)

        self.assertEqual(result["output_files"], [output_path])
        self.assertEqual(
            written_data,
            {"site_topology": self.test_data["site_topology"]},
        )

    def test_appends_topology_snapshots(self):
        """Append mode retains an existing snapshot and adds the next one."""

        with tempfile.TemporaryDirectory() as output_directory:
            base_path = os.path.join(output_directory, "topology_history")
            self._set_module_args(
                [
                    {
                        "requested_info": ["site_topology"],
                        "output_file_info": {
                            "file_path": base_path,
                            "file_format": "json",
                            "file_mode": "a",
                        },
                    },
                    {
                        "requested_info": ["vlan_details"],
                        "output_file_info": {
                            "file_path": base_path,
                            "file_format": "json",
                            "file_mode": "a",
                        },
                    },
                ]
            )

            result = self.execute_module(changed=False, failed=False)
            output_path = base_path + ".json"
            with open(output_path, "r", encoding="utf-8") as output_file:
                written_data = json.load(output_file)

        expected_snapshots = [
            {"site_topology": self.test_data["site_topology"]},
            {"vlan_details": self.test_data["vlan_details"]},
        ]
        self.assertEqual(result["response"], expected_snapshots)
        self.assertEqual(written_data, expected_snapshots)
        self.assertEqual(result["output_files"], [output_path, output_path])

    def test_supports_check_mode(self):
        """Check mode gathers data but does not write a requested output file."""

        self.run_catalystcenter_exec.side_effect = [
            self.test_data["site_topology"]
        ]
        config = [
            {
                "requested_info": ["site_topology"],
                "output_file_info": {
                    "file_path": "/tmp/topology_check_mode",
                    "file_format": "json",
                },
            }
        ]
        self._set_module_args(config, check_mode=True)

        with patch.object(
            topology_info_workflow_manager.TopologyInfo,
            "write_topology_info_to_file",
        ) as writer:
            result = self.execute_module(changed=False, failed=False)

        self.assertEqual(
            result["response"],
            [{"site_topology": self.test_data["site_topology"]}],
        )
        self.assertEqual(result["output_files"], [])
        writer.assert_not_called()

    def test_rejects_layer_2_without_vlan_ids(self):
        """Layer 2 topology cannot be queried without at least one VLAN name."""

        self._set_module_args(
            [{"requested_info": ["layer_2_topology"]}]
        )
        result = self.execute_module(changed=False, failed=True)

        self.assertIn("'vlan_ids' is required", result["msg"])
        self.run_catalystcenter_exec.assert_not_called()

    def test_rejects_layer_3_without_topology_types(self):
        """Layer 3 topology cannot be queried without at least one type."""

        self._set_module_args(
            [{"requested_info": ["layer_3_topology"]}]
        )
        result = self.execute_module(changed=False, failed=True)

        self.assertIn("'topology_types' is required", result["msg"])
        self.run_catalystcenter_exec.assert_not_called()

    def test_rejects_unknown_requested_info(self):
        """Only documented topology categories are accepted."""

        self._set_module_args(
            [{"requested_info": ["unknown_topology"]}]
        )
        result = self.execute_module(changed=False, failed=True)

        self.assertIn("Invalid requested_info value", result["msg"])

    def test_skips_file_when_output_path_is_missing(self):
        """Missing file_path matches other info managers and skips export."""

        self._set_module_args(
            [
                {
                    "requested_info": ["site_topology"],
                    "output_file_info": {"file_format": "json"},
                }
            ]
        )
        with patch.object(
            topology_info_workflow_manager.TopologyInfo,
            "write_topology_info_to_file",
        ) as writer:
            result = self.execute_module(changed=False, failed=False)

        self.assertEqual(
            result["response"],
            [{"site_topology": self.test_data["site_topology"]}],
        )
        self.assertEqual(result["output_files"], [])
        writer.assert_not_called()

    def test_rejects_relative_output_file_path(self):
        """Relative output paths are ambiguous for transferred Ansible modules."""

        self._set_module_args(
            [
                {
                    "requested_info": ["site_topology"],
                    "output_file_info": {
                        "file_path": "topology_snapshot",
                        "file_format": "json",
                    },
                }
            ]
        )
        result = self.execute_module(changed=False, failed=True)

        self.assertIn("must be an absolute path", result["msg"])

    def test_rejects_invalid_output_format_and_mode(self):
        """File format and mode values are validated before API calls."""

        invalid_configs = [
            {
                "requested_info": ["site_topology"],
                "output_file_info": {
                    "file_path": "/tmp/topology",
                    "file_format": "xml",
                },
            },
            {
                "requested_info": ["site_topology"],
                "output_file_info": {
                    "file_path": "/tmp/topology",
                    "file_format": "json",
                    "file_mode": ["append"],
                },
            },
        ]

        for config in invalid_configs:
            with self.subTest(config=config):
                self._set_module_args([config])
                result = self.execute_module(changed=False, failed=True)
                self.assertIn("output_file_info.file_", result["msg"])

    def test_reports_api_failure(self):
        """SDK failures fail the task without reporting a change."""

        self._set_module_args(
            [{"requested_info": ["site_topology"]}]
        )
        result = self.execute_module(changed=False, failed=True)

        self.assertIn("topology service unavailable", result["msg"])


if __name__ == "__main__":
    import unittest

    unittest.main()
