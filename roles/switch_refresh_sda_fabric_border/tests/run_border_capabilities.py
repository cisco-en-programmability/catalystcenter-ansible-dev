# Copyright (c) 2026 Cisco and/or its affiliates.
# Licensed under the Apache License, Version 2.0.
"""Run real refresh tasks with controller roles replaced in an isolated collection."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    role = Path(__file__).resolve().parents[1]
    collection = role.parents[1]
    with tempfile.TemporaryDirectory(prefix="border-capability-tests-") as directory:
        workspace = Path(directory)
        isolated = workspace / "ansible_collections" / "cisco" / "catalystcenter"
        isolated_role = isolated / "roles" / role.name
        for name in ("tasks", "tests"):
            shutil.copytree(role / name, isolated_role / name, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(role / "tests" / "fixtures" / "roles", isolated / "roles", dirs_exist_ok=True)
        (isolated / "plugins").symlink_to(collection / "plugins", target_is_directory=True)
        config = workspace / "ansible.cfg"
        config.write_text("[defaults]\nhost_key_checking = False\nretry_files_enabled = False\n")
        env = os.environ.copy()
        existing = env.get("ANSIBLE_COLLECTIONS_PATH", "")
        env.update({
            "ANSIBLE_CONFIG": str(config),
            "ANSIBLE_COLLECTIONS_PATH": str(workspace) + (os.pathsep + existing if existing else ""),
            "ANSIBLE_ROLES_PATH": str(isolated / "roles"),
            "ANSIBLE_LOCAL_TEMP": str(workspace / "local"),
            "ANSIBLE_REMOTE_TEMP": str(workspace / "remote"),
        })
        return subprocess.run([
            str(Path(sys.executable).with_name("ansible-playbook")),
            "-i", str(isolated_role / "tests" / "inventory"),
            str(isolated_role / "tests" / "test_border_capabilities.yml"),
        ], cwd=workspace, env=env, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
