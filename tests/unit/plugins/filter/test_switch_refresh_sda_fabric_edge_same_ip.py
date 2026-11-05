"""Offline contracts for the same-IP refresh planner and recovery manifest."""

from copy import deepcopy
from unittest import TestCase

from ansible.errors import AnsibleFilterError
from ansible_collections.cisco.catalystcenter.plugins.filter import (
    switch_refresh_sda_fabric_edge_same_ip as filters,
)


SITE = "Global/Region/Building"
IPS = ["192.0.2.10", "192.0.2.11"]


class TaggedInt(int):
    """Model Ansible's tagged integer values without coupling to core internals."""


def batch():
    return {
        "name": "edge-refresh", "fabric_site_name_hierarchy": SITE,
        "onboarding_method": "lan_automation",
        "new_devices": {
            "device_ips": list(IPS),
            "lan_automation_config": [{"lan_automation": {
                "discovered_device_site_name_hierarchy": SITE,
                "primary_device_management_ip_address": "198.51.100.1",
                "primary_device_interface_names": ["GigabitEthernet1/0/1", "GigabitEthernet1/0/2"],
                "ip_pools": [{"ip_pool_name": "LAN", "ip_pool_role": "MAIN_POOL"}],
                "isis_domain_pwd": "never-saved-in-the-manifest",
                "launch_and_wait": True,
                "discovery_devices": [
                    {"device_management_ip_address": ip, "device_serial_number": "NEW-%d" % index}
                    for index, ip in enumerate(IPS)]}}]},
        "device_mapping": [
            {"management_ip": ip, "interface_migration": {
                "only_mapped": False,
                "port_assignments": [{"source": "GigabitEthernet1/0/5", "destination": "GigabitEthernet1/0/10"}],
                "port_channels": [{"source": "GigabitEthernet1/0/47", "destination": "TenGigabitEthernet1/1/1"}]}}
            for ip in IPS],
    }


def records(new=False):
    return [{"managementIpAddress": ip, "id": ("new-" if new else "old-") + str(index),
             "serialNumber": ("NEW-" if new else "OLD-") + str(index),
             "hostname": "edge-%d.example.test" % index, "collectionStatus": "Managed",
             "managementState": "Managed", "reachabilityStatus": "Reachable",
             "role": "ACCESS", "family": "Switches and Hubs"}
            for index, ip in enumerate(IPS)]


def payloads():
    original, mapped = [], []
    for ip in IPS:
        assignment = {"interface_name": "GigabitEthernet1/0/5", "data_vlan_name": "data",
                      "voice_vlan_name": "voice", "security_group_name": "Employees",
                      "authentication_template_name": "Closed Authentication"}
        channel = {"interface_names": ["GigabitEthernet1/0/47", "GigabitEthernet1/0/48"], "protocol": "LACP"}
        original.append({"ip_address": ip, "fabric_site_name_hierarchy": SITE,
                         "port_assignments": [assignment], "port_channels": [channel]})
        mapped_assignment = deepcopy(assignment)
        mapped_assignment["interface_name"] = "GigabitEthernet1/0/10"
        mapped_channel = deepcopy(channel)
        mapped_channel["interface_names"] = ["TenGigabitEthernet1/1/1", "GigabitEthernet1/0/48"]
        mapped.append({"ip_address": ip, "fabric_site_name_hierarchy": SITE,
                       "port_assignments": [mapped_assignment], "port_channels": [mapped_channel]})
    return {
        "inventory": [{"ip_address_list": [ip], "role": "ACCESS"} for ip in IPS],
        "provision": [{"management_ip_address": ip, "site_name_hierarchy": SITE,
                       "provisioning": True, "force_provisioning": False} for ip in IPS],
        "fabric": [{"fabric_devices": {"fabric_name": SITE, "device_config": [
            {"device_ip": ip, "device_roles": ["EDGE_NODE"]} for ip in IPS]}}],
        "cleanup": original, "restore": mapped,
    }


def raw(items):
    return {"catalystcenter_response": {"response": items}}


