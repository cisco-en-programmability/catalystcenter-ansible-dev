#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module to generate a deploy config for a non-fabric switch refresh."""
from __future__ import absolute_import, division, print_function

__metaclass__ = type
__author__ = "Sunil Shatagopa, Madhan Sankaranarayanan"

DOCUMENTATION = r"""
---
module: switch_refresh_non_fabric_playbook_config_generator
short_description: Generate a ready-to-run deploy config for a non-fabric switch refresh.
description:
- Generates a deploy config - the C(config) input for the
  M(cisco.catalystcenter.switch_refresh_non_fabric_workflow_manager) module - that migrates
  the configuration intent of a legacy non-fabric switch onto a replacement Cisco Catalyst
  9000 switch.
- This module is read-only against the network. It reads from Cisco Catalyst Center and
  from the SOURCE (legacy) switch only, and never pushes configuration to any device. It
  writes the deploy config to a local YAML file (plus a read-only backup copy); the
  operator then runs C(switch_refresh_non_fabric_workflow_manager) to apply that config to
  the replacement switch.
- The templates to reapply are discovered automatically from Cisco Catalyst Center, which
  reports every template it has actually deployed on the source switch - both templates
  pushed through a network profile and templates deployed directly (Day-N) - together with
  the exact CLI it rendered and pushed for each, with every parameter value already
  resolved.
- Each deployed template is recreated for the replacement from that realized
  configuration. Interface names are renamed to the replacement's interfaces (per
  C(interface_mappings)), and unwanted lines are removed (per C(exclude_commands)). It
  is written as a C(configuration_templates) entry (project
  C(switch_refresh_non_fabric_project), template C(<name>_refresh)) paired with a
  C(deploy_template) entry that pushes it to the replacement by serial number. Because the
  content is already-resolved configuration, these entries carry no parameter values to
  fill.
- A deployed template is recreated only when its most recent deploy succeeded (status
  C(SUCCESS)). One that Cisco Catalyst Center reports without a realized configuration, or
  whose most recent deploy is any other status (for example failed, still in progress, or
  partially applied), is left out rather than recreated from unverified data.
- A template added with C(include_templates) is an operator add-on. It is deployed by
  reference, so it is added directly even when the same template is already deployed on the
  source switch - a C(deploy_template) entry names the original project and template and
  lists every parameter the template declares, with empty values, for the operator to
  review before deploying. An add-on that targets a different product family than the
  switch (for example a wireless template) is not applicable and is skipped. The module
  never guesses a value, and it does not pre-classify which parameters are required.
  Whether a value is actually required is validated at deploy time by the
  C(switch_refresh_non_fabric_workflow_manager) module, which renders the template through
  Catalyst Center's preview. Leave system variables (such as C($__ntpserver)) blank -
  Catalyst Center resolves them during deployment and ignores any supplied value.
- Use C(exclude_templates) to leave templates out of the deploy config, and
  C(include_templates) to add templates directly as add-ons - deployed by reference - for
  example net-new standard templates, or a template the module left out that the operator
  decides is needed. When a template is named in both lists, exclusion wins and it
  is left out.
- The Ansible task response is a concise summary only. It echoes the source device IP and
  the replacement serial number, and reports how many templates will be deployed
  (C(templates_to_deploy)), how many by-reference template parameters are listed for the
  operator to review (C(template_parameters_to_fill)), how many templates were excluded
  (C(templates_excluded)), and the paths of the generated deploy config and its backup. Any
  C(include_templates) entries that could not be found are noted in the response C(message).
- The module is idempotent. Re-running it with unchanged Catalyst Center state rewrites
  nothing and reports C(changed=false) with a "Config
  already up to date" message; a run that writes or updates a file reports C(changed=true)
  with a "Config generated" message.
- A read-only backup of the deploy config is always written to a separate YAML file
  alongside it. The backup is a pristine copy of the generated deploy config. If the
  working deploy config is later disturbed - edited by mistake, truncated or lost - copy
  the backup over it and continue, with no need to regenerate from Catalyst Center.
- The destination (replacement) switch is identified by serial number rather than by IP
  address, because the replacement is often not yet onboarded (so it has no management IP)
  and any DHCP-assigned address can change between runs, whereas the serial number is
  stable. The serial number targets the replacement in every C(deploy_template) entry and
  is echoed in the module response.
version_added: 6.44.0
extends_documentation_fragment:
- cisco.catalystcenter.workflow_manager_params
author:
- Sunil Shatagopa (@shatagopasunil)
- Madhan Sankaranarayanan (@madhansansel)
options:
  state:
    description: The desired state of Cisco Catalyst Center after module execution.
    type: str
    choices: [gathered]
    default: gathered
  file_path:
    description:
    - Path of the YAML file where the generated deploy config is written.
    - If not provided, the file is written to the current working directory using the
      default name C(<source_device_ip>_refresh_playbook_config.yml), for example
      C(204.1.1.25_refresh_playbook_config.yml).
    - Any missing parent directories in the path are created.
    type: str
    required: false
  backup_file_path:
    description:
    - Path of the YAML file where the read-only backup of the deploy config is written.
    - The backup is always written; this option only controls where it is placed. It is a
      pristine copy of the generated deploy config, kept as a clean fallback - if the
      working deploy config is disturbed (edited by mistake, truncated or lost), copy
      this file over it and continue, with no need to regenerate from Catalyst Center.
    - Treat the backup as read-only; unlike the deploy config it is not meant to be
      hand-edited.
    - If not provided, the file is written to the current working directory using the
      default name C(<source_device_ip>_refresh_backup.yml), for example
      C(204.1.1.25_refresh_backup.yml).
    - Any missing parent directories in the path are created.
    type: str
    required: false
  config:
    description:
    - Dictionary of inputs that drive the configuration generation.
    type: dict
    required: true
    suboptions:
      source_device_ip:
        description:
        - Management IP address of the source (legacy) switch whose deployed templates and
          their realized configuration are read from Cisco Catalyst Center to build the
          deploy config.
        type: str
        required: true
      destination_device_serial_number:
        description:
        - Serial number of the destination (replacement) Cisco Catalyst 9000 switch that
          the refresh targets.
        - A serial number is used instead of a management IP address because the
          replacement switch is often not yet onboarded (so it has no management IP), and
          a DHCP-assigned address can change between runs, whereas the serial number is
          stable.
        - The serial number is written once as the C(config.destination_device_serial_number)
          field of the generated deploy config, and is echoed in the module response.
          C(switch_refresh_non_fabric_workflow_manager) applies it to every template it
          deploys.
        - Optional. When omitted, the deploy config is still generated but the
          C(config.destination_device_serial_number) field is left empty and marked
          C(# [REQUIRED]); the operator must add the replacement switch serial number
          before running C(switch_refresh_non_fabric_workflow_manager).
        type: str
        required: false
      interface_migration:
        description:
        - Whether the replacement switch uses different interface names than the source
          switch, so C(interface_mappings) must be applied.
        - When C(true), C(interface_mappings) is mandatory - the module fails validation
          if it is missing or empty - and the listed source-to-destination renames are
          applied to the recreated configuration.
        - When C(false) (the default), C(interface_mappings) is ignored - the recreated
          configuration keeps the source interface names unchanged, even if
          C(interface_mappings) is supplied.
        type: bool
        required: false
        default: false
      interface_mappings:
        description:
        - List of source-to-destination interface renames for the replacement switch.
          Applied only when C(interface_migration) is C(true), and required in that
          case; ignored when C(interface_migration) is C(false).
        - The default is an identity (same-name) map, so only the ports that move to a
          differently named interface on the replacement switch need to be listed.
        - Renaming an interface header moves the whole indented interface block with it.
          The match is whole-token and case-insensitive, so C(Vlan20) is never rewritten
          inside C(Vlan200).
        - Sub-interfaces of a mapped parent are handled automatically and do not need to
          be listed. When C(GigabitEthernet1/0/1) is mapped, a sub-interface such as
          C(GigabitEthernet1/0/1.100) is renamed to the destination parent keeping the
          same unit (for example C(GigabitEthernet2/0/1.100)).
        - The mapping must be unambiguous, or the module fails validation before writing
          anything. A source interface may be listed only once (it cannot map to two
          different destinations). Mapping an interface to its own name is allowed and is
          treated as a no-op (the same as not listing it).
        - Swaps and chained renames are supported. Mapping C(GigabitEthernet1/0/1) to
          C(GigabitEthernet1/0/2) together with C(GigabitEthernet1/0/2) to
          C(GigabitEthernet1/0/1) swaps the two, and C(A) to C(B) together with C(B) to
          C(C) renames each independently. All renames are applied in a single
          simultaneous pass, so an interface may appear as both a source and a
          destination without the names cascading into one another.
        - Each C(source_interface_name) must be an interface that exists on the source
          switch. The mappings are checked against the source device's interface
          inventory right after the device is resolved, and the module fails before
          writing anything if a C(source_interface_name) is not found - a sub-interface
          such as C(GigabitEthernet1/0/1.100) satisfies its parent
          C(GigabitEthernet1/0/1).
        - The renamed interfaces are written into the recreated template content in the
          generated deploy config, so the replacement switch is configured with the
          destination interface names. A name that appears as a template variable (for
          example C($Vlan20)) keeps its variable name and is resolved at deploy time.
        type: list
        elements: dict
        suboptions:
          source_interface_name:
            description: Interface name on the source switch, for example C(Vlan20).
            type: str
            required: true
          destination_interface_name:
            description: Interface name to use on the replacement switch, for example C(Vlan220).
            type: str
            required: true
      exclude_templates:
        description:
        - Optional list of templates to skip. A skipped template is left out of the
          playbook entirely, so the operator is not asked to fill its parameters.
        - Each entry identifies a template by name, and optionally by project. When
          C(project_name) is given, only the matching template in that project is
          skipped; when it is omitted, the given name is skipped in every project.
        - Matching is exact and case-insensitive; wildcards (for example C(*qos*)) are
          not supported here.
        - Exclusion always wins over C(include_templates) - a template named in both is
          left out. The number of skipped templates is reported in the module response
          under C(templates_excluded).
        type: list
        elements: dict
        suboptions:
          template_name:
            description: Name of the template to skip.
            type: str
            required: true
          project_name:
            description:
            - Project the template belongs to.
            - Optional. Omit it to skip the given template name in every project; provide
              it to skip only the matching template in that one project.
            type: str
            required: false
      include_templates:
        description:
        - Optional list of extra templates to add to the deploy config as add-ons.
        - Use this to have the replacement switch receive a template directly, instead of
          running C(cisco.catalystcenter.switch_refresh_non_fabric_workflow_manager)
          separately for it -
          for example a standard template kept in a shared project, or a template that the
          module left out and the operator decides is needed.
        - An included template is deployed by reference, so it is added even when the same
          template is already deployed on the source switch. Every parameter it declares is
          listed with an empty value for the operator to review; which values are actually
          required is validated at deploy time by
          C(cisco.catalystcenter.switch_refresh_non_fabric_workflow_manager).
        - Each entry must name both the project and the template, because a template name
          is unique only within a project and the template first has to be located.
          Matching is exact and case-insensitive; wildcards are not supported.
        - An entry that matches no template is reported in the response C(message) and
          does not stop the run.
        - Exclusion wins over inclusion - a template named in both C(include_templates)
          and C(exclude_templates) is left out.
        type: list
        elements: dict
        suboptions:
          project_name:
            description: Project the template belongs to.
            type: str
            required: true
          template_name:
            description: Name of the template to add.
            type: str
            required: true
      exclude_commands:
        description:
        - Optional list of glob (shell-style wildcard) patterns that match individual
          command lines anywhere they appear.
        - Matched lines are removed from the generated configuration.
        - Matching is case-insensitive and applies to the whole line, so a substring match
          requires surrounding stars, for example C(*route-target*).
        - The removal is applied to the recreated template content in the generated
          deploy config, so the excluded lines are not reapplied to the replacement.
        type: list
        elements: str

requirements:
- catalystcentersdk >= 3.1.6.0.2
- python >= 3.12
notes:
- Cisco Catalyst Center >= 2.3.7.9
- The module reads only from Cisco Catalyst Center and writes a local file.
- The set of templates deployed on the source switch, and the realized CLI for each, is
  read from the C(deployedTemplateDetails) endpoint. That endpoint has no Catalyst Center
  SDK wrapper, so the module calls it directly as a raw REST C(GET); every other Catalyst
  Center read uses a published SDK method.
- |-
  SDK Methods used are
  devices.Devices.get_device_list
  devices.Devices.get_interface_info_by_id
  configuration_templates.ConfigurationTemplates.get_templates_details
  configuration_templates.ConfigurationTemplates.get_template_details
- |-
  SDK Paths used are
  GET /dna/intent/api/v1/network-device
  GET /dna/intent/api/v1/interface/network-device/{deviceId}
  GET /dna/intent/api/v2/template-programmer/template
  GET /dna/intent/api/v1/template-programmer/template/{templateId}
  GET /dna/intent/api/v1/template-programmer/template/deployedTemplateDetails/{deviceId}
"""

