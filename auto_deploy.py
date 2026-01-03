#!/usr/bin/env python3
"""
Automated deployment script for Inventory Management System
Deploys to Hetzner VPS using paramiko (Python SSH library)
"""

import paramiko
import os
import sys
from stat import S_IEXEC

# VPS Configuration
VPS_HOST = "5.223.54.209"
VPS_USER = "root"
VPS_PASSWORD = "t0573066F"
REMOTE_DIR = "/root/inventory-system"

def create_ssh_client():
    """Create and return SSH client"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"Connecting to {VPS_HOST}...")
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)
    print("✓ Connected successfully")

    return client

def execute_command(client, command, description=""):
    """Execute command on remote server"""
    if description:
        print(f"\n{description}...")

    stdin, stdout, stderr = client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode()
    error = stderr.read().decode()

    if exit_status != 0:
        print(f"✗ Error: {error}")
        return False

    if output:
        print(output)

    if description:
        print(f"✓ {description} completed")

    return True

def upload_file(sftp, local_path, remote_path, description=""):
    """Upload file to remote server"""
    if description:
        print(f"\n{description}...")

    try:
        sftp.put(local_path, remote_path)
        if description:
            print(f"✓ {description} completed")
        return True
    except Exception as e:
        print(f"✗ Error uploading {local_path}: {e}")
        return False

def main():
    print("="*50)
    print("Inventory System - Automated Deployment")
    print("="*50)

    # Check if required files exist
    required_files = [
        'inventory_monitor.py',
        'requirements.txt',
        'run_inventory.sh'
    ]

    for file in required_files:
        if not os.path.exists(file):
            print(f"✗ Error: {file} not found!")
            sys.exit(1)

    try:
        # Create SSH client
        client = create_ssh_client()
        sftp = client.open_sftp()

        # Step 1: Create directory structure
        execute_command(
            client,
            f"mkdir -p {REMOTE_DIR}/attachments",
            "Creating directory structure"
        )

        # Step 2: Upload files
        upload_file(sftp, 'inventory_monitor.py', f'{REMOTE_DIR}/inventory_monitor.py',
                   "Uploading inventory_monitor.py")
        upload_file(sftp, 'requirements.txt', f'{REMOTE_DIR}/requirements.txt',
                   "Uploading requirements.txt")
        upload_file(sftp, 'run_inventory.sh', f'{REMOTE_DIR}/run_inventory.sh',
                   "Uploading run_inventory.sh")

        if os.path.exists('README.md'):
            upload_file(sftp, 'README.md', f'{REMOTE_DIR}/README.md',
                       "Uploading README.md")

        # Step 3: Copy service account
        execute_command(
            client,
            f"cp /root/invoice-bot/service-account.json {REMOTE_DIR}/",
            "Copying service account"
        )

        # Step 4: Set permissions
        execute_command(
            client,
            f"chmod +x {REMOTE_DIR}/run_inventory.sh {REMOTE_DIR}/inventory_monitor.py",
            "Setting file permissions"
        )

        # Step 5: Install dependencies
        print("\nInstalling Python dependencies (this may take a minute)...")
        execute_command(
            client,
            f"cd {REMOTE_DIR} && pip3 install -r requirements.txt --break-system-packages",
            "Installing dependencies"
        )

        # Step 6: Verify installation
        print("\nVerifying installation...")
        execute_command(client, f"ls -la {REMOTE_DIR}/")

        sftp.close()
        client.close()

        print("\n" + "="*50)
        print("✓ Deployment Successful!")
        print("="*50)
        print("\nNext steps:")
        print("1. Get your Telegram Chat ID:")
        print("   curl https://api.telegram.org/bot7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ/getUpdates")
        print("\n2. SSH to VPS and update Chat ID:")
        print(f"   ssh {VPS_USER}@{VPS_HOST}")
        print(f"   nano {REMOTE_DIR}/run_inventory.sh")
        print("   # Update TELEGRAM_CHAT_ID line")
        print("\n3. Start the system:")
        print("   tmux new -s inventory-bot")
        print(f"   cd {REMOTE_DIR}")
        print("   ./run_inventory.sh")
        print("   # Press Ctrl+B then D to detach")
        print("\n4. Monitor logs:")
        print(f"   tail -f {REMOTE_DIR}/inventory.log")

    except Exception as e:
        print(f"\n✗ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