class TestSameIpPlanner(TestCase):
    def test_bulk_generator_filters_preserve_same_ip_and_mappings(self):
        plan = filters.edge_same_ip_plan([batch()])[0]
        migration = plan["generator_configs"]["restore"]["component_specific_filters"]
        self.assertEqual(len(migration["port_assignments"]), 2)
        self.assertEqual(len(migration["port_channels"]), 2)
        for component in migration.values():
            self.assertEqual([entry["source_device_ip"] for entry in component], IPS)
            self.assertEqual([entry["destination_device_ip"] for entry in component], IPS)
        self.assertEqual(migration["port_channels"][0]["interface_mappings"][0]["destination_interface_name"],
                         "TenGigabitEthernet1/1/1")
        self.assertEqual(plan["generator_configs"]["cleanup"]["component_specific_filters"]["port_assignments"][0]["device_ips"], IPS)

    def test_unknown_old_new_mapping_schema_is_rejected(self):
        value = batch()
        value["device_mapping"][0]["old"] = {"management_ip": IPS[0]}
        with self.assertRaisesRegex(AnsibleFilterError, "unsupported keys"):
            filters.edge_same_ip_plan([value])

    def test_rejects_cross_batch_ip_overlap_before_capture(self):
        second = batch()
        second["name"] = "other"
        second["new_devices"]["lan_automation_config"][0]["lan_automation"]["primary_device_management_ip_address"] = "198.51.100.2"
        with self.assertRaisesRegex(AnsibleFilterError, "management IPs across batches"):
            filters.edge_same_ip_plan([batch(), second])

    def test_requires_exact_device_mapping_and_discovery_coverage(self):
        for component in ("mapping", "discovery"):
            value = batch()
            if component == "mapping":
                value["device_mapping"].pop()
            else:
                value["new_devices"]["lan_automation_config"][0]["lan_automation"]["discovery_devices"].pop()
            with self.subTest(component=component), self.assertRaisesRegex(AnsibleFilterError, "cover"):
                filters.edge_same_ip_plan([value])

    def test_rejects_cross_component_destination_collision(self):
        value = batch()
        value["device_mapping"][0]["interface_migration"]["port_channels"][0]["destination"] = "gigabitethernet1/0/10"
        with self.assertRaisesRegex(AnsibleFilterError, "destination interfaces"):
            filters.edge_same_ip_plan([value])

    def test_accepts_native_pnp_authorization_and_stack_serials(self):
        value = batch()
        lan = value["new_devices"]["lan_automation_config"][0]["lan_automation"]
        lan["pnp_authorization"] = True
        lan["device_serial_number_authorization"] = ["NEW-0", "NEW-0B", "NEW-1"]
        lan["discovery_devices"][0]["device_serial_number"] = "new-0b, NEW-0"
        plan = filters.edge_same_ip_plan([value])[0]
        self.assertEqual(plan["serial_by_ip"][IPS[0]], "NEW-0,NEW-0B")

    def test_requires_completion_and_valid_hierarchy(self):
        for key, value in (("launch_and_wait", False), ("discovered_device_site_name_hierarchy", "Global/Other")):
            current = batch()
            current["new_devices"]["lan_automation_config"][0]["lan_automation"][key] = value
            with self.subTest(key=key), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_plan([current])

    def test_accepts_tagged_discovery_integers_but_rejects_booleans(self):
        value = batch()
        lan = value["new_devices"]["lan_automation_config"][0]["lan_automation"]
        lan["discovery_level"] = TaggedInt(2)
        lan["discovery_timeout"] = TaggedInt(20)
        self.assertEqual(len(filters.edge_same_ip_plan([value])), 1)
        for key in ("discovery_level", "discovery_timeout"):
            invalid = deepcopy(value)
            invalid["new_devices"]["lan_automation_config"][0]["lan_automation"][key] = True
            with self.subTest(key=key), self.assertRaisesRegex(AnsibleFilterError, "must be an integer"):
                filters.edge_same_ip_plan([invalid])

    def test_rejects_duplicate_stack_member_and_seed_port(self):
        value = batch()
        lan = value["new_devices"]["lan_automation_config"][0]["lan_automation"]
        lan["discovery_devices"][1]["device_serial_number"] = "NEW-0"
        with self.assertRaisesRegex(AnsibleFilterError, "replacement serials"):
            filters.edge_same_ip_plan([value])
        value = batch()
        value["new_devices"]["lan_automation_config"][0]["lan_automation"]["primary_device_interface_names"].append("gigabitethernet1/0/1")
        with self.assertRaisesRegex(AnsibleFilterError, "seed interfaces"):
            filters.edge_same_ip_plan([value])

    def test_only_mapped_requires_explicit_interfaces(self):
        value = batch()
        value["device_mapping"][0]["interface_migration"] = {"only_mapped": True}
        with self.assertRaisesRegex(AnsibleFilterError, "at least one"):
            filters.edge_same_ip_plan([value])