EXAMPLES = r"""
- name: Generate the deploy config for a non-fabric switch refresh
  cisco.catalystcenter.switch_refresh_non_fabric_playbook_config_generator:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log: true
    catalystcenter_log_level: INFO
    state: gathered
    config:
      source_device_ip: "204.1.1.25"
      destination_device_serial_number: "FJC2334ABCD"

- name: Generate the deploy config to a custom path, skipping and adding specific templates
  cisco.catalystcenter.switch_refresh_non_fabric_playbook_config_generator:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log: true
    catalystcenter_log_level: INFO
    state: gathered
    file_path: "tmp/switch_refresh_204.1.1.25.yml"
    backup_file_path: "tmp/switch_refresh_204.1.1.25_backup.yml"
    config:
      source_device_ip: "204.1.1.25"
      destination_device_serial_number: "FJC2334ABCD"
      # Skip templates you do not want on the replacement switch.
      exclude_templates:
        - template_name: "Legacy QoS Template"      # skip this name in every project
        - template_name: "Refresh_Vlan"             # skip only the one in this project
          project_name: "Nonfabric_Refresh_Test"
      # Add extra templates that are not attached to the switch's profile.
      include_templates:
        - project_name: "Shared_Standard_Templates"
          template_name: "Corporate NTP"

- name: Generate the deploy config, renaming interfaces on the replacement switch
  cisco.catalystcenter.switch_refresh_non_fabric_playbook_config_generator:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log: true
    catalystcenter_log_level: INFO
    state: gathered
    config:
      source_device_ip: "204.1.1.25"
      destination_device_serial_number: "FJC2334ABCD"
      # Turn on interface migration; interface_mappings is then mandatory.
      interface_migration: true
      interface_mappings:
        - source_interface_name: "GigabitEthernet1/0/1"
          destination_interface_name: "GigabitEthernet2/0/1"
        - source_interface_name: "Vlan20"
          destination_interface_name: "Vlan220"

- name: Preview the deploy config before the replacement switch is onboarded (no serial yet)
  cisco.catalystcenter.switch_refresh_non_fabric_playbook_config_generator:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log: true
    catalystcenter_log_level: INFO
    state: gathered
    config:
      # destination_device_serial_number omitted - fill it in the generated file
      # (under config) before deploying.
      source_device_ip: "204.1.1.25"
"""

RETURN = r"""
# Case 1: Success scenario - deploy config generated
response_1:
  description: A dictionary with the summary of the generated deploy config.
  returned: always
  type: dict
  contains:
    msg:
      description: One-line human-readable summary (same text as C(response.message)).
      returned: always
      type: str
    changed:
      description: Whether a file was written; C(false) when the deploy config was already up to date.
      returned: always
      type: bool
    response:
      description: The structured summary payload.
      returned: always
      type: dict
      contains:
        status:
          description: Outcome of the generation.
          returned: always
          type: str
          choices: ['success', 'failed']
        message:
          description: One-line human-readable summary of the run.
          returned: always
          type: str
        source_device_ip:
          description: Management IP of the source (legacy) switch that was read.
          returned: always
          type: str
        destination_device_serial_number:
          description: Serial number of the replacement switch the deploy config targets.
          returned: always
          type: str
        templates_to_deploy:
          description: Number of templates written into the deploy config.
          returned: always
          type: int
        template_parameters_to_fill:
          description: >
            Number of by-reference (C(include_templates)) template parameters listed in the
            deploy config for the operator to review. Which of these are actually required
            is validated at deploy time by C(switch_refresh_non_fabric_workflow_manager).
          returned: always
          type: int
        templates_excluded:
          description: Number of templates left out via C(exclude_templates).
          returned: always
          type: int
        file_path:
          description: Path of the generated deploy config file.
          returned: always
          type: str
        backup_file_path:
          description: Path of the read-only backup copy of the deploy config.
          returned: always
          type: str
    status:
      description: Overall outcome of the run.
      returned: always
      type: str
      choices: ['success', 'failed']
  sample: >
    {
        "msg": "Config generated for device 'FJC2334ABCD' from source '204.1.1.25': 2 template(s) to deploy.",
        "response": {
            "status": "success",
            "message": "Config generated for device 'FJC2334ABCD' from source '204.1.1.25': 2 template(s) to deploy.",
            "source_device_ip": "204.1.1.25",
            "destination_device_serial_number": "FJC2334ABCD",
            "templates_to_deploy": 2,
            "template_parameters_to_fill": 1,
            "templates_excluded": 1,
            "file_path": "204.1.1.25_refresh_playbook_config.yml",
            "backup_file_path": "204.1.1.25_refresh_backup.yml"
        },
        "status": "success"
    }
# Case 2: Idempotency scenario - deploy config already up to date
response_2:
  description: >
    Idempotent scenario where the generated content already matches the existing files.
    The module reports C(changed=false) and rewrites nothing.
  returned: success
  type: dict
  sample: >
    {
        "msg": "Config already up to date for device 'FJC2334ABCD' from source '204.1.1.25': 2 template(s) to deploy.",
        "response": {
            "status": "success",
            "message": "Config already up to date for device 'FJC2334ABCD' from source '204.1.1.25': 2 template(s) to deploy.",
            "source_device_ip": "204.1.1.25",
            "destination_device_serial_number": "FJC2334ABCD",
            "templates_to_deploy": 2,
            "template_parameters_to_fill": 1,
            "templates_excluded": 1,
            "file_path": "204.1.1.25_refresh_playbook_config.yml",
            "backup_file_path": "204.1.1.25_refresh_backup.yml"
        },
        "status": "success"
    }
# Case 3: Error scenario
response_3:
  description: A dictionary describing the validation or runtime error.
  returned: failure
  type: dict
  sample: >
    {
        "msg": "Source device '204.1.1.25' was not found in Cisco Catalyst Center.",
        "response": "Source device '204.1.1.25' was not found in Cisco Catalyst Center."
    }
"""

import os
import re
import time
from fnmatch import fnmatchcase

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter import (
    CatalystCenterBase,
)


