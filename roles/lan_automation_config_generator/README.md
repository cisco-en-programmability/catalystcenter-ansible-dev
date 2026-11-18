# Ansible role: lan_automation_config_generator

Generate a LAN automation variable file before replacing physical devices. This
role wraps `cisco.catalystcenter.lan_automation_playbook_config_generator` and
registers `lan_automation_config_generator_result`. It requires Catalyst Center
2.3.7.9 or later, Python 3.12+, PyYAML, and catalystcentersdk >= 3.2.3.0.0.

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: cisco.catalystcenter.lan_automation_config_generator
      vars:
        catalystcenter_host: "{{ vault_catalystcenter_host }}"
        catalystcenter_username: "{{ vault_catalystcenter_username }}"
        catalystcenter_password: "{{ vault_catalystcenter_password }}"
        catalystcenter_version: "3.1.3.0"
        lan_automation_config_generator_file_path: ./replacement_lan_automation.yml
        lan_automation_config_generator_config:
          site_name_hierarchy: Global/Region/Building
          ip_address_list: ["192.0.2.10", "192.0.2.11"]
```

| Variable | Default | Purpose |
|---|---|---|
| `lan_automation_config_generator_config` | `null`; required | Dictionary containing `site_name_hierarchy` and `ip_address_list`. |
| `lan_automation_config_generator_state` | `gathered` | Read existing configuration. |
| `lan_automation_config_generator_file_path` | `null` | Output path; the module generates a timestamped filename when omitted. |
| `lan_automation_config_generator_file_mode` | `overwrite` | `overwrite` or `append`. |
| `lan_automation_config_generator_isis_domain_pwd` | `null` | Optional password, supplied directly or through Vault. |

Standard `catalystcenter_*` connection, logging, timeout, and schema-validation
variables are forwarded to the module. Task output is suppressed because the
result can contain credentials.

The role preserves current hostnames, management IPs, exact sites, and supported
historical session settings. Standalone output contains
`REPLACE_WITH_SERIAL_FOR_<IP>` placeholders. Replace them with the new physical
device serials before passing the file's `config` list to
`lan_automation_workflow_manager` with `state: merged`.

Capture must happen before deleting the original devices. Missing or ambiguous
LAN automation history fails without writing an incomplete file. The primary
and peer seeds, seed interfaces, and pools must remain available. This role does
not delete devices or restore provisioning, fabric membership, or host ports.

The status API cannot recover IS-IS passwords. If supplied during standalone
generation, the password is written to the generated file, which should be
encrypted with Ansible Vault when retained. The same-IP refresh role omits the
password during capture and injects its runtime Vault input during restoration.

The generated file uses one YAML document with a top-level `config` list.
Repeated unchanged captures are idempotent; check mode predicts local changes
without writing. See [the module guide](../../cvp/lan_automation/README.md) and
[the role playbook](../../playbooks/lan_automation_config_generator.yml).
