#!/usr/bin/env python3
"""
Test script for DSA-110 alerting system.

Usage:
    python scripts/test_alerting.py
    
This will send test alerts through all configured channels.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dsa110_contimg.utils import alerting


def main():
    """Test alerting system."""
    
    print("Testing DSA-110 Alerting System")
    print("=" * 60)
    
    # Check if Slack is configured
    manager = alerting.get_alert_manager()
    slack_enabled = any(
        ch.name == "slack" and ch.enabled 
        for ch in manager.channels
    )
    
    if slack_enabled:
        print("Slack alerts: ENABLED")
    else:
        print("Slack alerts: DISABLED (set CONTIMG_SLACK_WEBHOOK_URL to enable)")
    
    email_enabled = any(
        ch.name == "email" and ch.enabled 
        for ch in manager.channels
    )
    
    if email_enabled:
        print("Email alerts: ENABLED")
    else:
        print("Email alerts: DISABLED (optional)")
    
    print("\nSending test alerts...")
    print("-" * 60)
    
    # Test each severity level
    print("\n1. INFO alert (general information)")
    alerting.info(
        "test",
        "Alerting system test - INFO level",
        context={"test_run": "success", "severity": "info"},
    )
    
    print("\n2. WARNING alert (non-critical issue)")
    alerting.warning(
        "test",
        "Alerting system test - WARNING level",
        context={
            "test_run": "success",
            "severity": "warning",
            "example_issue": "High fraction of flagged data: 45%",
        },
    )
    
    print("\n3. ERROR alert (significant problem)")
    alerting.error(
        "test",
        "Alerting system test - ERROR level",
        context={
            "test_run": "success",
            "severity": "error",
            "example_issue": "MS quality check failed",
        },
    )
    
    print("\n4. CRITICAL alert (requires immediate attention)")
    alerting.critical(
        "test",
        "Alerting system test - CRITICAL level (ignore, this is a test)",
        context={
            "test_run": "success",
            "severity": "critical",
            "example_issue": "All calibration solutions flagged",
        },
    )
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("\nIf Slack is enabled, check your channel for 4 test messages.")
    print("Check logs for any errors:")
    print("  journalctl -u contimg-stream -f | grep -i alert")
    print("\nTo enable Slack alerts:")
    print("  1. Get webhook URL from https://api.slack.com/apps")
    print("  2. Add to ops/systemd/contimg.env:")
    print("     CONTIMG_SLACK_WEBHOOK_URL=https://hooks.slack.com/...")
    print("  3. Restart services: sudo systemctl restart contimg-stream contimg-api")


if __name__ == "__main__":
    main()