if HAS_YAML:
    class _BackupYamlDumper(yaml.Dumper):
        """YAML dumper that renders multi-line strings as literal blocks.

        Each template's recreated configuration is multi-line CLI text; literal block style
        keeps it readable in the backup file instead of collapsing it into a single escaped
        line.

        Anchors and aliases are disabled so a value that is reused across entries (such as
        the replacement serial-number list) is written out in full every time, keeping the
        generated files plain and self-contained for an operator to read and edit.
        """

        def ignore_aliases(self, data):
            return True

    def _represent_multiline_str(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    _BackupYamlDumper.add_representer(str, _represent_multiline_str)


class SwitchRefreshNonFabricPlaybookConfigGenerator(CatalystCenterBase):
    """
    Generate a deploy config for a non-fabric switch refresh.

    The class reads the templates Cisco Catalyst Center has actually deployed on a source
    switch - both profile-pushed and directly deployed - from the C(deployedTemplateDetails)
    endpoint, and recreates each from the realized configuration Catalyst Center rendered
    and pushed for it (interfaces remapped to the replacement, unwanted blocks or lines
    removed). Templates added with C(include_templates) are treated as operator add-ons and
    emitted by reference, listing every parameter they declare with an empty value for the
    operator to review. Which values are actually required is validated at deploy time by
    C(switch_refresh_non_fabric_workflow_manager), which renders each template through
    Catalyst Center's preview. The deploy config is written to a YAML file (plus a
    read-only backup) for the operator to run with that module.
    """

    # Project the recreated ``<name>_refresh`` templates are created under in the
    # generated switch_refresh_non_fabric_workflow_manager config.
    REFRESH_PROJECT_NAME = "switch_refresh_non_fabric_project"

    def __init__(self, module):
        self.supported_states = ["gathered"]
        super().__init__(module)
        # Validated inputs.
        self.source_device_ip = None
        self.destination_device_serial_number = None
        self.interface_migration = False
        self.interface_mappings = []
        self.exclude_templates = []
        self.include_templates = []
        self.exclude_commands = []
        self.file_path = None
        self.backup_file_path = None
        # Working state.
        self.template_records = []
        self.source_device_facts = {}
        self.duplicate_template_count = 0
        self.interface_conflict_warning = None

    def validate_input(self):
        """
        Validate the module inputs and capture them onto the instance so
        :meth:`get_want` (which runs next) can read them without re-parsing config.

        ``source_device_ip`` is mandatory; ``destination_device_serial_number`` is
        optional (when omitted, each deploy entry is written with an empty
        ``serial_numbers`` list for the operator to complete). ``interface_migration``
        gates ``interface_mappings``: when true the mappings are mandatory and applied,
        when false (the default) they are ignored. The optional ``exclude_templates``
        and ``exclude_commands`` inputs are normalised to empty lists when absent.
        ``interface_mappings`` is rejected only when it is truly
        ambiguous - a source interface listed more than once (mapped to two
        destinations), or two different sources renamed to the same destination. A
        self-map (a source mapped to its own name) is accepted and treated as a no-op.
        Swaps and chained renames are allowed, because the rename is applied in a single
        simultaneous pass.

        Returns:
            self: The instance with ``status`` and ``msg`` set.
        """
        self.log("Starting validation of input parameters.", "DEBUG")

        if not isinstance(self.config, dict) or not self.config:
            self.msg = (
                "Configuration must be a non-empty dictionary containing at "
                "least 'source_device_ip'."
            )
            self.set_operation_result("failed", False, self.msg, "ERROR")
            return self

        config = self.config
        if not config.get("source_device_ip"):
            self.msg = "Required parameter 'source_device_ip' is missing from config."
            self.set_operation_result("failed", False, self.msg, "ERROR")
            return self

        # Capture each input onto the instance for get_want to read, validating as we go.
        # destination_device_serial_number is optional: when omitted, the deploy config
        # is still generated with an empty top-level destination_device_serial_number
        # for the operator to complete before running
        # switch_refresh_non_fabric_workflow_manager.
        self.source_device_ip = config.get("source_device_ip")
        self.destination_device_serial_number = str(
            config.get("destination_device_serial_number") or ""
        ).strip()

        # interface_migration gates interface_mappings: when true the mappings are
        # mandatory and applied; when false (the default) they are ignored entirely.
        interface_migration = config.get("interface_migration", False)
        if isinstance(interface_migration, str):
            lowered = interface_migration.strip().lower()
            if lowered in ("true", "yes", "on", "1"):
                interface_migration = True
            elif lowered in ("false", "no", "off", "0", ""):
                interface_migration = False
        if not isinstance(interface_migration, bool):
            self.msg = (
                "Parameter 'interface_migration' must be a boolean (true or false); "
                "got '{0}'.".format(config.get("interface_migration"))
            )
            self.set_operation_result("failed", False, self.msg, "ERROR")
            return self
        self.interface_migration = interface_migration

        self.interface_mappings = config.get("interface_mappings") or []
        if self.interface_migration:
            if not self.interface_mappings:
                self.msg = (
                    "Parameter 'interface_mappings' is required when "
                    "'interface_migration' is true. Provide the source-to-destination "
                    "interface renames, or set 'interface_migration' to false."
                )
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self
            error = self._validate_interface_mappings()
            if error:
                self.msg = error
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self
        else:
            if self.interface_mappings:
                self.log(
                    "'interface_migration' is false; ignoring the {0} supplied "
                    "interface_mappings entry(ies).".format(
                        len(self.interface_mappings)
                    ),
                    "WARNING",
                )
            self.interface_mappings = []

        self.exclude_templates, error = self._normalize_template_selectors(
            config.get("exclude_templates"), "exclude_templates", project_required=False
        )
        if error:
            self.msg = error
            self.set_operation_result("failed", False, self.msg, "ERROR")
            return self
        self.exclude_templates = self.exclude_templates or []

        self.include_templates, error = self._normalize_template_selectors(
            config.get("include_templates"), "include_templates", project_required=True
        )
        if error:
            self.msg = error
            self.set_operation_result("failed", False, self.msg, "ERROR")
            return self
        self.include_templates = self.include_templates or []

        self.exclude_commands = config.get("exclude_commands") or []
        self.file_path = self.params.get("file_path")
        self.backup_file_path = self.params.get("backup_file_path")

        self.msg = "Successfully validated input for source device '{0}'.".format(
            self.source_device_ip
        )
        self.log(self.msg, "INFO")
        self.status = "success"
        return self

    def get_want(self, config):
        """
        Record the desired-state summary from the already-captured inputs.

        :meth:`validate_input` runs first and captures every input onto the instance;
        this records the minimal ``want`` used downstream. ``config`` is the same mapping
        that method consumed and is accepted for the standard module signature.

        Args:
            config (dict): The validated configuration.

        Returns:
            self: The instance with ``want`` populated.
        """
        self.want = {
            "source_device_ip": self.source_device_ip,
            "destination_device_serial_number": self.destination_device_serial_number,
        }
        self.log(
            "Desired state captured. source_device_ip='{0}', "
            "destination_device_serial_number='{1}', interface_migration={2}, "
            "interface_mappings={3}, exclude_templates={4}, include_templates={5}, "
            "exclude_commands={6}.".format(
                self.source_device_ip,
                self.destination_device_serial_number,
                self.interface_migration,
                len(self.interface_mappings),
                len(self.exclude_templates),
                len(self.include_templates),
                len(self.exclude_commands),
            ),
            "INFO",
        )
        return self

    def _normalize_template_selectors(self, raw, field_name, project_required):
        """
        Validate and normalise an ``exclude_templates``/``include_templates`` list.

        Both inputs identify templates by ``project_name`` and ``template_name`` (the
        same pair Catalyst Center uses), because a template name is only unique within a
        project. ``include_templates`` must name the project (the template is not yet on
        the device, so it has to be located and fetched), while ``project_name`` is
        optional for ``exclude_templates`` (omitting it excludes that name in every
        project).

        Args:
            raw: The value supplied in ``config`` (expected: list of mappings).
            field_name (str): The option name, used in error messages.
            project_required (bool): Whether ``project_name`` is mandatory per entry.

        Returns:
            tuple: ``(normalized_list, error_message)``. ``error_message`` is ``None`` on
            success; on failure the list is ``None`` and the message describes the fault.
        """
        self.log(
            "Starting normalization of '{0}' selector input: {1}".format(
                field_name, raw
            ),
            "DEBUG",
        )
        if raw is None:
            self.log(
                "No '{0}' provided; defaulting to an empty list.".format(field_name),
                "DEBUG",
            )
            return [], None
        if not isinstance(raw, list):
            return None, "'{0}' must be a list of mappings, each with 'template_name'{1}.".format(
                field_name,
                " and 'project_name'" if project_required else " (and optional 'project_name')",
            )

        normalized = []
        for item in raw:
            if not isinstance(item, dict):
                return None, (
                    "Each entry in '{0}' must be a mapping with 'template_name'{1}, "
                    "not '{2}'.".format(
                        field_name,
                        " and 'project_name'" if project_required else "",
                        type(item).__name__,
                    )
                )

            template_name = item.get("template_name")
            if not template_name or not str(template_name).strip():
                return None, "Each entry in '{0}' requires a non-empty 'template_name'.".format(
                    field_name
                )

            project_name = item.get("project_name")
            if project_required and (not project_name or not str(project_name).strip()):
                return None, (
                    "Each entry in '{0}' requires a non-empty 'project_name' so the "
                    "template can be located (a template name is unique only within a "
                    "project).".format(field_name)
                )

            normalized.append(
                {
                    "template_name": str(template_name).strip(),
                    "project_name": str(project_name).strip() if project_name else None,
                }
            )
        self.log(
            "Completed normalization of '{0}': {1} entry(ies) normalized: {2}".format(
                field_name, len(normalized), normalized
            ),
            "DEBUG",
        )
        return normalized, None

    def _as_list(self, response):
        """
        Normalise an SDK response into a plain list of records.

        The Catalyst Center SDK returns either a dict wrapped in a ``response`` key
        (whose value can be a list or a single object) or, for some endpoints, a bare
        list. This flattens all of those shapes into a list so callers can iterate
        uniformly.

        Args:
            response: The raw value returned by ``execute_get_request``.

        Returns:
            list: The records contained in the response (possibly empty).
        """
        if response is None:
            return []
        if isinstance(response, dict):
            if "response" in response:
                inner = response.get("response")
                if inner is None:
                    return []
                return inner if isinstance(inner, list) else [inner]
            return [response]
        if isinstance(response, list):
            return response
        return [response]

    def resolve_source_device(self):
        """
        Resolve the source device record from its management IP address.

        Returns:
            dict or None: The first matching device record, or None when the device is
            not found in Cisco Catalyst Center.
        """
        self.log(
            "Resolving source device by management IP '{0}'.".format(
                self.source_device_ip
            ),
            "INFO",
        )

        response = self.execute_get_request(
            "devices",
            "get_device_list",
            {"management_ip_address": self.source_device_ip},
        )

        records = self._as_list(response)
        if not records:
            self.log(
                "No device found in Catalyst Center for management IP "
                "'{0}'.".format(self.source_device_ip),
                "WARNING",
            )
            return None

        device_record = records[0]
        self.log(
            "Resolved device. id='{0}', hostname='{1}', family='{2}', "
            "type='{3}'.".format(
                device_record.get("id"),
                device_record.get("hostname"),
                device_record.get("family"),
                device_record.get("type"),
            ),
            "INFO",
        )
        return device_record

    def fetch_deployed_templates(self, device_id):
        """
        Fetch the templates Catalyst Center has actually deployed on the source device.

        Calls the ``deployedTemplateDetails`` endpoint directly - a raw REST ``GET``
        rather than a typed SDK method, because Catalyst Center does not yet publish this
        endpoint in its intent API manifest (there is no generated SDK wrapper for it). It
        returns every template deployed to the device - whether pushed through a network
        profile or deployed directly - together with the exact CLI Catalyst Center
        rendered and pushed (``realizedTemplateConfig``, with every parameter value
        already resolved), the deploy status, the deployed version and the resolved
        parameter map. This single call is the source of truth for what to recreate on
        the replacement switch, and it covers the direct (Day-N) deploys a site/profile
        walk cannot see.

        The endpoint returns each template's ``projectName`` as null, so the caller
        annotates the project from the template catalog (by template id) when it is
        needed for ``exclude_templates`` matching or reporting.

        Args:
            device_id (str): The source device id (uuid).

        Returns:
            list: One record per deployed template. Each carries at least
            ``templateName``, ``templateId``, ``realizedTemplateConfig``, ``status`` and
            ``paramNameVsValue`` (``projectName`` is null and enriched later).
        """
        self.log(
            "Fetching deployed template details for source device id='{0}'.".format(
                device_id
            ),
            "INFO",
        )
        endpoint = (
            "/dna/intent/api/v1/template-programmer/template/"
            "deployedTemplateDetails/{0}".format(device_id)
        )
        response = self.catalystcenter.execute_rest_api_call("GET", endpoint)

        templates = [
            record for record in self._as_list(response) if isinstance(record, dict)
        ]
        self.log(
            "Catalyst Center reports {0} deployed template(s) on source device "
            "id='{1}'.".format(len(templates), device_id),
            "INFO",
        )
        return templates

    def fetch_template_details(self, template_id):
        """
        Fetch the full body of a template.

        The details are used to read the template's ``deviceTypes`` so a template that
        is attached to the device's profile but targets a different product family (for
        example a wireless template inherited by a switch site) can be flagged as not
        applicable.

        Args:
            template_id (str): The CLI template id.

        Returns:
            dict or None: The template details, or None when unavailable.
        """
        self.log(
            "Starting template detail fetch for template id '{0}'.".format(template_id),
            "DEBUG",
        )
        response = self.execute_get_request(
            "configuration_templates",
            "get_template_details",
            {"template_id": template_id},
        )
        if isinstance(response, dict) and "response" in response:
            details = response.get("response")
        else:
            details = response
        if not details:
            self.log(
                "No template details returned for template id '{0}'.".format(
                    template_id
                ),
                "DEBUG",
            )
            return details
        self.log(
            "Completed template detail fetch for template id '{0}'.".format(template_id),
            "DEBUG",
        )
        return details

    def fetch_template_catalog(self):
        """
        Fetch a lightweight catalog of every template (id, name, project).

        The catalog is read once and used for two purposes: to annotate each assigned
        template with its project name (the profile-attached stubs carry only an id and a
        name), and to resolve ``include_templates`` entries - which name a project and a
        template - to concrete template ids. Only the ``name`` filter is ever passed to
        Catalyst Center (here, none at all), never ``project_name``, because passing the
        project filter triggers a controller-side error on some releases; project
        matching is done here instead.

        Returns:
            list: One dict per template with ``id``, ``name`` and ``project_name``.
        """
        self.log("Starting template catalog fetch (all projects).", "DEBUG")
        response = self.execute_get_request(
            "configuration_templates", "get_templates_details", {}
        )
        catalog = []
        for item in self._as_list(response):
            if not isinstance(item, dict):
                continue
            catalog.append(
                {
                    "id": item.get("templateId") or item.get("id"),
                    "name": item.get("name"),
                    "project_name": item.get("projectName"),
                }
            )
        self.log(
            "Fetched template catalog: {0} template(s) across all projects.".format(
                len(catalog)
            ),
            "INFO",
        )
        return catalog

    def _resolve_included_templates(self, catalog):
        """
        Resolve ``include_templates`` entries to template stubs to add to the run.

        Each entry names a project and a template; the matching catalog record supplies
        the template id. Matching is case-insensitive. An entry that matches nothing is
        reported (not fatal) so the operator sees the typo; an entry that matches more
        than one template in the same project uses the first and logs a warning.

        Args:
            catalog (list): The template catalog from ``fetch_template_catalog``.

        Returns:
            tuple: ``(stubs, not_found)``. ``stubs`` are shaped like the assigned
            template stubs (``id``, ``name``, ``projectName``, ``included=True``);
            ``not_found`` lists the unresolved ``project_name/template_name`` labels.
        """
        stubs = []
        not_found = []
        self.log(
            "Resolving {0} include_templates entry(ies) against the catalog.".format(
                len(self.include_templates)
            ),
            "DEBUG",
        )
        for index, entry in enumerate(self.include_templates, start=1):
            want_name = entry["template_name"].lower()
            want_project = (entry["project_name"] or "").lower()
            matches = [
                record
                for record in catalog
                if (record["name"] or "").lower() == want_name
                and (record["project_name"] or "").lower() == want_project
            ]
            label = "{0}/{1}".format(entry["project_name"], entry["template_name"])
            self.log(
                "include_templates entry {0} of {1}: resolving '{2}'.".format(
                    index, len(self.include_templates), label
                ),
                "DEBUG",
            )
            if not matches:
                not_found.append(label)
                self.log(
                    "include_templates: no template named '{0}' found in project "
                    "'{1}'; it will not be added.".format(
                        entry["template_name"], entry["project_name"]
                    ),
                    "WARNING",
                )
                continue
            if len(matches) > 1:
                self.log(
                    "include_templates: {0} templates named '{1}' found in project "
                    "'{2}'; using the first.".format(
                        len(matches), entry["template_name"], entry["project_name"]
                    ),
                    "WARNING",
                )
            match = matches[0]
            stubs.append(
                {
                    "id": match["id"],
                    "name": match["name"],
                    "projectName": match["project_name"],
                    "included": True,
                }
            )
            self.log(
                "include_templates: added template '{0}' from project '{1}' "
                "(id '{2}').".format(match["name"], match["project_name"], match["id"]),
                "INFO",
            )
        self.log(
            "Completed include_templates resolution: {0} added, {1} not found.".format(
                len(stubs), len(not_found)
            ),
            "DEBUG",
        )
        return stubs, not_found

    def _is_excluded(self, template_name, project_name):
        """
        Report whether a template is removed by ``exclude_templates``.

        An exclude entry matches when its ``template_name`` equals the template's name
        (case-insensitive). When the entry also names a project, the project must match
        too; when it omits the project, the name is excluded in every project. Exclusion
        always wins over ``include_templates`` - a template named in both is left out.

        Args:
            template_name (str): The candidate template's name.
            project_name (str or None): The candidate template's project.

        Returns:
            bool: True when an exclude entry matches.
        """
        self.log(
            "Checking exclude_templates for template '{0}' (project '{1}').".format(
                template_name, project_name
            ),
            "DEBUG",
        )
        name = (template_name or "").lower()
        project = (project_name or "").lower()
        for entry in self.exclude_templates:
            if entry["template_name"].lower() != name:
                continue
            entry_project = entry.get("project_name")
            if entry_project and entry_project.lower() != project:
                continue
            self.log(
                "Template '{0}' (project '{1}') matched exclude entry '{2}'.".format(
                    template_name, project_name, entry["template_name"]
                ),
                "DEBUG",
            )
            return True
        self.log(
            "Template '{0}' (project '{1}') matched no exclude_templates entry.".format(
                template_name, project_name
            ),
            "DEBUG",
        )
        return False

    def _is_template_applicable(self, details, device_family):
        """
        Report whether a template targets the source device's product family.

        A template attached to a site profile is not necessarily applicable to the
        device (the profile can be a wireless profile inherited by a switch site, for
        example). When the template declares one or more device families, the device's
        family must be among them. When the template declares none, it is treated as
        applicable.

        Args:
            details (dict or None): The template details from ``fetch_template_details``.
            device_family (str): The source device's product family.

        Returns:
            bool: True when the template is applicable to the device.
        """
        self.log(
            "Checking template applicability against device family '{0}'.".format(
                device_family
            ),
            "DEBUG",
        )
        if not isinstance(details, dict):
            self.log(
                "No template details available; treating template as applicable.",
                "DEBUG",
            )
            return True
        device_types = details.get("deviceTypes") or []
        families = {
            dt.get("productFamily")
            for dt in device_types
            if isinstance(dt, dict) and dt.get("productFamily")
        }
        if not families:
            self.log(
                "Template declares no device families; treating as applicable.",
                "DEBUG",
            )
            return True
        applicable = device_family in families
        self.log(
            "Template targets families {0}; device family '{1}' -> applicable={2}.".format(
                sorted(families), device_family, applicable
            ),
            "DEBUG",
        )
        return applicable

    def _collect_parameters(self, details):
        """
        List the parameter names a template declares, each with an empty value.

        Every parameter Catalyst Center reports for the template is listed with a blank
        value for the operator to complete. Required/optional classification is
        intentionally not emitted here: whether a value is actually required is validated
        at deploy time by rendering the template through Catalyst Center's preview (see
        the switch refresh workflow manager), which is the authoritative check. System
        variables the operator should leave blank are simply left blank - Catalyst Center
        resolves them during deployment and the preview ignores any value supplied for
        them.

        Args:
            details (dict or None): The template details from ``fetch_template_details``.

        Returns:
            list: One record per parameter with ``name`` and an empty ``value``, sorted by
            name so the generated file is byte-stable across runs.
        """
        names = []
        if isinstance(details, dict):
            for param in details.get("templateParams") or []:
                if not isinstance(param, dict):
                    continue
                name = param.get("parameterName")
                if name:
                    names.append(name)

        # Catalyst Center returns templateParams in a non-deterministic order; sort by
        # name so the generated file is byte-stable across runs (keeps the module
        # idempotent - identical Catalyst Center state re-renders identically).
        names.sort(key=lambda value: str(value).lower())
        parameters = [{"name": name, "value": ""} for name in names]
        self.log(
            "Collected {0} parameter name(s) for the template.".format(len(parameters)),
            "DEBUG",
        )
        return parameters

    def fetch_source_device_interfaces(self, device_id):
        """
        Retrieve the interface names Catalyst Center has discovered on the source device.

        Uses the typed SDK ``get_interface_info_by_id`` endpoint - the device's full
        interface inventory - and keeps only each record's name (``portName``). This is
        the authoritative list of interfaces that physically exist on the device, used to
        fail fast when an ``interface_mappings`` source interface does not exist.

        Args:
            device_id (str): The source device id.

        Returns:
            list: Interface names (for example ``GigabitEthernet1/0/1``) present on the
            device, in the order Catalyst Center returns them.
        """
        self.log(
            "Fetching interface inventory for source device id='{0}'.".format(
                device_id
            ),
            "INFO",
        )

        response = self.execute_get_request(
            "devices",
            "get_interface_info_by_id",
            {"device_id": device_id},
        )

        names = []
        for record in self._as_list(response):
            if not isinstance(record, dict):
                continue
            name = record.get("portName")
            if name:
                names.append(str(name))

        if not names:
            self.log(
                "Catalyst Center returned no interfaces for source device id='{0}'; "
                "any interface mapping will be reported as unmatched.".format(device_id),
                "WARNING",
            )
            return names

        self.log(
            "Source device '{0}' reports {1} interface(s).".format(
                device_id, len(names)
            ),
            "INFO",
        )
        return names

    def _normalize_cli_line(self, line):
        """
        Normalise a single CLI line for tolerant comparison.

        Leading/trailing whitespace is removed and any internal run of whitespace becomes
        a single space, so two lines are compared by meaning rather than exact spacing.

        Args:
            line (str): A raw CLI line.

        Returns:
            str: The normalised line.
        """
        return " ".join(line.split())

    def _matches_any_glob(self, text, patterns):
        """
        Report whether a string matches any of the supplied glob patterns.

        The operator supplies shell-style wildcard patterns (``*`` for any run of
        characters, ``?`` for a single character) rather than regular expressions.
        Matching is case-insensitive and applied to the whole string, so a substring
        match requires surrounding stars (``*hostname*``).

        Args:
            text (str): The line to test.
            patterns (list): Glob patterns to test against.

        Returns:
            bool: True when any pattern matches.
        """
        if not patterns:
            return False
        lowered = text.lower()
        for pattern in patterns:
            if pattern and fnmatchcase(lowered, str(pattern).lower()):
                return True
        return False

    def _filter_cli_text(self, text):
        """
        Remove excluded commands from CLI text, preserving formatting.

        ``exclude_commands`` drops an individual matching line. The original indentation
        and ``!`` separators are preserved so the surviving configuration stays readable.

        Args:
            text (str): The CLI text to filter.

        Returns:
            tuple: ``(filtered_text, excluded_count)``.
        """
        self.log(
            "Starting CLI filtering ({0} exclude_command(s)).".format(
                len(self.exclude_commands)
            ),
            "DEBUG",
        )
        if not self.exclude_commands:
            self.log(
                "No exclude_commands configured; CLI text unchanged.",
                "DEBUG",
            )
            return text, 0

        kept = []
        excluded_count = 0

        for raw_line in text.splitlines():
            if not raw_line.strip():
                kept.append(raw_line)
                continue

            normalized = self._normalize_cli_line(raw_line)

            # A bare '!' separator carries no meaning and is kept as-is.
            if normalized == "!":
                kept.append(raw_line)
                continue

            if self._matches_any_glob(normalized, self.exclude_commands):
                excluded_count += 1
                continue

            kept.append(raw_line)

        self.log(
            "Completed CLI filtering: {0} line(s) excluded.".format(excluded_count),
            "DEBUG",
        )
        return "\n".join(kept), excluded_count

    def _validate_interface_mappings(self):
        """
        Reject malformed or truly ambiguous ``interface_mappings`` before any rename runs.

        Each entry must be a mapping that names a non-empty ``source_interface_name`` and a
        non-empty ``destination_interface_name``. The set as a whole must also be unambiguous:
        no ``source_interface_name`` may be listed more than once (a duplicate source has no
        single correct destination), and no two different sources may be renamed to the same
        ``destination_interface_name`` (that would configure one interface twice with
        conflicting settings). A self-map (a source mapped to its own name) is
        accepted and treated as a no-op - the same as not listing the interface at all;
        :meth:`_build_interface_mapping_pairs` drops it so it never produces a rename.

        Swaps (``A`` to ``B`` together with ``B`` to ``A``) and chains (``A`` to ``B``
        together with ``B`` to ``C``) are allowed. :meth:`_remap_interfaces_in_text`
        rewrites the whole set in a single simultaneous pass, so an interface may safely
        appear as both a source and a destination without the names cascading into one
        another. Comparison is case-insensitive.

        Returns:
            str or None: An error message when the input is invalid, otherwise None.
        """
        if not self.interface_mappings:
            return None
        if not isinstance(self.interface_mappings, list):
            return (
                "'interface_mappings' must be a list of mappings, each with a "
                "'source_interface_name' and a 'destination_interface_name'."
            )

        sources = []
        destinations = []
        display = {}
        for entry in self.interface_mappings:
            if not isinstance(entry, dict):
                return (
                    "Each entry in 'interface_mappings' must be a mapping with a "
                    "'source_interface_name' and a 'destination_interface_name', not "
                    "'{0}'.".format(type(entry).__name__)
                )
            source = self._normalize_cli_line(str(entry.get("source_interface_name") or ""))
            destination = self._normalize_cli_line(
                str(entry.get("destination_interface_name") or "")
            )
            if not source or not destination:
                return (
                    "Each entry in 'interface_mappings' requires a non-empty "
                    "'source_interface_name' and a non-empty "
                    "'destination_interface_name' (got source_interface_name='{0}', "
                    "destination_interface_name='{1}').".format(
                        source, destination
                    )
                )
            sources.append(source.lower())
            display.setdefault(source.lower(), source)
            # Only a real rename (source != destination) claims a destination name; a
            # self-map keeps the interface's own name and is dropped before any rename.
            if source.lower() != destination.lower():
                destinations.append(destination.lower())
                display.setdefault(destination.lower(), destination)

        duplicate_sources = sorted(
            {display[name] for name in sources if sources.count(name) > 1}
        )
        if duplicate_sources:
            return (
                "Interface mapping lists the same source interface more than once "
                "({0}); each source interface may be mapped to only one "
                "destination.".format(", ".join(duplicate_sources))
            )

        duplicate_destinations = sorted(
            {display[name] for name in destinations if destinations.count(name) > 1}
        )
        if duplicate_destinations:
            return (
                "Interface mapping renames more than one source interface to the same "
                "destination interface ({0}); each destination interface may be the "
                "target of only one source, otherwise the recreated templates would "
                "configure the same interface with conflicting settings.".format(
                    ", ".join(duplicate_destinations)
                )
            )

        return None

    def _build_interface_mapping_pairs(self):
        """
        Build the cleaned list of source/destination interface rename pairs.

        Names are whitespace-normalised. The default is an identity map: with no mapping
        the result is empty and the rename is a no-op (every interface keeps its name). A
        self-map (source equal to its destination, case-insensitively) is dropped, so it
        behaves exactly like an interface that was never listed - no phantom rename is
        recorded and the interface keeps its name.

        Returns:
            list: Tuples of ``(source_name, destination_name)``.
        """
        self.log(
            "Building interface rename pairs from {0} mapping entry(ies).".format(
                len(self.interface_mappings)
            ),
            "DEBUG",
        )
        pairs = []
        for entry in self.interface_mappings:
            if not isinstance(entry, dict):
                continue
            source = self._normalize_cli_line(str(entry.get("source_interface_name") or ""))
            destination = self._normalize_cli_line(
                str(entry.get("destination_interface_name") or "")
            )
            if source and destination and source.lower() != destination.lower():
                pairs.append((source, destination))
        self.log(
            "Built {0} interface rename pair(s) (self-maps dropped): {1}.".format(
                len(pairs), pairs
            ),
            "DEBUG",
        )
        return pairs

    def _unmatched_source_interfaces(self, device_interface_names):
        """
        Return the ``interface_mappings`` source interfaces the source device does not
        have.

        A source interface counts as present when it matches a device interface exactly,
        or when it is the parent of a sub-interface the device has - mapping
        ``GigabitEthernet1/0/1`` is satisfied by ``GigabitEthernet1/0/1.100``. This
        mirrors :meth:`_remap_interfaces_in_text`, which renames a mapped parent together
        with its sub-interfaces, so validation never rejects a mapping the rename would
        have applied. Comparison is case-insensitive and whitespace-normalised.

        Args:
            device_interface_names (list): Interface names present on the source device.

        Returns:
            list: The unmatched ``source_interface_name`` values, in their original casing and
            input order, with duplicates removed.
        """
        self.log(
            "Checking {0} device interface(s) against interface_mappings "
            "source(s).".format(len(device_interface_names)),
            "DEBUG",
        )
        present = {
            self._normalize_cli_line(str(name)).lower()
            for name in device_interface_names
            if name
        }
        present.discard("")

        unmatched = []
        seen = set()
        for source, _destination in self._build_interface_mapping_pairs():
            source_lower = source.lower()
            if source_lower in seen:
                continue
            seen.add(source_lower)
            is_present = source_lower in present or any(
                name.startswith(source_lower + ".")
                and name[len(source_lower) + 1:].isdigit()
                for name in present
            )
            if not is_present:
                unmatched.append(source)
        self.log(
            "Interface source existence check complete: {0} unmatched source(s): "
            "{1}.".format(len(unmatched), unmatched),
            "DEBUG",
        )
        return unmatched

    def _remap_interfaces_in_text(self, text, pairs):
        """
        Rewrite interface names in CLI text from source to destination.

        Replacement is whole-token and case-insensitive: a boundary check on either side
        (excluding the characters that make up an interface name) ensures ``Vlan20`` does
        not match inside ``Vlan200``. A sub-interface of a mapped parent is renamed
        automatically - when ``Gi1/0/1`` is mapped, ``Gi1/0/1.100`` becomes
        ``<destination>.100`` (the parent is swapped and the sub-interface unit is kept),
        so the operator never has to list sub-interfaces. Renaming an interface header
        moves the whole indented block with it.

        The whole set of renames is applied in a single simultaneous pass: every source
        name is matched once against the original text and its replacement is never
        re-scanned. Swaps (``A`` to ``B`` together with ``B`` to ``A``) and chains
        (``A`` to ``B`` together with ``B`` to ``C``) therefore resolve correctly - names
        can never cascade into one another.

        Template variable references are preserved verbatim - Velocity ``$name`` and
        ``${name}`` and Jinja ``{{ name }}`` spans are detected and skipped - so a
        parameterised interface keeps its variable name and still resolves at deploy
        time. Only literal interface names outside those spans are renamed.

        Args:
            text (str): The CLI text to transform.
            pairs (list): ``(source_name, destination_name)`` tuples.

        Returns:
            tuple: ``(remapped_text, applied)`` where applied lists the pairs that
            actually changed something.
        """
        self.log(
            "Starting interface remap in CLI text ({0} pair(s), {1} "
            "character(s)).".format(len(pairs), len(text) if text else 0),
            "DEBUG",
        )
        if not pairs:
            self.log("No interface rename pairs; CLI text left unchanged.", "DEBUG")
            return text, []

        # Interface names are renamed only in the literal CLI. A match touching an
        # interface-name character on either side is a partial hit and is skipped
        # (so ``Vlan20`` never rewrites inside ``Vlan200``). An optional trailing
        # ``.<unit>`` is captured so a sub-interface of a mapped parent (for example
        # ``GigabitEthernet1/0/1.100`` when ``GigabitEthernet1/0/1`` is mapped) is
        # renamed too - the parent is swapped and the sub-interface unit is preserved.
        name_char = r"[A-Za-z0-9/._-]"
        # Each source (lower-cased) resolves to its original-cased pair. Duplicate sources
        # are rejected upfront, so the first binding for a source is the only one.
        lookup = {}
        for source, destination in pairs:
            lookup.setdefault(source.lower(), (source, destination))
        # One alternation over every source name, longest first so a longer name wins over
        # a shorter one it starts with. Matching the whole set in a single pattern lets one
        # ``sub`` rewrite them simultaneously: each original name is matched once and its
        # replacement is never re-scanned, so a swap (``A`` -> ``B`` with ``B`` -> ``A``) or
        # a chain (``A`` -> ``B`` with ``B`` -> ``C``) never cascades one rename into the next.
        ordered_sources = sorted(
            (source for source, _replacement in pairs), key=len, reverse=True
        )
        alternation = "|".join(re.escape(name) for name in ordered_sources)
        matcher = re.compile(
            r"(?<!" + name_char + r")(" + alternation + r")"
            + r"(\.\d+)?(?!" + name_char + r")",
            re.IGNORECASE,
        )
        # Template variable references are kept verbatim: Velocity ``$name`` / ``${name}``
        # and Jinja ``{{ name }}`` spans are matched here and left untouched, so a
        # parameterised interface keeps its variable name.
        var_pattern = re.compile(r"\{\{.*?\}\}|\$\{[^{}]*\}|\$[A-Za-z_][A-Za-z0-9_]*")
        applied_pairs = set()

        def replace_match(match):
            # The matched parent (case-insensitive) selects its destination; any captured
            # sub-interface unit (``.100``) is kept and only the parent portion is swapped.
            source, destination = lookup[match.group(1).lower()]
            applied_pairs.add((source, destination))
            return destination + (match.group(2) or "")

        parts = []
        cursor = 0
        for match in var_pattern.finditer(text):
            parts.append(matcher.sub(replace_match, text[cursor:match.start()]))
            parts.append(match.group(0))
            cursor = match.end()
        parts.append(matcher.sub(replace_match, text[cursor:]))
        result = "".join(parts)

        applied = [
            {
                "source_interface_name": source,
                "destination_interface_name": destination,
            }
            for source, destination in pairs
            if (source, destination) in applied_pairs
        ]
        self.log(
            "Completed interface remap: {0} of {1} pair(s) applied: {2}.".format(
                len(applied), len(pairs), applied
            ),
            "DEBUG",
        )
        return result, applied

    def build_template_records(
        self, deployed_templates, included_stubs, device_family
    ):
        """
        Build one record per template to reapply to the replacement switch.

        Two sources feed the playbook:

        - The templates Catalyst Center has actually deployed on the source device, read
          in one call from ``deployedTemplateDetails`` (see
          :meth:`fetch_deployed_templates`). Each already carries the exact CLI Catalyst
          Center rendered and pushed (``realizedTemplateConfig``, every parameter value
          resolved), so it is recreated directly - the excluded commands are
          dropped and the interface names rewritten, and there are no parameter values for
          the operator to fill (the realized CLI is already fully resolved). A
          deployed template that matches ``exclude_templates`` is left out; one that
          returned no realized configuration, or whose deploy is any status other than
          ``SUCCESS`` (for example ``FAILURE``, ``IN_PROGRESS``, or ``PARTIAL_SUCCESS``),
          is left out instead of being recreated blindly.
        - The templates the operator pulled in with ``include_templates`` (add-ons). These
          are deployed by reference: their details are fetched, applicability is checked
          against the device family, and every parameter they declare is listed with an
          empty value. They are processed first, so a template that is both deployed and
          explicitly included is emitted by reference (its add-on behaviour) rather than
          recreated from realized config.

        Exclusion always wins - a template named in both ``include_templates`` and
        ``exclude_templates`` is left out.

        Args:
            deployed_templates (list): Deployed-template records from
                ``fetch_deployed_templates`` (project already annotated by the caller).
            included_stubs (list): ``include_templates`` stubs resolved from the catalog.
            device_family (str): The source device's product family.

        Returns:
            list: The per-template records (also stored on ``self.template_records``).
        """
        self.log(
            "Starting template record build ({0} deployed template(s), {1} "
            "include_templates add-on(s)).".format(
                len(deployed_templates or []), len(included_stubs or [])
            ),
            "DEBUG",
        )
        pairs = self._build_interface_mapping_pairs()
        if not pairs:
            self.log(
                "No interface_mappings supplied - identity (same-name) default applies.",
                "INFO",
            )

        records = []
        seen_template_ids = set()

        # endTime per deployed template, so an include that is also deployed can keep its
        # source deploy-order slot instead of being appended with the add-ons.
        deployed_end_times = {}
        for deployed in deployed_templates or []:
            if isinstance(deployed, dict):
                deployed_id = deployed.get("templateId") or deployed.get("id")
                if deployed_id:
                    deployed_end_times[deployed_id] = deployed.get("endTime")

        # 1) include_templates add-ons: deployed by reference. Processed first so that a
        #    template that is both deployed and explicitly included keeps its by-reference
        #    behaviour instead of being recreated from realized config.
        included_stubs = included_stubs or []
        self.log(
            "Processing {0} include_templates add-on(s).".format(len(included_stubs)),
            "DEBUG",
        )
        for index, stub in enumerate(included_stubs, start=1):
            if not isinstance(stub, dict):
                self.log("Add-on {0}: not a mapping; skipping.".format(index), "DEBUG")
                continue
            template_id = stub.get("id") or stub.get("templateId")
            template_name = stub.get("name") or template_id
            project_name = stub.get("projectName")
            if template_id:
                seen_template_ids.add(template_id)
            self.log(
                "Add-on {0} of {1}: evaluating include_templates template '{2}' "
                "(project '{3}').".format(
                    index, len(included_stubs), template_name, project_name
                ),
                "DEBUG",
            )

            record = {
                "template_id": template_id,
                "template_name": template_name,
                "project_name": project_name,
                "included": True,
                "applicable": True,
                "matched": False,
                "excluded": False,
                "excluded_count": 0,
                "interfaces_remapped": [],
                "config_text": "",
                "language": None,
                "parameters": [],
                "composite": False,
                "end_time": deployed_end_times.get(template_id),
            }

            # Exclusion wins over include_templates - a template named in both is left out.
            if self._is_excluded(template_name, project_name):
                record["excluded"] = True
                self.log(
                    "Template '{0}' (project '{1}') matches exclude_templates - "
                    "skipping; it is left out of the playbook.".format(
                        template_name, project_name
                    ),
                    "INFO",
                )
                records.append(record)
                continue

            details = self.fetch_template_details(template_id)
            if isinstance(details, dict):
                record["language"] = details.get("language")
            record["applicable"] = self._is_template_applicable(details, device_family)
            if not record["applicable"]:
                self.log(
                    "include_templates add-on '{0}' targets a different product family "
                    "than '{1}' - skipping (not applicable to this switch).".format(
                        template_name, device_family
                    ),
                    "INFO",
                )
                records.append(record)
                continue

            # List every parameter the template declares with an empty value; the add-on
            # is deployed by reference with these parameters.
            record["parameters"] = self._collect_parameters(details)
            if isinstance(details, dict) and details.get("composite"):
                record["composite"] = True
                self.log(
                    "include_templates add-on '{0}' (project '{1}') is a composite "
                    "template; member parameters are not listed and must be set in "
                    "Catalyst Center.".format(template_name, project_name),
                    "WARNING",
                )
            self.log(
                "include_templates add-on '{0}' (project '{1}') will be deployed by "
                "reference.".format(template_name, project_name),
                "INFO",
            )
            records.append(record)

        # 2) Templates Catalyst Center actually deployed on the source device. Each row
        #    carries its already-resolved CLI, so it is recreated directly.
        deployed_templates = deployed_templates or []
        self.log(
            "Processing {0} deployed template(s) from the source device.".format(
                len(deployed_templates)
            ),
            "DEBUG",
        )
        for index, deployed in enumerate(deployed_templates, start=1):
            if not isinstance(deployed, dict):
                self.log(
                    "Deployed {0}: not a mapping; skipping.".format(index), "DEBUG"
                )
                continue
            template_id = deployed.get("templateId") or deployed.get("id")
            template_name = deployed.get("templateName") or template_id
            project_name = deployed.get("projectName")
            self.log(
                "Deployed {0} of {1}: evaluating template '{2}' (project '{3}').".format(
                    index, len(deployed_templates), template_name, project_name
                ),
                "DEBUG",
            )

            # Skip a template already emitted as an include add-on, and collapse any
            # duplicate deployment rows for the same template.
            if template_id and template_id in seen_template_ids:
                self.log(
                    "Deployed template '{0}' already handled (include_templates add-on "
                    "or duplicate deployment row) - skipping.".format(template_name),
                    "DEBUG",
                )
                continue
            if template_id:
                seen_template_ids.add(template_id)

            record = {
                "template_id": template_id,
                "template_name": template_name,
                "project_name": project_name,
                "included": False,
                "applicable": True,
                "matched": False,
                "excluded": False,
                "excluded_count": 0,
                "interfaces_remapped": [],
                "config_text": "",
                "language": None,
                "parameters": [],
                "end_time": deployed.get("endTime"),
            }

            if self._is_excluded(template_name, project_name):
                record["excluded"] = True
                self.log(
                    "Template '{0}' (project '{1}') matches exclude_templates - "
                    "skipping; it is left out of the playbook.".format(
                        template_name, project_name
                    ),
                    "INFO",
                )
                records.append(record)
                continue

            realized = deployed.get("realizedTemplateConfig")
            status = str(deployed.get("status") or "").upper()
            if not realized or not str(realized).strip():
                self.log(
                    "Deployed template '{0}' returned no realized configuration "
                    "(status '{1}') - left out.".format(
                        template_name, status or "unknown"
                    ),
                    "INFO",
                )
                records.append(record)
                continue

            if status != "SUCCESS":
                self.log(
                    "Deployed template '{0}' is in state '{1}', not a successful "
                    "deploy - only SUCCESS templates are recreated, so it is left "
                    "out.".format(
                        template_name, status or "unknown"
                    ),
                    "INFO",
                )
                records.append(record)
                continue

            # Recreate the deployed config: drop excluded commands, then rewrite
            # the source interface names to the replacement's.
            filtered_text, excluded_count = self._filter_cli_text(str(realized))
            final_text, applied = self._remap_interfaces_in_text(filtered_text, pairs)
            if not final_text.strip():
                self.log(
                    "Deployed template '{0}' has no configuration left to deploy after "
                    "applying exclude_commands (status '{1}') - left "
                    "out.".format(template_name, status or "unknown"),
                    "INFO",
                )
                records.append(record)
                continue
            record.update(
                {
                    "matched": True,
                    "excluded_count": excluded_count,
                    "interfaces_remapped": applied,
                    "config_text": final_text,
                }
            )
            self.log(
                "Deployed template '{0}' (status '{1}'): realized config recreated, "
                "{2} line(s) excluded, {3} interface rename(s).".format(
                    template_name, status or "unknown", excluded_count, len(applied)
                ),
                "INFO",
            )
            records.append(record)

        # Deploy order matters: reapply templates in the sequence the source received
        # them. Sort the templates Catalyst Center deployed on the source by endTime, then
        # append include_templates add-ons - which have no deploy timestamp - last, in the
        # operator's listed order. An include that is also a deployed template carries that
        # template's endTime, so it keeps its source slot instead of moving to the end.
        def _end_time_text(record):
            raw = record.get("end_time")
            if raw is None or str(raw).strip() == "":
                return None
            return str(raw).strip()

        timed = [
            (index, record)
            for index, record in enumerate(records)
            if _end_time_text(record) is not None
        ]
        untimed = [record for record in records if _end_time_text(record) is None]
        if all(_end_time_text(record).lstrip("-").isdigit() for _index, record in timed):
            timed.sort(key=lambda item: (int(_end_time_text(item[1])), item[0]))
        else:
            timed.sort(key=lambda item: (_end_time_text(item[1]), item[0]))
        records = [record for _index, record in timed] + untimed

        # Collapse recreated templates whose final CLI is byte-identical: deploying the
        # same realized configuration twice (for example a template and the
        # already-refreshed copy of it a previous run left on the source) is redundant.
        self._mark_duplicate_configs(records)

        self.template_records = records
        self.log(
            "Completed template record build: {0} record(s) built "
            "({1} recreated, {2} by-reference add-on(s), {3} left out).".format(
                len(records),
                sum(1 for record in records if record.get("matched")),
                sum(
                    1
                    for record in records
                    if record.get("included") and not record.get("excluded")
                ),
                sum(
                    1
                    for record in records
                    if not record.get("matched")
                    and not (record.get("included") and not record.get("excluded"))
                ),
            ),
            "DEBUG",
        )
        return records

    def _mark_duplicate_configs(self, records):
        """
        Flag recreated templates whose final CLI duplicates an earlier one.

        Two deployed templates can carry byte-identical realized configuration - most
        often a template and the ``<name>_refresh`` copy a previous refresh run left on
        the source switch. Recreating and deploying both pushes the same CLI twice, so
        the later duplicate is marked (and left out of the deploy config by
        :meth:`_deploy_records`) while the first is kept. Only ``matched`` records
        (recreated from realized config) are compared.

        Args:
            records (list): The template records, in deploy order (mutated in place).

        Returns:
            int: The number of records marked as duplicates.
        """
        seen = {}
        duplicate_count = 0
        for record in records:
            if not record.get("matched"):
                continue
            key = "\n".join(
                line.rstrip()
                for line in (record.get("config_text") or "").splitlines()
            ).strip()
            if not key:
                continue
            first = seen.get(key)
            if first is None:
                seen[key] = record
                continue
            record["duplicate"] = True
            record["duplicate_of"] = first.get("template_name")
            duplicate_count += 1
            self.log(
                "Recreated template '{0}' has the same configuration as '{1}' - "
                "collapsing the duplicate; it is left out of the deploy config.".format(
                    record.get("template_name"), first.get("template_name")
                ),
                "INFO",
            )
        self.duplicate_template_count = duplicate_count
        self.log(
            "Duplicate-config check complete: {0} recreated template(s) "
            "collapsed.".format(duplicate_count),
            "DEBUG",
        )
        return duplicate_count

    def _extract_interface_stanzas(self, text):
        """
        Map each interface configured in CLI text to its normalised stanza body.

        An ``interface <name>`` header at column 0 starts a stanza; the indented lines
        that follow (until the next column-0 line) are its body. Names are lower-cased for
        comparison and bodies are whitespace-normalised, so two templates that configure
        the same interface identically compare equal while different settings do not.

        Args:
            text (str): The recreated CLI text.

        Returns:
            dict: ``{interface_name_lower: (display_name, normalised_body)}``.
        """
        stanzas = {}
        current_name = None
        current_display = None
        body_lines = []

        def _flush():
            if current_name is not None:
                stanzas[current_name] = (
                    current_display,
                    "\n".join(body_lines).strip(),
                )

        for raw_line in (text or "").splitlines():
            stripped = raw_line.strip()
            normalized = self._normalize_cli_line(raw_line)
            if normalized.lower().startswith("interface "):
                _flush()
                current_display = normalized[len("interface "):].strip()
                current_name = current_display.lower()
                body_lines = []
                continue
            if current_name is None:
                continue
            # A non-indented, non-separator line at column 0 ends the current stanza.
            if stripped and stripped != "!" and raw_line[:1] not in (" ", "\t"):
                _flush()
                current_name = None
                current_display = None
                body_lines = []
                continue
            if stripped and stripped != "!":
                body_lines.append(normalized)
        _flush()
        return stanzas

    def _detect_interface_conflicts(self, records):
        """
        Find interfaces configured by more than one recreated template with different
        settings.

        After interface renames are applied, two templates can end up configuring the same
        interface - for example when ``interface_mappings`` renames two different source
        interfaces to the same destination, or renames one interface onto another that a
        second template already configures. Deploying both would push conflicting settings
        to that interface, so the caller fails the run.

        Only ``matched`` records (recreated from realized config) are compared; by-reference
        add-ons carry no resolved CLI. An interface configured identically by two templates
        is redundant, not conflicting, and is not reported here.

        Args:
            records (list): The matched template records to compare, in deploy order.

        Returns:
            list: ``(interface_display_name, first_template, second_template)`` tuples,
            one per conflicting interface.
        """
        owner = {}
        conflicts = []
        reported = set()
        for record in records:
            if not record.get("matched"):
                continue
            label = record.get("template_name") or "(unnamed template)"
            for name_lower, (display, body) in self._extract_interface_stanzas(
                record.get("config_text") or ""
            ).items():
                if name_lower not in owner:
                    owner[name_lower] = (label, body)
                    continue
                prev_label, prev_body = owner[name_lower]
                if body != prev_body and name_lower not in reported:
                    reported.add(name_lower)
                    conflicts.append((display, prev_label, label))
        return conflicts

    def _template_label(self, record):
        """
        Return a label that uniquely identifies a template in the response lists.

        A template name is unique only within its project, so two templates in
        different projects can share a name. This returns ``project_name/template_name``
        (the same format as ``templates_include_not_found``) so the operator can tell
        them apart; when the project is unknown it falls back to the bare name.

        Args:
            record (dict): A template record with ``template_name`` and ``project_name``.

        Returns:
            str: ``"project_name/template_name"``, or the template name if no project.
        """
        template_name = record.get("template_name")
        project_name = record.get("project_name")
        if project_name:
            return "{0}/{1}".format(project_name, template_name)
        return template_name

    def _deploy_records(self):
        """
        Select the templates that belong in the deploy config.

        The generated file drives the
        ``cisco.catalystcenter.switch_refresh_non_fabric_workflow_manager``
        module, whose job is to reapply configuration to the replacement switch. Only two
        kinds of template belong there: templates that were actually deployed on the
        source switch (so the replacement gets what the original had), and templates the
        operator explicitly pulled in with ``include_templates``. Excluded templates,
        non-applicable add-ons, and templates whose last deploy was not ``SUCCESS`` are
        left out.

        Returns:
            list: The template records to emit as ``deploy_template`` entries.
        """
        records = [
            record
            for record in self.template_records
            if not record.get("excluded")
            and not record.get("duplicate")
            and record.get("applicable")
            and (record.get("matched") or record.get("included"))
        ]
        self.log(
            "Selected {0} of {1} template record(s) for the deploy config.".format(
                len(records), len(self.template_records)
            ),
            "DEBUG",
        )
        return records

    def _refresh_template_name(self, source_name, used_names):
        """
        Build a unique recreated-template name for the refresh project.

        The recreated template is normally ``<source_name>_refresh``. When the source name
        already ends in ``_refresh`` (for example a template a previous refresh run left on
        the switch) the suffix is not added again, avoiding ``_refresh_refresh``. The name
        is then made unique within the generated deploy config by appending ``_2``, ``_3``
        and so on, so two source templates can never collide on one recreated name in the
        single ``switch_refresh_non_fabric_project``.

        Args:
            source_name (str): The source template name.
            used_names (set): Lower-cased recreated names already used this run (updated
                in place).

        Returns:
            str: The unique recreated template name.
        """
        base = (source_name or "").strip()
        if base.lower().endswith("_refresh"):
            candidate = base
        else:
            candidate = "{0}_refresh".format(base)
        unique = candidate
        suffix = 2
        while unique.lower() in used_names:
            unique = "{0}_{1}".format(candidate, suffix)
            suffix += 1
        used_names.add(unique.lower())
        return unique

    def _build_deploy_entries(self):
        """
        Build the ``switch_refresh_non_fabric_workflow_manager`` ``config:`` entries.

        This is the machine-generated deploy content shared by the deploy config file and
        its read-only backup copy: a list of items, one per template to reapply to the
        replacement switch.

        A template that was deployed on the source switch is recreated from its realized
        configuration - the CLI Catalyst Center actually rendered and pushed, with
        interface names already renamed to the replacement's interfaces - as a
        ``configuration_templates`` entry (project ``switch_refresh_non_fabric_project``,
        template ``<name>_refresh``) paired with a ``deploy_template`` entry that pushes it
        to the replacement by serial number. Because the content is already-resolved
        configuration, there are no parameter values to fill.

        A template pulled in with ``include_templates`` is an add-on: it is deployed by
        reference, so it is added even when the same template is already on the source
        switch. A ``deploy_template`` entry names the original project and template and
        lists every parameter the template declares with an empty value. Whether a value
        is actually required is validated at deploy time by the switch refresh workflow
        manager, which renders the template through Catalyst Center's preview; system
        variables left blank are resolved by Catalyst Center during deployment.

        Returns:
            list: The ``config:`` entries for
            ``switch_refresh_non_fabric_workflow_manager``.
        """
        self.log(
            "Building switch_refresh_non_fabric_workflow_manager deploy entries.",
            "DEBUG",
        )
        product_family = self.source_device_facts.get("family") or "Switches and Hubs"
        # The workflow manager recreates each template on the replacement, and Catalyst
        # Center requires a software type to create a template. The replacement runs the
        # same software as the source switch, so reuse the source device's software type
        # (falling back to IOS-XE, the switch default) for every recreated template.
        software_type = self.source_device_facts.get("software_type") or "IOS-XE"
        deploy_records = self._deploy_records()
        self.log(
            "Composing {0} deploy entry(ies) from the selected template "
            "record(s).".format(len(deploy_records)),
            "DEBUG",
        )
        entries = []
        used_refresh_names = set()
        for index, record in enumerate(deploy_records, start=1):
            if record.get("matched"):
                # Recreate the source config (interfaces already renamed) as a new
                # template, then deploy that template to the replacement by serial.
                refresh_name = self._refresh_template_name(
                    record["template_name"], used_refresh_names
                )
                self.log(
                    "Deploy entry {0} of {1}: recreating template '{2}' as '{3}' and "
                    "deploying by serial.".format(
                        index,
                        len(deploy_records),
                        record["template_name"],
                        refresh_name,
                    ),
                    "DEBUG",
                )
                entries.append(
                    {
                        "configuration_templates": {
                            "project_name": self.REFRESH_PROJECT_NAME,
                            "template_name": refresh_name,
                            "language": record.get("language") or "VELOCITY",
                            "software_type": software_type,
                            "device_types": [{"product_family": product_family}],
                            "template_content": record.get("config_text") or "",
                        },
                        "deploy_template": {
                            "project_name": self.REFRESH_PROJECT_NAME,
                            "template_name": refresh_name,
                        },
                    }
                )
                continue

            # include_templates add-on: emitted by reference with no running-config
            # comparison, so deploy the original and list every parameter it declares
            # with an empty value. Whether a value is actually required is validated at
            # deploy time by the workflow manager's Catalyst Center preview; system
            # variables left blank are resolved by Catalyst Center during deployment.
            template_parameters = [
                {"param_name": parameter.get("name"), "param_value": ""}
                for parameter in record.get("parameters") or []
            ]
            self.log(
                "Deploy entry {0} of {1}: adding by-reference template '{2}' "
                "(project '{3}') with {4} parameter(s) to fill.".format(
                    index,
                    len(deploy_records),
                    record["template_name"],
                    record.get("project_name"),
                    len(template_parameters),
                ),
                "DEBUG",
            )
            entries.append(
                {
                    "deploy_template": {
                        "project_name": record.get("project_name"),
                        "template_name": record["template_name"],
                        "template_parameters": template_parameters,
                    }
                }
            )
        self.log(
            "Built {0} deploy entry(ies).".format(len(entries)),
            "DEBUG",
        )
        return entries

    def _render_deploy_config(self, entries):
        """
        Render the ``config:`` entries to YAML text.

        After the YAML is produced, a fill-in hint is appended to the blank
        ``destination_device_serial_number`` line so the operator knows to complete it.
        YAML comments are ignored when the file is loaded, so they never affect the
        deploy.

        Args:
            entries (list): The entries from :meth:`_build_deploy_entries`.

        Returns:
            str: The YAML body (no comment header).
        """
        serial = self.destination_device_serial_number
        body = yaml.dump(
            {
                "config": {
                    "destination_device_serial_number": serial or "",
                    "templates": entries,
                }
            },
            Dumper=_BackupYamlDumper,
            default_flow_style=False,
            sort_keys=False,
        )
        lines = body.split("\n")

        # Annotate the empty serial line with a fill-in hint so the operator completes it.
        if not serial:
            for position, line in enumerate(lines):
                if line.strip().startswith("destination_device_serial_number:"):
                    lines[position] = (
                        line
                        + "  # [REQUIRED] add the replacement switch serial number before deploying"
                    )
                    break

        self.log("Rendered deploy config YAML.", "DEBUG")
        return "\n".join(lines)

    def _composite_deploy_labels(self):
        """
        Return the ``project_name/template_name`` labels of any composite templates
        pulled in with ``include_templates`` that are in the deploy set.

        A composite template declares no parameters of its own - its member templates
        carry them - so the generator cannot list member parameters for the operator to
        fill. These labels drive an advisory note telling the operator to set the member
        templates' parameters in Catalyst Center.

        Returns:
            list: Labels of included composite templates, in deploy order.
        """
        return [
            self._template_label(record)
            for record in self._deploy_records()
            if record.get("composite")
        ]

    def _composite_note_lines(self):
        """
        Build the optional composite-template advisory comment block for the file header.

        Returns:
            list: Comment lines to splice into the header, or an empty list when no
            composite template is included.
        """
        labels = self._composite_deploy_labels()
        if not labels:
            return []
        return [
            "#",
            "#   NOTE: COMPOSITE TEMPLATE(S) INCLUDED: {0}.".format(", ".join(labels)),
            "#   A composite has no parameters of its own, so none are listed below.",
            "#   Set its member templates' parameter values in Catalyst Center; Catalyst",
            "#   Center resolves the members when the composite is deployed.",
        ]

    def _compose_playbook(self):
        """
        Compose the deploy config for the ``switch_refresh_non_fabric_workflow_manager`` module.

        The file is the ``config:`` input for that module and is ready to run as-is. It
        is the working copy the operator completes (filling any blank parameter values
        for by-reference templates) and deploys. A pristine copy is also written to the
        backup file - see :meth:`_compose_backup`.

        Returns:
            str: The full file text (comment header followed by YAML).
        """
        self.log(
            "Composing deploy config file for source device '{0}'.".format(
                self.source_device_ip
            ),
            "DEBUG",
        )
        entries = self._build_deploy_entries()
        backup_path = self._resolve_backup_path()
        eq_border = "# " + ("=" * 75)
        dash_border = "# " + ("-" * 75)
        header = [
            eq_border,
            "#            Non-Fabric Switch Refresh - Deploy Config",
            eq_border,
            "#",
            "#   Source hostname    : {0}".format(
                self.source_device_facts.get("hostname") or "(unknown)"
            ),
            "#   Source IP          : {0}".format(self.source_device_ip),
            "#   Replacement serial : {0}".format(
                self.destination_device_serial_number
                or "(not set - fill 'destination_device_serial_number' below)"
            ),
            "#   Backup copy        : {0}".format(backup_path),
            "#",
            dash_border,
            "#   PLEASE READ BEFORE USING THIS FILE",
            dash_border,
            "#",
            "#   1. FILL ONLY THE BLANKS. Set 'destination_device_serial_number' to the",
            "#      replacement switch serial. For by-reference templates, 'param_value:'",
            "#      lines are listed blank - fill the values you want to set and leave",
            "#      system variables blank (Catalyst Center resolves them at deploy). Do",
            "#      not change any other value - everything else is intentional. Required",
            "#      values are validated against Catalyst Center before deployment.",
            "#",
            "#   2. DO NOT EDIT THE RECREATED CONFIG. Template contents are the realized",
            "#      configuration Catalyst Center deployed on the source switch (interfaces",
            "#      already renamed to the replacement). Hand-editing them changes what",
            "#      gets deployed.",
            "#",
            "#   3. LOST OR CHANGED THIS FILE? A pristine, read-only copy is saved at:",
            "#          {0}".format(backup_path),
            "#      Copy it back over this file and continue - no need to regenerate.",
            "#",
            "#   4. SAFE TO RE-RUN. Re-running the generator rebuilds this file from",
            "#      Catalyst Center and overwrites any manual edits made here.",
            "#",
            "#   This file is the 'config:' input for switch_refresh_non_fabric_workflow_manager.",
            "#   Templates deployed on the source switch are recreated from their realized",
            "#   configuration as '<name>_refresh' (project '{0}') and".format(
                self.REFRESH_PROJECT_NAME
            ),
            "#   deployed to the replacement by serial; include_templates add-ons are",
            "#   deployed by reference.",
        ]
        header += self._composite_note_lines()
        header += [eq_border, ""]
        file_text = (
            "\n".join(header)
            + "\n"
            + self._render_deploy_config(entries)
        )
        self.log(
            "Composed deploy config file ({0} character(s)).".format(len(file_text)),
            "DEBUG",
        )
        return file_text

    def _resolve_output_path(self):
        """
        Resolve the output file path, applying the per-device default when unset.

        Returns:
            str: The absolute-or-relative path to write.
        """
        if self.file_path:
            return self.file_path
        return "{0}_refresh_playbook_config.yml".format(self.source_device_ip)

    def _resolve_backup_path(self):
        """
        Resolve the backup file path, applying the per-device default when unset.

        Returns:
            str: The absolute-or-relative path to write the backup to.
        """
        if self.backup_file_path:
            return self.backup_file_path
        return "{0}_refresh_backup.yml".format(self.source_device_ip)

    def _compose_backup(self):
        """
        Compose the read-only backup: a pristine copy of the generated deploy config.

        The backup holds exactly the same ``config:`` content as the deploy config file,
        under a do-not-edit header. Its purpose is recovery: if the working deploy config
        is disturbed - edited by mistake, truncated or lost - the operator can copy this
        file over it and carry on, without regenerating from Catalyst Center.

        Returns:
            str: The full backup file text (comment header followed by YAML).
        """
        self.log(
            "Composing read-only backup copy for source device '{0}'.".format(
                self.source_device_ip
            ),
            "DEBUG",
        )
        entries = self._build_deploy_entries()
        eq_border = "# " + ("=" * 75)
        dash_border = "# " + ("-" * 75)
        deploy_path = self._resolve_output_path()
        header = [
            eq_border,
            "#       Non-Fabric Switch Refresh - Deploy Config BACKUP (DO NOT EDIT)",
            eq_border,
            "#",
            "#   Source hostname    : {0}".format(
                self.source_device_facts.get("hostname") or "(unknown)"
            ),
            "#   Source IP          : {0}".format(self.source_device_ip),
            "#   Replacement serial : {0}".format(
                self.destination_device_serial_number
                or "(not set - fill 'destination_device_serial_number' below)"
            ),
            "#   Deploy config      : {0}".format(deploy_path),
            "#",
            dash_border,
            "#   READ-ONLY BACKUP",
            dash_border,
            "#",
            "#   This is a pristine, read-only copy of the generated deploy config",
            "#   (the same 'config:' content written to the deploy config file). If",
            "#   the working deploy config is lost or edited by mistake, copy this",
            "#   file over it and continue - no need to regenerate from Catalyst",
            "#   Center. Do not edit this file; keep it as the clean fallback.",
        ]
        header += self._composite_note_lines()
        header += [eq_border, ""]
        backup_text = (
            "\n".join(header)
            + "\n"
            + self._render_deploy_config(entries)
        )
        self.log(
            "Composed read-only backup copy ({0} character(s)).".format(
                len(backup_text)
            ),
            "DEBUG",
        )
        return backup_text

    def write_config_file(self, file_text, output_path):
        """
        Write the generated file text to the output file.

        The write is skipped when an existing file already holds the same content,
        so a replay with unchanged Catalyst Center state reports ``changed=false``.

        Args:
            file_text (str): The composed file text.
            output_path (str): The resolved output path.

        Returns:
            bool: True when the file was written, False when it was already up to date.
        """
        existing = None
        if os.path.exists(output_path):
            try:
                with open(output_path, "r") as handle:
                    existing = handle.read()
            except OSError as error:
                self.log(
                    "Could not read existing file '{0}': {1}".format(
                        output_path, str(error)
                    ),
                    "WARNING",
                )

        if existing is not None and existing == file_text:
            self.log(
                "Output file '{0}' already up to date - skipping write.".format(
                    output_path
                ),
                "INFO",
            )
            return False

        directory = os.path.dirname(output_path)
        if directory and not os.path.isdir(directory):
            try:
                os.makedirs(directory)
            except OSError as error:
                self.msg = (
                    "Could not create directory '{0}' for the output file: "
                    "{1}".format(directory, str(error))
                )
                self.fail_and_exit(self.msg)

        try:
            with open(output_path, "w") as handle:
                handle.write(file_text)
        except OSError as error:
            self.msg = "Could not write the output file '{0}': {1}".format(
                output_path, str(error)
            )
            self.fail_and_exit(self.msg)

        self.log(
            "Output file written to '{0}'.".format(output_path), "INFO"
        )
        return True

    def get_diff_gathered(self):
        """
        Generate the deploy config for the source switch.

        Resolves the source device, reads the templates Catalyst Center has actually
        deployed on it (``deployedTemplateDetails``) and recreates each from its realized
        configuration, adds any ``include_templates`` add-ons by reference, lists their
        parameters, writes the deploy config to the output file, and records a concise
        summary in the module result.

        Returns:
            self: The instance with the result populated.
        """
        start_time = time.time()
        self.log(
            "Starting non-fabric switch refresh config generation for device "
            "'{0}'.".format(self.source_device_ip),
            "INFO",
        )

        device_record = self.resolve_source_device()
        if device_record is None:
            self.msg = (
                "Source device '{0}' was not found in Cisco Catalyst "
                "Center.".format(self.source_device_ip)
            )
            self.fail_and_exit(self.msg)

        device_id = device_record.get("id") or device_record.get("instanceUuid")
        device_family = device_record.get("family")

        # Human-readable destination label for messages when the serial is left unset.
        dest_label = (
            self.destination_device_serial_number or "(destination serial not set)"
        )

        # Fail fast: every interface_mappings source interface must exist on the source
        # device. This runs right after device resolution - before the deployed-template
        # lookup - so a typo or a wrong device is caught immediately, before any file is
        # written.
        if self.interface_mappings:
            self.log(
                "Validating {0} interface mapping(s) against the source device "
                "inventory for device '{1}'.".format(
                    len(self.interface_mappings), self.source_device_ip
                ),
                "INFO",
            )
            device_interfaces = self.fetch_source_device_interfaces(device_id)
            self.log(
                "Source device '{0}' interface inventory ({1} port(s)): {2}.".format(
                    self.source_device_ip,
                    len(device_interfaces),
                    ", ".join(device_interfaces) or "none",
                ),
                "DEBUG",
            )
            unmatched_sources = self._unmatched_source_interfaces(device_interfaces)
            if unmatched_sources:
                self.msg = (
                    "Interface mapping source interface(s) {0} were not found on "
                    "source device '{1}'. Every 'source_interface_name' in "
                    "'interface_mappings' must be an interface present on the source "
                    "device; correct the mapping or the device selection and "
                    "retry.".format(
                        ", ".join(unmatched_sources), self.source_device_ip
                    )
                )
                self.fail_and_exit(self.msg)
            self.log(
                "All {0} interface mapping source interface(s) exist on source "
                "device '{1}'.".format(
                    len(self.interface_mappings), self.source_device_ip
                ),
                "INFO",
            )

        # Templates Catalyst Center has actually deployed on the source device - both
        # profile-pushed and directly (Day-N) deployed - read in one call, each already
        # carrying its resolved CLI. This is the source of truth for what to recreate on
        # the replacement switch.
        deployed_templates = self.fetch_deployed_templates(device_id)

        # Read the template catalog once to (a) annotate each deployed template with its
        # project - the deployedTemplateDetails rows carry a null projectName - and (b)
        # resolve any include_templates the operator asked for and add them to the run.
        include_not_found = []
        included_stubs = []
        if deployed_templates or self.include_templates:
            catalog = self.fetch_template_catalog()
            id_to_project = {
                record["id"]: record["project_name"]
                for record in catalog
                if record["id"]
            }
            for template in deployed_templates:
                if isinstance(template, dict) and not template.get("projectName"):
                    stub_id = template.get("templateId") or template.get("id")
                    template["projectName"] = id_to_project.get(stub_id)
            included_stubs, include_not_found = self._resolve_included_templates(catalog)

        # Reference facts about the source device, recorded for the deploy entries.
        self.source_device_facts = {
            "hostname": device_record.get("hostname"),
            "family": device_family,
            "platform_id": device_record.get("platformId"),
            "software_version": device_record.get("softwareVersion"),
            "software_type": device_record.get("softwareType"),
        }

        # Recreate each deployed template from its realized config and emit each
        # include_templates add-on by reference, listing its parameters.
        self.build_template_records(
            deployed_templates, included_stubs, device_family
        )

        # Two recreated templates can configure the same interface with conflicting
        # settings. Under interface_migration a rename introduced the collision (it did
        # not exist on the source), so stop. Without migration the collision already
        # existed on the source, and deploying both in source order reproduces its
        # last-wins end state, so only warn rather than fail.
        matched_records = [
            record for record in self._deploy_records() if record.get("matched")
        ]
        conflicts = self._detect_interface_conflicts(matched_records)
        if conflicts:
            details = "; ".join(
                "interface '{0}' (from templates '{1}' and '{2}')".format(
                    name, first, second
                )
                for name, first, second in conflicts
            )
            if self.interface_migration:
                self.msg = (
                    "Interface migration produces conflicting configuration: {0}. More "
                    "than one recreated template configures the same interface with "
                    "different settings, usually because 'interface_mappings' renames "
                    "two source interfaces to the same destination or renames an "
                    "interface onto one another template already configures. Give each "
                    "interface a unique destination name and retry.".format(details)
                )
                self.fail_and_exit(self.msg)
            # No migration: the conflict pre-existed on the source. Keep going (the
            # end state stays faithful) but warn so the operator knows two templates
            # fight over the interface.
            self.interface_conflict_warning = (
                "more than one recreated template configures the same interface with "
                "different settings ({0}); they deploy in the source's order so the "
                "last one wins, but verify this is intended".format(details)
            )
            self.log(
                "Interface conflict detected without interface_migration: {0}. "
                "Deploying both; the last in source order wins.".format(details),
                "WARNING",
            )

        # Nothing resolved to a deployable template - no deployed template was recreated
        # from realized config and no include_templates add-on applied. Report an
        # idempotent no-op (ok, unchanged, no file written) instead of emitting an empty
        # deploy config, mirroring the sibling *_playbook_config_generator modules.
        deploy_records = self._deploy_records()
        if not deploy_records:
            excluded_templates = [
                self._template_label(record)
                for record in self.template_records
                if record.get("excluded")
            ]
            self.msg = (
                "No configuration to generate for device '{0}' from source '{1}': no "
                "deployed templates to recreate and no include_templates add-ons "
                "resolved. {2} excluded. No file written.".format(
                    dest_label,
                    self.source_device_ip,
                    len(excluded_templates),
                )
            )
            # A wrong-family source (for example a wireless controller) has no non-fabric
            # switch templates to recreate; point the operator at the likely cause.
            if device_family and "switch" not in str(device_family).lower():
                self.msg += (
                    " Source device '{0}' is a '{1}', not a non-fabric switch; this "
                    "module recreates switch templates, so select a switch as the "
                    "source.".format(self.source_device_ip, device_family)
                )
            if include_not_found:
                self.msg += (
                    " Warning: {0} include_templates entry(ies) were not found in "
                    "Cisco Catalyst Center.".format(len(include_not_found))
                )
            response = {
                "status": "ok",
                "message": self.msg,
                "source_device_ip": self.source_device_ip,
                "destination_device_serial_number": self.destination_device_serial_number,
                "templates_to_deploy": 0,
                "template_parameters_to_fill": 0,
                "templates_excluded": len(excluded_templates),
                "file_path": None,
                "backup_file_path": None,
            }
            self.set_operation_result("ok", False, self.msg, "INFO", response)
            self.log(
                "No deployable templates for device '{0}' from source '{1}'; no deploy "
                "config or backup written.".format(
                    self.destination_device_serial_number, self.source_device_ip
                ),
                "INFO",
            )
            return self

        # Write the deploy config (switch_refresh_non_fabric_workflow_manager input) to the output file.
        output_path = self._resolve_output_path()
        file_text = self._compose_playbook()
        changed = self.write_config_file(file_text, output_path)

        # Always write the read-only backup: a pristine copy of the deploy config. If the
        # working deploy config is later disturbed, the operator can copy this backup
        # over it and continue without regenerating.
        backup_path = self._resolve_backup_path()
        backup_text = self._compose_backup()
        backup_changed = self.write_config_file(backup_text, backup_path)
        changed = changed or backup_changed

        # Summarise: applicable templates, the subset going into the deploy config, how
        # many parameter values still need filling, plus exclusions.
        applicable_records = [
            record
            for record in self.template_records
            if record.get("applicable") and not record.get("excluded")
        ]
        # Templates deployed on the source are recreated from their realized (already
        # resolved) configuration, so only the by-reference (include-only) templates carry
        # parameters. Every parameter they declare is listed blank for the operator to
        # review; which values are actually required is validated at deploy time by the
        # workflow manager's Catalyst Center preview.
        recreated_records = [r for r in deploy_records if r.get("matched")]
        reference_records = [r for r in deploy_records if not r.get("matched")]
        template_parameters_to_fill = sum(
            len(record.get("parameters") or []) for record in reference_records
        )
        excluded_templates = [
            self._template_label(record)
            for record in self.template_records
            if record.get("excluded")
        ]
        # Lead with whether this run (re)generated the file or found it already current,
        # so a replay against unchanged Catalyst Center state reads as idempotent.
        if changed:
            lead = "Config generated for device '{0}' from source '{1}'".format(
                dest_label, self.source_device_ip
            )
        else:
            lead = "Config already up to date for device '{0}' from source '{1}'".format(
                dest_label, self.source_device_ip
            )
        summary_message = (
            "{0}: {1} template(s) to deploy, {2} excluded, {3} by-reference template "
            "parameter(s) listed.".format(
                lead,
                len(deploy_records),
                len(excluded_templates),
                template_parameters_to_fill,
            )
        )
        # Unresolved include_templates entries no longer have a dedicated field, so
        # surface them in the message where they still warrant the operator's attention.
        if include_not_found:
            summary_message += (
                " Warning: {0} include_templates entry(ies) were not found in "
                "Cisco Catalyst Center.".format(len(include_not_found))
            )
        if self.duplicate_template_count:
            summary_message += (
                " {0} duplicate template(s) with identical configuration were "
                "collapsed.".format(self.duplicate_template_count)
            )
        # A composite include has no parameters of its own (its members carry them), so
        # none are listed; flag it so the operator sets the member parameters in CC.
        composite_includes = [
            record for record in deploy_records if record.get("composite")
        ]
        if composite_includes:
            summary_message += (
                " Note: {0} included composite template(s) have no listed parameters; "
                "set their member templates' parameters in Catalyst Center.".format(
                    len(composite_includes)
                )
            )
        # Same-interface/different-config across templates without a migration is
        # faithful but worth flagging; surface it alongside the other warnings.
        if self.interface_conflict_warning:
            summary_message += " Warning: {0}.".format(self.interface_conflict_warning)

        response = {
            "status": "success",
            "message": summary_message,
            "source_device_ip": self.source_device_ip,
            "destination_device_serial_number": self.destination_device_serial_number,
            "templates_to_deploy": len(deploy_records),
            "template_parameters_to_fill": template_parameters_to_fill,
            "templates_excluded": len(excluded_templates),
            "file_path": output_path,
            "backup_file_path": backup_path,
        }

        self.msg = response["message"]
        self.set_operation_result("success", changed, self.msg, "INFO", response)
        self.log(
            "Completed deploy-config generation in {0:.2f} seconds. {1} template(s) "
            "retrieved, {2} applicable, {3} to deploy ({4} recreated from realized "
            "config), {5} by-reference template parameter(s) listed, deploy config "
            "written to '{6}', backup copy written to '{7}'.".format(
                time.time() - start_time,
                len(self.template_records),
                len(applicable_records),
                len(deploy_records),
                len(recreated_records),
                template_parameters_to_fill,
                output_path,
                backup_path,
            ),
            "INFO",
        )
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
        "catalystcenter_log_level": {"type": "str", "default": "WARNING", "aliases": ["dnac_log_level"]},
        "catalystcenter_log_file_path": {"type": "str", "default": "catalystcenter.log", "aliases": ["dnac_log_file_path"]},
        "catalystcenter_log_append": {"type": "bool", "default": True, "aliases": ["dnac_log_append"]},
        "catalystcenter_log": {"type": "bool", "default": False, "aliases": ["dnac_log"]},
        "validate_response_schema": {"type": "bool", "default": True},
        "catalystcenter_api_task_timeout": {"type": "int", "default": 1200, "aliases": ["dnac_api_task_timeout"]},
        "catalystcenter_task_poll_interval": {"type": "int", "default": 2, "aliases": ["dnac_task_poll_interval"]},
        "state": {"default": "gathered", "choices": ["gathered"]},
        "file_path": {"required": False, "type": "str"},
        "backup_file_path": {"required": False, "type": "str"},
        "config": {"required": True, "type": "dict"},
    }

    module = AnsibleModule(argument_spec=element_spec, supports_check_mode=True)

    config_generator = SwitchRefreshNonFabricPlaybookConfigGenerator(module)

    if (
        config_generator.compare_catalystcenter_versions(
            config_generator.get_ccc_version(), "2.3.7.9"
        )
        < 0
    ):
        config_generator.msg = (
            "The specified version '{0}' does not support the non-fabric switch "
            "refresh configuration generation. Supported versions start from "
            "'2.3.7.9' onwards.".format(config_generator.get_ccc_version())
        )
        config_generator.set_operation_result(
            "failed", False, config_generator.msg, "ERROR"
        ).check_return_status()

    state = config_generator.params.get("state")
    if state not in config_generator.supported_states:
        config_generator.status = "invalid"
        config_generator.msg = "State {0} is invalid".format(state)
        config_generator.check_return_status()

    config_generator.validate_input().check_return_status()

    config = config_generator.config
    config_generator.get_want(config).check_return_status()
    config_generator.get_diff_state_apply[state]().check_return_status()

    module.exit_json(**config_generator.result)


if __name__ == "__main__":
    main()
