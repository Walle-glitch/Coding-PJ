import yaml
import os
import ipaddress
import argparse
import getpass
import copy
import logging
from jinja2 import Environment, FileSystemLoader

# --- Grundläggande konfiguration för loggning ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# === Ladda YAML-fil ===
def load_yaml(path):
    """Laddar en YAML-fil och returnerar dess innehåll."""
    if not os.path.exists(path):
        logging.warning(f"Konfigurationsfilen hittades inte, hoppar över: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logging.error(f"Fel vid läsning av YAML-fil {path}: {e}")
        return {}

# === Djup sammanslagning av dictionaries ===
def deep_merge(source, destination):
    """Rekursivt slår samman 'source' dict in i 'destination' dict."""
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value
    return destination

# === Slå samman konfigurationer ===
def merge_configs(global_config, device_type_config, device_specific_data):
    """
    Slår samman konfigurationer i en tydlig hierarki.
    Hierarki: Global -> Region -> Enhetstyp -> Specifik Enhet
    """
    # Steg 1: Börja med en kopia av de globala standardvärdena.
    final_config = {}
    deep_merge(global_config.get('default_configs', {}), final_config)
    deep_merge(global_config.get('default_capabilities', {}), final_config)
    if 'base_commands' in global_config: final_config['base_commands'] = global_config['base_commands']
    if 'banner_text' in global_config: final_config['banner_text'] = global_config['banner_text']
    if 'fallback_user' in global_config: final_config['fallback_user'] = global_config['fallback_user']
    logging.debug(f"MERGE: After globals: {final_config}")

    # Steg 2: Slå samman regionsspecifika värden
    region = device_specific_data.get("region", "").lower()
    if region and "regions" in global_config:
        region_overrides = global_config.get("regions", {}).get(region, {})
        if region_overrides:
            logging.info(f"Tillämpar regionsspecifika inställningar för region: {region.upper()}")
            deep_merge(region_overrides, final_config)
            logging.debug(f"MERGE: After region '{region.upper()}': {final_config}")

    # Steg 3: Slå samman enhetstyp-specifika värden (från t.ex. access_switch.yml)
    deep_merge(device_type_config, final_config)
    logging.debug(f"MERGE: After device type config: {final_config}")

    # Steg 4: Slå samman den mest specifika enhetsdatan (från t.ex. devices/test3.yml)
    deep_merge(device_specific_data, final_config)
    logging.debug(f"MERGE: After specific device data: {final_config}")

    return final_config

# === Rendera Jinja2-mall ===
def render_config(template_name, config, templates_dir="templates"):
    """Renderar Jinja2-mallen med den givna konfigurationen."""
    env = Environment(loader=FileSystemLoader(templates_dir), trim_blocks=True, lstrip_blocks=True)
    try:
        template = env.get_template(template_name)
        return template.render(**config)
    except Exception as e:
        logging.error(f"Fel vid rendering av mall {template_name}: {e}")
        return None

# === Spara output-fil ===
def write_output(config, rendered_config, output_dir="output_configs", force=False):
    """Sparar den renderade konfigurationen till en fil."""
    os.makedirs(output_dir, exist_ok=True)
    hostname = config.get("hostname", "unknown_device")
    filename = f"{hostname}.config"
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath) and not force:
        logging.warning(f"Filen {filename} existerar redan. Använd --force för att skriva över.")
        return
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(rendered_config)
    logging.info(f"✅ Konfiguration sparad till {filepath}")

# === Hämta hemlighet ===
def get_secret(key_name, device_info, env_var_name, prompt_text):
    """Hämtar en hemlighet: device_info -> miljövariabel -> fråga användaren."""
    keys = key_name.split('.')
    value = device_info
    try:
        for k in keys: value = value[k]
        secret = value
    except (KeyError, TypeError):
        secret = None
    if secret:
        logging.debug(f"Använder '{key_name}' från indata-fil.")
        return secret
    secret = os.getenv(env_var_name)
    if secret:
        logging.info(f"Använder '{key_name}' från miljövariabeln {env_var_name}.")
        return secret
    return getpass.getpass(prompt_text)

# === Interaktiv funktion för att välja från en lista ===
def prompt_for_choice(prompt_text, choices):
    """Visar en numrerad lista och säkerställer att användaren gör ett giltigt val."""
    if not choices:
        logging.error(f"Inga val att visa för: {prompt_text}")
        return None
    print(prompt_text)
    for i, choice in enumerate(choices, 1):
        print(f"  {i}. {choice}")
    while True:
        try:
            choice_num = int(input(f"Ange nummer (1-{len(choices)}): "))
            if 1 <= choice_num <= len(choices):
                return choices[choice_num - 1]
            else:
                print("Ogiltigt nummer, försök igen.")
        except ValueError:
            print("Ange ett giltigt nummer.")

