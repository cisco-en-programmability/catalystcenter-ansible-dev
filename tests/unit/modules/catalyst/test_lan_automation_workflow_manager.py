# Copyright (c) 2025 Cisco and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Authors:
#   Archit Soni <soni.archit03@gmail.com>
#
# Description:
#   Unit tests for the Ansible module `lan_automation_workflow_manager`.
#   These tests cover various LAN automation operations using mocked Catalyst Center responses.


from __future__ import absolute_import, division, print_function

# Metadata
__metaclass__ = type
__author__ = "Archit Soni"
__email__ = "soni.archit03@gmail.com"
__version__ = "1.0.0"

from unittest.mock import Mock, call, patch
from ansible_collections.cisco.catalystcenter.plugins.modules import (
    lan_automation_workflow_manager,
)
from .catalystcenter_module import TestCatalystModule, set_module_args, loadPlaybookData


class TestCatalystCenterLanAutomationWorkflow(TestCatalystModule):

    module = lan_automation_workflow_manager
    test_data = loadPlaybookData("lan_automation_workflow_manager")

    playbook_config_delete_port_channel_when_it_doesnot_exist_case_1 = test_data.get(
        "delete_port_channel_when_it_doesnot_exist_playbook_case_1"
    )
    playbook_config_create_port_channel_playbook_case_2 = test_data.get(
        "create_port_channel_playbook_case_2"
    )
    playbook_config_create_second_port_channel_playbook_case_3 = test_data.get(
        "create_second_port_channel_playbook_case_3"
    )
    playbook_config_delete_port_channel_negative_playbook_case_4 = test_data.get(
        "delete_port_channel_negative_playbook_case_4"
    )
    playbook_config_delete_second_port_channel_playbook_case_5 = test_data.get(
        "delete_second_port_channel_playbook_case_5"
    )
    playbook_config_add_links_to_first_port_channel_playbook_case_6 = test_data.get(
        "add_links_to_first_port_channel_playbook_case_6"
    )
    playbook_config_remove_link_from_port_channel_playbook_case_7 = test_data.get(
        "remove_link_from_port_channel_playbook_case_7"
    )
    playbook_config_create_port_channel_negative_testcase_playbook_case_8 = (
        test_data.get("create_port_channel_negative_testcase_playbook_case_8")
    )
    playbook_config_update_port_channel_negative_testcase_playbook_case_9 = (
        test_data.get("update_port_channel_negative_testcase_playbook_case_9")
    )
    playbook_config_add_link_to_port_channel_when_the_order_of_source_and_destination_device_is_reversed_case_10 = test_data.get(
        "add_link_to_port_channel_when_the_order_of_source_and_destination_device_is_reversed_case_10"
    )

    def setUp(self):
        super(TestCatalystCenterLanAutomationWorkflow, self).setUp()

        self.mock_catalystcenter_init = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter.CatalystCenterSDK.__init__"
        )
        self.run_catalystcenter_init = self.mock_catalystcenter_init.start()
        self.run_catalystcenter_init.side_effect = [None]
        self.mock_catalystcenter_exec = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter.CatalystCenterSDK._exec"
        )
        self.run_catalystcenter_exec = self.mock_catalystcenter_exec.start()
        self.load_fixtures()

    def tearDown(self):
        super(TestCatalystCenterLanAutomationWorkflow, self).tearDown()
        self.mock_catalystcenter_exec.stop()
        self.mock_catalystcenter_init.stop()

    def load_fixtures(self, response=None, device=""):
        """
        Load fixtures for user.
        """
        if "invalid_delete_config" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                # self.test_data.get(""),
            ]
        elif (
            "test_delete_port_channel_when_it_doesnot_exist_case_1"
            in self._testMethodName
        ):
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_1"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_1"),
                self.test_data.get("get_lan_automation_status_call_1_case_1"),
                self.test_data.get("get_port_channel_call_1_case_1"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_1"),
                self.test_data.get("get_lan_automation_status_call_1_case_1"),
                self.test_data.get("get_port_channel_call_1_case_1"),
            ]
        elif "test_create_port_channel_playbook_case_2" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_2"),
                self.test_data.get("get_device_list_call_2_case_2"),
                self.test_data.get("get_lan_automation_status_call_1_case_2"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_2"),
                self.test_data.get("get_port_channel_call_1_case_2"),
                self.test_data.get(
                    "create_a_new_port_channel_between_devices_call_1_case_2"
                ),
                self.test_data.get("get_tasks_by_id_call_1_case_2"),
                self.test_data.get("get_lan_automation_status_call_1_case_2"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_2"),
                self.test_data.get("get_port_channel_call_2_case_2"),
            ]
        elif "test_create_second_port_channel_playbook_case_3" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_3"),
                self.test_data.get("get_device_list_call_2_case_3"),
                self.test_data.get("get_lan_automation_status_call_1_case_3"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_3"),
                self.test_data.get("get_port_channel_call_1_case_3"),
                self.test_data.get(
                    "create_a_new_port_channel_between_devices_call_1_case_3"
                ),
                self.test_data.get("get_tasks_by_id_call_1_case_3"),
                self.test_data.get("get_lan_automation_status_call_1_case_3"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_3"),
                self.test_data.get("get_port_channel_call_2_case_3"),
            ]
        elif (
            "test_delete_port_channel_negative_playbook_case_4" in self._testMethodName
        ):
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_4"),
            ]
        elif "test_delete_second_port_channel_playbook_case_5" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_5"),
                self.test_data.get("get_device_list_call_2_case_5"),
                self.test_data.get("get_lan_automation_status_call_1_case_5"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_5"),
                self.test_data.get("get_port_channel_call_1_case_5"),
                self.test_data.get("delete_port_channel_call_1_case_5"),
                self.test_data.get("get_tasks_by_id_call_1_case_5"),
                self.test_data.get("get_lan_automation_status_call_1_case_5"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_5"),
                self.test_data.get("get_port_channel_call_2_case_5"),
            ]
        elif (
            "test_add_links_to_first_port_channel_playbook_case_6"
            in self._testMethodName
        ):
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_6"),
                self.test_data.get("get_device_list_call_2_case_6"),
                self.test_data.get("get_lan_automation_status_call_1_case_6"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_6"),
                self.test_data.get("get_port_channel_call_1_case_6"),
                self.test_data.get("get_port_channel_information_by_id_call_1_case_6"),
                self.test_data.get("add_links_to_port_channel_call_1_case_6"),
                self.test_data.get("get_tasks_by_id_call_1_case_6"),
                self.test_data.get("get_lan_automation_status_call_1_case_6"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_6"),
                self.test_data.get("get_port_channel_call_2_case_6"),
            ]
        elif "remove_link_from_port_channel_playbook_case_7" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_7"),
                self.test_data.get("get_device_list_call_2_case_7"),
                self.test_data.get("get_lan_automation_status_call_1_case_7"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_7"),
                self.test_data.get("get_port_channel_call_1_case_7"),
                self.test_data.get("get_port_channel_information_by_id_call_1_case_7"),
                self.test_data.get("remove_a_link_from_port_channel_case_7"),
                self.test_data.get("get_tasks_by_id_call_1_case_7"),
                self.test_data.get("get_lan_automation_status_call_1_case_7"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_7"),
                self.test_data.get("get_port_channel_call_2_case_7"),
            ]
        elif (
            "create_port_channel_negative_testcase_playbook_case_8"
            in self._testMethodName
        ):
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_8"),
                self.test_data.get("get_device_list_call_2_case_8"),
            ]
        elif (
            "update_port_channel_negative_testcase_playbook_case_9"
            in self._testMethodName
        ):
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_9"),
                self.test_data.get("get_device_list_call_2_case_9"),
                self.test_data.get("get_lan_automation_status_call_1_case_9"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_9"),
                self.test_data.get("get_port_channel_call_1_case_9"),
            ]
        elif (
            "add_link_to_port_channel_when_the_order_of_source_and_destination_device_is_reversed_case_10"
            in self._testMethodName
        ):
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_call_1_case_10"),
                self.test_data.get("get_device_list_call_2_case_10"),
                self.test_data.get("get_lan_automation_status_call_1_case_10"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_10"),
                self.test_data.get("get_port_channel_call_1_case_10"),
                self.test_data.get("get_port_channel_information_by_id_call_1_case_10"),
                self.test_data.get("add_a_link_to_port_channel_case_10"),
                self.test_data.get("get_tasks_by_id_call_1_case_10"),
                self.test_data.get("get_lan_automation_status_call_1_case_10"),
                self.test_data.get("get_active_lan_automation_sessions_call_1_case_10"),
                self.test_data.get("get_port_channel_call_2_case_10"),
            ]

    def test_delete_port_channel_when_it_doesnot_exist_case_1(self):
        #  Test Description: Delete port channel when it does not exist between source and destination device.
        #  Expected Result: No change required as port channel does not exist between source and destination
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="deleted",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_delete_port_channel_when_it_doesnot_exist_case_1,
            )
        )
        result = self.execute_module(changed=False, failed=False)
        self.assertEqual(
            result.get("msg"),
            "No port channel found to delete between source device '172.255.0.64' and destination device 'None' with links: null. No update needed.",
        )

    def test_create_port_channel_playbook_case_2(self):
        #  Test Description: Create port channel between source and destination device when no port channel exists before.
        #  Expected Result: Port channel created successfully between source and destination device.
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="merged",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_create_port_channel_playbook_case_2,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        self.assertIn(
            "Port channel created successfully between source device '172.255.0.64' and destination device '172.101.1.1'",
            result.get("msg"),
        )

    def test_create_second_port_channel_playbook_case_3(self):
        # Test Description: Create second port channel between source and destination device when one port channel already exists.
        # Expected Result: Second port channel created successfully between source and destination device.
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="merged",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_create_second_port_channel_playbook_case_3,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        self.assertIn(
            "Port channel created successfully between source device '172.255.0.64' and destination device '172.101.1.1'",
            result.get("msg"),
        )

    def test_delete_port_channel_negative_playbook_case_4(self):
        # Test Description: Negative test case for port channel deletion. Source device is not provided.
        # Expected Result: Fail the module with appropriate error message.
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="deleted",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_delete_port_channel_negative_playbook_case_4,
            )
        )
        result = self.execute_module(changed=False, failed=True)
        self.assertEqual(
            result.get("msg"),
            "The following required parameters are missing or invalid: Configuration 1: Missing source device identifiers "
            "- at least one of 'source_device_management_ip_address', 'source_device_management_mac_address' or "
            "'source_device_management_serial_number' is required",
        )

    def test_delete_second_port_channel_playbook_case_5(self):
        # Test Description: Delete second port channel between source and destination device.
        # Expected Result: Fail the module with appropriate error message.
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="deleted",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_delete_second_port_channel_playbook_case_5,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        self.assertIn(
            "Port channel deleted successfully between source device '172.255.0.64' and destination device '172.101.1.1' with links:",
            result.get("msg"),
        )

    def test_add_links_to_first_port_channel_playbook_case_6(self):
        # Test Description: Add links to the first port channel between source and destination device.
        # Expected Result: Links added successfully to the existing port channel.
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="merged",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_add_links_to_first_port_channel_playbook_case_6,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        self.assertIn(
            "Links added successfully to the port channel between source device '172.255.0.64' and destination device '172.101.1.1'. Added links:",
            result.get("msg"),
        )

    def test_remove_link_from_port_channel_playbook_case_7(self):
        # Test Description: Remove link from port channel between source and destination device.
        # Expected Result: Link removed successfully from the existing port channel.
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="deleted",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_remove_link_from_port_channel_playbook_case_7,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        self.assertIn(
            "Links removed successfully from the port channel between source device '172.255.0.64' and destination device '172.101.1.1'. Removed links:",
            result.get("msg"),
        )

    def test_create_port_channel_negative_testcase_playbook_case_8(self):
        # Test Description: Create port channel between source and destination device without specifying links in merged state, Invalid case.
        # Expected Result: Module should fail with appropriate error message indicating links are required for merged state.
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="merged",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_create_port_channel_negative_testcase_playbook_case_8,
            )
        )
        result = self.execute_module(changed=False, failed=True)
        self.assertIn(
            "Missing links parameter for merged state - at least one link must be specified",
            result.get("msg"),
        )

    def test_update_port_channel_negative_testcase_playbook_case_9(self):
        # Test Description: Update port channel by specifying port_channel_number that does not exist.
        # Expected Result: Module should fail with appropriate error message indicating the port channel
        # number does not exist and suggesting to remove the parameter to create a new port channel.
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="merged",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_update_port_channel_negative_testcase_playbook_case_9,
            )
        )
        result = self.execute_module(changed=False, failed=True)
        self.assertIn(
            "No existing Port Channel configuration found with the provided "
            "port_channel_number: 11. When both port_channel_number and links "
            "are specified, an existing Port Channel is expected for update. "
            "If you want to create a new Port Channel, please remove the "
            "port_channel_number parameter from your playbook configuration "
            "and try again.",
            result.get("msg"),
        )

    def add_link_to_port_channel_when_the_order_of_source_and_destination_device_is_reversed_case_10(
        self,
    ):
        # Test Description: Add link to port channel when the order of source and destination devices
        # is reversed compared to the Catalyst Center configuration. The module should automatically
        # detect the reversed order and swap the interface assignments before calling the API.
        # Expected Result: Module should successfully add links to the port channel by automatically
        # swapping device1Interface and device2Interface to match the Catalyst Center port channel configuration.
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_version="3.1.3.0",
                catalystcenter_log=True,
                state="merged",
                config_verify=True,
                catalystcenter_log_level="DEBUG",
                config=self.playbook_config_add_link_to_port_channel_when_the_order_of_source_and_destination_device_is_reversed_case_10,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        self.assertIn(
            "Links added successfully to the port channel between source device '172.254.0.2' and destination device '172.101.1.1'. Added links:",
            result.get("msg"),
        )

    def _filter_link_delete_updates(self, source_exists, destination_exists):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        workflow.no_link_deleted = []
        link_delete = {
            "sourceDeviceManagementIPAddress": "192.0.2.10",
            "sourceDeviceInterfaceName": "GigabitEthernet1/0/1",
            "destinationDeviceManagementIPAddress": "192.0.2.20",
            "destinationDeviceInterfaceName": "GigabitEthernet1/0/2",
        }

        with patch.object(
            workflow,
            "check_link_details",
            side_effect=[source_exists, destination_exists],
        ) as check_link_details, patch.object(workflow, "log"):
            filtered_updates = workflow.filter_updates({"linkDelete": link_delete})

        self.assertEqual(
            check_link_details.call_args_list,
            [
                call("192.0.2.10", "GigabitEthernet1/0/1"),
                call("192.0.2.20", "GigabitEthernet1/0/2"),
            ],
        )
        return workflow, link_delete, filtered_updates

    def test_filter_updates_submits_active_link_delete(self):
        workflow, link_delete, filtered_updates = self._filter_link_delete_updates(
            True, True
        )

        self.assertEqual(filtered_updates, {"linkDelete": link_delete})
        self.assertEqual(workflow.no_link_deleted, [])

    def test_filter_updates_skips_absent_link_delete(self):
        workflow, link_delete, filtered_updates = self._filter_link_delete_updates(
            False, False
        )

        self.assertEqual(filtered_updates, {})
        self.assertEqual(workflow.no_link_deleted, [link_delete])

    def test_filter_updates_submits_asymmetric_link_delete(self):
        for source_exists, destination_exists in [(True, False), (False, True)]:
            with self.subTest(
                source_exists=source_exists,
                destination_exists=destination_exists,
            ):
                workflow, link_delete, filtered_updates = (
                    self._filter_link_delete_updates(
                        source_exists,
                        destination_exists,
                    )
                )

                self.assertEqual(filtered_updates, {"linkDelete": link_delete})
                self.assertEqual(workflow.no_link_deleted, [])

    def _process_link_deletion(self, source_exists, destination_exists):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        link_delete = {
            "sourceDeviceManagementIPAddress": "192.0.2.10",
            "sourceDeviceInterfaceName": "GigabitEthernet1/0/1",
            "destinationDeviceManagementIPAddress": "192.0.2.20",
            "destinationDeviceInterfaceName": "GigabitEthernet1/0/2",
        }

        with patch.object(
            workflow,
            "check_link_details",
            side_effect=[source_exists, destination_exists],
        ) as check_link_details, patch.object(workflow, "log"), patch.object(
            workflow, "fail_and_exit"
        ) as fail_and_exit:
            workflow.process_link_deletion(link_delete)

        self.assertEqual(
            check_link_details.call_args_list,
            [
                call("192.0.2.10", "GigabitEthernet1/0/1"),
                call("192.0.2.20", "GigabitEthernet1/0/2"),
            ],
        )
        return fail_and_exit

    def test_process_link_deletion_accepts_absent_link(self):
        fail_and_exit = self._process_link_deletion(False, False)

        fail_and_exit.assert_not_called()

    def test_process_link_deletion_fails_when_link_state_remains(self):
        for source_exists, destination_exists in [
            (True, True),
            (True, False),
            (False, True),
        ]:
            with self.subTest(
                source_exists=source_exists,
                destination_exists=destination_exists,
            ):
                fail_and_exit = self._process_link_deletion(
                    source_exists,
                    destination_exists,
                )

                fail_and_exit.assert_called_once_with(
                    "Link deletion verification failed for "
                    "192.0.2.10/GigabitEthernet1/0/1 and "
                    "192.0.2.20/GigabitEthernet1/0/2: link configuration "
                    "remains on at least one endpoint."
                )

    def _filter_link_add_updates(self, source_exists, destination_exists):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        workflow.no_link_added = []
        link_add = {
            "sourceDeviceManagementIPAddress": "192.0.2.10",
            "sourceDeviceInterfaceName": "GigabitEthernet1/0/1",
            "destinationDeviceManagementIPAddress": "192.0.2.20",
            "destinationDeviceInterfaceName": "GigabitEthernet1/0/2",
            "ipPoolName": "LAN_AUTO_P2P",
        }

        with patch.object(
            workflow,
            "check_link_details",
            side_effect=[source_exists, destination_exists],
        ) as check_link_details, patch.object(workflow, "log"):
            filtered_updates = workflow.filter_updates({"linkAdd": link_add})

        self.assertEqual(
            check_link_details.call_args_list,
            [
                call("192.0.2.10", "GigabitEthernet1/0/1"),
                call("192.0.2.20", "GigabitEthernet1/0/2"),
            ],
        )
        return workflow, link_add, filtered_updates

    def test_filter_updates_skips_link_add_only_when_both_endpoints_exist(self):
        for source_exists, destination_exists in [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ]:
            with self.subTest(
                source_exists=source_exists,
                destination_exists=destination_exists,
            ):
                workflow, link_add, filtered_updates = self._filter_link_add_updates(
                    source_exists, destination_exists
                )

                if source_exists and destination_exists:
                    self.assertEqual(filtered_updates, {})
                    self.assertEqual(workflow.no_link_added, [link_add])
                else:
                    self.assertEqual(filtered_updates, {"linkAdd": link_add})
                    self.assertEqual(workflow.no_link_added, [])

    def test_filter_updates_returns_empty_mapping_for_compliant_hostname(self):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        workflow.no_hostname_updated = []
        hostname_update = {
            "deviceManagementIPAddress": "192.0.2.20",
            "newHostName": "SJ-IM",
        }

        with patch.object(
            workflow, "get_hostname_details", return_value="SJ-IM"
        ), patch.object(workflow, "log"):
            filtered_updates = workflow.filter_updates(
                {"hostnameUpdateDevices": [hostname_update]}
            )

        self.assertEqual(filtered_updates, {})
        self.assertEqual(workflow.no_hostname_updated, [hostname_update])

    def _process_link_addition(self, source_exists, destination_exists):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        link_add = {
            "sourceDeviceManagementIPAddress": "192.0.2.10",
            "sourceDeviceInterfaceName": "GigabitEthernet1/0/1",
            "destinationDeviceManagementIPAddress": "192.0.2.20",
            "destinationDeviceInterfaceName": "GigabitEthernet1/0/2",
        }

        with patch.object(
            workflow,
            "check_link_details",
            side_effect=[source_exists, destination_exists],
        ) as check_link_details, patch.object(workflow, "log"), patch.object(
            workflow, "fail_and_exit"
        ) as fail_and_exit:
            workflow.process_link_addition(link_add)

        self.assertEqual(
            check_link_details.call_args_list,
            [
                call("192.0.2.10", "GigabitEthernet1/0/1"),
                call("192.0.2.20", "GigabitEthernet1/0/2"),
            ],
        )
        return fail_and_exit

    def test_process_link_addition_requires_both_endpoints(self):
        for source_exists, destination_exists in [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ]:
            with self.subTest(
                source_exists=source_exists,
                destination_exists=destination_exists,
            ):
                fail_and_exit = self._process_link_addition(
                    source_exists, destination_exists
                )

                if source_exists and destination_exists:
                    fail_and_exit.assert_not_called()
                else:
                    fail_and_exit.assert_called_once_with(
                        "Link addition verification failed for "
                        "192.0.2.10/GigabitEthernet1/0/1 and "
                        "192.0.2.20/GigabitEthernet1/0/2: link configuration "
                        "is missing from at least one endpoint."
                    )

    def test_update_lan_auto_devices_fails_when_task_id_is_missing(self):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        link_add = {"sourceDeviceManagementIPAddress": "192.0.2.10"}

        with patch.object(
            workflow, "call_lan_auto_update_api", return_value=None
        ), patch.object(workflow, "log"), patch.object(
            workflow, "fail_and_exit"
        ) as fail_and_exit:
            result = workflow.update_lan_auto_devices({"linkAdd": link_add})

        self.assertIsNone(result)
        fail_and_exit.assert_called_once_with(
            "Failed to get a task ID for the requested link_add update: "
            "{'sourceDeviceManagementIPAddress': '192.0.2.10'}"
        )

    def test_get_diff_merged_rejects_all_none_task_ids(self):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        workflow.want = {
            "lan_automated_device_update": {
                "linkAdd": {"sourceDeviceManagementIPAddress": "192.0.2.10"}
            }
        }
        workflow.have = {}
        empty_task_ids = {
            "loopback_update": None,
            "hostname_update": None,
            "link_add": None,
            "link_delete": None,
        }

        with patch.object(
            workflow,
            "filter_updates",
            return_value=workflow.want["lan_automated_device_update"],
        ), patch.object(
            workflow, "update_lan_auto_devices", return_value=empty_task_ids
        ) as update_lan_auto_devices, patch.object(
            workflow, "log"
        ), patch.object(
            workflow, "fail_and_exit"
        ) as fail_and_exit:
            update_lan_auto_devices.__name__ = "update_lan_auto_devices"
            workflow.get_diff_merged()

        fail_and_exit.assert_called_once_with(
            "An error occurred while retrieving task_ids for "
            "'update_lan_auto_devices' operation."
        )

    def test_get_update_lan_task_status_fails_on_timeout(self):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        workflow.params = {
            "catalystcenter_api_task_timeout": 5,
            "catalystcenter_task_poll_interval": 30,
        }

        with patch.object(
            workflow,
            "get_task_details",
            return_value={"isError": False, "progress": "In progress"},
        ), patch.object(workflow, "log"), patch.object(
            workflow, "fail_and_exit"
        ) as fail_and_exit, patch.object(
            lan_automation_workflow_manager.time,
            "monotonic",
            side_effect=[0, 0, 0, 5],
        ), patch.object(
            lan_automation_workflow_manager.time, "sleep"
        ) as sleep:
            workflow.get_update_lan_task_status({"link_add": "task-123"})

        sleep.assert_called_once_with(5)
        fail_and_exit.assert_called_once_with(
            "Timed out after 5 seconds while waiting for link_add update task "
            "'task-123' to complete."
        )

    def test_get_device_id_fails_closed_on_api_error(self):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        workflow.catalystcenter_apply = {
            "exec": Mock(side_effect=RuntimeError("lookup failed"))
        }

        with patch.object(workflow, "log"), patch.object(
            workflow, "fail_and_exit"
        ) as fail_and_exit:
            result = workflow.get_device_id("192.0.2.10")

        self.assertIsNone(result)
        fail_and_exit.assert_called_once_with(
            "Unable to verify device 192.0.2.10: failed to retrieve its device "
            "ID: lookup failed"
        )

    def test_check_link_details_allows_known_unconfigured_interface(self):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        workflow.catalystcenter_apply = {
            "exec": Mock(
                return_value={
                    "response": {
                        "id": "interface-123",
                        "ipv4Address": None,
                        "isisSupport": "false",
                        "addresses": [],
                    }
                }
            )
        }

        with patch.object(
            workflow, "get_device_id", return_value="device-123"
        ), patch.object(workflow, "log"), patch.object(
            workflow, "fail_and_exit"
        ) as fail_and_exit:
            result = workflow.check_link_details("192.0.2.10", "GigabitEthernet1/0/1")

        self.assertFalse(result)
        fail_and_exit.assert_not_called()

    def test_check_link_details_fails_closed_on_interface_api_error(self):
        workflow = lan_automation_workflow_manager.LanAutomation.__new__(
            lan_automation_workflow_manager.LanAutomation
        )
        workflow.catalystcenter_apply = {
            "exec": Mock(side_effect=RuntimeError("interface lookup failed"))
        }

        with patch.object(
            workflow, "get_device_id", return_value="device-123"
        ), patch.object(workflow, "log"), patch.object(
            workflow, "fail_and_exit"
        ) as fail_and_exit:
            result = workflow.check_link_details("192.0.2.10", "GigabitEthernet1/0/1")

        self.assertFalse(result)
        fail_and_exit.assert_called_once_with(
            "Unable to verify link details for "
            "192.0.2.10/GigabitEthernet1/0/1: interface lookup failed"
        )
