# Ansible Role: `switch_refresh_sda_fabric_border`

Refresh pure SDA fabric border devices while preserving their complete border
handoff configuration. The role deliberately uses a break-before-make
cutover: Catalyst Center cannot assign the captured handoff to the replacement
until the old border has been removed.

The existing `sda_fabric_devices_config_generator` role is the authoritative
source for capture and readback. A generator failure stops the run. This role
does not modify the generator and does not call direct handoff information
modules.

## Phases

`prepare` is non-destructive. It resolves and captures each old border,
onboards the replacement, assigns inventory role `BORDER_ROUTER`, provisions
it, and adds it to the fabric as a `BORDER_NODE` with the captured Layer 3
border settings but no handoffs.

Normal `cutover` captures every source again and persists every batch manifest
before the first deletion. Manifest continuation loads and validates the
previously persisted capture instead of guessing intent that may already have
been deleted. Every cutover mode processes one old/new pair at a time:

```text
capture/persist, or load/validate, every manifest
  -> persist deletion_started immediately before source deletion
  -> remove old border from fabric
  -> prove old fabric absence
  -> unprovision old border
  -> delete old border from inventory
  -> prove old inventory absence
  -> apply captured handoffs to replacement
  -> generator readback and exact comparison
  -> optional hostname transfer
  -> advance to the next pair
```

The role never automatically rolls back a partially transferred handoff.
Recovery is manifest-backed and rolls forward.

## Requirements

- `cisco.catalystcenter` collection and a compatible Catalyst Center SDK
- Python and dependency versions required by the roles called by this role
- Old and replacement devices represented in the same Catalyst Center
- A maintenance window that accounts for the border handoff outage
- A normalized absolute, non-root work directory and, for cutover, a durable
  normalized absolute, non-root manifest directory, both writable by the
  Ansible controller account. Paths cannot contain dot, dot-dot, or repeated
  slash components; an existing target must be a directory and not a symlink.
- Secrets supplied through Ansible Vault or another secret store

Only pure `BORDER_NODE` sources are supported in the first implementation.
Combined border/control-plane/edge devices are rejected.

## Controls

Prepare:

```yaml
switch_refresh_sda_fabric_border_phase: prepare
switch_refresh_sda_fabric_border_cutover_approved: false
switch_refresh_sda_fabric_border_resume_from_manifest: false
```

Normal cutover:

```yaml
switch_refresh_sda_fabric_border_phase: cutover
switch_refresh_sda_fabric_border_cutover_approved: true
switch_refresh_sda_fabric_border_resume_from_manifest: false
switch_refresh_sda_fabric_border_manifest_dir: /var/lib/catalystcenter/border-refresh
```

Approved continuation after a destructive cutover stopped:

```yaml
switch_refresh_sda_fabric_border_phase: cutover
switch_refresh_sda_fabric_border_cutover_approved: true
switch_refresh_sda_fabric_border_resume_from_manifest: true
switch_refresh_sda_fabric_border_manifest_dir: /var/lib/catalystcenter/border-refresh
```

Non-destructive roll-forward, permitted only after the old device is already
fully absent:

```yaml
switch_refresh_sda_fabric_border_phase: cutover
switch_refresh_sda_fabric_border_cutover_approved: false
switch_refresh_sda_fabric_border_resume_from_manifest: true
switch_refresh_sda_fabric_border_manifest_dir: /var/lib/catalystcenter/border-refresh
```

Both safety overrides default to `false`:

```yaml
switch_refresh_sda_fabric_border_allow_single_border_outage: false
switch_refresh_sda_fabric_border_hostname_transfer_enabled: false
```

These control combinations define four public modes: prepare, normal cutover,
approved manifest continuation, and non-destructive manifest resume. Each of
the three cutover modes runs under one exclusive controller-scoped lock on the
local Ansible control node. The lock is acquired before cutover preflight and
held through all serial batch execution, so a competing invocation for the
same Catalyst Center host and port fails before preflight or deletion. The
lock is local to one control node; operators must prevent concurrent cutovers
from different control nodes themselves. A control-node crash or forced
termination can leave a stale directory under
`/tmp/catalystcenter-switch-refresh-sda-border-*.lock`. Remove only the exact
stale directory, and only after proving that no cutover for that controller is
active on any control node.

When optional hostname transfer is enabled, the update is submitted through
the existing `lan_automation` role. Hostname ownership and post-update
readback use `cisco.catalystcenter.network_device_info` directly; these are
inventory identity checks, not direct border-handoff reads.

## Batch input

