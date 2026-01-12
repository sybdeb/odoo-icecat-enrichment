#!/bin/bash
# Icecat Product Enrichment - Deployment Script
# Tests and deploys both FREE and PRO modules to odoo19-prod

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FREE_MODULE="icecat_product_enrichment"
PRO_MODULE="icecat_enrichment_pro_unlock"
SERVER="sybren@nerbys-main"
ADDONS_PATH="/home/sybren/services/odoo19-prod/data/addons"
UPGRADE_SCRIPT="/home/sybren/scripts/upgrade_module.py"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}ICECAT ENRICHMENT - DEPLOYMENT${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Step 1: Test FREE module
echo -e "${YELLOW}→ Step 1: Testing FREE module...${NC}"
cd "/c/Users/Sybde/Projects/icecat-product-enrichment"
python tests/test_module.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ FREE module tests FAILED${NC}"
    exit 1
fi
echo -e "${GREEN}✓ FREE module tests PASSED${NC}"
echo ""

# Step 2: Test PRO module
echo -e "${YELLOW}→ Step 2: Testing PRO module...${NC}"
cd "/c/Users/Sybde/Projects/icecat-enrichment-pro-unlock"
python tests/test_module.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ PRO module tests FAILED${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PRO module tests PASSED${NC}"
echo ""

# Step 3: Backup current version
echo -e "${YELLOW}→ Step 3: Creating backup...${NC}"
BACKUP_DIR="/c/Users/Sybde/Projects/live versies/icecat_product_enrichment/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

ssh "$SERVER" "tar -czf /tmp/icecat_backup.tar.gz -C $ADDONS_PATH $FREE_MODULE $PRO_MODULE 2>/dev/null || true"
scp "$SERVER:/tmp/icecat_backup.tar.gz" "$BACKUP_DIR/" 2>/dev/null || echo "No existing modules to backup"
echo -e "${GREEN}✓ Backup created: $BACKUP_DIR${NC}"
echo ""

# Step 4: Deploy FREE module
echo -e "${YELLOW}→ Step 4: Deploying FREE module to server...${NC}"
rsync -av --delete \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='tests' \
    --exclude='deploy.sh' \
    "/c/Users/Sybde/Projects/icecat-product-enrichment/" \
    "$SERVER:$ADDONS_PATH/$FREE_MODULE/"
echo -e "${GREEN}✓ FREE module deployed${NC}"
echo ""

# Step 5: Deploy PRO module
echo -e "${YELLOW}→ Step 5: Deploying PRO module to server...${NC}"
rsync -av --delete \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='tests' \
    "/c/Users/Sybde/Projects/icecat-enrichment-pro-unlock/" \
    "$SERVER:$ADDONS_PATH/$PRO_MODULE/"
echo -e "${GREEN}✓ PRO module deployed${NC}"
echo ""

# Step 6: Set permissions
echo -e "${YELLOW}→ Step 6: Setting permissions...${NC}"
ssh "$SERVER" "sudo chown -R 101:101 $ADDONS_PATH/$FREE_MODULE $ADDONS_PATH/$PRO_MODULE"
ssh "$SERVER" "sudo chmod -R 755 $ADDONS_PATH/$FREE_MODULE $ADDONS_PATH/$PRO_MODULE"
echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

# Step 7: Upgrade modules
echo -e "${YELLOW}→ Step 7: Upgrading modules in Odoo...${NC}"
echo -e "${YELLOW}  Upgrading FREE module...${NC}"
ssh "$SERVER" "python3 $UPGRADE_SCRIPT prod $FREE_MODULE"
echo -e "${GREEN}✓ FREE module upgraded${NC}"

echo -e "${YELLOW}  Upgrading PRO module...${NC}"
ssh "$SERVER" "python3 $UPGRADE_SCRIPT prod $PRO_MODULE || echo 'Pro module not installed yet (normal on first deploy)'"
echo -e "${GREEN}✓ PRO module upgrade attempted${NC}"
echo ""

# Step 8: Verify deployment
echo -e "${YELLOW}→ Step 8: Verifying deployment...${NC}"
ssh "$SERVER" "docker logs odoo19-prod-web-1 --tail 50 | grep -i 'icecat' || true"
echo -e "${GREEN}✓ Deployment verification complete${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}DEPLOYMENT SUCCESSFUL!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test in browser: http://nerbys-main:19089"
echo "2. Check FREE features: Manual sync per product"
echo "3. Check PRO gating: Bulk operations should show upgrade message"
echo "4. Install PRO module to test unlock functionality"
echo ""
