#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2024, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible module to perform operations on projects and templates in Cisco Catalyst Center."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

__author__ = [
    "Madhan Sankaranarayanan, Rishita Chowdhary, Akash Bhaskaran, Muthu Rakesh, Abhishek Maheshwari, Archit Soni, A Mohamed Rafeek, Vivek Raj"
]

DOCUMENTATION = r"""
---
module: template_workflow_manager
short_description: Resource module for Template functions
description:
  - Manages operations for creating, updating, and deleting
    configuration templates.
  - Creates templates by project and template names.
  - Updates templates by project and template names.
  - Deletes templates by project and template names.
  - Exports projects and templates based on specified
    parameters.
  - Handles the creation of resources for importing
    configuration templates and projects.
version_added: '1.0.0'
extends_documentation_fragment:
  - cisco.catalystcenter.workflow_manager_params
author: Madhan Sankaranarayanan (@madhansansel)
        Rishita Chowdhary (@rishitachowdhary)
        Akash Bhaskaran (@akabhask)
        Muthu Rakesh (@MUTHU-RAKESH-27)
        Abhishek Maheshwari (@abmahesh)
        Archit Soni (@koderchit)
        A Mohamed Rafeek (@mabdulk2)
options:
  config_verify:
    description: |
      If set to True, verifies the Cisco Catalyst Center
      configuration after applying the playbook.

    type: bool
    default: false
  state:
    description: Desired state of the Cisco Catalyst
      Center after module execution.
    type: str
    choices: [merged, deleted]
    default: merged
  config:
    description: Details of templates to manage.
    type: list
    elements: dict
    required: true
    suboptions:
      projects:
        description: |
          Create, update, or delete projects with associated details such as name,
          and description.
        type: list
        elements: dict
        required: false
        suboptions:
          name:
            description: |
              The name of the project. This is used to identify the project for creation,
              update, or deletion.
            type: str
            required: true
          new_name:
            description: |
              Specify a new name for the project when updating an existing project.
            type: str
            required: false
          description:
            description: A brief description of the project.
            type: str
            required: false

      configuration_templates:
        description: Operations for Create/Update/Delete
          on a template.
        type: dict
        suboptions:
          author:
            description: Creator of the template.
            type: str
          composite:
            description: Specifies if the template is
              composite.
            type: bool
          containing_templates:
            description:
              - Set of templates within the main template
                to define more complex or modular configurations.
              - This is particularly useful in systems
                that support hierarchical or nested
                templates.
              - Here parent templates may contain child
                templates to form a complete configuration.
            suboptions:
              composite:
                description: Specifies if the template
                  is composite.
                type: bool
              template_description:
                description: Provides a description
                  of the template.
                type: str
              device_types:
                description: List of dictionaries details
                  the types of devices that the templates
                  can be applied to.
                type: list
                elements: dict
                required: true
                suboptions:
                  product_family:
                    description: Denotes the family
                      to which the device belongs.
                    choices:
                      - Cisco Cloud Services Platform
                      - Cisco Interfaces and Modules
                      - Content Networking
                      - Network Management
                      - NFV-ThirdParty Devices
                      - NFVIS
                      - Routers
                      - Security and VPN
                      - Storage Networking
                      - Switches and Hubs
                      - Voice and Telephony
                      - Wireless Controller
                    type: str
                    required: true
                  product_series:
                    description: Specifies the series
                      classification of the device.
                    type: str
                  product_type:
                    description: Describes the exact
                      type of the device.
                    type: str
              id:
                description: Unique identifier for the
                  template, represented as a UUID.
                type: str
              language:
                description: Programming language used
                  for templating. Options are 'JINJA'
                  for Jinja templating or 'VELOCITY'
                  for Apache Velocity.
                choices:
                  - JINJA
                  - VELOCITY
                type: str
              name:
                description: Designation of the template,
                  serving as its unique name.
                type: str
              project_name:
                description: Title of the project within
                  which the template is categorized
                  and managed.
                type: str
              project_description:
                description: Narrative that elaborates
                  on the purpose and scope of the project.
                type: str
              profile_names:
                description: |
                    - List of profile names to be associated with the Configuration Template during creation or update operations.
                    - Enables assignment of one or more network profiles to CLI templates for enhanced device configuration management.
                    - Profile names must correspond to existing network profiles in Cisco Catalyst Center for the specified device types.
                    - Supports assignment of multiple profiles simultaneously for comprehensive device configuration coverage.
                    - Profiles are validated against the device types specified in the template configuration to ensure compatibility.
                    - When combined with existing profile assignments, new profiles are added while preserving existing assignments.
                    - Profile assignment operations are idempotent - re-assigning existing profiles will not cause errors or duplicate assignments.
                    - Requires Cisco Catalyst Center version 3.1.3.0 or later for profile assignment functionality.
                    - Profile names are case-sensitive and must match exactly as configured in Cisco Catalyst Center.
                    - Each profile in the list must be a valid string representing an existing network profile name.
                    - If no profiles are specified, the template will not be associated with any profiles by default.
                    - Profile names can be detached from the template based on deleted state operations.
                    - C(examples):
                    - ["Enterprise_Security_Profile", "QoS_Voice_Profile"]
                    - ["Campus_Switching_Profile"]
                    - ["WAN_Edge_Profile", "Security_Baseline_Profile", "Monitoring_Profile"]
                type: list
                elements: str
                required: false
              tags:
                description: A list of dictionaries
                  representing tags associated with
                  the Configuration Template during
                  creation.
                suboptions:
                  id:
                    description: The unique identifier
                      for each tag, presented as a UUID.
                    type: str
                  name:
                    description: The descriptive label
                      or name assigned to the tag.
                    type: str
                type: list
                elements: dict
              template_content:
                description: The actual script or code
                  constituting the body of the template.
                type: str
              template_content_file_path:
                description:
                  - Path to a local file containing the template content to be used during create or update operations.
                  - Supported file extensions are '.j2' (Jinja) and '.txt'. Files with other extensions will be rejected.
                  - When provided, this field takes precedence over 'template_content'.
                  - Supports absolute and relative paths. Relative paths are resolved from the playbook's working
                    directory (typically the directory where `ansible-playbook` is executed).
                  - For '.j2' files, content is rendered using Jinja before being sent to Cisco Catalyst Center;
                    variables and logic are evaluated using the provided `template_params` and runtime context.
                  - For '.txt' files, content is passed transparently to the Cisco Catalyst Center APIs without
                    evaluation or interpolation.
                  - Rendering errors (e.g., missing variables, invalid Jinja syntax) cause the module to fail with a descriptive message.
                  - The resolved file path must exist and be readable; otherwise the module fails and reports the missing path.
                type: str
              validate_jinja2_syntax:
                description:
                    - Validates Jinja2 template syntax when template_content_file_path ends with '.j2'.
                    - Requires jinja2 Python library (pip install jinja2).
                    - When True, module fails if syntax errors detected with line number and error details.
                    - When False, skips validation allowing potentially invalid templates to be uploaded.
                type: bool
                default: false
              template_params:
                description: The customization of the
                  contents within the template.
                elements: dict
                suboptions:
                  binding:
                    description: Associates the parameter
                      with its source.
                    type: str
                  custom_order:
                    description: Specifies a user-defined
                      ordering for the parameter.
                    type: int
                  data_type:
                    description: Identifies the data
                      type of the parameter (e.g., string,
                      integer, boolean).
                    type: str
                  default_value:
                    description: Establishes a default
                      value for the parameter, used
                      if no other value is provided.
                    type: str
                  description:
                    description: Provides a descriptive
                      explanation of the parameter's
                      purpose.
                    type: str
                  display_name:
                    description: The name of the parameter
                      as displayed to users.
                    type: str
                  group:
                    description: Categorizes the parameter
                      into a named group for organizational
                      purposes.
                    type: str
                  id:
                    description: A unique identifier
                      for the parameter, formatted as
                      a UUID.
                    type: str
                  instruction_text:
                    description: Gives guidance or instructions
                      regarding the parameter's use.
                    type: str
                  key:
                    description: A unique key that identifies
                      the parameter within the template.
                    type: str
                  not_param:
                    description: Indicates whether the
                      entry is not to be treated as
                      a parameter.
                    type: bool
                  order:
                    description: Determines the sequence
                      in which the parameter appears
                      relative to others.
                    type: int
                  param_array:
                    description: Specifies if the parameter
                      should be treated as an array.
                    type: bool
                  parameter_name:
                    description: The name of the parameter.
                    type: str
                  provider:
                    description: Denotes the provider
                      associated with the parameter.
                    type: str
                  range:
                    description: Defines the permissible
                      range for the parameter's value.
                    suboptions:
                      id:
                        description: Unique identifier
                          for the range, represented
                          as a UUID.
                        type: str
                      max_value:
                        description: Specifies the maximum
                          allowable value for the parameter.
                        type: int
                      min_value:
                        description: Specifies the minimum
                          allowable value for the parameter.
                        type: int
                    type: list
                    elements: dict
                  required:
                    description: Dictates whether the
                      parameter is required for template
                      operations.
                    type: bool
                  selection:
                    description: Contains options for
                      parameter selection when a choice
                      is available.
                    suboptions:
                      default_selected_values:
                        description: Lists the default
                          values that are preselected.
                        elements: str
                        type: list
                      id:
                        description: A unique identifier
                          for the selection entity,
                          represented as a UUID.
                        type: str
                      selection_type:
                        description: Specifies the type
                          of selection, such as 'SINGLE_SELECT'
                          or 'MULTI_SELECT'.
                        type: str
                      selection_values:
                        description: A dictionary of
                          available values for selection.
                        type: dict
                    type: dict
                type: list
              version:
                description: The current version of
                  template.
                type: str
            type: list
            elements: dict
          custom_params_order:
            description: Specifies the sequence in which
              custom parameters or variables should
              be arranged within the template.
            type: bool
          template_description:
            description: Provides a overview  of the
              template.
            type: str
          commit:
            description:
              - Indicates whether the template should be committed after configuration changes.
              - If set to 'false', the changes are not committed immediately, allowing for additional
                modifications before an explicit commit.
            type: bool
            default: true
          device_types:
            description: List of dictionaries details
              the types of devices that the templates
              can be applied to.
            type: list
            elements: dict
            suboptions:
              product_family:
                description: Denotes the family to which
                  the device belongs.
                choices:
                  - Cisco Cloud Services Platform
                  - Cisco Interfaces and Modules
                  - Content Networking
                  - Network Management
                  - NFV-ThirdParty Devices
                  - NFVIS
                  - Routers
                  - Security and VPN
                  - Storage Networking
                  - Switches and Hubs
                  - Voice and Telephony
                  - Wireless Controller
                type: str
              product_series:
                description: Specifies the series classification
                  of the device.
                type: str
              product_type:
                description: Describes the exact type
                  of the device.
                type: str
          failure_policy:
            description:
              - Define failure policy if template provisioning
                fails.
              - failure_policy will be enabled only
                when the composite is set to True.
            choices:
              - ABORT_TARGET_ON_ERROR
            type: str
          id:
            description: A unique identifier, represented
              as a UUID.
            type: str
          language:
            description: Programming language used for
              templating. Options are 'JINJA' for Jinja
              templating or 'VELOCITY' for Apache Velocity.
            choices:
              - JINJA
              - VELOCITY
            type: str
          template_name:
            description: Name of template. This field
              is required to create a new template.
            type: str
          new_template_name:
            description:
              - New name of the template.
              - Use this field to update the name of
                the existing template.
            type: str
          project_name:
            description: Title of the project within
              which the template is categorized and
              managed.
            type: str
          project_description:
            description: Narrative that elaborates on
              the purpose and scope of the project.
            type: str
          software_type:
            description: Applicable device software
              type. This field is required to create
              a new template.
            choices:
              - IOS
              - IOS-XE
              - IOS-XR
              - NX-OS
              - Cisco Controller
              - Wide Area Application Services
              - Adaptive Security Appliance
              - NFV-OS
              - Others
            type: str
          software_version:
            description: Applicable device software
              version.
            type: str
          template_tag:
            description: Refers to a keyword, label,
              or metadata assigned to a template.
            suboptions:
              id:
                description: A unique identifier for
                  the tag, represented as a UUID.
                type: str
              name:
                description: The name of the tag.
                type: str
            type: list
            elements: dict
          template_content:
            description: The actual script or code constituting
              the body of the template.
            type: str
          template_content_file_path:
            description:
              - Path to a local file containing the template content to be used during create or update operations.
              - Supported file extensions are '.j2' (Jinja) and '.txt'. Files with other extensions will be rejected.
              - When provided, this field takes precedence over 'template_content'.
              - Supports absolute and relative paths. Relative paths are resolved from the playbook's working
                directory (typically the directory where `ansible-playbook` is executed).
              - For '.j2' files, content is rendered using Jinja before being sent to Cisco Catalyst Center;
                variables and logic are evaluated using the provided `template_params` and runtime context.
              - For '.txt' files, content is passed transparently to the Cisco Catalyst Center APIs without
                evaluation or interpolation.
              - Rendering errors (e.g., missing variables, invalid Jinja syntax) cause the module to fail with a descriptive message.
              - The resolved file path must exist and be readable; otherwise the module fails and reports the missing path.
            type: str
          template_params:
            description: The customization of the contents
              within the template.
            suboptions:
              binding:
                description: Associates the parameter
                  with its source.
                type: str
              custom_order:
                description: Specifies a user-defined
                  ordering for the parameter.
                type: int
              data_type:
                description: Identifies the data type
                  of the parameter (e.g., string, integer,
                  boolean).
                type: str
              default_value:
                description: Establishes a default value
                  for the parameter, used if no other
                  value is provided.
                type: str
              description:
                description: Provides a descriptive
                  explanation of the parameter's purpose.
                type: str
              display_name:
                description: The name of the parameter
                  as displayed to users.
                type: str
              group:
                description: Categorizes the parameter
                  into a named group for organizational
                  purposes.
                type: str
              id:
                description: A unique identifier for
                  the parameter, formatted as a UUID.
                type: str
              instruction_text:
                description: Gives guidance or instructions
                  regarding the parameter's use.
                type: str
              key:
                description: A unique key that identifies
                  the parameter within the template.
                type: str
              not_param:
                description: Indicates whether the entry
                  is not to be treated as a parameter.
                type: bool
              order:
                description: Determines the sequence
                  in which the parameter appears relative
                  to others.
                type: int
              param_array:
                description: Specifies if the parameter
                  should be treated as an array.
                type: bool
              parameter_name:
                description: The name of the parameter.
                type: str
              provider:
                description: Denotes the provider associated
                  with the parameter.
                type: str
              range:
                description: Defines the permissible
                  range for the parameter's value.
                suboptions:
                  id:
                    description: Unique identifier for
                      the range, represented as a UUID.
                    type: str
                  max_value:
                    description: Specifies the maximum
                      allowable value for the parameter.
                    type: int
                  min_value:
                    description: Specifies the minimum
                      allowable value for the parameter.
                    type: int
                type: list
                elements: dict
              required:
                description: Dictates whether the parameter
                  is required for template operations.
                type: bool
              selection:
                description: Contains options for parameter
                  selection when a choice is available.
                suboptions:
                  default_selected_values:
                    description: Lists the default values
                      that are preselected.
                    elements: str
                    type: list
                  id:
                    description: A unique identifier
                      for the selection entity, represented
                      as a UUID.
                    type: str
                  selection_type:
                    description: Specifies the type
                      of selection, such as 'SINGLE_SELECT'
                      or 'MULTI_SELECT'.
                    type: str
                  selection_values:
                    description: A dictionary of available
                      values for selection.
                    type: dict
                type: dict
            type: list
            elements: dict
          version:
            description: The current version of template.
            type: str
          version_description:
            description: Template version comments.
            type: str
      export:
        description: Perform export on the projects
          and templates.
        type: dict
        suboptions:
          project:
            description: Export the project(s) details.
            type: list
            elements: str
          template:
            description: Export the template(s) details.
            type: list
            elements: dict
            suboptions:
              project_name:
                description: Name of the project under
                  the template available.
                type: str
              template_name:
                description: Name of the template which
                  we need to be exported.
                type: str
      import:
        description: Perform import on the projects
          and templates.
        type: dict
        suboptions:
          project:
            description: Import the projects.
            type: dict
            suboptions:
              do_version:
                description:
                  - Determines whether to create a new
                    version of the project with the
                    imported contents.
                  - If set to true and the project already
                    exists, a new version will be created.
                  - If false, the operation will fail
                    with a 'Project already exists'
                    error if the project already exists.
                type: bool
              project_file:
                description:
                  - Specifies the path to a JSON file
                    that contains the import project
                    configuration.
                  - If both 'project_file' and 'payload'
                    are provided, the 'project_file'
                    will be given priority.
                type: str
              payload:
                description:
                  - Directly imports configuration data
                    into the system using the provided
                    payload.
                  - Offers an alternative to 'project_file'
                    for importing configurations without
                    referencing an external file.
                  - Ignored if 'project_file' is also
                    provided.
                type: list
                elements: dict
                suboptions:
                  name:
                    description: Name of the project
                      to be imported.
                    type: str
          template:
            description: Import the templates.
            type: dict
            suboptions:
              do_version:
                description: DoVersion query parameter.
                  If this flag is true, creates a new
                  version of the template with the imported
                  contents, if the templates already
                  exists. " If false and if template
                  already exists, then operation fails
                  with 'Template already exists' error.
                type: bool
              template_file:
                description:
                  - Specifies the path to a JSON file
                    that contains an import template.
                  - If both 'template_file' and 'payload'
                    are provided, the 'template_file'
                    will be given priority.
                type: str
              payload:
                description:
                  - The payload parameter is used to
                    directly import configuration data
                    into the system.
                  - The payload provides an alternative
                    way to import configurations without
                    the need to reference an external
                    file.
                  - If both 'template_file' and 'payload'
                    are provided, the 'template_file'
                    will be given priority.
                type: list
                elements: dict
                suboptions:
                  author:
                    description: Identifies the creator
                      of the template.
                    type: str
                  composite:
                    description: Specifies if the template
                      is composite.
                    type: bool
                  containing_templates:
                    description:
                      - Refer to a set of templates
                        within the main template to
                        define more complex or modular
                        configurations.
                      - This is particularly useful
                        in systems that support hierarchical
                        or nested templates.
                      - Here parent templates may contain
                        child templates to form a complete
                        configuration.
                    suboptions:
                      composite:
                        description: Specifies if the
                          template is composite.
                        type: bool
                      description:
                        description: Provides a description
                          of the template.
                        type: str
                      device_types:
                        description: List of dictionaries
                          details the types of devices
                          that the templates can be
                          applied to.
                        type: list
                        elements: dict
                        suboptions:
                          product_family:
                            description: Denotes the
                              family to which the device
                              belongs.
                            choices:
                              - Cisco Cloud Services
                                Platform
                              - Cisco Interfaces and
                                Modules
                              - Content Networking
                              - Network Management
                              - NFV-ThirdParty Devices
                              - NFVIS
                              - Routers
                              - Security and VPN
                              - Storage Networking
                              - Switches and Hubs
                              - Voice and Telephony
                              - Wireless Controller
                            type: str
                          product_series:
                            description: Specifies the
                              series classification
                              of the device.
                            type: str
                          product_type:
                            description: Describes the
                              exact type of the device.
                            type: str
                      id:
                        description: Unique identifier
                          for the template, represented
                          as a UUID.
                        type: str
                      language:
                        description: Programming language
                          used for templating. Options
                          are 'JINJA' for Jinja templating
                          or 'VELOCITY' for Apache Velocity.
                        choices:
                          - JINJA
                          - VELOCITY
                        type: str
                      name:
                        description: Designation of
                          the template, serving as its
                          unique name.
                        type: str
                      project_name:
                        description: Title of the project
                          within which the template
                          is categorized and managed.
                        type: str
                      tags:
                        description: A list of dictionaries
                          representing tags associated
                          with the Configuration Template
                          during creation.
                        suboptions:
                          id:
                            description: The unique
                              identifier for each tag,
                              presented as a UUID.
                            type: str
                          name:
                            description: The descriptive
                              label or name assigned
                              to the tag.
                            type: str
                        type: list
                        elements: dict
                      template_content:
                        description: The actual script
                          or code constituting the body
                          of the template.
                        type: str
                      template_content_file_path:
                        description:
                          - Path to a local file containing the template content to be used during create or update operations.
                          - Supported file extensions are '.j2' (Jinja) and '.txt'. Files with other extensions will be rejected.
                          - When provided, this field takes precedence over 'template_content'.
                          - Supports absolute and relative paths. Relative paths are resolved from the playbook's working
                            directory (typically the directory where `ansible-playbook` is executed).
                          - For '.j2' files, content is rendered using Jinja before being sent to Cisco Catalyst Center;
                            variables and logic are evaluated using the provided `template_params` and runtime context.
                          - For '.txt' files, content is passed transparently to the Cisco Catalyst Center APIs without
                            evaluation or interpolation.
                          - Rendering errors (e.g., missing variables, invalid Jinja syntax) cause the module to fail with a descriptive message.
                          - The resolved file path must exist and be readable; otherwise the module fails and reports the missing path.
                        type: str
                      template_params:
                        description: The customization
                          of the contents within the
                          template.
                        elements: dict
                        suboptions:
                          binding:
                            description: Associates
                              the parameter with its
                              source.
                            type: str
                          custom_order:
                            description: Specifies a
                              user-defined ordering
                              for the parameter.
                            type: int
                          data_type:
                            description: Identifies
                              the data type of the parameter
                              (e.g., string, integer,
                              boolean).
                            type: str
                          default_value:
                            description: Establishes
                              a default value for the
                              parameter, used if no
                              other value is provided.
                            type: str
                          description:
                            description: Provides a
                              descriptive explanation
                              of the parameter's purpose.
                            type: str
                          display_name:
                            description: The name of
                              the parameter as displayed
                              to users.
                            type: str
                          group:
                            description: Categorizes
                              the parameter into a named
                              group for organizational
                              purposes.
                            type: str
                          id:
                            description: A unique identifier
                              for the parameter, formatted
                              as a UUID.
                            type: str
                          instruction_text:
                            description: Gives guidance
                              or instructions regarding
                              the parameter's use.
                            type: str
                          key:
                            description: A unique key
                              that identifies the parameter
                              within the template.
                            type: str
                          not_param:
                            description: Indicates whether
                              the entry is not to be
                              treated as a parameter.
                            type: bool
                          order:
                            description: Determines
                              the sequence in which
                              the parameter appears
                              relative to others.
                            type: int
                          param_array:
                            description: Specifies if
                              the parameter should be
                              treated as an array.
                            type: bool
                          parameter_name:
                            description: The name of
                              the parameter.
                            type: str
                          provider:
                            description: Denotes the
                              provider associated with
                              the parameter.
                            type: str
                          range:
                            description: Defines the
                              permissible range for
                              the parameter's value.
                            suboptions:
                              id:
                                description: Unique
                                  identifier for the
                                  range, represented
                                  as a UUID.
                                type: str
                              max_value:
                                description: Specifies
                                  the maximum allowable
                                  value for the parameter.
                                type: int
                              min_value:
                                description: Specifies
                                  the minimum allowable
                                  value for the parameter.
                                type: int
                            type: list
                            elements: dict
                          required:
                            description: Dictates whether
                              the parameter is required
                              for template operations.
                            type: bool
                          selection:
                            description: Contains options
                              for parameter selection
                              when a choice is available.
                            suboptions:
                              default_selected_values:
                                description: Lists the
                                  default values that
                                  are preselected.
                                elements: str
                                type: list
                              id:
                                description: A unique
                                  identifier for the
                                  selection entity,
                                  represented as a UUID.
                                type: str
                              selection_type:
                                description: Specifies
                                  the type of selection,
                                  such as 'SINGLE_SELECT'
                                  or 'MULTI_SELECT'.
                                type: str
                              selection_values:
                                description: A dictionary
                                  of available values
                                  for selection.
                                type: dict
                            type: dict
                        type: list
                      version:
                        description: The current version
                          of template.
                        type: str
                    type: list
                    elements: dict
                  custom_params_order:
                    description: Specifies the sequence
                      in which custom parameters or
                      variables should be arranged within
                      the template.
                    type: bool
                  template_description:
                    description: Provides a overview  of
                      the template.
                    type: str
                  device_types:
                    description: List of dictionaries
                      details the types of devices that
                      the templates can be applied to.
                    type: list
                    elements: dict
                    suboptions:
                      product_family:
                        description: Denotes the family
                          to which the device belongs.
                        choices:
                          - Cisco Cloud Services Platform
                          - Cisco Interfaces and Modules
                          - Content Networking
                          - Network Management
                          - NFV-ThirdParty Devices
                          - NFVIS
                          - Routers
                          - Security and VPN
                          - Storage Networking
                          - Switches and Hubs
                          - Voice and Telephony
                          - Wireless Controller
                        type: str
                      product_series:
                        description: Specifies the series
                          classification of the device.
                        type: str
                      product_type:
                        description: Describes the exact
                          type of the device.
                        type: str
                  failure_policy:
                    description:
                      - Define failure policy if template
                        provisioning fails.
                      - failure_policy will be enabled
                        only when the composite is set
                        to True.
                    choices:
                      - ABORT_TARGET_ON_ERROR
                    type: str
                  id:
                    description: A unique identifier,
                      represented as a UUID.
                    type: str
                  language:
                    description: Programming language
                      used for templating. Options are
                      'JINJA' for Jinja templating or
                      'VELOCITY' for Apache Velocity.
                    choices:
                      - JINJA
                      - VELOCITY
                    type: str
                  template_name:
                    description: Name of template. This
                      field is required to create a
                      new template.
                    type: str
                  project_name:
                    description: Title of the project
                      within which the template is categorized
                      and managed.
                    type: str
                  project_description:
                    description: Narrative that elaborates
                      on the purpose and scope of the
                      project.
                    type: str
                  software_type:
                    description: Applicable device software
                      type. This field is required to
                      create a new template.
                    choices:
                      - IOS
                      - IOS-XE
                      - IOS-XR
                      - NX-OS
                      - Cisco Controller
                      - Wide Area Application Services
                      - Adaptive Security Appliance
                      - NFV-OS
                      - Others
                    type: str
                  software_version:
                    description: Applicable device software
                      version.
                    type: str
                  template_tag:
                    description: Refers to a keyword,
                      label, or metadata assigned to
                      a template.
                    suboptions:
                      id:
                        description: A unique identifier
                          for the tag, represented as
                          a UUID.
                        type: str
                      name:
                        description: The name of the
                          tag.
                        type: str
                    type: list
                    elements: dict
                  template_content:
                    description: The actual script or
                      code constituting the body of
                      the template.
                    type: str
                  template_content_file_path:
                    description:
                      - Path to a local file containing the template content to be used during create or update operations.
                      - Supported file extensions are '.j2' (Jinja) and '.txt'. Files with other extensions will be rejected.
                      - When provided, this field takes precedence over 'template_content'.
                      - Supports absolute and relative paths. Relative paths are resolved from the playbook's working
                        directory (typically the directory where `ansible-playbook` is executed).
                      - For '.j2' files, content is evaluated if validate_jinja2_syntax is set to true, using Jinja templating engine before
                        being sent to Cisco Catalyst Center; variables and logic are evaluated using the provided `template_params` and runtime context.
                      - For '.txt' files, content is passed transparently to the Cisco Catalyst Center APIs without
                        evaluation or interpolation.
                      - Rendering errors (e.g., missing variables, invalid Jinja syntax) cause the module to fail with a descriptive message.
                      - The resolved file path must exist and be readable; otherwise the module fails and reports the missing path.
                    type: str
                  template_params:
                    description: The customization of
                      the contents within the template.
                    suboptions:
                      binding:
                        description: Associates the
                          parameter with its source.
                        type: str
                      custom_order:
                        description: Specifies a user-defined
                          ordering for the parameter.
                        type: int
                      data_type:
                        description: Identifies the
                          data type of the parameter
                          (e.g., string, integer, boolean).
                        type: str
                      default_value:
                        description: Establishes a default
                          value for the parameter, used
                          if no other value is provided.
                        type: str
                      description:
                        description: Provides a descriptive
                          explanation of the parameter's
                          purpose.
                        type: str
                      display_name:
                        description: The name of the
                          parameter as displayed to
                          users.
                        type: str
                      group:
                        description: Categorizes the
                          parameter into a named group
                          for organizational purposes.
                        type: str
                      id:
                        description: A unique identifier
                          for the parameter, formatted
                          as a UUID.
                        type: str
                      instruction_text:
                        description: Gives guidance
                          or instructions regarding
                          the parameter's use.
                        type: str
                      key:
                        description: A unique key that
                          identifies the parameter within
                          the template.
                        type: str
                      not_param:
                        description: Indicates whether
                          the entry is not to be treated
                          as a parameter.
                        type: bool
                      order:
                        description: Determines the
                          sequence in which the parameter
                          appears relative to others.
                        type: int
                      param_array:
                        description: Specifies if the
                          parameter should be treated
                          as an array.
                        type: bool
                      parameter_name:
                        description: The name of the
                          parameter.
                        type: str
                      provider:
                        description: Denotes the provider
                          associated with the parameter.
                        type: str
                      range:
                        description: Defines the permissible
                          range for the parameter's
                          value.
                        suboptions:
                          id:
                            description: Unique identifier
                              for the range, represented
                              as a UUID.
                            type: str
                          max_value:
                            description: Specifies the
                              maximum allowable value
                              for the parameter.
                            type: int
                          min_value:
                            description: Specifies the
                              minimum allowable value
                              for the parameter.
                            type: int
                        type: list
                        elements: dict
                      required:
                        description: Dictates whether
                          the parameter is required
                          for template operations.
                        type: bool
                      selection:
                        description: Contains options
                          for parameter selection when
                          a choice is available.
                        suboptions:
                          default_selected_values:
                            description: Lists the default
                              values that are preselected.
                            elements: str
                            type: list
                          id:
                            description: A unique identifier
                              for the selection entity,
                              represented as a UUID.
                            type: str
                          selection_type:
                            description: Specifies the
                              type of selection, such
                              as 'SINGLE_SELECT' or
                              'MULTI_SELECT'.
                            type: str
                          selection_values:
                            description: A dictionary
                              of available values for
                              selection.
                            type: dict
                        type: dict
                    type: list
                    elements: dict
                  version:
                    description: The current version
                      of template.
                    type: str
              project_name:
                description: ProjectName path parameter.
                  Project name to create template under
                  the project.
                type: str
      deploy_template:
        description: To deploy the template to the devices
          based on either list of site provisionig details
          with further filtering criteria like device
          family, device role, device tag or by providing
          the device specific details which includes
          device_ips, device_hostnames, serial_numbers
          or mac_addresses.
        type: dict
        suboptions:
          project_name:
            description: Provide the name of project
              under which the template is available.
            type: str
          template_name:
            description: Name of the template to be
              deployed.
            type: str
          force_push:
            description: Boolean flag to indicate whether
              the template should be forcefully pushed
              to the devices, overriding any existing
              configuration.
            type: bool
          is_composite:
            description: Boolean flag indicating whether
              the template is composite, which means
              the template is built using multiple smaller
              templates.
            type: bool
          member_template_deployment_info:
            description:
              - A list of member template deployment
                details used when deploying a composite
                template.
              - Each entry describes a child template
                and its deployment parameters.
              - Required when is_composite is set to
                true.
            type: list
            elements: dict
            suboptions:
              project_name:
                description:
                - Name of the project under which the member
                  template resides in Catalyst Center.
                - Matched against the 'name' field of projects
                  returned by the Catalyst Center API.
                - If omitted, defaults to the parent template's
                  project_name, allowing member templates in the
                  same project to be referenced without
                  repetition.
                - Applies per member entry in the
                  member_template_deployment_info list.
                - For example, 'Composite_Project'.
                type: str
              template_name:
                description: Name of the member template
                  to deploy.
                type: str
                required: true
              force_push_template:
                description: Whether to force push the
                  member template to the device even if
                  the template has already been applied.
                type: bool
                default: true
              copy_config:
                description: Whether to copy the running
                  configuration to startup after applying
                  the member template.
                type: bool
                default: true
              template_parameters:
                description: A list of parameter name-value
                  pairs for customizing the member template.
                type: list
                elements: dict
                suboptions:
                  param_name:
                    description: Name of the parameter.
                    type: str
                  param_value:
                    description: Value for the parameter.
                    type: str
          copy_config:
            description:
              - A boolean flag that specifies whether
                the device's running configuration should
                be copied to the startup configuration
                after applying the template.
              - If set to 'true', the updated configuration
                will be saved to the startup configuration.
                be copied to the start up config from
                the device before applying the template.
            type: bool
            default: true
          version:
            description: This is useful for targeting specific template versions, such as rolling back
              to a tested version.
            type: int
          template_parameters:
            description: A list of parameter name-value
              pairs used for customizing the template
              with specific values for each device.
            type: list
            elements: dict
            suboptions:
              param_name:
                description: Name of the parameter in
                  the template that needs to be replaced
                  with a specific value.
                type: str
              param_value:
                description: Value assigned to the parameter
                  for deployment to devices.
                type: str
          resource_parameters:
            description: A list of configuration parameters
              required for provisioning resources in
              the system. These parameters define specific
              settings or details that must be supplied
              when deploying templates. If the template
              uses system variables (variables prefixed
              with __, (e.g., __device), the corresponding
              resource parameters must be provided to
              ensure successful deployment.
            type: list
            elements: dict
            suboptions:
              resource_type:
                description: The type of the resource param that is to be provisioned during template deployment
                  - Specifies the type of the resource parameter to be provisioned during template deployment.
                  - Possible enum values are -
                    - MANAGED_DEVICE_UUID - Used when the parameter value is the UUID of the device.
                    - MANAGED_DEVICE_IP - Used when the parameter value is the device's IP address.
                    - MANAGED_DEVICE_HOSTNAME - Used when the parameter value is the device's hostname.
                    - SITE_UUID - Used when the parameter value is the UUID of a site.
                    - MANAGED_AP_LOCATIONS - Used when the parameter value is the locations of managed access points within the network.
                    - SECONDARY_MANAGED_AP_LOCATIONS - Used when the parameter value is the locations of secondary or backup managed access points.
                    - SSID_NAME - Used when the parameter value is the name of a wireless network.
                    - POLICY_PROFILE - Used when the parameter value is a set of policies that can be applied to network devices or users.
                    - From the above enum values, the following resource types support value provisioning at runtime
                      - MANAGED_DEVICE_UUID
                      - MANAGED_DEVICE_IP
                      - MANAGED_DEVICE_HOSTNAME
                      - SITE_UUID
                    - For all other resource types, the values must be provided at design time in the playbook.
                type: str
              resource_scope:
                description:
                  - Specifies the scope in which the
                    resource parameter is to be provisioned.
                  - Possible enum values are - - RUNTIME
                    - A parameter with a runtime scope
                    is provided at the time of deployment.
                    These values are dynamic and may
                    change with each deployment, as
                    they are based on the specific context
                    of the deployment. - DESIGN - A
                    parameter with a design scope is
                    defined during the design phase
                    of the template. These values are
                    static after template creation and
                    remain consistent across deployments.
                type: str
              resource_value:
                description: The actual value of the
                  resource param to be provisioned.
                type: str
          device_details:
            description: Details specific to devices
              where the template will be deployed, including
              lists of device IPs, hostnames, serial
              numbers, or MAC addresses.
            type: dict
            suboptions:
              device_ips:
                description: A list of IP addresses
                  of the devices where the template
                  will be deployed.
                type: list
                elements: str
              device_hostnames:
                description: A list of hostnames of
                  the devices where the template will
                  be deployed.
                type: list
                elements: str
              serial_numbers:
                description: A list of serial numbers
                  of the devices where the template
                  will be deployed.
                type: list
                elements: str
              mac_addresses:
                description: A list of MAC addresses
                  of the devices where the template
                  will be deployed.
                type: list
                elements: str
          site_provisioning_details:
            description: Parameters related to site-based
              provisioning, allowing the deployment
              of templates to devices associated with
              specific sites, with optional filtering
              by device family, role, or tag.
            type: list
            elements: dict
            suboptions:
              site_name:
                description: Name of the site where
                  the devices are associated for provisioning.
                type: list
                elements: str
              device_family:
                description: Family of the devices (e.g.,
                  switches, routers) used to filter
                  devices for template deployment.
                type: str
              device_role:
                description: Role of the devices (e.g.,
                  access, core, edge) used to filter
                  devices for template deployment.
                type: str
              device_tag:
                description: Specific device tag used
                  to filter devices for template deployment.
                type: str

requirements:
  - catalystcentersdk >= 3.2.3.0.0
  - python >= 3.12
notes:
  - SDK Method used are
    configuration_templates.ConfigurationTemplates.create_template,
    configuration_templates.ConfigurationTemplates.deletes_the_template,
    configuration_templates.ConfigurationTemplates.update_template,
    configuration_templates.ConfigurationTemplates.export_projects,
    configuration_templates.ConfigurationTemplates.export_templates,
    configuration_templates.ConfigurationTemplates.imports_the_projects_provided,
    configuration_templates.ConfigurationTemplates.imports_the_templates_provided,

  - Paths used are
    post /dna/intent/api/v1/template-programmer/project/{projectId}/template,
    delete /dna/intent/api/v1/template-programmer/template/{templateId},
    put /dna/intent/api/v1/template-programmer/template,
    post /dna/intent/api/v1/template-programmer/project/name/exportprojects,
    post /dna/intent/api/v1/template-programmer/template/exporttemplates,
    post /dna/intent/api/v1/template-programmer/project/importprojects,
    post /dna/intent/api/v1/template-programmer/project/name/{projectName}/template/importtemplates,
  - While deploying the template to devices, the value for the following resource types can be filled in the resource parameters at
    RUNTIME- MANAGED_DEVICE_UUID, MANAGED_DEVICE_IP, MANAGED_DEVICE_HOSTNAME, and SITE_UUID. For all other resource types, the value
    must be provided at DESIGN time in the playbook.
  - Sensitive data such as template parameter values, credentials, or other confidential information can be protected
    using Ansible Vault. Store sensitive values in a vault-encrypted file and reference them as variables in the playbook.
    Use C(ansible-vault encrypt <file>) to encrypt the file and pass C(--ask-vault-pass) or C(--vault-password-file)
    when running the playbook.
"""

