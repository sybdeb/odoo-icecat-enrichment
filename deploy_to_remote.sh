#!/bin/bash
# Deploy script for dbw_product_enrichment module

echo "=== Deploying DBW Product Enrichment Module ==="
echo ""

# Step 1: Create tar archive
echo "[1/4] Creating tar archive..."
cd "$(dirname "$0")"
tar -czf /tmp/dbw_enrichment.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='*.tar.gz' \
    .
echo "✓ Archive created"

# Step 2: Upload to server
echo "[2/4] Uploading to remote server..."
scp /tmp/dbw_enrichment.tar.gz hetzner-sybren:/tmp/
echo "✓ Upload complete"

# Step 3: Deploy in container
echo "[3/4] Deploying in Docker container..."
ssh hetzner-sybren << 'ENDSSH'
docker cp /tmp/dbw_enrichment.tar.gz odoo19-dev-web-1:/tmp/
docker exec -u root odoo19-dev-web-1 bash -c '
    cd /mnt/extra-addons/dbw_product_enrichment
    rm -rf *
    tar -xzf /tmp/dbw_enrichment.tar.gz
    chown -R odoo:odoo /mnt/extra-addons/dbw_product_enrichment
    echo "Files deployed successfully"
'
ENDSSH
echo "✓ Deployment complete"

# Step 4: Restart Odoo
echo "[4/4] Restarting Odoo container..."
ssh hetzner-sybren 'docker restart odoo19-dev-web-1'
echo "✓ Odoo restarted"

echo ""
echo "=== Deployment Complete ==="
echo "Module is now live at: http://YOUR_SERVER:19069"
echo ""
echo "Next steps:"
echo "1. Login to Odoo"
echo "2. Go to Apps > Upgrade module 'DBW Product Enrichment'"
echo "3. Test by syncing a product with Icecat"
echo ""
