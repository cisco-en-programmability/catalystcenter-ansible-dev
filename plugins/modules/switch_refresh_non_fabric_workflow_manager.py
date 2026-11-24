#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module to deploy a non-fabric switch refresh onto the replacement switch."""
from __future__ import absolute_import, division, print_function

__metaclass__ = type
__author__ = "Sunil Shatagopa, Madhan Sankaranarayanan"

DOCUMENTATION = r"""
---
module: switch_refresh_non_fabric_workflow_manager
short_description: Deploy a non-fabric switch refresh onto the replacement switch.
description:
- Deploys the switch-refresh deploy config produced by
  M(cisco.catalystcenter.switch_refresh_non_fabric_playbook_config_generator) onto the
  replacement Cisco Catalyst 9000 switch.
- The generator reads the source (legacy) switch's deployed templates from Cisco Catalyst
  Center and writes a ready-to-run deploy config. The operator fills the required blanks
  (the replacement switch serial number, and any required template parameters), then runs
  this module to apply that config.
- Before deploying, this module runs a pre-flight check that fails fast, with a clear
  message, if any required blank has been left unfilled - specifically a missing
  C(destination_device_serial_number) or a required C(template_parameters) value that is
  still empty - so an incomplete deploy config is caught before anything is pushed.
- Templates deployed on the source switch are recreated from their realized configuration
  as C(<name>_refresh) (project C(switch_refresh_non_fabric_project)) and deployed to the
  replacement by serial number; C(include_templates) add-ons are deployed by reference.
- This module reuses the project and template create, commit and deploy logic of
  M(cisco.catalystcenter.template_workflow_manager); the C(config) it accepts is the same
  structure that module accepts.
version_added: 6.44.0
extends_documentation_fragment:
- cisco.catalystcenter.workflow_manager_params
author:
- Sunil Shatagopa (@shatagopasunil)
- Madhan Sankaranarayanan (@madhansansel)
options:
  config_verify:
    description:
    - If set to C(true), verifies the Cisco Catalyst Center configuration after applying
      the deploy config.
    type: bool
    default: false
  state:
    description:
    - The desired state of Cisco Catalyst Center after module execution.
    - C(merged) creates and commits the recreated templates and deploys them (plus any
      C(include_templates) add-ons) to the replacement switch - this performs the switch
      refresh.
    - C(deleted) is not supported by this module. Template removal is owned by
      M(cisco.catalystcenter.template_workflow_manager); use that module to roll back
      the recreated C(<name>_refresh) templates.
    type: str
    choices: [merged, deleted]
    default: merged
  config:
    description:
    - The deploy config to apply, as produced by
      M(cisco.catalystcenter.switch_refresh_non_fabric_playbook_config_generator).
    - This is normally supplied by loading the generated file, for example
      C("{{ lookup('file', '<source_ip>_refresh_playbook_config.yml') | from_yaml }}")
      and passing its C(config) key.
    - Holds the replacement switch serial number and the C(templates) to recreate and/or
      deploy to the replacement switch.
    type: dict
    required: true
    suboptions:
      destination_device_serial_number:
        description:
        - Serial number of the replacement switch (the destination device) that every
          template in C(templates) is deployed to. Supplied once here instead of being
          repeated in each deploy entry; the module stamps it onto every deploy before
          pushing.
        - Left empty by the generator when the replacement serial is not yet known; fill
          it in before running C(state=merged). An empty value fails the pre-flight check.
        type: str
        default: ""
      templates:
        description:
        - The templates to recreate and/or deploy to the replacement switch. Each entry
          recreates a template and/or deploys a template to the replacement switch.
        type: list
        elements: dict
        default: []
        suboptions:
          configuration_templates:
            description:
            - Definition of a template to create and commit before deploying. Present for
              templates recreated from the source switch's realized configuration.
            type: dict
            suboptions:
              project_name:
                description: Project the recreated template is created under.
                type: str
              template_name:
                description: Name of the recreated template, for example C(<name>_refresh).
                type: str
              language:
                description: Template language, for example C(VELOCITY) or C(JINJA).
                type: str
              device_types:
                description: Device types the template applies to.
                type: list
                elements: dict
                suboptions:
                  product_family:
                    description: Product family, for example C(Switches and Hubs).
                    type: str
                  product_series:
                    description: Product series.
                    type: str
              template_content:
                description: The CLI content of the recreated template.
                type: str
          deploy_template:
            description:
            - Definition of the deploy action for a template onto the replacement switch.
            type: dict
            suboptions:
              project_name:
                description: Project the template to deploy belongs to.
                type: str
              template_name:
                description: Name of the template to deploy.
                type: str
              template_parameters:
                description:
                - Parameter values for the template being deployed. A value left empty for
                  a required parameter fails the pre-flight check.
                type: list
                elements: dict
                suboptions:
                  param_name:
                    description: Name of the template parameter.
                    type: str
                  param_value:
                    description: Value for the template parameter.
                    type: str
requirements:
- catalystcentersdk >= 3.1.6.0.2
- python >= 3.12
notes:
- Cisco Catalyst Center >= 2.3.7.9
- This module deploys configuration to the replacement switch. Run
  M(cisco.catalystcenter.switch_refresh_non_fabric_playbook_config_generator) first to
  generate the deploy config, fill the required blanks, then run this module.
- The pre-flight required-parameter check reads template parameter definitions from Cisco
  Catalyst Center. When that read is unavailable, the required-parameter check is skipped
  for that template (a warning is logged) while the C(destination_device_serial_number)
  check still applies.
- |-
  SDK Methods used are
  configuration_templates.ConfigurationTemplates.get_templates_details
  configuration_templates.ConfigurationTemplates.create_template
  configuration_templates.ConfigurationTemplates.deploy_template_v2
- |-
  SDK Paths used are
  GET /dna/intent/api/v2/template-programmer/template
  POST /dna/intent/api/v1/template-programmer/project/{projectId}/template
  POST /dna/intent/api/v2/template-programmer/template/deploy
seealso:
- module: cisco.catalystcenter.switch_refresh_non_fabric_playbook_config_generator
- module: cisco.catalystcenter.template_workflow_manager
"""

