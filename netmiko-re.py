import os
from netmiko import ConnectHandler
import re

PRIVATE_KEY_FILE = os.path.expanduser("~/.ssh/admin_key")

device_creds = {
    "R1-P": {
        "device_type": "cisco_ios",
        "host": "172.31.42.4",
        "username": "admin",
        "use_keys": True,
        "key_file": PRIVATE_KEY_FILE,
        "secret": "",
    },
    "R2-P": {
        "device_type": "cisco_ios",
        "host": "172.31.42.5",
        "username": "admin",
        "use_keys": True,
        "key_file": PRIVATE_KEY_FILE,
        "secret": "",
    }
}

def parse_active_interfaces(output):
    """
    Parses 'show ip interface brief' output to find interfaces that are 'up/up'.
    Returns a list of active interface names.
    """
    active_interfaces = []
    pattern = re.compile(
        r"^(?P<interface>\S+)\s+\S+\s+YES\s+NVRAM\s+up\s+up\s*$",
        re.MULTILINE
    )

    for line in output.splitlines():
        match = pattern.search(line.strip())
        if match:
            active_interfaces.append(match.group("interface"))
    return active_interfaces

def parse_uptime(output):
    """
    Parses 'show version' output to extract the device uptime.
    Returns the uptime string or None if not found.
    """
    pattern = re.compile(r"^\S+\s+uptime is (.*?)\n", re.MULTILINE)

    match = pattern.search(output)
    if match:
        return match.group(1).strip()
    return None


def get_device_info(device_name):
    """
    Connects to a specific network device, executes commands,
    and extracts active interfaces and uptime using regex.
    """
    device_params = device_creds[device_name]
    net_connect = None

    try:
        print(f"\n--- Connecting to {device_name} ({device_params['host']}) ---")
        net_connect = ConnectHandler(**device_params)

        print(f"  Sending 'show ip interface brief' to {device_name}...")
        int_status_output = net_connect.send_command("show ip interface brief")
        active_interfaces = parse_active_interfaces(int_status_output)
        print(f"  Active Interfaces (Status: up, Protocol: up): {active_interfaces}")

        # --- Get Uptime ---
        print(f"  Sending 'show version' to {device_name}...")
        version_output = net_connect.send_command("show version")
        uptime = parse_uptime(version_output)
        print(f"  Device Uptime: {uptime if uptime else 'Uptime not found.'}")

    except Exception as e:
        print(f"!!! Error processing {device_name}: {e}")
    finally:
        if net_connect and net_connect.is_alive():
            net_connect.disconnect()
            print(f"  Disconnected from {device_name}.")

if __name__ == "__main__":
    print("Starting network information gathering script...\n")

    for device_name in device_creds:
        get_device_info(device_name)

    print("\n--- All Done :P ---")