# Copyright (c) 2026 Cisco and/or its affiliates.
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

"""Exercise the manager's real creation payload path without a controller."""

from copy import deepcopy
from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.cisco.catalystcenter.plugins.modules.sda_fabric_devices_workflow_manager import (
    FabricDevices,
)


class TestIpTransitReplayPayload(TestCase):
    def setUp(self):
        self.manager = FabricDevices.__new__(FabricDevices)
        self.manager.have = {"fabric_devices": [{"ip_l3_handoff_details": [None]}]}
        self.manager.log = Mock()
        self.manager.validate_layer3_handoff_ip_transit = Mock(
            return_value=("transit-id", "HundredGigE1/0/1", "BLDG23_Campus_VN", 440, 510, True)
        )
        self.manager.check_valid_reserved_pool = Mock(return_value=True)
        self.manager.get_taskid_post_api_call = Mock(return_value="task-id")
        self.manager.get_task_status_from_tasks_by_id = Mock(return_value=self.manager)
        self.manager.check_return_status = Mock(return_value=self.manager)
        self.handoff = {
            "interface_name": "HundredGigE1/0/1",
            "transit_network_name": "BLDG23_IP_Transit",
            "virtual_network_name": "BLDG23_Campus_VN",
            "vlan_id": 440,
            "tcp_mss_adjustment": 510,
            "local_ip_address": "204.1.100.5/30",
            "remote_ip_address": "204.1.100.6/30",
        }

    def build_and_submit(self):
        payload = self.manager.get_ip_l3_handoff_params(
            "fabric-id",
            "replacement-uuid",
            {"device_ip": "192.0.2.10", "borders_settings": {"layer3_handoff_ip_transit": [self.handoff]}},
            0,
            "Global/USA/San Jose/BLDG23",
        )
        self.manager.update_ip_l3_handoff([None], payload, "192.0.2.10", {}, {})
        self.manager.get_taskid_post_api_call.assert_called_once_with(
            "sda", "add_fabric_devices_layer3_handoffs_with_ip_transit", {"payload": payload}
        )
        return payload[0]

    def test_explicit_addresses_reach_creation_api_without_pool_selector(self):
        original = deepcopy(self.handoff)
        payload = self.build_and_submit()
        self.assertEqual(payload["localIpAddress"], "204.1.100.5/30")
        self.assertEqual(payload["remoteIpAddress"], "204.1.100.6/30")
        self.assertEqual(payload["interfaceName"], "HundredGigE1/0/1")
        self.assertEqual(payload["vlanId"], 440)
        self.assertNotIn("externalConnectivityIpPoolName", payload)
        self.manager.check_valid_reserved_pool.assert_not_called()
        self.assertEqual(self.handoff, original)

    def test_captured_ipv6_pair_reaches_creation_api(self):
        self.handoff.update(
            local_ipv6_address="2001:db8::1/126",
            remote_ipv6_address="2001:db8::2/126",
        )
        payload = self.build_and_submit()
        self.assertEqual(payload["localIpv6Address"], "2001:db8::1/126")
        self.assertEqual(payload["remoteIpv6Address"], "2001:db8::2/126")
        self.assertEqual(payload["localIpAddress"], "204.1.100.5/30")
        self.assertNotIn("externalConnectivityIpPoolName", payload)

    def test_pool_selector_would_override_captured_addresses(self):
        self.handoff["external_connectivity_ip_pool_name"] = "TB4_SJ_AP"
        payload = self.build_and_submit()
        self.assertEqual(payload["externalConnectivityIpPoolName"], "TB4_SJ_AP")
        self.assertNotIn("localIpAddress", payload)
        self.assertNotIn("remoteIpAddress", payload)
