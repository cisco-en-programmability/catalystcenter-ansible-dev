# Ansible Role: `switch_refresh_sda_fabric_border`

Refresh supported SDA fabric devices while preserving their complete fabric
role set and, when present, border handoff configuration. The role deliberately
uses a break-before-make cutover: Catalyst Center cannot assign a captured
border handoff to the replacement until the old device has been removed.

The existing `sda_fabric_devices_config_generator` role is the authoritative
source for capture and readback. A generator failure stops the run. This role
uses the generator's explicit border capability readback and does not call
direct handoff information modules.

## Phases

`prepare` is non-destructive. It resolves and captures each old device,
including its inventory role and complete fabric `device_roles` list, onboards
the replacement, waits for Catalyst Center inventory collection to finish,
assigns and confirms the captured inventory role, provisions it, and adds it to
the fabric with the same fabric roles. Devices containing `BORDER_NODE` are
prepared with their captured `border_types` (including both `LAYER_2` and
`LAYER_3` for a mixed border) and Layer 3 settings, without handoffs. Catalyst
Center must accept the capability configuration and report those types before
Prepare succeeds.

Normal `cutover` captures every source again and persists every batch manifest
before the first deletion. Manifest continuation loads and validates the
previously persisted capture instead of guessing intent that may already have
been deleted. Every cutover mode processes one old/new pair at a time:

```text
capture/persist, or load/validate, every manifest
  -> verify replacement platform/image inventory and required border capabilities
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
- `ansible.utils` collection version 2.2.0 or later (below 7.0), for address-family validation
- Python and dependency versions required by the roles called by this role
- Old and replacement devices represented in the same Catalyst Center
- A maintenance window that accounts for the border handoff outage
- A normalized absolute, non-root work directory and, for cutover, a durable
  normalized absolute, non-root manifest directory, both writable by the
  Ansible controller account. Paths cannot contain dot, dot-dot, or repeated
  slash components; an existing target must be a directory and not a symlink.
- Secrets supplied through Ansible Vault or another secret store

The supported source fabric role sets are exactly:

- `BORDER_NODE`
- `CONTROL_PLANE_NODE`
- `BORDER_NODE` plus `CONTROL_PLANE_NODE`
- `BORDER_NODE` plus `CONTROL_PLANE_NODE` plus `EDGE_NODE`

The replacement inherits the source role set unchanged. Other role sets are
rejected.

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

Optional hostname transfer defaults to `false`:

```yaml
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
        new:
          management_ip: "192.0.2.20"
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

Neither the inventory role nor fabric `device_roles` is a user input. The old
inventory record and generated fabric configuration are authoritative, and the
workflow requires the replacement to match both before cutover.

Set `onboarding_method` to `discovery` or `lan_automation`. A Discovery batch
can use the generated configuration or provide `new_devices.discovery_config`.
A LAN Automation batch supplies `new_devices.lan_automation_config`. Complete
custom inventory and provisioning configurations may be supplied under
`new_devices.inventory_config` and `new_devices.provision_config`; every custom
configuration must cover exactly the replacement IP set.

## Prepare inventory synchronization

Inventory addition and role assignment are separate prepare stages. The first
inventory payload contains only device-addition and connection fields; a
custom inventory payload cannot set `role`. Prepare
waits until every replacement has exact inventory coverage, completed
collection and management state, wired-device classification, successful
inventory status, stable identity and platform fields, a non-empty device
software version, a non-empty device support level other than `Unsupported`, and `Reachable` or `Ping Reachable`
status. It then groups replacements by the normalized inventory role captured
from their source devices, submits protected role-only payloads, and waits for
every replacement to report its inherited role before provisioning.

Both readiness barriers delegate polling to `network_devices_info`, requiring
`collectionStatus: Managed` and `managementState: Managed`. Polling runs every
10 seconds and uses `switch_refresh_sda_fabric_border_inventory_readiness_timeout`
(default 1200 seconds). The role then validates inventory identity, reachability,
device support, and the expected inventory role before provisioning. A batch
failure or rerun is safe: an existing inventory record and an already assigned
matching role are treated idempotently, while provisioning remains blocked
until both barriers pass.

## Mandatory safety checks

- Valid execution mode and explicit approval for every destructive action
- Safe work/manifest paths and exclusive local cutover lock ownership
- Unique batch names, replacement IPs, old selectors, and resolved old devices
- Exact old-selector resolution with stable UUID and serial identity
- Exact generator capture for the requested fabric, device, and supported role set
- Complete source-to-destination interface mapping
- Address-preserving IP-transit replay using captured local/remote IPv4
  addresses and complete IPv6 pairs when present; pool selectors are omitted
  only from outgoing handoff creation payloads
- Manager-compatible priority handling: default readback priority `10` is
  omitted from mutation payloads, while explicit priorities `1..9` are kept
