import yaml
import os
import ipaddress
import argparse
import getpass
import copy
import logging
from jinja2 import Environment, FileSystemLoader

# --- Basic logging configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# === Load YAML file ===
def load_yaml(path):
    """Loads a YAML file and returns its content."""
    if not os.path.exists(path):
        logging.warning(f"Configuration file not found, skipping: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logging.error(f"Error reading YAML file {path}: {e}")
        return {}

# === Deep merge dictionaries ===
def deep_merge(source, destination):
    """Recursively merges 'source' dict into 'destination' dict."""
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value
    return destination

# === Merge configurations ===
def merge_configs(global_config, device_type_config, device_specific_data):
    """
    Merges configurations in a clear hierarchy.
    Hierarchy: Global -> Region -> Device Type -> Specific Device
    """
    # Step 1: Start with a copy of the global default values.
    final_config = {}
    deep_merge(global_config.get('default_configs', {}), final_config)
    deep_merge(global_config.get('default_capabilities', {}), final_config)
    if 'base_commands' in global_config: final_config['base_commands'] = global_config['base_commands']
    if 'banner_text' in global_config: final_config['banner_text'] = global_config['banner_text']
    if 'fallback_user' in global_config: final_config['fallback_user'] = global_config['fallback_user']
    logging.debug(f"MERGE: After globals: {final_config}")

    # Step 2: Merge region-specific values
    region = device_specific_data.get("region", "").lower()
    if region and "regions" in global_config:
        region_overrides = global_config.get("regions", {}).get(region, {})
        if region_overrides:
            logging.info(f"Applying region-specific settings for region: {region.upper()}")
            deep_merge(region_overrides, final_config)
            logging.debug(f"MERGE: After region '{region.upper()}': {final_config}")

    # Step 3: Merge device-type-specific values (from e.g., access_switch.yml)
    deep_merge(device_type_config, final_config)
    logging.debug(f"MERGE: After device type config: {final_config}")

    # Step 4: Merge the most specific device data (from e.g., devices/test3.yml)
    deep_merge(device_specific_data, final_config)
    logging.debug(f"MERGE: After specific device data: {final_config}")

    return final_config

# === Render Jinja2 template ===
def render_config(template_name, config, templates_dir="templates"):
    """Renders the Jinja2 template with the given configuration."""
    env = Environment(loader=FileSystemLoader(templates_dir), trim_blocks=True, lstrip_blocks=True)
    try:
        template = env.get_template(template_name)
        return template.render(**config)
    except Exception as e:
        logging.error(f"Error rendering template {template_name}: {e}")
        return None

# === Save output file ===
def write_output(config, rendered_config, output_dir="output_configs", force=False):
    """Saves the rendered configuration to a file."""
    os.makedirs(output_dir, exist_ok=True)
    hostname = config.get("hostname", "unknown_device")
    filename = f"{hostname}.config"
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath) and not force:
        logging.warning(f"File {filename} already exists. Use --force to overwrite.")
        return
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(rendered_config)
    logging.info(f"✅ Configuration saved to {filepath}")

# === Get secret ===
def get_secret(key_name, device_info, env_var_name, prompt_text):
    """Gets a secret: device_info -> environment variable -> prompt user."""
    keys = key_name.split('.')
    value = device_info
    try:
        for k in keys: value = value[k]
        secret = value
    except (KeyError, TypeError):
        secret = None
    if secret:
        logging.debug(f"Using '{key_name}' from input file.")
        return secret
    secret = os.getenv(env_var_name)
    if secret:
        logging.info(f"Using '{key_name}' from environment variable {env_var_name}.")
        return secret
    return getpass.getpass(prompt_text)

# === Interactive function for choosing from a list ===
def prompt_for_choice(prompt_text, choices):
    """Displays a numbered list and ensures the user makes a valid choice."""
    if not choices:
        logging.error(f"No choices to display for: {prompt_text}")
        return None
    print(prompt_text)
    for i, choice in enumerate(choices, 1):
        print(f"  {i}. {choice}")
    while True:
        try:
            choice_num = int(input(f"Enter number (1-{len(choices)}): "))
            if 1 <= choice_num <= len(choices):
                return choices[choice_num - 1]
            else:
                print("Invalid number, try again.")
        except ValueError:
            print("Please enter a valid number.")

