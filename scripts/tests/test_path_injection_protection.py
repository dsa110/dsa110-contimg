#!/usr/bin/env python3
"""
Test script to verify path injection protection in API endpoints.

This script tests that API endpoints properly reject malicious path inputs
and prevent path traversal attacks.
"""

import sys
from pathlib import Path

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

BASE_URL = "http://localhost:8000"  # Adjust if needed


def test_path_injection(base_url: str = BASE_URL):
    """Test path injection protection on various endpoints."""

    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\..\\etc\\passwd",
        "/etc/passwd",
        "../../../etc/shadow",
        "base/../../../etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
    ]

    endpoints_to_test = [
        # Routes endpoints
        f"{base_url}/api/ms/{{path}}/metadata",
        f"{base_url}/api/qa/file/{{group}}/{{name}}",
        f"{base_url}/api/qa/calibration/{{path}}/bandpass-plots",
        f"{base_url}/api/thumbnails/{{path}}.png",
        # Visualization endpoints
        f"{base_url}/api/visualization/browse?path={{path}}",
        f"{base_url}/api/visualization/fits/view?path={{path}}",
        f"{base_url}/api/visualization/image/view?path={{path}}",
        f"{base_url}/api/visualization/text/view?path={{path}}",
        f"{base_url}/api/visualization/notebook/{{path}}",
    ]

    results = {
        "passed": [],
        "failed": [],
        "errors": [],
    }

    print("Testing path injection protection...")
    print("=" * 60)

    for endpoint_template in endpoints_to_test:
        for malicious_path in malicious_paths:
            try:
                # Format endpoint with malicious path
                if "{" in endpoint_template and "}" in endpoint_template:
                    # Replace path parameter
                    if "?path=" in endpoint_template:
                        endpoint = endpoint_template.replace("{path}", malicious_path)
                    elif "/{path}" in endpoint_template:
                        endpoint = endpoint_template.replace("{path}", malicious_path)
                    elif "/{group}" in endpoint_template:
                        # For qa/file endpoint, split path
                        parts = malicious_path.split("/")
                        endpoint = endpoint_template.replace(
                            "{group}", parts[0] if parts else "test"
                        )
                        endpoint = endpoint.replace(
                            "{name}", parts[-1] if len(parts) > 1 else "test"
                        )
                    else:
                        endpoint = endpoint_template.replace("{path}", malicious_path)
                else:
                    endpoint = endpoint_template

                # Make request
                try:
                    response = requests.get(endpoint, timeout=5)

                    # Should return 400 (Bad Request) or 403 (Forbidden), not 200 or 404
                    if response.status_code in [400, 403]:
                        test_name = f"{endpoint_template} with {malicious_path[:30]}"
                        results["passed"].append(test_name)
                        print(f"✓ {test_name}: Rejected (status {response.status_code})")
                    elif response.status_code == 404:
                        # 404 might be acceptable if path validation passed but file doesn't exist
                        # But we want to ensure it's not 404 because the malicious path was accepted
                        test_name = f"{endpoint_template} with {malicious_path[:30]}"
                        results["failed"].append(f"{test_name}: Returned 404 (might be vulnerable)")
                        print(f"⚠ {test_name}: Returned 404 (needs review)")
                    else:
                        test_name = f"{endpoint_template} with {malicious_path[:30]}"
                        results["failed"].append(
                            f"{test_name}: Returned {response.status_code} (VULNERABLE!)"
                        )
                        print(f"✗ {test_name}: VULNERABLE! Status {response.status_code}")

                except requests.exceptions.RequestException as e:
                    test_name = f"{endpoint_template} with {malicious_path[:30]}"
                    results["errors"].append(f"{test_name}: {str(e)}")
                    print(f"✗ {test_name}: Error - {e}")

            except Exception as e:
                test_name = f"{endpoint_template} with {malicious_path[:30]}"
                results["errors"].append(f"{test_name}: {str(e)}")
                print(f"✗ {test_name}: Exception - {e}")

    print("=" * 60)
    print(f"\nResults:")
    print(f"  Passed: {len(results['passed'])}")
    print(f"  Failed: {len(results['failed'])}")
    print(f"  Errors: {len(results['errors'])}")

    if results["failed"]:
        print(f"\n⚠ Failed tests (potential vulnerabilities):")
        for failure in results["failed"][:10]:
            print(f"  - {failure}")

    if results["errors"]:
        print(f"\n✗ Errors:")
        for error in results["errors"][:5]:
            print(f"  - {error}")

    return len(results["failed"]) == 0 and len(results["errors"]) == 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test path injection protection")
    parser.add_argument("--url", default=BASE_URL, help=f"Base URL for API (default: {BASE_URL})")

    args = parser.parse_args()

    success = test_path_injection(args.url)
    sys.exit(0 if success else 1)