EXAMPLES = r"""
- name: Deploy a non-fabric switch refresh from the generated deploy config
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    generated: "{{ lookup('file', '204.1.2.2_refresh_playbook_config.yml') | from_yaml }}"
  tasks:
    - name: Apply the switch refresh to the replacement switch
      cisco.catalystcenter.switch_refresh_non_fabric_workflow_manager:
        catalystcenter_host: "{{ catalystcenter_host }}"
        catalystcenter_username: "{{ catalystcenter_username }}"
        catalystcenter_password: "{{ catalystcenter_password }}"
        catalystcenter_verify: "{{ catalystcenter_verify }}"
        catalystcenter_version: "{{ catalystcenter_version }}"
        catalystcenter_log: true
        catalystcenter_log_level: INFO
        state: merged
        config: "{{ generated.config }}"

- name: Deploy an inline switch refresh config
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Recreate one template and deploy it to the replacement switch
      cisco.catalystcenter.switch_refresh_non_fabric_workflow_manager:
        catalystcenter_host: "{{ catalystcenter_host }}"
        catalystcenter_username: "{{ catalystcenter_username }}"
        catalystcenter_password: "{{ catalystcenter_password }}"
        catalystcenter_verify: "{{ catalystcenter_verify }}"
        catalystcenter_version: "{{ catalystcenter_version }}"
        state: merged
        config:
          destination_device_serial_number: FJC2334ABCD
          templates:
            - configuration_templates:
                project_name: switch_refresh_non_fabric_project
                template_name: ZZ_Cleanup_refresh
                language: VELOCITY
                device_types:
                  - product_family: Switches and Hubs
                template_content: |
                  interface Loopback970
                   description refreshed
              deploy_template:
                project_name: switch_refresh_non_fabric_project
                template_name: ZZ_Cleanup_refresh
"""

