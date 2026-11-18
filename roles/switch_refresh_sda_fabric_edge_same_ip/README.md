# Ansible role: switch_refresh_sda_fabric_edge_same_ip

Replace SDA fabric edge switches while reusing their management IPs. Run the
role in two explicit phases: capture and remove the old devices, then restore
configuration onto new physical devices after the hardware/IP handoff.

The role supports `onboarding_method: lan_automation` and
`onboarding_method: discovery`. Every `device_mapping` entry requires a
`management_ip` and a `replacement_serial_number`, for both methods. The IP is
used to capture the old device and to identify its replacement during restore.
There is no separate replacement IP list in the new input format.

## Execution flow

1. Run `capture_and_remove`. All batch inputs are validated first. The role
   captures and validates every batch before any old-device mutation, then
   checks generated seed claims and physical identities across batches.
2. For each batch, remove original host-port configuration, fabric membership,
   provisioning, and remaining inventory records, in that order. Verify old
   UUID fabric memberships and inventory absence by IP and serial. Save the
   `awaiting_ip_release` checkpoint.
3. Complete the customer handoff: isolate/remove old hardware, resolve individual
   address allocations in Catalyst Center/IPAM, and prepare/connect replacements.
4. Run `restore` with the same mappings and snapshot directory. Onboard all
   replacements using the selected method, verify serial/IP/UUID and inventory
   readiness, restore inventory roles, provisioning, fabric membership, and
   mapped host ports. Independently verify the complete restored batch.

Each workflow manager receives the complete relevant device set for a batch.
Batches execute in list order after all captures have passed preflight. A
maintenance outage is required because the old devices must stop using their
addresses before replacements can reuse them. For different replacement IPs,
use `switch_refresh_sda_fabric_edge`.

## Requirements

- Ansible Core 2.16+, Python 3.12+, `catalystcentersdk >= 3.2.3.0.0`, PyYAML,
  the `cisco.catalystcenter` collection, and `ansible.utils`.
- Catalyst Center 2.3.7.9 or later with compatible SDK/API support.
- Pure `EDGE_NODE` fabric devices with inventory role `ACCESS`. Existing fabric
  design, virtual networks, pools, and site settings remain available.
- One play host, normally `localhost` with `connection: local`. Controller calls
  and persistent snapshots run on the Ansible controller. Check mode is rejected;
  use `--syntax-check` and the offline tests for controller-free verification.
- A persistent absolute snapshot directory writable by the controller account.
  Use a separate directory per refresh/change.
- Real replacement serials must be supplied before phase 1, must differ from
  every old device, and must be unique across batches. Replacement devices must
  not already appear in inventory during the removal preflight.

The role does not release individual IP allocations, reset seed interfaces,
factory-reset hardware, or restore custom CLI and unrelated template settings.

## Inputs

The complete example is
[`playbooks/vars/switch_refresh_sda_fabric_edge_same_ip_usecase.yml`](../../playbooks/vars/switch_refresh_sda_fabric_edge_same_ip_usecase.yml).
Keep only the batches applicable to your deployment.

```yaml
switch_refresh_sda_fabric_edge_same_ip_snapshot_dir: /var/lib/catalystcenter/edge-refresh/change-123
switch_refresh_sda_fabric_edge_same_ip_batches:
  - name: building-lan-refresh
    fabric_site_name_hierarchy: Global/Region/Building
    onboarding_method: lan_automation
    # Optional: runtime input, never persisted in a new snapshot.
    # new_devices:
    #   isis_domain_pwd: "{{ vault_lan_automation_isis_domain_pwd }}"
    device_mapping:
      - management_ip: "192.0.2.10"
        replacement_serial_number: NEW-SERIAL-01
        interface_migration:
          only_mapped: false
          port_assignments:
            - source: GigabitEthernet1/0/5
              destination: GigabitEthernet1/0/10
          port_channels: []
      - management_ip: "192.0.2.11"
        replacement_serial_number: NEW-SERIAL-02
```

`interface_migration` is optional. Omitting it preserves original interface
names. With `only_mapped: false`, specified interfaces are renamed and unlisted
interfaces remain unchanged. With `only_mapped: true`, only explicitly mapped
assignments/channel members are restored; at least one mapping is required.
Duplicate or conflicting destinations and nonexistent source interfaces are
rejected. Original cleanup configuration is always captured separately and
removes the complete original port configuration.

