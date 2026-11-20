"""Offline contracts for the same-IP refresh planner and recovery manifest."""

from copy import deepcopy
import hashlib
import json
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


def component_entries(config):
    """Match the onboarding generator's separate list for each component."""
    return [
        {"ip_address": entry["ip_address"], "fabric_site_name_hierarchy": entry["fabric_site_name_hierarchy"],
         component: deepcopy(entry[component])}
        for component in ("port_assignments", "port_channels")
        for entry in config if component in entry
    ]


def raw(items):
    return {"catalystcenter_response": {"response": items}}


def generated_batch(method="lan_automation"):
    value = batch()
    value.pop("new_devices")
    value["onboarding_method"] = method
    for index, mapping in enumerate(value["device_mapping"]):
        mapping["replacement_serial_number"] = "NEW-%d" % index
    return value


def generated_lan():
    config = deepcopy(batch()["new_devices"]["lan_automation_config"])
    config[0]["lan_automation"].pop("isis_domain_pwd")
    for device, record in zip(config[0]["lan_automation"]["discovery_devices"], records()):
        device["device_serial_number"] = "REPLACE_WITH_SERIAL_FOR_" + device[
            "device_management_ip_address"
        ].replace(".", "_")
        device["device_host_name"] = record["hostname"]
        device["device_site_name_hierarchy"] = SITE
    return config


