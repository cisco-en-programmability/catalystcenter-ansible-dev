# Copyright (c) 2024 Cisco and/or its affiliates.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Make coding more python3-ish

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from copy import deepcopy
from unittest.mock import patch

from ansible_collections.cisco.catalystcenter.plugins.modules import (
    inventory_workflow_manager,
)
from .catalystcenter_module import TestCatalystModule, set_module_args, loadPlaybookData


class TestCatalystCenterInventoryWorkflow(TestCatalystModule):

    module = inventory_workflow_manager

    test_data = loadPlaybookData("inventory_workflow_manager")

    playbook_add_device = test_data.get("playbook_add_device")
    playbook_delete_a_device = test_data.get("playbook_delete_a_device")
    playbook_add_existing_devices = test_data.get("playbook_add_existing_devices")
    playbook_add_udf = test_data.get("playbook_add_udf")
    playbook_add_udf_ = test_data.get("playbook_add_udf_")
    playbook_provision_failed_for_site = test_data.get(
        "playbook_provision_failed_for_site"
    )
    playbook_delete_provisioned_device = test_data.get(
        "playbook_delete_provisioned_device"
    )
    playbook_update_interface_details = test_data.get(
        "playbook_update_interface_details"
    )
    playbook_update_role = test_data.get("playbook_update_role")
    playbook_delete_device_udf = test_data.get("playbook_delete_device_udf")
    playbook_missing_mand_params = test_data.get("playbook_missing_mand_params")
    playbook_update_mgmt_ip = test_data.get("playbook_update_mgmt_ip")
    playbook_provision_device = test_data.get("playbook_provision_device")
    playbook_del_provisioned_device_2353 = test_data.get(
        "playbook_del_provisioned_device_2353"
    )
    playbook_prov_device_2353 = test_data.get("playbook_prov_device_2353")
    playbook_already_provisioned = test_data.get("playbook_already_provisioned")
    playbook_delete_provision_device = test_data.get("playbook_delete_provision_device")
    playbook_config_create_device_maintenance_schedule = test_data.get(
        "playbook_config_create_device_maintenance_schedule"
    )
    playbook_config_no_device_maintenance_schedule_update = test_data.get(
        "playbook_config_no_device_maintenance_schedule_update"
    )
    playbook_config_failed_update_device_maintenance_schedule = test_data.get(
        "playbook_config_failed_update_device_maintenance_schedule"
    )
    playbook_config_delete_device_maintenance_schedule = test_data.get(
        "playbook_config_delete_device_maintenance_schedule"
    )
    playbook_config_update_device_maintenance_schedule = test_data.get(
        "playbook_config_update_device_maintenance_schedule"
    )

    def setUp(self):
        super(TestCatalystCenterInventoryWorkflow, self).setUp()

        self.mock_catalystcenter_init = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter.CatalystCenterSDK.__init__"
        )
        self.run_catalystcenter_init = self.mock_catalystcenter_init.start()
        self.run_catalystcenter_init.side_effect = [None]
        self.mock_catalystcenter_exec = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter.CatalystCenterSDK._exec"
        )
        self.run_catalystcenter_exec = self.mock_catalystcenter_exec.start()

    def tearDown(self):
        super(TestCatalystCenterInventoryWorkflow, self).tearDown()
        self.mock_catalystcenter_exec.stop()
        self.mock_catalystcenter_init.stop()

    def load_fixtures(self, response=None, device=""):
        """
        Load fixtures for user.
        """
        if "playbook_add_device" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_add_device"),
                self.test_data.get("get_device_list_add_device_2"),
                self.test_data.get("add_device_add_device"),
                self.test_data.get("TaskDetails_add_device_start"),
                self.test_data.get("TaskDetails_add_device_end"),
                self.test_data.get("get_device_list_add_device_3"),
                self.test_data.get("get_device_list_add_device_5"),
                self.test_data.get("add_device_response"),
            ]

        elif "playbook_delete_a_device" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1"),
                self.test_data.get("get_device_list2"),
                self.test_data.get("get_device_list3"),
                self.test_data.get("device_not_provisioned_to_site"),
                self.test_data.get("get_device_list4"),
                self.test_data.get("deleted_device_by_id1"),
                self.test_data.get("Task_Details1"),
                self.test_data.get("Task_Details2"),
                self.test_data.get("get_device_list5"),
                self.test_data.get("get_device_list6"),
                self.test_data.get("delete_device_response1"),
            ]

        elif "playbook_add_existing_devices" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_existing_devices"),
                self.test_data.get("get_device_list2_existing_devices"),
                self.test_data.get("get_device_list3_existing_devices"),
                self.test_data.get("get_device_list4_existing_devices"),
                self.test_data.get("add_existing_devices_response"),
            ]
        elif "playbook_add_udf_" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_udf_2"),
                self.test_data.get("get_device_list_udf"),
                self.test_data.get("get_all_user_defined_fields_udf"),
                self.test_data.get("get_device_list_udf_1"),
                self.test_data.get("retrieve_network_devices"),
                self.test_data.get("add_user_defined_field_to_device"),
            ]
        elif "playbook_provision_failed_for_site" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_provision_failed_for_site"),
                self.test_data.get("get_device_list2_provision_failed_for_site"),
                self.test_data.get("povisioning_failed_response"),
            ]
        elif "playbook_delete_provisioned_device" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_delete_provisioned_device"),
                self.test_data.get("get_device_list2_delete_provisioned_device"),
                self.test_data.get("get_device_list3_delete_provisioned_device"),
                self.test_data.get("get_provisioned_devices_delete_provisioned_device"),
                self.test_data.get("delete_provisioned_devices"),
                self.test_data.get("Task_Details1_delete_provisioned_device"),
                self.test_data.get("Task_Details2_delete_provisioned_device"),
                self.test_data.get("get_device_list4_delete_provisioned_device"),
                self.test_data.get("get_device_list5_delete_provisioned_device"),
                self.test_data.get("delete_provisioned_response"),
            ]
        elif "playbook_update_interface_details" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_update_interface"),
                self.test_data.get("get_device_list2_update_interface"),
                self.test_data.get("get_device_list3_update_interface"),
                self.test_data.get("get_interface_details1_update_interface"),
                self.test_data.get("get_device_list4_update_interface"),
                self.test_data.get("update_interface_details"),
                self.test_data.get("Task_Details1_update_interface"),
                self.test_data.get("Task_Details2_update_interface"),
                self.test_data.get("get_device_list5_update_interface"),
                self.test_data.get("get_device_list6_update_interface"),
                self.test_data.get("get_device_list7_update_interface"),
                self.test_data.get("get_interface_details2_update_interface"),
                self.test_data.get("update_interface_details_response"),
            ]
        elif "playbook_update_role_border_router" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = self.border_role_api_response
        elif "playbook_update_role_task_failure" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_update_role"),
                self.test_data.get("get_device_list2_update_role"),
                self.test_data.get("get_device_list3_update_role"),
                self.test_data.get("get_device_list4_update_role"),
                self.test_data.get("update_device_role"),
                {
                    "response": {
                        "progress": "Device role update failed",
                        "isError": True,
                        "failureReason": "Catalyst Center rejected the role update",
                    }
                },
            ]
        elif "playbook_update_role_api_failure" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_update_role"),
                self.test_data.get("get_device_list2_update_role"),
                self.test_data.get("get_device_list3_update_role"),
                self.test_data.get("get_device_list4_update_role"),
                Exception(
                    "NCIM90673: Controller rejected the requested role."
                ),
            ]
        elif "playbook_update_role" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_update_role"),
                self.test_data.get("get_device_list2_update_role"),
                self.test_data.get("get_device_list3_update_role"),
                self.test_data.get("get_device_list4_update_role"),
                self.test_data.get("update_device_role"),
                self.test_data.get("Task_Details_update_role"),
                self.test_data.get("get_device_list5_update_role"),
                self.test_data.get("get_device_list6_update_role"),
                self.test_data.get("get_device_list7_update_role"),
                self.test_data.get("update_role_response"),
            ]
        elif "playbook_missing_mand_params" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_missing_mand_params"),
                self.test_data.get("get_device_list2_missing_mand_params"),
                self.test_data.get("response_missing_uname_pwd_in_adding_device"),
            ]
        elif "playbook_delete_device_udf" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_delete_device_udf"),
                self.test_data.get("get_device_list2_delete_device_udf"),
                self.test_data.get("get_device_list3_delete_device_udf"),
                self.test_data.get("get_provisioned_devices_delete_device_udf"),
                self.test_data.get("get_device_list4_delete_device_udf"),
                self.test_data.get("deleted_device_by_id_delete_device_udf"),
                self.test_data.get("Task_Details1_delete_device_udf"),
                self.test_data.get("Task_Details2_delete_device_udf"),
                self.test_data.get("get_device_list5_delete_device_udf"),
                self.test_data.get("get_device_list6_delete_device_udf"),
                self.test_data.get("delete_device_udf_response"),
            ]
        elif "playbook_update_mgmt_ip" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_update_mgmt_ip"),
                self.test_data.get("get_device_list2_update_mgmt_ip"),
                self.test_data.get("get_device_list3_update_mgmt_ip"),
                self.test_data.get("get_device_list4_update_mgmt_ip"),
                self.test_data.get("export_device_list_update_mgmt_ip"),
                self.test_data.get("Task_Details2_update_mgmt_ip"),
                self.test_data.get("download_a_file_by_fileid_update_mgmt_ip"),
                self.test_data.get("sync_devices_update_mgmt_ip"),
                self.test_data.get("Task_Details3_update_mgmt_ip"),
                self.test_data.get("get_device_list5_update_mgmt_ip"),
                self.test_data.get("get_device_list6_update_mgmt_ip"),
                self.test_data.get("get_device_list7_update_mgmt_ip"),
                self.test_data.get("export_device_list2_update_mgmt_ip"),
                self.test_data.get("Task_Details3_update_mgmt_ip"),
                self.test_data.get("Task_Details4_update_mgmt_ip"),
                self.test_data.get("download_a_file_by_fileid2_update_mgmt_ip"),
                self.test_data.get("response_update_mgmt_ipaddress"),
            ]

        elif "playbook_provision_device" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_provision_device"),
                self.test_data.get("get_device_list2_provision_device"),
                self.test_data.get("get_sites"),
                self.test_data.get("device"),
                self.test_data.get("get_sites1_provision_device"),
                self.test_data.get("get_sites_1"),
                self.test_data.get("device2"),
                self.test_data.get("get_sites2_provision_device"),
                self.test_data.get("get_site_assigned_network_device"),
                self.test_data.get("get_sites_3"),
                self.test_data.get("get_device_list3_provision_device"),
                self.test_data.get("assign_network_devices_to_a_site_provision_device"),
                self.test_data.get("Task_Details"),
                self.test_data.get("get_provisioned_wired_device"),
                self.test_data.get("provision_devices"),
                self.test_data.get("Task_Details_1"),
                self.test_data.get("Task_Details_2"),
                self.test_data.get("get_provisioned_wired_devices"),
                self.test_data.get("provisioned_success_response"),
            ]

        elif "playbook_already_provisioned" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_device_list_1"),
                self.test_data.get("get_sites_2"),
                self.test_data.get("get_sites_4"),
                self.test_data.get("get_device_list_2"),
                self.test_data.get("get_sites_5"),
                self.test_data.get("get_sites_6"),
                self.test_data.get("get_device_list_3"),
                self.test_data.get("get_site_assigned_network_device_1"),
                self.test_data.get("get_provisioned_wired_device_1"),
                self.test_data.get("get_provisioned_wired_devices_2"),
                self.test_data.get("already_provisioned_response"),
            ]

        elif "playbook_delete_provision_device" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_10"),
                self.test_data.get("get_device_list_11"),
                self.test_data.get("get_device_list_12"),
                self.test_data.get("get_provisioned_wired_device_10"),
                self.test_data.get("get_device_list_13"),
                self.test_data.get("delete_provisioned_devices_10"),
                self.test_data.get("Task_Details_10"),
                self.test_data.get("Task_Details_11"),
                self.test_data.get("get_device_list_14"),
                self.test_data.get("get_device_list_15"),
                self.test_data.get("delete_response"),
            ]

        elif "playbook_del_provisioned_device_2353" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_del_prov_dev2353"),
                self.test_data.get("get_device_list2_del_prov_dev2353"),
                self.test_data.get("get_provisioned_wired_device_del_prov_dev2353"),
                self.test_data.get("delete_provisioned_wired_device_del_prov_dev2353"),
                self.test_data.get("get_execution_details_device_del_prov_dev2353"),
                self.test_data.get("get_device_list3_del_prov_dev2353"),
                self.test_data.get("get_device_list4_del_prov_dev2353"),
                self.test_data.get("response_del_provisioned_device_2353"),
            ]

        elif "playbook_prov_device_2353" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list1_prov_device_2353"),
                self.test_data.get("get_device_list2_prov_device_2353"),
                self.test_data.get("get_site1_prov_device_2353"),
                self.test_data.get("get_device_list3_prov_device_2353"),
                self.test_data.get("provision_wired_device_prov_device_2353"),
                self.test_data.get("Task_Details_prov_device_2353"),
                self.test_data.get("get_device_list4_prov_device_2353"),
                self.test_data.get("get_device_list5_prov_device_2353"),
                self.test_data.get("get_provisioned_wired_devices_prov_device_2353"),
                self.test_data.get("prov_device_2353_response"),
            ]

        elif "create_device_maintenance_schedule" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_existing_device_details_in_system"),
                self.test_data.get("get_empty_existing_device_detail_in_system"),
                self.test_data.get("get_device_list_for_schedule_device_1"),
                self.test_data.get("get_device_list_for_schedule_device_2"),
                self.test_data.get("get_device_1_id_response"),
                self.test_data.get("get_device_2_id_response"),
                self.test_data.get("get_empty_schedule_details"),
                self.test_data.get("get_empty_schedule_details"),
                self.test_data.get("get_task_id_post_response"),
                self.test_data.get("get_task_status_by_id"),
            ]

        elif "no_device_maintenance_schedule_update" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_existing_device_details_in_system"),
                self.test_data.get("get_empty_existing_device_detail_in_system"),
                self.test_data.get("get_device_list_for_schedule_device_1"),
                self.test_data.get("get_device_list_for_schedule_device_2"),
                self.test_data.get("get_device_1_id_response"),
                self.test_data.get("get_device_2_id_response"),
                self.test_data.get("get_device_maintenance_schedule_details"),
                self.test_data.get("get_device_maintenance_schedule_details"),
                self.test_data.get("get_device_maintenance_schedule_details"),
                self.test_data.get("get_device_maintenance_schedule_details"),
            ]

        elif "failed_update_device_maintenance_schedule" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_existing_device_details_in_system"),
                self.test_data.get("get_empty_existing_device_detail_in_system"),
                self.test_data.get("get_device_list_for_schedule_device_1"),
                self.test_data.get("get_device_list_for_schedule_device_2"),
                self.test_data.get("get_device_1_id_response"),
                self.test_data.get("get_device_2_id_response"),
                self.test_data.get("get_complete_schedule_maintenance_status_details"),
                self.test_data.get("get_complete_schedule_maintenance_status_details"),
                self.test_data.get("get_complete_schedule_maintenance_status_details"),
            ]

        elif "update_device_maintenance_schedule" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_existing_device_details_in_system"),
                self.test_data.get("get_empty_existing_device_detail_in_system"),
                self.test_data.get("get_device_list_for_schedule_device_1"),
                self.test_data.get("get_device_list_for_schedule_device_2"),
                self.test_data.get("get_device_1_id_response"),
                self.test_data.get("get_device_2_id_response"),
                self.test_data.get("get_schedule_maintenance_status_details"),
                self.test_data.get("get_schedule_maintenance_status_details"),
                self.test_data.get("get_schedule_maintenance_status_details"),
                self.test_data.get("get_task_id_post_response"),
                self.test_data.get("get_task_status_by_id"),
                self.test_data.get(
                    "get_scheduled_maintenance_windows_for_network_devices"
                ),
            ]

        elif "delete_device_maintenance_schedule" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_existing_device_details_in_system"),
                self.test_data.get("get_empty_existing_device_detail_in_system"),
                self.test_data.get("get_device_list_for_schedule_device_1"),
                self.test_data.get("get_complete_schedule_maintenance_status_details"),
                self.test_data.get("get_device_list_for_schedule_device_2"),
                self.test_data.get("get_complete_schedule_maintenance_status_details"),
                self.test_data.get("get_task_id_post_response"),
                self.test_data.get("get_task_status_by_id"),
            ]

    def test_inventory_workflow_manager_playbook_add_device(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=True,
                config=self.playbook_add_device,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        print(result)
        self.assertEqual(
            result.get("msg"),
            "device(s) '60.1.1.1', '50.1.1.1' added successfully in Cisco Catalyst Center.",
        )

    def test_inventory_workflow_manager_playbook_add_existing_devices(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=True,
                config=self.playbook_add_existing_devices,
            )
        )
        result = self.execute_module(changed=False, failed=False)
        print(result)
        self.assertEqual(
            result.get("msg"),
            "device(s) '70.2.2.2, 80.2.2.2' already present in the cisco catalyst center",
        )

    def test_inventory_workflow_manager_playbook_add_udf_(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="3.1.3.0",
                state="merged",
                config_verify=False,
                config=self.playbook_add_udf_,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        print(result)
        self.assertEqual(
            result.get("msg"),
            "Global User Defined Field(UDF) named 'To_test_udf' has been successfully added to the device.",
        )

    def test_inventory_workflow_manager_playbook_provision_failed_for_site(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=True,
                config=self.playbook_provision_failed_for_site,
            )
        )
        result = self.execute_module(changed=False, failed=True)
        print(result)
        self.assertEqual(
            result.get("msg"),
            (
                "An exception occurred while retrieving Site details for Site 'Global/Chennai/LTTS/FLOOR1' does not exist "
                "in the Cisco Catalyst Center. Error: object of type 'NoneType' has no len()"
            ),
        )

    def test_inventory_workflow_manager_playbook_update_interface_details(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=True,
                config=self.playbook_update_interface_details,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        print(result)
        self.assertEqual(
            result.get("msg"),
            "Successfully updated the Interface Details for device '204.1.2.4'.",
        )

    def test_inventory_workflow_manager_playbook_update_role(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=True,
                config=self.playbook_update_role,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        print(result)
        self.assertEqual(
            result.get("msg"),
            "Device(s) '['2.2.2.2']' role updated successfully to '['ACCESS']'",
        )
        role_calls = [call for call in self.run_catalystcenter_exec.call_args_list
                      if call.kwargs.get("function") == "update_device_role"]
        self.assertEqual(role_calls[0].kwargs["params"]["role"], "ACCESS")

    def test_inventory_workflow_manager_playbook_update_role_api_failure(self):
        """A rejected role update must fail instead of being logged and ignored."""
        failed_role_config = [dict(self.playbook_update_role[0])]
        failed_role_config[0]["role"] = "BORDER_ROUTER"
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=False,
                config=failed_role_config,
            )
        )

        result = self.execute_module(changed=False, failed=True)

        self.assertIn("Error while updating device role 'BORDER_ROUTER'", result["msg"])
        self.assertIn("NCIM90673", result["msg"])
        role_calls = [call for call in self.run_catalystcenter_exec.call_args_list
                      if call.kwargs.get("function") == "update_device_role"]
        self.assertEqual(role_calls[0].kwargs["params"]["role"], "BORDER ROUTER")

    def border_role_api_response(self, *args, **kwargs):
        """Simulate inventory readback and validate the controller's role contract."""
        function = kwargs["function"]
        params = kwargs.get("params") or {}
        if function == "get_device_list":
            return {"response": [] if params.get("offset") else [deepcopy(self.border_role_device)]}
        if function == "update_device_role":
            self.assertEqual(params, {
                "id": "73f91ecd-d61d-4014-98ce-10c400c35924",
                "role": "BORDER ROUTER",
                "roleSource": "MANUAL",
            })
            self.border_role_device.update(role=params["role"], roleSource=params["roleSource"])
            return deepcopy(self.test_data["update_device_role"])
        if function == "get_task_by_id":
            return {"response": {"isError": False, "progress": "Device role updated successfully"}}
        self.fail("Unexpected API call: {0}".format(function))

    def run_border_role_workflow(self, desired_role, current_role, changed):
        self.border_role_device = {
            "id": "73f91ecd-d61d-4014-98ce-10c400c35924",
            "managementIpAddress": "204.1.2.11",
            "role": current_role,
            "roleSource": "MANUAL",
        }
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_log=False,
            catalystcenter_version="2.3.7.9",
            state="merged",
            config_verify=True,
            config=[{"ip_address_list": ["204.1.2.11"], "role": desired_role}],
        ))
        result = self.execute_module(changed=changed, failed=False)
        role_calls = [
            call for call in self.run_catalystcenter_exec.call_args_list
            if call.kwargs.get("function") == "update_device_role"
        ]
        self.assertEqual(len(role_calls), 1 if changed else 0)
        self.assertEqual(self.border_role_device["role"], "BORDER ROUTER" if changed else current_role)
        return result

    def test_inventory_workflow_manager_playbook_update_role_border_router_underscore(self):
        """Prepare's canonical role must reach the API with the required space."""
        result = self.run_border_role_workflow("BORDER_ROUTER", "ACCESS", changed=True)
        self.assertIn("BORDER_ROUTER", result["msg"])

    def test_inventory_workflow_manager_playbook_update_role_border_router_spaced(self):
        """The controller's spelling must be rejected as playbook input before API calls."""
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            state="merged",
            config=[{"ip_address_list": ["204.1.2.11"], "role": "BORDER ROUTER"}],
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn("BORDER ROUTER : Invalid choice provided", result["msg"])
        self.run_catalystcenter_exec.assert_not_called()

    def test_inventory_workflow_manager_playbook_update_role_border_router_after_ui(self):
        """A role already assigned through the UI must not be written again."""
        self.run_border_role_workflow("BORDER_ROUTER", "BORDER ROUTER", changed=False)

    def test_inventory_workflow_manager_playbook_update_role_border_router_invalid_batch(self):
        """Validate every entry before submitting any role updates."""
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            state="merged",
            config=[
                {"ip_address_list": ["204.1.2.10"], "role": "BORDER_ROUTER"},
                {"ip_address_list": ["204.1.2.11"], "role": "BORDER ROUTER"},
            ],
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn("BORDER ROUTER : Invalid choice provided", result["msg"])
        self.run_catalystcenter_exec.assert_not_called()

    def test_inventory_workflow_manager_playbook_update_role_border_router_legacy_readback(self):
        """The canonical input must also match underscore-form controller readback."""
        self.run_border_role_workflow("BORDER_ROUTER", "BORDER_ROUTER", changed=False)

    def test_inventory_workflow_manager_accepts_documented_role_inputs(self):
        """Public role choices remain valid and unchanged during validation."""
        roles = ["ACCESS", "DISTRIBUTION", "CORE", "BORDER_ROUTER", "UNKNOWN"]
        manager = inventory_workflow_manager.Inventory.__new__(inventory_workflow_manager.Inventory)
        manager.config = [{"role": role} for role in roles]
        manager.result = {}
        with patch.object(manager, "log"):
            manager.validate_input()
        self.assertEqual(manager.status, "success")
        self.assertEqual([entry["role"] for entry in manager.validated_config], roles)

    def test_inventory_workflow_manager_border_role_readback_verification(self):
        """Verification must equate role aliases and still reject actual drift."""
        manager = inventory_workflow_manager.Inventory.__new__(inventory_workflow_manager.Inventory)
        manager.config = [{"role": "BORDER_ROUTER"}]
        with patch.object(manager, "get_device_response") as readback:
            for role, expected in (("BORDER ROUTER", True), ("BORDER_ROUTER", True), ("ACCESS", False), (None, False)):
                with self.subTest(role=role):
                    readback.return_value = {"role": role}
                    self.assertEqual(manager.check_device_role("204.1.2.11"), expected)

    def test_inventory_workflow_manager_playbook_update_role_task_failure(self):
        """An asynchronous role task failure must not be overwritten as success."""
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=False,
                config=self.playbook_update_role,
            )
        )

        result = self.execute_module(changed=False, failed=True)

        self.assertEqual(
            result["msg"],
            "Device role update get failed because of Catalyst Center rejected the role update",
        )

    def test_inventory_workflow_manager_playbook_missing_mand_params(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=True,
                config=self.playbook_missing_mand_params,
            )
        )
        result = self.execute_module(changed=False, failed=True)
        print(result)
        self.assertEqual(
            result.get("msg"),
            "Required parameters ['password', 'username'] for adding devices '['70.2.2.2', '80.2.2.2']' are not present",
        )

    def test_inventory_workflow_manager_playbook_delete_a_device(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="deleted",
                config_verify=True,
                config=self.playbook_delete_a_device,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        print(result)
        self.assertEqual(
            result.get("msg"),
            "provisioned device(s) '12.12.12.12' successfully deleted in Cisco Catalyst Center.",
        )

    def test_inventory_workflow_manager_playbook_provision_device(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=True,
                config=self.playbook_provision_device,
            )
        )
        result = self.execute_module(changed=False, failed=True)
        print(result)
        self.assertEqual(
            result.get("response"), "Wired Device Provisioning failed for all devices"
        )

    def test_inventory_workflow_manager_playbook_already_provisioned(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="merged",
                config_verify=True,
                config=self.playbook_already_provisioned,
            )
        )
        result = self.execute_module(changed=False, failed=True)
        print(result)
        self.assertEqual(
            result.get("response"), "Wired Device Provisioning failed for all devices"
        )

    def test_inventory_workflow_manager_playbook_delete_provision_device(self):
        """
        Test case for add device with full crendentials.

        This test case checks the addition of new network device added with full credentials in Cisco Catalyst Center.
        """
        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.6",
                state="deleted",
                config_verify=True,
                config=self.playbook_delete_provision_device,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        print(result)
        self.assertEqual(
            result.get("response"),
            "provisioned device(s) '204.192.3.40' successfully deleted in Cisco Catalyst Center.",
        )

    # def test_inventory_workflow_manager_playbook_config_create_device_maintenance_schedule(self):
    #     """
    #     Test case for creating the maintenance schedule for the network devices.

    #     This test case checks the creating the maintenance schedule for the network devices in Cisco Catalyst Center.
    #     """

    #     set_module_args(
    #         dict(
    #             catalystcenter_host="1.1.1.1",
    #             catalystcenter_username="dummy",
    #             catalystcenter_password="dummy",
    #             catalystcenter_log=True,
    #             catalystcenter_version="2.3.7.9",
    #             state="merged",
    #             config_verify=False,
    #             config=self.playbook_config_create_device_maintenance_schedule
    #         )
    #     )
    #     result = self.execute_module(changed=True, failed=False)
    #     self.assertIn(
    #         "scheduled successfully",
    #         result.get('msg')
    #     )

    # def test_inventory_workflow_manager_playbook_config_no_device_maintenance_schedule_update(self):
    #     """
    #     Test case for checking the maintenance schedule for the network devices does not need any update.

    #     This test case checks the maintenance schedule for the network devices does not need any update in Cisco Catalyst Center.
    #     """

    #     set_module_args(
    #         dict(
    #             catalystcenter_host="1.1.1.1",
    #             catalystcenter_username="dummy",
    #             catalystcenter_password="dummy",
    #             catalystcenter_log=True,
    #             catalystcenter_version="2.3.7.9",
    #             state="merged",
    #             config_verify=False,
    #             config=self.playbook_config_no_device_maintenance_schedule_update
    #         )
    #     )
    #     result = self.execute_module(changed=False, failed=False)
    #     self.assertIn(
    #         "not required any update",
    #         result.get('msg')
    #     )

    # def test_inventory_workflow_manager_playbook_config_failed_update_device_maintenance_schedule(self):
    #     """
    #     Test case for maintenance schedule for the network devices failure while update it.

    #     This test case checks the maintenance schedule for the network devices failure while update it in Cisco Catalyst Center.
    #     """

    #     set_module_args(
    #         dict(
    #             catalystcenter_host="1.1.1.1",
    #             catalystcenter_username="dummy",
    #             catalystcenter_password="dummy",
    #             catalystcenter_log=True,
    #             catalystcenter_version="2.3.7.9",
    #             state="merged",
    #             config_verify=False,
    #             config=self.playbook_config_failed_update_device_maintenance_schedule
    #         )
    #     )
    #     result = self.execute_module(changed=False, failed=True)
    #     self.assertIn(
    #         "status is neither",
    #         result.get('msg')
    #     )

    # def test_inventory_workflow_manager_playbook_config_update_device_maintenance_schedule(self):
    #     """
    #     Test case for maintenance schedule for the network devices required any update.

    #     This test case checks the maintenance schedule for the network devices required any update in Cisco Catalyst Center.
    #     """

    #     set_module_args(
    #         dict(
    #             catalystcenter_host="1.1.1.1",
    #             catalystcenter_username="dummy",
    #             catalystcenter_password="dummy",
    #             catalystcenter_log=True,
    #             catalystcenter_version="2.3.7.9",
    #             state="merged",
    #             config_verify=False,
    #             config=self.playbook_config_update_device_maintenance_schedule
    #         )
    #     )
    #     result = self.execute_module(changed=True, failed=False)
    #     self.assertIn(
    #         "updated successfully",
    #         result.get('msg')
    #     )

    def test_inventory_workflow_manager_playbook_config_delete_device_maintenance_schedule(
        self,
    ):
        """
        Test case for deletion of maintenance schedule for the network devices.

        This test case checks the deletion of maintenance schedule for the network devices in Cisco Catalyst Center.
        """

        set_module_args(
            dict(
                catalystcenter_host="1.1.1.1",
                catalystcenter_username="dummy",
                catalystcenter_password="dummy",
                catalystcenter_log=True,
                catalystcenter_version="2.3.7.9",
                state="deleted",
                config_verify=False,
                config=self.playbook_config_delete_device_maintenance_schedule,
            )
        )
        result = self.execute_module(changed=True, failed=False)
        self.assertIn("deleted successfully", result.get("msg"))
