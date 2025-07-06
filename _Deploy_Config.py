import serial
import time
import argparse
import os
import sys

# --- Helper function for user-friendly output ---
def print_status(message, msg_type="info"):
    """Prints a formatted status message."""
    if msg_type == "info":
        print(f"[i] {message}")
    elif msg_type == "success":
        print(f"[✅] {message}")
    elif msg_type == "error":
        print(f"[❌] {message}", file=sys.stderr)
    elif msg_type == "sending":
        print(f"--> {message.strip()}")

def deploy_config_serial(file_path, port, baud_rate=9600, delay=0.5):
    """
    Sends a configuration file line-by-line over a serial connection.

    :param file_path: Path to the configuration file.
    :param port: The serial port to use (e.g., COM3, /dev/ttyUSB0).
    :param baud_rate: The baud rate for the connection.
    :param delay: Delay in seconds between sending each line.
    """
    # --- Check if the configuration file exists ---
    if not os.path.exists(file_path):
        print_status(f"Configuration file not found: {file_path}", "error")
        return

    ser = None
    try:
        # --- Open the serial port ---
        print_status(f"Opening serial port {port} with baud rate {baud_rate}...")
        ser = serial.Serial(port, baud_rate, timeout=1)
        print_status("Port is open. Waiting 2 seconds for the device to stabilize...", "success")
        time.sleep(2)

        # --- Send an initial newline to get a prompt ---
        ser.write(b'\n')
        time.sleep(delay)

        # --- Read the configuration file ---
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print_status(f"Starting transmission of {len(lines)} lines from {file_path}...")
        
        # --- Send each line ---
        for line in lines:
            # Skip empty lines or comments
            if not line.strip() or line.strip().startswith('!'):
                continue

            print_status(line, "sending")
            ser.write(line.encode('utf-8') + b'\n')
            time.sleep(delay)

        print_status("Last command sent. Waiting a moment...", "info")
        time.sleep(2)
        
        # --- Read any final output from the device ---
        final_output = ser.read(1024).decode('utf-8', errors='ignore')
        if final_output.strip():
            print_status("Last output from the device:", "info")
            print(final_output)

        print_status("Configuration has been sent!", "success")

    except serial.SerialException as e:
        print_status(f"Could not open or use port {port}: {e}", "error")
        print_status("Verify that the port name is correct and the cable is connected.", "info")
        print_status("Example port names: COM3 (Windows), /dev/ttyUSB0 (Linux), /dev/tty.usbserial-XXXX (macOS)", "info")
    
    except Exception as e:
        print_status(f"An unexpected error occurred: {e}", "error")

    finally:
        if ser and ser.is_open:
            ser.close()
            print_status(f"Serial port {port} has been closed.", "info")

def main():
    """Main function to parse arguments and start deployment."""
    parser = argparse.ArgumentParser(
        description="Send a configuration file to a network device via serial console cable.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-f", "--file",
        required=True,
        help="Path to the configuration file to be sent.\nExample: output_configs/stockholm-access-01.config"
    )
    parser.add_argument(
        "-p", "--port",
        required=True,
        help="The name of the serial port.\nExample: COM3 (Windows), /dev/ttyUSB0 (Linux), /dev/tty.usbserial-XXXX (macOS)"
    )
    parser.add_argument(
        "-b", "--baud",
        type=int,
        default=9600,
        help="Baud rate for the connection (default: 9600)."
    )
    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between each line (default: 0.5)."
    )
    args = parser.parse_args()

    deploy_config_serial(args.file, args.port, args.baud, args.delay)

if __name__ == "__main__":
    main()
# --- End of file: _Deploy_Config.py ---
# --- This file is used to deploy configuration files to network devices via serial console cable.
# --- It reads a configuration file and sends it line-by-line over the specified serial port.