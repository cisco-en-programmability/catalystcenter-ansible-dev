# -*- coding: utf-8 -*-
# Copyright (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Common template primitives shared across Cisco Catalyst Center template modules."""
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
import time
import re
from ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter import (
    validate_list_of_dicts,
    get_dict_result,
    catalystcenter_compare_equality,
    validate_str
)
from ansible_collections.cisco.catalystcenter.plugins.module_utils.network_profiles import (
    NetworkProfileFunctions,
)


class TemplateCommon(NetworkProfileFunctions):
    """Common template primitives shared by template workflow modules."""

    def __init__(self, module):
        super().__init__(module)
        self.have_project = {}
        self.have_template = {}
        self.supported_states = ["merged", "deleted"]
        self.accepted_languages = ["JINJA", "VELOCITY"]
        self.export_template = []
        self.max_timeout = self.params.get('catalystcenter_api_task_timeout')
        self.template_created, self.no_update_template, self.template_updated = [], [], []
        self.project_created, self.template_committed = [], []
        self.profile_assigned, self.no_profile_assigned, self.profile_exists = [], [], []
        self.profile_detached, self.profile_not_detached, self.profile_already_detached = [], [], []
        # Global set to track processed profile assignments across all config iterations
        # Format: set of tuples (template_name, project_name, profile_name)
        self.processed_profile_assignments = set()
        self.result['response'] = [
            {"configurationTemplate": {"response": {}, "msg": {}}},
            {"export": {"response": {}}},
            {"import": {"response": {}}},
        ]

    def validate_input(self):
        """
        Validate the fields provided in the playbook.
        Checks the configuration provided in the playbook against a predefined specification
        to ensure it adheres to the expected structure and data types.
        Parameters:
            self: The instance of the class containing the 'config' attribute to be validated.
        Returns:
            The method returns an instance of the class with updated attributes:
                - self.msg: A message describing the validation result.
                - self.status: The status of the validation (either 'success' or 'failed').
                - self.validated_config: If successful, a validated version of 'config' parameter.
        Example:
            To use this method, create an instance of the class and call 'validate_input' on it.
            If the validation succeeds, 'self.status' will be 'success' and 'self.validated_config'
            will contain the validated configuration. If it fails, 'self.status' will be 'failed',
            'self.msg' will describe the validation issues.

        """

        if not self.config:
            self.msg = "config not available in playbook for validattion"
            self.status = "success"
            return self

        temp_spec = {
            "configuration_templates": {
                "type": "dict",
                "tags": {"type": "list"},
                "author": {"type": "str"},
                "composite": {"type": "bool"},
                "containing_templates": {"type": "list"},
                "custom_params_order": {"type": "bool"},
                "template_description": {"type": "str"},
                "device_types": {
                    "type": "list",
                    "elements": "dict",
                    "product_family": {"type": "str"},
                    "product_series": {"type": "str"},
                    "product_type": {"type": "str"},
                },
                "failure_policy": {"type": "str"},
                "id": {"type": "str"},
                "language": {"type": "str"},
                "name": {"type": "str"},
                "project_name": {"type": "str"},
                "project_description": {"type": "str"},
                "profile_names": {"type": "list", "elements": "str"},
                "software_type": {"type": "str"},
                "software_version": {"type": "str"},
                "template_content": {"type": "str"},
                "template_content_file_path": {"type": "str"},
                "validate_jinja2_syntax": {"type": "bool", "default": False},
                "template_params": {"type": "list"},
                "template_name": {"type": "str"},
                "new_template_name": {"type": "str"},
                "version": {"type": "str"},
            },
            "deploy_template": {
                "type": "dict",
                "project_name": {"type": "str"},
                "template_name": {"type": "str"},
                "force_push": {"type": "bool"},
                "is_composite": {"type": "bool"},
                "member_template_deployment_info": {
                    "type": "list",
                    "elements": "dict",
                    "template_name": {"type": "str"},
                    "project_name": {"type": "str"},
                    "force_push_template": {"type": "bool", "default": True},
                    "copy_config": {"type": "bool", "default": True},
                    "template_parameters": {
                        "type": "list",
                        "elements": "dict",
                        "param_name": {"type": "str"},
                        "param_value": {"type": "str"},
                    },
                },
                "copy_config": {"type": "bool", "default": True},
                "template_parameters": {
                    "type": "list",
                    "elements": "dict",
                    "param_name": {"type": "str"},
                    "param_value": {"type": "str"},
                },
                "resource_parameters": {
                    "type": "list",
                    "elements": "dict",
                    "resource_type": {"type": "str"},
                    "resource_scope": {"type": "str"},
                    "resource_value": {"type": "str"},
                },
                "device_details": {
                    "type": "dict",
                    "device_ips": {"type": "list", "elements": "str"},
                    "device_hostnames": {"type": "list", "elements": "str"},
                    "serial_numbers": {"type": "list", "elements": "str"},
                    "mac_addresses": {"type": "list", "elements": "str"},
                },
                "site_provisioning_details": {
                    "type": "list",
                    "elements": "dict",
                    "site_name": {"type": "str"},
                    "device_family": {"type": "str"},
                    "device_role": {"type": "str"},
                    "device_tag": {"type": "str"},
                },
            },
            "export": {
                "type": "dict",
                "project": {"type": "list", "elements": "str"},
                "template": {
                    "type": "list",
                    "elements": "dict",
                    "project_name": {"type": "str"},
                    "template_name": {"type": "str"},
                },
            },
            "import": {
                "type": "dict",
                "project": {
                    "type": "dict",
                    "project_file": {"type": "str"},
                    "do_version": {"type": "str", "default": "False"},
                },
                "template": {
                    "type": "dict",
                    "do_version": {"type": "str", "default": "False"},
                    "template_file": {"type": "str"},
                    "payload": {
                        "type": "list",
                        "elements": "dict",
                        "tags": {"type": "list"},
                        "author": {"type": "str"},
                        "composite": {"type": "bool"},
                        "containing_templates": {"type": "list"},
                        "custom_params_order": {"type": "bool"},
                        "template_description": {"type": "str"},
                        "device_types": {
                            "type": "list",
                            "elements": "dict",
                            "product_family": {"type": "str"},
                            "product_series": {"type": "str"},
                            "product_type": {"type": "str"},
                        },
                        'failure_policy': {'type': 'str'},
                        'id': {'type': 'str'},
                        'language': {'type': 'str'},
                        'name': {'type': 'str'},
                        'project_name': {'type': 'str'},
                        'project_description': {'type': 'str'},
                        'software_type': {'type': 'str'},
                        'software_version': {'type': 'str'},
                        'template_content': {'type': 'str'},
                        'template_params': {'type': 'list'},
                        'template_name': {'type': 'str'},
                        'version': {'type': 'str'}
                    }
                }
            },
            "projects": {
                "type": "list",
                "elements": "dict",
                "options": {
                    "name": {"type": "str", "required": True},
                    "new_name": {"type": "str"},
                    "description": {"type": "str"}
                }
            }
        }

        # Validate template params
        self.config = self.camel_to_snake_case(self.config)

        valid_temp, invalid_params = validate_list_of_dicts(
            self.config, temp_spec
        )

        if invalid_params:
            self.msg = "Invalid parameters in playbook: {0}".format(
                "\n".join(invalid_params)
            )
            self.status = "failed"
            return self

        self.input_data_validation(valid_temp).check_return_status()

        self.validated_config = valid_temp
        self.log(
            "Successfully validated playbook config params: {0}".format(self.pprint(valid_temp)),
            "INFO",
        )
        self.msg = "Successfully validated input"
        self.status = "success"
        return self

    def input_data_validation(self, config):
        """
        Validates the input configuration structure for template workflow operations in Cisco Catalyst Center.

        Args:
            self (object): Instance of the class interacting with Cisco Catalyst Center.
            config (list[dict]): List of dictionaries containing project definitions data.

        Returns:
            object: Returns self if validation passes; otherwise, logs an error and exits the module.

        Description:
            This method performs structural and type validation on the 'projects' list within the config.
            It checks for the presence and string type of required fields like 'name', and optionally
            validates fields such as 'new_name' and 'description'.

            If the module state is set to 'deleted', only minimal validation is performed.
            If any validation errors are detected, the method logs an error and terminates the module run.
        """

        self.log("Starting input data validation.", "INFO")
        errormsg = []
        param_spec_str = dict(type="str")

        projects = config[0].get("projects")
        if projects and isinstance(projects, list):
            for each_project in projects:
                project_name = each_project.get("name")
                if project_name and isinstance(project_name, str):
                    validate_str(project_name, param_spec_str, "name", errormsg)
                else:
                    errormsg.append("Missing or invalid 'name' field in project.")

                if self.payload.get("state") == "deleted":
                    continue

                project_new_name = each_project.get("new_name")
                if project_new_name and isinstance(project_new_name, str):
                    validate_str(project_new_name, param_spec_str, "new_name", errormsg)

                description = each_project.get("description")
                if description and isinstance(description, str):
                    validate_str(description, param_spec_str, "description", errormsg)

        self.log("Initiating profile assignment validation for CLI templates", "DEBUG")
        configuration_templates = config[0].get("configuration_templates")
        if configuration_templates and isinstance(configuration_templates, dict):
            profile_names = configuration_templates.get("profile_names")
            ccc_version = self.get_ccc_version()
            self.log("Processing profile assignment configuration - profiles: {0}".format(
                profile_names), "DEBUG")

            if profile_names and isinstance(profile_names, list):
                if self.compare_catalystcenter_versions(ccc_version, "3.1.3.0") < 0:
                    msg = (
                        "Profile assignment feature is not supported in Cisco Catalyst Center version '{0}'. "
                        "Supported versions start from '3.1.3.0' onwards. Current configuration includes "
                        "profiles: {1}".format(ccc_version, bool(profile_names))
                    )
                    errormsg.append(msg)
                else:
                    self.log("Validating profiles configuration for template profile assignment", "DEBUG")
                    for each_profile in profile_names:
                        if each_profile and isinstance(each_profile, str):
                            validate_str(each_profile, param_spec_str, "profile_names", errormsg)

        if errormsg:
            msg = "Invalid parameters in playbook config: '{0}' ".format(errormsg)
            self.log(msg, "ERROR")
            self.fail_and_exit(msg)

        msg = "Successfully validated config params: {0}".format(str(config))
        self.log(msg, "INFO")
        return self

    def get_project_params(self, params):
        """
        Store project parameters from the playbook for template processing in Cisco Catalyst Center.

        Parameters:
            params (dict) - Playbook details containing Project information.

        Returns:
            project_params (dict) - Organized Project parameters.
        """

        project_params = {
            "name": params.get("project_name"),
            "description": params.get("project_description"),
        }
        return project_params

    def get_tags(self, _tags):
        """
        Store tags from the playbook for template processing in Cisco Catalyst Center.
        Check using check_return_status()

        Parameters:
            tags (dict) - Tags details containing Template information.

        Returns:
            tags (dict) - Organized tags parameters.
        """

        self.log(
            "Starting template tag configuration processing for Cisco Catalyst Center operations",
            "INFO"
        )

        if _tags is None:
            self.log(
                "No tag configuration provided - returning None for template processing",
                "DEBUG"
            )
            return None

        tags = []

        for index, tag_item in enumerate(_tags):
            self.log(
                "Processing tag configuration at index {0}: {1}".format(index, tag_item),
                "DEBUG"
            )

            tags.append({})
            tag_id = tag_item.get("id")
            if tag_id is not None:
                tags[index].update({"id": tag_id})
                self.log(
                    "Tag at index {0} includes ID: {1}".format(index, tag_id),
                    "DEBUG"
                )

            # Process required tag name field
            tag_name = tag_item.get("name")
            if tag_name is not None:
                tags[index].update({"name": tag_name})
                self.log(
                    "Tag at index {0} configured with name: {1}".format(index, tag_name),
                    "DEBUG"
                )
            else:
                error_msg = "Tag name is required but not provided for tag at index {0}".format(index)
                self.log(error_msg, "ERROR")
                self.msg = error_msg
                self.status = "failed"
                return self.check_return_status()

            self.log(
                "Successfully processed tag configuration at index {0}".format(index),
                "DEBUG"
            )

        self.log(
            "Template tag configuration processing completed successfully - processed {0} tags".format(
                len(tags)
            ),
            "INFO"
        )
        return tags

    def get_device_types(self, device_types):
        """
        Store device types parameters from the playbook for template processing in Cisco Catalyst Center.
        Check using check_return_status()

        Parameters:
            device_types (dict) - Device types details containing Template information.

        Returns:
            deviceTypes (dict) - Organized device types parameters.
        """

        if device_types is None:
            self.msg = "The parameter 'device_types' is required but not provided."
            self.status = "failed"
            return self.check_return_status()

        deviceTypes = []
        i = 0
        for item in device_types:
            deviceTypes.append({})
            product_family = item.get("product_family")
            if product_family is not None:
                deviceTypes[i].update({"productFamily": product_family})
            else:
                self.msg = "The parameter 'product_family' is required for 'device_types' but not provided."
                self.status = "failed"
                return self.check_return_status()

            product_families_list = [
                "Cisco Cloud Services Platform",
                "Cisco Interfaces and Modules",
                "Content Networking",
                "Network Management",
                "NFV-ThirdParty Devices",
                "NFVIS",
                "Routers",
                "Security and VPN",
                "Storage Networking",
                "Switches and Hubs",
                "Voice and Telephony",
                "Wireless Controller",
            ]
            if product_family not in product_families_list:
                self.msg = (
                    "The 'product_family should be in the following list {0}.".format(
                        product_families_list
                    )
                )
                self.status = "failed"
                return self.check_return_status()

            product_series = item.get("product_series")
            if product_series is not None:
                deviceTypes[i].update({"productSeries": product_series})
            product_type = item.get("product_type")
            if product_type is not None:
                deviceTypes[i].update({"productType": product_type})
            i = i + 1

        return deviceTypes

    def get_template_info(self, template_params):
        """
        Store template params from the playbook for template processing in Cisco Catalyst Center.
        Check using check_return_status()

        Parameters:
            template_params (dict) - Playbook details containing template params information.

        Returns:
            templateParams (dict) - Organized template params parameters.
        """

        if template_params is None:
            return None

        templateParams = []
        i = 0
        self.log("Template params details: {0}".format(template_params), "DEBUG")
        for item in template_params:
            self.log("Template params items: {0}".format(item), "DEBUG")
            templateParams.append({})
            binding = item.get("binding")
            if binding is not None:
                templateParams[i].update({"binding": binding})

            custom_order = item.get("custom_order")
            if custom_order is not None:
                templateParams[i].update({"customOrder": custom_order})

            default_value = item.get("default_value")
            if default_value is not None:
                templateParams[i].update({"defaultValue": default_value})

            description = item.get("description")
            if description is not None:
                templateParams[i].update({"description": description})

            display_name = item.get("display_name")
            if display_name is not None:
                templateParams[i].update({"displayName": display_name})

            group = item.get("group")
            if group is not None:
                templateParams[i].update({"group": group})

            id = item.get("id")
            if id is not None:
                templateParams[i].update({"id": id})

            instruction_text = item.get("instruction_text")
            if instruction_text is not None:
                templateParams[i].update({"instructionText": instruction_text})

            key = item.get("key")
            if key is not None:
                templateParams[i].update({"key": key})

            not_param = item.get("not_param")
            if not_param is not None:
                templateParams[i].update({"notParam": not_param})

            order = item.get("order")
            if order is not None:
                templateParams[i].update({"order": order})

            param_array = item.get("param_array")
            if param_array is not None:
                templateParams[i].update({"paramArray": param_array})

            provider = item.get("provider")
            if provider is not None:
                templateParams[i].update({"provider": provider})

            parameter_name = item.get("parameter_name")
            if parameter_name is not None:
                templateParams[i].update({"parameterName": parameter_name})
            else:
                self.msg = "The parameter 'parameter_name' is required for 'template_params' but not provided."
                self.status = "failed"
                return self.check_return_status()

            data_type = item.get("data_type")
            datatypes = [
                "STRING",
                "INTEGER",
                "IPADDRESS",
                "MACADDRESS",
                "SECTIONDIVIDER",
            ]
            if data_type is not None:
                templateParams[i].update({"dataType": data_type})
            else:
                self.msg = "dataType is required for the template_params."
                self.status = "failed"
                return self.check_return_status()
            if data_type not in datatypes:
                self.msg = "data_type under template_params should be in " + str(
                    datatypes
                )
                self.status = "failed"
                return self.check_return_status()

            required = item.get("required")
            if required is not None:
                templateParams[i].update({"required": required})

            range = item.get("range")
            self.log("Template params range list: {0}".format(range), "DEBUG")
            if range is not None:
                templateParams[i].update({"range": []})
                _range = templateParams[i].get("range")
                self.log("Template params range: {0}".format(_range), "DEBUG")
                j = 0
                for value in range:
                    _range.append({})
                    id = value.get("id")
                    if id is not None:
                        _range[j].update({"id": id})
                    max_value = value.get("max_value")
                    if max_value is not None:
                        _range[j].update({"maxValue": max_value})
                    else:
                        self.msg = "The parameter 'max_value' is required for range under 'template_params' but not provided."
                        self.status = "failed"
                        return self.check_return_status()
                    min_value = value.get("min_value")
                    if min_value is not None:
                        _range[j].update({"minValue": min_value})
                    else:
                        self.msg = "The parameter 'min_value' is required for range under 'template_params' but not provided."
                        self.status = "failed"
                        return self.check_return_status()
                    j = j + 1

            self.log("Template params details: {0}".format(templateParams), "DEBUG")
            selection = item.get("selection")
            self.log("Template params selection: {0}".format(selection), "DEBUG")
            if selection is not None:
                templateParams[i].update({"selection": {}})
                _selection = templateParams[i].get("selection")
                id = selection.get("id")
                if id is not None:
                    _selection.update({"id": id})
                default_selected_values = selection.get("default_selected_values")
                if default_selected_values is not None:
                    _selection.update(
                        {"defaultSelectedValues": default_selected_values}
                    )
                selection_values = selection.get("selection_values")
                if selection_values is not None:
                    _selection.update({"selectionValues": selection_values})
                selection_type = selection.get("selection_type")
                if selection_type is not None:
                    _selection.update({"selectionType": selection_type})
            i = i + 1

        return templateParams

    def get_project_defined_template_details(self, project_name, template_name):
        """
        Get the template details from the template name provided in the playbook.
        Parameters:
            project_name (str) - Name of the project under which templates are associated.
            template_name (str) - Name of the template provided in the playbook.
        Returns:
            template_details (dict) - Template details for the given template name.
        """

        self.log(
            "Starting to retrieve template details for project '{0}' and template '{1}'.".format(
                project_name, template_name
            ),
            "INFO",
        )
        template_details = None
        try:
            items = self.catalystcenter_apply["exec"](
                family="configuration_templates",
                function="get_templates_details",
                op_modifies=True,
                params={"project_name": project_name, "name": template_name},
            )
            if items:
                template_details = items
                self.log(
                    "Received template details for '{0}': {1}".format(
                        template_name, template_details
                    ),
                    "DEBUG",
                )
            else:
                self.log(
                    "No template details found for project '{0}' and template '{1}'.".format(
                        project_name, template_name
                    ),
                    "WARNING",
                )

            self.log(
                "Received API response from 'get_templates_details': {0}".format(
                    template_details
                ),
                "DEBUG",
            )
        except Exception as e:
            self.log(
                "Exception occurred while retrieving template details for '{0}': {1}".format(
                    template_name, str(e)
                ),
                "ERROR",
            )

        return template_details

    def get_containing_templates(self, containing_templates):
        """
        Store tags from the playbook for template processing in Cisco Catalyst Center.
        Check using check_return_status()

        Parameters:
            containing_templates (dict) - Containing templates details.
            containing Template information.

        Returns:
            containingTemplates (dict) - Organized containing templates parameters.
        """

        if containing_templates is None:
            return None

        containingTemplates = []
        i = 0
        for item in containing_templates:
            containingTemplates.append({})
            _tags = item.get("tags")
            if _tags is not None:
                containingTemplates[i].update({"tags": self.get_tags(_tags)})

            composite = item.get("composite")
            if composite is not None:
                containingTemplates[i].update({"composite": composite})

            description = item.get("description")
            if description is not None:
                containingTemplates[i].update({"description": description})

            device_types = item.get("device_types")
            if device_types is not None:
                containingTemplates[i].update(
                    {"deviceTypes": self.get_device_types(device_types)}
                )

            name = item.get("name")
            if name is None:
                self.msg = "The parameter 'name' is required under 'containing_templates' but not provided."
                self.status = "failed"
                return self.check_return_status()

            containingTemplates[i].update({"name": name})

            project_name = item.get("project_name")
            if project_name is None:
                self.msg = "The parameter 'project_name' is required under 'containing_templates' but not provided."
                self.set_operation_result(
                    "failed", False, self.msg, "ERROR"
                ).check_return_status()
                return self

            template_response = self.get_project_defined_template_details(
                project_name, name
            )
            template_details = template_response.get("response") if template_response else None
            if not template_details:
                self.msg = "No template with the template name '{0}' or it is not versioned".format(
                    name
                )
                self.status = "failed"
                return self.check_return_status()

            id = template_details[0].get("id")
            if id is not None:
                containingTemplates[i].update({"id": id})

            language = item.get("language")
            if language is None:
                self.msg = "The parameter 'language' is required under 'containing_templates' but not provided."
                self.status = "failed"
                return self.check_return_status()

            language_list = ["JINJA", "VELOCITY"]
            if language not in language_list:
                self.msg = "language under containing templates should be in " + str(
                    language_list
                )
                self.status = "failed"
                return self.check_return_status()

            containingTemplates[i].update({"language": language})

            containingTemplates[i].update({"projectName": project_name})
            template_content = item.get("template_content")
            if template_content is not None:
                containingTemplates[i].update({"templateContent": template_content})

            template_params = item.get("template_params")
            if template_params is not None:
                containingTemplates[i].update(
                    {"templateParams": self.get_template_info(template_params)}
                )

            version = item.get("version")
            if version is not None:
                containingTemplates[i].update({"version": version})

            i += 1

        return containingTemplates

    def get_template_params(self, params):
        """
        Converts template parameter data from playbook format to Cisco Catalyst Center API format with
        comprehensive validation and file handling. Supports both inline template content and file-based
        template content with proper priority handling and security validation. Both content sources are
        optional; if neither is provided, the playbook will be created without template content.

        Parameters:
            params (dict): Playbook details containing template information including:
                          - template_content (str, optional): Inline template content
                          - template_content_file_path (str, optional): Path to template content file
                          - template_name (str, required): Name of the template
                          - project_name (str, required): Name of the project
                          - language (str, required): Template language (JINJA/VELOCITY)
                          - software_type (str, required): Software type for template

        Returns:
            dict: Organized template parameters formatted for Cisco Catalyst Center API consumption

        Description:
            - Validates template content sources with file-first priority pattern
            - Processes file-based template content with security validation
            - Handles both inline content and file path specifications (both optional)
            - Validates required parameters and formats for API compatibility
            - Supports composite template configurations with failure policies
        """

        self.log("Template params playbook details: {0}".format(params), "DEBUG")

        # Read template content from file if file path is provided (both sources optional)
        template_content = params.get("template_content")
        template_content_file_path = params.get("template_content_file_path")
        validate_jinja2_syntax = params.get("validate_jinja2_syntax")

        self.log(
            "Template content sources - file_path: {0}, inline_content: {1}".format(
                bool(template_content_file_path), bool(template_content)
            ),
            "DEBUG"
        )

        # Priority 1: template_content_file_path (file-based content)
        if template_content_file_path:
            self.log(
                "Processing file-based template content from path: {0}".format(
                    template_content_file_path
                ),
                "INFO"
            )

            # Validate file existence
            if not self.is_path_exists(template_content_file_path):
                error_msg = "Template content file path '{0}' does not exist".format(
                    template_content_file_path
                )
                self.log(error_msg, "ERROR")
                self.msg = error_msg
                self.status = "failed"
                return self.check_return_status()

            # Validate file extension
            allowed_ext = (".j2", ".txt")
            if not str(template_content_file_path).lower().endswith(allowed_ext):
                self.msg = (
                    "Invalid template_content_file_path extension. Allowed: .j2, .txt"
                )
                self.status = "failed"
                return self.check_return_status()

            if template_content:
                warning_msg = (
                    "Both 'template_content' and 'template_content_file_path' provided. "
                    "Using file path and ignoring inline content"
                )
                self.log(warning_msg, "WARNING")

            try:
                with open(template_content_file_path, "r", encoding="utf-8") as f:
                    template_content = f.read()
            except Exception as e:
                self.msg = (
                    "Failed to read template content from file '{0}': {1}".format(
                        template_content_file_path, str(e)
                    )
                )
                self.status = "failed"
                return self.check_return_status()

            # Validate .j2 file content for Jinja2 syntax
            if validate_jinja2_syntax and str(template_content_file_path).lower().endswith(".j2"):
                self.log(
                    "Validating Jinja2 template syntax for file: {0}".format(
                        template_content_file_path
                    ),
                    "DEBUG"
                )
                try:
                    from jinja2 import Environment, TemplateSyntaxError
                except ImportError:
                    self.msg = (
                        "Jinja2 library is required to validate .j2 template files. "
                        "Install it using: pip install jinja2"
                    )
                    self.log(self.msg, "ERROR")
                    self.status = "failed"
                    return self.check_return_status()

                try:
                    env = Environment()
                    env.parse(template_content)
                    self.log(
                        "Jinja2 template validation successful for file: {0}".format(
                            template_content_file_path
                        ),
                        "DEBUG"
                    )
                except TemplateSyntaxError as e:
                    self.msg = (
                        "Invalid Jinja2 template syntax in file '{0}' at line {1}: {2}".format(
                            template_content_file_path, e.lineno, e.message
                        )
                    )
                    self.log(self.msg, "ERROR")
                    self.status = "failed"
                    return self.check_return_status()
                except Exception as e:
                    self.msg = (
                        "Failed to validate Jinja2 template from file '{0}': {1}".format(
                            template_content_file_path, str(e)
                        )
                    )
                    self.log(self.msg, "ERROR")
                    self.status = "failed"
                    return self.check_return_status()

        # Priority 2: template_content (inline content) - fallback
        elif template_content:
            self.log(
                "Using inline template content - length: {0} characters".format(
                    len(template_content)
                ),
                "DEBUG"
            )
        else:
            # No content provided; proceed without 'templateContent' field
            self.log(
                "No template content provided; proceeding with empty template content",
                "DEBUG"
            )
            template_content = ""

        temp_params = {
            "tags": self.get_tags(params.get("template_tag")),
            "author": params.get("author"),
            "composite": params.get("composite"),
            "containingTemplates": self.get_containing_templates(
                params.get("containing_templates")
            ),
            "customParamsOrder": params.get("custom_params_order"),
            "description": params.get("template_description"),
            "deviceTypes": self.get_device_types(params.get("device_types")),
            "id": params.get("id"),
            "softwareVersion": params.get("software_version"),
            "templateContent": template_content,
            "templateParams": self.get_template_info(params.get("template_params")),
            "version": params.get("version"),
        }
        language = params.get("language")
        if not language:
            self.msg = "The parameter 'language' is required but not provided."
            self.status = "failed"
            return self.check_return_status()

        language = language.upper()
        language_list = ["JINJA", "VELOCITY"]
        if language not in language_list:
            self.msg = "language should be in '{0}'".format(language_list)
            self.status = "failed"
            return self.check_return_status()

        temp_params.update({"language": language})

        name = params.get("template_name")
        if not name:
            self.msg = "The parameter 'template_name' is required but not provided."
            self.status = "failed"
            return self.check_return_status()

        temp_params.update({"name": name})

        projectName = params.get("project_name")
        if not projectName:
            self.msg = "The parameter 'project_name' is required but not provided."
            self.status = "failed"
            return self.check_return_status()

        temp_params.update({"projectName": projectName})

        softwareType = params.get("software_type")
        if not softwareType:
            self.msg = "The parameter 'software_type' is required but not provided."
            self.status = "failed"
            return self.check_return_status()

        software_types_list = [
            "IOS",
            "IOS-XE",
            "IOS-XR",
            "NX-OS",
            "Cisco Controller",
            "Wide Area Application Services",
            "Adaptive Security Appliance",
            "NFV-OS",
            "Others",
        ]
        if softwareType not in software_types_list:
            self.msg = (
                "The 'software_type' should be in the following list {0}.".format(
                    software_types_list
                )
            )
            self.status = "failed"
            return self.check_return_status()

        temp_params.update({"softwareType": softwareType})

        if temp_params.get("composite") is True:
            failure_policy = params.get("failure_policy")
            failure_policy_list = ["ABORT_TARGET_ON_ERROR", None]
            if failure_policy not in failure_policy_list:
                self.msg = (
                    "The 'failure_policy' should be in the following list {0}.".format(
                        failure_policy
                    )
                )
                self.status = "failed"
                return self

            temp_params.update({"failurePolicy": failure_policy})

        self.log("Formatted template params details: {0}".format(temp_params), "DEBUG")
        copy_temp_params = copy.deepcopy(temp_params)
        for item in copy_temp_params:
            if temp_params[item] is None:
                del temp_params[item]
        return temp_params

    def get_template(self, config):
        """
        Get the template needed for update or creation.

        Parameters:
            config (dict) - Playbook details containing Template information.

        Returns:
            result (dict) - Template details for the given template ID.
        """

        result = None
        items = self.catalystcenter_apply["exec"](
            family="configuration_templates",
            function="get_template_details",
            op_modifies=True,
            params={"template_id": config.get("templateId")},
        )
        if items:
            result = items

        self.log(
            "Received API response from 'get_template_details': {0}".format(items),
            "DEBUG",
        )

        return result

    def get_uncommitted_template_id(self, project_name, template_name):
        """
        Retrieves the ID of an uncommitted template from a specified project in the Cisco Catalyst Center.

        Args:
            self (object): An instance of the class used for interacting with Cisco Catalyst Center.
            project_name (str): The name of the project under which the template is located.
            template_name (str): The name of the template whose uncommitted ID is to be retrieved.
        Returns:
            str or None: The template ID if found, otherwise `None` if the template is not available or uncommitted.
        Description:
            This function queries the Cisco Catalyst Center for uncommitted templates within a specified project.
            It checks if the template list contains the specified `template_name` and if found, returns the associated
            `templateId`. If the template is not found, the function logs a warning message and returns `None`.
            The function is useful for identifying templates that are not yet committed, which can then be versioned
            or deployed. If the template is unavailable, an appropriate log message is recorded and the function
            exits early with `None`.
        """
        self.log(
            "Retrieving uncommitted template ID for project '{0}' and template "
            "'{1}'.".format(project_name, template_name),
            "INFO",
        )
        template_id = None
        try:
            template_list = self.catalystcenter_apply["exec"](
                family="configuration_templates",
                function="gets_the_templates_available",
                op_modifies=False,
                params={"projectNames": project_name, "un_committed": True},
            )
            self.log(
                "Received Response from 'gets_the_templates_available' for 'project_name': '{0}' is {1}".format(
                    project_name, template_list
                ),
                "DEBUG",
            )

            if not template_list:
                msg = (
                    "No uncommitted templates available under the project '{0}'. "
                    "Cannot commit or deploy the template '{1}' in device(s)."
                ).format(project_name, template_name)
                self.log(msg, "WARNING")
                return template_id

            for template in template_list:
                if template.get("name") == template_name:
                    template_id = template.get("templateId")
                    self.log(
                        "Found uncommitted template '{0}' with ID: '{1}'.".format(
                            template_name, template_id
                        ),
                        "INFO",
                    )
                    return template_id
            self.log(
                "Template '{0}' not found in the uncommitted templates for project '{1}'.".format(
                    template_name, project_name
                ),
                "WARNING",
            )
        except Exception as e:
            error_msg = (
                "Exception occurred while retrieving uncommitted template ID for project '{0}' and "
                "template '{1}': {2}."
            ).format(project_name, template_name, str(e))
            self.log(error_msg, "ERROR")
            self.msg = error_msg

        return template_id

    def versioned_given_template(self, project_name, template_name, template_id):
        """
        Versions (commits) a specified template in the Cisco Catalyst Center.

        Args:
            self (object): An instance of the class used for interacting with Cisco Catalyst Center.
            project_name (str): The name of the project under which the template resides.
            template_name (str): The name of the template to be versioned.
            template_id (str): The unique identifier of the template to be versioned.
        Returns:
            self (object): The instance of the class itself, with the operation result (success/failure) set accordingly.
        Description:
            This function handles the process of versioning or committing a template in the Cisco Catalyst Center.
            It constructs a request payload with versioning comments and template ID, and then calls the API to
            initiate the versioning task.
            The function returns the class instance for further chaining of operations.
        """

        self.log(
            "Starting the versioning process for template '{0}' in project '{1}'.".format(
                template_name, project_name
            ),
            "INFO",
        )
        try:
            comments = (
                "Given template '{0}' under the project '{1}' versioned successfully."
            ).format(template_name, project_name)

            version_params = {"comments": comments, "templateId": template_id}
            self.log(
                "Preparing to version template with parameters: {0}".format(
                    version_params
                ),
                "DEBUG",
            )
            task_name = "version_template"
            task_id = self.get_taskid_post_api_call(
                "configuration_templates", task_name, version_params
            )

            if not task_id:
                self.msg = "Unable to retrieve the task_id for the task '{0}'.".format(
                    task_name
                )
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self

            success_msg = "Given template '{0}' versioned/committed successfully in the Cisco Catalyst Center.".format(
                template_name
            )
            self.get_task_status_from_tasks_by_id(task_id, task_name, success_msg)

        except Exception as e:
            self.msg = (
                "An exception occurred while versioning the template '{0}' in the Cisco Catalyst "
                "Center: {1}"
            ).format(template_name, str(e))
            self.set_operation_result("failed", False, self.msg, "ERROR")

        return self

    def get_have_project(self, config):
        """
        Get the current project related information from Cisco Catalyst Center.

        Parameters:
            config (dict) - Playbook details containing Project information.

        Returns:
            template_available (list) - Current project information.
        """

        have_project = {}
        given_projectName = config.get("configuration_templates").get("project_name")
        template_available = None

        # Check if project exists.
        project_details = self.get_project_details(given_projectName)
        # Cisco Catalyst Center returns project details even if the substring matches.
        # Hence check the projectName retrieved from Cisco Catalyst Center.
        if not (project_details and isinstance(project_details, list)):
            self.log(
                "Project: {0} not found, need to create new project in Cisco Catalyst Center".format(
                    given_projectName
                ),
                "INFO",
            )
            return None

        fetched_projectName = project_details[0].get("name")
        if fetched_projectName != given_projectName:
            self.log(
                "Project {0} provided is not exact match in Cisco Catalyst Center DB".format(
                    given_projectName
                ),
                "INFO",
            )
            return None

        template_available = project_details[0].get("templates")
        have_project["project_found"] = True
        have_project["id"] = project_details[0].get("id")
        have_project["isDeletable"] = project_details[0].get("isDeletable")

        self.have_project = have_project
        return template_available

    def get_have_template(self, config, template_available):
        """
        Get the current template related information from Cisco Catalyst Center.

        Parameters:
            config (dict) - Playbook details containing Template information.
            template_available (list) -  Current project information.

        Returns:
            self
        """

        projectName = config.get("configuration_templates").get("project_name")
        templateName = config.get("configuration_templates").get("template_name")
        template = None
        have_template = {}

        have_template["isCommitPending"] = False
        have_template["template_found"] = False
        template_details = get_dict_result(template_available, "name", templateName)
        # Check if specified template in playbook is available
        if not template_details:
            self.log(
                "Template {0} not found in project {1}".format(
                    templateName, projectName
                ),
                "INFO",
            )
            self.msg = "Template : {0} missing, new template to be created".format(
                templateName
            )
            self.status = "success"
            return self

        config["templateId"] = template_details.get("id")
        have_template["id"] = template_details.get("id")
        project_name = config.get("configuration_templates").get("project_name")
        # Get available templates which are committed under the project
        template_list = self.catalystcenter_apply["exec"](
            family="configuration_templates",
            function="gets_the_templates_available",
            op_modifies=True,
            params={
                "projectNames": projectName,
                "un_committed": True
            },
        )
        self.log(
            "Received response from 'gets_the_templates_available' for project_name: '{0}' is {1}".format(
                project_name, template_list
            ),
            "DEBUG",
        )

        have_template["isCommitPending"] = True
        # This check will fail if specified template is there not committed in Cisco Catalyst Center
        if template_list and isinstance(template_list, list):
            template_info = get_dict_result(template_list, "name", templateName)
            if template_info:
                template = self.get_template(config)
                have_template["template"] = template
                have_template["isCommitPending"] = False
                have_template["template_found"] = template is not None and isinstance(
                    template, dict
                )
                self.log(
                    "Template {0} is found and template "
                    "details are :{1}".format(templateName, str(template)),
                    "INFO",
                )

        # There are committed templates in the project but the
        # one specified in the playbook may not be committed
        self.log(
            "Commit pending for template name {0}"
            " is {1}".format(templateName, have_template.get("isCommitPending")),
            "INFO",
        )

        self.have_template = have_template
        self.msg = "Successfully collected all template parameters from Cisco Catalyst Center for comparison"
        self.status = "success"
        return self

    def _retrieve_all_profiles_with_pagination(self, device_type):
        """
        Retrieves all profiles for the specified device type using pagination.

        Parameters:
            device_type (str): The type of device for which to retrieve profiles.
        """

        self.log("Starting profile retrieval with pagination for device type: '{0}'".format(
            device_type), "DEBUG")

        offset = 1
        limit = 500
        api_timeout = int(self.payload.get("catalystcenter_api_task_timeout", 1200))
        poll_interval = int(self.payload.get("catalystcenter_task_poll_interval", 2))

        start_time = time.time()

        while True:
            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time >= api_timeout:
                self.msg = "Timeout exceeded ({0}s) while retrieving profiles for device type '{1}'".format(
                    api_timeout, device_type)
                self.log(self.msg, "ERROR")
                self.fail_and_exit(self.msg)

            self.log("Retrieving profiles with offset={0}, limit={1} for device type '{2}'".format(
                offset, limit, device_type), "DEBUG")

            profiles = self._get_profiles_by_device_type(device_type, offset, limit)

            if not profiles:
                self.log("No more profiles received from API (offset={0}). Pagination complete.".format(offset), "DEBUG")
                break

            self.log("Retrieved {0} profile(s) from API (offset={1})".format(len(profiles), offset), "DEBUG")
            self.have["profile_list"].extend(profiles)

            # Check if we've received all available profiles
            if len(profiles) < limit:
                self.log("Received fewer profiles than limit ({0} < {1}). Last page reached.".format(
                    len(profiles), limit), "DEBUG")
                break

            # Prepare for next iteration
            offset += limit
            self.log("Incrementing offset to {0} for next API request".format(offset), "DEBUG")

            # Rate limiting
            self.log("Applying rate limiting delay of {0} seconds before next API call".format(poll_interval), "DEBUG")
            time.sleep(poll_interval)

    def _get_profiles_by_device_type(self, device_type, offset, limit):
        """
        Maps device type to appropriate network profile category and retrieves profiles.

        Parameters:
            device_type (str): The type of device.
            offset (int): Pagination offset.
            limit (int): Pagination limit.

        Returns:
            list: List of profiles for the specified device type.
        """

        # Device type to profile category mapping
        device_type_mapping = {
            "Switches and Hubs": "Switching",
            "Wireless Controller": "Wireless",
            "Routers": "Routing",
            "Security and VPN": "Firewall"
        }

        profile_category = device_type_mapping.get(device_type, "Assurance")

        self.log("Mapping device type '{0}' to profile category '{1}'".format(
            device_type, profile_category), "DEBUG")

        try:
            profiles = self.get_network_profile(profile_category, offset, limit)
            self.log("Successfully retrieved profiles for category '{0}'".format(
                profile_category), "DEBUG")
            return profiles

        except Exception as e:
            self.log("Error retrieving profiles for category '{0}': {1}".format(
                profile_category, str(e)), "ERROR")
            return []

    def _process_individual_profile(self, profile_name, template_name, template_id):
        """
        Processes an individual profile to determine its assignment status.

        Parameters:
            profile_name (str): Name of the profile to process.
            template_name (str): Name of the template to check assignment against.
            template_id (str): UUID of the template to check assignment against.

        Returns:
            dict: Profile information including assignment status.
        """
        self.log("Processing individual profile: '{0}' for template: '{1}' (ID: {2})".format(
            profile_name, template_name, template_id), "DEBUG")

        profile_info = {
            "profile_name": profile_name,
            "template_name": template_name,
            "template_id": template_id
        }
        self.log("Created profile_info with template_id '{0}' for profile '{1}'".format(
            template_id, profile_name), "DEBUG")

        # Validate profile existence
        if not self.value_exists(self.have["profile_list"], "name", profile_name):
            self.msg = "Profile '{0}' does not exist in Cisco Catalyst Center".format(profile_name)
            self.log(self.msg, "ERROR")
            self.fail_and_exit(self.msg)

        # Get profile ID
        profile_index = next(
            (index for index, profile in enumerate(self.have["profile_list"])
             if profile.get("name") == profile_name), -1
        )

        if profile_index == -1:
            self.msg = "Failed to locate profile '{0}' in retrieved profile list".format(profile_name)
            self.log(self.msg, "ERROR")
            self.fail_and_exit(self.msg)

        profile_id = self.have["profile_list"][profile_index]["id"]
        profile_info["profile_id"] = profile_id

        self.log("Successfully resolved profile '{0}' to ID: '{1}'".format(
            profile_name, profile_id), "DEBUG")

        # Check template assignment
        self.log("Checking assignment status for profile '{0}' against template ID '{1}'".format(
            profile_name, template_id), "DEBUG")
        assignment_status = self._check_profile_template_assignment(
            profile_name, profile_id, template_id)
        profile_info["profile_status"] = assignment_status
        self.log("Assignment status determined for profile '{0}': '{1}'".format(
            profile_name, assignment_status), "INFO")

        if assignment_status == "already assigned":
            self.profile_exists.append(profile_name)
            self.log("Profile '{0}' marked as existing (already assigned)".format(
                profile_name), "DEBUG")

        self.log("Profile processing completed for '{0}': status='{1}'".format(
            profile_name, assignment_status), "DEBUG")
        return profile_info

    def _check_profile_template_assignment(self, profile_name, profile_id, template_id):
        """
        Checks if a profile is assigned to the specified template.

        Parameters:
            profile_name (str): Name of the profile.
            profile_id (str): ID of the profile.
            template_id (str): UUID of the template to check assignment against.

        Returns:
            str: Assignment status ('Not Assigned' or 'already assigned').
        """

        self.log("Checking template assignment for profile '{0}' (ID: {1}) against template ID '{2}'".format(
            profile_name, profile_id, template_id), "DEBUG")

        try:
            template_details = self.get_templates_for_profile(profile_id)

            if not template_details:
                self.log("No templates found assigned to profile '{0}'".format(
                    profile_name), "INFO")
                return "Not Assigned"

            self.log("Found {0} template(s) assigned to profile '{1}'".format(
                len(template_details), profile_name), "DEBUG")

            # Check if the specific template (by ID) is assigned
            # Using template ID ensures uniqueness even across projects with same template names
            for template in template_details:
                assigned_template_id = template.get("id")
                assigned_template_name = template.get("name")
                assigned_project_name = template.get("projectName")

                self.log("Checking assigned template: name='{0}', projectName='{1}', id='{2}'".format(
                    assigned_template_name, assigned_project_name, assigned_template_id), "DEBUG")

                # Compare template IDs for exact match
                if assigned_template_id == template_id:
                    self.log("Profile '{0}' is already assigned to template ID '{1}' (name: '{2}')".format(
                        profile_name, template_id, assigned_template_name), "INFO")
                    return "already assigned"

            self.log("Profile '{0}' is not assigned to template ID '{1}' (may be assigned to other templates)".format(
                profile_name, template_id), "INFO")
            return "Not Assigned"

        except Exception as e:
            self.log("Error checking template assignment for profile '{0}': {1}".format(
                profile_name, str(e)), "ERROR")
            return "Not Assigned"

    def get_profile_details(self, device_type, input_profiles, template_name, template_id):
        """
        Retrieves profile details and assignment status for given profile names from Cisco Catalyst Center.

        Parameters:
            device_type (str) - The type of device for which to retrieve profile details.
            input_profiles (list) - List of profile names to retrieve details for.
            template_name (str) - The name of the template for which to retrieve profile details.
            template_id (str) - The UUID of the template for which to retrieve profile details.

        Returns:
            list: A list of dictionaries containing profile information including:
                - profile_name (str): Name of the profile
                - profile_id (str): UUID of the profile
                - profile_status (str): Assignment status ('Not Assigned' or 'already assigned')
                - template_name (str): Name of the template
                - template_id (str): UUID of the template

        Description:
            This function retrieves comprehensive profile information from Cisco Catalyst Center and determines
            the assignment status of each profile to the specified template. It handles pagination for large
            profile datasets, validates profile existence, and checks current template assignments. The function
            supports multiple device types and maps them to appropriate network profile categories for API calls.
        """
        self.log("Initiating profile details collection for device type '{0}' with profiles: {1} and template '{2}'".format(
            device_type, input_profiles, template_name), "DEBUG")

        # Input validation
        if not device_type:
            self.msg = "Device type is required but not provided for profile details collection"
            self.log(self.msg, "ERROR")
            self.fail_and_exit(self.msg)

        if not input_profiles or not isinstance(input_profiles, list):
            self.msg = "Input profiles must be provided as a non-empty list for profile details collection"
            self.log(self.msg, "ERROR")
            self.fail_and_exit(self.msg)

        if not template_name:
            self.msg = "Template name is required but not provided for profile details collection"
            self.log(self.msg, "ERROR")
            self.fail_and_exit(self.msg)

        if not template_id:
            self.msg = "Template ID is required but not provided for profile details collection"
            self.log(self.msg, "ERROR")
            self.fail_and_exit(self.msg)

        self.log("Collecting profile information for device type '{0}', profiles: {1}, template: '{2}' (ID: {3})".format(
            device_type, input_profiles, template_name, template_id), "INFO")

        # Initialize profile storage
        self.have["profile"] = []
        self.have["profile_list"] = []

        # Retrieve all profiles with pagination
        self._retrieve_all_profiles_with_pagination(device_type)

        if not self.have["profile_list"]:
            self.msg = "No profiles found for device type '{0}' in Cisco Catalyst Center".format(device_type)
            self.log(self.msg, "ERROR")
            self.fail_and_exit(self.msg)

        self.log("Successfully retrieved {0} total profile(s) for device type '{1}'".format(
            len(self.have["profile_list"]), device_type), "INFO")

        # Process each input profile
        processed_profiles = []
        for profile_name in input_profiles:
            profile_info = self._process_individual_profile(profile_name, template_name, template_id)
            processed_profiles.append(profile_info)

        self.log("Profile details collection completed successfully. Processed {0} profile(s): {1}".format(
            len(processed_profiles), self.pprint(processed_profiles)), "INFO")

        return processed_profiles

    def get_have(self, config):
        """
        Get the current project and template details from Cisco Catalyst Center.

        Parameters:
            config (dict) - Playbook details containing Project/Template information.

        Returns:
            self
        """
        have = {}
        configuration_templates = config.get("configuration_templates")
        if configuration_templates:
            profile_names = configuration_templates.get("profile_names")
            template_name = configuration_templates.get("template_name")
            device_types = configuration_templates.get("device_types")
            project_name = configuration_templates.get("project_name")

            if not project_name:
                self.msg = "The parameter 'project_name' is required but not provided."
                self.status = "failed"
                return self
            template_available = self.get_have_project(config)
            if template_available:
                self.get_have_template(config, template_available)

            if profile_names and template_name and device_types:
                self.log("Initiating profile assignment collection for template profile management", "DEBUG")

                # Get template ID for accurate profile assignment tracking
                # Only proceed with profile collection if template exists
                template_id = self.have_template.get("id") if self.have_template else None
                self.log("Retrieved template_id from have_template: {0}".format(
                    template_id if template_id else "None (template does not exist)"), "DEBUG")

                if template_id:
                    self.log("Template ID '{0}' found for template '{1}'. Proceeding with profile assignment collection.".format(
                        template_id, template_name), "DEBUG")

                    if device_types:
                        parsed_current_profile = []
                        for each_type in device_types:
                            each_family = each_type.get("product_family")
                            parsed_current_profile.extend(
                                self.get_profile_details(each_family,
                                                         profile_names,
                                                         template_name,
                                                         template_id)
                            )

                    have["current_profile"] = self.deduplicate_list_of_dict(parsed_current_profile)
                else:
                    self.log("Template '{0}' does not exist yet. Profile assignment will be handled after template creation.".format(
                        template_name), "INFO")
                    have["current_profile"] = []

        project_config = config.get("projects", [])
        if project_config and isinstance(project_config, list):
            have["projects"] = []
            for project in project_config:
                project_name = project.get("name")

                if not project_name:
                    self.log("Skipping project: Missing 'name' field.", "WARNING")
                    continue

                # Fetch existing project details based on the name
                existing = self.get_project_details(project_name)
                if existing:
                    proj_status, unmatched = self.compare_projects(project, existing[0])
                    existing[0]["project_status"] = proj_status
                    existing[0]["unmatched"] = unmatched
                    have["projects"].append(existing[0] or {})
                else:
                    self.log("No existing project found for name: {0}".format(
                        project_name), "INFO")

        deploy_temp_details = config.get("deploy_template")
        if deploy_temp_details:
            template_name = deploy_temp_details.get("template_name")
            project_name = deploy_temp_details.get("project_name")
            self.log(
                "Fetching template details for '{0}' under project '{1}'.".format(
                    template_name, project_name
                ),
                "INFO",
            )
            template_response = self.get_project_defined_template_details(
                project_name, template_name
            )
            temp_details = template_response.get("response") if template_response else None

            if temp_details:
                self.log(
                    "Given template '{0}' is already committed in the Catalyst Center.".format(
                        template_name
                    ),
                    "INFO",
                )
                have["temp_id"] = temp_details[0].get("id")

                self.log(
                    "Successfully collected the details for the template '{0}' from the "
                    "Cisco Catalyst Center.".format(template_name),
                    "INFO",
                )
            else:
                self.log(
                    "No details found for template '{0}' under project '{1}'.".format(
                        template_name, project_name
                    ),
                    "WARNING",
                )

        self.have = have

        self.msg = "Successfully collected all project and template \
                    parameters from Cisco Catalyst Center for comparison"
        self.status = "success"
        self.log("Current State (have): {0}".format(self.pprint(self.have)), "INFO")
        return self

    def get_project_details(self, project_name):
        """
        Get the details of specific project name provided.

        Parameters:
            project_name (str) - Project Name

        Returns:
            items (dict) - Project details with given project name.
        """

        self.log(
            "Initializing retrival of project details for project: {0}".format(
                project_name
            ),
            "DEBUG",
        )
        ccc_version = self.get_ccc_version()

        if self.compare_catalystcenter_versions(ccc_version, "2.3.7.9") < 0:
            self.log(
                "Retrieving project details for project: {0} when catalyst version is less than 2.3.7.9".format(
                    project_name
                ),
                "DEBUG",
            )

            items = self.catalystcenter_apply["exec"](
                family="configuration_templates",
                function="get_projects",
                op_modifies=True,
                params={"name": project_name},
            )

            self.log(
                "Received Response from get_projects for project: {0} when catalyst version is less than 2.3.7.9: {1}".format(
                    project_name, items
                ),
                "DEBUG",
            )
        else:
            self.log(
                "Retrieving project details for project: {0} when catalyst version is greater than or equal to 2.3.7.9".format(
                    project_name
                ),
                "DEBUG",
            )
            items = self.catalystcenter_apply["exec"](
                family="configuration_templates",
                function="get_projects_details",
                op_modifies=True,
                params={"name": project_name},
            )

            self.log(
                "Received Response from get_projects for project: {0} when catalyst version is greater than or equal to 2.3.7.9: {1}".format(
                    project_name, items
                ),
                "DEBUG",
            )
            items = items["response"]

        self.log(
            "Retrieved project details for project '{0}' are {1}".format(
                project_name, items
            ),
            "DEBUG",
        )
        return items

    def get_want(self, config):
        """
        Get all the template and project related information from playbook
        that is needed to be created in Cisco Catalyst Center.

        Parameters:
            config (dict) - Playbook details.

        Returns:
            self
        """

        want = {}

        project_details = config.get("projects", [])
        if project_details:
            want["projects"] = project_details

        configuration_templates = config.get("configuration_templates")
        self.log("Playbook details: {0}".format(config), "INFO")
        if configuration_templates:
            template_params = self.get_template_params(configuration_templates)
            project_params = self.get_project_params(configuration_templates)
            version_comments = configuration_templates.get("version_description")

            if self.params.get("state") == "merged":
                self.update_mandatory_parameters(template_params)

            ccc_version = self.get_ccc_version()
            if (
                self.compare_catalystcenter_versions(ccc_version, "3.1.3.0") >= 0
                and configuration_templates.get("profile_names")
            ):
                want["profile_names"] = configuration_templates.get("profile_names")

            want["template_params"] = template_params
            want["project_params"] = project_params
            want["comments"] = version_comments

        deploy_temp_details = config.get("deploy_template")
        if deploy_temp_details:
            project_name = deploy_temp_details.get("project_name")
            if not project_name:
                self.msg = (
                    "To Deploy the template in the devices, parameter 'project_name' "
                    "must be given in the playboook."
                )
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self

            self.log(
                "Project name '{0}' found in the playbook.".format(project_name), "INFO"
            )
            template_name = deploy_temp_details.get("template_name")
            if not template_name:
                self.msg = (
                    "To Deploy the template in the devices, parameter 'template_name' "
                    "must be given in the playboook."
                )
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self

            self.log(
                "Template name '{0}' found in the playbook.".format(template_name),
                "INFO",
            )
            device_details = deploy_temp_details.get("device_details")
            site_provisioning_details = deploy_temp_details.get(
                "site_provisioning_details"
            )

            if not (device_details or site_provisioning_details):
                self.msg = (
                    "Either give the parameter 'device_details' or 'site_provisioning_details' "
                    "in the playbook to fetch the device ids and proceed for the deployment of template {0}."
                ).format(template_name)
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self

            self.log(
                "Proceeding with deployment details for template '{0}'.".format(
                    template_name
                ),
                "INFO",
            )
            want["deploy_tempate"] = deploy_temp_details

        self.want = want
        self.msg = (
            "Successfully collected all parameters from playbook " + "for comparison"
        )
        self.status = "success"
        self.log("Desired State (want): {0}".format(self.pprint(self.want)), "INFO")
        return self

    def compare_projects(self, input_config, current_proj):
        """
        Compares an input project configuration with the current project configuration in
        Cisco Catalyst Center.

        Args:
            self (object): Instance of the class used for interacting with Cisco Catalyst Center.
            input_config (dict): The new project configuration intended to be applied.
            current_proj (dict): The existing project configuration retrieved from the system.

        Returns:
            tuple:
                - bool: True if the configurations match (excluding tags), False otherwise.
                - list: List of values from the input configuration that differ from
                the current configuration.

        Description:
            This method performs a key-by-key comparison between the input and existing project configurations,
            excluding the "tags" field. It logs the comparison process and results. If mismatches are found,
            the differing input values are collected and returned for further processing or reporting.
        """
        self.log("Comparing input project config with current config.", "INFO")
        self.log("Input project config: {0}".format(self.pprint(input_config)), "DEBUG")
        self.log("Current project config: {0}".format(self.pprint(current_proj)), "DEBUG")

        unmatched_keys = []

        if input_config and current_proj:
            for key, value in input_config.items():
                # Compare values of the current key
                if current_proj.get(key) != value:
                    unmatched_keys.append(key)
                    self.log("Mismatch found for key: {0}. Input value: {1}, Current value: {2}".format(
                        key, value, current_proj.get(key)), "DEBUG")

            # If no mismatches are found, configurations match
            if not unmatched_keys:
                self.log("Input project config matches current project config.", "INFO")
                return True, None

        self.log("Configurations do not match. Mismatched keys: {0}".format(
            unmatched_keys), "DEBUG")

        return False, unmatched_keys

    def create_project_or_template(self, is_create_project=False):
        """
        Call Cisco Catalyst Center API to create project or template based on the input provided.

        Parameters:
            is_create_project (bool) - Default value is False.

        Returns:
            creation_id (str) - Project Id.
            created (str) - True if Project created, else False.
        """

        creation_id = None
        created = False
        self.log("Desired State (want): {0}".format(self.want), "INFO")
        template_params = self.want.get("template_params")
        project_params = self.want.get("project_params")

        if is_create_project:
            params_key = project_params
            self.project_created.append(project_params.get('name'))
            name = "project: {0}".format(project_params.get('name'))
            validation_string = "Successfully created project"
            creation_value = "create_project"
        else:
            params_key = template_params
            self.template_created.append(template_params.get('name'))
            name = "template: {0}".format(template_params.get('name'))
            validation_string = "Successfully created template"
            creation_value = "create_template"

        response = self.catalystcenter_apply["exec"](
            family="configuration_templates",
            function=creation_value,
            op_modifies=True,
            params=params_key,
        )
        if not isinstance(response, dict):
            self.log(
                "Response of '{0}' is not in dictionary format.".format(creation_value),
                "CRITICAL",
            )
            return creation_id, created

        task_id = response.get("response").get("taskId")
        if not task_id:
            self.log(
                "Task id {0} not found for '{1}'.".format(task_id, creation_value),
                "CRITICAL",
            )
            return creation_id, created

        while not created:
            task_details = self.get_task_details(task_id)
            if not task_details:
                self.log(
                    "Failed to get task details of '{0}' for taskid: {1}".format(
                        creation_value, task_id
                    ),
                    "CRITICAL",
                )
                return creation_id, created

            self.log(
                "Task details for {0}: {1}".format(creation_value, task_details),
                "DEBUG",
            )
            if task_details.get("isError"):
                self.log(
                    "Error occurred for '{0}' with taskid: {1}".format(
                        creation_value, task_id
                    ),
                    "ERROR",
                )
                return task_id, created

            if validation_string not in task_details.get("progress"):
                self.log(
                    "'{0}' progress set to {1} for taskid: {2}".format(
                        creation_value, task_details.get("progress"), task_id
                    ),
                    "DEBUG",
                )
                continue

            task_details_data = task_details.get("data")
            value = self.check_string_dictionary(task_details_data)
            if value is None:
                creation_id = task_details.get("data")
            else:
                creation_id = value.get("templateId")
            if not creation_id:
                self.log(
                    "Export data is not found for '{0}' with taskid : {1}".format(
                        creation_value, task_id
                    ),
                    "DEBUG",
                )
                continue

            created = True
            if is_create_project:
                # ProjectId is required for creating a new template.
                # Store it with other template parameters.
                template_params["projectId"] = creation_id
                template_params["project_id"] = creation_id

        self.result['changed'] = True
        self.msg = "{0} created successfully with id {1}".format(name, creation_id)
        self.log("New {0} created with id {1}".format(name, creation_id), "DEBUG")
        return creation_id, created

    def requires_containing_templates_update(self, current_obj, requested_obj):
        """
        Determines if an update is required for 'containingTemplates' based on 'name' and 'projectName' fields.

        Returns True if any requested containing template is missing from the current list,
        or if any present template differs in any field (using catalystcenter_compare_equality).

        Args:
            current_obj (dict): The current template object (should contain 'containingTemplates' key).
            requested_obj (dict): The requested template object (should contain 'containingTemplates' key).

        Returns:
            bool: True if an update is required, False otherwise.
        """
        self.log("Checking if containingTemplates requires update...", "DEBUG")

        current_list = current_obj.get("containingTemplates", [])
        requested_list = requested_obj.get("containingTemplates", [])

        self.log("Current containingTemplates: {0}".format(current_list), "DEBUG")
        self.log("Requested containingTemplates: {0}".format(requested_list), "DEBUG")

        # Build a dictionary for fast lookup by (name, projectName)
        current_dict = {
            (item.get("name"), item.get("projectName")): item
            for item in current_list
            if item.get("name") is not None and item.get("projectName") is not None
        }

        for req in requested_list:
            req_name = req.get("name")
            req_project = req.get("projectName")
            if req_name is None or req_project is None:
                self.log(
                    "Skipping requested containing template with missing 'name' or 'projectName': {0}".format(req),
                    "WARNING"
                )
                continue

            req_key = (req_name, req_project)
            if req_key not in current_dict:
                self.log(
                    "Containing template '{0}' under project '{1}' is missing in current state and requires update.".format(
                        req_name, req_project
                    ),
                    "INFO"
                )
                return True

            if not catalystcenter_compare_equality(current_dict[req_key], req):
                self.log(
                    "Containing template '{0}' in project '{1}' differs. Current: {2} | Requested: {3}".format(
                        req_name, req_project, current_dict[req_key], req
                    ), "INFO")
                return True

        self.log("No update required for containingTemplates.", "DEBUG")
        return False

    def requires_update(self):
        """
        Check if the template config given requires update.

        Parameters:
            self - Current object.

        Returns:
            bool - True if any parameter specified in obj_params differs between
            current_obj and requested_obj, indicating that an update is required.
            False if all specified parameters are equal.
        """

        if self.have_template.get("isCommitPending"):
            self.log(
                "Template '{0}' is in saved state and needs to be updated and committed.".format(
                    self.have_template.get("template").get("name")
                ),
                "DEBUG",
            )
            return True

        current_obj = self.have_template.get("template")
        requested_obj = self.want.get("template_params")
        self.log("Current State (have): {0}".format(current_obj), "INFO")
        self.log("Desired State (want): {0}".format(requested_obj), "INFO")
        obj_params = [
            ("tags", "tags", ""),
            ("author", "author", ""),
            ("composite", "composite", False),
            ("customParamsOrder", "customParamsOrder", False),
            ("description", "description", ""),
            ("deviceTypes", "deviceTypes", []),
            ("failurePolicy", "failurePolicy", ""),
            ("id", "id", ""),
            ("language", "language", "VELOCITY"),
            ("name", "name", ""),
            ("projectName", "projectName", ""),
            ("softwareType", "softwareType", ""),
            ("softwareVersion", "softwareVersion", ""),
            ("templateContent", "templateContent", ""),
            ("templateParams", "templateParams", []),
            ("version", "version", ""),
        ]

        return any(
            not catalystcenter_compare_equality(
                current_obj.get(catalystcenter_param, default), requested_obj.get(ansible_param)
            )
            for (catalystcenter_param, ansible_param, default) in obj_params
        ) or self.requires_containing_templates_update(current_obj, requested_obj)

    def update_mandatory_parameters(self, template_params):
        """
        Update parameters which are required for creating a template.

        Parameters:
            template_params (dict) - Template information.

        Returns:
            None
        """

        # Mandate fields required for creating a new template.
        # Store it with other template parameters.
        template_params["projectId"] = self.have_project.get("id")
        template_params["project_id"] = self.have_project.get("id")
        # Update language,deviceTypes and softwareType if not provided for existing template.
        if not template_params.get("language"):
            template_params["language"] = self.have_template.get("template").get(
                "language"
            )
        if not template_params.get("deviceTypes"):
            template_params["deviceTypes"] = self.have_template.get("template").get(
                "deviceTypes"
            )
        if not template_params.get("softwareType"):
            template_params["softwareType"] = self.have_template.get("template").get(
                "softwareType"
            )

    def validate_input_merge(self, template_exists):
        """
        Validate input after getting all the parameters from Cisco Catalyst Center.
        "If mandate like deviceTypes, softwareType and language "
        "already present in Cisco Catalyst Center for a template."
        "It is not required to be provided in playbook, "
        "but if it is new creation error will be thrown to provide these fields.

        Parameters:
            template_exists (bool) - True if template exists, else False.

        Returns:
            None
        """

        template_params = self.want.get("template_params")
        language = template_params.get("language").upper()
        if language:
            if language not in self.accepted_languages:
                self.msg = (
                    "Invalid value language {0} ."
                    "Accepted language values are {1}".format(
                        self.accepted_languages, language
                    )
                )
                self.status = "failed"
                return self
        else:
            template_params["language"] = "JINJA"

        if not template_exists:
            if not template_params.get("deviceTypes") or not template_params.get(
                "softwareType"
            ):
                self.msg = "DeviceTypes and SoftwareType are required arguments to create Templates"
                self.status = "failed"
                return self

        self.msg = "Input validated for merging"
        self.status = "success"
        return self

    def commit_the_template(self, template_id, template_name):
        """
        Commits (versions) a given configuration template in Cisco Catalyst Center.

        Args:
            template_id (str): The UUID of the configuration template to be committed.
            template_name (str): The human-readable name of the template (used for logging and messaging).

        Returns:
            object: Returns the current instance (`self`) with updated result and status fields.

        Description:
            This method commits a configuration template by versioning it through the
            `version_template` API call. It uses optional comments from `self.want` as versioning metadata.
            Upon successful API execution, it retrieves the associated task ID and fetches detailed
            task information. The method updates the `self.result` dictionary with the response and a
            commit confirmation message. Logging is performed at key steps for traceability,
            and proper error handling ensures robustness in case of missing task IDs or API failures.
        """

        try:
            self.log("Starting the commit process for template '{0}' with ID '{1}'.".format(template_name, template_id), "INFO")
            version_params = {
                "comments": self.want.get("comments"),
                "templateId": template_id
            }
            self.log("Versioning parameters for template '{0}': {1}".format(template_name, version_params), "DEBUG")
            response = self.catalystcenter_apply['exec'](
                family="configuration_templates",
                function="version_template",
                op_modifies=True,
                params=version_params
            )
            self.log("Received response from API 'version_template' for 'template': '{0}' is {1}".format(template_name, response), "DEBUG")
            if not response or not isinstance(response, dict):
                self.msg = "Invalid response received from 'version_template' API for template '{0}'.".format(template_name)
                self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()
                return self

            task_id = response.get("response").get("taskId")
            if not task_id:
                self.msg = "Unable to retrieve the task_id for the template '{0}'.".format(template_name)
                self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

            self.log("Task ID '{0}' retrieved successfully for template '{1}'.".format(task_id, template_name), "INFO")
            task_details = self.get_task_details(task_id)
            self.log("Task details retrieved for task ID '{0}': {1}".format(task_id, task_details), "DEBUG")
            self.msg = "Template '{0}' committed successfully in Cisco Catalyst Center.".format(template_name)
            # Ensure the response structure in self.result is initialized properly
            self.log("Initializing response structure in self.result for template '{0}'.".format(template_name), "DEBUG")
            if not self.result.get('response'):
                self.result['response'] = [{}]  # Initialize as a list with one empty dictionary

            self.log("Updated self.result structure for template '{0}': {1}".format(template_name, self.result), "DEBUG")
            # Add the template name to the committed list
            self.template_committed.append(template_name)
            self.log("Template '{0}' added to the committed list.".format(template_name), "INFO")
            self.result['changed'] = True
            self.log("Successfully committed template '{0}'.".format(template_name), "INFO")
        except Exception as e:
            self.msg = "Error while executing 'version_template' API for template '{0}': {1}".format(template_name, str(e))
            self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

        return self

    def get_template_commit_status(self, template_id, name):
        """
        Checks whether a given configuration template is committed in Cisco Catalyst Center.

        Args:
            self (object): An instance of the class used for interacting with Cisco Catalyst Center.
            template_id (str): The UUID of the configuration template to check.
            name (str): The name of the configuration template (used for logging purposes).

        Returns:
            bool: Returns True if the template is not committed (uncommitted),
                  and False if it is already committed.

        Description:
            This method verifies the commit status of a configuration template by calling the
            'gets_the_templates_available' API with the `un_committed` parameter set to True.
            If the template is not found in the uncommitted list, it is considered committed.
            Logs are generated for debugging and audit purposes. Any exceptions are caught and
            logged without halting execution.
        """

        self.log("Checking commit status for template '{0}' with ID '{1}'.".format(name, template_id), "INFO")
        is_template_uncommitted = True
        try:
            response = self.catalystcenter_apply['exec'](
                family="configuration_templates",
                function="gets_the_templates_available",
                op_modifies=False,
                params={
                    "id": template_id,
                    "un_committed": True
                },
            )
            self.log("Received Response from 'gets_the_templates_available' for 'template': '{0}' is {1}".format(name, response), "DEBUG")
            if not response or not isinstance(response, dict):
                self.log("The response for template '{0}' is invalid or empty. Assuming it is already committed.".format(name), "INFO")
                is_template_uncommitted = False
                return is_template_uncommitted

            self.log("Given template '{0}' is not committed in the Cisco Catalyst Center.".format(name), "INFO")
        except Exception as e:
            self.msg = (
                "An exception occurred while retrieving the commit status for template '{0}': {1}"
                .format(name, str(e))
            )
            self.set_operation_result("failed", False, self.msg, "ERROR")
        self.log("Commit status for template '{0}': {1}".format(name, is_template_uncommitted), "DEBUG")

        return is_template_uncommitted

    def update_configuration_templates(self, config, configuration_templates):
        """
        Update/Create templates and projects in CCC with fields provided in Cisco Catalyst Center.

        Parameters:
            config (dict) - Playbook details containing the template, export, import and deploy templates details
            configuration_templates (dict) - Playbook details containing template information.

        Returns:
            self
        """

        is_project_found = self.have_project.get("project_found")
        if not is_project_found:
            project_id, project_created = self.create_project_or_template(
                is_create_project=True
            )
            if not project_created:
                self.status = "failed"
                self.msg = "Project creation failed"
                return self

            self.log("project created with projectId: {0}".format(project_id), "DEBUG")

        is_template_found = self.have_template.get("template_found")
        template_params = self.want.get("template_params")
        self.log("Desired template details: {0}".format(template_params), "DEBUG")
        self.log("Current template details: {0}".format(self.have_template), "DEBUG")
        template_id = None
        self.validate_input_merge(is_template_found).check_return_status()
        if is_template_found:
            current_template_name = self.want.get("template_params").get("name")
            new_template_name = configuration_templates.get("new_template_name")
            template_id = self.have_template.get("id")
            if new_template_name:
                self.log(
                    "User provided 'new_template_name' field. Attempting to change the template name "
                    "from '{template_name}' to '{new_template_name}'.".format(
                        template_name=current_template_name,
                        new_template_name=new_template_name,
                    ),
                    "INFO",
                )
                project_name = configuration_templates.get("project_name")
                self.log(
                    "Checking if template '{new_template_name}' already exists in project '{project_name}'.".format(
                        new_template_name=new_template_name, project_name=project_name
                    ),
                    "DEBUG",
                )
                template_response = self.get_project_defined_template_details(
                    project_name, new_template_name
                )
                if template_response is None:
                    self.msg = "The response of the API 'get_templates_details' for checking template existence is None."
                    self.log(str(self.msg), "WARNING")
                    self.status = "failed"
                    return self
                else:
                    template_response = template_response.get("response")

                if template_response:
                    self.msg = (
                        "Cannot update template name from '{current_template_name}' to '{new_template_name}' "
                        "in project '{project_name}', as a template with the new name already exists in Cisco Catalyst Center.".format(
                            current_template_name=current_template_name,
                            new_template_name=new_template_name,
                            project_name=project_name,
                        )
                    )
                    self.log(str(self.msg), "ERROR")
                    self.status = "failed"
                    return self

                self.log(
                    "Updating template name from '{current_template_name}' to '{new_template_name}'.".format(
                        current_template_name=current_template_name,
                        new_template_name=new_template_name,
                    ),
                    "INFO",
                )
                template_params.update({"name": new_template_name})
                self.want.get("template_params").update({"name": new_template_name})
                config.get("configuration_templates").update(
                    {"template_name": new_template_name}
                )

            if not self.requires_update():
                # Template does not need update
                self.no_update_template.append(current_template_name)
                is_template_un_committed = self.get_template_commit_status(template_id, current_template_name)
                self.log("Template '{0}' uncommitted status: {1}".format(current_template_name, is_template_un_committed), "DEBUG")
                # Check whether the above template is committed or not
                is_commit = configuration_templates.get("commit", True)
                self.log("Commit flag for template '{0}': {1}".format(current_template_name, is_commit), "DEBUG")
                if is_commit and is_template_un_committed:
                    self.commit_the_template(template_id, current_template_name).check_return_status()
                    self.log("Template '{0}' committed successfully in the Cisco Catalyst Center.".format(current_template_name), "INFO")

                return self

            template_id = self.have_template.get("id")
            template_params.update({"id": template_id})
            self.log("Current State (have): {0}".format(self.have_template), "INFO")
            self.log("Desired State (want): {0}".format(self.want), "INFO")
            task_name = "update_template"
            parameters = template_params
            current_response = copy.deepcopy(self.result["response"])
            task_id = self.get_taskid_post_api_call(
                "configuration_templates", task_name, parameters
            )
            template_name = self.want.get("template_params").get("name")
            if not task_id:
                self.msg = "Unable to retrieve the task_id for the task '{0}' for the template: '{1}'.".format(
                    task_name, template_name
                )
                self.set_operation_result(
                    "failed", False, self.msg, "ERROR"
                ).check_return_status()
                return self

            success_msg = "Successfully updated the configuration template '{0}' in Cisco Catalyst Center".format(template_name)
            self.template_updated.append(template_name)
            self.get_task_status_from_tasks_by_id(task_id, task_name, success_msg)
            self.result['response'] = copy.deepcopy(current_response)
            self.log("Updating existing template '{0}'."
                     .format(self.have_template.get("template").get("name")), "INFO")

        else:
            if not template_params.get("name"):
                self.msg = "missing required arguments: template_name"
                self.status = "failed"
                return self
            template_id, template_updated = self.create_project_or_template()

        is_commit = configuration_templates.get("commit", True)
        if is_commit:
            name = self.want.get("template_params").get("name")
            self.log("Attempting to commit template '{0}' with ID '{1}'.".format(name, template_id), "INFO")

            self.commit_the_template(template_id, name).check_return_status()
            self.log("Template '{0}' committed successfully in the Cisco Catalyst Center.".format(name), "INFO")

            self.log("Initiating profile assignment and detachment processing for template '{0}'".format(
                name), "DEBUG")

            # If template was just created, we need to collect profile information now
            current_profiles = self.have.get("current_profile", [])
            if not current_profiles and configuration_templates.get("profile_names"):
                self.log("Template was newly created. Collecting profile information for assignment.", "INFO")
                self.log("Using template_id '{0}' for newly created template '{1}'".format(
                    template_id, name), "DEBUG")
                profile_names = configuration_templates.get("profile_names")
                self.log("Profile names specified for assignment: {0}".format(profile_names), "DEBUG")

                device_types = configuration_templates.get("device_types")
                self.log("Device types specified for profile assignment: {0}".format(device_types), "DEBUG")

                if profile_names and device_types:
                    parsed_current_profile = []
                    for each_type in device_types:
                        each_family = each_type.get("product_family")
                        parsed_current_profile.extend(
                            self.get_profile_details(each_family,
                                                     profile_names,
                                                     name,
                                                     template_id)
                        )
                    current_profiles = self.deduplicate_list_of_dict(parsed_current_profile)
                    self.log("Collected {0} profile(s) for newly created template '{1}' (ID: {2})".format(
                        len(current_profiles), name, template_id), "INFO")

            self.log("Processing {0} profile(s) for template '{1}'.".format(
                len(current_profiles), name), "INFO")

            for profile_index, each_profile in enumerate(current_profiles):
                # Extract profile information once per iteration
                each_profile_name = each_profile.get("profile_name")
                each_profile_id = each_profile.get("profile_id")
                profile_template_name = each_profile.get("template_name")
                profile_template_id = each_profile.get("template_id")
                profile_status = each_profile.get("profile_status")

                # Skip profiles not associated with the current template
                if profile_template_name != name:
                    self.log("Skipping profile '{0}' - not associated with template '{1}' (associated with '{2}')".format(
                        each_profile_name, name, profile_template_name), "DEBUG")
                    continue

                self.log("Processing profile '{0}' (index {1}) with status '{2}' for template '{3}' (ID: {4})".format(
                    each_profile_name, profile_index, profile_status, name, template_id), "DEBUG")

                # Create a unique key using template_id for this profile assignment
                # This prevents duplicates across config iterations and handles templates with same name in different projects
                assignment_key = (template_id, each_profile_name)
                self.log("Generated assignment key for profile '{0}': {1}".format(each_profile_name, assignment_key), "DEBUG")
                # Check if this profile+template combination has already been processed
                if assignment_key in self.processed_profile_assignments:
                    self.log(
                        "Profile '{0}' for template ID '{1}' (name: '{2}') already processed in a previous config entry "
                        "- skipping to avoid duplicate assignment".format(
                            each_profile_name,
                            template_id,
                            name
                        ),
                        "INFO")
                    continue

                # Case 1: Assign profile to template
                if profile_status == "Not Assigned":
                    self.log("Assigning profile '{0}' to template '{1}' - profile not currently assigned".format(
                        each_profile_name, name), "INFO")

                    try:
                        template_status = self.attach_networkprofile_cli_template(
                            each_profile_name, each_profile_id, name, template_id)
                        self.log("Received response from profile attachment API for profile '{0}': {1}".format(
                            each_profile_name, template_status), "DEBUG")

                        if template_status and template_status.get("progress"):
                            success_msg = "Profile '{0}' successfully attached to template '{1}'".format(
                                each_profile_name, name)
                            self.log(success_msg, "INFO")
                            self.profile_assigned.append(each_profile_name)
                            # Mark this assignment as processed
                            self.processed_profile_assignments.add(assignment_key)
                            self.log("Marked assignment key {0} as processed in tracking set".format(
                                assignment_key), "DEBUG")
                        else:
                            error_msg = "Failed to attach profile '{0}' to template '{1}' - API response indicates failure".format(
                                each_profile_name, name)
                            self.log(error_msg, "ERROR")
                            self.no_profile_assigned.append(each_profile_name)

                    except Exception as e:
                        error_msg = "Exception occurred while attaching profile '{0}' to template '{1}': {2}".format(
                            each_profile_name, name, str(e))
                        self.log(error_msg, "ERROR")
                        self.no_profile_assigned.append(each_profile_name)

                # Case 2: Profile already assigned (idempotent case)
                elif profile_status == "already assigned":
                    self.log("Profile '{0}' already assigned to template '{1}' - no action required".format(
                        each_profile_name, name), "DEBUG")
                    # Mark this assignment as processed to avoid duplicate attempts in subsequent iterations
                    self.processed_profile_assignments.add(assignment_key)
                    self.log("Marked pre-existing assignment key {0} as processed in tracking set".format(
                        assignment_key), "DEBUG")

                # Case 3: Unexpected scenario
                else:
                    self.log("Unexpected scenario for profile '{0}' on template '{1}': status='{2}'".format(
                        each_profile_name, name, profile_status), "WARNING")

            # Log summary of operations
            total_assigned = len(getattr(self, 'profile_assigned', []))
            total_assignment_failures = len(getattr(self, 'no_profile_assigned', []))

            self.log("Profile operation summary for template '{0}':".format(name), "INFO")
            self.log("  - Profiles assigned: {0} {1}".format(total_assigned,
                                                             getattr(self, 'profile_assigned', [])), "INFO")
            self.log("  - Assignment failures: {0} {1}".format(total_assignment_failures,
                                                               getattr(self, 'no_profile_assigned', [])), "INFO")
            self.log("  - Total entries in processed_profile_assignments tracking set: {0}".format(
                len(self.processed_profile_assignments)), "DEBUG")

            self.log("Completed profile assignment and processing for template '{0}'".format(name), "INFO")

        return self

    def get_latest_template_version_id(self, template_id, template_name):
        """
        Fetches the latest version ID of a specified template from the Cisco Catalyst Center.

        Args:
            self (object): An instance of the class interacting with Cisco Catalyst Center.
            template_id (str): The unique identifier of the template to retrieve its versions.
            template_name (str): The name of the template for logging and reference purposes.
        Returns:
            str: The ID of the latest version of the template if available; otherwise, returns None.
        Description:
            This method calls the Cisco Catalyst Center API to fetch all versions of the specified template.
            It selects the version with the most recent timestamp and retrieves its version ID.
            If no versions are available or an error occurs during the API call, appropriate logs are generated.
        """
        version_temp_id = None
        self.log(
            "Fetching the latest version ID for template '{0}' using template_id '{1}'.".format(
                template_name, template_id
            ),
            "DEBUG",
        )

        try:
            response = self.catalystcenter._exec(
                family="configuration_templates",
                function="get_template_versions",
                op_modifies=True,
                params={
                    "template_id": template_id,
                },
            )
            self.log(
                "Received Response for 'get_template_versions' for template_name: {0} is {1}".format(
                    template_name, response
                ),
                "DEBUG",
            )
            self.log("Received Response for 'get_template_versions' for template_name: {0} is {1}".format(template_name, response), "DEBUG")
            response = response.get("response")

            if not response or not isinstance(response, list):
                self.log(
                    "No version information found for template '{0}' in Cisco Catalyst Center.".format(
                        template_name
                    ),
                    "INFO",
                )
                return version_temp_id

            self.log(
                "Successfully retrieved version information for template '{0}'.".format(
                    template_name
                ),
                "DEBUG",
            )

            version_temp_id = response[0].get("versionId")
            if not version_temp_id:
                self.log(
                    "Failed to identify the latest version for template '{0}'. 'versionId' key is missing in the response.".format(
                        template_name
                    ), "ERROR"
                )
                self.msg = "Missing 'versionId' in the response for the template '{0}'.".format(template_name)
                self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

            self.log(
                "Identified the latest version for template '{0}'. Version ID: {1}".format(
                    template_name, version_temp_id), "DEBUG"
            )
            return version_temp_id

        except Exception as e:
            error_message = "Error while getting the latest version id for the template '{0}': '{1}'".format(
                template_name, str(e)
            )
            self.log(error_message, "CRITICAL")

        self.log(
            "Returning latest version ID '{0}' for template '{1}'.".format(
                version_temp_id, template_name
            ),
            "DEBUG",
        )

        return version_temp_id

    def get_device_hostname_from_device_id(self, device_id):
        """
        Retrieves the hostname of a network device using its device UUID.

        Args:
            self (object): An instance of the class interacting with Cisco Catalyst Center.
            device_id (str): UUID of the network device for which the hostname is to be fetched.

        Returns:
            str or None: The hostname of the device if found; otherwise, returns None.

        Description:
            This method fetches the hostname of a specific network device by invoking the
            `get_device_list` API function with the device UUID as a parameter. It parses the
            response to extract the hostname. Logs are maintained for traceability, and exceptions
            are properly handled to avoid runtime failures in case of API errors or invalid inputs.
        """

        device_hostname = None
        self.log("Fetching device hostname for device_id: {0}".format(device_id), "INFO")
        try:
            response = self.catalystcenter._exec(
                family="devices",
                function='get_device_list',
                op_modifies=True,
                params={"id": device_id}
            )
            self.log("Received API response for 'get_device_list' for device {0}: {1}".format(device_id, str(response)), "DEBUG")
            response = response.get("response")
            if not response:
                self.log("No device found with ID: {0}".format(device_id), "WARNING")
                return None

            if "hostname" not in response[0]:
                self.log("Hostname key missing in the API response for device_id: {0}".format(device_id), "ERROR")
                return None

            device_hostname = response[0].get("hostname")
        except Exception as e:
            self.msg = "Exception occurred while fetching device hostname for device_id '{0}': {1}".format(device_id, str(e))
            self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

        self.log("Device hostname for device_id '{0}' is '{1}'.".format(device_id, device_hostname), "INFO")

        return device_hostname

    def get_site_uuid_from_device_id(self, device_id):
        """
        Fetches the Site UUID associated with a given network device UUID.

        Args:
            self (object): An instance of the class interacting with Cisco Catalyst Center.
            device_id (str): UUID of the network device for which the site assignment is to be retrieved.
        Returns:
            str or None: Returns the UUID of the assigned site if found; otherwise, returns None.
        Description:
            This method checks the site assignment for a given network device by making an API call
            using the `get_site_assigned_network_device` function. If the device is assigned to a site,
            the corresponding site UUID is extracted and returned. Logs are generated at each step for
            traceability, and proper exception handling ensures that any issues are logged and reported
            without breaking execution flow.
        """

        self.log("Checking site assignment for device with UUID: {0}".format(device_id), "INFO")
        site_uuid = None
        try:
            response = self.catalystcenter_apply['exec'](
                family="site_design",
                function='get_site_assigned_network_device',
                params={"id": device_id}
            )

            self.log("API response received for 'get_site_assigned_network_device': {0}".format(response), "DEBUG")
            if not response or not isinstance(response, dict):
                self.log("No site assignment found for device with UUID: {0}".format(device_id), "WARNING")
                return site_uuid

            response = response.get("response")
            if not isinstance(response, dict):
                self.log("Unexpected 'response' format for device with UUID: {0}".format(device_id), "WARNING")
                return None

            # Extract site details
            site_uuid = response.get("siteId")
            site_name = response.get("siteNameHierarchy")

            if not site_uuid:
                self.log("No site assignment found for device with UUID: {0}".format(device_id), "WARNING")
                return None

            self.log(
                "Device with UUID {0} is assigned to site: {1} (siteId: {2})".format(device_id, site_name, site_uuid), "INFO"
            )
            return site_uuid

        except Exception as e:
            self.msg = "Exception occurred while fetching site assignment for device with UUID '{0}': {1}".format(device_id, str(e))
            self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

    def create_payload_for_template_deploy(self, deploy_temp_details, device_ids):
        """
        Creates a payload for deploying a template to specified devices in the Cisco Catalyst Center.

        Args:
            self (object): An instance of the class interacting with Cisco Catalyst Center.
            deploy_temp_details (dict): A dictionary containing details about the template to be deployed.
            device_ids (list): A list of device UUIDs to which the template should be deployed.
        Returns:
            dict: A dictionary representing the payload required to deploy the template.
        Description:
            This function generates the necessary payload for deploying a template to devices in the Cisco Catalyst Center.
            It first checks if the given template is already committed. If not, it fetches its uncommitted version, commits it,
            and uses its template ID for deployment. The payload includes information about target devices and their respective
            template parameters.
            The function logs appropriate messages during the process, including if a template is already committed, if
            parameters are updated, and when the payload is successfully collected.
        """

        project_name = deploy_temp_details.get("project_name")
        template_name = deploy_temp_details.get("template_name")
        self.log(
            "Starting to create deployment payload for template '{0}' in project '{1}'.".format(
                template_name, project_name
            ),
            "DEBUG",
        )
        # Check if the template is available but not yet committed
        if self.have.get("temp_id"):
            self.log(
                "Template '{0}' is already committed in Cisco Catalyst Center. Using the committed template ID.".format(
                    template_name
                ),
                "INFO",
            )
            template_id = self.have.get("temp_id")
        else:
            self.log(
                "Fetching uncommitted template ID for template '{0}' in project '{1}'.".format(
                    template_name, project_name
                ),
                "DEBUG",
            )
            template_id = self.get_uncommitted_template_id(project_name, template_name)

            if not template_id:
                self.msg = (
                    "Unable to fetch the details for the template '{0}' from the Cisco "
                    "Catalyst Center."
                ).format(template_name)
                self.set_operation_result(
                    "failed", False, self.msg, "ERROR"
                ).check_return_status()

            self.log(
                "Template '{0}' is available but not committed yet. Committing template...".format(
                    template_name
                ),
                "INFO",
            )

            # Commit or versioned the given template in the Catalyst Center
            self.versioned_given_template(
                project_name, template_name, template_id
            ).check_return_status()

        is_composite = deploy_temp_details.get("is_composite", False)
        self.log(
            "Preparing deployment payload for"
            " template '{0}', is_composite={1}.".format(
                template_name, is_composite),
            "DEBUG",
        )
        member_deployments = []

        self.log(
            "Preparing deployment payload for"
            " template '{0}', is_composite={1}.".format(
                template_name, is_composite),
            "DEBUG",
        )
        deploy_payload = {
            "forcePushTemplate": deploy_temp_details.get("force_push", False),
            "isComposite": is_composite,
            "templateId": template_id,
            "copyingConfig": deploy_temp_details.get("copy_config", True),
        }

        # For composite templates, set mainTemplateId and build memberTemplateDeploymentInfo
        if is_composite:
            self.log(
                "Processing composite template deployment"
                " for template '{0}'.".format(template_name),
                "INFO",
            )
            deploy_payload["mainTemplateId"] = template_id
            # Resolve versioned template ID for the composite parent
            composite_version_id = self.get_latest_template_version_id(template_id, template_name)
            self.log(
                "Resolved composite template '{0}'"
                " version ID: '{1}'.".format(
                    template_name,
                    composite_version_id or template_id),
                "DEBUG",
            )

            if composite_version_id:
                deploy_payload["templateId"] = composite_version_id

            member_info_list = deploy_temp_details.get("member_template_deployment_info", [])
            if not member_info_list:
                self.msg = (
                    "Composite template '{0}' requires 'member_template_deployment_info' "
                    "to be provided in the playbook."
                ).format(template_name)
                self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

            for idx, member in enumerate(member_info_list):
                member_template_name = member.get("template_name")
                self.log(
                    "Processing member template {0}/{1}"
                    " with name '{2}' for composite"
                    " template '{3}'.".format(
                        idx + 1, len(member_info_list),
                        member_template_name, template_name),
                    "DEBUG",
                )
                if not member_template_name:
                    self.msg = (
                        "Each entry in 'member_template_deployment_info' must include a 'template_name' "
                        "for composite template '{0}'."
                    ).format(template_name)
                    self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

                member_project_name = member.get("project_name") or project_name
                member_response = self.get_project_defined_template_details(
                    member_project_name, member_template_name
                )
                member_templates = member_response.get("response") if member_response else None
                if not member_templates or not isinstance(member_templates, list):
                    self.msg = (
                        "Member template '{0}' not found under project '{1}' or it is not versioned."
                    ).format(member_template_name, member_project_name)
                    self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

                member_template_id = member_templates[0].get("id")
                if not member_template_id:
                    self.msg = (
                        "Member template '{0}' under"
                        " project '{1}' has no valid ID."
                    ).format(
                        member_template_name, member_project_name
                    )
                    self.set_operation_result(
                        "failed", False, self.msg, "ERROR"
                    ).check_return_status()
                self.log("Resolved member template '{0}' to ID '{1}'.".format(
                    member_template_name, member_template_id), "DEBUG")

                member_version_id = self.get_latest_template_version_id(member_template_id, member_template_name)
                if not member_version_id:
                    member_version_id = member_template_id

                member_params = {}
                member_template_params = member.get("template_parameters", [])
                for idx, param in enumerate(member_template_params):
                    self.log(
                        "Processing parameter {0}/{1} for"
                        " member template '{2}'.".format(
                            idx + 1, len(member_template_params),
                            member_template_name),
                        "DEBUG",
                    )
                    p_name = param.get("param_name")
                    p_value = param.get("param_value")

                    if not p_name:
                        self.msg = (
                            "Each template parameter in member"
                            " template '{0}' must include"
                            " 'param_name'."
                        ).format(member_template_name)
                        self.set_operation_result(
                            "failed", False, self.msg, "ERROR"
                        ).check_return_status()

                    member_params[p_name] = p_value

                member_deploy = {
                    "forcePushTemplate": member.get("force_push_template", True),
                    "isComposite": False,
                    "templateId": member_version_id,
                    "copyingConfig": member.get("copy_config", True),
                    "targetInfo": [],
                }

                member_deployments.append({
                    "deploy": member_deploy,
                    "params": member_params,
                    "version_id": member_version_id,
                })

            self.log("Built {0} member template deployment entries for composite template '{1}'.".format(
                len(member_deployments), template_name), "DEBUG")
        self.log(
            "Handling template parameters for the deployment of template '{0}'.".format(
                template_name
            ),
            "DEBUG",
        )
        target_info_list = []
        template_dict = {}
        template_parameters = deploy_temp_details.get("template_parameters", [])

        for param in template_parameters:
            name = param["param_name"]
            value = param["param_value"]
            self.log(
                "Update the template placeholder for the name '{0}' with value {1}".format(
                    name, value
                ),
                "DEBUG",
            )
            template_dict[name] = value

        # Get the latest version template ID (only needed for non-composite deployments)
        version_template_id = None
        if not is_composite:
            version_template_id = self.get_latest_template_version_id(template_id, template_name)
            if not version_template_id:
                self.log(
                    "Using base template ID for '{0}' — no committed version found in Catalyst Center.".format(template_name),
                    "INFO",
                )
                version_template_id = template_id

        self.log("Preparing to deploy template '{0}' to the following device IDs: '{1}'".format(template_name, device_ids), "DEBUG")
        for device_id in device_ids:
            self.log(
                "Adding device '{0}' to the deployment payload.".format(device_id),
                "DEBUG",
            )
            target_device_dict = {
                "id": device_id,
                "type": "MANAGED_DEVICE_UUID",
                "params": template_dict,
            }
            if not is_composite:
                target_device_dict["versionedTemplateId"] = version_template_id
            resource_params = deploy_temp_details.get("resource_parameters")
            self.log("Handling resource parameters for the deployment of template '{0}'.".format(template_name), "DEBUG")
            resource_params_list = []
            runtime_scopes_available = ["MANAGED_DEVICE_UUID", "MANAGED_DEVICE_IP", "MANAGED_DEVICE_HOSTNAME", "SITE_UUID"]
            self.log("Available runtime scopes for resource parameters: {0}".format(runtime_scopes_available), "DEBUG")
            if resource_params:
                for resource_param in resource_params:
                    r_type = resource_param.get("resource_type")
                    scope = resource_param.get("resource_scope", "RUNTIME")
                    resource_params_dict = {
                        'type': r_type,
                        'scope': scope
                    }
                    if scope == "RUNTIME":
                        # Validate runtime scope type
                        if r_type not in runtime_scopes_available:
                            self.msg = (
                                "The resource type '{0}' with scope '{1}' is not supported for runtime provisioning. "
                                "Supported types are: {2}."
                            ).format(r_type, scope, ", ".join(runtime_scopes_available))
                            self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

                        self.log(
                            "Processing resource parameter with type '{0}' and scope '{1}' for runtime"
                            " provisioning.".format(r_type, scope), "DEBUG"
                        )
                        if r_type == "SITE_UUID":
                            value = self.get_site_uuid_from_device_id(device_id)
                        elif r_type == "MANAGED_DEVICE_UUID":
                            value = device_id
                        elif r_type == "MANAGED_DEVICE_IP":
                            device_ip_id_map = self.get_device_ips_from_device_ids([device_id])
                            value = device_ip_id_map[device_id]
                        elif r_type == "MANAGED_DEVICE_HOSTNAME":
                            value = self.get_device_hostname_from_device_id(device_id)

                        resource_params_dict['value'] = value
                        self.log("Update the resource placeholder for the type '{0}' with scope {1}".format(r_type, scope), "DEBUG")
                        resource_params_list.append(resource_params_dict)
                        continue

                    # If the scope is not RUNTIME, we take the value directly from the resource_param dictionary
                    self.log("Processing resource parameter with type '{0}' and scope '{1}'.".format(r_type, scope), "DEBUG")
                    value = resource_param.get("resource_value")
                    if not value:
                        self.msg = (
                            "The resource type '{0}' with scope '{1}' requires a value to be provided. "
                            "Please specify a value for this resource parameter."
                        ).format(r_type, scope)
                        self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

                    resource_params_dict['value'] = value
                    self.log("Update the resource placeholder for the type '{0}' with scope {1}".format(r_type, scope), "DEBUG")
                    resource_params_list.append(resource_params_dict)

            if resource_params_list:
                self.log(
                    "Adding resource parameters to the target device dictionary for template '{0}'.".format(
                        template_name
                    ),
                    "DEBUG",
                )
                target_device_dict["resourceParams"] = resource_params_list

            target_info_list.append(target_device_dict)
            del target_device_dict

        deploy_payload["targetInfo"] = target_info_list

        # For composite templates, populate memberTemplateDeploymentInfo with per-device target info
        if is_composite:
            member_template_deployment_info = []
            for idx, member_entry in enumerate(member_deployments):
                self.log(
                    "Building target info for member"
                    " deployment {0}/{1}, templateId"
                    " '{2}'.".format(
                        idx + 1, len(member_deployments),
                        member_entry.get("version_id")),
                    "DEBUG",
                )
                member_deploy = member_entry["deploy"]
                member_params = member_entry["params"]
                member_version_id = member_entry["version_id"]
                member_resource_params = deploy_temp_details.get("resource_parameters", [])

                member_target_info_list = []
                for dev_idx, device_id in enumerate(device_ids):
                    self.log(
                        "Preparing member deployment target"
                        " {0}/{1} for device_id '{2}'"
                        " in member template"
                        " '{3}'.".format(
                            dev_idx + 1, len(device_ids),
                            device_id,
                            member_deploy.get("templateId")),
                        "DEBUG",
                    )
                    member_target = {
                        "id": device_id,
                        "type": "MANAGED_DEVICE_UUID",
                        "params": member_params,
                    }

                    member_res_list = []
                    runtime_scopes_available = ["MANAGED_DEVICE_UUID", "MANAGED_DEVICE_IP", "MANAGED_DEVICE_HOSTNAME", "SITE_UUID"]
                    for res_idx, resource_param in enumerate(member_resource_params):
                        r_type = resource_param.get("resource_type")
                        self.log(
                            "Resolving resource param"
                            " {0}/{1} type='{2}' for"
                            " device '{3}'.".format(
                                res_idx + 1,
                                len(member_resource_params),
                                r_type, device_id),
                            "DEBUG",
                        )
                        scope = resource_param.get("resource_scope", "RUNTIME")
                        resource_params_dict = {"type": r_type, "scope": scope}
                        if scope == "RUNTIME":
                            if r_type not in runtime_scopes_available:
                                self.msg = (
                                    "The resource type '{0}' with scope '{1}' is not supported for runtime provisioning. "
                                    "Supported types are: {2}."
                                ).format(r_type, scope, ", ".join(runtime_scopes_available))
                                self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

                            if r_type == "SITE_UUID":
                                value = self.get_site_uuid_from_device_id(device_id)
                            elif r_type == "MANAGED_DEVICE_UUID":
                                value = device_id
                            elif r_type == "MANAGED_DEVICE_IP":
                                device_ip_id_map = self.get_device_ips_from_device_ids([device_id])
                                value = device_ip_id_map[device_id]
                            elif r_type == "MANAGED_DEVICE_HOSTNAME":
                                value = self.get_device_hostname_from_device_id(device_id)

                            resource_params_dict['value'] = value
                            member_res_list.append(resource_params_dict)
                            self.log("Resolved runtime resource parameter '{0}' with scope '{1}' to value '{2}' for device '{3}'.".format(
                                r_type, scope, value, device_id), "DEBUG")
                            continue

                        self.log("Processing resource parameter with type '{0}' and scope '{1}'.".format(r_type, scope), "DEBUG")
                        value = resource_param.get("resource_value")
                        if not value:
                            self.msg = (
                                "The resource type '{0}' with scope '{1}' requires a value to be provided. "
                                "Please specify a value for this resource parameter."
                            ).format(r_type, scope)
                            self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

                        resource_params_dict["value"] = value
                        member_res_list.append(resource_params_dict)

                    if member_res_list:
                        member_target["resourceParams"] = member_res_list
                    member_target_info_list.append(member_target)

                member_deploy["targetInfo"] = member_target_info_list
                member_template_deployment_info.append(member_deploy)

            deploy_payload["memberTemplateDeploymentInfo"] = member_template_deployment_info
            self.log("Added {0} member template deployment info entries to composite payload.".format(
                len(member_template_deployment_info)), "DEBUG")

        self.log(
            "Successfully generated deployment payload for template '{0}'.".format(
                template_name
            ),
            "INFO",
        )
        self.log("Final deployment payload for template '{0}': {1}".format(template_name, deploy_payload), "DEBUG")
        return deploy_payload

    def monitor_template_deployment_status(
        self, template_name, deployment_id, device_ips
    ):
        """
        Monitors the status of a template deployment in Cisco Catalyst Center until it completes
        successfully, fails, or times out.

        Args:
            self (object): An instance of the class interacting with Cisco Catalyst Center.
            template_name (str): Name of the configuration template being deployed.
            deployment_id (str): Unique identifier for the deployment task.
            device_ips (list): List of IP addresses of devices to which the template is being deployed.
        Description:
            This method continuously polls the deployment status of a configuration template applied
            to one or more devices using the Cisco Catalyst Center API. It logs status updates, handles
            failures, and manages timeout conditions. Upon successful deployment, it marks the
            operation as successful; otherwise, it collects and logs failure reasons and exits
            accordingly.
        """

        loop_start_time = time.time()
        self.log(
            "Starting template deployment monitoring for '{0}' with deployment ID '{1}', targeting"
            " devices: {2}.".format(template_name, deployment_id, device_ips),
            "DEBUG",
        )
        self.log(
            "Starting template deployment monitoring for '{0}' with deployment ID '{1}'.".format(
                template_name, deployment_id
            ),
            "DEBUG",
        )

        while True:
            try:
                task_name = "get_template_deployment_status"
                response = self.catalystcenter._exec(
                    family="configuration_templates",
                    function=task_name,
                    params={"deployment_id": deployment_id},
                    op_modifies=True,
                )
                self.log(
                    "API response received for task '{0}'. Deployment ID: '{1}', Response: {2}".format(
                        task_name, deployment_id, response
                    ),
                    "DEBUG",
                )

                if not isinstance(response, dict):
                    self.log(
                        "Error: Received invalid response type for deployment ID: '{0}'. Expected a dictionary but got: {1}".format(
                            deployment_id, type(response).__name__
                        ),
                        "ERROR",
                    )
                    self.set_operation_result("failed", False, self.msg, "ERROR")
                    return self

                deployment_status = response.get("status")
                self.log(
                    "Deployment status for template '{0}': {1}".format(
                        template_name, deployment_status
                    ),
                    "DEBUG",
                )
                if deployment_status == "SUCCESS":
                    self.msg = (
                        "Given template '{0}' deployed successfully to all the device(s) '{1}' "
                        " in the Cisco Catalyst Center."
                    ).format(template_name, device_ips)
                    self.set_operation_result("success", True, self.msg, "INFO")
                    return self

                if deployment_status == "FAILURE":
                    self.log(
                        "Deployment of template '{0}' failed. Retrieving detailed failure messages...".format(
                            template_name
                        ),
                        "ERROR",
                    )
                    devices = response.get("devices", [])
                    failure_msg = []
                    for device in devices:
                        status_msg = device.get(
                            "detailedStatusMessage", "No detailed status available."
                        )
                        self.log(
                            "Device deployment failure: {0}".format(status_msg), "ERROR"
                        )
                        failure_msg.append(status_msg)

                    failure_reason = "Deployment of the template '{0}' failed on devices {1} with the following reason(s): {2}".format(
                        template_name, device_ips, ", ".join(failure_msg)
                    )
                    self.msg = failure_reason
                    self.set_operation_result("failed", False, self.msg, "ERROR")
                    return self

                # Check if the elapsed time exceeds the timeout
                elapsed_time = time.time() - loop_start_time
                if self.check_timeout_and_exit(
                    loop_start_time, deployment_id, task_name
                ):
                    self.log(
                        "Timeout exceeded after {0:.2f} seconds while monitoring deployment task '{1}'. Deployment ID: '{2}'.".format(
                            elapsed_time, task_name, deployment_id
                        ),
                        "DEBUG",
                    )
                    self.check_return_status()

                # Wait for the specified poll interval before the next check
                poll_interval = self.params.get("catalystcenter_task_poll_interval")
                self.log(
                    "Waiting for the next poll interval of {0} seconds before checking deployment status again.".format(
                        poll_interval
                    ),
                    "DEBUG",
                )
                time.sleep(poll_interval)

            except Exception as e:
                self.msg = (
                    "An unexpected error occurred during API call for task '{0}'. Deployment ID: '{1}'. "
                    "Exception: {2}".format(task_name, deployment_id, str(e))
                )
                self.fail_and_exit(self.msg)

    def deploy_template_to_devices(
        self, deploy_temp_payload, template_name, device_ips
    ):
        """
        Deploys a specified template to devices associated with a site in the Cisco Catalyst Center.

        Args:
            self (object): An instance of the class used for interacting with Cisco Catalyst Center.
            deploy_temp_payload (dict): The payload containing the details required to deploy the template.
                This includes the template ID, device details, and template parameters.
            template_name (str): The name of the template to be deployed.
            device_ips (list): The management ip address of the devices to which template will be deployed.
        Returns:
            self (object): The instance of the class itself, with the operation result (success or failure)
            set accordingly.
        Description:
            This function handles the deployment of a template to a set of devices managed in the Cisco Catalyst Center.
            It sends a POST request with the deployment payload and retrieves the task ID associated with the deployment task.
            It then monitors the status of the task using the task ID and logs the result.
            If the task ID is not retrieved or an exception occurs during deployment, the function logs an error message,
            sets the operation result to "failed," and returns the instance.
            The success message indicates that the template has been successfully deployed to all the devices in the specified
            site, while any exceptions are caught and logged with appropriate details.
        """

        try:
            self.log(
                "Deploying the given template {0} to the device(s) {1}.".format(
                    template_name, device_ips
                )
            )
            payload = {"payload": deploy_temp_payload}
            task_name = "deploy_template_v2"
            task_id = self.get_taskid_post_api_call(
                "configuration_templates", task_name, payload
            )

            if not task_id:
                self.msg = "Unable to retrieve the task_id for the task '{0}'.".format(
                    task_name
                )
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self

            loop_start_time = time.time()
            sleep_duration = self.params.get("catalystcenter_task_poll_interval")
            self.log(
                "Starting task monitoring for '{0}' with task ID '{1}'.".format(
                    task_name, task_id
                ),
                "DEBUG",
            )

            while True:
                task_details = self.get_task_details_by_id(task_id)
                if not task_details:
                    self.msg = "Error retrieving task status for '{0}' with task ID '{1}'".format(
                        task_name, task_id
                    )
                    self.set_operation_result("failed", False, self.msg, "ERROR")
                    return self

                # Check if the elapsed time exceeds the timeout
                elapsed_time = time.time() - loop_start_time
                if self.check_timeout_and_exit(loop_start_time, task_id, task_name):
                    self.log(
                        "Timeout exceeded after {0:.2f} seconds while monitoring task '{1}' with task ID '{2}'.".format(
                            elapsed_time, task_name, task_id
                        ),
                        "DEBUG",
                    )
                    return self

                progress = task_details.get("progress")
                self.log(
                    "Task ID '{0}' progress details retrieved from API '{1}'. Progress: '{2}'.".format(
                        task_id, task_name, progress
                    ),
                    "DEBUG",
                )
                # Get the deployment id of the template if it get deployed successfully on the devices
                self.log(
                    "Searching for the Deployment ID in the task progress message using regex...",
                    "DEBUG",
                )
                match = re.search(
                    r"Template\s+Deployment\s+Id:\s+([a-f0-9\-]+)",
                    progress,
                    re.IGNORECASE,
                )
                deployment_id = None
                if match:
                    deployment_id = match.group(1)
                    if deployment_id:
                        self.log(
                            "Deployment ID found in the progress message. Template Deployment ID: '{0}'.".format(
                                deployment_id
                            ),
                            "DEBUG",
                        )
                        self.log(
                            "Proceeding to monitor the deployment with Deployment ID: '{0}'.".format(
                                deployment_id
                            ),
                            "DEBUG",
                        )
                        self.monitor_template_deployment_status(
                            template_name, deployment_id, device_ips
                        ).check_return_status()
                        self.log(
                            "Deployment monitoring completed"
                            " for template '{0}' with"
                            " deployment ID '{1}'."
                            " Returning.".format(
                                template_name,
                                deployment_id),
                            "INFO",
                        )
                        return self
                    else:
                        self.log(
                            "Regex matched the progress message, but no Deployment ID was captured. "
                            "This could indicate an issue with the progress message or the regex pattern. Progress: '{0}'.".format(
                                progress
                            ),
                            "ERROR",
                        )
                else:
                    self.log(
                        "Deployment ID not found in the progress message for template '{0}'. Progress message: '{1}'.".format(
                            template_name, progress
                        ),
                        "DEBUG",
                    )

                # Check for task-level success even without a deployment ID
                is_task_end = task_details.get("isError")
                if is_task_end is False and "endTime" in task_details and task_details.get("endTime"):
                    self.msg = (
                        "Given template '{0}' deployed successfully to all the device(s) '{1}' "
                        " in the Cisco Catalyst Center."
                    ).format(template_name, device_ips)
                    self.set_operation_result("success", True, self.msg, "INFO")
                    return self

                if "already deployed with same params" in progress:
                    self.msg = "Template '{0}' is already deployed with the same parameters. No deployment actions will be performed.".format(
                        template_name
                    )
                    self.log(self.msg, "INFO")
                    self.set_operation_result("success", False, self.msg, "INFO")
                    return self

                failure_reason = task_details.get("failureReason")
                if failure_reason:
                    self.log(
                        "Deployment of the template '{0}' failed. Failure reason: '{1}'. No further actions will be taken.".format(
                            template_name, failure_reason
                        ),
                        "ERROR",
                    )
                    self.msg = failure_reason
                    self.set_operation_result("failed", False, self.msg, "ERROR")
                    return self

                if "not deploying" in progress:
                    self.log(
                        "Deployment of the template {0} gets failed because of: {1}".format(
                            template_name, progress
                        ),
                        "WARNING",
                    )
                    self.msg = progress
                    self.set_operation_result("failed", False, self.msg, "ERROR")
                    return self

                if "ApplicableTargets" in progress:
                    self.msg = (
                        "Given template '{0}' deployed successfully to all the device(s) '{1}' "
                        " in the Cisco Catalyst Center."
                    ).format(template_name, device_ips)
                    self.set_operation_result("success", True, self.msg, "INFO")
                    return self

                self.log(
                    "Waiting for {0} seconds before checking the task status again.".format(
                        sleep_duration
                    ),
                    "DEBUG",
                )
                time.sleep(sleep_duration)

        except Exception as e:
            self.msg = (
                "An exception occurred while deploying the template '{0}' to the device(s) {1} "
                " in the Cisco Catalyst Center: {2}."
            ).format(template_name, device_ips, str(e))
            self.set_operation_result("failed", False, self.msg, "ERROR")

        return self

    def get_device_ips_from_config_priority(self, device_details):
        """
        Retrieve device IPs based on the configuration.
        Parameters:
            -  self (object): An instance of a class used for interacting with Cisco Cisco Catalyst Center.
        Returns:
            list: A list containing device IPs.
        Description:
            This method retrieves device IPs based on the priority order specified in the configuration.
            It first checks if device IPs are available. If not, it checks hostnames, serial numbers,
            and MAC addresses in order and retrieves IPs based on availability.
            If none of the information is available, an empty list is returned.
        """
        # Retrieve device IPs from the configuration
        self.log(
            "Retrieving device IPs based on the configuration priority with details: {0}".format(
                device_details
            ),
            "INFO",
        )
        try:
            device_ips = device_details.get("device_ips")
            if device_ips and not isinstance(device_ips, list):
                self.msg = "Device IPs should be a list, but got: {0}".format(type(device_ips).__name__)
                self.set_operation_result("failed", False, self.msg, "ERROR").check_return_status()

            if device_ips:
                self.log("Found device IPs: {0}".format(device_ips), "INFO")
                return device_ips

            # If device IPs are not available, check hostnames
            device_hostnames = device_details.get("device_hostnames")
            if device_hostnames:
                self.log(
                    "No device IPs found. Checking hostnames: {0}".format(
                        device_hostnames
                    ),
                    "INFO",
                )
                device_ip_dict = self.get_device_ips_from_hostnames(device_hostnames)
                return self.get_list_from_dict_values(device_ip_dict)

            # If hostnames are not available, check serial numbers
            device_serial_numbers = device_details.get("serial_numbers")
            if device_serial_numbers:
                self.log(
                    "No device IPs or hostnames found. Checking serial numbers: {0}".format(
                        device_serial_numbers
                    ),
                    "INFO",
                )
                device_ip_dict = self.get_device_ips_from_serial_numbers(
                    device_serial_numbers
                )
                return self.get_list_from_dict_values(device_ip_dict)

            # If serial numbers are not available, check MAC addresses
            device_mac_addresses = device_details.get("mac_addresses")
            if device_mac_addresses:
                self.log(
                    "No device IPs, hostnames, or serial numbers found. Checking MAC addresses: {0}".format(
                        device_mac_addresses
                    ),
                    "INFO",
                )
                device_ip_dict = self.get_device_ips_from_mac_addresses(
                    device_mac_addresses
                )
                return self.get_list_from_dict_values(device_ip_dict)

            # If no information is available, return an empty list
            self.log("No device information available to retrieve IPs.", "WARNING")
            return []

        except Exception as e:
            self.log("No device information available to retrieve IPs.", "WARNING")
            return []

    def update_template_projects_message(self):
        """
        Updates the result message and change status based on the outcomes of project and template operations.

        Args:
            self (object): An instance of the class used for interacting with Cisco Catalyst Center.

        Returns:
            object: Returns the current instance (`self`) with updated `result` and `msg` fields.

        Description:
            This method checks various internal flags (such as whether a project or template was created, updated,
            or committed) and builds a descriptive message accordingly. It updates the result dictionary with a
            `changed` flag and constructs a human-readable summary message about the performed operations.
            The message is stored in `self.msg`, and the result is logged via `set_operation_result`.
        """

        self.result["changed"] = False
        result_msg_list = []
        if self.project_created:
            create_project_msg = "Project '{0}' created successfully in the Cisco Catalyst Center.".format(self.project_created)
            result_msg_list.append(create_project_msg)

        if self.template_created:
            create_template_msg = "Template '{0}' created successfully in the Cisco Catalyst Center.".format(self.template_created)
            result_msg_list.append(create_template_msg)

        if self.template_updated:
            update_template_msg = "Template '{0}' updated successfully in the Cisco Catalyst Center.".format(self.template_updated)
            result_msg_list.append(update_template_msg)

        if self.no_update_template:
            no_update_template_msg = (
                "No changes detected in the template '{0}' so not updating it in the Cisco Catalyst Center."
            ).format(self.no_update_template)
            result_msg_list.append(no_update_template_msg)

        if self.template_committed:
            commit_template_msg = "Template '{0}' committed successfully in the Cisco Catalyst Center.".format(self.template_committed)
            result_msg_list.append(commit_template_msg)

        if self.profile_assigned:
            profile_assign_msg = "Profile(s) '{0}' assigned successfully to the template.".format(str(
                self.profile_assigned))
            result_msg_list.append(profile_assign_msg)

        if self.no_profile_assigned:
            no_profile_assign_msg = "Unable to assign the profile(s) '{0}' to the template.".format(str(
                self.no_profile_assigned))
            result_msg_list.append(no_profile_assign_msg)

        if (self.profile_exists and not self.profile_detached
           and not self.profile_not_detached and not self.profile_already_detached):
            profile_exists_msg = "Profile(s) '{0}' already exist and cannot be assigned to the template.".format(str(
                self.profile_exists))
            result_msg_list.append(profile_exists_msg)

        if self.profile_detached:
            profile_detach_msg = "Profile(s) '{0}' detached successfully from the template.".format(str(
                self.profile_detached))
            result_msg_list.append(profile_detach_msg)

        if self.profile_not_detached:
            profile_not_detach_msg = "Profile(s) '{0}' could not be detached from the template.".format(str(
                self.profile_not_detached))
            result_msg_list.append(profile_not_detach_msg)

        if self.profile_already_detached:
            profile_already_detach_msg = "Profile(s) '{0}' were already detached from the template.".format(str(
                self.profile_already_detached))
            result_msg_list.append(profile_already_detach_msg)

        if (
            self.project_created or self.template_created or self.template_updated
            or self.template_committed or self.profile_assigned or self.profile_detached
        ):
            self.result["changed"] = True

        self.msg = " ".join(result_msg_list)
        self.set_operation_result("success", self.result["changed"], self.msg, "INFO")

        return self

    def verify_diff_merged(self, config):
        """
        Validating the Cisco Catalyst Center configuration with the playbook details
        when state is merged (Create/Update).

        Parameters:
            config (dict) - Playbook details containing Global Pool,
            Reserved Pool, and Network Management configuration.

        Returns:
            self
        """

        if config.get("configuration_templates") is not None:
            is_template_available = self.get_have_project(config)
            self.log("Template availability: {0}".format(is_template_available), "INFO")
            if not is_template_available:
                self.msg = "Configuration Template config is not applied to the Cisco Catalyst Center."
                self.status = "failed"
                return self

            self.get_have_template(config, is_template_available)
            self.log(
                "Desired State (want): {0}".format(self.want.get("template_params")),
                "INFO",
            )
            self.log(
                "Current State (have): {0}".format(self.have_template.get("template")),
                "INFO",
            )
            if not self.have_template.get("template"):
                self.msg = "No template created with the name '{0}'".format(
                    self.want.get("template_params").get("name")
                )
                self.status = "failed"
                return self

            template_params = [
                "language",
                "name",
                "projectName",
                "softwareType",
                "templateContent",
            ]
            have_template = self.have_template.get("template")
            want_template = self.want.get("template_params")
            for item in template_params:
                if have_template.get(item) != want_template.get(item):
                    self.msg = "Configuration Template config with template_name {0}'s '{1}' is not applied to the Cisco Catalyst Center.".format(
                        want_template.get("name"), item
                    )
                    self.status = "failed"
                    return self

            want_template_containing_template = want_template.get("containingTemplates")
            if want_template_containing_template:
                for item in want_template_containing_template:
                    name = item.get("name")
                    response = get_dict_result(
                        have_template.get("containingTemplates"), "name", name
                    )
                    if response is None:
                        self.msg = (
                            "Configuration Template config with template_name '{0}' under ".format(
                                name
                            )
                            + "'containing_templates' is not available in the Cisco Catalyst Center."
                        )
                        self.status = "failed"
                        return self
                    for value in item:
                        if item.get(value) != response.get(value):
                            self.msg = (
                                "Configuration Template config with template_name "
                                + "{0}'s '{1}' is not applied to the Cisco Catalyst Center.".format(
                                    name, value
                                )
                            )
                            self.status = "failed"
                            return self

            self.log(
                "Successfully validated the Template in the Catalyst Center.", "INFO"
            )

        self.msg = "Successfully validated the Configuration Templates."
        self.status = "success"
        return self

    def reset_values(self):
        """
        Reset all neccessary attributes to default values.

        Parameters:
            self - The current object.

        Returns:
            None
        """

        self.have_project.clear()
        self.have_template.clear()
        self.want.clear()
