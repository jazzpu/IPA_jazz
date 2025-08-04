import os
from netmiko import ConnectHandler

# --- Device Connection Details ---
PRIVATE_KEY_FILE = os.path.expanduser("~/.ssh/admin_key")

devices = {
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
    },
    # entering S1-P from the MGMT VLAN 99 ip address
    "S1-P": {
        "device_type": "cisco_ios",
        "host": "172.31.42.3",
        "username": "admin",
        "use_keys": True,
        "key_file": PRIVATE_KEY_FILE,
        "secret": "",
    },
}

# 1. Configure VLAN 101 for control/data plane on S1 to separate management and control plane.
# Based on your S1-P show run, VLAN 101 exists, and Gi0/1 and Gi0/2 are already assigned.
# No IP address is needed on Vlan101 if S1 is just switching this VLAN.
s1_vlan_101_config = [
    "vlan 101",
    "name Control_Data_Plane",
    "interface range GigabitEthernet0/1-2",
    "switchport mode access",
    "switchport access vlan 101",
]

# 2. Configure OSPF on R1 and R2 on control/data plane. All interfaces in control/data plane
# (except G0/3 of R2) and loopback interfaces are in area 0
r1_ospf_config = [
    "router ospf 1 vrf Control-Data",
    "network 10.42.1.0 0.0.0.255 area 0",
    "network 10.42.2.0 0.0.0.255 area 0",
]

r2_ospf_config = [
    "router ospf 1 vrf Control-Data",
    "network 10.42.2.0 0.0.0.255 area 0",
    "network 10.42.3.0 0.0.0.255 area 0",
]

# 3. Advertise a default route to the NAT cloud on R2 into the OSPF at R2.
# This command must be placed under the specific OSPF VRF process.
# Your R2-P show run already has 'default-information originate' under 'router ospf 1 vrf Control-Data'.
r2_default_route_ospf_vrf_config = [
    "router ospf 1 vrf Control-Data",
    "default-information originate", # This is the command that advertises the default route within the VRF's OSPF process
]

# 4. Configure PAT on R2.
# Your R2-P show run already has all PAT configurations.
r2_pat_config = [
    "access-list 101 permit ip 10.42.1.0 0.0.0.255 any",
    "access-list 101 permit ip 10.42.2.0 0.0.0.255 any",
    "access-list 101 permit ip 10.42.3.0 0.0.0.255 any",
    "interface GigabitEthernet0/1",
    "ip nat inside",
    "interface GigabitEthernet0/2",
    "ip nat inside",
    "interface GigabitEthernet0/3",
    "ip nat outside",
    "ip nat inside source list 101 interface GigabitEthernet0/3 vrf Control-Data overload",
]

# --- Main Script Logic ---
def configure_device(device_name, commands):
    """Connects to a device and sends configuration commands."""
    device_params = devices[device_name]
    try:
        print(f"\n--- Connecting to {device_name} ({device_params['host']}) ---")
        net_connect = ConnectHandler(**device_params)
        net_connect.enable()
        print(f"Sending commands to {device_name}:")
        output = net_connect.send_config_set(commands)
        print(output)
        net_connect.save_config()
        print(f"--- Configuration on {device_name} complete and saved ---")
    except Exception as e:
        print(f"!!! Error configuring {device_name}: {e}")
    finally:
        if 'net_connect' in locals() and net_connect.is_alive():
            net_connect.disconnect()

if __name__ == "__main__":
    print("Starting Netmiko configuration script (strict to instructions)...\n")

    # S1-P: Configure VLAN 101
    configure_device("S1-P", s1_vlan_101_config)

    # R1-P: Configure OSPF
    configure_device("R1-P", r1_ospf_config)

    # R2-P: Configure OSPF, Default Route (VRF), and PAT
    # The default-information originate is specifically for the VRF's OSPF process
    r2_all_commands = r2_ospf_config + r2_default_route_ospf_vrf_config + r2_pat_config
    configure_device("R2-P", r2_all_commands)

    print("\n--- All specified configurations attempted ---")
    print("Please verify configurations and check connectivity as per checkpoint list.")