# === Process a device configuration ===
def process_device(device_info, global_config, base_dir, force_overwrite):
    """Main logic to process and generate configuration for one device."""
    vendor = device_info.get("vendor", "").lower()
    device_type = device_info.get("device_type", "").lower()
    hostname = device_info.get("hostname")
    if not all([vendor, device_type, hostname]):
        logging.error("❌ 'vendor', 'device_type', and 'hostname' are required fields. Skipping.")
        return

    logging.info(f"--- Processing device: {hostname} (Vendor: {vendor.capitalize()}, Type: {device_type}) ---")
    config_dir = os.path.join(base_dir, "config")
    device_type_file = f"{device_type}.yml"
    device_type_path = os.path.join(config_dir, device_type_file)
    device_type_config = load_yaml(device_type_path)
    logging.debug(f"Content from device type file ({device_type_file}): {device_type_config}")

    if 'enable_password' not in device_info:
        device_info['enable_password'] = get_secret("enable_password", device_info, "ENABLE_PASSWORD", f"Enter Enable Password for {hostname}: ")
    if 'fallback_user_password' not in device_info:
        device_info['fallback_user_password'] = get_secret("fallback_user_password", device_info, "FALLBACK_USER_PASSWORD", f"Enter password for fallback user on {hostname}: ")

    full_config = merge_configs(global_config, device_type_config, device_info)
    template_file = f"{vendor}_{device_type}.j2"
    template_path = os.path.join(base_dir, "templates", template_file)
    if not os.path.exists(template_path):
        logging.error(f"❌ Template file not found: {template_file}. Skipping device {hostname}.")
        return

    rendered_config = render_config(template_file, full_config, os.path.join(base_dir, "templates"))
    if rendered_config:
        write_output(full_config, rendered_config, force=force_overwrite)

# === Run in interactive mode ===
def run_interactive_mode(global_config, base_dir, force_overwrite):
    """Gathers device information from the user with validation."""
    logging.info("--- Running in interactive mode ---")
    validation_data = global_config.get('validation_data', {})
    valid_vendors = validation_data.get('vendors', [])
    valid_device_types = validation_data.get('template_styles', [])

    vendor = prompt_for_choice("Select a vendor:", valid_vendors)
    if not vendor: return

    device_type = prompt_for_choice("Select a device type:", valid_device_types)
    if not device_type: return

    hostname = input("Enter hostname: ").strip()
    if not hostname:
        logging.error("❌ Hostname is required.")
        return

    user_input = {
        "hostname": hostname,
        "vendor": vendor.lower(),
        "device_type": device_type.lower(),
        "region": input("Enter region (e.g., eu, ap, am): ").strip().lower(),
        "snmp": {},
        "tacacs": {},
    }

    # Passwords for enable and fallback are handled by process_device.
    # We need to ask for other secrets here.
    user_input["snmp"]["location"] = input("Enter SNMP Location: ").strip()
    user_input["snmp"]["key"] = get_secret("snmp.key", {}, "SNMP_SHA_KEY", "Enter SNMP SHA Key: ")
    user_input["snmp"]["privacy_key"] = get_secret("snmp.privacy_key", {}, "SNMP_AES_KEY", "Enter SNMP AES Key: ")
    user_input["tacacs"]["key"] = get_secret("tacacs.key", {}, "TACACS_KEY", "Enter TACACS Password: ")
    
    process_device(user_input, global_config, base_dir, force_overwrite)

# === Main program ===
def main():
    """Main function of the script."""
    parser = argparse.ArgumentParser(description="Generate network device configurations from YAML and Jinja2.")
    # The --directory argument has been removed
    parser.add_argument("-f", "--file", help="Path to a YAML file with a list of devices.", type=str)
    parser.add_argument("--force", help="Overwrite existing configuration files.", action="store_true")
    parser.add_argument("-v", "--verbose", help="Enable detailed DEBUG logging.", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose logging enabled.")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, "config")
    global_path = os.path.join(config_dir, "_Global.yml")

    global_config = load_yaml(global_path)
    if not global_config:
        logging.critical("❌ Could not load global configuration. Exiting.")
        exit(1)

    # *** SIMPLIFIED LOGIC ***
    if args.file:
        # If --file is specified, run in file mode
        logging.info(f"--- Running in file mode for {args.file} ---")
        devices_to_configure = load_yaml(args.file)
        if not devices_to_configure or 'devices' not in devices_to_configure:
            logging.critical(f"❌ Input file {args.file} is empty or incorrectly formatted.")
            exit(1)
        for device_info in devices_to_configure['devices']:
            process_device(device_info, global_config, base_dir, args.force)
    else:
        # If no arguments are given, run in interactive mode
        logging.info("No arguments provided. Starting interactive mode.")
        run_interactive_mode(global_config, base_dir, args.force)

if __name__ == "__main__":
    main()