EXAMPLES = r"""
---
- name: Create a new template.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      - configuration_templates:
          author: string
          composite: true
          custom_params_order: true
          template_description: string
          device_types:
            - product_family: string
              product_series: string
              product_type: string
          failure_policy: string
          id: string
          language: string
          template_name: string
          project_name: string
          project_description: string
          profile_names:
            - string
          software_type: string
          software_version: string
          tags:
            - id: string
              name: string
          template_content: string
          version: string

- name: Update a template.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      - configuration_templates:
          author: string
          composite: true
          custom_params_order: true
          template_description: string
          device_types:
            - product_family: string
              product_series: string
              product_type: string
          failure_policy: string
          id: string
          language: string
          template_name: string
          new_template_name: string
          project_name: string
          project_description: string
          profile_names:
            - string
          software_type: string
          software_version: string
          tags:
            - id: string
              name: string
          template_content: string

- name: Export the projects.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      export:
        project:
          - string
          - string

- name: Export the templates.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      export:
        template:
          - project_name: string
            template_name: string
          - project_name: string
            template_name: string

- name: Import the Projects.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      import:
        project:
          do_version: false
          payload:
            - name: string
            - name: string

- name: Import the Templates.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      import:
        template:
          do_version: false
          project_name: string
          template_file: string

- name: Creating a JINJA-based template to configure
    access VLAN and interfaces on Catalyst 9300
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{catalystcenter_host}}"
    catalystcenter_username: "{{catalystcenter_username}}"
    catalystcenter_password: "{{catalystcenter_password}}"
    catalystcenter_verify: "{{catalystcenter_verify}}"
    catalystcenter_port: "{{catalystcenter_port}}"
    catalystcenter_version: "{{catalystcenter_version}}"
    catalystcenter_debug: "{{catalystcenter_debug}}"
    catalystcenter_log: true
    catalystcenter_log_level: "{{catalystcenter_log_level}}"
    state: merged
    config_verify: true
    config:
      - configuration_templates:
          author: Test_User
          composite: false
          custom_params_order: true
          template_description: Template to configure access
            VLAN and access interfaces
          device_types:
            - product_family: Switches and Hubs
              product_series: Cisco Catalyst 9300 Series
                Switches
          failure_policy: ABORT_TARGET_ON_ERROR
          language: JINJA
          template_name: PnP-Upstream-SW1
          project_name: access_vlan_template_9300_switches
          project_description: This project contains
            all the templates for Access Switches
          software_type: IOS-XE
          template_content: |
            {% raw %}
            vlan {{ vlan }}
            interface {{ interface }}
            no shutdown
            switchport access vlan {{ vlan }}
            switchport mode access
            description {{ interface_description }}
            {% endraw %}
          version: "1.0"

- name: Creating a VELOCITY-based Fusion Router template
    for Catalyst 3850 switches
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{catalystcenter_host}}"
    catalystcenter_username: "{{catalystcenter_username}}"
    catalystcenter_password: "{{catalystcenter_password}}"
    catalystcenter_verify: "{{catalystcenter_verify}}"
    catalystcenter_port: "{{catalystcenter_port}}"
    catalystcenter_version: "{{catalystcenter_version}}"
    catalystcenter_debug: "{{catalystcenter_debug}}"
    catalystcenter_log: true
    catalystcenter_log_level: "{{catalystcenter_log_level}}"
    state: merged
    config_verify: true
    config:
      - configuration_templates:
          template_name: "Fusion Router Config"
          template_description: "VELOCITY template to configure
            L3 handoff and loopback on Catalyst 3850"
          project_name: "Network Configuration Templates"
          tags: []
          author: admin
          device_types:
            - product_family: "Switches and Hubs"
              product_series: "Cisco Catalyst 3850 Series
                Ethernet Stackable Switch"
          software_type: IOS-XE
          language: VELOCITY
          failure_policy: ABORT_TARGET_ON_ERROR
          template_content: |
            ! L3handoff Vlan
            vlan $VLANID
            hostname  Old$__device.hostname
            interface Loopback0
            ip address $LOOPBACKIP 255.255.255.255
            ipv6 address $LOOPBACKIPV6
            ipv6 enable
            ipv6 nd other-config-flag
            ipv6 dhcp server EMPPool
            ! L3handdoff interface for provider VN
            interface Vlan$VLANID
            description L3handoff $VLANID
            ip address $interfaceIP 255.255.255.252
            ip route-cache same-interface
            ipv6 address $interfaceIPV6
            ipv6 enable
            ipv6 tcp adjust-mss 1400

- name: Deploy the given template to the devices based
    on site specific details and other filtering mode
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      deploy_template:
        project_name: "Sample_Project"
        template_name: "Sample Template"
        force_push: true
        template_parameters:
          - param_name: "vlan_id"
            param_value: "1431"
          - param_name: "vlan_name"
            param_value: "testvlan31"
        site_provisioning_details:
          - site_name: "Global/Bangalore/Building14/Floor1"
            device_family: "Switches and Hubs"

- name: Deploy the given template to the devices based
    on device specific details
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      deploy_template:
        project_name: "Sample_Project"
        template_name: "Sample Template"
        force_push: true
        template_parameters:
          - param_name: "vlan_id"
            param_value: "1431"
          - param_name: "vlan_name"
            param_value: "testvlan31"
        device_details:
          device_ips: ["10.1.2.1", "10.2.3.4"]

- name: Deploy template to the devices using resource
    parameters and copying config
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{catalystcenter_host}}"
    catalystcenter_username: "{{catalystcenter_username}}"
    catalystcenter_password: "{{catalystcenter_password}}"
    catalystcenter_verify: "{{catalystcenter_verify}}"
    catalystcenter_port: "{{catalystcenter_port}}"
    catalystcenter_version: "{{catalystcenter_version}}"
    catalystcenter_debug: "{{catalystcenter_debug}}"
    catalystcenter_log: true
    catalystcenter_log_level: "{{catalystcenter_log_level}}"
    state: merged
    config_verify: true
    config:
      deploy_template:
        project_name: "Sample_Project"
        template_name: "Sample Template"
        force_push: true
        template_parameters:
          - param_name: "vlan_id"
            param_value: "1431"
          - param_name: "vlan_name"
            param_value: "testvlan31"
        resource_parameters:
          - resource_type: "MANAGED_DEVICE_IP"
            resource_scope: "RUNTIME"
        device_details:
          device_ips: ["10.1.2.1", "10.2.3.4"]
        copy_config: true

- name: Delete the given project or template from the
    Cisco Catalyst Center
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: deleted
    config:
      configuration_templates:
        project_name: "Sample_Project"
        template_name: "Sample Template"
        language: "velocity"
        software_type: "IOS-XE"
        device_types:
          - product_family: "Switches and Hubs"

- name: Create a New Project
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      - projects:
          - name: Wireless_Controller
            description: Centralized repository for managing templates and configurations for wireless controllers (WLCs).

- name: Update project name and details.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      - projects:
          - name: Wireless_Controller
            new_name: Wireless_Template_Management
            description: Centralized repository for managing templates and configurations for wireless controllers (WLCs).

- name: Delete project based on the name.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: deleted
    config:
      - projects:
          - name: Wireless_Template_Management

- name: Creating complete configuration template with profiles
    response in Case_9
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{catalystcenter_host}}"
    catalystcenter_username: "{{catalystcenter_username}}"
    catalystcenter_password: "{{catalystcenter_password}}"
    catalystcenter_verify: "{{catalystcenter_verify}}"
    catalystcenter_port: "{{catalystcenter_port}}"
    catalystcenter_version: "{{catalystcenter_version}}"
    catalystcenter_debug: "{{catalystcenter_debug}}"
    catalystcenter_log: true
    catalystcenter_log_level: "{{catalystcenter_log_level}}"
    state: merged
    config_verify: true
    config:
      - configuration_templates:
          author: Test_User
          composite: false
          custom_params_order: true
          template_description: Template to configure access
            VLAN and access interfaces
          device_types:
            - product_family: Switches and Hubs
              product_series: Cisco Catalyst 9300 Series
                Switches
          failure_policy: ABORT_TARGET_ON_ERROR
          language: JINJA
          template_name: PnP-Upstream-SW1
          profile_names:
            - TestProfile
            - PNP_Onboarding_Template
          project_name: access_vlan_template_9300_switches
          project_description: This project contains
            all the templates for Access Switches
          software_type: IOS-XE
          template_content: |
            {% raw %}
            vlan {{ vlan }}
            interface {{ interface }}
            no shutdown
            switchport access vlan {{ vlan }}
            switchport mode access
            description {{ interface_description }}
            {% endraw %}
          version: "1.0"

- name: Update configuration template with additional profile
    response in Case_10
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{catalystcenter_host}}"
    catalystcenter_username: "{{catalystcenter_username}}"
    catalystcenter_password: "{{catalystcenter_password}}"
    catalystcenter_verify: "{{catalystcenter_verify}}"
    catalystcenter_port: "{{catalystcenter_port}}"
    catalystcenter_version: "{{catalystcenter_version}}"
    catalystcenter_debug: "{{catalystcenter_debug}}"
    catalystcenter_log: true
    catalystcenter_log_level: "{{catalystcenter_log_level}}"
    state: merged
    config_verify: true
    config:
      - configuration_templates:
          author: Test_User
          composite: false
          custom_params_order: true
          template_description: Template to configure access
            VLAN and access interfaces
          device_types:
            - product_family: Switches and Hubs
              product_series: Cisco Catalyst 9300 Series
                Switches
          failure_policy: ABORT_TARGET_ON_ERROR
          language: JINJA
          template_name: PnP-Upstream-SW1
          profile_names:
            - TestProfile
            - PNP_Onboarding_Template
          project_name: access_vlan_template_9300_switches
          project_description: This project contains
            all the templates for Access Switches
          software_type: IOS-XE
          template_content: |
            {% raw %}
            vlan {{ vlan }}
            interface {{ interface }}
            no shutdown
            switchport access vlan {{ vlan }}
            switchport mode access
            description {{ interface_description }}
            {% endraw %}
          version: "1.0"

- name: Detach a profile from the configuration template on deleted state
    response in Case_11
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: deleted
    config:
      configuration_templates:
        project_name: "access_vlan_template_9300_switches"
        template_name: "AA_PnP-Upstream-SW1"
        language: "JINJA"
        software_type: "IOS-XE"
        profile_names:
          - TestProfile
        device_types:
          - product_family: "Switches and Hubs"

- name: Deleting configuration template no need to attach profiles
    it will unassign profiles and delete the template without impacting profiles
    response in Case_12
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: "{{ catalystcenter_log_level }}"
    catalystcenter_log: true
    config_verify: true
    state: deleted
    config:
      configuration_templates:
        project_name: "access_vlan_template_9300_switches"
        template_name: "AA_PnP-Upstream-SW1"
        language: "JINJA"
        software_type: "IOS-XE"
        device_types:
          - product_family: "Switches and Hubs"

- name: Create L2VN anycast template in Catalyst Center where
    template content is stored in a file and its path is set in a ENV variable.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: DEBUG
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      - configuration_templates:
          project_name: "evpn_l2vn_anycast"
          template_name: "evpn_l2vn_anycast_template"
          template_content_file_path: "{{ lookup('env', 'BGPEVPN_L2VNANYCAST_TEMPDIR_PATH') | mandatory }}/evpn_anycast.j2"
          version_description: "Raw Jinja BGP EVPN L2VN anycast template"
          language: JINJA
          software_type: "IOS-XE"
          device_types:
            - product_family: Switches and Hubs

- name: Create L2VN anycast template in Catalyst Center where
    template content is stored in a file and its relative path is provided. validate_jinja2_syntax is set to true.
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log_level: DEBUG
    catalystcenter_log: true
    config_verify: true
    state: merged
    config:
      - configuration_templates:
          project_name: "evpn_l2vn_anycast"
          template_name: "evpn_l2vn_anycast_template"
          template_content_file_path: "evpn_templates/evpn_anycast.j2"
          validate_jinja2_syntax: true
          version_description: "Raw Jinja BGP EVPN L2VN anycast template"
          language: JINJA
          software_type: "IOS-XE"
          device_types:
            - product_family: Switches and Hubs

- name: Deploy a composite template with member templates to devices based on device specific details
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log: true
    catalystcenter_log_level: DEBUG
    catalystcenter_log_append: true
    validate_response_schema: false
    state: "merged"
    config_verify: true
    config:
      - deploy_template:
          project_name: "composite_project"
          template_name: "composite_template"
          is_composite: true
          force_push: true
          member_template_deployment_info:
            - project_name: "composite_project"
              template_name: "containing_template1"
              copy_config: false
            - project_name: "composite_project"
              template_name: "containing_template2"
              copy_config: false
          device_details:
            device_ips:
              - 10.1.1.1

- name: Deploy a composite template with member templates using template_parameters to devices based on device specific details
  cisco.catalystcenter.template_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_port: "{{ catalystcenter_port }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    catalystcenter_debug: "{{ catalystcenter_debug }}"
    catalystcenter_log: true
    catalystcenter_log_level: DEBUG
    catalystcenter_log_append: true
    validate_response_schema: false
    state: "merged"
    config_verify: true
    config:
      - deploy_template:
          project_name: "composite_project"
          template_name: "composite_template"
          is_composite: true
          force_push: true
          member_template_deployment_info:
            - project_name: "composite_project"
              template_name: "containing_template1"
              copy_config: false
              template_parameters:
                - param_name: "name"
                  param_value: "abc"
            - project_name: "composite_project"
              template_name: "containing_template2"
              copy_config: false
              template_parameters:
                - param_name: "name"
                  param_value: "xyz"
          device_details:
            device_ips:
              - 10.1.1.1

- name: Deploy template with sensitive parameter values protected using Ansible Vault
  # Step 1 - Create a vault file (e.g., vault_vars.yml) with sensitive values:
  #   password: "my_password"
  # Step 2 - Encrypt it: ansible-vault encrypt vault_vars.yml --ask-vault-pass
  # Step 3 - Run the playbook: ansible-playbook playbook.yml --ask-vault-pass
  hosts: localhost
  vars_files:
    - credentials.yml
    - vault_vars.yml
  gather_facts: false
  tasks:
    - name: Deploy template with vaulted parameter values
      cisco.catalystcenter.template_workflow_manager:
        catalystcenter_host: "{{ catalystcenter_host }}"
        catalystcenter_port: "{{ catalystcenter_port }}"
        catalystcenter_username: "{{ catalystcenter_username }}"
        catalystcenter_password: "{{ catalystcenter_password }}"
        catalystcenter_verify: "{{ catalystcenter_verify }}"
        catalystcenter_version: "{{ catalystcenter_version }}"
        catalystcenter_debug: "{{ catalystcenter_debug }}"
        catalystcenter_log: true
        catalystcenter_log_level: "{{ catalystcenter_log_level }}"
        state: merged
        config_verify: true
        config:
          - deploy_template:
              project_name: "Sample_Project"
              template_name: "Sample Template"
              force_push: true
              template_parameters:
                - param_name: "password"
                  param_value: "{{ password }}"
              device_details:
                device_ips:
                  - 10.1.2.1
"""

