#!/usr/bin/env python3
"""
Configure OpenAI in RAGFlow.

This script helps configure the OpenAI API in RAGFlow by:
1. Logging in with your RAGFlow credentials
2. Setting up the OpenAI API key

Usage:
    python scripts/configure_ragflow_openai.py --email YOUR_EMAIL --password YOUR_PASSWORD
    
Or set environment variables:
    RAGFLOW_EMAIL=your@email.com
    RAGFLOW_PASSWORD=yourpassword
    OPENAI_API_KEY=sk-...
"""

import argparse
import os
import sys
import requests

RAGFLOW_URL = "http://localhost:9380"


def login(email: str, password: str) -> str | None:
    """Login to RAGFlow and return session token."""
    r = requests.post(
        f"{RAGFLOW_URL}/v1/user/login",
        json={"email": email, "password": password},
    )
    data = r.json()
    
    if data.get("code") != 0:
        print(f"Login failed: {data.get('message')}")
        return None
    
    # Get session token from cookies
    token = r.cookies.get("Authorization") or r.cookies.get("access_token")
    if not token and "data" in data:
        token = data["data"].get("access_token")
    
    return token


def configure_openai(session: requests.Session, openai_key: str) -> bool:
    """Configure OpenAI as a model provider."""
    r = session.post(
        f"{RAGFLOW_URL}/v1/llm/set_api_key",
        json={
            "llm_factory": "OpenAI",
            "api_key": openai_key,
        },
    )
    data = r.json()
    
    if data.get("code") != 0:
        print(f"Failed to configure OpenAI: {data.get('message')}")
        return False
    
    print("✅ OpenAI configured successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Configure OpenAI in RAGFlow")
    parser.add_argument("--email", default=os.environ.get("RAGFLOW_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("RAGFLOW_PASSWORD"))
    parser.add_argument("--openai-key", default=os.environ.get("OPENAI_API_KEY"))
    parser.add_argument("--ragflow-url", default=RAGFLOW_URL)
    
    args = parser.parse_args()
    
    if not args.email or not args.password:
        print("Error: RAGFlow email and password required")
        print("Use --email and --password, or set RAGFLOW_EMAIL and RAGFLOW_PASSWORD")
        return 1
    
    if not args.openai_key:
        print("Error: OpenAI API key required")
        print("Use --openai-key or set OPENAI_API_KEY")
        return 1
    
    # Create session
    session = requests.Session()
    
    # Login
    print(f"Logging in to RAGFlow as {args.email}...")
    r = session.post(
        f"{args.ragflow_url}/v1/user/login",
        json={"email": args.email, "password": args.password},
    )
    data = r.json()
    
    if data.get("code") != 0:
        print(f"Login failed: {data.get('message')}")
        return 1
    
    print("✅ Logged in successfully")
    
    # Configure OpenAI
    print("Configuring OpenAI API key...")
    if configure_openai(session, args.openai_key):
        print("\n✅ OpenAI is now available as a model provider in RAGFlow")
        print("   You can now use text-embedding-3-small for embeddings")
        return 0
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
