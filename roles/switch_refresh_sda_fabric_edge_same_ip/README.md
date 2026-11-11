# Ansible Role: switch_refresh_sda_fabric_edge_same_ip

Refresh SDA fabric edge switches while reusing each old switch's management IP.
The role captures the old devices' supported Catalyst Center configuration,
removes the old devices, and restores their configuration onto replacements
onboarded through LAN automation.

This workflow requires a maintenance outage. The old devices are removed before
the replacements can use their addresses. Use
`switch_refresh_sda_fabric_edge` for a refresh in which replacements have
different management IPs and can be prepared before the old devices are removed.

## Phases and batch execution

Run the same input in two separate invocations:

1. `capture_and_remove` captures configuration and old device identities,
   validates and saves the snapshots, removes original host-port configuration,
   removes the old devices from the fabric, and ensures they are removed from
   provisioning and inventory.
2. `restore` loads the saved configuration, LAN automates the replacement
   serial/IP pairs, verifies replacement identity and inventory readiness,
   restores provisioning and fabric membership, and applies the saved port
   mappings.

Between the two invocations, the customer isolates/removes the old switches,
releases their individual address allocations in Catalyst Center/IPAM, prepares
the seed ports, and connects the replacements in the required PnP initial state.
Selecting `restore` means that this handoff has been completed. Inventory
deletion alone does not prove an address is available or prevent an old switch
from continuing to use it.

Each generator or workflow manager receives the complete relevant device set
for one batch in a single invocation. A batch must complete a stage before it
advances to the next stage. Separate batches run in list order. Put switches
that should advance together in the same batch; internal API scheduling belongs
to the called modules.

```text
capture_and_remove
  capture all old devices and configuration
  -> generate and save all mapped replacement configuration
  -> validate and persist the complete snapshot
  -> delete all original host-port configuration
  -> remove all old fabric memberships
  -> unprovision and ensure all old inventory records are absent
  -> awaiting_ip_release

customer IP and hardware handoff

restore
  load the snapshot
  -> LAN automate all replacement serial/IP pairs
  -> verify all replacement identities and inventory readiness
  -> restore inventory roles and provisioning
  -> restore fabric membership
  -> restore mapped host-port configuration
  -> verify the restored configuration
```

## Requirements

- Ansible Core 2.16 or later, the `cisco.catalystcenter` collection, and
  `ansible.utils` for the information-module action plugins.
- Python 3.12 or later and `catalystcentersdk >= 3.2.3.0.0` on the controller.
- Catalyst Center 2.3.7.9 or later, with the required SDK/API compatibility.
- Existing fabric sites and pure `EDGE_NODE` devices with inventory role
  `ACCESS`. Existing fabric design, virtual networks, pools, and site settings
  remain available throughout the refresh.
- A persistent absolute snapshot directory writable by the Ansible controller
  account. Use a unique directory for each refresh/change.
- Replacement serial numbers, LAN automation seeds/ports/pools, and any required
  port mappings supplied before the capture phase.
- Each reused management IP is allocatable from an eligible pool at the
  discovery/device site before restoration begins.

Prepare reused seed interfaces for LAN automation and resynchronize the seed
devices after making changes. The role does not reset seed ports, factory-reset
replacement switches, delete shared pools, or release individual IP allocations.

Run the role once on a single play host, normally `localhost` with
`connection: local`. Its files and module calls run on the Ansible controller.

## Role variables

| Variable | Default | Purpose |
|---|---|---|
| `switch_refresh_sda_fabric_edge_same_ip_phase` | `capture_and_remove` | Selects removal or restoration. |
| `switch_refresh_sda_fabric_edge_same_ip_snapshot_dir` | Empty; required | Persistent absolute directory for snapshots and progress. |
| `switch_refresh_sda_fabric_edge_same_ip_batches` | `[]`; required | Complete batch definitions. |
| `switch_refresh_sda_fabric_edge_same_ip_config_verify` | `true` | Enables workflow-manager verification in addition to role postconditions. |
| `switch_refresh_sda_fabric_edge_same_ip_timeout` | `1200` | Timeout in seconds for inventory/provisioning/postcondition polling. |
| `switch_refresh_sda_fabric_edge_same_ip_poll_interval` | `10` | Polling interval in seconds. |
| `switch_refresh_sda_fabric_edge_same_ip_lan_automation_timeout` | `604800` | LAN automation completion timeout in seconds. |
| `switch_refresh_sda_fabric_edge_same_ip_lan_automation_poll_interval` | `30` | LAN automation completion polling interval in seconds. |