RETURN = r"""
# Case_1: Successful creation/update/deletion of template/project
response_1:
  description: A dictionary with versioning details of the template as returned by the Cisco Catalyst Center Python SDK
  returned: always
  type: dict
  sample: >
    {
      "response": {
                        "endTime": 0,
                        "version": 0,
                        "data": String,
                        "startTime": 0,
                        "username": String,
                        "progress": String,
                        "serviceType": String, "rootId": String,
                        "isError": bool,
                        "instanceTenantId": String,
                        "id": String
                        "version": 0
                  },
      "msg": String
    }

# Case_2: Error while deleting a template or when given project is not found
response_2:
  description: A list with the response returned by the Cisco Catalyst Center Python SDK
  returned: always
  type: list
  sample: >
    {
      "response": [],
      "msg": String
    }

# Case_3: Given template already exists and requires no update
response_3:
  description: A dictionary with the exisiting template deatails as returned by the Cisco Catalyst Center Python SDK
  returned: always
  type: dict
  sample: >
    {
      "response": {},
      "msg": String
    }

# Case_4: Given template list that needs to be exported
response_4:
  description: Details of the templates in the list as returned by the Cisco Catalyst Center Python SDK
  returned: always
  type: dict
  sample: >
    {
      "response": {},
      "msg": String
    }

# Case_5: Given project list that needs to be exported
response_5:
  description: Details of the projects in the list as returned by the Cisco Catalyst Center Python SDK
  returned: always
  type: dict
  sample: >
    {
      "response": {},
      "msg": String
    }

# Case_6: Response for Creating a Project with a Name
response_6:
  description: Response when a project is created successfully
  returned: always
  type: dict
  sample: >
    {
        "msg": "project Wireless_Controller created successfully",
        "response": "project Wireless_Controller created successfully",
        "status": "success"
    }

# Case_7: Response for Updating a Project with a Name
response_7:
  description: Provides details of the response when a project is successfully updated using the Cisco Catalyst Center Python SDK.
  returned: always
  type: dict
  sample: >
    {
        "msg": "Project 'Wireless_Template_Management' updated successfully.",
        "response": Project 'Wireless_Template_Management' updated successfully.",
        "status": "success"
    }

# Case_8: Response for Deleting a Project by Name
response_8:
  description: Response when a project is Deleted successfully.
  returned: always
  type: dict
  sample: >
    {
        "msg": "Project(s) are deleted and verified successfully. ['Wireless_Template_Management']",
        "response": [
            {
                "name": "Wireless_Template_Management"
            }
        ],
        "status": "success"
    }

# Case_9: Response for Creating a Complete Configuration Template with profiles
response_9:
  description: Response when a complete configuration template is created successfully with profiles.
  returned: always
  type: dict
  sample: >
    {
        "msg": "Template '['AA_PnP-Upstream-SW1']' created successfully in the Cisco Catalyst Center.
                Template '['AA_PnP-Upstream-SW1']' committed successfully in the Cisco Catalyst Center.
                Profile(s) '['TestProfile', 'PNP_Onboarding_Template']' assigned successfully to the template.",
        "response": "Template '['AA_PnP-Upstream-SW1']' created successfully in the Cisco Catalyst Center.
                    Template '['AA_PnP-Upstream-SW1']' committed successfully in the Cisco Catalyst Center.
                    Profile(s) '['TestProfile', 'PNP_Onboarding_Template']' assigned successfully to the template.",
        "status": "success"
    }

# Case_10: Response for Updating a Configuration Template with Additional Profile
response_10:
  description: Response when a configuration template is updated successfully with an additional profile.
  returned: always
  type: dict
  sample: >
    {
        "msg": "Template '['AA_PnP-Upstream-SW1']' updated successfully in the Cisco Catalyst Center.
                Template '['AA_PnP-Upstream-SW1']' committed successfully in the Cisco Catalyst Center.
                Profile(s) '['PNP_Onboarding_Template']' assigned successfully to the template.
                Profile(s) '['TestProfile']' already exist and cannot be assigned to the template.",
        "response": "Template '['AA_PnP-Upstream-SW1']' updated successfully in the Cisco Catalyst Center.
                    Template '['AA_PnP-Upstream-SW1']' committed successfully in the Cisco Catalyst Center.
                    Profile(s) '['PNP_Onboarding_Template']' assigned successfully to the template.
                    Profile(s) '['TestProfile']' already exist and cannot be assigned to the template.",
        "status": "success"
    }

# Case_11: Response for Detach a profile from the configuration template on deleted state
response_11:
  description: Response when a profile is detached from the configuration template on deleted state.
  returned: always
  type: dict
  sample: >
    {
        "msg": "Profile(s) '['TestProfile']' detached successfully from the template.",
        "response": "Profile(s) '['TestProfile']' detached successfully from the template.",
        "status": "success"
    }

# Case_12: Response for Deleting a configuration template without affecting profiles
response_12:
  description: Response when a configuration template is deleted without affecting profiles.
  returned: always
  type: dict
  sample: >
    {
        "msg": "Task: deletes_the_template is successful for parameters:
                {'template_id': '9a68dfa3-86ac-442b-bc92-957bfbd76ca7', 'active_validation': False}",
        "response": "Task: deletes_the_template is successful for parameters:
                    {'template_id': '9a68dfa3-86ac-442b-bc92-957bfbd76ca7', 'active_validation': False}",
        "status": "success"
    }
"""

