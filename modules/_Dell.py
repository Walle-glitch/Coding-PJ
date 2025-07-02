def generate_config(config: dict) -> str:
    lines = []

    lines.append(f"hostname {config['hostname']}")
    lines.append("!")

    # VLAN configuration
    for vlan in config.get("vlans", []):
        lines.append(f"vlan {vlan['id']}")
        if vlan.get("name"):
            lines.append(f" name {vlan['name']}")
        lines.append("!")

    # Interface configuration
    for iface in config.get("interfaces", []):
        names = iface["name"] if isinstance(iface["name"], list) else [iface["name"]]

        for name in names:
            lines.append(f"interface {name}")
            if 'description' in iface:
                lines.append(f" description {iface['description']}")
            if iface.get("mode") == "access":
                lines.append(" switchport mode access")
                if "vlan" in iface:
                    lines.append(f" switchport access vlan {iface['vlan']}")
            elif iface.get("mode") == "trunk":
                lines.append(" switchport mode trunk")
                if "allowed_vlans" in iface:
                    lines.append(f" switchport trunk allowed vlan {iface['allowed_vlans']}")
            if iface.get("no_shutdown", True):
                lines.append(" no shutdown")
            else:
                lines.append(" shutdown")
            if iface.get("spanningtree") == "portfast":
                lines.append(" spanning-tree portfast")
            lines.append("!")

    # Loopback
    if "loopback" in config:
        loop = config["loopback"]
        lines.append(f"interface {loop['name']}")
        lines.append(f" ip address {loop['ip_address']} {loop['subnet_mask']}")
        lines.append("!")

    # SNMP
    snmp = config.get("snmp", {})
    if snmp.get("community"):
        lines.append(f"snmp-server community {snmp['community']} RO")
    if snmp.get("contact"):
        lines.append(f"snmp-server contact {snmp['contact']}")
    if snmp.get("location"):
        lines.append(f"snmp-server location {snmp['location']}")
    lines.append("!")

    # NTP
    for server in config.get("ntp", {}).get("servers", []):
        lines.append(f"ntp server {server}")
    lines.append("!")

    # Logging
    logging = config.get("logging", {})
    for host in logging.get("hosts", []):
        lines.append(f"logging host {host}")
    lines.append(f"logging trap {logging.get('level', 'informational')}")
    lines.append("!")

    # DNS
    dns = config.get("dns", {})
    if "domain_name" in dns:
        lines.append(f"ip domain-name {dns['domain_name']}")
        for dns_ip in dns.get("servers", []):
            lines.append(f"ip name-server {dns_ip}")
        lines.append("!")

    # TACACS
    for server in config.get("tacacs", {}).get("servers", []):
        lines.append(f"tacacs-server host {server}")
    if tacacs_key := config.get("tacacs", {}).get("key"):
        lines.append(f"tacacs-server key {tacacs_key}")
    lines.append("!")

    # ACL
    for acl in config.get("acl", []):
        lines.append(f"ip access-list extended {acl['name']}")
        for rule in acl["rules"]:
            entry = f" {rule['action']} {rule['protocol']} {rule['dst']}"
            if "port" in rule:
                entry += f" eq {rule['port']}"
            lines.append(entry)
        lines.append("!")

    return "\n".join(lines)
