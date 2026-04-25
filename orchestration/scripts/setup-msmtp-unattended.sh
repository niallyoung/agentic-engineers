#!/bin/bash
# Setup msmtp for 24/7 unattended cron operation
# Stores password in plaintext file with OS-level protection (600 permissions)
# Alternative: use .bash_profile with environment variables

set -e

CREDS_FILE="$HOME/.msmtp-credentials"

echo "=== msmtp Unattended Setup (for cron) ==="
echo
echo "Password stored in: $CREDS_FILE (plaintext, 600 permissions)"
echo "Protected by: OS file permissions (only you can read)"
echo

# Step 1: Get credentials
echo "[1/3] Enter SMTP credentials..."
read -p "SMTP Host (e.g., smtp.themessagingco.com.au): " SMTP_HOST
read -p "SMTP User/Email: " SMTP_USER
read -sp "SMTP Password (hidden): " SMTP_PASS
echo

# Step 2: Create credentials file (plaintext, protected by OS)
cat > "$CREDS_FILE" << EOF
# msmtp Credentials (protected by 600 file permissions)
# DO NOT COMMIT TO GIT
SMTP_HOST=$SMTP_HOST
SMTP_USER=$SMTP_USER
SMTP_PASS=$SMTP_PASS
EOF

chmod 600 "$CREDS_FILE"

echo "✓ Credentials file created: $CREDS_FILE"
echo "  Permissions: $(ls -l $CREDS_FILE | awk '{print $1}')"
echo

# Step 3: Update msmtp config
echo "[2/3] Updating msmtp config..."

# Create config if doesn't exist
if [ ! -f ~/.msmtprc ]; then
    cat > ~/.msmtprc << 'EOF'
defaults
auth           on
tls            on
tls_trust_file /usr/local/etc/openssl@3/certs/ca-certificates.crt
logfile        ~/.msmtp.log

account ers
host           PLACEHOLDER_HOST
port           587
from           PLACEHOLDER_USER
user           PLACEHOLDER_USER
passwordeval   "grep '^SMTP_PASS=' ~/.msmtp-credentials | cut -d= -f2"

account default : ers
EOF
    chmod 600 ~/.msmtprc
fi

# Update config with actual values
sed -i '' "s|PLACEHOLDER_HOST|$SMTP_HOST|g" ~/.msmtprc
sed -i '' "s|PLACEHOLDER_USER|$SMTP_USER|g" ~/.msmtprc

echo "✓ Config updated: ~/.msmtprc"
echo

# Step 4: Test decryption (reading from file)
echo "[3/3] Testing password retrieval..."

TEST_PASS=$(grep '^SMTP_PASS=' "$CREDS_FILE" | cut -d= -f2)

if [ "$TEST_PASS" = "$SMTP_PASS" ]; then
    echo "✓ Password retrieval working"
else
    echo "❌ Password retrieval failed"
    rm "$CREDS_FILE"
    exit 1
fi

echo

# Step 5: Test SMTP connection
echo "[4/4] Testing msmtp connection..."

TEST_EMAIL="From: $SMTP_USER
To: $SMTP_USER
Subject: msmtp Unattended Test
Date: $(date -R)

This is a test from msmtp unattended setup on $(hostname).
If you received this, cron jobs can now send emails 24/7."

echo "$TEST_EMAIL" | msmtp -a ers "$SMTP_USER" 2>&1 && {
    echo "✓ Test email sent successfully"
    echo
    echo "=== Setup Complete ==="
    echo
    echo "Credentials stored at: $CREDS_FILE"
    echo "  - Plaintext (simple, reliable)"
    echo "  - Protected by OS: chmod 600 (only you can read)"
    echo "  - Works 24/7 without prompts"
    echo "  - Fast (no encryption overhead)"
    echo
    echo "Security note:"
    echo "  - Same security model as environment variables"
    echo "  - File is readable only by you (600 permissions enforced by OS)"
    echo "  - If someone gets your account, they can read it"
    echo "  - Use app-specific password (Gmail, etc.) for extra safety"
    echo
    echo "Next step:"
    echo "  crontab -e"
    echo "  Add: */5 * * * * cd /home/user/git/ers/{service-name} && bash agentic-engineers/orchestration/scripts/process-log-queue.sh"
    echo
} || {
    echo "❌ Test failed"
    echo "  Credentials file saved: $CREDS_FILE"
    echo "  Check credentials: cat $CREDS_FILE"
    echo "  Check msmtp config: cat ~/.msmtprc"
    echo "  Debug logs: tail -f ~/.msmtp.log"
    echo "  Fix config and retry: echo 'test' | msmtp -v -a ers user@example.com"
    exit 1
}
