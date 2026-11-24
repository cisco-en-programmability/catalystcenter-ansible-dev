#  Copyright (c) 2026 Cisco and/or its affiliates.
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
#   Sunil Shatagopa (@shatagopasunil)
#   Madhan Sankaranarayanan (@madhansansel)
#
# Description:
#   Unit tests for the Ansible module `switch_refresh_non_fabric_playbook_config_generator`.
#   These tests cover input validation, source-device resolution, interface-mapping
#   existence checks and the end-to-end deploy-config generation for a non-fabric
#   switch refresh in Cisco Catalyst Center.

from __future__ import absolute_import, division, print_function

__metaclass__ = type
from unittest.mock import patch, mock_open
from ansible_collections.cisco.catalystcenter.plugins.modules import switch_refresh_non_fabric_playbook_config_generator
from .catalystcenter_module import TestCatalystModule, set_module_args, loadPlaybookData


class TestSwitchRefreshNonFabricPlaybookConfigGenerator(TestCatalystModule):
    module = switch_refresh_non_fabric_playbook_config_generator
    test_data = loadPlaybookData("switch_refresh_non_fabric_playbook_config_generator")

    config_happy_no_templates = test_data.get("config_happy_no_templates")
    config_happy_with_template = test_data.get("config_happy_with_template")
    config_device_not_found = test_data.get("config_device_not_found")
    config_interface_mapping_source_not_found = test_data.get("config_interface_mapping_source_not_found")
    config_duplicate_interface_mapping = test_data.get("config_duplicate_interface_mapping")
    config_duplicate_interface_destination = test_data.get("config_duplicate_interface_destination")
    config_interface_collision = test_data.get("config_interface_collision")
    config_duplicate_configs = test_data.get("config_duplicate_configs")
    config_interface_conflict_no_migration = test_data.get("config_interface_conflict_no_migration")
    config_refresh_suffix = test_data.get("config_refresh_suffix")
    config_missing_source_device_ip = test_data.get("config_missing_source_device_ip")
    config_missing_serial = test_data.get("config_missing_serial")
    config_empty = test_data.get("config_empty")
    config_excluded_template = test_data.get("config_excluded_template")
    config_include_by_reference = test_data.get("config_include_by_reference")
    config_interface_mappings_not_list = test_data.get("config_interface_mappings_not_list")
    config_interface_mapping_missing_destination = test_data.get("config_interface_mapping_missing_destination")
    config_exclude_templates_not_list = test_data.get("config_exclude_templates_not_list")
    config_include_templates_missing_project = test_data.get("config_include_templates_missing_project")

    def setUp(self):
        super(TestSwitchRefreshNonFabricPlaybookConfigGenerator, self).setUp()
        self.mock_catalystcenter_init = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter.CatalystCenterSDK.__init__")
        self.run_catalystcenter_init = self.mock_catalystcenter_init.start()
        self.run_catalystcenter_init.side_effect = [None]
        self.mock_catalystcenter_exec = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter.CatalystCenterSDK._exec"
        )
        self.run_catalystcenter_exec = self.mock_catalystcenter_exec.start()
        # The deployed-template lookup (deployedTemplateDetails) goes through a raw REST
        # call (execute_rest_api_call -> custom_caller) because it has no typed SDK
        # wrapper, so it is mocked separately from the typed _exec GETs.
        self.mock_catalystcenter_rest = patch(
            "ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter.CatalystCenterSDK.execute_rest_api_call"
        )
        self.run_catalystcenter_rest = self.mock_catalystcenter_rest.start()
        self.load_fixtures()

    def tearDown(self):
        super(TestSwitchRefreshNonFabricPlaybookConfigGenerator, self).tearDown()
        self.mock_catalystcenter_rest.stop()
        self.mock_catalystcenter_exec.stop()
        self.mock_catalystcenter_init.stop()

    def load_fixtures(self, response=None, device=""):
        """
        Load the ordered Catalyst Center responses for each test scenario.

        The module makes two kinds of call: typed SDK GETs (mocked through ``_exec``, in
        the order the module issues them) and one raw REST GET for the deployed-template
        lookup (``deployedTemplateDetails``, mocked through ``execute_rest_api_call``).
        The typed sequence is: ``get_device_list`` (device resolution); then, only when
        interface migration is requested, ``get_interface_info_by_id``; then, only when
        there are deployed or include templates, ``get_templates_details`` (the catalog);
        then one ``get_template_details`` per ``include_templates`` add-on. Tests that
        fail in input validation or the version gate issue no calls at all.
        """
        # Default: the device has no deployed templates. Flow tests override this below.
        self.run_catalystcenter_rest.return_value = self.test_data.get(
            "get_deployed_empty"
        )

        if "happy_path_no_templates" in self._testMethodName:
            # Device has no deployed templates and no include_templates, so the catalog
            # is never read and no file is written (idempotent no-op).
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
            ]

        elif "happy_path_with_template" in self._testMethodName:
            # One SUCCESS deployed template, recreated from its realized config. The
            # catalog is read once to annotate the template's project.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_templates_details_catalog"),
            ]
            self.run_catalystcenter_rest.return_value = self.test_data.get(
                "get_deployed_one"
            )

        elif "excluded_template" in self._testMethodName:
            # The one deployed template matches exclude_templates, so it is dropped and
            # nothing is written.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_templates_details_catalog"),
            ]
            self.run_catalystcenter_rest.return_value = self.test_data.get(
                "get_deployed_one"
            )

        elif "include_not_applicable" in self._testMethodName:
            # include_templates resolves one add-on, but its details target a different
            # product family, so it is not applicable and nothing is written.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_templates_details_catalog"),
                self.test_data.get("get_template_details_wrong_family"),
            ]

        elif "deployed_template_not_successful" in self._testMethodName:
            # The deployed template's last deploy was FAILURE, so it is left out.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_templates_details_catalog"),
            ]
            self.run_catalystcenter_rest.return_value = self.test_data.get(
                "get_deployed_failure"
            )

        elif "deployed_template_no_realized_config" in self._testMethodName:
            # The deployed template returned no realized configuration, so it is left out.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_templates_details_catalog"),
            ]
            self.run_catalystcenter_rest.return_value = self.test_data.get(
                "get_deployed_no_realized"
            )

        elif "include_by_reference" in self._testMethodName:
            # No deployed templates, but include_templates resolves one applicable add-on
            # with a parameter, deployed by reference.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_templates_details_catalog"),
                self.test_data.get("get_template_details_included"),
            ]

        elif "interface_mapping_source_not_found" in self._testMethodName:
            # Device resolves, then its interface inventory is fetched and the mapped
            # source interface is absent from it (fails before the deployed lookup).
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_interface_info_missing_source"),
            ]

        elif "device_not_found" in self._testMethodName:
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list_empty"),
            ]

        elif "optional_serial_accepted" in self._testMethodName:
            # No destination serial supplied: accepted, and with no deployed templates the
            # run is an idempotent no-op.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
            ]

        elif "interface_collision" in self._testMethodName:
            # Device resolves, its interface inventory contains both mapped interfaces,
            # and two SUCCESS deployed templates collide on the same interface once the
            # rename is applied.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_interface_info_collision"),
                self.test_data.get("get_templates_details_catalog_two"),
            ]
            self.run_catalystcenter_rest.return_value = self.test_data.get(
                "get_deployed_two_collision"
            )

        elif "duplicate_configs_collapsed" in self._testMethodName:
            # Two deployed templates carry identical realized config; the duplicate is
            # collapsed so only one template is deployed.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_templates_details_catalog_two"),
            ]
            self.run_catalystcenter_rest.return_value = self.test_data.get(
                "get_deployed_two_identical"
            )

        elif "conflict_no_migration" in self._testMethodName:
            # Two SUCCESS deployed templates configure the same interface with different
            # settings, but no interface_migration is requested, so the run warns (not
            # fails) and still deploys both.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_templates_details_catalog_two"),
            ]
            self.run_catalystcenter_rest.return_value = self.test_data.get(
                "get_deployed_two_conflict"
            )

        elif "refresh_suffix" in self._testMethodName:
            # The one deployed template is already named '<name>_refresh'; the recreated
            # template keeps that name instead of doubling the suffix.
            self.run_catalystcenter_exec.side_effect = [
                self.test_data.get("get_device_list"),
                self.test_data.get("get_templates_details_catalog_refresh"),
            ]
            self.run_catalystcenter_rest.return_value = self.test_data.get(
                "get_deployed_one_refresh"
            )

        else:
            # Validation and version-gate failures make no API calls.
            self.run_catalystcenter_exec.side_effect = []

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_happy_path_no_templates(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_happy_no_templates
        ))
        result = self.execute_module(changed=False, failed=False)
        self.assertIn("No configuration to generate for device", str(result.get("msg")))
        self.assertEqual(result.get("response").get("templates_to_deploy"), 0)
        self.assertEqual(self.run_catalystcenter_exec.call_count, 1)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_happy_path_with_template(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_happy_with_template
        ))
        result = self.execute_module(changed=True, failed=False)
        self.assertIn("Config generated for device", str(result.get("msg")))
        self.assertEqual(result.get("response").get("templates_to_deploy"), 1)
        self.assertEqual(result.get("response").get("templates_excluded"), 0)
        self.assertEqual(result.get("response").get("template_parameters_to_fill"), 0)
        self.assertEqual(self.run_catalystcenter_exec.call_count, 2)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_excluded_template(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_excluded_template
        ))
        result = self.execute_module(changed=False, failed=False)
        self.assertIn("No configuration to generate for device", str(result.get("msg")))
        self.assertEqual(result.get("response").get("templates_to_deploy"), 0)
        self.assertEqual(result.get("response").get("templates_excluded"), 1)
        # device_list + catalog only; the excluded template is dropped before any
        # get_template_details fetch.
        self.assertEqual(self.run_catalystcenter_exec.call_count, 2)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_include_not_applicable(self, mock_exists, mock_file):
        # An include_templates add-on that resolves from the catalog but targets a
        # different product family than the switch is not applicable and is left out.
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_include_by_reference
        ))
        result = self.execute_module(changed=False, failed=False)
        self.assertIn("No configuration to generate for device", str(result.get("msg")))
        self.assertEqual(result.get("response").get("templates_to_deploy"), 0)
        self.assertEqual(result.get("response").get("templates_excluded"), 0)
        self.assertEqual(self.run_catalystcenter_exec.call_count, 3)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_deployed_template_not_successful(self, mock_exists, mock_file):
        # A deployed template whose last deploy was not SUCCESS (FAILURE) is not recreated.
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_happy_with_template
        ))
        result = self.execute_module(changed=False, failed=False)
        self.assertIn("No configuration to generate for device", str(result.get("msg")))
        self.assertEqual(result.get("response").get("templates_to_deploy"), 0)
        self.assertEqual(result.get("response").get("templates_excluded"), 0)
        self.assertEqual(self.run_catalystcenter_exec.call_count, 2)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_deployed_template_no_realized_config(self, mock_exists, mock_file):
        # A deployed template that returned no realized configuration is left out.
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_happy_with_template
        ))
        result = self.execute_module(changed=False, failed=False)
        self.assertIn("No configuration to generate for device", str(result.get("msg")))
        self.assertEqual(result.get("response").get("templates_to_deploy"), 0)
        self.assertEqual(self.run_catalystcenter_exec.call_count, 2)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_include_by_reference(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_include_by_reference
        ))
        result = self.execute_module(changed=True, failed=False)
        self.assertIn("Config generated for device", str(result.get("msg")))
        self.assertEqual(result.get("response").get("templates_to_deploy"), 1)
        self.assertEqual(result.get("response").get("template_parameters_to_fill"), 1)
        self.assertEqual(result.get("response").get("templates_excluded"), 0)
        self.assertEqual(self.run_catalystcenter_exec.call_count, 3)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_device_not_found(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_device_not_found
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn("was not found in Cisco Catalyst Center", str(result.get("msg")))
        self.assertEqual(self.run_catalystcenter_exec.call_count, 1)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_interface_mapping_source_not_found(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_interface_mapping_source_not_found
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn("were not found on source device", str(result.get("msg")))
        self.assertEqual(self.run_catalystcenter_exec.call_count, 2)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_duplicate_interface_mapping(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_duplicate_interface_mapping
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn("same source interface more than once", str(result.get("msg")))
        self.assertEqual(self.run_catalystcenter_exec.call_count, 0)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_duplicate_interface_destination(self, mock_exists, mock_file):
        # Two different source interfaces mapped to the same destination is rejected in
        # input validation, before any API call.
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_duplicate_interface_destination
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn("same destination interface", str(result.get("msg")))
        self.assertEqual(self.run_catalystcenter_exec.call_count, 0)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_interface_collision(self, mock_exists, mock_file):
        # interface_migration renames Loopback811 onto Loopback812, which another
        # template already configures; the two recreated templates would configure
        # Loopback812 with conflicting settings, so the run fails before writing.
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_interface_collision
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn("conflicting configuration", str(result.get("msg")))
        self.assertIn("Loopback812", str(result.get("msg")))
        self.assertEqual(self.run_catalystcenter_exec.call_count, 3)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_duplicate_configs_collapsed(self, mock_exists, mock_file):
        # Two deployed templates carry identical realized config; the duplicate is
        # collapsed so only one template is deployed.
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_duplicate_configs
        ))
        result = self.execute_module(changed=True, failed=False)
        self.assertEqual(result.get("response").get("templates_to_deploy"), 1)
        self.assertIn("collapsed", str(result.get("msg")))
        self.assertEqual(self.run_catalystcenter_exec.call_count, 2)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_interface_conflict_no_migration(self, mock_exists, mock_file):
        # Two deployed templates configure the same interface with different settings and
        # no interface_migration is requested; the run warns but still deploys both
        # (the end state stays faithful to the source's last-wins order).
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_interface_conflict_no_migration
        ))
        result = self.execute_module(changed=True, failed=False)
        self.assertEqual(result.get("response").get("templates_to_deploy"), 2)
        self.assertIn("Warning", str(result.get("msg")))
        self.assertIn("same interface", str(result.get("msg")))
        self.assertIn("Loopback811", str(result.get("msg")))
        self.assertEqual(self.run_catalystcenter_exec.call_count, 2)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_refresh_suffix_not_doubled(self, mock_exists, mock_file):
        # A source template already named '<name>_refresh' is recreated under the same
        # name, not '<name>_refresh_refresh'.
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_refresh_suffix
        ))
        result = self.execute_module(changed=True, failed=False)
        self.assertEqual(result.get("response").get("templates_to_deploy"), 1)
        handle = mock_file()
        written = "".join(
            call.args[0] for call in handle.write.call_args_list if call.args
        )
        self.assertIn("Loopback_refresh", written)
        self.assertNotIn("Loopback_refresh_refresh", written)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_missing_source_device_ip(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_missing_source_device_ip
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn(
            "Required parameter 'source_device_ip' is missing from config.",
            str(result.get("msg")),
        )

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_optional_serial_accepted(self, mock_exists, mock_file):
        # destination_device_serial_number is optional: omitting it is accepted (not an
        # error), and with no deployed templates the run is an idempotent no-op.
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_missing_serial
        ))
        result = self.execute_module(changed=False, failed=False)
        self.assertIn("No configuration to generate for device", str(result.get("msg")))
        self.assertEqual(result.get("response").get("destination_device_serial_number"), "")
        self.assertEqual(self.run_catalystcenter_exec.call_count, 1)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_empty_config(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_empty
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn(
            "Configuration must be a non-empty dictionary",
            str(result.get("msg")),
        )

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_interface_mappings_not_a_list(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_interface_mappings_not_list
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn(
            "'interface_mappings' must be a list of mappings",
            str(result.get("msg")),
        )
        self.assertEqual(self.run_catalystcenter_exec.call_count, 0)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_interface_mapping_missing_destination(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_interface_mapping_missing_destination
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn(
            "requires a non-empty",
            str(result.get("msg")),
        )
        self.assertIn("destination_interface_name", str(result.get("msg")))
        self.assertEqual(self.run_catalystcenter_exec.call_count, 0)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_invalid_exclude_templates_not_list(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_exclude_templates_not_list
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn(
            "'exclude_templates' must be a list of mappings",
            str(result.get("msg")),
        )
        self.assertEqual(self.run_catalystcenter_exec.call_count, 0)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_invalid_include_templates_missing_project(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.9",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_include_templates_missing_project
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn(
            "requires a non-empty 'project_name'",
            str(result.get("msg")),
        )
        self.assertEqual(self.run_catalystcenter_exec.call_count, 0)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_unsupported_version(self, mock_exists, mock_file):
        mock_exists.return_value = True
        set_module_args(dict(
            catalystcenter_host="1.1.1.1",
            catalystcenter_username="dummy",
            catalystcenter_password="dummy",
            catalystcenter_version="2.3.7.6",
            catalystcenter_log=True,
            state="gathered",
            config=self.config_happy_no_templates
        ))
        result = self.execute_module(changed=False, failed=True)
        self.assertIn(
            "does not support the non-fabric switch",
            str(result.get("msg")),
        )
