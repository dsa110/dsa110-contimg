#!/usr/bin/env python3
"""Command-line tool for transient triage operations.

Provides quick CLI access to transient detection user intervention functions:
- Acknowledge alerts
- Classify candidates
- Update follow-up status
- Add notes
- List alerts and candidates

Examples:
    # List unacknowledged alerts
    python transient_triage.py list-alerts --unacknowledged

    # Acknowledge an alert
    python transient_triage.py acknowledge-alert 42 --user operator --notes "False positive"

    # Classify a candidate
    python transient_triage.py classify 15 --classification real --user astronomer

    # Update follow-up status
    python transient_triage.py follow-up alert 42 --status scheduled --notes "VLA observation"

    # Add notes
    python transient_triage.py add-notes candidate 15 --notes "Interesting variability" --user scientist

    # Bulk acknowledge
    python transient_triage.py bulk-acknowledge 10 11 12 --user operator --notes "Batch review"
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "dsa110_contimg" / "src"))

from dsa110_contimg.catalog.transient_detection import (
    acknowledge_alert,
    add_notes,
    classify_candidate,
    get_transient_alerts,
    get_transient_candidates,
    update_follow_up_status,
)


def list_alerts(args):
    """List transient alerts."""
    df = get_transient_alerts(
        alert_level=args.level,
        acknowledged=args.acknowledged,
        limit=args.limit,
        db_path=args.db,
    )

    if df.empty:
        print("No alerts found.")
        return

    # Format output
    print(f"\n{'='*80}")
    print(f"Found {len(df)} alerts")
    print(f"{'='*80}\n")

    for _, row in df.iterrows():
        ack_status = "✓ Acknowledged" if row["acknowledged"] else "✗ Unacknowledged"
        print(f"Alert ID: {row['id']}")
        print(f"  Level: {row['alert_level']}")
        print(f"  Status: {ack_status}")
        print(f"  Message: {row['alert_message']}")
        print(f"  Created: {row['created_at']}")
        if row.get("acknowledged_by"):
            print(f"  Acknowledged by: {row['acknowledged_by']}")
        if row.get("follow_up_status"):
            print(f"  Follow-up: {row['follow_up_status']}")
        if row.get("notes"):
            print(f"  Notes: {row['notes'][:100]}...")
        print()


def list_candidates(args):
    """List transient candidates."""
    detection_types = [args.type] if args.type else None

    df = get_transient_candidates(
        min_significance=args.min_sigma,
        detection_types=detection_types,
        limit=args.limit,
        db_path=args.db,
    )

    if df.empty:
        print("No candidates found.")
        return

    # Format output
    print(f"\n{'='*80}")
    print(f"Found {len(df)} candidates")
    print(f"{'='*80}\n")

    for _, row in df.iterrows():
        print(f"Candidate ID: {row['id']}")
        print(f"  Source: {row['source_name']}")
        print(f"  Position: RA={row['ra_deg']:.4f}°, Dec={row['dec_deg']:.4f}°")
        print(f"  Type: {row['detection_type']}")
        print(f"  Significance: {row['significance_sigma']:.2f}σ")
        print(f"  Flux: {row['flux_obs_mjy']:.2f} mJy")
        if row.get("classification"):
            print(f"  Classification: {row['classification']}")
        if row.get("follow_up_status"):
            print(f"  Follow-up: {row['follow_up_status']}")
        if row.get("notes"):
            print(f"  Notes: {row['notes'][:100]}...")
        print()


def acknowledge_alert_cmd(args):
    """Acknowledge an alert."""
    try:
        result = acknowledge_alert(
            alert_id=args.alert_id,
            acknowledged_by=args.user,
            notes=args.notes,
            db_path=args.db,
        )
        if result:
            print(f"✓ Alert {args.alert_id} acknowledged by {args.user}")
        else:
            print(f"✗ Failed to acknowledge alert {args.alert_id}")
            sys.exit(1)
    except ValueError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def classify_candidate_cmd(args):
    """Classify a candidate."""
    try:
        result = classify_candidate(
            candidate_id=args.candidate_id,
            classification=args.classification,
            classified_by=args.user,
            notes=args.notes,
            db_path=args.db,
        )
        if result:
            print(
                f"✓ Candidate {args.candidate_id} classified as '{args.classification}' by {args.user}"
            )
        else:
            print(f"✗ Failed to classify candidate {args.candidate_id}")
            sys.exit(1)
    except ValueError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def follow_up_cmd(args):
    """Update follow-up status."""
    try:
        result = update_follow_up_status(
            item_id=args.id,
            item_type=args.type,
            status=args.status,
            notes=args.notes,
            db_path=args.db,
        )
        if result:
            print(f"✓ {args.type.capitalize()} {args.id} follow-up status: {args.status}")
        else:
            print(f"✗ Failed to update follow-up status")
            sys.exit(1)
    except ValueError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def add_notes_cmd(args):
    """Add notes to alert or candidate."""
    try:
        result = add_notes(
            item_id=args.id,
            item_type=args.type,
            notes=args.notes,
            username=args.user,
            append=not args.replace,
            db_path=args.db,
        )
        if result:
            action = "replaced" if args.replace else "appended"
            print(f"✓ Notes {action} for {args.type} {args.id} by {args.user}")
        else:
            print(f"✗ Failed to add notes")
            sys.exit(1)
    except ValueError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def bulk_acknowledge_cmd(args):
    """Acknowledge multiple alerts."""
    success_count = 0
    failed_ids = []

    for alert_id in args.alert_ids:
        try:
            result = acknowledge_alert(
                alert_id=alert_id,
                acknowledged_by=args.user,
                notes=args.notes,
                db_path=args.db,
            )
            if result:
                success_count += 1
                print(f"✓ Alert {alert_id} acknowledged")
            else:
                failed_ids.append(alert_id)
        except Exception as e:
            print(f"✗ Alert {alert_id} failed: {e}")
            failed_ids.append(alert_id)

    print(f"\n{'='*80}")
    print(f"Bulk operation complete:")
    print(f"  Succeeded: {success_count}/{len(args.alert_ids)}")
    print(f"  Failed: {len(failed_ids)}")
    if failed_ids:
        print(f"  Failed IDs: {', '.join(map(str, failed_ids))}")
    print(f"{'='*80}")

    if failed_ids:
        sys.exit(1)


def bulk_classify_cmd(args):
    """Classify multiple candidates."""
    success_count = 0
    failed_ids = []

    for candidate_id in args.candidate_ids:
        try:
            result = classify_candidate(
                candidate_id=candidate_id,
                classification=args.classification,
                classified_by=args.user,
                notes=args.notes,
                db_path=args.db,
            )
            if result:
                success_count += 1
                print(f"✓ Candidate {candidate_id} classified as '{args.classification}'")
            else:
                failed_ids.append(candidate_id)
        except Exception as e:
            print(f"✗ Candidate {candidate_id} failed: {e}")
            failed_ids.append(candidate_id)

    print(f"\n{'='*80}")
    print(f"Bulk operation complete:")
    print(f"  Succeeded: {success_count}/{len(args.candidate_ids)}")
    print(f"  Failed: {len(failed_ids)}")
    if failed_ids:
        print(f"  Failed IDs: {', '.join(map(str, failed_ids))}")
    print(f"{'='*80}")

    if failed_ids:
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Transient triage CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db",
        default="/data/dsa110-contimg/state/db/products.sqlite3",
        help="Path to products database (default: %(default)s)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List alerts
    list_alerts_parser = subparsers.add_parser("list-alerts", help="List transient alerts")
    list_alerts_parser.add_argument(
        "--level", help="Filter by alert level (CRITICAL, HIGH, MEDIUM)"
    )
    list_alerts_parser.add_argument(
        "--acknowledged",
        action="store_true",
        help="Show acknowledged alerts (default: unacknowledged)",
    )
    list_alerts_parser.add_argument(
        "--unacknowledged",
        dest="acknowledged",
        action="store_false",
        help="Show unacknowledged alerts",
    )
    list_alerts_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum results (default: 50)"
    )
    list_alerts_parser.set_defaults(func=list_alerts, acknowledged=False)

    # List candidates
    list_candidates_parser = subparsers.add_parser(
        "list-candidates", help="List transient candidates"
    )
    list_candidates_parser.add_argument(
        "--min-sigma", type=float, help="Minimum significance threshold (sigma)"
    )
    list_candidates_parser.add_argument(
        "--type", help="Filter by type (new_source, brightening, fading, variable)"
    )
    list_candidates_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum results (default: 50)"
    )
    list_candidates_parser.set_defaults(func=list_candidates)

    # Acknowledge alert
    ack_parser = subparsers.add_parser("acknowledge-alert", help="Acknowledge an alert")
    ack_parser.add_argument("alert_id", type=int, help="Alert ID to acknowledge")
    ack_parser.add_argument("--user", required=True, help="Username acknowledging the alert")
    ack_parser.add_argument("--notes", help="Optional notes about acknowledgment")
    ack_parser.set_defaults(func=acknowledge_alert_cmd)

    # Classify candidate
    classify_parser = subparsers.add_parser("classify", help="Classify a candidate")
    classify_parser.add_argument("candidate_id", type=int, help="Candidate ID to classify")
    classify_parser.add_argument(
        "--classification",
        required=True,
        choices=["real", "artifact", "variable", "uncertain"],
        help="Classification label",
    )
    classify_parser.add_argument("--user", required=True, help="Username classifying the candidate")
    classify_parser.add_argument("--notes", help="Optional notes about classification")
    classify_parser.set_defaults(func=classify_candidate_cmd)

    # Follow-up status
    followup_parser = subparsers.add_parser("follow-up", help="Update follow-up status")
    followup_parser.add_argument("type", choices=["alert", "candidate"], help="Type of item")
    followup_parser.add_argument("id", type=int, help="Alert or candidate ID")
    followup_parser.add_argument(
        "--status",
        required=True,
        choices=["pending", "scheduled", "completed", "declined"],
        help="Follow-up status",
    )
    followup_parser.add_argument("--notes", help="Optional notes about status")
    followup_parser.set_defaults(func=follow_up_cmd)

    # Add notes
    notes_parser = subparsers.add_parser("add-notes", help="Add notes to alert or candidate")
    notes_parser.add_argument("type", choices=["alert", "candidate"], help="Type of item")
    notes_parser.add_argument("id", type=int, help="Alert or candidate ID")
    notes_parser.add_argument("--notes", required=True, help="Notes to add")
    notes_parser.add_argument("--user", required=True, help="Username adding notes")
    notes_parser.add_argument(
        "--replace", action="store_true", help="Replace existing notes instead of appending"
    )
    notes_parser.set_defaults(func=add_notes_cmd)

    # Bulk acknowledge
    bulk_ack_parser = subparsers.add_parser("bulk-acknowledge", help="Acknowledge multiple alerts")
    bulk_ack_parser.add_argument("alert_ids", type=int, nargs="+", help="Alert IDs to acknowledge")
    bulk_ack_parser.add_argument("--user", required=True, help="Username acknowledging alerts")
    bulk_ack_parser.add_argument("--notes", help="Optional notes for all alerts")
    bulk_ack_parser.set_defaults(func=bulk_acknowledge_cmd)

    # Bulk classify
    bulk_classify_parser = subparsers.add_parser(
        "bulk-classify", help="Classify multiple candidates"
    )
    bulk_classify_parser.add_argument(
        "candidate_ids", type=int, nargs="+", help="Candidate IDs to classify"
    )
    bulk_classify_parser.add_argument(
        "--classification",
        required=True,
        choices=["real", "artifact", "variable", "uncertain"],
        help="Classification label",
    )
    bulk_classify_parser.add_argument(
        "--user", required=True, help="Username classifying candidates"
    )
    bulk_classify_parser.add_argument("--notes", help="Optional notes for all candidates")
    bulk_classify_parser.set_defaults(func=bulk_classify_cmd)

    # Parse and execute
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