import json
import time
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter import (
    get_dict_result,
)
from ansible_collections.cisco.catalystcenter.plugins.module_utils.template_common import (
    TemplateCommon,
)


class Template(TemplateCommon):
    """Class containing member attributes for template_workflow_manager module"""

    def delete_project(self, project_name):
        """
        Deletes a project from Cisco Catalyst Center by its name.

        Args:
          self (object): An instance of the class used to interact with Cisco Catalyst Center.
          project_name (str): The name of the project to delete.

        Returns:
          object: The current instance of the class with updated status and result attributes.

        Description:
          This method attempts to locate a project by its name and delete it using the appropriate API call.
          If the project is found and deleted successfully, the method updates the status, result, and logs
          the outcome. In cases of failure (e.g., missing name, project not found, or API error), it sets the
          operation result to failed and logs the issue accordingly.
        """
        self.log(
            "Attempting to delete project with name: {0}".format(project_name), "DEBUG"
        )

        if not project_name:
            self.msg = "No project name provided for deletion."
            self.log(self.msg, "WARNING")
            return self

        # Fetch the project ID using the project name
        project_id = None
        for each_project in self.have.get("projects"):
            if each_project.get("name") == project_name:
                project_id = each_project.get("id")
                break

        if not project_id:
            self.msg = "Could not find a project with the name: {0}".format(
                project_name
            )
            self.log(self.msg, "ERROR")
            self.status = "failed"
            return self

        # If a valid project ID is found, proceed to delete the project
        self.log(
            "Found project ID: {0} for project name: {1}".format(
                project_id, project_name
            ),
            "INFO",
        )

        try:
            function_name = "delete_template_project"
            params = {"project_id": project_id}
            task_id = self.get_taskid_post_api_call(
                "configuration_templates", function_name, params
            )

            if not task_id:
                self.msg = "Unable to retrieve the task_id for the task '{0}'.".format(
                    function_name
                )
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self

            self.log(
                "Successfully deleted project with ID: {0}".format(project_name), "INFO"
            )
            self.result["changed"] = True  # Indicate that the project was deleted
            self.status = "success"
            self.msg = "Successfully deleted project: {0}".format(project_name)
            return self

        except Exception as e:
            self.msg = (
                "An error occurred while deleting project {0} (ID: {1}). ".format(
                    project_name, project_id
                )
            )
            self.log(self.msg + str(e), "ERROR")
            self.status = "failed"

        return self

    def apply_project_config(self, config):
        """
        Create or update projects based on the presence of a 'new_name' key in each project config.

        Parameters:
            self (object): An instance of a class for interacting with Cisco Catalyst Center.
            config (list[dict]): A list of dictionaries, each containing project details.

        Returns:
            self: The current instance with updated project configuration.
        """
        self.log(
            "Starting to apply project configurations. Total projects: {0}".format(
                len(config)
            ),
            "INFO",
        )

        for project in config:
            project_name = project.get("name", "Unnamed Project")
            self.log("Processing project: {0}".format(project_name), "DEBUG")
            if project.get("new_name"):
                self.log(
                    "Updating project: {0} with new name: {1}".format(
                        project_name, project.get("new_name")
                    ),
                    "INFO",
                )
                self.update_project(project)
            else:
                self.log("Creating project: {0}".format(project_name), "INFO")
                self.create_project(project)

        self.log("Finished applying project configurations.", "INFO")
        return self

    def create_project(self, project_detail):
        """
        Create a new project in Cisco Catalyst Center with the provided details.

        Parameters:
            self (object): An instance of a class for interacting with Cisco Catalyst Center.
            project_detail (dict): Dictionary containing project details.

        Returns:
            self: The current instance with created project configuration.
        """

        self.log(
            "Processing Project creation with input details: {0}".format(
                self.pprint(project_detail)
            ),
            "DEBUG",
        )

        if not project_detail:
            self.msg = "No project details provided for creation."
            self.log(self.msg, "WARNING")
            return self

        try:
            create_project_params = {
                "name": project_detail.get("name"),
                "description": project_detail.get("description"),
                "createTime": int(time.time()),
                "lastUpdateTime": int(time.time()),
            }

            self.log(
                "Creating project with parameters: {0}".format(
                    self.pprint(create_project_params)
                ),
                "INFO",
            )

            task_name = "create_project"
            task_id = self.get_taskid_post_api_call(
                "configuration_templates", task_name, create_project_params
            )

            if not task_id:
                self.msg = "Unable to retrieve the task_id for the task '{0}'.".format(
                    task_name
                )
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self

            success_msg = "project(s) {0} created successfully".format(
                project_detail.get("name")
            )
            self.log(
                "Task ID '{0}' received. Checking task status.".format(task_id), "DEBUG"
            )
            self.get_task_status_from_tasks_by_id(task_id, task_name, success_msg)
            self.log(
                "project(s) {0} created successfully".format(
                    project_detail.get("name")
                ),
                "INFO",
            )
            return self

        except Exception as e:
            self.msg = "Failed to create the project - ({0}) from Cisco Catalyst Center due to - {1}".format(
                project_detail.get("name"), str(e)
            )
            self.set_operation_result("failed", False, self.msg, "ERROR")

    def update_project(self, project_detail):
        """
        Identify an existing project in Cisco Catalyst Center by its current name and description,
        and update it with the new name and project details.

        Parameters:
            self (object): An instance of a class for interacting with Cisco Catalyst Center.
            project_detail (dict): Dictionary containing the project config details.

        Returns:
            self: The current instance with updated project configuration.
        """

        self.log(
            "Processing Project update with input details: {0}".format(
                self.pprint(project_detail)
            ),
            "DEBUG",
        )

        if not project_detail:
            self.msg = "No project details provided for update."
            self.log(self.msg, "WARNING")
            return self

        try:
            old_name = project_detail.get("name")
            new_name = project_detail.get("new_name")

            if not old_name or not new_name:
                self.msg = "Both 'name' (old name) and 'new_name' (new name) are required for the update."
                self.log(self.msg, "ERROR")
                return self

            # Get the existing project info
            existing_projects = self.get_project_details(old_name)
            if not existing_projects:
                self.msg = "Project with name '{0}' not found.".format(old_name)
                self.log(self.msg, "ERROR")
                return self

            existing_project = existing_projects[0]
            # Prepare update parameters
            update_project_params = {
                "id": existing_project.get("id"),
                "name": new_name,
                "description": project_detail.get(
                    "description", existing_project.get("description")
                ),
                "createTime": existing_project.get("createTime"),
                "lastUpdateTime": int(time.time()),
                "templates": project_detail.get(
                    "templates", existing_project.get("templates", [])
                ),
            }

            # Log the update parameters
            self.log(
                "Updating project with parameters: {0}".format(
                    self.pprint(update_project_params)
                ),
                "DEBUG",
            )

            task_name = "update_project"
            task_id = self.get_taskid_post_api_call(
                "configuration_templates", task_name, update_project_params
            )

            if not task_id:
                self.msg = "Unable to retrieve the task_id for the task '{0}'.".format(
                    task_name
                )
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self

            success_msg = "Project(s) '{0}' updated successfully.".format(new_name)
            self.log(
                "Task ID '{0}' received. Checking task status.".format(task_id), "DEBUG"
            )
            self.get_task_status_from_tasks_by_id(task_id, task_name, success_msg)

            self.log("Project(s) '{0}' updated successfully.".format(new_name), "INFO")
            return self

        except Exception as e:
            self.msg = "Failed to update the project '{0}' due to error: {1}".format(
                project_detail.get("name"), str(e)
            )
            self.set_operation_result("failed", False, self.msg, "ERROR")
            return self

    def get_export_template_values(self, export_values):
        """
        Get the export template values from the details provided by the playbook.

        Parameters:
            export_values (bool) - All the template available under the project.

        Returns:
            self
        """

        all_project_details = self.catalystcenter._exec(
            family="configuration_templates", function="get_projects_details"
        )
        self.log(
            "Received response from 'get_projects_details' is {0}".format(
                all_project_details
            ),
            "DEBUG",
        )
        all_project_details = all_project_details.get("response")
        for values in export_values:
            project_name = values.get("project_name")
            self.log(
                "Project name for export template: {0}".format(project_name), "DEBUG"
            )
            self.log("Template details: {0}".format(all_project_details), "DEBUG")
            project_details = get_dict_result(all_project_details, "name", project_name)
            if not project_details:
                self.msg = "There are no projects with the given project name '{project_name}'.".format(
                    project_name=project_name
                )
                self.status = "failed"
                return self

            all_template_details = project_details.get("templates")
            if not all_template_details:
                self.msg = "There are no templates associated with the given project name '{project_name}'.".format(
                    project_name=project_name
                )
                self.status = "failed"
                return self

            self.log(
                "Template details under the project name {0}: {1}".format(
                    project_name, all_template_details
                ),
                "DEBUG",
            )
            template_name = values.get("template_name")
            template_details = get_dict_result(
                all_template_details, "name", template_name
            )
            self.log(
                "Template details with template name {0}: {1}".format(
                    template_name, template_details
                ),
                "DEBUG",
            )
            if template_details is None:
                self.msg = (
                    "Invalid 'project_name' and 'template_name' in export templates."
                )
                self.status = "failed"
                return self
            self.export_template.append(template_details.get("id"))

        self.msg = "Successfully collected the export template IDs"
        self.status = "success"
        return self

    def handle_export(self, export):
        """
        Export templates and projects in CCC with fields provided in Cisco Catalyst Center.

        Parameters:
            export (dict) - Playbook details containing export project/template information.

        Returns:
            self
        """

        export_project = export.get("project")
        self.log("Export project playbook details: {0}".format(export_project), "DEBUG")
        if export_project:
            self.log(
                "Found export project details: {0}".format(export_project), "DEBUG"
            )
            response = self.catalystcenter._exec(
                family="configuration_templates",
                function="export_projects",
                op_modifies=True,
                params={
                    "payload": export_project,
                },
            )

            validation_string = "successfully exported project"
            self.check_task_response_status(
                response, validation_string, "export_projects", True
            ).check_return_status()
            self.result["response"][1].get("export").get("response").update(
                {"exportProject": self.msg}
            )

        export_values = export.get("template")
        if export_values:
            self.get_export_template_values(export_values).check_return_status()
            self.log(
                "Exporting template playbook details: {0}".format(self.export_template),
                "DEBUG",
            )
            response = self.catalystcenter._exec(
                family="configuration_templates",
                function="export_templates",
                op_modifies=True,
                params={
                    "payload": self.export_template,
                },
            )
            validation_string = "successfully exported template"
            self.check_task_response_status(
                response, validation_string, "export_templates", True
            ).check_return_status()
            self.result["response"][1].get("export").get("response").update(
                {"exportTemplate": self.msg}
            )

        return self

    def handle_import(self, _import):
        """
        Import templates and projects in CCC with fields provided in Cisco Catalyst Center.

        Parameters:
            _import (dict) - Playbook details containing import project/template information.

        Returns:
            self
        """

        _import_project = _import.get("project")
        if _import_project:
            do_version = _import_project.get("do_version")
            if not do_version:
                do_version = False

            payload = _import.get("project").get("payload")
            project_file = _import.get("project").get("project_file")
            if not (payload or project_file):
                self.msg = "Required parameter 'payload' or 'project_file' is not found under import project"
                self.status = "failed"
                return self

            final_payload = []
            if project_file:
                is_path_exists = self.is_path_exists(project_file)
                if not is_path_exists:
                    self.msg = "Import project file path '{0}' does not exist.".format(
                        project_file
                    )
                    self.status = "failed"
                    return self

                is_json = self.is_json(project_file)
                if not is_json:
                    self.msg = "Import project file '{0}' is not in JSON format".format(
                        project_file
                    )
                    self.status = "failed"
                    return self
                try:
                    with open(project_file, "r") as file:
                        json_data = file.read()
                    json_project = json.loads(json_data)
                    final_payload = json_project
                except Exception as msg:
                    self.msg = "An unexpected error occurred while processing the file '{0}': {1}".format(
                        project_file, msg
                    )
                    self.status = "failed"
                    return self
            elif payload:
                for item in payload:
                    response = self.get_project_details(item.get("name"))
                    if response == []:
                        final_payload.append(item)

            if final_payload != []:
                _import_project = {
                    "do_version": do_version,
                    "payload": final_payload,
                }
                self.log(
                    "Importing project details from the playbook: {0}".format(
                        _import_project
                    ),
                    "DEBUG",
                )
                if _import_project:
                    response = self.catalystcenter._exec(
                        family="configuration_templates",
                        function="imports_the_projects_provided",
                        op_modifies=True,
                        params=_import_project,
                    )
                    validation_string = "successfully imported project"
                    self.check_task_response_status(
                        response, validation_string, "imports_the_projects_provided"
                    ).check_return_status()
                    self.result["response"][2].get("import").get("response").update(
                        {"importProject": "Successfully imported the project(s)."}
                    )
            else:
                self.msg = "Projects '{0}' already available.".format(payload)
                self.result["response"][2].get("import").get("response").update(
                    {
                        "importProject": "Projects '{0}' already available.".format(
                            payload
                        )
                    }
                )

        _import_template = _import.get("template")
        if _import_template:
            do_version = _import_template.get("do_version")
            if not do_version:
                do_version = False

            project_name = _import_template.get("project_name")
            if not _import_template.get("project_name"):
                self.msg = (
                    "Required parameter project_name is not found under import template"
                )
                self.status = "failed"
                return self

            is_project_exists = self.get_project_details(project_name)
            if not is_project_exists:
                self.msg = "Project '{0}' is not found.".format(project_name)
                self.status = "failed"
                return self

            payload = _import_template.get("payload")
            template_file = _import_template.get("template_file")
            if not (payload or template_file):
                self.msg = "Required parameter 'payload' or 'template_file' is not found under import template"
                self.status = "failed"
                return self

            final_payload = None
            if template_file:
                is_path_exists = self.is_path_exists(template_file)
                if not is_path_exists:
                    self.msg = "Import template file path '{0}' does not exist.".format(
                        template_file
                    )
                    self.status = "failed"
                    return self

                is_json = self.is_json(template_file)
                if not is_json:
                    self.msg = (
                        "Import template file '{0}' is not in JSON format".format(
                            template_file
                        )
                    )
                    self.status = "failed"
                    return self
                try:
                    with open(template_file, "r") as file:
                        json_data = file.read()
                    json_template = json.loads(json_data)
                    final_payload = json_template
                except Exception as msg:
                    self.msg = "An unexpected error occurred while processing the file '{0}': {1}".format(
                        template_file, msg
                    )
                    self.status = "failed"
                    return self

            elif payload:
                final_payload = []
                for item in payload:
                    final_payload.append(self.get_template_params(item))
            import_template = {
                "do_version": do_version,
                "project_name": project_name,
                "payload": final_payload,
            }
            self.log(
                "Import template details from the playbook: {0}".format(
                    import_template
                ),
                "DEBUG",
            )
            global_project_name = import_template.get("project_name")
            for item in import_template.get("payload"):
                template_project_name = item.get("projectName")
                if (
                    template_project_name is not None
                    and global_project_name != template_project_name
                ):
                    self.msg = "Template '{0}' under the the 'Import Template' should have project_name as {1}".format(
                        item.get("name"), global_project_name
                    )
                    self.log(str(self.msg), "ERROR")
                    self.status = "failed"
                    return self

            if _import_template:
                response = self.catalystcenter._exec(
                    family="configuration_templates",
                    function="imports_the_templates_provided",
                    op_modifies=True,
                    params=import_template,
                )
                validation_string = "successfully imported template"
                self.check_task_response_status(
                    response, validation_string, "imports_the_templates_provided"
                ).check_return_status()
                self.result["response"][2].get("import").get("response").update(
                    {"importTemplate": "Successfully imported the templates"}
                )

        return self

    def filter_devices_with_family_role(
        self, site_assign_device_ids, device_family=None, device_role=None
    ):
        """
        Filters devices based on their family and role from a list of site-assigned device IDs.

        Args:
            self (object): An instance of the class interacting with Cisco Catalyst Center.
            site_assign_device_ids (list): A list of device IDs (strings) assigned to a site that need to be filtered.
            device_family (str, optional): The family of devices to filter by (e.g., 'Switches and Hubs'). If None,
                this filter is not applied. Defaults to None.
            device_role (str, optional): The role of the devices to filter by (e.g., 'ACCESS', 'CORE'). If None,
                this filter is not applied. Defaults to None.
        Returns:
            list (str): A list of filtered device IDs (strings) that belong to the specified device family and role.
            If no matching devices are found, the list will be empty.
        Description:
            This function filters a list of device IDs based on the specified `device_family` and `device_role` by querying
            the Cisco Catalyst Center API. It iterates over each device ID, checking if the device belongs to the specified
            family and has the desired role. Devices that match the criteria are added to the `filtered_device_list`.
            If a device does not match the criteria or no response is received from the API, the function logs an
            informational message and skips that device. In the event of an error during the API call, it logs the error
            message and continues processing the remaining devices.
            The function returns the list of devices that meet the filtering criteria.
        """

        filtered_device_list = []
        self.log(
            "Filtering devices from the provided site-assigned device IDs: {0},  device_family='{1}', "
            "and device_role='{2}'".format(
                site_assign_device_ids, device_family, device_role
            ),
            "DEBUG",
        )

        for device_id in site_assign_device_ids:
            try:
                self.log("Processing device ID: {0}".format(device_id), "DEBUG")
                response = self.catalystcenter._exec(
                    family="devices",
                    function="get_device_list",
                    op_modifies=True,
                    params={
                        "family": device_family,
                        "id": device_id,
                        "role": device_role,
                    },
                )
                self.log(
                    "Received response from get_device_list for device_family: {0}, device_id: {1}, device_role: {2} is {3}".format(
                        device_family, device_id, device_role, response
                    ),
                    "DEBUG",
                )
                if response and "response" in response:
                    response_data = response.get("response")
                else:
                    self.log(
                        "No valid response for device with ID '{0}'.".format(device_id),
                        "INFO",
                    )
                    continue

                if not response_data:
                    self.log(
                        "Device with ID '{0}' does not match family '{1}' or role '{2}'.".format(
                            device_id, device_family, device_role
                        ),
                        "INFO",
                    )
                    continue

                self.log(
                    "Device with ID '{0}' matches the criteria.".format(device_id),
                    "DEBUG",
                )
                filtered_device_list.append(device_id)

            except Exception as e:
                error_message = "Error while getting the response of device from Cisco Catalyst Center: {0}".format(
                    str(e)
                )
                self.log(error_message, "CRITICAL")
                continue
        self.log(
            "Completed filtering. Filtered devices: {0}".format(filtered_device_list),
            "DEBUG",
        )

        return filtered_device_list

    def get_device_ids_from_tag(self, tag_name, tag_id):
        """
        Retrieves the device IDs associated with a specific tag from the Cisco Catalyst Center.

        Args:
            self (object): An instance of the class used for interacting with Cisco Catalyst Center.
            tag_name (str): The name of the tag, used for logging purposes.
            tag_id (str): The unique identifier of the tag from which to retrieve associated device IDs.
        Returns:
            list (str): A list of device IDs (strings) associated with the specified tag. If no devices are found or
            an error occurs, the function returns an empty list.
        Description:
            This function queries the Cisco Catalyst Center API to retrieve a list of devices associated with a given tag.
            It calls the `get_tag_members_by_id` function using the tag's ID, specifying that the tag members should be of
            type "networkdevice". If the API response contains device data, the function extracts and returns the device IDs.
            The function logs whether the tag has associated devices and details about the API response. In the event of an
            exception, it logs an error message, sets the operation result to "failed," and returns an empty list.
        """

        device_ids = []
        self.log(
            "Fetching device IDs associated with the tag '{0}' (ID: {1}).".format(
                tag_name, tag_id
            ),
            "INFO",
        )

        try:
            response = self.catalystcenter._exec(
                family="tag",
                function="get_tag_members_by_id",
                op_modifies=False,
                params={
                    "id": tag_id,
                    "member_type": "networkdevice",
                },
            )
            if response and "response" in response:
                response_data = response.get("response")
            else:
                self.log(
                    "No valid response for device with tag ID '{0}'.".format(tag_id),
                    "INFO",
                )
                return device_ids

            if not response_data:
                self.log(
                    "No device(s) are associated with the tag '{0}'.".format(tag_name),
                    "WARNING",
                )
                return device_ids

            self.log(
                "Received API response from 'get_tag_members_by_id' for the tag {0}: {1}".format(
                    tag_name, response_data
                ),
                "DEBUG",
            )
            for tag in response_data:
                device_id = tag.get("id")
                self.log(
                    "Device ID '{0}' found for tag '{1}'.".format(device_id, tag_name),
                    "DEBUG",
                )
                device_ids.append(device_id)

        except Exception as e:
            self.msg = (
                "Exception occurred while fetching tag id for the tag '{0} 'from "
                "Cisco Catalyst Center: {1}"
            ).format(tag_name, str(e))
            self.set_operation_result(
                "failed", False, self.msg, "INFO"
            ).check_return_status()

        return device_ids

    def get_diff_merged(self, config):
        """
        Update/Create templates and projects in CCC with fields provided in Cisco Catalyst Center.
        Export the tempaltes and projects.
        Import the templates and projects.
        Deploy the template to the devices based on device specific details or by fetching the device
        details from site using other filtering parameters like device tag, device family, device role.
        Check using check_return_status().

        Parameters:
            config (dict) - Playbook details containing template information.

        Returns:
            self
        """

        project_details = config.get("projects")
        if project_details:
            if len(self.have.get("projects")) == len(project_details):
                project_unmatch = any(
                    not project.get("project_status") and not project.get("new_name")
                    for project in self.have.get("projects")
                )
                if not project_unmatch:
                    self.msg = "No changes required, project(s) already exist"
                    self.log(self.msg, "INFO")
                    self.set_operation_result(
                        "success", False, self.msg, "INFO"
                    ).check_return_status()
                    return self
            self.apply_project_config(project_details).check_return_status()
            return self

        configuration_templates = config.get("configuration_templates")
        if configuration_templates:
            self.update_configuration_templates(
                config, configuration_templates
            ).check_return_status()
            self.update_template_projects_message().check_return_status()

        _import = config.get("import")
        if _import:
            self.handle_import(_import).check_return_status()

        export = config.get("export")
        if export:
            self.log("Found export configuration: {0}".format(export), "DEBUG")
            self.handle_export(export).check_return_status()

        deploy_temp_details = config.get("deploy_template")
        if deploy_temp_details:
            template_name = deploy_temp_details.get("template_name")
            device_details = deploy_temp_details.get("device_details")
            site_specific_details = deploy_temp_details.get("site_provisioning_details")
            self.log(
                "Deploy template details found for template '{0}'".format(
                    template_name
                ),
                "DEBUG",
            )
            self.log("Device specific details: {0}".format(device_details), "DEBUG")
            self.log(
                "Site associated provisioning details: {0}".format(
                    site_specific_details
                ),
                "DEBUG",
            )

            if device_details:
                self.log(
                    "Attempting to retrieve device IPs based on priority from device specific details.",
                    "DEBUG",
                )
                device_ips = self.get_device_ips_from_config_priority(device_details)
                if not device_ips:
                    self.msg = (
                        "No matching device management IP addresses found for the "
                        "deployment of template '{0}'."
                    ).format(template_name)
                    self.set_operation_result("failed", False, self.msg, "ERROR")
                    return self

                self.log(
                    "Successfully retrieved device IPs for template '{0}': '{1}'".format(
                        template_name, device_ips
                    ),
                    "INFO",
                )
                device_id_dict = self.get_device_ids_from_device_ips(device_ips)
                device_ids = self.get_list_from_dict_values(device_id_dict)

                device_missing_msg = (
                    "There are no device id found for the device(s) '{0}' in the "
                    "Cisco Catalyst Center so cannot deploy the given template '{1}'."
                ).format(device_ips, template_name)
            elif site_specific_details:
                device_ids, site_name_list = [], []

                for site in site_specific_details:
                    site_name = site.get("site_name")
                    site_exists, site_id = self.get_site_id(site_name)
                    self.log(
                        "Checking if the site '{0}' exists in Cisco Catalyst Center.".format(
                            site_name
                        ),
                        "DEBUG",
                    )
                    if not site_exists:
                        self.msg = (
                            "To Deploy the template in the devices, given site '{0}' must be "
                            "present in the Cisco Catalyst Center and it's not there currently."
                        ).format(site_name)
                        self.set_operation_result("failed", False, self.msg, "ERROR")
                        return self

                    self.log(
                        "Retrieving devices associated with site ID '{0}' for site '{1}'.".format(
                            site_id, site_name
                        ),
                        "DEBUG",
                    )
                    site_response, site_assign_device_ids = (
                        self.get_device_ids_from_site(site_name, site_id)
                    )
                    site_name_list.append(site_name)

                    if not site_assign_device_ids:
                        device_missing_msg = (
                            "There is no device currently associated with the site '{0}' in the "
                            "Cisco Catalyst Center so cannot deploy the given template '{1}'."
                        ).format(site_name, template_name)
                        self.msg = device_missing_msg
                        self.log(device_missing_msg, "WARNING")
                        continue

                    device_family = site.get("device_family")
                    device_role = site.get("device_role")

                    # Filter devices based on the device family or device role
                    if device_family or device_role:
                        self.log(
                            "Filtering devices based on the device family '{0}' or role '{1}' for the site '{2}'.".format(
                                device_family, device_role, site_name
                            ),
                            "DEBUG",
                        )
                        self.log(
                            "Filtering devices based on the given family/role for the site {0}.".format(
                                site_name
                            ),
                            "INFO",
                        )
                        site_assign_device_ids = self.filter_devices_with_family_role(
                            site_assign_device_ids, device_family, device_role
                        )

                    # Filter devices based on the device tag given to the devices
                    tag_name = site.get("device_tag")
                    tag_device_ids = None
                    if tag_name:
                        self.log(
                            "Filtering out the devices based on the given device tag: '{0}'".format(
                                tag_name
                            ),
                            "INFO",
                        )
                        tag_id = self.get_network_device_tag_id(tag_name)
                        self.log(
                            "Successfully collected the tag id '{0}' for the tag '{1}'".format(
                                tag_id, tag_name
                            ),
                            "INFO",
                        )
                        # Get the device ids associated with the given tag for given site
                        tag_device_ids = self.get_device_ids_from_tag(tag_name, tag_id)
                        self.log(
                            "Successfully collected the device ids {0} associated with the tag {1}".format(
                                tag_device_ids, tag_name
                            ),
                            "INFO",
                        )

                    self.log(
                        "Getting the device ids based on device assoicated with tag or site or both.",
                        "DEBUG",
                    )

                    if tag_device_ids and site_assign_device_ids:
                        self.log(
                            "Determining device IDs from site and tag criteria.",
                            "DEBUG",
                        )
                        common_device_ids = list(
                            set(tag_device_ids).intersection(
                                set(site_assign_device_ids)
                            )
                        )
                        device_ids.extend(common_device_ids)
                    elif site_assign_device_ids and not tag_device_ids:
                        self.log(
                            "Getting the device ids based on devices fetched from site.",
                            "DEBUG",
                        )
                        device_ids.extend(site_assign_device_ids)
                    elif tag_device_ids and not site_assign_device_ids:
                        self.log(
                            "Getting the device ids based on devices fetched with the tag {0}.".format(
                                tag_name
                            ),
                            "DEBUG",
                        )
                        device_ids.extend(tag_device_ids)
                    else:
                        self.log(
                            "There is no matching device ids found for the deployment of template {0} "
                            "for the given site {1}".format(template_name, site_name),
                            "WARNING",
                        )
                        continue

                device_missing_msg = (
                    "There is no device id found for the given site(s) '{0}' in the "
                    "Cisco Catalyst Center so cannot deploy the template '{1}'."
                ).format(site_name_list, template_name)
            else:
                self.msg = (
                    "Unable to provision the template '{0}' as device related details are "
                    "not given in the playboook. Please provide it either via the parameter "
                    "device_details or with site_provisioning_details."
                ).format(self.msg)
                self.set_operation_result(
                    "failed", False, self.msg, "INFO"
                ).check_return_status()

            if not device_ids:
                self.msg = device_missing_msg
                self.set_operation_result("failed", False, self.msg, "INFO")
                return self

            device_ip_dict = self.get_device_ips_from_device_ids(device_ids)
            device_ips = self.get_list_from_dict_values(device_ip_dict)
            self.log(
                "Successfully collect the device ips {0} for the device ids {1}.".format(
                    device_ips, device_ids
                ),
                "INFO",
            )
            deploy_temp_payload = self.create_payload_for_template_deploy(
                deploy_temp_details, device_ids
            )
            self.log(
                "Deployment payload created successfully for template '{0}'.".format(
                    template_name
                ),
                "INFO",
            )
            self.deploy_template_to_devices(
                deploy_temp_payload, template_name, device_ips
            ).check_return_status()
            self.log(
                "Successfully deployed template '{0}'.".format(template_name), "INFO"
            )

        self.msg = "Successfully completed merged state execution"
        self.status = "success"

        return self

    def delete_project_or_template(self, config, is_delete_project=False):
        """
        Call Cisco Catalyst Center API to delete project or template with provided inputs.

        Parameters:
            config (dict) - Playbook details containing template information.
            is_delete_project (bool) - True if we need to delete project, else False.

        Returns:
            self
        """

        if is_delete_project:
            params_key = {"project_id": self.have_project.get("id")}
            deletion_value = "deletes_the_project"
            name = "project: {0}".format(
                config.get("configuration_templates").get("project_name")
            )
        else:
            template_params = self.want.get("template_params")
            params_key = {"template_id": self.have_template.get("id")}
            deletion_value = "deletes_the_template"
            name = "templateName: {0}".format(template_params.get("name"))
        ccc_version = self.get_ccc_version()
        if self.compare_catalystcenter_versions(ccc_version, "2.3.5.3") <= 0:
            self.log(
                "Deleting '{0}' using function '{1}' with parameters: {2} on Catalyst version: {3} (≤ 2.3.5.3)".format(
                    name, deletion_value, params_key, ccc_version
                ),
                "DEBUG",
            )
            response = self.catalystcenter_apply["exec"](
                family="configuration_templates",
                function=deletion_value,
                op_modifies=True,
                params=params_key,
            )
            task_id = response.get("response").get("taskId")
            if not task_id:
                self.msg = "Unable to retrieve the task ID for the task '{0}'.".format(
                    deletion_value
                )
                self.set_operation_result("failed", False, self.msg, "ERROR")
                return self

            sleep_duration = self.params.get("catalystcenter_task_poll_interval")
            while True:
                task_details = self.get_task_details(task_id)
                self.log("Printing task details: {0}".format(task_details), "DEBUG")
                if not task_details:
                    self.msg = "Unable to delete {0} as task details is empty.".format(
                        deletion_value
                    )
                    self.set_operation_result("failed", False, self.msg, "ERROR")
                    return self

                progress = task_details.get("progress")
                self.log(
                    "Task details for the API {0}: {1}".format(
                        deletion_value, progress
                    ),
                    "DEBUG",
                )

                if "deleted" in progress:
                    self.log(
                        "Successfully performed the operation of '{0}' for '{1}'".format(
                            deletion_value, name
                        ),
                        "INFO",
                    )
                    self.msg = "Successfully deleted {0} ".format(name)
                    self.set_operation_result("success", True, self.msg, "INFO")
                    break

                if task_details.get("isError"):
                    failure_reason = task_details.get("failureReason")
                    if failure_reason:
                        self.msg = (
                            "Failed to perform the operation of {0} for {1} because of: {2}"
                        ).format(deletion_value, name, failure_reason)
                    else:
                        self.msg = (
                            "Failed to perform the operation of {0} for {1}.".format(
                                deletion_value, name
                            )
                        )
                    self.set_operation_result("failed", False, self.msg, "ERROR")
                    break

                self.log(
                    "Waiting for {0} seconds before checking the task status again.".format(
                        sleep_duration
                    ),
                    "DEBUG",
                )
                time.sleep(sleep_duration)
        else:
            current_profiles = self.have.get("current_profile", [])
            if (
                current_profiles
                and self.compare_catalystcenter_versions(ccc_version, "3.1.3.0") >= 0
            ):
                template_name = self.want.get("template_params").get("name")
                self.log("Detaching profile from template", "DEBUG")
                detach_status = self.detach_profiles_from_template(
                    template_name, current_profiles
                )
                if detach_status:
                    self.log("Received response from detach profile.", "DEBUG")
                    self.update_template_projects_message().check_return_status()
                    return self

            self.log(
                "Deleting '{0}' using function '{1}' with parameters: '{2}' on Catalyst version: {3} (> 2.3.5.3)".format(
                    name, deletion_value, params_key, ccc_version
                ),
                "DEBUG",
            )

            task_name = deletion_value
            parameters = params_key
            task_id = self.get_taskid_post_api_call(
                "configuration_templates", task_name, parameters
            )

            if not task_id:
                self.msg = "Unable to retrieve the task_id for the task '{0} for the parameters {1}'.".format(
                    task_name, parameters
                )
                self.set_operation_result(
                    "failed", False, self.msg, "ERROR"
                ).check_return_status()
                return self

            success_msg = "Task: {0} is successful for parameters: {1}".format(
                task_name, parameters
            )
            self.get_task_status_from_tasks_by_id(task_id, task_name, success_msg)

        return self

    def detach_profiles_from_template(self, name, current_profiles):
        """
        Detach profiles from a specific template in Cisco Catalyst Center.

        Args:
            name (str): The name of the template.
            current_profiles (list): A list of profile names to detach.

        Returns:
            bool: Returns True if the detachment was successful execution.
        """
        self.log(
            "Detaching profiles from template '{0}': {1}".format(
                name, current_profiles
            ),
            "INFO",
        )

        for profile_index, each_profile in enumerate(current_profiles):
            # Extract profile information once per iteration
            each_profile_name = each_profile.get("profile_name")
            each_profile_id = each_profile.get("profile_id")
            profile_template_name = each_profile.get("template_name")
            profile_status = each_profile.get("profile_status")
            template_id = self.have_template.get("id")

            # Skip profiles not associated with the current template
            if profile_template_name != name:
                self.log(
                    "Skipping profile '{0}' - not associated with template '{1}' (associated with '{2}')".format(
                        each_profile_name, name, profile_template_name
                    ),
                    "DEBUG",
                )
                continue

            self.log(
                "Processing profile '{0}' (index {1}) with status '{2}' for template '{3}'".format(
                    each_profile_name, profile_index, profile_status, name
                ),
                "DEBUG",
            )

            # Case 1: Detach profile from template
            if profile_status == "already assigned":
                self.log(
                    "Detaching profile '{0}' from template '{1}' - profile currently assigned and detach requested".format(
                        each_profile_name, name
                    ),
                    "INFO",
                )

                try:
                    template_status = self.detach_networkprofile_cli_template(
                        each_profile_name, each_profile_id, name, template_id
                    )
                    self.log(
                        "Received response from profile detachment API for profile '{0}': {1}".format(
                            each_profile_name, template_status
                        ),
                        "DEBUG",
                    )

                    if template_status and template_status.get("progress"):
                        success_msg = "Profile '{0}' successfully detached from template '{1}'".format(
                            each_profile_name, name
                        )
                        self.log(success_msg, "INFO")
                        self.profile_detached.append(each_profile_name)
                    else:
                        error_msg = "Failed to detach profile '{0}' from template '{1}' - API response indicates failure".format(
                            each_profile_name, name
                        )
                        self.log(error_msg, "ERROR")
                        self.profile_not_detached.append(each_profile_name)

                except Exception as e:
                    error_msg = "Exception occurred while detaching profile '{0}' from template '{1}': {2}".format(
                        each_profile_name, name, str(e)
                    )
                    self.log(error_msg, "ERROR")
                    self.profile_not_detached.append(each_profile_name)

            # Case 2: Profile already detached (idempotent case)
            elif profile_status == "Not Assigned":
                self.log(
                    "Profile '{0}' already detached from template '{1}' - no action required".format(
                        each_profile_name, name
                    ),
                    "INFO",
                )
                self.profile_already_detached.append(each_profile_name)

            # Case 3: Unexpected scenario
            else:
                self.log(
                    "Unexpected scenario for profile '{0}' on template '{1}': status='{2}'".format(
                        each_profile_name, name, profile_status
                    ),
                    "WARNING",
                )

        # Log summary of operations
        total_detached = len(getattr(self, "profile_detached", []))
        total_detachment_failures = len(getattr(self, "profile_not_detached", []))
        total_already_detached = len(getattr(self, "profile_already_detached", []))

        self.log("Profile operation summary for template '{0}':".format(name), "INFO")
        self.log(
            "  - Profiles detached: {0} {1}".format(
                total_detached, getattr(self, "profile_detached", [])
            ),
            "INFO",
        )
        self.log(
            "  - Detachment failures: {0} {1}".format(
                total_detachment_failures, getattr(self, "profile_not_detached", [])
            ),
            "INFO",
        )
        self.log(
            "  - Already detached: {0} {1}".format(
                total_already_detached, getattr(self, "profile_already_detached", [])
            ),
            "INFO",
        )

        self.log(
            "Completed profile detachment processing for template '{0}'".format(name),
            "INFO",
        )

        return True

    def get_diff_deleted(self, config):
        """
        Delete projects or templates in Cisco Catalyst Center with fields provided in playbook.

        Parameters:
            config (dict) - Playbook details containing template information.

        Returns:
            self
        """

        configuration_templates = config.get("configuration_templates")
        if configuration_templates:
            is_project_found = self.have_project.get("project_found")
            projectName = config.get("configuration_templates").get("project_name")

            if not is_project_found:
                self.msg = "Project {0} is not found".format(projectName)
                self.status = "failed"
                return self

            is_template_found = self.have_template.get("template_found")
            template_params = self.want.get("template_params")
            templateName = config.get("configuration_templates").get("template_name")
            if template_params.get("name"):
                if is_template_found:
                    self.delete_project_or_template(config)
                else:
                    self.result["response"][0].get("configurationTemplate").update(
                        {
                            "msg": "Template with template_name '{0}' already deleted".format(
                                templateName
                            )
                        }
                    )
                    self.msg = "Invalid template {0} under project".format(templateName)
                    self.status = "success"
                    return self
            else:
                self.log(
                    "Template name is empty, deleting the project '{0}' and "
                    "associated templates".format(
                        config.get("configuration_templates").get("project_name")
                    ),
                    "INFO",
                )
                is_project_deletable = self.have_project.get("isDeletable")
                if is_project_deletable:
                    self.delete_project_or_template(config, is_delete_project=True)
                else:
                    self.msg = "Project is not deletable"
                    self.status = "failed"
                    return self
            self.log(
                "Successfully completed the delete operation for the template {0}".format(
                    templateName
                ),
                "DEBUG",
            )

        deploy_temp_details = config.get("deploy_template")
        if deploy_temp_details:
            template_name = deploy_temp_details.get("template_name")
            self.msg = (
                "Deleting or removing the device configuration using deployment of template is not supported "
                "for the template {0} in the Cisco Catalyst Center."
            ).format(template_name)
            self.set_operation_result(
                "failed", False, self.msg, "ERROR"
            ).check_return_status()

        project_details = config.get("projects")
        if project_details and isinstance(project_details, list):
            self.processed_project = []
            if not self.have.get("projects"):
                self.log("No existing projects found. Nothing to delete.", "INFO")
                return self

            for each_project in project_details:
                project_name = each_project.get("name")
                if not project_name:
                    self.log("Skipping project with missing 'name' field.", "WARNING")
                    continue

                if self.delete_project(project_name):
                    self.processed_project.append(project_name)
                    self.log(
                        "Successfully deleted project: {0}".format(project_name), "INFO"
                    )

        return self

    def verify_diff_deleted(self, config):
        """
        Validating the Cisco Catalyst Center configuration with the playbook details
        when state is deleted (delete).

        Parameters:
            config (dict) - Playbook details containing Global Pool,
            Reserved Pool, and Network Management configuration.

        Returns:
            self
        """

        if config.get("configuration_templates") is not None:
            self.log("Current State (have): {0}".format(self.have), "INFO")
            self.log("Desired State (want): {0}".format(self.want), "INFO")
            template_list = self.catalystcenter_apply["exec"](
                family="configuration_templates",
                function="gets_the_templates_available",
                op_modifies=True,
                params={
                    "projectNames": config.get("configuration_templates").get(
                        "project_name"
                    )
                },
            )
            self.log(
                "Received response from 'gets_the_templates_available' for 'project_name': '{0}' is {1}".format(
                    config.get("configuration_templates").get("project_name"),
                    template_list,
                ),
                "DEBUG",
            )
            if template_list and isinstance(template_list, list):
                templateName = config.get("configuration_templates").get(
                    "template_name"
                )
                template_info = get_dict_result(template_list, "name", templateName)
                if template_info:
                    self.log(
                        "Configuration Template config is not applied to the Cisco Catalyst Center.",
                        "WARNING",
                    )
                    return self

                self.log(
                    "Successfully validated the absence of Template {0} in the Cisco Catalyst Center.".format(
                        templateName
                    ),
                    "INFO",
                )

        if config.get("projects"):
            if not self.processed_project:
                self.msg = "No changes required, project(s) are already deleted"
                self.log(self.msg, "INFO")
                self.set_operation_result(
                    "success", False, self.msg, "INFO"
                ).check_return_status()
                return self

            self.get_have(config)
            self.log("Current State (have): {0}".format(self.have), "INFO")
            self.log("Desired State (want): {0}".format(self.want), "INFO")
            if not self.have.get("projects"):
                self.msg = (
                    "Project(s) are deleted and verified successfully. {0}".format(
                        self.processed_project
                    )
                )
                self.log(self.msg, "INFO")
                self.set_operation_result(
                    "success", True, self.msg, "INFO", config.get("projects")
                ).check_return_status()
                return self

            self.msg = "Unable to delete the following project(s): {0}".format(
                [project.get("name") for project in self.have.get("projects", [])]
            )
            self.log(self.msg, "ERROR")
            self.set_operation_result(
                "failed", False, self.msg, "INFO", self.have.get("projects")
            ).check_return_status()
        return self