class TestSameIpSnapshot(TestCase):
    def setUp(self):
        self.plan = filters.edge_same_ip_plan([batch()])[0]
        self.manifest = filters.edge_same_ip_snapshot(self.plan, records(), payloads(), "controller.example.test")

    def test_snapshot_contains_original_and_mapped_ports_without_lan_secrets(self):
        self.assertNotIn("never-saved", str(self.manifest))
        self.assertNotIn("lan_config", self.manifest)
        cleanup = self.manifest["payloads"]["cleanup"]
        restore = self.manifest["payloads"]["restore"]
        self.assertEqual(cleanup[0]["port_assignments"][0]["interface_name"], "GigabitEthernet1/0/5")
        self.assertEqual(restore[0]["port_assignments"][0]["interface_name"], "GigabitEthernet1/0/10")
        self.assertEqual(filters.edge_same_ip_manifest(self.manifest, self.plan, "controller.example.test"), self.manifest)

    def test_rejects_input_and_controller_changes_on_resume(self):
        value = batch()
        value["device_mapping"][0]["interface_migration"]["only_mapped"] = True
        other = filters.edge_same_ip_plan([value])[0]
        for plan, controller in ((other, "controller.example.test"), (self.plan, "other-controller")):
            with self.subTest(controller=controller), self.assertRaisesRegex(AnsibleFilterError, "does not match"):
                filters.edge_same_ip_manifest(self.manifest, plan, controller)

    def test_rejects_payload_checksum_mismatch(self):
        self.manifest["hashes"]["restore"] = "corrupted"
        with self.assertRaisesRegex(AnsibleFilterError, "checksum mismatch"):
            filters.edge_same_ip_manifest(self.manifest, self.plan, "controller.example.test")

    def test_capture_checksum_protects_original_identity_and_survives_checkpoints(self):
        for field, value in (("uuid", "accidental-new-uuid"), ("serial_number", "ACCIDENTAL-SERIAL")):
            manifest = deepcopy(self.manifest)
            manifest["old_devices"][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(AnsibleFilterError, "immutable capture checksum"):
                filters.edge_same_ip_manifest(manifest, self.plan, "controller.example.test")
        advanced = filters.edge_same_ip_checkpoint(self.manifest, "inventory_ready", records(True))
        self.assertEqual(advanced["capture_checksum"], self.manifest["capture_checksum"])
        self.assertEqual(filters.edge_same_ip_manifest(advanced, self.plan, "controller.example.test"), advanced)

    def test_accepts_tagged_checkpoint_integer_but_rejects_boolean(self):
        self.manifest["stage_index"] = TaggedInt(0)
        self.assertEqual(filters.edge_same_ip_manifest(self.manifest, self.plan, "controller.example.test")["stage_index"], 0)
        self.manifest["stage_index"] = False
        with self.assertRaisesRegex(AnsibleFilterError, "stage is invalid"):
            filters.edge_same_ip_manifest(self.manifest, self.plan, "controller.example.test")

    def test_rejects_missing_devices_and_fabric_roles(self):
        for component in ("inventory", "provision", "fabric", "cleanup", "restore"):
            value = payloads()
            value[component] = []
            with self.subTest(component=component), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_snapshot(self.plan, records(), value, "controller")
        value = payloads()
        value["fabric"][0]["fabric_devices"]["device_config"][0]["device_roles"].append("BORDER_NODE")
        with self.assertRaisesRegex(AnsibleFilterError, "pure EDGE_NODE"):
            filters.edge_same_ip_snapshot(self.plan, records(), value, "controller")

    def test_rejects_stale_or_unmapped_restoration_payload(self):
        value = payloads()
        value["restore"] = deepcopy(value["cleanup"])
        with self.assertRaisesRegex(AnsibleFilterError, "does not match the original"):
            filters.edge_same_ip_snapshot(self.plan, records(), value, "controller")

    def test_normalizes_identical_inventory_stack_exports(self):
        value = payloads()
        value["inventory"].append(deepcopy(value["inventory"][0]))
        manifest = filters.edge_same_ip_snapshot(self.plan, records(), value, "controller")
        self.assertEqual(len(manifest["payloads"]["inventory"]), 2)

    def test_original_and_replacement_serials_must_differ(self):
        value = records()
        value[0]["serialNumber"] = "NEW-0"
        with self.assertRaisesRegex(AnsibleFilterError, "different serial"):
            filters.edge_same_ip_snapshot(self.plan, value, payloads(), "controller")

    def test_original_identity_cannot_be_another_devices_replacement(self):
        value = records()
        value[0]["serialNumber"] = "NEW-1"
        with self.assertRaisesRegex(AnsibleFilterError, "different serial"):
            filters.edge_same_ip_snapshot(self.plan, value, payloads(), "controller")
        for field in ("id", "serialNumber"):
            value = records()
            value[1][field] = value[0][field]
            with self.subTest(field=field), self.assertRaisesRegex(AnsibleFilterError, "must be unique"):
                filters.edge_same_ip_snapshot(self.plan, value, payloads(), "controller")
        manifest = deepcopy(self.manifest)
        manifest["old_devices"][0]["serial_number"] = "NEW-1"
        manifest["capture_checksum"] = filters._capture_checksum(manifest)
        with self.assertRaisesRegex(AnsibleFilterError, "different serial"):
            filters.edge_same_ip_manifest(manifest, self.plan, "controller.example.test")

    def test_empty_ports_require_explicit_opt_in(self):
        value = batch()
        value["allow_empty_host_port_config"] = True
        for mapping in value["device_mapping"]:
            mapping["interface_migration"] = {}
        plan = filters.edge_same_ip_plan([value])[0]
        configs = payloads()
        configs["cleanup"] = configs["restore"] = []
        manifest = filters.edge_same_ip_snapshot(plan, records(), configs, "controller")
        self.assertEqual(manifest["payloads"]["cleanup"], [])
        self.assertEqual(filters.edge_same_ip_subset([{"ip_address": IPS[0], "port_assignments": []}], IPS), [])

    def test_captured_floor_sites_populate_lan_devices_and_validate_supplied_site(self):
        configs = payloads()
        configs["provision"][0]["site_name_hierarchy"] = SITE + "/Floor1"
        manifest = filters.edge_same_ip_snapshot(self.plan, records(), configs, "controller")
        lan = filters.edge_same_ip_lan_config(self.plan, manifest)[0]["lan_automation"]
        self.assertEqual(lan["discovery_devices"][0]["device_site_name_hierarchy"], SITE + "/Floor1")
        self.assertEqual(lan["discovery_devices"][0]["device_host_name"], "edge-0")
        self.plan["lan_config"][0]["lan_automation"]["discovery_devices"][0]["device_site_name_hierarchy"] = SITE
        with self.assertRaisesRegex(AnsibleFilterError, "conflicts"):
            filters.edge_same_ip_lan_config(self.plan, manifest)

    def test_explicit_lan_site_conflict_fails_during_capture_and_manifest_load(self):
        value = batch()
        device = value["new_devices"]["lan_automation_config"][0]["lan_automation"]["discovery_devices"][0]
        device["device_site_name_hierarchy"] = SITE + "/Floor2"
        plan = filters.edge_same_ip_plan([value])[0]
        configs = payloads()
        configs["provision"][0]["site_name_hierarchy"] = SITE + "/Floor1"
        with self.assertRaisesRegex(AnsibleFilterError, "conflicts"):
            filters.edge_same_ip_snapshot(plan, records(), configs, "controller")
        self.plan["lan_config"][0]["lan_automation"]["discovery_devices"][0]["device_site_name_hierarchy"] = SITE + "/Floor2"
        with self.assertRaisesRegex(AnsibleFilterError, "conflicts"):
            filters.edge_same_ip_manifest(self.manifest, self.plan, "controller.example.test")

    def test_checkpoints_require_replacement_identity_and_cannot_move_back(self):
        with self.assertRaisesRegex(AnsibleFilterError, "must be saved"):
            filters.edge_same_ip_checkpoint(self.manifest, "inventory_ready")
        new = filters.edge_same_ip_checkpoint(self.manifest, "inventory_ready", records(True))
        self.assertEqual(new["stage_index"], 7)
        with self.assertRaisesRegex(AnsibleFilterError, "backwards"):
            filters.edge_same_ip_checkpoint(new, "captured")
        changed = records(True)
        changed[0]["id"] = "changed-new-uuid"
        with self.assertRaisesRegex(AnsibleFilterError, "changed after checkpoint"):
            filters.edge_same_ip_checkpoint(new, "provisioned", changed)


class TestSameIpIdentityAndPostconditions(TestCase):
    def setUp(self):
        self.plan = filters.edge_same_ip_plan([batch()])[0]
        self.manifest = filters.edge_same_ip_snapshot(self.plan, records(), payloads(), "controller.example.test")

    def test_teardown_guard_rejects_replacement_at_reused_ip(self):
        with self.assertRaisesRegex(AnsibleFilterError, "refusing to target the replacement"):
            filters.edge_same_ip_identity_guard(records(True), self.manifest)
        self.assertEqual(filters.edge_same_ip_identity_guard(records()[:1], self.manifest), IPS[:1])
        self.assertEqual(filters.edge_same_ip_identity_guard([], self.manifest), [])

    def test_readiness_requires_new_serial_and_uuid(self):
        self.assertTrue(filters.edge_same_ip_ready(raw(records(True)), self.plan, self.manifest, "ACCESS"))
        with self.assertRaisesRegex(AnsibleFilterError, "unexpected serial"):
            filters.edge_same_ip_ready(raw(records()), self.plan, self.manifest)
        value = records(True)
        value[0]["id"] = "old-0"
        with self.assertRaisesRegex(AnsibleFilterError, "original device"):
            filters.edge_same_ip_ready(raw(value), self.plan, self.manifest)

    def test_readiness_retries_incomplete_records_but_rejects_later_wrong_serial(self):
        value = records(True)
        value[0]["collectionStatus"] = "In Progress"
        self.assertFalse(filters.edge_same_ip_ready(raw(value), self.plan, self.manifest))
        value[1]["serialNumber"] = "UNEXPECTED"
        with self.assertRaisesRegex(AnsibleFilterError, "unexpected serial"):
            filters.edge_same_ip_ready(raw(value), self.plan, self.manifest)
        self.assertFalse(filters.edge_same_ip_ready(raw([]), self.plan, self.manifest))

    def test_readiness_rejects_changed_checkpoint_uuid(self):
        manifest = filters.edge_same_ip_checkpoint(self.manifest, "inventory_ready", records(True))
        value = records(True)
        value[0]["id"] = "replacement-replaced-again"
        with self.assertRaisesRegex(AnsibleFilterError, "UUID changed"):
            filters.edge_same_ip_ready(raw(value), self.plan, manifest)

    def test_readiness_requires_captured_or_explicit_desired_hostname(self):
        value = records(True)
        value[0]["hostname"] = "wrong-name.example.test"
        self.assertFalse(filters.edge_same_ip_ready(raw(value), self.plan, self.manifest))
        value[0]["hostname"] = "EDGE-0.other-domain.test"
        self.assertTrue(filters.edge_same_ip_ready(raw(value), self.plan, self.manifest))
        self.plan["lan_config"][0]["lan_automation"]["discovery_devices"][0]["device_host_name"] = "desired-custom-name"
        self.assertFalse(filters.edge_same_ip_ready(raw(value), self.plan, self.manifest))
        value[0]["hostname"] = "DESIRED-CUSTOM-NAME.example.test"
        self.assertTrue(filters.edge_same_ip_ready(raw(value), self.plan, self.manifest))

    def test_partial_new_identity_can_wait_without_ignoring_populated_wrong_identity(self):
        value = records(True)
        for field in ("hostname", "serialNumber", "collectionStatus", "managementState"):
            value[0].pop(field)
        self.assertFalse(filters.edge_same_ip_ready(raw(value), self.plan, self.manifest))
        value[0]["id"] = "old-0"
        with self.assertRaisesRegex(AnsibleFilterError, "original device"):
            filters.edge_same_ip_ready(raw(value), self.plan, self.manifest)

    def test_query_failure_is_not_device_absence(self):
        for value in ({"failed": True}, {"catalystcenter_response": {}}, {"catalystcenter_response": {"response": "error"}}):
            with self.subTest(value=value), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_devices(value)
        self.assertEqual(filters.edge_same_ip_devices(raw([])), [])

    def test_subset_targets_only_still_present_original_devices(self):
        configs = payloads()
        for kind in ("host", "provision", "inventory", "fabric"):
            component = "cleanup" if kind == "host" else kind
            subset = filters.edge_same_ip_subset(configs[component], [IPS[1]], kind)
            self.assertEqual(len(subset), 1)
            self.assertNotIn(IPS[0], str(subset))
            self.assertIn(IPS[1], str(subset))

    def test_ports_compare_order_insensitive_interfaces_and_controller_defaults(self):
        desired = payloads()["restore"]
        observed = deepcopy(desired)
        observed.reverse()
        observed[0]["port_channels"][0]["interface_names"].reverse()
        observed[0]["port_assignments"][0]["native_vlan_id"] = 1
        self.assertTrue(filters.edge_same_ip_ports_match(desired, observed))
        observed[0]["port_assignments"][0]["data_vlan_name"] = "incorrect"
        self.assertFalse(filters.edge_same_ip_ports_match(desired, observed))
        self.assertTrue(filters.edge_same_ip_ports_match([], [{"ip_address": IPS[0], "fabric_site_name_hierarchy": SITE,
                                                              "port_assignments": [], "port_channels": []}]))

    def test_fabric_postcondition_requires_exact_membership_and_pure_edge(self):
        result = {"response": [[{"fabric_info": [
            {"device_ip": ip, "fabric_details": [{"deviceRoles": ["EDGE_NODE"]}]} for ip in IPS]}]]}
        self.assertTrue(filters.edge_same_ip_fabric(result, self.plan, IPS))
        self.assertFalse(filters.edge_same_ip_fabric(result, self.plan, IPS, "absent"))
        result["response"][0][0]["fabric_info"].pop()
        self.assertFalse(filters.edge_same_ip_fabric(result, self.plan, IPS))
        absent = {"response": ["No fabric devices found for the given filters."]}
        self.assertTrue(filters.edge_same_ip_fabric(absent, self.plan, IPS, "absent"))
        self.assertFalse(filters.edge_same_ip_fabric(absent, self.plan, IPS))
        for malformed in ({"response": []}, {"failed": True, "response": []}, {"response": ["unknown error"]}):
            with self.subTest(result=malformed), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_fabric(malformed, self.plan, IPS, "absent")
