#!/bin/bash
# Send alert emails via msmtp
# Called by queue processor for email routing

set -e

usage() {
    echo "Send alert email via msmtp"
    echo "Usage: send-alert-email.sh <recipient> <subject> <body>"
    exit 1
}

if [ $# -lt 3 ]; then
    usage
fi

RECIPIENT="$1"
SUBJECT="$2"
BODY="$3"

# Get sender email from msmtp config
SENDER_EMAIL=$(grep "^from" ~/.msmtprc | awk '{print $NF}')

if [ -z "$SENDER_EMAIL" ]; then
    echo "Error: No sender email found in ~/.msmtprc"
    exit 1
fi

# Use "Agent" as display name
SENDER="Agent <$SENDER_EMAIL>"

# Construct email
EMAIL="From: $SENDER
To: $RECIPIENT
Subject: $SUBJECT
Date: $(date -R)
Message-ID: <$(date +%s)-ers@$(hostname)>
Content-Type: text/plain; charset=utf-8

$BODY
"

# Send via msmtp
echo "$EMAIL" | msmtp -a ers "$RECIPIENT" 2>&1 || {
    echo "Failed to send email to $RECIPIENT" >&2
    exit 1
}

exit 0
