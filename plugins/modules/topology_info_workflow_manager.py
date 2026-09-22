#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Gather and optionally export Cisco Catalyst Center topology information."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: topology_info_workflow_manager
short_description: Gather topology information from Cisco Catalyst Center
description:
  - Gathers one or more topology information categories from Cisco Catalyst Center in a single task.
  - Supports site, Layer 2, Layer 3, physical, overall network health, and loop-affected VLAN information.
  - Supports retrieving Layer 2 topology for multiple VLANs and Layer 3 topology for multiple topology types.
  - Always returns the gathered information in the module response.
  - Optionally writes each gathered topology snapshot to a JSON or YAML file when C(output_file_info) is provided.
  - Does not create a file when C(output_file_info) is omitted.
  - This module is read-only with respect to Cisco Catalyst Center and always reports C(changed=false).
version_added: "6.52.0"
extends_documentation_fragment:
  - cisco.catalystcenter.workflow_manager_params
author:
  - Cisco Systems (@Cisco)
options:
  state:
    description: Operation performed by the workflow manager.
    type: str
    choices: [gathered]
    default: gathered
  config:
    description:
      - List of topology information collection requests.
      - Each entry produces one topology snapshot in the returned C(response) list.
    type: list
    elements: dict
    required: true
    suboptions:
      requested_info:
        description:
          - Topology information categories to retrieve.
          - C(layer_2_topology) requires C(vlan_ids).
          - C(layer_3_topology) requires C(topology_types).
          - C(vlan_details) returns VLAN names involved in loops detected by Spanning Tree Protocol.
        type: list
        elements: str
        required: true
        choices:
          - site_topology
          - layer_2_topology
          - layer_3_topology
          - physical_topology
          - network_health
          - vlan_details
      vlan_ids:
        description:
          - VLAN names for which Layer 2 topology is retrieved.
          - Examples include C(Vlan1) and C(Vlan23).
        type: list
        elements: str
      topology_types:
        description:
          - Layer 3 topology or routing protocol types to retrieve.
          - Examples include C(OSPF) and C(ISIS).
        type: list
        elements: str
      node_type:
        description: Optional node type used to filter the physical topology query.
        type: str
      timestamp:
        description: Optional UTC timestamp in milliseconds used for the network health query.
        type: float
      headers:
        description: Additional headers supplied to topology API requests in this config entry.
        type: dict
      output_file_info:
        description:
          - Optional file export settings for this topology snapshot.
          - When omitted, no file is created and the data is returned only in the module response.
        type: dict
        suboptions:
          file_path:
            description:
              - Absolute base path for the output file.
              - The extension selected by C(file_format) is appended when it is not already present.
              - When omitted, file output is skipped and the gathered data is returned in the module response.
            type: str
          file_format:
            description: Serialization format for the output file.
            type: str
            choices: [json, yaml]
            default: yaml
          file_mode:
            description:
              - C(w) overwrites the file with the current snapshot.
              - C(a) appends the current snapshot to existing snapshot data.
            type: str
            choices: [w, a]
            default: w
          timestamp:
            description: Include the UTC collection timestamp with the exported snapshot.
            type: bool
            default: false
requirements:
  - catalystcentersdk >= 3.1.6.0.2
  - python >= 3.12
notes:
  - The module supports check mode because all Cisco Catalyst Center API operations are GET requests.
  - File output is skipped when the module runs in check mode.
  - File output occurs on the host on which the module executes, normally localhost for Catalyst Center workflow playbooks.
  - The complete SDK response envelope is preserved for every requested information category.
  - SDK methods used are
    topology.Topology.get_site_topology,
    topology.Topology.get_topology_details,
    topology.Topology.get_l3_topology_details,
    topology.Topology.get_physical_topology,
    topology.Topology.get_overall_network_health,
    topology.Topology.get_vlan_details.
"""

EXAMPLES = r"""
---
- name: Gather topology information without creating a file
  cisco.catalystcenter.topology_info_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    state: gathered
    config:
      - requested_info:
          - site_topology
          - physical_topology
          - network_health
          - vlan_details
        node_type: device
  register: topology_result

- name: Gather Layer 2 and Layer 3 topology and export it
  cisco.catalystcenter.topology_info_workflow_manager:
    catalystcenter_host: "{{ catalystcenter_host }}"
    catalystcenter_username: "{{ catalystcenter_username }}"
    catalystcenter_password: "{{ catalystcenter_password }}"
    catalystcenter_verify: "{{ catalystcenter_verify }}"
    catalystcenter_version: "{{ catalystcenter_version }}"
    state: gathered
    config:
      - requested_info:
          - layer_2_topology
          - layer_3_topology
        vlan_ids:
          - Vlan10
          - Vlan20
        topology_types:
          - OSPF
          - ISIS
        output_file_info:
          file_path: /var/tmp/catalystcenter_topology
          file_format: json
          file_mode: w
          timestamp: true
  register: topology_result
