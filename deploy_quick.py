#!/usr/bin/env python3
"""
Quick deployment script - deploys modules to odoo19-prod via SSH
"""
import os
import subprocess
import sys

SERVER = "sybren@hetzner-sybren"
ADDONS_PATH = "/home/sybren/services/odoo19-prod/data/addons"

def run_ssh(command):
    """Run SSH command"""
    full_cmd = f'ssh {SERVER} "{command}"'
    print(f"→ {command}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"✗ Error: {result.stderr}")
        return False
    if result.stdout:
        print(result.stdout)
    return True

def deploy_module(local_path, module_name):
    """Deploy a single module"""
    print(f"\n→ Deploying {module_name}...")
    
    # Create temp tar (exclude unnecessary files)
    tar_file = f"/tmp/{module_name}.tar.gz"
    exclude_patterns = [
        "--exclude='*.pyc'",
        "--exclude='__pycache__'",
        "--exclude='.git'",
        "--exclude='tests'",
        "--exclude='deploy.sh'",
        "--exclude='*.md'"
    ]
    
    tar_cmd = f"cd '{local_path}' && tar {' '.join(exclude_patterns)} -czf {tar_file} ."
    result = subprocess.run(tar_cmd, shell=True)
    if result.returncode != 0:
        print(f"✗ Failed to create tar for {module_name}")
        return False
    
    print(f"✓ Tar created: {tar_file}")
    
    # Upload to server
    scp_cmd = f"scp {tar_file} {SERVER}:/tmp/{module_name}.tar.gz"
    result = subprocess.run(scp_cmd, shell=True)
    if result.returncode != 0:
        print(f"✗ Failed to upload {module_name}")
        return False
    
    print(f"✓ Uploaded to server")
    
    # Extract on server with sudo
    extract_cmd = (
        f"sudo rm -rf {ADDONS_PATH}/{module_name} && "
        f"sudo mkdir -p {ADDONS_PATH}/{module_name} && "
        f"sudo tar -xzf /tmp/{module_name}.tar.gz -C {ADDONS_PATH}/{module_name}/ && "
        f"sudo chown -R 101:101 {ADDONS_PATH}/{module_name} && "
        f"sudo chmod -R 755 {ADDONS_PATH}/{module_name} && "
        f"rm /tmp/{module_name}.tar.gz"
    )
    
    if not run_ssh(extract_cmd):
        return False
    
    print(f"✓ {module_name} deployed and permissions set")
    return True

def upgrade_module(module_name):
    """Upgrade module via RPC script"""
    print(f"\n→ Upgrading {module_name}...")
    upgrade_cmd = f"python3 /home/sybren/scripts/upgrade_module.py prod {module_name}"
    if not run_ssh(upgrade_cmd):
        print(f"⚠ Upgrade failed (module might not be installed yet)")
    else:
        print(f"✓ {module_name} upgraded")

def main():
    print("=" * 60)
    print("ICECAT ENRICHMENT - QUICK DEPLOYMENT")
    print("=" * 60)
    
    # Deploy FREE module
    if not deploy_module(
        "/c/Users/Sybde/Projects/icecat-product-enrichment",
        "icecat_product_enrichment"
    ):
        sys.exit(1)
    
    # Deploy PRO module  
    if not deploy_module(
        "/c/Users/Sybde/Projects/icecat-enrichment-pro-unlock",
        "icecat_enrichment_pro_unlock"
    ):
        sys.exit(1)
    
    # Upgrade modules
    upgrade_module("icecat_product_enrichment")
    upgrade_module("icecat_enrichment_pro_unlock")
    
    print("\n" + "=" * 60)
    print("✓ DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Test in browser: http://hetzner-sybren:19068")
    print("2. Check module: Apps → Search 'Icecat'")
    print("3. Test FREE features: Manual sync per product")
    print("4. Install PRO to test unlock")
    print()

if __name__ == '__main__':
    main()
