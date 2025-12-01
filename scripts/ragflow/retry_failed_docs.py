#!/usr/bin/env python3
"""
Retry parsing for failed documents in RAGFlow.

This script fetches all documents with FAIL status from a RAGFlow dataset
and re-triggers parsing for them in batches.

Usage:
    export RAGFLOW_API_KEY="your-api-key"
    python retry_failed_docs.py [--dataset-id ID] [--batch-size N] [--dry-run]

Environment:
    RAGFLOW_API_KEY: Required. Your RAGFlow API key.
    RAGFLOW_URL: Optional. RAGFlow server URL (default: http://localhost:9380)
"""

import argparse
import os
import sys
import time
from typing import Optional

import requests

# Configuration
DEFAULT_RAGFLOW_URL = "http://localhost:9380"
DEFAULT_DATASET_ID = "735f3e9acba011f08a110242ac140006"  # DSA-110 Docs
DEFAULT_BATCH_SIZE = 50
DEFAULT_PAGE_SIZE = 100


def get_api_key() -> str:
    """Get RAGFlow API key from environment."""
    api_key = os.environ.get("RAGFLOW_API_KEY")
    if not api_key:
        print("ERROR: RAGFLOW_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    return api_key


def get_headers(api_key: str) -> dict:
    """Build request headers."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def fetch_failed_documents(
    base_url: str, dataset_id: str, api_key: str, page_size: int = 100
) -> list[dict]:
    """Fetch all documents with FAIL status from the dataset."""
    headers = get_headers(api_key)
    failed_docs = []
    page = 1

    print(f"Fetching failed documents from dataset {dataset_id}...")

    while True:
        url = f"{base_url}/api/v1/datasets/{dataset_id}/documents"
        params = {"page": page, "page_size": page_size}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                print(f"API error: {data.get('message', 'Unknown error')}", file=sys.stderr)
                break

            docs = data.get("data", {}).get("docs", [])
            if not docs:
                break

            # Filter for failed documents
            page_failed = [doc for doc in docs if doc.get("run") == "FAIL"]
            failed_docs.extend(page_failed)

            total = data.get("data", {}).get("total", 0)
            fetched = page * page_size
            print(f"  Page {page}: found {len(page_failed)} failed docs (total fetched: {min(fetched, total)}/{total})")

            if fetched >= total:
                break

            page += 1

        except requests.RequestException as e:
            print(f"Request error on page {page}: {e}", file=sys.stderr)
            break

    return failed_docs


def retry_documents(
    base_url: str,
    dataset_id: str,
    api_key: str,
    doc_ids: list[str],
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Retry parsing for a list of document IDs.
    
    Returns (success_count, fail_count).
    """
    if not doc_ids:
        return 0, 0

    headers = get_headers(api_key)
    url = f"{base_url}/api/v1/datasets/{dataset_id}/documents/run"

    if dry_run:
        print(f"  [DRY RUN] Would retry {len(doc_ids)} documents")
        return len(doc_ids), 0

    try:
        # RAGFlow expects document_ids in the request body
        payload = {"document_ids": doc_ids}
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") == 0:
            return len(doc_ids), 0
        else:
            print(f"  API error: {data.get('message', 'Unknown')}", file=sys.stderr)
            return 0, len(doc_ids)

    except requests.RequestException as e:
        print(f"  Request error: {e}", file=sys.stderr)
        return 0, len(doc_ids)


def main():
    parser = argparse.ArgumentParser(
        description="Retry parsing for failed RAGFlow documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dataset-id",
        default=DEFAULT_DATASET_ID,
        help=f"RAGFlow dataset ID (default: {DEFAULT_DATASET_ID})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of documents to retry per batch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between batches (default: 2.0)",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("RAGFLOW_URL", DEFAULT_RAGFLOW_URL),
        help=f"RAGFlow server URL (default: {DEFAULT_RAGFLOW_URL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of documents to retry (default: all)",
    )

    args = parser.parse_args()

    api_key = get_api_key()
    base_url = args.url.rstrip("/")

    print(f"RAGFlow URL: {base_url}")
    print(f"Dataset ID: {args.dataset_id}")
    print(f"Batch size: {args.batch_size}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print()

    # Fetch failed documents
    failed_docs = fetch_failed_documents(
        base_url, args.dataset_id, api_key, page_size=DEFAULT_PAGE_SIZE
    )

    if not failed_docs:
        print("\nNo failed documents found. Nothing to retry.")
        return 0

    print(f"\nFound {len(failed_docs)} failed documents")

    # Apply limit if specified
    if args.limit and args.limit < len(failed_docs):
        failed_docs = failed_docs[: args.limit]
        print(f"Limiting to first {args.limit} documents")

    # Process in batches
    doc_ids = [doc["id"] for doc in failed_docs]
    total_success = 0
    total_fail = 0
    batch_num = 0

    print(f"\nRetrying in batches of {args.batch_size}...")

    for i in range(0, len(doc_ids), args.batch_size):
        batch = doc_ids[i : i + args.batch_size]
        batch_num += 1

        print(f"\nBatch {batch_num}: retrying {len(batch)} documents...")
        success, fail = retry_documents(
            base_url, args.dataset_id, api_key, batch, dry_run=args.dry_run
        )
        total_success += success
        total_fail += fail

        if success > 0:
            print(f"  ✓ Triggered parsing for {success} documents")
        if fail > 0:
            print(f"  ✗ Failed to trigger {fail} documents")

        # Delay between batches to avoid overwhelming the server
        if i + args.batch_size < len(doc_ids) and not args.dry_run:
            print(f"  Waiting {args.delay}s before next batch...")
            time.sleep(args.delay)

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total documents processed: {len(doc_ids)}")
    print(f"Successfully triggered: {total_success}")
    print(f"Failed to trigger: {total_fail}")

    if not args.dry_run and total_success > 0:
        print("\nNote: Documents are now queued for parsing.")
        print("Check RAGFlow UI or run this script again later to verify status.")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
