Network Configuration Generator & Deployer
This project is a powerful and flexible automation tool designed to generate and deploy network device configurations. It uses a data-driven approach with YAML for defining variables and Jinja2 for templating, allowing for consistent, scalable, and vendor-agnostic configuration management.

Key Features
Data-Driven Configuration: Separates data (YAML), from logic (Python), and presentation (Jinja2), making it easy to manage and scale.

Hierarchical Configuration: Merges data from global, regional, and device-type specific files, allowing for granular control and standardization.

Multi-Vendor Support: Easily extendable to support any network vendor by creating a corresponding Jinja2 template.

Multiple Operating Modes:

Interactive Mode: Guides the user through a series of prompts to configure a single device.

File Mode: Processes a central YAML file containing a list of devices for bulk configuration generation.

Dry Run Mode: Prints the generated configuration to the console for verification without saving any files.

Serial Console Deployment: Includes a separate script to push the generated configuration files to a device over a serial console cable, perfect for initial device setup (zero-touch provisioning).

Project Structure
.
├── _Main_script.py             # Main script to generate configurations
├── _Deploy_Config.py           # Script to deploy configs via serial console
├── config/
│   ├── _Global.yml             # Global defaults, capabilities, and regions
│   ├── access_switch.yml       # Golden Template for all access switches
│   ├── core_switch.yml         # Golden Template for all core switches
│   └── firewall.yml            # Golden Template for all firewalls
├── templates/
│   ├── dell_access_switch.j2   # Dell-specific template for access switches
│   ├── dell_core_switch.j2     # Dell-specific template for core switches
│   └── ...                     # Other templates per vendor/device type
├── output_configs/             # Generated configuration files are saved here
│   └── stockholm-access-01.config
├── input_devices.yml           # Central input file listing all devices to be configured
└── README.md                   # This file

config/: Contains "Golden Template" YAML files. Each file defines the standard configuration for a type of device (e.g., all access switches should have STP enabled).

templates/: Contains vendor-specific Jinja2 templates. These files translate the YAML data into the correct command-line syntax for a specific vendor's OS.

input_devices.yml: The main inventory file. This is where you list the individual devices you want to configure, specifying their unique properties like hostname, vendor, device_type, and any necessary secrets.

output_configs/: The default directory where the final .config files are saved.

Prerequisites
Python 3.6+

pip (Python package installer)

Installation
Clone the repository:

git clone <your-repository-url>
cd <your-repository-name>

Create and activate a virtual environment (recommended):

python3 -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate

Install the required Python libraries:

pip install pyyaml jinja2 pyserial

Configuration
The system uses a hierarchical data model. When generating a configuration for a device, data is merged in the following order (later steps override earlier ones):

config/_Global.yml: The base layer with global standards.

config/<device_type>.yml: The "Golden Template" for the specific device type (e.g., config/access_switch.yml).

input_devices.yml: The specific, unique data for the individual device.

Usage: Generating Configurations (_Main_script.py)
The main script can be run in several modes.

1. File Mode (Recommended for bulk operations)
This is the primary mode for generating configurations. You define all your devices in the input_devices.yml file.

python _Main_script.py --file input_devices.yml

2. Dry Run Mode
To test your changes and see the output without saving any files, use the --dry-run flag.

python _Main_script.py --file input_devices.yml --dry-run

3. Targeting a Specific Hostname
When you only want to generate the config for a single device from your main input file, use the --hostname flag.

python _Main_script.py --file input_devices.yml --hostname "stockholm-access-01"

4. Interactive Mode
If you run the script without any arguments, it will launch an interactive wizard to guide you through configuring a single device.

python _Main_script.py

Usage: Deploying Configurations (_Deploy_Config.py)
This script sends a generated configuration file to a device over a serial console connection.

1. Find Your Serial Port
Windows: Open Device Manager and look under "Ports (COM & LPT)". It will be something like COM3.

macOS: Open a terminal and run ls /dev/tty.*. Look for /dev/tty.usbserial-XXXXXXXX.

Linux: Open a terminal and run ls /dev/ttyUSB*. It is typically /dev/ttyUSB0.

2. Run the Deployment Script
Use the --file flag to specify the configuration file and the --port flag for your serial port.

Example (macOS/Linux):

python _Deploy_Config.py --file output_configs/stockholm-access-01.config --port /dev/tty.usbserial-A1B2C3D4

Example (Windows):

python _Deploy_Config.py --file output_configs\stockholm-access-01.config --port COM3

You can also adjust the baud rate (default: 9600) and the delay between lines (default: 0.5s) with the --baud and --delay flags.
