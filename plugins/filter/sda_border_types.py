# Copyright (c) 2026 Cisco and/or its affiliates.
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Expose shared SDA capability handling to refresh task files."""

from ansible.errors import AnsibleFilterError
from ansible_collections.cisco.catalystcenter.plugins.module_utils.sda_border_capabilities import (
    capability_config,
    required_border_types,
)


def border_types(value):
    try:
        return required_border_types(value)
    except (TypeError, ValueError) as exc:
        raise AnsibleFilterError(str(exc)) from exc


def with_border_types(value, source=None):
    try:
        return capability_config(value, source)
    except (TypeError, ValueError) as exc:
        raise AnsibleFilterError(str(exc)) from exc


class FilterModule:
    def filters(self):
        return {"sda_border_types": border_types, "sda_border_capability_config": with_border_types}
