---
name: msmtp-setup
description: Setup and credential management for msmtp SMTP relay with macOS Keychain
---

# msmtp Setup Guide

Lightweight SMTP relay for ERS automation alerts. Credentials stored securely in macOS Keychain.

---

## Quick Start

### 1. Run Full Setup (Interactive)

```bash
bash agentic-engineers/orchestration/scripts/setup-msmtp.sh
```

This will:
- Install msmtp via brew
- Create ~/.msmtprc config
- Store credentials in Keychain
- Send test email to verify

### 2. Manage Credentials (Terminal or GUI)

#### Terminal: Add/Update Credentials

```bash
bash agentic-engineers/orchestration/scripts/manage-credentials.sh add
```

Then answer prompts:
```
SMTP Host (e.g., smtp.gmail.com): smtp.gmail.com
SMTP User/Email: your-email@gmail.com
SMTP Password (hidden): ••••••••
```

#### GUI: Open Keychain Access

```bash
bash agentic-engineers/orchestration/scripts/manage-credentials.sh gui
```

Then in Keychain Access:
1. Search for: `msmtp-ers`
2. Double-click entry
3. Check "Show password" (macOS will ask for your password)
4. View or edit credentials

---

## Manual Setup (If Needed)

### Install msmtp

```bash
brew install msmtp
```

### Create Config

```bash
mkdir -p ~/.msmtprc.d
cat > ~/.msmtprc << 'EOF'
defaults
auth           on
tls            on
tls_trust_file /usr/local/etc/openssl@3/certs/ca-certificates.crt
logfile        ~/.msmtp.log

account ers
host           smtp.gmail.com
port           587
from           your-email@gmail.com
user           your-email@gmail.com
passwordeval   "security find-generic-password -s msmtp-ers -w"

account default : ers
EOF

chmod 600 ~/.msmtprc
```

### Store Credentials in Keychain

```bash
security add-generic-password -s "msmtp-ers" -a "your-email@gmail.com" -w "your-app-password"
```