Connection settings use the common `catalystcenter_host`,
`catalystcenter_username`, `catalystcenter_password`, `catalystcenter_port`,
`catalystcenter_verify`, and `catalystcenter_version` variables. Workflow calls
suppress task output and module debug/file logging.

## Input

The only supported input is
`switch_refresh_sda_fabric_edge_same_ip_batches`. Each batch has:

- A unique `name` suitable for a directory name.
- The complete `fabric_site_name_hierarchy`.
- `onboarding_method: lan_automation` (also the default).
- `new_devices.device_ips`, the unique management IPs being reused.
- `new_devices.lan_automation_config`, containing the replacement serial/IP
  pairs and `launch_and_wait: true`.
- `device_mapping`, with exactly one entry for each IP in `device_ips`.

Each `device_mapping` entry contains one `management_ip`, used as both the
source and destination IP for the migration generator. There are no redundant
`old` or `new` sections. The old UUID and serial are obtained from the live
inventory and persisted automatically; the replacement serial is supplied in
LAN automation's `discovery_devices`.

```yaml
switch_refresh_sda_fabric_edge_same_ip_phase: capture_and_remove
switch_refresh_sda_fabric_edge_same_ip_snapshot_dir: /var/lib/catalystcenter/edge-refresh/change-123

switch_refresh_sda_fabric_edge_same_ip_batches:
  - name: building-edge-refresh
    fabric_site_name_hierarchy: Global/Region/Building
    onboarding_method: lan_automation
    new_devices:
      device_ips: ["192.0.2.10", "192.0.2.11"]
      lan_automation_config:
        - lan_automation:
            discovered_device_site_name_hierarchy: Global/Region/Building
            primary_device_management_ip_address: "198.51.100.10"
            primary_device_interface_names:
              - GigabitEthernet1/0/1
              - GigabitEthernet1/0/2
            ip_pools:
              - ip_pool_name: LAN_AUTO_MAIN
                ip_pool_role: MAIN_POOL
            discovery_devices:
              - device_serial_number: NEW-SERIAL-01
                device_management_ip_address: "192.0.2.10"
              - device_serial_number: NEW-SERIAL-02
                device_management_ip_address: "192.0.2.11"
            launch_and_wait: true
    device_mapping:
      - management_ip: "192.0.2.10"
        interface_migration:
          only_mapped: false
          port_assignments:
            - source: GigabitEthernet1/0/5
              destination: GigabitEthernet1/0/10
          port_channels: []
      - management_ip: "192.0.2.11"
        interface_migration:
          only_mapped: false
          port_assignments: []
          port_channels:
            - source: GigabitEthernet1/0/47
              destination: TenGigabitEthernet1/1/1
```

`interface_migration` is optional. Its defaults preserve interface names for
1:1 restoration. With `only_mapped: false`, listed interfaces are renamed and
unlisted source interfaces retain their names. With `only_mapped: true`, only
the explicitly mapped assignments and port-channel members are restored; at
least one mapping is required. Old-device cleanup always removes the complete
captured original configuration.

Keep port-assignment mappings separate from port-channel member mappings.
Duplicate or conflicting destinations are rejected. The role also rejects
duplicate IPs, replacement serials, and conflicting seed-port claims across
batches before execution.

The LAN automation discovery site may be the fabric target or a complete
ancestor of it. The role preserves each device's captured provisioning site,
which may be the fabric target or a floor below it. A discovery device's
optional `device_site_name_hierarchy` must match that captured site; when
omitted, the role fills it from the provisioning snapshot. When
`device_host_name` is omitted, the saved old hostname supplies the replacement
hostname.

A device with no host-port configuration may be handled by explicitly setting
`allow_empty_host_port_config: true` on its batch. This permits a verified empty
host-port snapshot; it does not permit incomplete inventory, provisioning, or
fabric captures.

## Configuration modules

All names below are in the `cisco.catalystcenter` collection.

| Capture during phase 1 | Purpose | Apply during phase 2 |
|---|---|---|
| `inventory_playbook_config_generator` | Inventory role | `inventory_workflow_manager` |
| `provision_playbook_config_generator` | Wired provisioning/site assignment | `provision_workflow_manager` |
| `sda_fabric_devices_playbook_config_generator` | Fabric membership | `sda_fabric_devices_workflow_manager` |
| `sda_host_port_onboarding_playbook_config_generator` | Original host-port configuration for cleanup | Used during phase 1 with `sda_host_port_onboarding_workflow_manager`, `state: deleted` |
| `sda_host_port_migration_playbook_config_generator` | Mapped replacement port assignments/channels | `sda_host_port_onboarding_workflow_manager`, `state: merged` |

