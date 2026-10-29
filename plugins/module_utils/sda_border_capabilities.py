# Copyright (c) 2026 Cisco and/or its affiliates.
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared border capability validation for device payloads and refresh recovery."""

from copy import deepcopy


def normalize_border_types(value):
    """Require an explicit nonempty set of supported border capabilities."""
    if not isinstance(value, list) or not value:
        raise ValueError("border_types must be a nonempty list of LAYER_2 and/or LAYER_3")
    if any(not isinstance(item, str) or item not in ("LAYER_2", "LAYER_3") for item in value):
        raise ValueError("border_types accepts only LAYER_2 and LAYER_3")
    if len(set(value)) != len(value):
        raise ValueError("border_types must not contain duplicates")
    return sorted(value)


def required_border_types(device_config):
    """Read explicit capabilities, deriving legacy manifest intent without mutation."""
    if not isinstance(device_config, dict):
        raise ValueError("A device configuration mapping is required")
    if "BORDER_NODE" not in device_config.get("device_roles", []):
        return []
    settings = device_config.get("borders_settings")
    if not isinstance(settings, dict):
        raise ValueError("A border device requires borders_settings")
    inferred = set()
    if settings.get("layer2_handoff"):
        inferred.add("LAYER_2")
    if (settings.get("layer3_settings") or settings.get("layer3_handoff_ip_transit")
            or settings.get("layer3_handoff_sda_transit")):
        inferred.add("LAYER_3")
    if "border_types" in settings:
        declared = normalize_border_types(settings["border_types"])
        if not inferred.issubset(declared):
            raise ValueError("border_types does not include all configured border settings and handoffs")
        return declared
    if not inferred:
        raise ValueError("Legacy border capability requirements cannot be derived from the captured configuration")
    return sorted(inferred)


def capability_config(device_config, source_config=None):
    """Return a runtime copy with capabilities, preserving immutable manifest records."""
    if not isinstance(device_config, dict):
        raise ValueError("A device configuration mapping is required")
    result = deepcopy(device_config)
    required = required_border_types(source_config if source_config is not None else device_config)
    if required:
        settings = result.get("borders_settings")
        if not isinstance(settings, dict) or "BORDER_NODE" not in result.get("device_roles", []):
            raise ValueError("A replacement border requires its captured role and border settings")
        if "border_types" in settings and normalize_border_types(settings["border_types"]) != required:
            raise ValueError("Replacement border_types differs from the captured source capabilities")
        settings["border_types"] = required
        required_border_types(result)
    return result
