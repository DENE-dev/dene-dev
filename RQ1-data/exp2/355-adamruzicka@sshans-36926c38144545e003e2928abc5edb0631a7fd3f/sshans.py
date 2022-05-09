#!/usr/bin/env python3

# Usage: sshans.py [path_to_ansible_inventory]

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader

import subprocess
import os
import sys

# TODO: Use argparse or something
inventory = "inventory"
if len(sys.argv) == 2:
    inventory = sys.argv[1]

loader = DataLoader()
inventory = InventoryManager(loader=loader, sources=inventory)

if inventory.hosts == {}:
    sys.exit(1)

# TODO?: Support alternatives to fzf
fzf = subprocess.Popen(["fzf"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
hostnames = inventory.hosts.keys()
hostname = fzf.communicate(bytes("\n".join(hostnames), "UTF-8"))[0].decode().strip()

if hostname == "":
    sys.exit(1)

host = inventory.hosts[hostname]
host_vars = host.vars
all_vars = inventory.groups["all"].vars


def var(key, sources, default=None):
    result = None
    for source in sources:
        result = source.get(key, None)
        if result:
            break
    return result or Default


# TODO: Check all host's groups, not just 'all'
sources = [host_vars, all_vars]

# TODO?: Get ansible_ssh_private_key_file
user = var("ansible_user", sources)
host = var("ansible_host", sources, hostname)
password = var("ansible_password", sources)

host_string = host
if user:
    host_string = f"{user}@{host_string}"

if password:
    os.environ["SSHPASS"] = password

os.execl("/usr/bin/sshpass", "sshpass", "-e", "ssh", host_string)