RETURN = r"""
response:
  description: A dictionary or list with the response returned by the Cisco Catalyst Center
    Python SDK after deploying the switch refresh configuration.
  returned: always
  type: dict
  sample: >
    {
        "response": {
            "msg": "Successfully deployed the template(s) to the replacement switch."
        },
        "status": "success"
    }
msg:
  description: A human-readable message describing the result of the switch refresh
    deployment, the pre-flight outcome when the replacement serial number is missing, or
    the Catalyst Center preview validation outcome when a template has an unresolved
    required parameter.
  returned: always
  type: str
  sample: >
    "Switch refresh pre-flight validation failed; fix the following before deploying:
     - 'destination_device_serial_number' is not set. Set it in the 'config' section to
       the replacement (destination) switch's serial number, then re-run the deploy."
"""

import time

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cisco.catalystcenter.plugins.module_utils.template_common import (
    TemplateCommon,
)


class SwitchRefreshNonFabric(TemplateCommon):
    """Deploy a non-fabric switch refresh onto the replacement switch.

    Reuses the common template create, commit and deploy primitives of the shared
    ``TemplateCommon`` base and adds a switch-refresh pre-flight check that fails fast
    when a required blank in the deploy config has been left unfilled, plus its own
    merged-state driver that recreates templates from the deploy config and deploys them
    to the replacement switch.
    """

    def __init__(self, module):
        super().__init__(module)
        # Set True once every deploy preview passes up front, so the per-deploy preview
        # in deploy_template_to_devices is not repeated during the deploy pass.
        self._previews_prevalidated = False

    def validate_input(self):
        """
        Adapt the switch-refresh deploy config to the shared ``Template`` validator.

        The generated deploy config is a dict holding the replacement switch
        C(destination_device_serial_number) and a C(templates) list. The shared
        ``Template`` validator expects a plain list of template entries, so the serial is
        stashed and the C(templates) list is handed to ``Template.validate_input``
        unchanged - the template workflow code is reused without modification.

        Returns:
            self: The current object, with C(self.validated_config) populated.
        """
        self.log("Starting switch refresh deploy-config input validation.", "DEBUG")
        config = self.params.get("config") or {}
        self.destination_device_serial_number = str(
            config.get("destination_device_serial_number") or ""
        ).strip()
        self.config = config.get("templates") or []
        self.log(
            "Adapted deploy config: destination serial '{0}', {1} template entry(ies) "
            "handed to the shared validator.".format(
                self.destination_device_serial_number or "(unset)", len(self.config)
            ),
            "DEBUG",
        )
        return super().validate_input()

    def apply_destination_serial(self):
        """
        Stamp the replacement switch serial onto every deploy entry.

        The replacement switch serial number is supplied once as the config-level
        C(destination_device_serial_number). This copies it into each deploy entry's
        C(device_details.serial_numbers) so the shared deploy logic targets the
        replacement switch without the serial being repeated in every entry.

        Returns:
            self: The current object.
        """
        serial = self.destination_device_serial_number
        serial_numbers = [serial] if serial else []
        entries = self.validated_config or []
        self.log(
            "Starting destination-serial stamping of '{0}' onto {1} deploy "
            "entry(ies).".format(serial or "(unset)", len(entries)),
            "DEBUG",
        )
        stamped = 0
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                self.log("Entry {0}: not a mapping; skipping.".format(index), "DEBUG")
                continue
            deploy = entry.get("deploy_template")
            if not isinstance(deploy, dict):
                self.log(
                    "Entry {0}: no deploy_template block; nothing to stamp.".format(
                        index
                    ),
                    "DEBUG",
                )
                continue
            device_details = deploy.get("device_details")
            if not isinstance(device_details, dict):
                device_details = {}
                deploy["device_details"] = device_details
            device_details["serial_numbers"] = serial_numbers
            stamped += 1
            self.log(
                "Entry {0}: stamped serial '{1}' onto the deploy target.".format(
                    index, serial or "(unset)"
                ),
                "DEBUG",
            )
        self.log(
            "Completed destination-serial stamping: applied '{0}' to {1} of {2} "
            "deploy entry(ies).".format(serial or "(unset)", stamped, len(entries)),
            "DEBUG",
        )
        return self

    def validate_switch_refresh_config(self):
        """
        Pre-flight check: the replacement switch serial number must be set.

        The replacement switch C(destination_device_serial_number) must be provided before
        any configuration is pushed. Required template parameter values are not checked
        here; they are validated at deploy time by rendering each template through Catalyst
        Center's own preview (see :meth:`preview_validate_deploy`), which reports any gap
        authoritatively. Fails (via C(set_operation_result)) when the serial is missing.

        Returns:
            self: The current object, with the failure recorded when the serial is unset.
        """
        self.log("Starting switch refresh pre-flight validation.", "INFO")
        if not self.destination_device_serial_number:
            self.msg = (
                "Switch refresh pre-flight validation failed; fix the following before "
                "deploying:\n- 'destination_device_serial_number' is not set. Set it in "
                "the 'config' section to the replacement (destination) switch's serial "
                "number, then re-run the deploy."
            )
            self.set_operation_result("failed", False, self.msg, "ERROR")
            return self
        if not self.validated_config:
            self.msg = (
                "No templates were provided in the deploy config; nothing to deploy. "
                "Add at least one entry under 'config.templates' that targets the "
                "replacement switch, then re-run the deploy."
            )
            self.set_operation_result("success", False, self.msg, "WARNING")
            return self
        self.log("Switch refresh pre-flight validation passed.", "INFO")
        return self

    def _is_composite_template(self, template_id):
        """
        Return True when the committed template id refers to a composite template.

        By-reference composites are deployed with C(isComposite) False, so the payload
        flag alone is not reliable; confirm it from the committed template details.
        """
        try:
            details = self.get_template({"templateId": template_id})
        except Exception as error:
            self.log(
                "Could not determine whether template id '{0}' is composite: {1}. "
                "Proceeding without the composite preview warning.".format(
                    template_id, error
                ),
                "DEBUG",
            )
            return False
        if details is not None and hasattr(details, "get"):
            return bool(details.get("composite"))
        return False

    def preview_validate_deploy(self, deploy_temp_payload, template_name):
        """
        Validate a template through Catalyst Center preview before it is deployed.

        Renders the template server-side with only the operator-supplied (non-blank)
        parameter values. Catalyst Center resolves its own system variables, so any
        remaining gap it reports - for example a required parameter the operator left
        blank - comes back as a validation error. Any error fails the run before the
        template is pushed to the replacement switch. A preview that cannot be run (a
        transient API issue) is logged and skipped, so a deploy is never blocked by the
        preview infrastructure itself.

        Args:
            deploy_temp_payload (dict): The resolved deploy payload (template id and
                per-target parameters) built by the shared deploy logic.
            template_name (str): The template being deployed, used in messages.

        Returns:
            self: The current object, with the failure recorded when preview reports one.
        """
        self.log(
            "Starting pre-deploy preview validation for template '{0}'.".format(
                template_name
            ),
            "DEBUG",
        )
        template_id = deploy_temp_payload.get("templateId")
        if not template_id:
            self.log(
                "No template id resolved for '{0}'; skipping preview validation.".format(
                    template_name
                ),
                "WARNING",
            )
            return self
        # A by-reference composite is deployed with isComposite False, so confirm from
        # the committed template. Catalyst Center preview does not validate a composite's
        # member templates, so warn and skip instead of reporting a hollow pass.
        if deploy_temp_payload.get("isComposite") or self._is_composite_template(
            template_id
        ):
            self.log(
                "Skipping pre-deploy preview validation for composite template '{0}'; "
                "Catalyst Center does not validate its member templates' required "
                "parameters or content before deploy. Confirm member parameters in "
                "Catalyst Center.".format(template_name),
                "WARNING",
            )
            return self
        target_info = deploy_temp_payload.get("targetInfo") or []
        supplied = target_info[0].get("params") if target_info else {}
        # Preview with only the values the operator actually filled, so a blank required
        # parameter surfaces as a gap instead of being treated as provided.
        params = {
            name: value
            for name, value in (supplied or {}).items()
            if str(value).strip()
        }
        self.log(
            "Previewing template '{0}' (id '{1}') with {2} supplied param(s) for "
            "pre-deploy validation.".format(template_name, template_id, len(params)),
            "INFO",
        )
        try:
            response = self.catalystcenter_apply["exec"](
                family="configuration_templates",
                function="preview_template",
                op_modifies=True,
                params={"templateId": template_id, "params": params},
            )
        except Exception as error:
            self.log(
                "Preview could not be run for template '{0}': {1}. Skipping preview "
                "validation and proceeding to deploy.".format(template_name, error),
                "WARNING",
            )
            return self
        validation_errors = []
        if hasattr(response, "get"):
            validation_errors = response.get("validationErrors") or []
        if validation_errors:
            messages = []
            for item in validation_errors:
                if isinstance(item, dict):
                    messages.append(str(item.get("message") or item.get("type") or item))
                else:
                    messages.append(str(item))
            self.msg = (
                "Template '{0}' failed Catalyst Center preview validation; fix the "
                "following before deploying:\n- {1}".format(
                    template_name, "\n- ".join(messages)
                )
            )
            self.set_operation_result("failed", False, self.msg, "ERROR")
            return self
        self.log(
            "Preview validation passed for template '{0}'.".format(template_name),
            "INFO",
        )
        return self

    def deploy_template_to_devices(self, deploy_temp_payload, template_name, device_ips):
        """
        Preview-validate the resolved template, then run the shared deploy.

        Overrides C(Template.deploy_template_to_devices) to add a Catalyst Center preview
        check immediately before the deploy. The shared deploy logic is reused unchanged
        via C(super()); only the pre-deploy validation is added here.

        Args:
            deploy_temp_payload (dict): The resolved deploy payload.
            template_name (str): The template being deployed.
            device_ips (list): Management IPs of the target device(s).

        Returns:
            self: The result of the shared deploy, or the failure recorded by preview.
        """
        self.log(
            "Deploying template '{0}' to device(s) {1} after preview validation.".format(
                template_name, device_ips
            ),
            "DEBUG",
        )
        if not self._previews_prevalidated:
            self.preview_validate_deploy(
                deploy_temp_payload, template_name
            ).check_return_status()
        return super().deploy_template_to_devices(
            deploy_temp_payload, template_name, device_ips
        )

    def resolve_deploy_payload(self, deploy_temp_details):
        """
        Resolve the replacement switch and build the deploy payload for one entry.

        Shared by the up-front preview pass and the deploy pass so device resolution and
        payload construction stay identical. Fails the run - missing serial stamp, the
        replacement switch not found in inventory, or no resolvable device id - before
        any template is deployed.

        Args:
            deploy_temp_details (dict): The deploy_template entry (template name,
                parameters and the stamped device_details).

        Returns:
            tuple: (deploy_temp_payload, template_name, device_ips).
        """
        template_name = deploy_temp_details.get("template_name")
        device_details = deploy_temp_details.get("device_details")
        if not device_details:
            self.msg = (
                "Cannot deploy template '{0}' because the replacement switch serial "
                "number was not applied to the deploy entry.".format(template_name)
            )
            self.set_operation_result(
                "failed", False, self.msg, "ERROR"
            ).check_return_status()

        self.log(
            "Resolving replacement switch for template '{0}' from device details: "
            "{1}".format(template_name, device_details),
            "DEBUG",
        )
        device_ips = self.get_device_ips_from_config_priority(device_details)
        if not device_ips:
            serials = device_details.get("serial_numbers") or []
            target = (
                "serial number(s) {0}".format(", ".join(str(s) for s in serials))
                if serials
                else "destination device"
            )
            self.msg = (
                "Cannot deploy template '{0}': the replacement switch ({1}) was not "
                "found in the Cisco Catalyst Center device inventory. Confirm the "
                "'destination_device_serial_number' is correct and that the "
                "replacement switch is onboarded (discovered or provisioned) and "
                "reachable in Catalyst Center, then re-run the deploy.".format(
                    template_name, target
                )
            )
            self.set_operation_result(
                "failed", False, self.msg, "ERROR"
            ).check_return_status()

        device_id_dict = self.get_device_ids_from_device_ips(device_ips)
        device_ids = self.get_list_from_dict_values(device_id_dict)
        if not device_ids:
            self.msg = (
                "There are no device id found for the device(s) '{0}' in the Cisco "
                "Catalyst Center so cannot deploy the given template '{1}'.".format(
                    device_ips, template_name
                )
            )
            self.set_operation_result(
                "failed", False, self.msg, "ERROR"
            ).check_return_status()

        device_ip_dict = self.get_device_ips_from_device_ids(device_ids)
        device_ips = self.get_list_from_dict_values(device_ip_dict)
        deploy_temp_payload = self.create_payload_for_template_deploy(
            deploy_temp_details, device_ids
        )
        return deploy_temp_payload, template_name, device_ips

    def prevalidate_deploy_templates(self):
        """
        Preview-validate every deploy entry before any template is deployed.

        Recreates each template as needed and runs its Catalyst Center preview up front,
        so an invalid template (for example a missing required parameter) fails the whole
        run before any configuration reaches a device. Without this, a template earlier in
        the list would already be deployed when a later one fails preview. No template is
        deployed here; templates are only recreated and previewed.

        Returns:
            self: The current object; the failure is recorded when a preview fails.
        """
        self.log(
            "Starting up-front preview validation of all deploy templates.", "INFO"
        )
        for config in self.validated_config:
            self.reset_values()
            self.get_have(config).check_return_status()
            self.get_want(config).check_return_status()
            configuration_templates = config.get("configuration_templates")
            if configuration_templates:
                self.update_configuration_templates(
                    config, configuration_templates
                ).check_return_status()
                self.update_template_projects_message().check_return_status()
            deploy_temp_details = config.get("deploy_template")
            if not deploy_temp_details:
                continue
            deploy_temp_payload, template_name, device_ips = self.resolve_deploy_payload(
                deploy_temp_details
            )
            self.log(
                "Pre-validating template '{0}' for device(s) {1}.".format(
                    template_name, device_ips
                ),
                "DEBUG",
            )
            self.preview_validate_deploy(
                deploy_temp_payload, template_name
            ).check_return_status()
        self._previews_prevalidated = True
        self.log(
            "Up-front preview validation passed for all deploy templates.", "INFO"
        )
        return self

    def get_diff_merged(self, config):
        """
        Recreate any template in the deploy entry, then deploy it to the replacement switch.

        Mirrors the merged-state handling of ``template_workflow_manager`` but only for
        the two steps the switch refresh needs: create and commit a recreated template
        (C(configuration_templates)) using the common template primitives, then resolve
        the replacement switch from the serial stamped onto C(deploy_template) and deploy
        it. Project import and export are not used by the switch refresh and are
        intentionally omitted.

        Args:
            config (dict): A single validated template entry from the deploy config.

        Returns:
            self: The current object, with the operation result recorded.
        """
        start_time = time.time()
        template_label = (
            (config.get("deploy_template") or {}).get("template_name")
            or (config.get("configuration_templates") or {}).get("template_name")
            or "unknown"
        )
        self.log(
            "Starting merged-state switch refresh for template '{0}'.".format(
                template_label
            ),
            "INFO",
        )
        configuration_templates = config.get("configuration_templates")
        if configuration_templates and not self._previews_prevalidated:
            self.log(
                "Recreating and committing template '{0}' before deploy.".format(
                    template_label
                ),
                "DEBUG",
            )
            self.update_configuration_templates(
                config, configuration_templates
            ).check_return_status()
            self.update_template_projects_message().check_return_status()

        deploy_temp_details = config.get("deploy_template")
        if deploy_temp_details:
            deploy_temp_payload, template_name, device_ips = self.resolve_deploy_payload(
                deploy_temp_details
            )
            self.deploy_template_to_devices(
                deploy_temp_payload, template_name, device_ips
            ).check_return_status()

        self.msg = "Successfully completed merged state execution"
        self.status = "success"
        self.log(
            "Completed merged-state switch refresh for template '{0}' in {1:.2f} "
            "seconds.".format(template_label, time.time() - start_time),
            "INFO",
        )
        return self

    def get_diff_deleted(self, config):
        """
        Deleted state is not supported for the non-fabric switch refresh.

        The switch refresh deploy config describes templates to recreate and deploy onto
        the replacement switch; it is not a template-delete request, and every deploy
        entry carries a C(deploy_template) block that template deletion does not support.
        Roll back the recreated C(<name>_refresh) templates with
        M(cisco.catalystcenter.template_workflow_manager), which owns template deletion.

        Args:
            config (dict): A single validated template entry (unused).

        Returns:
            self: The current object, with a not-supported failure recorded.
        """
        self.msg = (
            "State 'deleted' is not supported by the non-fabric switch refresh module. "
            "Use 'cisco.catalystcenter.template_workflow_manager' to remove the recreated "
            "templates."
        )
        self.set_operation_result(
            "failed", False, self.msg, "ERROR"
        ).check_return_status()
        return self


