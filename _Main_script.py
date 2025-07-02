import yaml
import os
import ipaddress
from modules._Dell import generate_config


def load_yaml(path):
    if not os.path.exists(path):
        print(f"❌ Missing configuration file: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge_configs(global_config, device_config, user_input):
    merged = global_config.copy()
    merged.update(device_config)
    merged.update(user_input)

    region = merged.get("region", "").lower()
    region_overrides = global_config.get("regions", {}).get(region, {})
    for key, value in region_overrides.items():
        if key not in merged:
            print(f"🌍 Applying region override: {key}")
            merged[key] = value

    return merged


def write_output(config, output_dir="output_configs"):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{config['hostname']}.config"
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        print(f"⚠️  File {filename} already exists. Not overwriting.")
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(generate_config(config))
        print(f"✅ Configuration saved to {filepath}")


if __name__ == "__main__":
    # === Paths ===
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, "config")
    global_path = os.path.join(config_dir, "_Global.yml")
    dell_path = os.path.join(config_dir, "_Dell.yml")

    global_config = load_yaml(global_path)
    if not global_config:
        print("❌ Failed to load global config. Exiting.")
        exit(1)

    device_config = load_yaml(dell_path)

    # === User Input ===
    hostname = input("Hostname: ").strip()
    region = input("Region (EU, AP, AM): ").strip().lower()
    loopback_ip = input("Loopback IP: ").strip()
    tacacs_pw = input("TACACS Password: ").strip()
    snmp_location = input("SNMP Location: ").strip()

    vlans = []
    try:
        vlan_count = int(input("How many VLANs? "))
        for i in range(vlan_count):
            vid = input(f"  VLAN ID {i+1}: ").strip()
            vname = input(f"  VLAN Name {i+1}: ").strip()
            vip = input(f"  VLAN IP (optional): ").strip()
            vlans.append({"id": vid, "name": vname, "ip_address": vip})
    except ValueError:
        print("❌ Invalid number of VLANs.")
        exit(1)

    user_input = {
        "hostname": hostname,
        "region": region,
        "loopback": {
            "name": "Loopback0",
            "ip_address": loopback_ip,
            "subnet_mask": "255.255.255.255"
        },
        "vlans": vlans,
        "snmp": {
            "location": snmp_location
        },
        "tacacs": {
            "key": tacacs_pw
        }
    }

    full_config = merge_configs(global_config, device_config, user_input)
    write_output(full_config)