def main():
    """main entry point for module execution"""

    element_spec = {
        "catalystcenter_host": {
            "required": True,
            "type": "str",
            "aliases": ["dnac_host"],
        },
        "catalystcenter_port": {
            "type": "str",
            "default": "443",
            "aliases": ["dnac_port", "catalystcenter_api_port"],
        },
        "catalystcenter_username": {
            "type": "str",
            "default": "admin",
            "aliases": ["dnac_username", "user"],
        },
        "catalystcenter_password": {
            "type": "str",
            "no_log": True,
            "aliases": ["dnac_password"],
        },
        "catalystcenter_verify": {
            "type": "bool",
            "default": "True",
            "aliases": ["dnac_verify"],
        },
        "catalystcenter_version": {
            "type": "str",
            "default": "2.3.7.6",
            "aliases": ["dnac_version"],
        },
        "catalystcenter_debug": {
            "type": "bool",
            "default": False,
            "aliases": ["dnac_debug"],
        },
        "catalystcenter_log": {
            "type": "bool",
            "default": False,
            "aliases": ["dnac_log"],
        },
        "catalystcenter_log_level": {
            "type": "str",
            "default": "WARNING",
            "aliases": ["dnac_log_level"],
        },
        "catalystcenter_log_file_path": {
            "type": "str",
            "default": "catalystcenter.log",
            "aliases": ["dnac_log_file_path"],
        },
        "catalystcenter_log_append": {
            "type": "bool",
            "default": True,
            "aliases": ["dnac_log_append"],
        },
        "validate_response_schema": {"type": "bool", "default": True},
        "config_verify": {"type": "bool", "default": False},
        "catalystcenter_api_task_timeout": {
            "type": "int",
            "default": 1200,
            "aliases": ["dnac_api_task_timeout"],
        },
        "catalystcenter_task_poll_interval": {
            "type": "int",
            "default": 2,
            "aliases": ["dnac_task_poll_interval"],
        },
        "config": {"required": True, "type": "list", "elements": "dict"},
        "state": {"default": "merged", "choices": ["merged", "deleted"]},
    }
    module = AnsibleModule(argument_spec=element_spec, supports_check_mode=False)
    ccc_template = Template(module)

    ccc_version = ccc_template.get_ccc_version()
    if ccc_template.compare_catalystcenter_versions(ccc_version, "2.3.7.6") < 0:
        ccc_template.msg = (
            "Template module is not supported in Cisco Catalyst Center version '{0}'. Supported versions start "
            "from '2.3.7.6' onwards.".format(ccc_version)
        )
        ccc_template.set_operation_result(
            "failed", False, ccc_template.msg, "ERROR"
        ).check_return_status()

    ccc_template.validate_input().check_return_status()
    state = ccc_template.params.get("state")
    config_verify = ccc_template.params.get("config_verify")
    if state not in ccc_template.supported_states:
        ccc_template.status = "invalid"
        ccc_template.msg = "State {0} is invalid".format(state)
        ccc_template.check_return_status()

    for config in ccc_template.validated_config:
        ccc_template.reset_values()
        ccc_template.get_have(config).check_return_status()
        ccc_template.get_want(config).check_return_status()
        ccc_template.get_diff_state_apply[state](config).check_return_status()
        if config_verify:
            ccc_template.verify_diff_state_apply[state](config).check_return_status()

    module.exit_json(**ccc_template.result)


if __name__ == "__main__":
    main()