class TestGeneratedOnboarding(TestCase):
    def snapshot(self, value):
        plan = filters.edge_same_ip_plan([value])[0]
        return plan, filters.edge_same_ip_snapshot(
            plan, records(), payloads(), "controller", "fabric-1", generated_lan()
        )

    def test_both_methods_derive_ips_and_require_every_replacement_serial(self):
        for method in ("lan_automation", "discovery"):
            value = generated_batch(method)
            plan = filters.edge_same_ip_plan([value])[0]
            self.assertEqual(plan["ips"], IPS)
            self.assertEqual(plan["serial_by_ip"], dict(zip(IPS, ("NEW-0", "NEW-1"))))
            value["device_mapping"][0].pop("replacement_serial_number")
            with self.subTest(method=method), self.assertRaisesRegex(
                AnsibleFilterError, "serial number"
            ):
                filters.edge_same_ip_plan([value])

    def test_generated_serials_are_substituted_by_ip_and_saved_without_password(self):
        value = generated_batch()
        value["new_devices"] = {"isis_domain_pwd": "runtime-secret"}
        plan = filters.edge_same_ip_plan([value])[0]
        generated = generated_lan()
        generated[0]["lan_automation"]["discovery_devices"].reverse()
        manifest = filters.edge_same_ip_snapshot(
            plan, records(), payloads(), "controller", "fabric-1", generated
        )
        self.assertEqual(manifest["schema_version"], 3)
        self.assertEqual(manifest["onboarding"]["method"], "lan_automation")
        saved = manifest["onboarding"]["config"]
        self.assertNotIn("REPLACE_WITH", str(saved))
        self.assertNotIn("runtime-secret", str(manifest))
        self.assertEqual(
            {d["device_management_ip_address"]: d["device_serial_number"]
             for d in saved[0]["lan_automation"]["discovery_devices"]},
            plan["serial_by_ip"],
        )
        filters.edge_same_ip_manifest(manifest, plan, "controller")
        restored = filters.edge_same_ip_lan_config(plan, manifest)
        self.assertEqual(restored[0]["lan_automation"]["isis_domain_pwd"], "runtime-secret")
        self.assertNotIn("isis_domain_pwd", saved[0]["lan_automation"])

    def test_capture_rejects_incomplete_generated_targets_and_stored_secrets(self):
        plan = filters.edge_same_ip_plan([generated_batch()])[0]
        for kind in ("missing", "duplicate", "unexpected", "password"):
            config = generated_lan()
            lan = config[0]["lan_automation"]
            if kind == "missing":
                lan["discovery_devices"].pop()
            elif kind == "duplicate":
                lan["discovery_devices"].append(deepcopy(lan["discovery_devices"][0]))
            elif kind == "unexpected":
                lan["discovery_devices"][0]["device_management_ip_address"] = "192.0.2.99"
            else:
                lan["isis_domain_pwd"] = "unexpected-secret"
            with self.subTest(kind=kind), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_snapshot(
                    plan, records(), payloads(), "controller", "fabric-1", config
                )

    def test_saved_onboarding_is_protected_and_revalidated_on_resume(self):
        plan, manifest = self.snapshot(generated_batch())
        for field, value in (("method", "discovery"), ("config", [])):
            changed = deepcopy(manifest)
            changed["onboarding"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(AnsibleFilterError, "checksum"):
                filters.edge_same_ip_manifest(changed, plan, "controller")
        changed = deepcopy(manifest)
        changed["onboarding"]["config"][0]["lan_automation"]["discovery_devices"][0][
            "device_serial_number"
        ] = "WRONG"
        changed["capture_checksum"] = filters._capture_checksum(changed)
        with self.assertRaisesRegex(AnsibleFilterError, "saved onboarding serials"):
            filters.edge_same_ip_manifest(changed, plan, "controller")

    def test_discovery_inherits_credentials_by_type_and_replaces_lists(self):
        value = generated_batch("discovery")
        value["new_devices"] = {
            "discovery": {
                "protocol_order": "ssh",
                "use_global_credentials": False,
                "discovery_specific_credentials": {
                    "cli_credentials_list": [{"username": "shared", "password": "shared-secret"}],
                    "snmp_v2_read_credential": {"community": "shared-snmp"},
                },
            }
        }
        value["device_mapping"][1]["discovery"] = {
            "discovery_specific_credentials": {
                "cli_credentials_list": [{"username": "device", "password": "device-secret"}],
            }
        }
        plan, manifest = self.snapshot(value)
        jobs = filters.edge_same_ip_discovery_config(plan)
        self.assertEqual([job["ip_address_list"] for job in jobs], [[IPS[0]], [IPS[1]]])
        self.assertTrue(all(job["discovery_type"] == "SINGLE" for job in jobs))
        self.assertNotEqual(jobs[0]["discovery_name"], jobs[1]["discovery_name"])
        self.assertEqual(
            jobs[1]["discovery_specific_credentials"]["cli_credentials_list"],
            [{"username": "device", "password": "device-secret"}],
        )
        self.assertEqual(
            jobs[1]["discovery_specific_credentials"]["snmp_v2_read_credential"],
            {"community": "shared-snmp"},
        )
        self.assertNotIn("secret", str(manifest))
        self.assertEqual(manifest["onboarding"], {"method": "discovery", "config": []})
        self.assertTrue(filters.edge_same_ip_ready(raw(records(True)), plan, manifest))

    def test_discovery_can_switch_a_device_to_global_credentials(self):
        value = generated_batch("discovery")
        value["new_devices"] = {
            "discovery": {
                "use_global_credentials": False,
                "discovery_specific_credentials": {
                    "cli_credentials_list": [{"username": "shared", "password": "secret"}]
                },
            }
        }
        value["device_mapping"][1]["discovery"] = {
            "use_global_credentials": True,
            "global_credentials": {
                "cli_credentials_list": [{"username": "global", "description": "Global CLI"}]
            },
        }
        plan = filters.edge_same_ip_plan([value])[0]
        job = filters.edge_same_ip_discovery_config(plan)[1]
        self.assertTrue(job["use_global_credentials"])
        self.assertNotIn("discovery_specific_credentials", job)
        self.assertEqual(
            job["global_credentials"]["cli_credentials_list"][0]["description"], "Global CLI"
        )

    def test_runtime_credentials_can_rotate_without_invalidating_capture(self):
        value = generated_batch("discovery")
        value["new_devices"] = {
            "discovery": {
                "use_global_credentials": False,
                "discovery_specific_credentials": {
                    "cli_credentials_list": [{"username": "admin", "password": "before"}]
                },
            }
        }
        plan, manifest = self.snapshot(value)
        value["new_devices"]["discovery"]["discovery_specific_credentials"]["cli_credentials_list"][
            0
        ]["password"] = "after"
        rotated = filters.edge_same_ip_plan([value])[0]
        self.assertEqual(rotated["fingerprint"], plan["fingerprint"])
        filters.edge_same_ip_manifest(manifest, rotated, "controller")

    def test_bad_discovery_options_fail_during_planning(self):
        for discovery in (
            {"retry": True},
            {"use_global_credentials": False},
            {"unknown": "value"},
            {
                "discovery_specific_credentials": {
                    "cli_credentials_list": [{"username": "missing-password"}]
                }
            },
        ):
            value = generated_batch("discovery")
            value["new_devices"] = {"discovery": discovery}
            with self.subTest(discovery=discovery), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_plan([value])

    def test_generated_onboarding_checkpoint_is_generic_and_keeps_legacy_indices(self):
        plan, manifest = self.snapshot(generated_batch("discovery"))
        manifest = filters.edge_same_ip_checkpoint(manifest, "onboarded", records(True))
        self.assertEqual(manifest["stage_index"], 6)
        filters.edge_same_ip_manifest(manifest, plan, "controller")


class TestSameIpGoldenImage(TestCase):
    def golden(self):
        return {"image_name": "cat9k_iosxe.17.12.04.SPA.bin",
                "device_image_family_name": "Cisco Catalyst 9300 Switch"}

    def value(self, legacy=False):
        value = batch() if legacy else generated_batch()
        value.setdefault("new_devices", {})["golden_image"] = self.golden()
        return value

    def snapshot(self, value, enabled=True):
        plan = filters.edge_same_ip_plan([value], enabled)[0]
        manifest = filters.edge_same_ip_snapshot(
            plan, records(), payloads(), "controller", "fabric-1", generated_lan())
        return plan, manifest

    def test_tag_only_and_both_import_sources_work_for_both_input_formats(self):
        for legacy in (False, True):
            for kind in (None, "remote", "CCO"):
                value = self.value(legacy)
                golden = value["new_devices"]["golden_image"]
                if kind == "remote":
                    golden["import_image_details"] = {"type": kind, "url_details": {"payload": [
                        {"source_url": "https://user:secret@images.example/" + golden["image_name"]}]}}
                elif kind == "CCO":
                    golden["import_image_details"] = {"type": kind, "cco_image_details": {
                        "image_name": golden["image_name"]}}
                with self.subTest(legacy=legacy, kind=kind):
                    plan, manifest = self.snapshot(value)
                    tagging = plan["swim_config"][0]["tagging_details"]
                    self.assertEqual(tagging, dict(self.golden(), site_name=SITE, device_role="ALL", tagging=True))
                    if kind:
                        imported = plan["swim_config"][0]["import_image_details"]
                        names = (imported["url_details"]["payload"][0]["source_url"] if kind == "remote"
                                 else imported["cco_image_details"]["image_name"])
                        self.assertIsInstance(names, list)
                        self.assertEqual(len(names), 1)
                    self.assertEqual(manifest["schema_version"], 4)
                    self.assertEqual(manifest["golden_image"], tagging)
                    self.assertNotIn("secret@", json.dumps(manifest))
                    self.assertNotIn("import_image_details", manifest)
                    filters.edge_same_ip_manifest(manifest, plan, "controller")
                    self.assertEqual(len(filters.edge_same_ip_lan_config(plan, manifest)), 1)

    def test_controls_require_an_image_only_for_enabled_lan_batches(self):
        filters.edge_same_ip_plan([generated_batch()])
        filters.edge_same_ip_plan([generated_batch("discovery")], True)
        for value in (batch(), generated_batch()):
            with self.assertRaisesRegex(AnsibleFilterError, "golden_image is required"):
                filters.edge_same_ip_plan([value], True)
        for enabled in ("true", 1, None):
            with self.subTest(enabled=enabled), self.assertRaisesRegex(AnsibleFilterError, "boolean"):
                filters.edge_same_ip_plan([generated_batch()], enabled)
        value = generated_batch("discovery")
        value["new_devices"] = {"golden_image": self.golden()}
        with self.assertRaisesRegex(AnsibleFilterError, "only for LAN automation"):
            filters.edge_same_ip_plan([value])

    def test_rejects_unsafe_or_ambiguous_image_inputs_even_with_swim_disabled(self):
        image = self.golden()["image_name"]
        sources = [
            {"type": "local"},
            {"type": "remote", "url_details": {}, "cco_image_details": {}},
            {"type": "remote", "url_details": {"payload": []}},
            {"type": "remote", "url_details": {"payload": [{"source_url": [image, image]}]}},
            {"type": "remote", "url_details": {"payload": [{"source_url": image, "is_third_party": True}]}},
            {"type": "remote", "url_details": {"payload": [{"source_url": image, "is_third_party": "false"}]}},
            {"type": "remote", "url_details": {"payload": [{"source_url": image + "?token=secret"}]}},
            {"type": "remote", "url_details": {"payload": [{"source_url": image + "#fragment"}]}},
            {"type": "remote", "url_details": {"payload": [{"source_url": "other.bin"}]}},
            {"type": "CCO", "cco_image_details": {"image_name": "other.bin"}},
            {"type": "CCO", "cco_image_details": {"image_name": [image, image]}},
        ]
        invalid = [None, {}, dict(self.golden(), image_name=" "), dict(self.golden(), device_role="ACCESS")]
        invalid.extend(dict(self.golden(), import_image_details=source) for source in sources)
        for index, golden in enumerate(invalid):
            value = self.value()
            value["new_devices"]["golden_image"] = golden
            with self.subTest(case=index), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_plan([value], False)

    def test_cross_batch_image_conflicts_fail_before_capture(self):
        first, second = self.value(), self.value()
        second["name"] = "other"
        for index, mapping in enumerate(second["device_mapping"]):
            mapping.update(management_ip="192.0.2.%d" % (index + 20), replacement_serial_number="OTHER-%d" % index)
        filters.edge_same_ip_plan([first, second], True)
        second["new_devices"]["golden_image"]["image_name"] = "other.bin"
        with self.assertRaisesRegex(AnsibleFilterError, "conflicting golden images"):
            filters.edge_same_ip_plan([first, second], True)
        second["new_devices"]["golden_image"]["device_image_family_name"] = "Another family"
        filters.edge_same_ip_plan([first, second], True)

    def test_import_credentials_can_rotate_but_image_intent_is_immutable(self):
        for legacy in (False, True):
            value = self.value(legacy)
            image = value["new_devices"]["golden_image"]
            image["import_image_details"] = {"type": "remote", "url_details": {"payload": [
                {"source_url": "https://old:secret@images.example/" + image["image_name"]}]}}
            plan, manifest = self.snapshot(value)
            image["import_image_details"]["url_details"]["payload"][0]["source_url"] = (
                "https://new:rotated@mirror.example/" + image["image_name"])
            resumed = filters.edge_same_ip_plan([value], False)[0]
            with self.subTest(legacy=legacy):
                self.assertEqual(resumed["fingerprint"], plan["fingerprint"])
                filters.edge_same_ip_manifest(manifest, resumed, "controller")
                changed = deepcopy(manifest)
                changed["golden_image"]["image_name"] = "other.bin"
                with self.assertRaisesRegex(AnsibleFilterError, "checksum"):
                    filters.edge_same_ip_manifest(changed, plan, "controller")
                changed["capture_checksum"] = filters._capture_checksum(changed)
                with self.assertRaisesRegex(AnsibleFilterError, "golden image intent"):
                    filters.edge_same_ip_manifest(changed, plan, "controller")
                image["device_image_family_name"] = "Another family"
                with self.assertRaisesRegex(AnsibleFilterError, "golden image intent"):
                    filters.edge_same_ip_manifest(manifest, filters.edge_same_ip_plan([value])[0], "controller")

    def test_existing_snapshots_cannot_silently_gain_or_drop_image_intent(self):
        for legacy in (False, True):
            value = batch() if legacy else generated_batch()
            plan, old = self.snapshot(value, enabled=False)
            self.assertEqual(old["schema_version"], 2 if legacy else 3)
            value.setdefault("new_devices", {})["golden_image"] = self.golden()
            with self.assertRaisesRegex(AnsibleFilterError, "new schema-4 capture"):
                filters.edge_same_ip_manifest(old, filters.edge_same_ip_plan([value])[0], "controller")
            enriched, manifest = self.snapshot(value)
            with self.assertRaisesRegex(AnsibleFilterError, "golden image intent"):
                filters.edge_same_ip_manifest(manifest, plan, "controller")
            advanced = filters.edge_same_ip_checkpoint(manifest, "onboarded", records(True))
            self.assertEqual(advanced["stage_index"], 6)
            filters.edge_same_ip_manifest(advanced, enriched, "controller")


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


class TestSameIpHostPortComponents(TestCase):
    def setUp(self):
        self.plan = filters.edge_same_ip_plan([generated_batch("discovery")])[0]

    def snapshot(self, configs):
        return filters.edge_same_ip_snapshot(self.plan, records(), configs, "controller", "fabric-1")

    def test_snapshot_consolidates_original_and_mapped_component_entries(self):
        expected = self.snapshot(payloads())
        for components in (("cleanup",), ("restore",), ("cleanup", "restore")):
            configs = payloads()
            for component in components:
                configs[component] = component_entries(configs[component])
            original = deepcopy(configs)
            with self.subTest(components=components):
                actual = self.snapshot(configs)
                # Canonical payloads, hashes, and checksum match existing captures.
                self.assertEqual(actual, expected)
                self.assertEqual(configs, original)
                filters.edge_same_ip_manifest(actual, self.plan, "controller")

    def test_verification_accepts_split_combined_and_reordered_components(self):
        combined = payloads()["restore"]
        split = component_entries(combined)
        split.reverse()
        split[0]["port_channels"][0]["interface_names"].reverse()
        for expected, actual in ((combined, split), (split, combined), (split, split)):
            with self.subTest(expected_split=expected is split, actual_split=actual is split):
                self.assertTrue(filters.edge_same_ip_ports_match(expected, actual))
        assignment = next(entry for entry in split if "port_assignments" in entry)
        assignment["port_assignments"][0]["data_vlan_name"] = "wrong-vlan"
        self.assertFalse(filters.edge_same_ip_ports_match(combined, split))

    def test_duplicate_or_conflicting_interfaces_across_entries_are_rejected(self):
        for component in ("port_assignments", "port_channels"):
            for conflicting in (False, True):
                for payload in ("cleanup", "restore"):
                    configs = payloads()
                    configs[payload] = component_entries(configs[payload])
                    duplicate = deepcopy(next(entry for entry in configs[payload] if component in entry))
                    item = duplicate[component][0]
                    if component == "port_assignments":
                        item["interface_name"] = item["interface_name"].lower()
                        if conflicting:
                            item["data_vlan_name"] = "conflicting-vlan"
                    elif conflicting:
                        item["interface_names"] = [item["interface_names"][0].lower(), "GigabitEthernet1/0/49"]
                    configs[payload].append(duplicate)
                    with self.subTest(component=component, conflicting=conflicting, payload=payload):
                        with self.assertRaisesRegex(AnsibleFilterError, "interfaces must be unique"):
                            self.snapshot(configs)
                        with self.assertRaisesRegex(AnsibleFilterError, "interfaces must be unique"):
                            filters.edge_same_ip_ports_match(configs[payload], configs[payload])

    def test_separate_disjoint_assignments_and_channels_are_all_preserved(self):
        configs = payloads()
        for component in ("cleanup", "restore"):
            configs[component] = component_entries(configs[component])
            extra_entries = []
            for entry in configs[component]:
                extra = deepcopy(entry)
                if "port_assignments" in extra:
                    extra["port_assignments"][0]["interface_name"] = "GigabitEthernet1/0/6"
                else:
                    extra["port_channels"][0]["interface_names"] = ["GigabitEthernet1/0/45", "GigabitEthernet1/0/46"]
                extra_entries.append(extra)
            configs[component].extend(extra_entries)
        captured = self.snapshot(configs)
        for component in ("cleanup", "restore"):
            self.assertEqual(len(captured["payloads"][component]), len(IPS))
            for entry in captured["payloads"][component]:
                self.assertEqual(len(entry["port_assignments"]), 2)
                self.assertEqual(len(entry["port_channels"]), 2)

    def test_source_interfaces_shared_between_components_remain_supported(self):
        configs = payloads()
        for component in ("cleanup", "restore"):
            configs[component][0]["port_channels"][0]["interface_names"].append("GigabitEthernet1/0/5")
            configs[component] = component_entries(configs[component])
        manifest = self.snapshot(configs)
        self.assertIn("GigabitEthernet1/0/5", manifest["payloads"]["cleanup"][0]["port_channels"][0]["interface_names"])

    def test_grouping_does_not_hide_wrong_devices_sites_or_missing_devices(self):
        for invalid in ("ip", "site", "missing"):
            configs = payloads()
            configs["cleanup"] = component_entries(configs["cleanup"])
            if invalid == "ip":
                configs["cleanup"][-1]["ip_address"] = "192.0.2.99"
            elif invalid == "site":
                configs["cleanup"][-1]["fabric_site_name_hierarchy"] = SITE + "/Other"
            else:
                configs["cleanup"] = [entry for entry in configs["cleanup"] if entry["ip_address"] != IPS[1]]
            with self.subTest(invalid=invalid), self.assertRaises(AnsibleFilterError):
                self.snapshot(configs)
        split = component_entries(payloads()["restore"])
        split[-1]["fabric_site_name_hierarchy"] = SITE + "/Other"
        self.assertFalse(filters.edge_same_ip_ports_match(payloads()["restore"], split))

    def test_malformed_component_rows_are_rejected(self):
        for invalid in (None, {}, "port", [None]):
            configs = payloads()
            configs["cleanup"] = component_entries(configs["cleanup"])
            configs["cleanup"][0]["port_assignments"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(AnsibleFilterError):
                self.snapshot(configs)
            with self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_ports_match([], configs["cleanup"])


class TestSameIpSnapshot(TestCase):
    def setUp(self):
        self.plan = filters.edge_same_ip_plan([batch()])[0]
        self.manifest = filters.edge_same_ip_snapshot(self.plan, records(), payloads(), "controller.example.test", "fabric-1")

    def test_snapshot_contains_original_and_mapped_ports_without_lan_secrets(self):
        self.assertNotIn("never-saved", str(self.manifest))
        self.assertNotIn("lan_config", self.manifest)
        cleanup = self.manifest["payloads"]["cleanup"]
        restore = self.manifest["payloads"]["restore"]
        self.assertEqual(cleanup[0]["port_assignments"][0]["interface_name"], "GigabitEthernet1/0/5")
        self.assertEqual(restore[0]["port_assignments"][0]["interface_name"], "GigabitEthernet1/0/10")
        self.assertEqual(filters.edge_same_ip_manifest(self.manifest, self.plan, "controller.example.test"), self.manifest)

    def test_new_snapshot_requires_and_protects_fabric_identity(self):
        self.assertEqual(self.manifest["schema_version"], 2)
        self.assertEqual(self.manifest["fabric_id"], "fabric-1")
        for value in (None, "", " "):
            with self.subTest(value=value), self.assertRaisesRegex(AnsibleFilterError, "fabric ID"):
                filters.edge_same_ip_snapshot(self.plan, records(), payloads(), "controller", value)
        changed = deepcopy(self.manifest)
        changed["fabric_id"] = "other-fabric"
        with self.assertRaisesRegex(AnsibleFilterError, "checksum mismatch"):
            filters.edge_same_ip_manifest(changed, self.plan, "controller.example.test")

    def test_legacy_snapshot_retains_original_checksum_and_resumes(self):
        legacy = deepcopy(self.manifest)
        legacy["schema_version"] = 1
        del legacy["fabric_id"]
        # This is the original schema-1 algorithm, independent of the current
        # helper. A recovery fix must not invalidate already-published captures.
        fields = ("schema_version", "controller", "fingerprint", "name", "site", "ips",
                  "serial_by_ip", "old_devices", "payloads", "hashes")
        content = json.dumps({key: legacy[key] for key in fields}, sort_keys=True,
                             separators=(",", ":"), ensure_ascii=True)
        legacy["capture_checksum"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        validated = filters.edge_same_ip_manifest(legacy, self.plan, "controller.example.test")
        advanced = filters.edge_same_ip_checkpoint(validated, "awaiting_ip_release")
        self.assertEqual(advanced["capture_checksum"], legacy["capture_checksum"])
        self.assertNotIn("fabric_id", advanced)
        filters.edge_same_ip_manifest(advanced, self.plan, "controller.example.test")
        legacy["fabric_id"] = "unprotected-fabric"
        with self.assertRaisesRegex(AnsibleFilterError, "unprotected"):
            filters.edge_same_ip_manifest(legacy, self.plan, "controller.example.test")

    def test_rejects_unknown_or_boolean_manifest_schema(self):
        for value in (True, 0, 5, "2"):
            manifest = deepcopy(self.manifest)
            manifest["schema_version"] = value
            with self.subTest(value=value), self.assertRaisesRegex(AnsibleFilterError, "schema version"):
                filters.edge_same_ip_manifest(manifest, self.plan, "controller.example.test")

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
                filters.edge_same_ip_snapshot(self.plan, records(), value, "controller", "fabric-1")
        value = payloads()
        value["fabric"][0]["fabric_devices"]["device_config"][0]["device_roles"].append("BORDER_NODE")
        with self.assertRaisesRegex(AnsibleFilterError, "pure EDGE_NODE"):
            filters.edge_same_ip_snapshot(self.plan, records(), value, "controller", "fabric-1")

    def test_rejects_stale_or_unmapped_restoration_payload(self):
        value = payloads()
        value["restore"] = deepcopy(value["cleanup"])
        with self.assertRaisesRegex(AnsibleFilterError, "does not match the original"):
            filters.edge_same_ip_snapshot(self.plan, records(), value, "controller", "fabric-1")

    def test_normalizes_identical_inventory_stack_exports(self):
        value = payloads()
        value["inventory"].append(deepcopy(value["inventory"][0]))
        manifest = filters.edge_same_ip_snapshot(self.plan, records(), value, "controller", "fabric-1")
        self.assertEqual(len(manifest["payloads"]["inventory"]), 2)

    def test_original_and_replacement_serials_must_differ(self):
        value = records()
        value[0]["serialNumber"] = "NEW-0"
        with self.assertRaisesRegex(AnsibleFilterError, "different serial"):
            filters.edge_same_ip_snapshot(self.plan, value, payloads(), "controller", "fabric-1")

    def test_original_identity_cannot_be_another_devices_replacement(self):
        value = records()
        value[0]["serialNumber"] = "NEW-1"
        with self.assertRaisesRegex(AnsibleFilterError, "different serial"):
            filters.edge_same_ip_snapshot(self.plan, value, payloads(), "controller", "fabric-1")
        for field in ("id", "serialNumber"):
            value = records()
            value[1][field] = value[0][field]
            with self.subTest(field=field), self.assertRaisesRegex(AnsibleFilterError, "must be unique"):
                filters.edge_same_ip_snapshot(self.plan, value, payloads(), "controller", "fabric-1")
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
        manifest = filters.edge_same_ip_snapshot(plan, records(), configs, "controller", "fabric-1")
        self.assertEqual(manifest["payloads"]["cleanup"], [])
        self.assertEqual(filters.edge_same_ip_subset([{"ip_address": IPS[0], "port_assignments": []}], IPS), [])

    def test_captured_floor_sites_populate_lan_devices_and_validate_supplied_site(self):
        configs = payloads()
        configs["provision"][0]["site_name_hierarchy"] = SITE + "/Floor1"
        manifest = filters.edge_same_ip_snapshot(self.plan, records(), configs, "controller", "fabric-1")
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
            filters.edge_same_ip_snapshot(plan, records(), configs, "controller", "fabric-1")
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


class TestSameIpFabricQueries(TestCase):
    def setUp(self):
        self.plan = filters.edge_same_ip_plan([batch()])[0]
        self.row = {"fabricId": "fabric-1", "networkDeviceId": "old-uuid"}

    def test_site_lookup_requires_one_exact_hierarchy(self):
        self.assertEqual(filters.edge_same_ip_site_id(raw([
            {"id": "site-1", "nameHierarchy": SITE}, {"id": "child", "nameHierarchy": SITE + "/Floor"}]),
            self.plan), "site-1")
        for rows in ([], [{"id": "wrong", "nameHierarchy": SITE + "/Floor"}],
                     [{"id": "one", "nameHierarchy": SITE}, {"id": "two", "nameHierarchy": SITE}]):
            with self.subTest(rows=rows), self.assertRaisesRegex(AnsibleFilterError, "exactly one site"):
                filters.edge_same_ip_site_id(raw(rows), self.plan)

    def test_fabric_lookup_checks_scope_and_only_accepts_explicit_empty_fallback(self):
        self.assertEqual(filters.edge_same_ip_fabric_id(raw([{"id": "fabric-1", "siteId": "site-1"}]), "site-1"),
                         "fabric-1")
        self.assertEqual(filters.edge_same_ip_fabric_id(raw([]), "site-1", True), "")
        for rows in ([], [{"id": "fabric-1", "siteId": "wrong-site"}],
                     [{"id": "fabric-1", "siteId": "site-1"}] * 2):
            with self.subTest(rows=rows), self.assertRaisesRegex(AnsibleFilterError, "exactly one fabric"):
                filters.edge_same_ip_fabric_id(raw(rows), "site-1")

    def test_query_errors_and_malformed_responses_are_never_absence(self):
        for result in ({"failed": True}, {}, {"catalystcenter_response": {"response": None}}, raw(["invalid"])):
            with self.subTest(result=result), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_old_fabric(result, "fabric-1", "old-uuid")
            with self.subTest(result=result), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_fabric_id(result, "site-1", True)

    def test_uuid_membership_requires_both_fabric_and_device_ids(self):
        for fabric_id, uuid in ((None, "old-uuid"), ("fabric-1", None), ("", "old-uuid")):
            with self.subTest(fabric_id=fabric_id, uuid=uuid), self.assertRaises(AnsibleFilterError):
                filters.edge_same_ip_old_fabric(raw([]), fabric_id, uuid)
        self.assertTrue(filters.edge_same_ip_old_fabric(raw([]), "fabric-1", "old-uuid"))
        self.assertFalse(filters.edge_same_ip_old_fabric(raw([self.row]), "fabric-1", "old-uuid"))
        self.assertTrue(filters.edge_same_ip_old_fabric(raw([self.row]), "fabric-1", "old-uuid", "present"))
        self.assertTrue(filters.edge_same_ip_old_fabric(raw([self.row]), "fabric-1", "old-uuid", "any"))
        self.assertTrue(filters.edge_same_ip_old_fabric(raw([]), "fabric-1", "old-uuid", "any"))

    def test_uuid_lookup_rejects_wrong_scope_and_duplicate_memberships(self):
        for field in ("fabricId", "networkDeviceId"):
            row = dict(self.row, **{field: "wrong"})
            with self.subTest(field=field), self.assertRaisesRegex(AnsibleFilterError, "different fabric or device"):
                filters.edge_same_ip_old_fabric(raw([row]), "fabric-1", "old-uuid")
        with self.assertRaisesRegex(AnsibleFilterError, "duplicate memberships"):
            filters.edge_same_ip_old_fabric(raw([self.row, self.row]), "fabric-1", "old-uuid")


class TestSameIpIdentityAndPostconditions(TestCase):
    def setUp(self):
        self.plan = filters.edge_same_ip_plan([batch()])[0]
        self.manifest = filters.edge_same_ip_snapshot(self.plan, records(), payloads(), "controller.example.test", "fabric-1")

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
