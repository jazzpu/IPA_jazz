import paramiko
import time

# Router login details
router = {
    "hostname": "172.31.42.5",      # Replace with your router's IP
    "username": "admin",
    "port": 22
}

def ssh_into_router(router):
    try:
        # Load private key (not public key!)
        private_key = paramiko.RSAKey.from_private_key_file("/home/devasc/.ssh/admin_key")

        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect using key, no password
        client.connect(
            hostname=router["hostname"],
            port=router["port"],
            username=router["username"],
            pkey=private_key,
            look_for_keys=False,
            allow_agent=False
        )

        # Open an interactive shell
        shell = client.invoke_shell()
        time.sleep(1)

        # Send commands
        shell.send("terminal length 0\n")
        time.sleep(0.5)
        shell.send("show ip interface brief\n")
        time.sleep(1)

        # Get output
        output = shell.recv(65535).decode("utf-8")
        print(output)

        # Close connection
        client.close()

    except Exception as e:
        print(f"❌ Failed to connect: {e}")

if __name__ == "__main__":
    ssh_into_router(router)
