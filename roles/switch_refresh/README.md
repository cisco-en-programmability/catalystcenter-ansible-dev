# Ansible Role: switch_refresh

This role orchestrates a Catalyst Center switch refresh where an old SDA edge
switch is replaced by a new switch and the host-facing port configuration is
migrated from the old switch to the new switch.

The prepare phase supports stage-oriented batches. A batch onboards all new
devices first, then invokes inventory, provisioning, fabric onboarding, fabric
validation, migration generation, and host onboarding once per stage with the
complete device set. This removes the previous outer loop that completed every
stage for device 1 before starting device 2.

The role is intentionally split into two phases:

1. `prepare`: onboard the new devices through either Discovery or LAN Automation,
   add them to Catalyst Center inventory, set and verify their inventory device
   role, provision them, add them to fabric as edge devices, generate host-port
   migration config from the old devices, and push the combined host onboarding
   config to the new devices.
2. `cleanup_old`: after validation and cutover, delete the old switch port
   assignments and port channels, remove the old switch from fabric, and
   unprovision it, then remove it from Catalyst Center inventory.

## Requirements

- `cisco.catalystcenter` collection installed
- Catalyst Center SDK compatible with this collection
- LAN Automation onboarding additionally requires `ansible.utils`, Catalyst
  Center SDK >= 3.1.6.0.2, and Python >= 3.12 on the Ansible controller
- Old switch must still be present in Catalyst Center during prepare and cleanup
- New switch discovery/provisioning inputs must be supplied by the user

## Important Behavior

- New batch entries use `new_devices.device_ips` as the authoritative target
  list. Optional `discovery_config`, `lan_automation_config`,
  `inventory_config`, `provision_config`, and `fabric_devices_config` values are
  complete stage replacements; they are not deep-merged with generated values.
- Batch execution is fail-fast and stage-gated, not transactional. Workflow
  managers receive the full device set once per stage, but some managers or
  Catalyst Center APIs may internally process individual devices sequentially.
  A stage failure stops later stages for the batch and may leave partial state
  that an idempotent rerun must reconcile.
- Devices that should share prepare-stage workflow calls must be grouped in one
  `switch_refresh_devices` entry. Separate entries remain ordered and
  sequential. Cleanup first resolves the entire old-device mapping set and
  rejects duplicate resolved targets, then cleans up old devices sequentially
  for cutover safety.
- Old-device lookup is deferred until after replacement fabric validation. It
  is used only for host-port migration and the separately gated cleanup phase.
- Existing one-old/one-new entries using `old` and `new` remain supported.
- The new switch may have a different port layout. Provide `interface_mappings`
  when source and destination interface names differ.
- Replacement switch onboarding supports two methods:
  - `discovery`: use the existing `discovery` role to discover a reachable
    replacement switch. This is the default.
  - `lan_automation`: use the existing `lan_automation` role to run Catalyst
    Center LAN Automation, then continue with inventory lookup, provisioning,
    fabric add, and host-port migration.
- LAN Automation onboarding is blocking in this role. Each batch accepts exactly
  one launch-only `lan_automation` entry and requires an explicit boolean
  `launch_and_wait: true` when the role launches LAN Automation.
  Device-update and port-channel entries are rejected because the manager would
  execute them before the external completion barrier. After the manager
  returns, the role waits for Catalyst Center to report zero active LAN
  Automation sessions in two consecutive polls before any inventory,
  provisioning, or fabric workflow is called. This conservative barrier also
  waits for unrelated LAN Automation sessions active on the same controller.
- `switch_refresh_lan_automation_enabled` must remain `true` when
  `onboarding_method` is `lan_automation`; disabling it would bypass the launch
  that the completion barrier is intended to protect.
- Before provisioning, the existing `inventory` role adds or merges the
  replacement switch, then explicitly sets its inventory device role to
  `ACCESS` by default. `network_devices_info` verifies that every expected record
  exists with the expected management IP and inventory role before provisioning
  or fabric onboarding begins. The inventory role update uses Catalyst Center's
  manual role source, so LAN Automation's initial `DISTRIBUTION` classification
  does not block adding the switch as an SDA edge node.
- Adding an absent `NETWORK_DEVICE` through the inventory workflow requires a
  device username and password. Discovery global credentials cannot be read
  back by Ansible, so provide them through Ansible Vault using
  `switch_refresh_inventory_credentials`, batch-level
  `new_devices.inventory_credentials`, or a complete inventory configuration.
