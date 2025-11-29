#!/usr/bin/env python3
"""
RAGFlow MCP client test script.

Tests connectivity to the RAGFlow MCP server and retrieval functionality.

Usage:
    # Basic connectivity test
    python scripts/test_ragflow_mcp.py
    
    # With API key
    RAGFLOW_API_KEY=your-key python scripts/test_ragflow_mcp.py
    
    # Query test
    python scripts/test_ragflow_mcp.py --query "How do I convert UVH5 files?"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_SSE_URL = "http://localhost:9382/sse"
DEFAULT_HTTP_URL = "http://localhost:9382/mcp"
DEFAULT_API_URL = "http://localhost:9380"


async def test_sse_connection(url: str, api_key: str | None = None) -> bool:
    """
    Test SSE MCP connection to RAGFlow.
    
    Args:
        url: SSE endpoint URL
        api_key: Optional API key
        
    Returns:
        True if connection successful
    """
    try:
        # Try to import mcp client
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client
        
        headers = {}
        if api_key:
            headers["api_key"] = api_key
            headers["Authorization"] = f"Bearer {api_key}"
        
        logger.info(f"Connecting to RAGFlow MCP SSE at {url}")
        
        async with sse_client(url, headers=headers) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                # List available tools
                tools = await session.list_tools()
                
                logger.info(f"Connected! Found {len(tools.tools)} tools:")
                for tool in tools.tools:
                    logger.info(f"  - {tool.name}: {tool.description[:50]}...")
                
                return True
                
    except ImportError:
        logger.error("MCP client not installed. Run: pip install mcp")
        return False
    except Exception as e:
        logger.error(f"SSE connection failed: {e}")
        return False


async def test_retrieval(
    url: str,
    api_key: str | None,
    query: str,
    dataset_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Test retrieval through MCP.
    
    Args:
        url: SSE endpoint URL
        api_key: API key
        query: Search query
        dataset_ids: Optional dataset filter
        
    Returns:
        List of chunk results
    """
    try:
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client
        
        headers = {}
        if api_key:
            headers["api_key"] = api_key
            headers["Authorization"] = f"Bearer {api_key}"
        
        async with sse_client(url, headers=headers) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                # Call retrieval tool
                args = {
                    "question": query,
                    "page_size": 5,
                }
                if dataset_ids:
                    args["dataset_ids"] = dataset_ids
                
                logger.info(f"Querying: {query}")
                
                response = await session.call_tool(
                    name="ragflow_retrieval",
                    arguments=args,
                )
                
                # Parse response
                if response.content:
                    for content in response.content:
                        if hasattr(content, "text"):
                            try:
                                data = json.loads(content.text)
                                return data.get("chunks", [])
                            except json.JSONDecodeError:
                                logger.warning(f"Non-JSON response: {content.text[:200]}")
                
                return []
                
    except ImportError:
        logger.error("MCP client not installed")
        return []
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return []


def test_api_connection(base_url: str, api_key: str | None = None) -> bool:
    """
    Test direct API connection (fallback if MCP client not available).
    
    Args:
        base_url: RAGFlow API URL
        api_key: API key
        
    Returns:
        True if API responds
    """
    import requests
    
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Try listing datasets
        response = requests.get(
            f"{base_url}/api/v1/datasets",
            headers=headers,
            params={"page": 1, "page_size": 1},
            timeout=10,
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                logger.info("API connection successful")
                return True
            else:
                logger.warning(f"API returned error: {data.get('message')}")
                return False
        else:
            logger.warning(f"API returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API connection failed: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test RAGFlow MCP connection",
    )
    parser.add_argument(
        "--sse-url",
        default=os.environ.get("RAGFLOW_MCP_SSE_URL", DEFAULT_SSE_URL),
        help="MCP SSE endpoint URL",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("RAGFLOW_BASE_URL", DEFAULT_API_URL),
        help="RAGFlow API URL",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("RAGFLOW_API_KEY"),
        help="RAGFlow API key",
    )
    parser.add_argument(
        "--query",
        "-q",
        help="Test query to run",
    )
    parser.add_argument(
        "--skip-mcp",
        action="store_true",
        help="Skip MCP test, only test API",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    success = True
    
    # Test API connection
    print("\n" + "=" * 60)
    print("Testing RAGFlow API Connection")
    print("=" * 60)
    
    api_ok = test_api_connection(args.api_url, args.api_key)
    if not api_ok:
        print("❌ API connection failed")
        success = False
    else:
        print("✅ API connection OK")
    
    # Test MCP connection
    if not args.skip_mcp:
        print("\n" + "=" * 60)
        print("Testing RAGFlow MCP SSE Connection")
        print("=" * 60)
        
        mcp_ok = asyncio.run(test_sse_connection(args.sse_url, args.api_key))
        if not mcp_ok:
            print("❌ MCP SSE connection failed")
            print("   (This may be OK if MCP client is not installed)")
        else:
            print("✅ MCP SSE connection OK")
            
            # Run query test if requested
            if args.query:
                print("\n" + "=" * 60)
                print("Testing Retrieval Query")
                print("=" * 60)
                
                results = asyncio.run(test_retrieval(
                    args.sse_url,
                    args.api_key,
                    args.query,
                ))
                
                if results:
                    print(f"✅ Found {len(results)} results")
                    for i, chunk in enumerate(results[:3], 1):
                        score = chunk.get("similarity", 0)
                        content = chunk.get("content", "")[:100]
                        print(f"\n[{i}] Score: {score:.4f}")
                        print(f"    {content}...")
                else:
                    print("⚠️  No results found (this may be OK if no documents uploaded)")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"API URL:     {args.api_url}")
    print(f"MCP SSE URL: {args.sse_url}")
    print(f"API Key:     {'Set' if args.api_key else 'Not set'}")
    
    if not args.api_key:
        print("\n⚠️  No API key set. To get one:")
        print("   1. Open http://localhost:9080 in your browser")
        print("   2. Create an account or log in")
        print("   3. Go to Settings → API Keys")
        print("   4. Create a new API key")
        print("   5. Set RAGFLOW_API_KEY environment variable")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