`allow_empty_host_port_config: true` permits verified empty host-port captures.
It never permits missing inventory, provisioning, fabric, or LAN automation data.

### LAN automation

The role invokes `cisco.catalystcenter.lan_automation_config_generator` before
removal, using IPs derived from `device_mapping` and the batch site. It maps
placeholder serials to each entry's required `replacement_serial_number`,
validates complete target coverage, and saves the resulting configuration in
`manifest.json` and `lan_automation.yml`. Restore loads the protected snapshot;
it never regenerates configuration from deleted devices.

The generator requires stopped, inactive session history for the original
physical devices in their site ancestry. A source without matching LAN automation
history fails before removal. Seeds, interfaces, and pools must remain available;
seed devices cannot be targets of this refresh. Different batches cannot claim
the same primary seed port; put coupled devices in one batch.

LAN discovery placement is checked against each captured provisioning site,
including floors below the fabric target. Captured hostnames, reused management
IPs, pools, interfaces, and supported session settings are retained. Sessions
use `launch_and_wait: true`; the role additionally waits for zero active LAN
sessions and verifies managed/reachable replacement inventory.

After phase 1, prepare seed interfaces and resynchronize seeds as needed, and
connect new switches in the required PnP state. Supply any required IS-IS
password through `new_devices.isis_domain_pwd` on restore. It applies to all
captured sessions in that batch and is not written to new snapshots. The status
API cannot recover that password. Use separate batches with non-conflicting
seed ports if different runtime passwords are needed.

### Discovery

Discovery needs no historical LAN automation configuration. After phase 1, the
customer configures the replacements with the reused management IPs, reachable
routing, the old hostnames, and working SSH/SNMP settings.

```yaml
onboarding_method: discovery
new_devices:
  discovery:
    protocol_order: ssh
    retry: 2
    use_global_credentials: false
    discovery_specific_credentials:
      cli_credentials_list:
        - username: "{{ vault_shared_cli_username }}"
          password: "{{ vault_shared_cli_password }}"
          enable_password: "{{ vault_shared_enable_password }}"
      snmp_v3_credential:
        username: "{{ vault_snmp_username }}"
        snmp_mode: AUTHPRIV
        auth_type: SHA
        auth_password: "{{ vault_snmp_auth_password }}"
        privacy_type: AES128
        privacy_password: "{{ vault_snmp_privacy_password }}"
device_mapping:
  - management_ip: "192.0.2.20"
    replacement_serial_number: NEW-SERIAL-20
  - management_ip: "192.0.2.21"
    replacement_serial_number: NEW-SERIAL-21
    discovery:
      discovery_specific_credentials:
        cli_credentials_list:
          - username: "{{ vault_device_21_username }}"
            password: "{{ vault_device_21_password }}"
```

Per-device `discovery` settings override batch settings. Credential overrides
replace the complete corresponding credential type; CLI lists are replaced,
not concatenated. Other types remain inherited. The module's CLI, SNMPv2,
SNMPv3, HTTP, and NETCONF credential structures are supported.

For existing Catalyst Center global credentials, set
`new_devices.discovery.use_global_credentials: true`. Optional
`global_credentials` selectors use the Discovery module's schema. The same
selection can be overridden per device. When omitted, global credentials are
used unless explicit discovery-specific credentials are supplied. Explicit
`use_global_credentials: false` requires effective device credentials.
When switching a device from batch global credentials to device-specific
credentials, also set `use_global_credentials: false` on that device.

The role generates a uniquely named `SINGLE` discovery job per mapped IP and
passes all jobs to the existing `cisco.catalystcenter.discovery` role in one
invocation. Discovery creates inventory records; the shared restore stages then
validate replacement serials and apply the captured intent. Discovery is skipped
on a resumed run when every intended replacement is already managed/reachable.
Credentials remain runtime inputs and may rotate between phases without changing
the immutable physical device mapping. Protect input credentials with Vault.

## Captured configuration

| Capture | Purpose | Apply |
|---|---|---|
| `inventory_playbook_config_generator` | Inventory role `ACCESS` | `inventory_workflow_manager` |
| `provision_playbook_config_generator` | Wired provisioning and exact sites | `provision_workflow_manager` |
| `sda_fabric_devices_playbook_config_generator` | Pure edge fabric membership | `sda_fabric_devices_workflow_manager` |
| `sda_host_port_onboarding_playbook_config_generator` | Original ports/channels | Delete with `sda_host_port_onboarding_workflow_manager` |
| `sda_host_port_migration_playbook_config_generator` | Mapped replacement ports/channels | Merge with `sda_host_port_onboarding_workflow_manager` |
| `lan_automation_config_generator` role, LAN method only | Replacement LAN automation input | `lan_automation_workflow_manager` |

