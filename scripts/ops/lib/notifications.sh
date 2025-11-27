#!/bin/bash
# Notification Library for DSA-110 Pipeline Monitoring
# 
# Supports multiple notification backends:
# - Email (sendmail/SMTP)
# - Slack webhooks
# - Generic webhooks
# - System logging
#
# Configuration via environment variables:
#   NOTIFICATION_METHOD=email,slack,webhook,log
#   SLACK_WEBHOOK_URL=https://hooks.slack.com/...
#   EMAIL_RECIPIENTS=ops@example.com,admin@example.com
#   WEBHOOK_URL=https://api.example.com/notify
#   ALERT_THRESHOLD=warning|critical
#
# Usage:
#   source scripts/ops/lib/notifications.sh
#   send_notification "Subject" "Message body" "severity"

set -euo pipefail

# Severity levels
readonly SEVERITY_INFO="info"
readonly SEVERITY_WARNING="warning"
readonly SEVERITY_CRITICAL="critical"

# Emoji/icons for different severities
get_severity_icon() {
  local severity=$1
  case "$severity" in
    info) echo "ℹ️" ;;
    warning) echo "⚠️" ;;
    critical) echo "🚨" ;;
    *) echo "📢" ;;
  esac
}

# Get color for Slack messages
get_slack_color() {
  local severity=$1
  case "$severity" in
    info) echo "#2196F3" ;;  # Blue
    warning) echo "#FF9800" ;;  # Orange
    critical) echo "#F44336" ;;  # Red
    *) echo "#9E9E9E" ;;  # Gray
  esac
}

# Check if severity meets threshold
meets_threshold() {
  local severity=$1
  local threshold=${ALERT_THRESHOLD:-info}
  
  # Severity hierarchy: info < warning < critical
  case "$threshold" in
    critical)
      [[ "$severity" == "critical" ]] && return 0
      return 1
      ;;
    warning)
      [[ "$severity" == "warning" || "$severity" == "critical" ]] && return 0
      return 1
      ;;
    info|*)
      return 0
      ;;
  esac
}

# Send email notification
send_email() {
  local subject=$1
  local body=$2
  local severity=$3
  local recipients=${EMAIL_RECIPIENTS:-}
  
  if [[ -z "$recipients" ]]; then
    echo "⚠️  EMAIL_RECIPIENTS not configured, skipping email notification" >&2
    return 1
  fi
  
  local icon=$(get_severity_icon "$severity")
  local full_subject="$icon [$severity] $subject"
  
  # Try to send via sendmail or mail command
  if command -v sendmail &>/dev/null; then
    echo -e "Subject: $full_subject\n\n$body" | sendmail -t "$recipients"
    echo "✓ Email sent to: $recipients" >&2
  elif command -v mail &>/dev/null; then
    echo "$body" | mail -s "$full_subject" "$recipients"
    echo "✓ Email sent to: $recipients" >&2
  else
    echo "⚠️  No email command available (sendmail/mail)" >&2
    return 1
  fi
}

# Send Slack notification
send_slack() {
  local subject=$1
  local body=$2
  local severity=$3
  local webhook_url=${SLACK_WEBHOOK_URL:-}
  
  if [[ -z "$webhook_url" ]]; then
    echo "⚠️  SLACK_WEBHOOK_URL not configured, skipping Slack notification" >&2
    return 1
  fi
  
  local icon=$(get_severity_icon "$severity")
  local color=$(get_slack_color "$severity")
  local hostname=$(hostname -f 2>/dev/null || hostname)
  
  # Build JSON payload
  local payload=$(cat <<EOF
{
  "attachments": [
    {
      "color": "$color",
      "title": "$icon $subject",
      "text": "$body",
      "fields": [
        {
          "title": "Severity",
          "value": "$severity",
          "short": true
        },
        {
          "title": "Host",
          "value": "$hostname",
          "short": true
        }
      ],
      "footer": "DSA-110 Pipeline Monitor",
      "ts": $(date +%s)
    }
  ]
}
EOF
)
  
  # Send to Slack
  if curl -X POST -H 'Content-type: application/json' \
     --data "$payload" \
     --silent --show-error --fail \
     "$webhook_url" &>/dev/null; then
    echo "✓ Slack notification sent" >&2
  else
    echo "⚠️  Failed to send Slack notification" >&2
    return 1
  fi
}

