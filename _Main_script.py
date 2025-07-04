import yaml
import os
import ipaddress
from jinja2 import Environment, FileSystemLoader

# === Load YAML File ===
def load_yaml(path):
    if not os.path.exists(path):
        print(f"❌ Missing configuration file: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

# === Merge Global + Device Type + User Input ===
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

# === Render Jinja2 Template ===
def render_config(template_name, config):
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_name)
    return template.render(**config)

# === Save Output File ===
def write_output(config, rendered_config, output_dir="output_configs"):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{config['hostname']}.config"
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        print(f"⚠️  File {filename} already exists. Not overwriting.")
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(rendered_config)
        print(f"✅ Configuration saved to {filepath}")

# === Validate IP ===
def validate_ip(ip_str):
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

# === Main Program ===
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, "config")
    global_path = os.path.join(config_dir, "_Global.yml")

    # === Load Global Config ===
    global_config = load_yaml(global_path)
    if not global_config:
        print("❌ Failed to load global config. Exiting.")
        exit(1)

    # === User Input ===
    vendor = input("Vendor (Cisco, FortiSwitch, Dell, etc.): ").strip().lower()
    device_type = input("Device Type (access_switch, core_switch, router, firewall): ").strip().lower()
    hostname = input("Hostname: ").strip()
    if not hostname:
        print("❌ Hostname is required.")
        exit(1)

    region = input("Region (EU, AP, AM): ").strip().lower()

    loopbacks = []
    if global_config.get("supports_loopback", False) or device_type == "core_switch":
        loopback_ip = input("Loopback IP (or press Enter to skip): ").strip()
        if loopback_ip:
            if not validate_ip(loopback_ip):
                print("❌ Invalid Loopback IP address.")
                exit(1)
            loopbacks.append({
                "id": 0,
                "description": "Loopback Interface",
                "ip_address": loopback_ip,
                "subnet_mask": "255.255.255.255"
            })

    snmp_location = input("SNMP Location: ").strip()
    snmp_key_aes = input("SNMP AES Key: ").strip()
    snmp_key_sha = input("SNMP SHA Key: ").strip()
    tacacs_pw = input("TACACS Password: ").strip()
    enable_pw = input("Enable Password: ").strip()
    user_pw = input("User Password: ").strip()

    # === Load Device Type Config ===
    device_file = f"{device_type}.yml"
    device_path = os.path.join(config_dir, device_file)
    if not os.path.exists(device_path):
        print(f"❌ Device type config file not found: {device_path}")
        exit(1)
    device_config = load_yaml(device_path)

    # === Build User Configuration Data ===
    user_input = {
        "hostname": hostname,
        "region": region,
        "loopbacks": loopbacks,
        "snmp": {
            "encryption": "sha",
            "key": snmp_key_sha,
            "privacy": "aes",
            "privacy_key": snmp_key_aes,
            "location": snmp_location
        },
        "tacacs": {
            "key": tacacs_pw,
            "servers": global_config.get("regions", {}).get(region, {}).get("tacacs", {}).get("servers", [])
        },
        "enable_password": enable_pw,
        "user_password": user_pw
    }

    # === Merge All Configs ===
    full_config = merge_configs(global_config, device_config, user_input)

    # === Determine Template File ===
    template_file = f"{vendor}_{device_type}.j2"
    template_path = os.path.join(base_dir, "templates", template_file)
    if not os.path.exists(template_path):
        print(f"❌ Template not found: {template_file}")
        exit(1)

    # === Render and Save ===
    rendered_config = render_config(template_file, full_config)
    write_output(full_config, rendered_config)