- The host-port migration generator handles `port_assignments` and
  `port_channels` only during prepare through the
  `sda_host_port_migration_config_generator` role wrapper. Cleanup uses the
  read-only `sda_host_port_onboarding_config_generator` to retrieve the old
  device payload before passing it to host onboarding with `state: deleted`.
- Fabric membership is validated with the `fabric_devices_info` role after
  adding the replacement switch and after removing the old switch.
- Old and replacement switch inventory details are resolved with the
  `network_devices_info` role. The user can provide hostname, serial number,
  MAC address, or management IP for the old switch.
- Old-switch cleanup is gated by `switch_refresh_cleanup_old: true` and is
  normally run through the separate cleanup playbook.
- After the old switch is unprovisioned, the existing `inventory` role removes
  it from Catalyst Center inventory using its resolved management IP.
- The replacement switch can later take over the old switch identity after
  cutover, but this role uses the current management IPs for Catalyst Center
  operations.

## Role Variables

Connection variables:

- `catalystcenter_host`
- `catalystcenter_username`
- `catalystcenter_password`
- `catalystcenter_verify`
- `catalystcenter_port`
- `catalystcenter_version`
- `catalystcenter_debug`
- `catalystcenter_log_level`
- `catalystcenter_log`

Control variables:

- `switch_refresh_phase`: `prepare`, `cleanup_old`, or `all`
- `switch_refresh_onboarding_method`: replacement onboarding method,
  `discovery` or `lan_automation`
- `switch_refresh_cleanup_old`: must be `true` for cleanup
- `switch_refresh_work_dir`: directory for generated migration files
- `switch_refresh_devices`: list of switch refresh entries
- `switch_refresh_inventory_credentials`: default device credentials merged
  into the generated replacement inventory payload
- `switch_refresh_inventory_config_verify`: verify inventory configuration
  after applying it
- `switch_refresh_device_info_lookup_enabled`: resolve device details with
  `network_devices_info`
- `switch_refresh_device_info_lookup_timeout`: inventory lookup timeout
- `switch_refresh_device_info_lookup_retries`: inventory lookup retry count
- `switch_refresh_device_info_lookup_interval`: inventory lookup retry interval
- `switch_refresh_lan_automation_completion_timeout`: maximum manager task/PnP
  wait and polling window for each no-active-session check, in seconds
- `switch_refresh_lan_automation_completion_poll_interval`: delay between
  manager task and LAN Automation active-session polls, in seconds
- `switch_refresh_fabric_validation_enabled`: validate fabric presence/absence
  with `fabric_devices_info`
- `switch_refresh_fabric_validation_timeout`: validation timeout in seconds
- `switch_refresh_fabric_validation_retries`: validation retry count
- `switch_refresh_fabric_validation_interval`: validation retry interval
- `switch_refresh_allow_empty_host_port_config`: allow empty generated host-port
  payloads when set to `true`; an entirely empty batch skips the host-onboarding
  call, while a partial batch still fails coverage validation

Stage toggles:

- `switch_refresh_discovery_enabled`
- `switch_refresh_lan_automation_enabled`
- `switch_refresh_inventory_enabled`
- `switch_refresh_inventory_role_update_enabled`
- `switch_refresh_provision_enabled`
- `switch_refresh_fabric_add_enabled`
- `switch_refresh_host_onboarding_enabled`
- `switch_refresh_cleanup_host_onboarding_enabled`
- `switch_refresh_cleanup_fabric_enabled`
- `switch_refresh_cleanup_unprovision_enabled`
- `switch_refresh_cleanup_inventory_enabled`

## Batch Input Model

Use `new_devices.device_ips` for the replacement-device set and
`device_mapping` only for the old-to-new host-port migration association:

```yaml
switch_refresh_devices:
  - name: sjc-bldg23-edge-refresh
    fabric_site_name_hierarchy: Global/USA/SAN-JOSE/BLDG23
    onboarding_method: discovery

    new_devices:
      device_ips:
        - 10.10.10.20
        - 10.10.10.21

      # Optional complete stage replacements:
      # discovery_config: [...]
      # lan_automation_config: [...]
      # inventory_config: [...]
      # provision_config: [...]
      # fabric_devices_config: [...]

    device_mapping:
      - old_device_hostname: SJ-EDGE-OLD-01.cisco.local
        new_device_management_ip: 10.10.10.20
        interface_mappings:
          - source_interface_name: GigabitEthernet1/0/1
            destination_interface_name: TenGigabitEthernet1/0/1
      - old:
          serial_number: FOC1234ABCD
        new_device_management_ip: 10.10.10.21
        interface_mappings: []
```

