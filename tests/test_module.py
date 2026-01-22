#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Icecat Product Enrichment - Module Tests
Validates module before deployment to production
"""

import os
import sys
import py_compile
import xml.etree.ElementTree as ET
from pathlib import Path

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{YELLOW}→ {msg}{RESET}")

def test_python_syntax():
    """Test all Python files compile without syntax errors"""
    print_info("Testing Python syntax...")
    
    module_path = Path(__file__).parent.parent
    python_files = list(module_path.glob('**/*.py'))
    
    errors = []
    for py_file in python_files:
        if '__pycache__' in str(py_file):
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
            print_success(f"Python syntax OK: {py_file.relative_to(module_path)}")
        except Exception as e:
            errors.append(f"{py_file.relative_to(module_path)}: {e}")
            print_error(f"Python syntax ERROR: {py_file.relative_to(module_path)}")
    
    return errors

def test_xml_syntax():
    """Test all XML files are valid"""
    print_info("Testing XML syntax...")
    
    module_path = Path(__file__).parent.parent
    xml_files = list(module_path.glob('**/*.xml'))
    
    errors = []
    for xml_file in xml_files:
        try:
            ET.parse(str(xml_file))
            print_success(f"XML syntax OK: {xml_file.relative_to(module_path)}")
        except Exception as e:
            errors.append(f"{xml_file.relative_to(module_path)}: {e}")
            print_error(f"XML syntax ERROR: {xml_file.relative_to(module_path)}")
    
    return errors

def test_manifest():
    """Test manifest file is valid"""
    print_info("Testing manifest file...")
    
    module_path = Path(__file__).parent.parent
    manifest_file = module_path / '__manifest__.py'
    
    if not manifest_file.exists():
        return ["Manifest file not found"]
    
    try:
        with open(manifest_file, 'r', encoding='utf-8') as f:
            content = f.read()
            manifest = eval(content)
        
        # Check required fields
        required_fields = ['name', 'version', 'depends', 'data']
        missing = [f for f in required_fields if f not in manifest]
        
        if missing:
            return [f"Missing required fields: {', '.join(missing)}"]
        
        # Check version format
        version = manifest['version']
        if not version.startswith('19.0.'):
            return [f"Invalid version format: {version} (expected 19.0.x.x.x)"]
        
        print_success(f"Manifest OK: {manifest['name']} v{version}")
        return []
    except Exception as e:
        return [f"Manifest parse error: {e}"]

def test_pro_gating():
    """Test that Pro features are properly gated"""
    print_info("Testing Pro feature gating...")
    
    module_path = Path(__file__).parent.parent
    errors = []
    
    # Check cron jobs are disabled by default
    cron_file = module_path / 'data' / 'ir_cron_data.xml'
    if cron_file.exists():
        with open(cron_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if '<field name="active">True</field>' in content:
                errors.append("Cron jobs must be disabled by default (active=False)")
                print_error("Cron jobs are ENABLED by default (should be False)")
            else:
                print_success("Cron jobs disabled by default")
    
    # Check Pro checks in cron methods
    product_template = module_path / 'models' / 'product_template.py'
    if product_template.exists():
        with open(product_template, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if 'icecat_enrichment_pro_unlock' in content:
                print_success("Pro checks found in product_template.py")
            else:
                errors.append("Missing Pro version checks in cron methods")
                print_error("No Pro checks in product_template.py")
    
    # Check Pro checks in wizard
    wizard = module_path / 'wizards' / 'icecat_sync_wizard.py'
    if wizard.exists():
        with open(wizard, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if 'icecat_enrichment_pro_unlock' in content:
                print_success("Pro checks found in icecat_sync_wizard.py")
            else:
                errors.append("Missing Pro version checks in wizard")
                print_error("No Pro checks in wizard")
    
    return errors

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("ICECAT PRODUCT ENRICHMENT - MODULE TESTS")
    print("="*60 + "\n")
    
    all_errors = []
    
    # Test Python syntax
    errors = test_python_syntax()
    all_errors.extend(errors)
    
    print()
    
    # Test XML syntax
    errors = test_xml_syntax()
    all_errors.extend(errors)
    
    print()
    
    # Test manifest
    errors = test_manifest()
    all_errors.extend(errors)
    
    print()
    
    # Test Pro gating
    errors = test_pro_gating()
    all_errors.extend(errors)
    
    print("\n" + "="*60)
    if all_errors:
        print_error(f"TESTS FAILED: {len(all_errors)} error(s) found")
        print("="*60 + "\n")
        for error in all_errors:
            print(f"  - {error}")
        print()
        sys.exit(1)
    else:
        print_success("ALL TESTS PASSED")
        print("="*60 + "\n")
        print_info("Module is ready for deployment!")
        print()
        sys.exit(0)

if __name__ == '__main__':
    main()
