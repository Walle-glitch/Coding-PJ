
**Network Configuration Generator & Deployer**

This project is a powerful and flexible automation tool designed to generate and deploy network device configurations. It uses a data-driven approach with YAML for defining variables and Jinja2 for templating, allowing for consistent, scalable, and vendor-agnostic configuration management.

  

**Key Features**

 - Data-Driven Configuration: Separates data (YAML), from logic
   (Python), and presentation (Jinja2), making it easy to manage and
   scale. 
 - Hierarchical Configuration: Merges data from global, regional,    and
   device-type specific files, allowing for granular control and   
   standardization.
 - Multi-Vendor Support: Easily extendable to support    any network
   vendor by creating a corresponding Jinja2 template.
 - Multiple Operating Modes: 
	 - Interactive Mode: Guides the user through a    series of prompts to
   configure a single device.
	 - File Mode: Processes a central YAML file containing a list of devices for bulk
   configuration generation. 
	 - Dry Run Mode: Prints the generated    configuration to the console
   for verification without saving any files.
	 - Serial Console Deployment: Includes a separate script to push    the
   generated configuration files to a device over a serial console   
   cable, perfect for initial device setup (zero-touch provisioning).

  

**Project Structure**
.
├── _Main_script.py # Main script to generate configurations
├── _Deploy_Config.py # Script to deploy configs via serial console
├── config/
│ ├── _Global.yml # Global defaults, capabilities, and regions
│ ├── access_switch.yml # Golden Template for all access switches
│ ├── core_switch.yml # Golden Template for all core switches
│ └── firewall.yml # Golden Template for all firewalls
├── templates/
│ ├── dell_access_switch.j2 # Dell-specific template for access switches
│ ├── dell_core_switch.j2 # Dell-specific template for core switches
│ └── ... # Other templates per vendor/device type
├── output_configs/ # Generated configuration files are saved here
│ └── stockholm-access-01.config
├── input_devices.yml # Central input file listing all devices to be configured
└── README.md # This file

config/: Contains "Golden Template" YAML files. Each file defines the standard configuration for a type of device (e.g., all access switches should have STP enabled).

templates/: Contains vendor-specific Jinja2 templates. These files translate the YAML data into the correct command-line syntax for a specific vendor's OS.

input_devices.yml: The main inventory file. This is where you list the individual devices you want to configure, specifying their unique properties like hostname, vendor, device_type, and any necessary secrets.
output_configs/: The default directory where the final .config files are saved.