`device_mapping` accepts a nested `old` mapping with exactly one of
`management_ip`, `hostname`, `serial_number`, or `mac_address`. For concise
input, the aliases `old_device_management_ip`, `old_device_hostname`,
`old_device_serial_number`, and `old_device_mac_address` are also accepted.

When host onboarding is enabled, mapping destination IPs must be unique and
exactly cover `new_devices.device_ips`. When host onboarding is disabled,
`device_mapping` may be omitted so discovery onboarding can use IP-only input.
This omission applies only to `prepare`; `cleanup_old` always requires a
non-empty `device_mapping` that exactly covers `new_devices.device_ips`.

For minimal Discovery input, the role builds flat workflow-manager
configuration. One device uses `SINGLE`; multiple arbitrary IPs use
`MULTI RANGE` in chunks of eight, the manager's per-entry limit. Inventory uses
one configuration with all IPs, provisioning uses one entry per IP, and fabric
onboarding uses one fabric entry containing every device.

For LAN Automation, provide exactly one shared launch configuration with no more
than 50 discovery devices. Its
`discovery_devices[].device_management_ip_address` set must exactly match
`new_devices.device_ips`, and `launch_and_wait` must be the boolean `true`.

## Legacy Input Model

The original one-old/one-new form remains supported:

```yaml
switch_refresh_devices:
  - name: sjc-edge-01-refresh
    fabric_site_name_hierarchy: Global/USA/SAN-JOSE/BLDG23
    old:
      hostname: SJ-EDGE-OLD.cisco.local
    onboarding_method: discovery
    new:
      management_ip: 10.10.10.20
    interface_mappings:
      - source_interface_name: GigabitEthernet1/0/1
        destination_interface_name: TenGigabitEthernet1/0/1
```

Legacy `old` can use any one of `management_ip`, `hostname`, `serial_number`, or
`mac_address`. The role resolves the old management IP with
`network_devices_info`.

Set `onboarding_method` per entry when the replacement switch or batch should
use a method different from the global `switch_refresh_onboarding_method`.

Configure inventory credentials once, preferably with Ansible Vault, to keep
individual switch entries minimal:

```yaml
switch_refresh_inventory_credentials:
  username: "{{ vault_switch_cli_username }}"
  password: "{{ vault_switch_cli_password }}"
  enable_password: "{{ vault_switch_enable_password }}"
  cli_transport: ssh
  type: NETWORK_DEVICE
```

## Replacement Switch Onboarding Options

### Option 1: Discovery

Use `discovery` when the replacement devices already have reachable management
IPs and Catalyst Center can log in to them. With minimal batch input, the role
builds the flat list accepted by `discovery_workflow_manager`:

```yaml
new_devices:
  device_ips:
    - 10.10.10.20
    - 10.10.10.21
```

The generated workflow payload is equivalent to:

```yaml
discovery_config:
  - discovery_name: switch-refresh-<name>
    discovery_type: MULTI RANGE
    ip_address_list:
      - 10.10.10.20
      - 10.10.10.21
    protocol_order: ssh
    retry: 2
    use_global_credentials: true
```

One IP uses `SINGLE`. Multiple arbitrary IPs use `MULTI RANGE`; because the
manager accepts at most eight ranges per entry, larger batches are divided into
uniquely named eight-IP entries inside the same role call. Pass a flat
`new_devices.discovery_config` list when custom credentials or target-only
Discovery settings are required. It replaces the generated configuration
completely, and its explicit IPs must exactly match `new_devices.device_ips`.
Switch refresh rejects broad CDP, LLDP, CIDR, and multi-device ranges because
they can discover devices outside the authoritative replacement set.

### Option 2: LAN Automation

Use `lan_automation` when the replacement devices should be onboarded through
Catalyst Center LAN Automation instead of normal Discovery. This requires the
full `new_devices.lan_automation_config` expected by the `lan_automation` role.
One LAN Automation launch accepts up to 50 `discovery_devices`; it is not limited
to five. Their `device_management_ip_address` values must exactly match
`new_devices.device_ips`.

`lan_automation_state: merged` and `launch_and_wait: true` are mandatory for
switch refresh; `launch_and_wait` must be nested directly under
`lan_automation`, aligned with `discovery_devices`. The
`discovery_timeout` value is a Catalyst Center server-side timeout in minutes;
it is not the Ansible completion timeout. Configure the latter with
`switch_refresh_lan_automation_completion_timeout` (seconds). The existing LAN
Automation manager continues to handle its normal task and optional PnP flow;
the switch-refresh role then independently waits for the active-session endpoint
to remain empty.