The migration generator runs while the old devices are still available. Its
mapped output contains replacement interface names and is saved for phase 2.
It is never used to delete the old devices' original ports.

Removal uses the host-port, fabric-device, provisioning, and inventory workflow
managers in that order. On controller versions where provisioning deletion also
removes inventory, the final inventory operation only targets devices that
remain present. LAN automation already creates replacement inventory records;
the inventory stage ensures the captured role/settings rather than adding the
devices again.

## Persistent state and recovery

Each batch has its own snapshot directory. Directories use mode `0700` and
saved configuration/manifest files use mode `0600`. The manifest binds the
snapshot to the controller and batch inputs and records payload
checksums, old identities, replacement identities, and progress checkpoints.

New snapshots use schema 2 and include the resolved fabric ID in the immutable
capture checksum. Each phase resolves the saved hierarchy through the site and
fabric-site APIs (with a fabric-zone fallback) and checks it against that ID.
A fabric recreated at the same hierarchy cannot silently replace the captured
fabric scope. UUID membership queries always pass both `fabricId` and the
captured `networkDeviceId`; their query contract is checked before old-device
mutations, and membership absence is checked independently of inventory.

Schema-1 snapshots created by earlier versions remain valid with their original
checksums. The role resolves their fabric ID from the saved hierarchy even when
all old inventory records have already been deleted. If an earlier run stopped
at the old-UUID verification task, retain the snapshot directory and unchanged
inputs, install this fix, and rerun `capture_and_remove`. It resumes verification
without recapturing or deleting already-absent devices, then reaches
`awaiting_ip_release`. No manual snapshot edits or regeneration are required.

A `.lock` directory under `snapshot_dir` prevents simultaneous runs against the
same snapshots. Normal completion or task failure removes the lock. If the
Ansible process is interrupted, a lock may remain. Confirm that no run is still
active before removing that stale lock and resuming.

All required captures must pass validation before the first deletion. The role
keeps original cleanup configuration and mapped restoration configuration
separate. Repeated capture invocations load an existing valid manifest rather
than overwriting the only recovery source with partial live state.

Resume a failed phase with the same inputs and snapshot directory. Completed
checkpoints are preserved, and current device identity is checked before
destructive operations. A reused IP that belongs to a different UUID/serial is
not accepted as the old device. Once restoration has started,
`capture_and_remove` cannot run against that snapshot.

Restoration reads the saved payloads; it does not attempt to rediscover the
deleted old device's configuration. Keep the snapshot after successful
completion. Workflow-manager operations are not transactional, so recovery
resumes verified stages and does not automatically roll back an interrupted
hardware replacement.

## Running the examples

The two example playbooks use the same variables file:

- `playbooks/switch_refresh_sda_fabric_edge_same_ip_capture_and_remove.yml`
- `playbooks/switch_refresh_sda_fabric_edge_same_ip_restore.yml`
- `playbooks/vars/switch_refresh_sda_fabric_edge_same_ip_usecase.yml`

Edit the example device/site/seed/pool values, choose a persistent snapshot
directory, and supply `vault_catalystcenter_host`,
`vault_catalystcenter_username`, and `vault_catalystcenter_password` through an
encrypted vars file or inventory secret store.

```bash
ansible-playbook -i localhost, \
  playbooks/switch_refresh_sda_fabric_edge_same_ip_capture_and_remove.yml \
  -e @/secure/path/catalystcenter-vault.yml --ask-vault-pass

# Complete the customer IP and hardware handoff before running restoration.
ansible-playbook -i localhost, \
  playbooks/switch_refresh_sda_fabric_edge_same_ip_restore.yml \
  -e @/secure/path/catalystcenter-vault.yml --ask-vault-pass
```

Choosing `capture_and_remove` authorizes the destructive removal phase. Choosing
`restore` starts onboarding after the customer handoff. The role does not wait
inside a long-running interactive pause between these phases.

## Scope

This role restores the supported Catalyst Center intent represented by the
generators above. Custom CLI, previously deployed template parameters, tags,
multicast-RP dependencies, software-image preparation, and combined fabric
roles require separate handling. Keep an independent device configuration
backup when those features are present.

Fabric-zone targets require complete support from every capture generator.
The current fabric-device generator exports fabric sites; an incomplete or
unsupported zone capture fails before removal. The role never substitutes an
empty export for a required device configuration.

Check mode does not execute the two-phase workflow. Use Ansible syntax checking
and the role's offline tests for controller-free verification.

## License

GPL-3.0-or-later