**Note:** For Gmail, use an [app-specific password](https://myaccount.google.com/apppasswords), not your regular password.

---

## Verify Setup

### View Stored Credentials

```bash
bash agentic-engineers/orchestration/scripts/manage-credentials.sh view
```

Output:
```
Stored msmtp Credentials
Service: msmtp-ers
Account: your-email@gmail.com
Password: ••••••••

✓ Credentials found in Keychain
```

### Test SMTP Connection

```bash
bash agentic-engineers/orchestration/scripts/manage-credentials.sh test
```

Sends a test email to verify everything works.

### Manual Test

```bash
echo "To: your-email@gmail.com
Subject: Test Email
Date: $(date -R)

This is a test." | msmtp -a ers your-email@gmail.com
```

### Debug

```bash
# Check credentials are in Keychain
security find-generic-password -s msmtp-ers -w

# View msmtp logs
tail -f ~/.msmtp.log

# Test with verbose output
echo "test" | msmtp -v -a ers your-email@gmail.com
```

---

## How It Works

### Credential Storage (Secure)

```bash
# Retrieve password from Keychain (msmtp config uses this)
security find-generic-password -s msmtp-ers -w
```

The password is **never** stored in config files. It's:
- Encrypted in macOS Keychain
- Only decrypted when msmtp requests it
- Protected by your macOS login password

### Alert Email Flow

```
Cron Job
  ↓
Generates alert JSON → QUEUE/pending/
  ↓
Queue Processor (every 5 min)
  ↓
Reads alert JSON
  ↓
should_email=true?
  ↓
send-alert-email.sh
  ↓
msmtp (reads password from Keychain)
  ↓
SMTP (smtp.gmail.com or your provider)
  ↓
Your Inbox
```

---

## Gmail Setup (Most Common)

### 1. Enable 2-Factor Authentication

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable "2-Step Verification"

### 2. Create App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select "Mail" and "macOS"
3. Copy the generated 16-character password
4. Use this in setup: `bash manage-credentials.sh add`

### 3. msmtp Config

```bash
# Run setup
bash agentic-engineers/orchestration/scripts/setup-msmtp.sh

# When prompted:
SMTP Host: smtp.gmail.com
SMTP User: your-email@gmail.com
SMTP Password: [16-char app password from Gmail]
```

---

## Other Email Providers

### Microsoft 365/Outlook

```
SMTP Host: smtp.office365.com
Port: 587
User: your-email@outlook.com
Password: Your Microsoft password (or app password if 2FA enabled)
```

### SendGrid

```
SMTP Host: smtp.sendgrid.net
Port: 587
User: apikey
Password: SG.xxxxxxxxxxxx... (your SendGrid API key)
```

### AWS SES

```
SMTP Host: email-smtp.REGION.amazonaws.com
Port: 587
User: Your SMTP username (from AWS SES)
Password: Your SMTP password (from AWS SES)
```

See AWS SES documentation for generating SMTP credentials.

---

## Troubleshooting

### "Permission denied" when storing credentials

```bash
# Unlock Keychain first
security unlock-keychain -p YOUR_MACOS_PASSWORD
```

### "Authentication failed"

```bash
# Check credential is in Keychain
security find-generic-password -s msmtp-ers -w

# Verify it's not expired (e.g., Gmail app password)
# Re-enter with: bash manage-credentials.sh add
```

### "TLS error" or "CA certificates"

```bash
# Check OpenSSL certificate path (for your macOS version)
ls /usr/local/etc/openssl@3/certs/ca-certificates.crt

# If missing, reinstall OpenSSL
brew reinstall openssl@3

# Or update ~/.msmtprc with correct path:
tls_trust_file /etc/ssl/cert.pem
```

### Emails not sent, but no error

```bash
# Check msmtp logs
tail -100 ~/.msmtp.log

# Test with verbose flag
echo "test" | msmtp -v -a ers your-email@gmail.com
```

---

## Integration with ERS Alerts

Alert emails are sent automatically by `process-log-queue.sh` when:
- Cron job outputs `should_email: true` in structured JSON
- Queue processor reads alert JSON
- Recipient: `niall.young@icloud.com` (set in queue processor)

To customize recipient:

```bash
# Edit queue processor
vi agentic-engineers/orchestration/scripts/process-log-queue.sh

# Change this line:
RECIPIENT="your-email@example.com"
```

---

## Commands Reference

```bash
# Setup
bash agentic-engineers/orchestration/scripts/setup-msmtp.sh

# Manage credentials
bash agentic-engineers/orchestration/scripts/manage-credentials.sh add      # Add/update
bash agentic-engineers/orchestration/scripts/manage-credentials.sh gui      # Open Keychain GUI
bash agentic-engineers/orchestration/scripts/manage-credentials.sh view     # Show what's stored
bash agentic-engineers/orchestration/scripts/manage-credentials.sh test     # Send test email
bash agentic-engineers/orchestration/scripts/manage-credentials.sh delete   # Remove credentials

# Direct Keychain access
security find-generic-password -s msmtp-ers -w                             # Get password
security add-generic-password -s msmtp-ers -a USER -w PASS                # Add/update
security delete-generic-password -s msmtp-ers                              # Delete

# Send email manually
bash agentic-engineers/orchestration/scripts/send-alert-email.sh \
  "recipient@example.com" \
  "Subject" \
  "Body text"

# Test msmtp
echo "test" | msmtp -a ers recipient@example.com
echo "test" | msmtp -v -a ers recipient@example.com   # Verbose
```

---

## Security Notes

✓ Passwords never in config files  
✓ Encrypted in macOS Keychain  
✓ Protected by macOS login password  
✓ Keychain requires authentication to view in GUI  

⚠ Keychain can be accessed by any process in your user session  
⚠ If someone has your macOS password, they can access credentials  
⚠ Keep your macOS updated and lock screen when away  

---

## Next Steps

1. Run setup: `bash agentic-engineers/orchestration/scripts/setup-msmtp.sh`
2. Test credentials: `bash manage-credentials.sh test`
3. Queue processor will auto-send emails for alerts with `should_email: true`
4. Check inbox for test email

Questions? Check logs:
```bash
tail -f ~/.msmtp.log
tail -f agentic-engineers/data/logs/queue-processor-*.log
```
