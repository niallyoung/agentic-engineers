#!/bin/bash
# Setup msmtp with macOS Keychain credential storage

set -e

echo "=== msmtp + Keychain Setup ==="
echo

# Step 1: Install msmtp via brew
echo "[1/4] Installing msmtp..."
if command -v msmtp &> /dev/null; then
    echo "  ✓ msmtp already installed"
else
    brew install msmtp
    echo "  ✓ msmtp installed"
fi

echo

# Step 2: Create msmtp config directory
echo "[2/4] Creating msmtp config..."
mkdir -p ~/.msmtprc.d
chmod 700 ~/.msmtprc.d

# Create main config (credentials stored in Keychain, not file)
cat > ~/.msmtprc << 'EOF'
# msmtp configuration with macOS Keychain integration
# Run: setup-msmtp.sh to add credentials

defaults
auth           on
tls            on
tls_trust_file /usr/local/etc/openssl@3/certs/ca-certificates.crt
logfile        ~/.msmtp.log

# ERS Automation SMTP account
# Credentials stored in macOS Keychain via security command
account ers
host           PLACEHOLDER_SMTP_HOST
port           587
from           PLACEHOLDER_EMAIL
user           PLACEHOLDER_EMAIL
passwordeval   "security find-generic-password -s msmtp-ers -w"

# Set default account
account default : ers
EOF

chmod 600 ~/.msmtprc
echo "  ✓ Config created: ~/.msmtprc"

echo

# Step 3: Add credentials to Keychain
echo "[3/4] macOS Keychain credential storage"
echo

read -p "Enter SMTP host (e.g., smtp.gmail.com): " SMTP_HOST
read -p "Enter SMTP email/username: " SMTP_USER
read -p "Enter SMTP password (or app-specific password for Gmail): " SMTP_PASS

# Validate inputs
if [ -z "$SMTP_HOST" ] || [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASS" ]; then
    echo "❌ Missing required fields"
    exit 1
fi

# Store in Keychain
security add-generic-password -s "msmtp-ers" -a "$SMTP_USER" -w "$SMTP_PASS" -U 2>/dev/null || \
security add-generic-password -s "msmtp-ers" -a "$SMTP_USER" -w "$SMTP_PASS" -U

echo "  ✓ Credentials stored in Keychain"
echo "    Service: msmtp-ers"
echo "    Account: $SMTP_USER"

# Update config with actual values
sed -i '' "s|PLACEHOLDER_SMTP_HOST|$SMTP_HOST|g" ~/.msmtprc
sed -i '' "s|PLACEHOLDER_EMAIL|$SMTP_USER|g" ~/.msmtprc

echo

# Step 4: Test the setup
echo "[4/4] Testing msmtp connection..."
echo "Sending test email to $SMTP_USER..."

TEST_EMAIL="From: $SMTP_USER
To: $SMTP_USER
Subject: msmtp Test
Date: $(date -R)

This is a test from msmtp setup on $(hostname).
"

echo "$TEST_EMAIL" | msmtp -a ers "$SMTP_USER" 2>&1 && {
    echo "  ✓ Test email sent successfully"
} || {
    echo "  ⚠ Test failed - check credentials and SMTP settings"
    echo "  Debug: tail -f ~/.msmtp.log"
}

echo
echo "=== Setup Complete ==="
echo
echo "Your credentials are now secure in macOS Keychain:"
echo "  security find-generic-password -s msmtp-ers -w"
echo
echo "Next step:"
echo "  Update your cron jobs to use: | msmtp -a ers recipient@example.com"
echo