# Send generic webhook notification
send_webhook() {
  local subject=$1
  local body=$2
  local severity=$3
  local webhook_url=${WEBHOOK_URL:-}
  
  if [[ -z "$webhook_url" ]]; then
    echo "⚠️  WEBHOOK_URL not configured, skipping webhook notification" >&2
    return 1
  fi
  
  local hostname=$(hostname -f 2>/dev/null || hostname)
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  
  # Build JSON payload
  local payload=$(cat <<EOF
{
  "subject": "$subject",
  "message": "$body",
  "severity": "$severity",
  "hostname": "$hostname",
  "timestamp": "$timestamp",
  "service": "dsa110-pipeline"
}
EOF
)
  
  # Send webhook
  if curl -X POST -H 'Content-type: application/json' \
     --data "$payload" \
     --silent --show-error --fail \
     "$webhook_url" &>/dev/null; then
    echo "✓ Webhook notification sent" >&2
  else
    echo "⚠️  Failed to send webhook notification" >&2
    return 1
  fi
}

# Log to system journal
send_log() {
  local subject=$1
  local body=$2
  local severity=$3
  
  local icon=$(get_severity_icon "$severity")
  local log_priority
  
  case "$severity" in
    critical) log_priority="crit" ;;
    warning) log_priority="warning" ;;
    info|*) log_priority="info" ;;
  esac
  
  # Log to systemd journal if available, otherwise syslog
  if command -v logger &>/dev/null; then
    logger -t "dsa110-pipeline" -p "user.$log_priority" "$icon [$severity] $subject: $body"
    echo "✓ Logged to system journal" >&2
  else
    echo "$icon [$severity] $subject: $body" >&2
  fi
}

# Main notification dispatcher
send_notification() {
  local subject=$1
  local body=${2:-}
  local severity=${3:-info}
  local methods=${NOTIFICATION_METHOD:-log}
  
  # Validate severity
  if [[ ! "$severity" =~ ^(info|warning|critical)$ ]]; then
    echo "⚠️  Invalid severity '$severity', using 'info'" >&2
    severity="info"
  fi
  
  # Check if severity meets threshold
  if ! meets_threshold "$severity"; then
    echo "ℹ️  Severity '$severity' below threshold '${ALERT_THRESHOLD:-info}', skipping notification" >&2
    return 0
  fi
  
  local sent_count=0
  local failed_count=0
  
  # Send via each configured method
  IFS=',' read -ra method_array <<< "$methods"
  for method in "${method_array[@]}"; do
    method=$(echo "$method" | tr -d ' ')  # Trim whitespace
    
    case "$method" in
      email)
        if send_email "$subject" "$body" "$severity"; then
          ((sent_count++))
        else
          ((failed_count++))
        fi
        ;;
      slack)
        if send_slack "$subject" "$body" "$severity"; then
          ((sent_count++))
        else
          ((failed_count++))
        fi
        ;;
      webhook)
        if send_webhook "$subject" "$body" "$severity"; then
          ((sent_count++))
        else
          ((failed_count++))
        fi
        ;;
      log)
        send_log "$subject" "$body" "$severity"
        ((sent_count++))
        ;;
      *)
        echo "⚠️  Unknown notification method: $method" >&2
        ((failed_count++))
        ;;
    esac
  done
  
  if [[ $sent_count -eq 0 ]]; then
    echo "❌ All notification methods failed" >&2
    return 1
  elif [[ $failed_count -gt 0 ]]; then
    echo "⚠️  Some notification methods failed ($failed_count/$((sent_count + failed_count)))" >&2
  fi
  
  return 0
}

# Test notification function
test_notifications() {
  echo "Testing notification system..."
  echo ""
  
  echo "Test 1: Info notification"
  send_notification "Test Info" "This is a test info message" "info"
  echo ""
  
  echo "Test 2: Warning notification"
  send_notification "Test Warning" "This is a test warning message" "warning"
  echo ""
  
  echo "Test 3: Critical notification"
  send_notification "Test Critical" "This is a test critical alert" "critical"
  echo ""
  
  echo "✓ Notification tests complete"
}

# If script is run directly (not sourced), run tests
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  test_notifications
fi
