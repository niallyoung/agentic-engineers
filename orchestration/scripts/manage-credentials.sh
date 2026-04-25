#!/bin/bash
# Manage msmtp credentials in macOS Keychain
# Can be used via terminal or opened in Keychain Access GUI

SERVICE="msmtp-ers"

usage() {
    cat << EOF
msmtp Credential Manager

Usage:
  $0 [COMMAND]

Commands:
  add              Add/update credentials interactively
  gui              Open Keychain Access GUI to manage credentials
  view             View stored credentials (masked password)
  test             Test SMTP connection
  delete           Remove credentials from Keychain
  setup            Run full msmtp setup (interactive)

Examples:
  $0 add                 # Interactive credential entry
  $0 gui                 # Open Keychain Access GUI
  $0 view                # Show what's stored
  $0 test                # Send test email

EOF
    exit 1
}

cmd_add() {
    echo "Add/Update msmtp Credentials"
    echo "================================"
    echo

    read -p "SMTP Host (e.g., smtp.gmail.com): " SMTP_HOST
    read -p "SMTP User/Email: " SMTP_USER
    read -sp "SMTP Password (hidden): " SMTP_PASS
    echo

    if [ -z "$SMTP_HOST" ] || [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASS" ]; then
        echo "❌ Aborted: missing required fields"
        return 1
    fi

    # Update/create credentials in Keychain
    security add-generic-password -s "$SERVICE" -a "$SMTP_USER" -w "$SMTP_PASS" -U 2>/dev/null || {
        # Try with -U flag for update
        security delete-generic-password -s "$SERVICE" 2>/dev/null || true
        security add-generic-password -s "$SERVICE" -a "$SMTP_USER" -w "$SMTP_PASS"
    }

    # Update msmtp config
    if [ -f ~/.msmtprc ]; then
        sed -i '' "s|^host.*|host           $SMTP_HOST|g" ~/.msmtprc
        sed -i '' "s|^from.*|from           $SMTP_USER|g" ~/.msmtprc
        sed -i '' "s|^user.*|user           $SMTP_USER|g" ~/.msmtprc
    fi

    echo "✓ Credentials stored in Keychain"
    echo "  Service: $SERVICE"
    echo "  User: $SMTP_USER"
    echo "  Host: $SMTP_HOST"
    echo
}

cmd_gui() {
    echo "Opening Keychain Access..."
    open /Applications/Utilities/Keychain\ Access.app
    echo
    echo "To manage msmtp credentials:"
    echo "  1. Search for: $SERVICE"
    echo "  2. Double-click entry"
    echo "  3. Check 'Show password' (you'll need to authenticate)"
    echo "  4. Update as needed"
    echo
}

cmd_view() {
    echo "Stored msmtp Credentials"
    echo "================================"
    echo

    ACCOUNT=$(security find-generic-password -s "$SERVICE" -w 2>/dev/null | head -1)
    if [ $? -eq 0 ]; then
        ACCOUNT=$(security find-generic-password -s "$SERVICE" -a 2>/dev/null | grep "acct" | sed 's/.*acct=//')
        echo "Service: $SERVICE"
        echo "Account: $ACCOUNT"
        echo "Password: ••••••••"
        echo
        echo "✓ Credentials found in Keychain"
    else
        echo "❌ No credentials found for: $SERVICE"
        echo
        echo "Run: $0 add"
    fi
    echo
}

cmd_test() {
    echo "Testing msmtp SMTP Connection"
    echo "================================"
    echo

    if [ ! -f ~/.msmtprc ]; then
        echo "❌ Config file not found: ~/.msmtprc"
        echo "Run: $0 setup"
        return 1
    fi

    SMTP_USER=$(grep "^from" ~/.msmtprc | awk '{print $NF}')

    if [ -z "$SMTP_USER" ]; then
        echo "❌ No email found in config"
        return 1
    fi

    echo "Sending test email to: $SMTP_USER"
    echo

    TEST_EMAIL="From: $SMTP_USER
To: $SMTP_USER
Subject: msmtp Connection Test
Date: $(date -R)
Message-ID: <test-$(date +%s)@$(hostname)>

This is a test email from msmtp setup on $(hostname).
If you received this, your SMTP credentials are working correctly.
"

    echo "$TEST_EMAIL" | msmtp -a ers "$SMTP_USER" 2>&1 && {
        echo
        echo "✓ Test email sent successfully!"
        echo "  Check your inbox"
    } || {
        echo
        echo "❌ Test failed. Debug:"
        echo "  tail -f ~/.msmtp.log"
        echo "  security find-generic-password -s $SERVICE -w"
        return 1
    }
    echo
}

cmd_delete() {
    echo "Delete msmtp Credentials"
    echo "================================"
    echo

    read -p "Are you sure? This will remove credentials from Keychain (y/N): " CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "Aborted"
        return 0
    fi

    security delete-generic-password -s "$SERVICE" 2>/dev/null && {
        echo "✓ Credentials removed from Keychain"
    } || {
        echo "❌ Failed to remove credentials (may not exist)"
        return 1
    }
    echo
}

cmd_setup() {
    bash "$(dirname "$0")/setup-msmtp.sh"
}

# Main
case "${1:-add}" in
    add)     cmd_add ;;
    gui)     cmd_gui ;;
    view)    cmd_view ;;
    test)    cmd_test ;;
    delete)  cmd_delete ;;
    setup)   cmd_setup ;;
    *)       usage ;;
esac