- Empty `custom_bgp_router_id` overrides are omitted from replacement payloads
  and treated as absent during verification and cutover classification;
  explicit router IDs are preserved and compared
- Replacement inventory identity, reachability, and destination interfaces
- Supported replacement inventory with nonempty platform and software version;
  controller acceptance and explicit capability readback before source deletion
- Replacement base fabric configuration contains no handoff before cutover
- All cutover manifests are protected and validated before the first deletion
- Fresh normal cutover never overwrites an existing manifest
- Old fabric and inventory absence before handoff apply; a workflow-reported
  inventory absence is confirmed fail-closed by direct UUID, serial, and
  management-IP reads
- Exact generator readback after handoff apply

Cutover does not require another operational border or control-plane node
outside the old/replacement pair. A single-border refresh therefore proceeds
after explicit destructive cutover approval and causes a planned border outage
between removal of the old device and verified handoff restoration on the
replacement. Run that cutover in an approved maintenance window.

## Border capability preparation and recovery

For a source with `borderTypes: [LAYER_3, LAYER_2]`, Prepare sends
`borders_settings.border_types: [LAYER_2, LAYER_3]` independently of handoffs.
It verifies that the handoff-free replacement reports both types. A fresh
Cutover rejects a replacement that still reports only `LAYER_3` before deleting
any source; rerun Prepare to enable the missing capability.

Inventory must identify the replacement platform and running software and
report `deviceSupportLevel: Supported`. This inventory status alone does not
prove L2 support. Capability configuration must also succeed in Catalyst
Center, followed by explicit `borderTypes` readback from that controller. The
role does not maintain a platform/software compatibility matrix. Controller
rejection, missing readback, or a type mismatch blocks deletion and handoff
application. The fabric manager repeats capability readback after device
configuration and before any L2, SDA-transit, or IP-transit handoff request.

Manifest continuation can enable missing capabilities using a capability-only
update before replaying handoffs, including recovery from `old_deleted`. For
older manifests without explicit types, the role derives requirements from
the protected source settings and captured handoffs. Runtime copies receive
the derived types; original payloads and fingerprints remain unchanged.
Requirements absent from an older capture cannot be reconstructed. Unexpected
replacement capabilities or other configuration drift require operator review.
Every manifest-backed replacement is checked during batch preflight, and each
mapping is checked again before destructive release or handoff restoration.

## Pool-backed IP-transit handoffs

Prepare accepts existing pool-backed handoffs, including their allocated peer
addresses. The original capture and expected replacement configuration retain
`external_connectivity_ip_pool_name` in the protected manifest. Prepare still
adds only the handoff-free base configuration.

At cutover, the role derives a separate creation payload that removes the pool
selector and supplies the captured local/remote addresses, with mapped
replacement interfaces. This selects the fabric manager's explicit-address
path; supplying the pool name would override the captured addresses. Missing
IPv4 addresses, invalid CIDR syntax or address families, and incomplete IPv6
pairs fail preflight and manifest validation before old-device deletion. IPv4
fields require IPv4 CIDRs with numeric prefixes 0..32; optional IPv6 fields
require IPv6 CIDRs with numeric prefixes 0..128.

Replacement verification and recovery accept the captured pool association or
an absent/empty pool association in generated readback. A different non-empty
pool, changed peer address, or any other changed handoff setting fails
verification. Old-device drift checks remain strict, including the pool name.
The role does not request or guarantee that Catalyst Center retains a pool
association after explicit-address creation. Controller acceptance of the
previous allocation and resulting pool metadata require lab validation.

## Manifest recovery

Each batch has one mode-`0600` manifest containing controller and fabric scope,
an input fingerprint, immutable old/new identities, inherited inventory and
fabric roles, the original generated configuration, the transformed replacement
configuration, and per-mapping state. Each entry also has an
`immutable_payload_fingerprint` over those roles, the old and new identities
(including the captured old hostname), old selector, interface mappings,
original/base/expected configurations, source configuration fingerprint, and
source handoff-interface list. All batch manifests are written before any old
device is removed in normal cutover. Those freshly persisted manifests are then
read back from disk and revalidated before deletion is permitted. Immediately
before an old fabric removal is submitted, the entry is atomically advanced
from `captured` to `deletion_started`.

The initial manifest schema is version 1 and includes inherited inventory and
fabric roles in each immutable device entry.

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

## Offline capability regression

Run with the Python interpreter from an environment containing Ansible and the
collection dependencies:

```sh
python roles/switch_refresh_sda_fabric_border/tests/run_border_capabilities.py
```

The runner creates a temporary collection with simulated controller roles and
executes the real capture, transformation, capability gates, manifest
preflight, and `old_deleted` recovery tasks. It checks mixed L2/L3 handoffs,
controller rejection, stale readback, unsupported inventory, and preservation
of legacy manifest payloads. It makes no controller requests.
