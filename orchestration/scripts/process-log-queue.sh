#!/bin/bash
# Process pending alerts from log queue
# Run every 15 minutes via cron to route alerts to email/voice/dashboard

set -e

QUEUE_DIR="agentic-engineers/data/logs/QUEUE"
PENDING="$QUEUE_DIR/pending"
PROCESSING="$QUEUE_DIR/processing"
COMPLETED="$QUEUE_DIR/completed"
FAILED="$QUEUE_DIR/failed"

# Create directories if needed
mkdir -p "$PENDING" "$PROCESSING" "$COMPLETED" "$FAILED"

# Log file for processor activity
LOG_FILE="agentic-engineers/data/logs/queue-processor-$(date +%Y-%m-%d).log"
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "Queue processor started"

# Count files
pending_count=$(find "$PENDING" -type f -name "*.json" | wc -l)
log_message "Found $pending_count pending alerts"

# Process each pending alert (atomic: pending → processing → completed/failed)
for alert_file in "$PENDING"/*.json; do
    [ -f "$alert_file" ] || continue

    alert_name=$(basename "$alert_file")

    # Atomic move to processing (prevents race conditions)
    if ! mv "$alert_file" "$PROCESSING/$alert_name" 2>/dev/null; then
        log_message "WARN: Could not acquire lock on $alert_name"
        continue
    fi

    processing_file="$PROCESSING/$alert_name"
    log_message "Processing: $alert_name"

    # Extract alert details using jq
    if ! command -v jq &> /dev/null; then
        log_message "ERROR: jq not found, cannot parse JSON"
        mv "$processing_file" "$FAILED/"
        continue
    fi

    # Extract fields
    JOB=$(jq -r '.job // "unknown"' "$processing_file" 2>/dev/null || echo "unknown")
    SEVERITY=$(jq -r '.severity // "info"' "$processing_file" 2>/dev/null || echo "info")
    MESSAGE=$(jq -r '.message // ""' "$processing_file" 2>/dev/null || echo "")
    SHOULD_EMAIL=$(jq -r '.should_email // false' "$processing_file" 2>/dev/null || echo "false")
    SHOULD_VOICE=$(jq -r '.should_voice // false' "$processing_file" 2>/dev/null || echo "false")
    TIMESTAMP=$(jq -r '.timestamp // ""' "$processing_file" 2>/dev/null || echo "")

    # Route to destinations
    if [ "$SHOULD_EMAIL" = "true" ]; then
        log_message "  → EMAIL: [$SEVERITY] $JOB: $MESSAGE"

        # Send email alert
        RECIPIENT="niall.young@icloud.com"
        SUBJECT="[ERS Alert] $SEVERITY - $JOB"
        EMAIL_BODY="Alert: $MESSAGE

Job: $JOB
Severity: $SEVERITY
Time: $TIMESTAMP

---
Automated alert from ERS Automation Framework"

        if bash "$(dirname "$0")/send-alert-email.sh" "$RECIPIENT" "$SUBJECT" "$EMAIL_BODY" 2>&1; then
            log_message "    ✓ Email sent to $RECIPIENT"
        else
            log_message "    ✗ Failed to send email"
        fi
    fi

    if [ "$SHOULD_VOICE" = "true" ]; then
        log_message "  → VOICE: $MESSAGE (voice queue ready when TTS implemented)"
        # Voice implementation: add to voice queue when TTS is ready
        # mkdir -p "agentic-engineers/data/voice-queue/pending"
        # cp "$processing_file" "agentic-engineers/data/voice-queue/pending/"
    fi

    # Atomic move to completed
    if mv "$processing_file" "$COMPLETED/$alert_name" 2>/dev/null; then
        log_message "  ✓ Completed: $alert_name"
    else
        log_message "  ✗ Failed to finalize: $alert_name"
        [ -f "$processing_file" ] && mv "$processing_file" "$FAILED/"
    fi
done

log_message "Queue processor completed"
