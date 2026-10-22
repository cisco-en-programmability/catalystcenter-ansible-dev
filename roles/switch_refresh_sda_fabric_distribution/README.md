# Ansible Role: switch_refresh_sda_fabric_distribution

This role replaces an existing intermediate distribution switch with a new
switch while keeping the existing fabric border and edge peers in service. The
replacement is assigned inventory role `DISTRIBUTION` and provisioned to the
requested site. It is intentionally not enrolled as an SDA fabric-role device.

The workflow has two explicit runs:

1. `prepare` discovers or onboards the replacement, waits for its inventory
   record, assigns inventory role `DISTRIBUTION`, provisions it to the site,
   and creates its routed links to the existing fabric peers.
2. `cleanup_old` removes the old routed-link configuration, unprovisions the
   old switch, and removes it from inventory. This phase requires explicit
   cleanup approval.

The new and old links must use different peer interfaces so they can coexist
during the validation window. The initial release supports IPv4 pool-based
links only.

## Safety model

Before any Catalyst Center mutation, the role validates every batch and pins
the live inventory UUID, serial number, management IP, and interface evidence
used by the run. It also verifies that:

- every peer is reachable and is an `EDGE_NODE` or `BORDER_NODE` in the
  requested fabric site;
- every declared old physical relationship is exact;
- replacement and peer endpoints are unique and the old and new peer
  interfaces do not overlap;
- each requested link pool exists exactly once at the relevant site, has
  `poolType` `LAN`, and contains an IPv4 address space;
- the replacement has inventory role `DISTRIBUTION`, is provisioned to the
  exact requested site, and has no SDA fabric-device enrollment; and
- before cleanup, the old switch is reachable and provisioned to the same
  requested site. Its inventory role is not used as an eligibility check.

Link creation and deletion always run with LAN Automation verification enabled.
Physical topology is checked before cleanup and the replacement links are
checked again after every cleanup action. The old cable can remain connected;
logical configuration removal is proved by LAN Automation rather than by
requiring the physical neighbor record to disappear.

## Requirements

- `cisco.catalystcenter` and `ansible.utils`
- Python 3.12 or later and Catalyst Center SDK 3.2.3.0.0 or later on the
  Ansible controller (required by the information modules used for the safety
  checks)
- replacement management connectivity and valid onboarding credentials
- the IPv4 LAN pools referenced by `new_link.ip_pool_name` already reserved to
  the batch site in Catalyst Center
- free peer interfaces for all replacement links

Store Catalyst Center and onboarding credentials in Ansible Vault or another
secret store. The role does not ask for a second set of device credentials to
assign the inventory role after onboarding.

## Input schema

```yaml
switch_refresh_sda_fabric_distribution_batches:
  - name: san-jose-distribution-refresh
    fabric_site_name_hierarchy: Global/USA/San Jose
    onboarding_method: discovery

    new_devices:
      device_ips:
        - "192.0.2.20"

    device_mapping:
      - old:
          hostname: SJ-IM.example.test
        new:
          management_ip: "192.0.2.20"
        links:
          - peer_management_ip: "192.0.2.10"
            old_link:
              peer_interface_name: TenGigabitEthernet1/0/1
              distribution_interface_name: TenGigabitEthernet1/0/47
            new_link:
              peer_interface_name: TenGigabitEthernet1/0/3
              distribution_interface_name: TenGigabitEthernet1/0/47
              ip_pool_name: SJ-ROUTED-LINKS

          - peer_management_ip: "192.0.2.11"
            old_link:
              peer_interface_name: TenGigabitEthernet1/0/1
              distribution_interface_name: TenGigabitEthernet1/0/48
            new_link:
              peer_interface_name: TenGigabitEthernet1/0/3
              distribution_interface_name: TenGigabitEthernet1/0/48
              ip_pool_name: SJ-ROUTED-LINKS
```

Each `old` mapping must contain exactly one of `management_ip`, `hostname`,
`serial_number`, or `mac_address`. `new.management_ip` must appear exactly once
in `new_devices.device_ips`. Each mapping requires at least one `links` entry.

Every link requires:

- the fabric peer's canonical IPv4 `peer_management_ip`;
- the exact peer and distribution interface names for `old_link`; and
- the exact spare peer interface, replacement interface, and existing Catalyst
  Center IPv4 LAN `ip_pool_name` for `new_link`.