```yaml
switch_refresh_sda_fabric_border_batches:
  - name: blr-border-refresh
    fabric_site_name_hierarchy: Global/India/BLR/Fabric
    onboarding_method: discovery

    new_devices:
      device_ips:
        - "192.0.2.20"

    device_mapping:
      - old:
          serial_number: OLD-BORDER-01
        new_device_management_ip: "192.0.2.20"
        handoff_interface_mappings:
          - source_interface_name: FortyGigabitEthernet1/1/1
            destination_interface_name: HundredGigE1/0/1
          - source_interface_name: FortyGigabitEthernet1/1/2
            destination_interface_name: HundredGigE1/0/2
```

`new_devices.device_ips` is authoritative. Every IP must have one mapping.
`old` accepts exactly one of `management_ip`, `hostname`, `serial_number`, or
`mac_address`. Every interface used by a captured Layer 2 or IP-transit
handoff must be explicitly mapped, including unchanged interface names.
SDA-transit handoffs have no interface mapping.

Set `onboarding_method` to `discovery` or `lan_automation`. A Discovery batch
can use the generated configuration or provide `new_devices.discovery_config`.
A LAN Automation batch supplies `new_devices.lan_automation_config`. Complete
custom inventory and provisioning configurations may be supplied under
`new_devices.inventory_config` and `new_devices.provision_config`; every custom
configuration must cover exactly the replacement IP set.

## Mandatory safety checks

- Valid execution mode and explicit approval for every destructive action
- Safe work/manifest paths and exclusive local cutover lock ownership
- Unique batch names, replacement IPs, old selectors, and resolved old devices
- Exact old-selector resolution with stable UUID and serial identity
- Exact generator capture for the requested fabric, device, and pure border role
- Complete source-to-destination interface mapping
- Replay-safe IP-transit handoffs; a non-empty external-connectivity pool is
  rejected because replay could reallocate the captured peer addresses
- Manager-compatible priority handling: default readback priority `10` is
  omitted from mutation payloads, while explicit priorities `1..9` are kept
- Replacement inventory identity, reachability, and destination interfaces
- Replacement base fabric configuration contains no handoff before cutover
- All cutover manifests are protected and validated before the first deletion
- Fresh normal cutover never overwrites an existing manifest
- Old fabric and inventory absence before handoff apply; a workflow-reported
  inventory absence is confirmed fail-closed by direct UUID, serial, and
  management-IP reads
- Exact generator readback after handoff apply

By default, an operational peer is another border outside the current old/new
pair that has a non-empty handoff in the site-wide generator result and is
reported by inventory as Managed and either Reachable or Ping Reachable. A
handoff-free prepared replacement does not count, while a replacement whose
handoff was verified by an earlier serial mapping can count. Explicitly set
`switch_refresh_sda_fabric_border_allow_single_border_outage: true` only when
the outage of the site's last operational border is understood and approved.

## Manifest recovery

Each batch has one mode-`0600` manifest containing controller and fabric scope,
an input fingerprint, immutable old/new identities, the original generated
configuration, the transformed replacement configuration, and per-mapping
state. Each entry also has an `immutable_payload_fingerprint` over the old and
new identities (including the captured old hostname), old selector, interface
mappings, original/base/expected configurations, source configuration
fingerprint, and source handoff-interface list. All batch manifests are written
before any old device is removed in normal cutover. Those freshly persisted
manifests are then read back from disk and revalidated before deletion is
permitted. Immediately before an old fabric removal is submitted, the entry is
atomically advanced from `captured` to `deletion_started`.

Per-mapping progress is monotonic:

```text
captured -> deletion_started -> old_deleted -> handoff_verified -> complete
```

On resume, the role reloads the manifest, revalidates its scope and
fingerprint, and observes current state. Live state normally determines work,
but `deletion_started` is a durable intent boundary: approved continuation can
retry an interrupted old-fabric deletion when the remaining old configuration
has the same roles and base settings and only captured handoffs are missing.
Normal cutover will not replace an existing manifest, and non-destructive
resume cannot use this exception. Missing, corrupt, permissive, mismatched, or
symlinked manifests fail closed.

## Example playbooks

- `playbooks/switch_refresh_sda_fabric_border_prepare.yml`
- `playbooks/switch_refresh_sda_fabric_border_cutover.yml`
- `playbooks/vars/switch_refresh_sda_fabric_border_usecase.yml`

See [FLOW_GUIDE.md](FLOW_GUIDE.md) for the complete state model, data
transformation, recovery cases, role calls, and operational procedure.