"""

RETURN = r"""
response:
  description:
    - Topology snapshots collected for each entry in C(config).
    - Only requested information-category keys are present in each snapshot.
  returned: always
  type: list
  elements: dict
  sample:
    - site_topology:
        response:
          sites:
            - id: site-1
              name: Global
        version: '1.0'
      layer_2_topology:
        Vlan10:
          response:
            id: topology-1
            nodes: []
            links: []
          version: '1.0'
      layer_3_topology:
        OSPF:
          response:
            id: topology-2
            nodes: []
            links: []
          version: '1.0'
      physical_topology:
        response:
          id: topology-3
          nodes: []
          links: []
        version: '1.0'
      network_health:
        response: []
        version: '1.0'
      vlan_details:
        response:
          - Vlan10
        version: '1.0'
output_files:
  description: Absolute paths of files written by the workflow.
  returned: always
  type: list
  elements: str
  sample:
    - /var/tmp/catalystcenter_topology.json
"""


import json
import os
import tempfile
from datetime import datetime, timezone

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.cisco.catalystcenter.plugins.module_utils.catalystcenter import (
    CatalystCenterBase,
)

try:
    import yaml
except ImportError:
    yaml = None


class TopologyInfo(CatalystCenterBase):
    """Gather and aggregate topology information from Catalyst Center."""

    ALLOWED_INFO = {
        "site_topology",
        "layer_2_topology",
        "layer_3_topology",
        "physical_topology",
        "network_health",
        "vlan_details",
    }
    ALLOWED_CONFIG_KEYS = {
        "requested_info",
        "vlan_ids",
        "topology_types",
        "node_type",
        "timestamp",
        "headers",
        "output_file_info",
    }
    ALLOWED_OUTPUT_KEYS = {
        "file_path",
        "file_format",
        "file_mode",
        "timestamp",
    }

    def __init__(self, module):
        super().__init__(module)
        self.supported_states = ["gathered"]
        self.topology_responses = []
        self.output_files = []
        self.result["output_files"] = self.output_files

    def validate_input(self):
        """Validate and normalize topology collection requests."""

        if not isinstance(self.config, list) or not self.config:
            return self._validation_failure("'config' must be a non-empty list.")

        validated_config = []
        for index, config_entry in enumerate(self.config):
            entry_label = "config[{0}]".format(index)
            if not isinstance(config_entry, dict):
                return self._validation_failure(
                    "'{0}' must be a dictionary.".format(entry_label)
                )

            unknown_keys = sorted(
                set(config_entry.keys()) - self.ALLOWED_CONFIG_KEYS
            )
            if unknown_keys:
                return self._validation_failure(
                    "Invalid key(s) in '{0}': {1}. Allowed keys are: {2}.".format(
                        entry_label,
                        ", ".join(unknown_keys),
                        ", ".join(sorted(self.ALLOWED_CONFIG_KEYS)),
                    )
                )

            requested_info = config_entry.get("requested_info")
            if not isinstance(requested_info, list) or not requested_info:
                return self._validation_failure(
                    "'{0}.requested_info' must be a non-empty list.".format(
                        entry_label
                    )
                )

            if any(
                not isinstance(info_name, str) or not info_name.strip()
                for info_name in requested_info
            ):
                return self._validation_failure(
                    "Every value in '{0}.requested_info' must be a non-empty string.".format(
                        entry_label
                    )
                )

            requested_info = self._deduplicate(requested_info)
            invalid_info = sorted(set(requested_info) - self.ALLOWED_INFO)
            if invalid_info:
                return self._validation_failure(
                    "Invalid requested_info value(s) in '{0}': {1}. Allowed values are: {2}.".format(
                        entry_label,
                        ", ".join(invalid_info),
                        ", ".join(sorted(self.ALLOWED_INFO)),
                    )
                )

            normalized_entry = dict(config_entry)
            normalized_entry["requested_info"] = requested_info

            validation_error = self._validate_selectors(
                normalized_entry, entry_label
            )
            if validation_error:
                return self._validation_failure(validation_error)

            validation_error = self._validate_optional_query_fields(
                normalized_entry, entry_label
            )
            if validation_error:
                return self._validation_failure(validation_error)

            validation_error = self._validate_output_file_info(
                normalized_entry.get("output_file_info"), entry_label
            )
            if validation_error:
                return self._validation_failure(validation_error)

            if normalized_entry.get("output_file_info") is not None:
                output_file_info = dict(normalized_entry["output_file_info"])
                output_file_info.setdefault("file_format", "yaml")
                output_file_info.setdefault("file_mode", "w")
                output_file_info.setdefault("timestamp", False)
                normalized_entry["output_file_info"] = output_file_info

            validated_config.append(normalized_entry)

        self.validated_config = validated_config
        self.msg = "Topology information workflow input validation succeeded."
        self.status = "success"
        return self

    def _validate_selectors(self, config_entry, entry_label):
        """Validate selectors required by Layer 2 and Layer 3 queries."""

        requested_info = config_entry["requested_info"]

        vlan_ids = config_entry.get("vlan_ids")
        if "layer_2_topology" in requested_info:
            error = self._validate_non_empty_string_list(
                vlan_ids, "{0}.vlan_ids".format(entry_label)
            )
            if error:
                return (
                    "'vlan_ids' is required when 'layer_2_topology' is requested. "
                    + error
                )
            config_entry["vlan_ids"] = self._deduplicate(vlan_ids)
        elif vlan_ids is not None:
            error = self._validate_non_empty_string_list(
                vlan_ids, "{0}.vlan_ids".format(entry_label)
            )
            if error:
                return error
            config_entry["vlan_ids"] = self._deduplicate(vlan_ids)

        topology_types = config_entry.get("topology_types")
        if "layer_3_topology" in requested_info:
            error = self._validate_non_empty_string_list(
                topology_types, "{0}.topology_types".format(entry_label)
            )
            if error:
                return (
                    "'topology_types' is required when 'layer_3_topology' is requested. "
                    + error
                )
            config_entry["topology_types"] = self._deduplicate(topology_types)
        elif topology_types is not None:
            error = self._validate_non_empty_string_list(
                topology_types, "{0}.topology_types".format(entry_label)
            )
            if error:
                return error
            config_entry["topology_types"] = self._deduplicate(topology_types)

        return None

    def _validate_optional_query_fields(self, config_entry, entry_label):
        """Validate optional physical, health, and header parameters."""

        node_type = config_entry.get("node_type")
        if node_type is not None and (
            not isinstance(node_type, str) or not node_type.strip()
        ):
            return "'{0}.node_type' must be a non-empty string.".format(
                entry_label
            )

        timestamp = config_entry.get("timestamp")
        if timestamp is not None:
            if isinstance(timestamp, bool) or not isinstance(
                timestamp, (int, float)
            ):
                return "'{0}.timestamp' must be a number.".format(entry_label)
            if timestamp < 0:
                return "'{0}.timestamp' must be greater than or equal to zero.".format(
                    entry_label
                )

        headers = config_entry.get("headers")
        if headers is not None and not isinstance(headers, dict):
            return "'{0}.headers' must be a dictionary.".format(entry_label)

        return None

    def _validate_output_file_info(self, output_file_info, entry_label):
        """Validate optional output file configuration."""

        if output_file_info is None:
            return None
        if not isinstance(output_file_info, dict):
            return "'{0}.output_file_info' must be a dictionary.".format(
                entry_label
            )

        unknown_keys = sorted(
            set(output_file_info.keys()) - self.ALLOWED_OUTPUT_KEYS
        )
        if unknown_keys:
            return (
                "Invalid key(s) in '{0}.output_file_info': {1}. Allowed keys are: {2}.".format(
                    entry_label,
                    ", ".join(unknown_keys),
                    ", ".join(sorted(self.ALLOWED_OUTPUT_KEYS)),
                )
            )

        file_path = output_file_info.get("file_path")
        if not file_path:
            return None
        if not isinstance(file_path, str):
            return "'{0}.output_file_info.file_path' must be a string.".format(
                entry_label
            )
        if not os.path.isabs(file_path):
            return "'{0}.output_file_info.file_path' must be an absolute path.".format(
                entry_label
            )

        file_format = output_file_info.get("file_format", "yaml")
        if not isinstance(file_format, str) or file_format.lower() not in {
            "json",
            "yaml",
        }:
            return "'{0}.output_file_info.file_format' must be one of: json, yaml.".format(
                entry_label
            )

        file_mode = output_file_info.get("file_mode", "w")
        if not isinstance(file_mode, str) or file_mode not in {"w", "a"}:
            return "'{0}.output_file_info.file_mode' must be one of: w, a.".format(
                entry_label
            )

        include_timestamp = output_file_info.get("timestamp", False)
        if not isinstance(include_timestamp, bool):
            return "'{0}.output_file_info.timestamp' must be a boolean.".format(
                entry_label
            )

        return None

    def _validation_failure(self, message):
        """Record a validation failure and return this manager."""

        self.msg = message
        self.set_operation_result(
            "failed",
            False,
            self.msg,
            "ERROR",
            self.topology_responses,
        )
        return self

    @staticmethod
    def _validate_non_empty_string_list(value, field_name):
        """Return a validation message for an invalid string list."""

        if not isinstance(value, list) or not value:
            return "'{0}' must be a non-empty list.".format(field_name)
        if any(not isinstance(item, str) or not item.strip() for item in value):
            return "Every value in '{0}' must be a non-empty string.".format(
                field_name
            )
        return None

    @staticmethod
    def _deduplicate(values):
        """Deduplicate hashable values while retaining the input order."""

        return list(dict.fromkeys(values))

    def get_want(self, config):
        """Store the validated query request for state dispatch consistency."""

        self.want = dict(config)
        return self

    def get_diff_gathered(self, config):
        """Gather all requested topology information for one config entry."""

        requested_info = config["requested_info"]
        headers = config.get("headers")
        snapshot = {}

        if "site_topology" in requested_info:
            snapshot["site_topology"] = self._execute_topology_query(
                "get_site_topology", self._optional_params(headers=headers)
            )

        if "layer_2_topology" in requested_info:
            layer_2_topologies = {}
            for vlan_id in config["vlan_ids"]:
                layer_2_topologies[vlan_id] = self._execute_topology_query(
                    "get_topology_details",
                    self._optional_params(vlan_id=vlan_id, headers=headers),
                )
            snapshot["layer_2_topology"] = layer_2_topologies

        if "layer_3_topology" in requested_info:
            layer_3_topologies = {}
            for topology_type in config["topology_types"]:
                layer_3_topologies[topology_type] = self._execute_topology_query(
                    "get_l3_topology_details",
                    self._optional_params(
                        topology_type=topology_type, headers=headers
                    ),
                )
            snapshot["layer_3_topology"] = layer_3_topologies

        if "physical_topology" in requested_info:
            snapshot["physical_topology"] = self._execute_topology_query(
                "get_physical_topology",
                self._optional_params(
                    node_type=config.get("node_type"), headers=headers
                ),
            )

        if "network_health" in requested_info:
            snapshot["network_health"] = self._execute_topology_query(
                "get_overall_network_health",
                self._optional_params(
                    timestamp=config.get("timestamp"), headers=headers
                ),
            )

        if "vlan_details" in requested_info:
            snapshot["vlan_details"] = self._execute_topology_query(
                "get_vlan_details", self._optional_params(headers=headers)
            )

        self.topology_responses.append(snapshot)

        output_file_info = config.get("output_file_info")
        if output_file_info and output_file_info.get("file_path"):
            if self.module.check_mode:
                self.log(
                    "Skipping topology file output because check mode is enabled.",
                    "INFO",
                )
            else:
                output_path = self.write_topology_info_to_file(
                    snapshot, output_file_info
                )
                self.output_files.append(output_path)
        elif output_file_info:
            self.log(
                "No file_path was supplied in output_file_info; skipping file output.",
                "WARNING",
            )

        self.msg = "Successfully gathered topology information."
        self.set_operation_result(
            "success",
            False,
            self.msg,
            "INFO",
            self.topology_responses,
        )
        self.result["output_files"] = self.output_files
        return self

    def _execute_topology_query(self, function, params):
        """Execute a read-only topology SDK operation and preserve its response."""

        try:
            return self.catalystcenter._exec(
                family="topology",
                function=function,
                params=params or None,
                op_modifies=False,
            )
        except Exception as exception:
            self.msg = (
                "An error occurred while executing topology API function "
                "'{0}': {1}".format(function, exception)
            )
            self.set_operation_result(
                "failed",
                False,
                self.msg,
                "ERROR",
                self.topology_responses,
            ).check_return_status()

    @staticmethod
    def _optional_params(**params):
        """Drop only None values while preserving valid falsey values such as 0."""

        return {key: value for key, value in params.items() if value is not None}

    def write_topology_info_to_file(self, snapshot, output_file_info):
        """Serialize one topology snapshot to a JSON or YAML file atomically."""

        file_format = output_file_info.get("file_format", "yaml").lower()
        file_mode = output_file_info.get("file_mode", "w")
        include_timestamp = output_file_info.get("timestamp", False)
        output_path = self._output_path(
            output_file_info["file_path"], file_format
        )
        output_directory = os.path.dirname(output_path)

        try:
            os.makedirs(output_directory, exist_ok=True)
            record = snapshot
            if include_timestamp:
                record = {
                    "collected_at": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "topology": snapshot,
                }

            data_to_write = record
            if file_mode == "a":
                existing_data = []
                if os.path.exists(output_path):
                    existing_data = self._read_output_file(
                        output_path, file_format
                    )
                    if existing_data is None:
                        existing_data = []
                    elif not isinstance(existing_data, list):
                        existing_data = [existing_data]
                data_to_write = existing_data + [record]

            self._atomic_write(output_path, file_format, data_to_write)
            self.log(
                "Successfully wrote topology information to '{0}'.".format(
                    output_path
                ),
                "INFO",
            )
            return output_path
        except Exception as exception:
            self.msg = "Failed to write topology information to '{0}': {1}".format(
                output_path, exception
            )
            self.set_operation_result(
                "failed",
                False,
                self.msg,
                "ERROR",
                self.topology_responses,
            ).check_return_status()

    @staticmethod
    def _output_path(file_path, file_format):
        """Append the selected extension unless the path already has it."""

        extension = ".{0}".format(file_format)
        if file_path.lower().endswith(extension):
            return file_path
        return file_path + extension

    @staticmethod
    def _read_output_file(file_path, file_format):
        """Read an existing JSON or YAML output file."""

        with open(file_path, "r", encoding="utf-8") as output_file:
            if file_format == "json":
                return json.load(output_file)
            if yaml is None:
                raise RuntimeError(
                    "PyYAML is required when file_format is 'yaml'."
                )
            return yaml.safe_load(output_file)

    @staticmethod
    def _atomic_write(file_path, file_format, data):
        """Write serialized data through a temporary file and replace atomically."""

        if file_format == "yaml" and yaml is None:
            raise RuntimeError("PyYAML is required when file_format is 'yaml'.")

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=os.path.dirname(file_path),
                prefix=".topology_info_",
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
                if file_format == "json":
                    json.dump(data, temporary_file, indent=2)
                    temporary_file.write("\n")
                else:
                    yaml.safe_dump(
                        data,
                        temporary_file,
                        default_flow_style=False,
                        sort_keys=False,
                    )

            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, file_path)
        except Exception:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise


def main():
    """Module entry point."""

    element_spec = {
        "catalystcenter_host": {"required": True, "type": "str"},
        "catalystcenter_port": {"type": "str", "default": "443"},
        "catalystcenter_username": {"type": "str", "default": "admin"},
        "catalystcenter_password": {"type": "str", "no_log": True},
        "catalystcenter_verify": {"type": "bool", "default": True},
        "catalystcenter_version": {"type": "str", "default": "2.3.7.6"},
        "catalystcenter_debug": {"type": "bool", "default": False},
        "catalystcenter_log": {"type": "bool", "default": False},
        "catalystcenter_log_level": {"type": "str", "default": "WARNING"},
        "catalystcenter_log_file_path": {
            "type": "str",
            "default": "catalystcenter.log",
        },
        "catalystcenter_log_append": {"type": "bool", "default": True},
        "validate_response_schema": {"type": "bool", "default": True},
        "catalystcenter_api_task_timeout": {"type": "int", "default": 1200},
        "catalystcenter_task_poll_interval": {"type": "int", "default": 2},
        "config": {"required": True, "type": "list", "elements": "dict"},
        "state": {"default": "gathered", "choices": ["gathered"]},
    }

    module = AnsibleModule(argument_spec=element_spec, supports_check_mode=True)
    topology_info = TopologyInfo(module)
    state = topology_info.params.get("state")

    if state not in topology_info.supported_states:
        topology_info.msg = "State '{0}' is invalid.".format(state)
        topology_info.set_operation_result(
            "invalid",
            False,
            topology_info.msg,
            "ERROR",
            topology_info.topology_responses,
        ).check_return_status()

    topology_info.validate_input().check_return_status()

    for config in topology_info.validated_config:
        topology_info.reset_values()
        topology_info.get_want(config).check_return_status()
        topology_info.get_diff_state_apply[state](config).check_return_status()

    module.exit_json(**topology_info.result)


if __name__ == "__main__":
    main()
