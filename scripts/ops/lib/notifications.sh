#!/usr/bin/env bash
# shellcheck shell=bash
#
# Lightweight notification helpers for ops scripts.
#
# Supported backends (comma-separated via NOTIFICATION_METHOD):
#   - slack     : POST to Slack webhook (env: SLACK_WEBHOOK_URL)
#   - email     : send via `mail`/`mailx` (env: EMAIL_RECIPIENTS[, EMAIL_SENDER])
#   - webhook   : generic JSON POST (env: NOTIFICATION_WEBHOOK_URL)
#   - log       : always available fallback that just logs locally
#
# Optional env:
#   NOTIFY_LOG_FILE   : path to append notification log entries
#   NOTIFY_LOG_LEVEL  : minimum level to log (info|warning|critical), default: info
#   NOTIFICATION_TITLE_PREFIX : prefix added to subject/title

_notify_timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

_notify_log() {
  local level="$1"; shift
  local msg="$*"
  local line="[$(_notify_timestamp)] [$level] $msg"
  echo "$line"
  if [[ -n "${NOTIFY_LOG_FILE:-}" ]]; then
    mkdir -p "$(dirname "$NOTIFY_LOG_FILE")" 2>/dev/null || true
    echo "$line" >>"$NOTIFY_LOG_FILE"
  fi
}

_notify_should_log() {
  local level="${1,,}"
  local min="${NOTIFY_LOG_LEVEL:-info}"
  case "$min" in
    critical) [[ "$level" == "critical" ]] && return 0 ;;
    warning) [[ "$level" =~ ^(warning|critical)$ ]] && return 0 ;;
    *) return 0 ;;
  esac
  return 1
}

_notify_curl() {
  # Run curl but never fail the caller (ops scripts often run with set -e).
  if ! command -v curl >/dev/null 2>&1; then
    _notify_log "WARN" "curl not available; skipping HTTP notification"
    return 1
  fi
  local curl_rc=0
  curl --fail --silent --show-error "$@" || curl_rc=$?
  return "$curl_rc"
}

_notify_slack() {
  local subject="$1"; shift
  local body="$1"; shift
  local severity="${1:-info}"

  if [[ -z "${SLACK_WEBHOOK_URL:-}" ]]; then
    _notify_log "WARN" "SLACK_WEBHOOK_URL not set; skipping Slack notification"
    return 1
  fi

  local payload
  payload=$(printf '{"text":"[%s] %s\n%s"}' "$severity" "$subject" "$body")
  _notify_curl -H 'Content-type: application/json' \
    --data "$payload" \
    "$SLACK_WEBHOOK_URL" >/dev/null 2>&1 || {
    _notify_log "WARN" "Failed to send Slack notification"
    return 1
  }
  _notify_log "INFO" "Slack notification sent"
}

_notify_email() {
  local subject="$1"; shift
  local body="$1"; shift

  if [[ -z "${EMAIL_RECIPIENTS:-}" ]]; then
    _notify_log "WARN" "EMAIL_RECIPIENTS not set; skipping email notification"
    return 1
  fi

  if command -v mail >/dev/null 2>&1; then
    local sender_arg=()
    [[ -n "${EMAIL_SENDER:-}" ]] && sender_arg=(-r "$EMAIL_SENDER")
    printf "%s\n" "$body" | mail -s "$subject" "${sender_arg[@]}" "$EMAIL_RECIPIENTS" || {
      _notify_log "WARN" "mail command failed; email not sent"
      return 1
    }
    _notify_log "INFO" "Email notification sent to $EMAIL_RECIPIENTS"
    return 0
  fi

  if command -v sendmail >/dev/null 2>&1; then
    {
      echo "Subject: $subject"
      [[ -n "${EMAIL_SENDER:-}" ]] && echo "From: $EMAIL_SENDER"
      echo "To: $EMAIL_RECIPIENTS"
      echo
      echo "$body"
    } | sendmail -t || {
      _notify_log "WARN" "sendmail failed; email not sent"
      return 1
    }
    _notify_log "INFO" "Email notification sent to $EMAIL_RECIPIENTS"
    return 0
  fi

  _notify_log "WARN" "No mail/sendmail command available; skipping email notification"
  return 1
}

_notify_webhook() {
  local subject="$1"; shift
  local body="$1"; shift
  local severity="${1:-info}"

  if [[ -z "${NOTIFICATION_WEBHOOK_URL:-}" ]]; then
    _notify_log "WARN" "NOTIFICATION_WEBHOOK_URL not set; skipping webhook notification"
    return 1
  fi

  local payload
  payload=$(printf '{"subject":"%s","severity":"%s","body":"%s"}' "$subject" "$severity" "$body")
  _notify_curl -H 'Content-type: application/json' \
    --data "$payload" \
    "$NOTIFICATION_WEBHOOK_URL" >/dev/null 2>&1 || {
    _notify_log "WARN" "Failed to send webhook notification"
    return 1
  }
  _notify_log "INFO" "Webhook notification sent"
}

notify_send() {
  local subject="$1"; shift
  local body="$1"; shift
  local severity="${1:-info}"

  if [[ -n "${NOTIFICATION_TITLE_PREFIX:-}" ]]; then
    subject="${NOTIFICATION_TITLE_PREFIX} ${subject}"
  fi

  if _notify_should_log "$severity"; then
    _notify_log "${severity^^}" "$subject :: $body"
  fi

  local methods_raw="${NOTIFICATION_METHOD:-}"
  IFS=',' read -ra methods <<<"$methods_raw"
  if [[ "${#methods[@]}" -eq 0 || -z "${methods_raw}" ]]; then
    # Always fall back to local logging
    return 0
  fi

  for method in "${methods[@]}"; do
    case "${method,,}" in
      slack) _notify_slack "$subject" "$body" "$severity" || true ;;
      email) _notify_email "$subject" "$body" || true ;;
      webhook) _notify_webhook "$subject" "$body" "$severity" || true ;;
      log|"") : ;;  # already logged
      *)
        _notify_log "WARN" "Unknown notification method: $method"
        ;;
    esac
  done
}

export -f notify_send