# === Processa en enhetskonfiguration ===
def process_device(device_info, global_config, base_dir, force_overwrite):
    """Huvudlogik för att processa och generera konfiguration för en enhet."""
    vendor = device_info.get("vendor", "").lower()
    device_type = device_info.get("device_type", "").lower()
    hostname = device_info.get("hostname")
    if not all([vendor, device_type, hostname]):
        logging.error("❌ 'vendor', 'device_type' och 'hostname' är obligatoriska fält. Hoppar över.")
        return

    logging.info(f"--- Bearbetar enhet: {hostname} (Vendor: {vendor.capitalize()}, Type: {device_type}) ---")
    config_dir = os.path.join(base_dir, "config")
    device_type_file = f"{device_type}.yml"
    device_type_path = os.path.join(config_dir, device_type_file)
    device_type_config = load_yaml(device_type_path)
    logging.debug(f"Innehåll från enhetstyp-filen ({device_type_file}): {device_type_config}")

    if 'enable_password' not in device_info:
        device_info['enable_password'] = get_secret("enable_password", device_info, "ENABLE_PASSWORD", f"Ange Enable Password för {hostname}: ")
    if 'fallback_user_password' not in device_info:
        device_info['fallback_user_password'] = get_secret("fallback_user_password", device_info, "FALLBACK_USER_PASSWORD", f"Ange lösenord för fallback-användare på {hostname}: ")

    full_config = merge_configs(global_config, device_type_config, device_info)
    template_file = f"{vendor}_{device_type}.j2"
    template_path = os.path.join(base_dir, "templates", template_file)
    if not os.path.exists(template_path):
        logging.error(f"❌ Mallfilen hittades inte: {template_file}. Hoppar över enhet {hostname}.")
        return

    rendered_config = render_config(template_file, full_config, os.path.join(base_dir, "templates"))
    if rendered_config:
        write_output(full_config, rendered_config, force=force_overwrite)

# === Kör i interaktivt läge ===
def run_interactive_mode(global_config, base_dir, force_overwrite):
    """Samlar in enhetsinformation från användaren med validering."""
    logging.info("--- Kör i interaktivt läge ---")
    validation_data = global_config.get('validation_data', {})
    valid_vendors = validation_data.get('vendors', [])
    valid_device_types = validation_data.get('template_styles', [])

    vendor = prompt_for_choice("Välj en tillverkare:", valid_vendors)
    if not vendor: return

    device_type = prompt_for_choice("Välj en enhetstyp:", valid_device_types)
    if not device_type: return

    hostname = input("Ange hostname: ").strip()
    if not hostname:
        logging.error("❌ Hostname är obligatoriskt.")
        return

    user_input = {
        "hostname": hostname,
        "vendor": vendor.lower(),
        "device_type": device_type.lower(),
        "region": input("Ange region (t.ex. eu, ap, am): ").strip().lower(),
        "snmp": {},
        "tacacs": {},
    }

    # Lösenord för enable och fallback hanteras av process_device.
    # Vi behöver fråga efter övriga hemligheter här.
    user_input["snmp"]["location"] = input("Ange SNMP Location: ").strip()
    user_input["snmp"]["key"] = get_secret("snmp.key", {}, "SNMP_SHA_KEY", "Ange SNMP SHA Key: ")
    user_input["snmp"]["privacy_key"] = get_secret("snmp.privacy_key", {}, "SNMP_AES_KEY", "Ange SNMP AES Key: ")
    user_input["tacacs"]["key"] = get_secret("tacacs.key", {}, "TACACS_KEY", "Ange TACACS Password: ")
    
    process_device(user_input, global_config, base_dir, force_overwrite)

# === Huvudprogram ===
def main():
    """Huvudfunktion för skriptet."""
    parser = argparse.ArgumentParser(description="Generera nätverkskonfigurationer från YAML och Jinja2.")
    # Argumentet --directory är borttaget
    parser.add_argument("-f", "--file", help="Sökväg till en YAML-fil med en lista av enheter.", type=str)
    parser.add_argument("--force", help="Skriv över existerande konfigurationsfiler.", action="store_true")
    parser.add_argument("-v", "--verbose", help="Aktivera detaljerad DEBUG-loggning.", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose-loggning aktiverad.")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, "config")
    global_path = os.path.join(config_dir, "_Global.yml")

    global_config = load_yaml(global_path)
    if not global_config:
        logging.critical("❌ Kunde inte ladda global konfiguration. Avslutar.")
        exit(1)

    # *** FÖRENKLAD LOGIK ***
    if args.file:
        # Om --file anges, kör i filläge
        logging.info(f"--- Kör i filläge för {args.file} ---")
        devices_to_configure = load_yaml(args.file)
        if not devices_to_configure or 'devices' not in devices_to_configure:
            logging.critical(f"❌ Indatafilen {args.file} är tom eller felaktigt formaterad.")
            exit(1)
        for device_info in devices_to_configure['devices']:
            process_device(device_info, global_config, base_dir, args.force)
    else:
        # Om inga argument anges, kör i interaktivt läge
        logging.info("Inga argument angivna. Startar interaktivt läge.")
        run_interactive_mode(global_config, base_dir, args.force)

if __name__ == "__main__":
    main()