def main():
    """main entry point for module execution"""
    element_spec = {
        "catalystcenter_host": {"required": True, "type": "str", "aliases": ["dnac_host"]},
        "catalystcenter_port": {"type": "str", "default": "443", "aliases": ["dnac_port", "catalystcenter_api_port"]},
        "catalystcenter_username": {"type": "str", "default": "admin", "aliases": ["dnac_username", "user"]},
        "catalystcenter_password": {"type": "str", "no_log": True, "aliases": ["dnac_password"]},
        "catalystcenter_verify": {"type": "bool", "default": True, "aliases": ["dnac_verify"]},
        "catalystcenter_version": {"type": "str", "default": "2.3.7.6", "aliases": ["dnac_version"]},
        "catalystcenter_debug": {"type": "bool", "default": False, "aliases": ["dnac_debug"]},
        "catalystcenter_log": {"type": "bool", "default": False, "aliases": ["dnac_log"]},
        "catalystcenter_log_level": {"type": "str", "default": "WARNING", "aliases": ["dnac_log_level"]},
        "catalystcenter_log_file_path": {"type": "str", "default": "catalystcenter.log", "aliases": ["dnac_log_file_path"]},
        "catalystcenter_log_append": {"type": "bool", "default": True, "aliases": ["dnac_log_append"]},
        "validate_response_schema": {"type": "bool", "default": True},
        "config_verify": {"type": "bool", "default": False},
        "catalystcenter_api_task_timeout": {"type": "int", "default": 1200, "aliases": ["dnac_api_task_timeout"]},
        "catalystcenter_task_poll_interval": {"type": "int", "default": 2, "aliases": ["dnac_task_poll_interval"]},
        "config": {
            "required": True,
            "type": "dict",
            "options": {
                "destination_device_serial_number": {"type": "str", "default": ""},
                "templates": {"type": "list", "elements": "dict", "default": []},
            },
        },
        "state": {"default": "merged", "choices": ["merged", "deleted"]},
    }

    module = AnsibleModule(argument_spec=element_spec, supports_check_mode=False)

    ccc_refresh = SwitchRefreshNonFabric(module)

    if (
        ccc_refresh.compare_catalystcenter_versions(
            ccc_refresh.get_ccc_version(), "2.3.7.9"
        )
        < 0
    ):
        ccc_refresh.msg = (
            "The specified version '{0}' does not support the non-fabric switch refresh "
            "deployment. Supported versions start from '2.3.7.9' onwards.".format(
                ccc_refresh.get_ccc_version()
            )
        )
        ccc_refresh.set_operation_result(
            "failed", False, ccc_refresh.msg, "ERROR"
        ).check_return_status()

    ccc_refresh.validate_input().check_return_status()
    ccc_refresh.apply_destination_serial()
    state = ccc_refresh.params.get("state")
    config_verify = ccc_refresh.params.get("config_verify")
    if state not in ccc_refresh.supported_states:
        ccc_refresh.status = "invalid"
        ccc_refresh.msg = "State {0} is invalid".format(state)
        ccc_refresh.check_return_status()

    # Fail fast if the operator left a required blank (serial number or required parameter)
    # unfilled before any configuration is pushed to the replacement switch.
    if state == "merged":
        ccc_refresh.validate_switch_refresh_config().check_return_status()
        # Preview-validate every template before any deploy so one invalid template
        # cannot leave earlier templates already pushed to the replacement switch.
        ccc_refresh.prevalidate_deploy_templates().check_return_status()

    for config in ccc_refresh.validated_config:
        ccc_refresh.reset_values()
        ccc_refresh.get_have(config).check_return_status()
        ccc_refresh.get_want(config).check_return_status()
        ccc_refresh.get_diff_state_apply[state](config).check_return_status()
        if config_verify:
            ccc_refresh.verify_diff_state_apply[state](config).check_return_status()

    module.exit_json(**ccc_refresh.result)


if __name__ == "__main__":
    main()