Interface names must match Catalyst Center inventory spelling. A pool name is
not created by this role; it must already be assigned to the required site.

## Discovery onboarding

The example above generates a bounded Discovery payload. Discovery must place
every replacement in inventory; the role waits for those records before it
assigns `DISTRIBUTION`. A custom `new_devices.discovery_config` can be supplied,
but it must cover exactly the replacement IP set and use globally unique
discovery names.

## LAN Automation onboarding

When the replacement is initially discovered by LAN Automation, provide the
complete launch configuration. It must include one `MAIN_POOL`; each pool used
by a replacement routed link must also be declared as a
`PHYSICAL_LINK_POOL`.

```yaml
onboarding_method: lan_automation
new_devices:
  device_ips:
    - "192.0.2.20"
  lan_automation_config:
    - lan_automation:
        launch_and_wait: true
        primary_device_management_ip_address: "192.0.2.10"
        primary_device_interface_names:
          - TenGigabitEthernet1/0/3
        ip_pools:
          - ip_pool_name: SJ-LAN-AUTOMATION
            ip_pool_role: MAIN_POOL
          - ip_pool_name: SJ-ROUTED-LINKS
            ip_pool_role: PHYSICAL_LINK_POOL
        discovered_device_site_name_hierarchy: Global/USA/San Jose
        discovery_devices:
          - device_serial_number: NEW-DIST-SERIAL
            device_management_ip_address: "192.0.2.20"
            device_site_name_hierarchy: Global/USA/San Jose
```

All supplied onboarding pools are preflighted at the discovery site before LAN
Automation starts.

## Running the two phases

Prepare the replacement first:

```yaml
- name: Prepare replacement distribution switch
  hosts: localhost
  gather_facts: false
  roles:
    - role: cisco.catalystcenter.switch_refresh_sda_fabric_distribution
      vars:
        switch_refresh_sda_fabric_distribution_phase: prepare
        switch_refresh_sda_fabric_distribution_batches: "{{ distribution_refresh_batches }}"
```

After operational checks, run cleanup with explicit approval:

```yaml
- name: Remove old distribution switch
  hosts: localhost
  gather_facts: false
  roles:
    - role: cisco.catalystcenter.switch_refresh_sda_fabric_distribution
      vars:
        switch_refresh_sda_fabric_distribution_phase: cleanup_old
        switch_refresh_sda_fabric_distribution_cleanup_old: true
        switch_refresh_sda_fabric_distribution_batches: "{{ distribution_refresh_batches }}"
```

Useful result facts are
`switch_refresh_sda_fabric_distribution_prepare_results` and
`switch_refresh_sda_fabric_distribution_cleanup_results`.

## Hostname transfer and recovery

Hostname transfer is optional. Before destructive cleanup, the role captures
the live old hostname and immutable old/new identities for every batch, checks
global ownership and uniqueness, and writes mode `0600` manifests inside an
explicit mode `0700` directory.

```yaml
switch_refresh_sda_fabric_distribution_hostname_transfer_enabled: true
switch_refresh_sda_fabric_distribution_hostname_transfer_manifest_dir: /var/lib/ansible/distribution-refresh
```

If cleanup removed the old inventory record but hostname update did not
complete, rerun only the durable hostname step:

```yaml
switch_refresh_sda_fabric_distribution_phase: cleanup_old
switch_refresh_sda_fabric_distribution_cleanup_old: false
switch_refresh_sda_fabric_distribution_hostname_transfer_enabled: true
switch_refresh_sda_fabric_distribution_hostname_transfer_resume_from_manifest: true
switch_refresh_sda_fabric_distribution_hostname_transfer_manifest_dir: /var/lib/ansible/distribution-refresh
```

Recovery loads and validates every manifest before changing any hostname. It
revalidates the controller identity, replacement UUID and serial, exact site,
inventory role, reachability, management state, and absence of fabric-device
enrollment. It also proves that each old IP, UUID, and serial number is absent
before reusing a hostname.

## Operational controls

The defaults expose bounded inventory, provisioning, topology, LAN Automation,
and hostname convergence timeouts. Normal `cleanup_old` requires both old-device
unprovision and inventory removal. Link creation and deletion are mandatory,
idempotent workflow barriers rather than optional stages.