```yaml
switch_refresh_devices:
  - name: sjc-edge-refresh-lan-auto
    fabric_site_name_hierarchy: Global/USA/SAN-JOSE/BLDG23
    onboarding_method: lan_automation
    new_devices:
      device_ips:
        - 204.1.1.13
        - 204.1.1.14
      lan_automation_config:
        - lan_automation:
            discovered_device_site_name_hierarchy: Global/USA/SAN JOSE
            peer_device_management_ip_address: 91.1.1.2
            primary_device_management_ip_address: 204.1.1.4
            primary_device_interface_names:
              - HundredGigE1/0/2
            ip_pools:
              - ip_pool_name: underlay_sub
                ip_pool_role: MAIN_POOL
              - ip_pool_name: underlay_sub_small
                ip_pool_role: PHYSICAL_LINK_POOL
            discovery_level: 5
            discovery_timeout: 40
            discovery_devices:
              - device_serial_number: FXS2429Q0WE
                device_host_name: SR-LAN-9400X-EDGE1
                device_site_name_hierarchy: Global/USA/SAN JOSE/BLD20/BLD20_FLOOR1
                device_management_ip_address: 204.1.1.13
              - device_serial_number: FXS2429Q0WF
                device_host_name: SR-LAN-9400X-EDGE2
                device_site_name_hierarchy: Global/USA/SAN JOSE/BLD20/BLD20_FLOOR1
                device_management_ip_address: 204.1.1.14
            launch_and_wait: true
```

## Inventory Before Provisioning

After Discovery or LAN Automation, the role builds one inventory payload from
`new_devices.device_ips` and `switch_refresh_inventory_credentials`:

```yaml
inventory_config:
  - ip_address_list:
      - 10.10.10.20
      - 10.10.10.21
    username: "{{ vault_switch_cli_username }}"
    password: "{{ vault_switch_cli_password }}"
    enable_password: "{{ vault_switch_enable_password }}"
    cli_transport: ssh
    type: NETWORK_DEVICE
```

The payload is passed to the existing `inventory` role with `state: merged`.
The role then performs a separate idempotent inventory update that sets the
device role to `ACCESS` for all batch IPs. This role is fixed because switch
refresh replacements are SDA edge devices. Finally, one `network_devices_info`
query requires exactly one `ACCESS` record for every expected IP. Provisioning
starts only after the complete set passes that assertion.

Use `new_devices.inventory_credentials` to override the global credentials for
the batch. Use a complete `new_devices.inventory_config` list when devices need
different credentials or the workflow needs additional SNMP, NETCONF, HTTP, or
other fields. Its combined IP set must exactly match `device_ips`. The prepare
flow always enforces the inventory device role as `ACCESS` afterward.

If `new_devices.provision_config` is omitted, the role builds one entry per IP:

```yaml
provision_config:
  - site_name_hierarchy: "{{ fabric_site_name_hierarchy }}"
    management_ip_address: 10.10.10.20
  - site_name_hierarchy: "{{ fabric_site_name_hierarchy }}"
    management_ip_address: 10.10.10.21
```

If `new_devices.fabric_devices_config` is omitted, the role builds one SDA
fabric entry containing every batch IP with `EDGE_NODE`. Complete custom
provision and fabric configurations must exactly cover `device_ips`; custom
fabric entries must also use `fabric_site_name_hierarchy` as `fabric_name`.

Set `provision_site_name_hierarchy` when the provisioning site differs from the
SDA fabric site.

Use separate mappings when port assignment mappings differ from port channel
member mappings:

```yaml
port_assignment_interface_mappings:
  - source_interface_name: GigabitEthernet1/0/10
    destination_interface_name: GigabitEthernet1/0/20
port_channel_interface_mappings:
  - source_interface_name: GigabitEthernet1/0/47
    destination_interface_name: TenGigabitEthernet1/1/1
```

## Example Playbooks

Prepare the replacement switch:

```bash
ansible-playbook playbooks/switch_refresh_prepare.yml
```

Clean up the old switch after validation and cutover:

```bash
ansible-playbook playbooks/switch_refresh_cleanup_old.yml
```

You can also run the role with tags from your own playbook:

```bash
ansible-playbook my_switch_refresh.yml --tags switch_refresh_prepare
ansible-playbook my_switch_refresh.yml --tags switch_refresh_cleanup_old -e switch_refresh_cleanup_old=true
```

See `playbooks/vars/switch_refresh_usecase.yml` for a complete sample use case.