The five common native workflow payloads remain separate from onboarding data.
The migration generator runs before deletion while old devices are available.
Inventory restoration sets captured roles; it does not re-add records already
created by LAN automation or discovery. If unprovisioning already removes
inventory on the controller version, redundant inventory deletion is skipped.

## Persistence and recovery

Each batch directory contains `inventory.yml`, `provision.yml`, `fabric.yml`,
`cleanup.yml`, `restore.yml`, and `manifest.json`. LAN captures also produce
`lan_automation.yml`. Directories are `0700`; saved files are `0600`.

New-format inputs create schema-3 manifests. The immutable checksum binds the
controller, batch input fingerprint, physical IP/serial mapping, fabric ID,
original identities, all five workflow payloads, and onboarding method/config.
Discovery credentials and IS-IS passwords are excluded from new persisted data.
A fabric recreated at the same hierarchy cannot silently replace the saved ID.
Fabric sites/zones are resolved independently of old inventory, and old UUID
membership checks include both `fabricId` and `networkDeviceId`.

A `.lock` directory prevents simultaneous runs against the same snapshot root.
Normal completion and task failure release it. After an interrupted Ansible
process, confirm that no run remains active before removing a stale lock.

Resume using the same batch names, site, mappings, replacement serials, onboarding
method, and snapshot directory. Existing valid manifests are loaded instead of
recapturing partially removed devices. Verified checkpoints advance monotonically:
`captured`, `ports_removed`, `fabric_removed`, `old_inventory_absent`,
`awaiting_ip_release`, `restore_started`, `onboarded`, `inventory_ready`,
`provisioned`, `fabric_added`, `ports_restored`, `complete`.

Once restoration starts, teardown is permanently disabled for that snapshot.
Replacement identity is verified by expected serial and a UUID distinct from the
old device; subsequent runs also enforce any recorded replacement UUID. Successful
completed runs still verify provisioning, fabric, inventory, and host ports.
There is no automatic rollback of an interrupted physical replacement.

Legacy manual inputs containing `new_devices.device_ips` and
`new_devices.lan_automation_config` remain accepted for existing workflows and
schema-1/schema-2 snapshots. Keep those original inputs unchanged when resuming;
legacy checksums and the `lan_automated` checkpoint remain supported. New-format
inputs must not be substituted into an existing legacy snapshot. If an earlier
run stopped after inventory deletion, reuse its snapshot and rerun the phase;
fabric resolution and UUID checks do not require old inventory to exist.

## Controls and execution

| Variable suffix (prefix: `switch_refresh_sda_fabric_edge_same_ip_`) | Default |
|---|---|
| `phase` | `capture_and_remove` |
| `snapshot_dir` | Empty; required absolute path |
| `batches` | Empty; required nonempty list |
| `config_verify` | `true` |
| `timeout` | `1200` seconds |
| `poll_interval` | `10` seconds |
| `lan_automation_timeout` | `604800` seconds |
| `lan_automation_poll_interval` | `30` seconds |

Common `catalystcenter_*` connection variables apply to both methods. Workflow
calls suppress task output and disable SDK/module debug and file logging.
Independent role postconditions remain active even with `config_verify: false`.

The provided playbooks use the same example vars file:

```bash
ansible-playbook -i localhost, \
  playbooks/switch_refresh_sda_fabric_edge_same_ip_capture_and_remove.yml \
  -e @/secure/path/catalystcenter-vault.yml --ask-vault-pass

# Complete the customer handoff before starting restore.
ansible-playbook -i localhost, \
  playbooks/switch_refresh_sda_fabric_edge_same_ip_restore.yml \
  -e @/secure/path/catalystcenter-vault.yml --ask-vault-pass
```

Selecting `capture_and_remove` authorizes destructive removal after verified
capture. Selecting `restore` means the customer handoff has been completed.
There is no interactive pause inside the role between phases.

## Scope

Only supported Catalyst Center intent is captured. Custom CLI, deployed template
parameters, tags, multicast-RP dependencies, software-image preparation, and
combined fabric roles require separate handling. Keep independent device backups
for those features. Fabric-zone targets require complete support from every
capture generator; unsupported or incomplete captures fail before removal.

GPL-3.0-or-later.
