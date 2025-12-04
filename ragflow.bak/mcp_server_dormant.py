"""
MCP Server for RAGFlow Integration.

**Location:** This script has been moved to `docs/ragflow/` and should be run
directly from that directory.

This creates an MCP server that exposes RAGFlow's retrieval and chat capabilities
as tools that VS Code/Copilot can use.

Usage:
    # Navigate to the directory
    cd /data/dsa110-contimg/docs/ragflow
    
    # SSE mode (default):
    python mcp_server.py --sse --port 9400

    # STDIO mode (for direct integration):
    python mcp_server.py --stdio
"""

import asyncio
import json
import logging
import os
import sys
from typing import Optional

# Check for MCP SDK
try:
    from mcp.server import Server
    from mcp.server.sse import SseServerTransport
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
    )
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

# Check for Starlette
try:
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import Response
    import uvicorn
    HAS_STARLETTE = True
except ImportError:
    HAS_STARLETTE = False

from config import RAGFlowConfig
from client import RAGFlowClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_config() -> RAGFlowConfig:
    """Get RAGFlow configuration from environment."""
    return RAGFlowConfig(
        base_url=os.environ.get("RAGFLOW_BASE_URL", "http://localhost:9380"),
        api_key=os.environ.get("RAGFLOW_API_KEY", ""),
    )


class RAGFlowMCPServer:
    """MCP Server that exposes RAGFlow as tools."""

    def __init__(self, config: Optional[RAGFlowConfig] = None):
        if not HAS_MCP:
            raise ImportError(
                "MCP SDK not installed. Install with: pip install mcp"
            )
        
        self.config = config or get_config()
        self.client = RAGFlowClient(self.config)
        self.server = Server("ragflow-dsa110")
        
        # Dataset ID for DSA-110 docs
        self.dataset_id = os.environ.get(
            "RAGFLOW_DATASET_ID",
            "735f3e9acba011f08a110242ac140006"  # Default to DSA-110 Docs
        )
        
        # Chat assistant ID
        self.chat_id = os.environ.get(
            "RAGFLOW_CHAT_ID",
            "7e0c99d2cba511f0ad1a0242ac140006"  # Default DSA-110 Assistant
        )
        
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP request handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="search_dsa110_docs",
                    description=(
                        "Search DSA-110 continuum imaging pipeline documentation. "
                        "Use this to find information about UVH5 to Measurement Set "
                        "conversion, calibration, imaging, pipeline stages, and "
                        "radio astronomy data processing."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for DSA-110 documentation"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="ask_dsa110_assistant",
                    description=(
                        "Ask a question to the DSA-110 documentation assistant. "
                        "The assistant has access to all pipeline documentation and "
                        "can provide detailed answers about the codebase."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Question to ask about DSA-110 pipeline"
                            }
                        },
                        "required": ["question"]
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "search_dsa110_docs":
                    return await self._search_docs(
                        arguments.get("query", ""),
                        arguments.get("top_k", 5)
                    )
                elif name == "ask_dsa110_assistant":
                    return await self._ask_assistant(
                        arguments.get("question", "")
                    )
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
            except Exception as e:
                logger.error(f"Tool call failed: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    async def _search_docs(self, query: str, top_k: int) -> list[TextContent]:
        """Search documentation and return results."""
        try:
            results = self.client.retrieve(
                dataset_ids=[self.dataset_id],
                question=query,
                top_n=top_k
            )
            
            if not results:
                return [TextContent(
                    type="text",
                    text=f"No results found for query: {query}"
                )]
            
            # Format results
            formatted = []
            for i, chunk in enumerate(results, 1):
                content = chunk.get("content", "")
                doc_name = chunk.get("document_name", "Unknown")
                score = chunk.get("similarity", 0)
                
                formatted.append(
                    f"**Result {i}** (score: {score:.3f})\n"
                    f"Source: {doc_name}\n"
                    f"```\n{content}\n```"
                )
            
            return [TextContent(
                type="text",
                text="\n\n".join(formatted)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Search error: {str(e)}"
            )]

    async def _ask_assistant(self, question: str) -> list[TextContent]:
        """Ask the chat assistant and return response."""
        try:
            # Create a conversation session
            session_resp = self.client._post(
                f"/api/v1/chats/{self.chat_id}/sessions",
                json={"name": f"MCP Query: {question[:50]}..."}
            )
            
            if session_resp.get("code") != 0:
                # Try to use retrieval instead
                return await self._search_docs(question, 5)
            
            session_id = session_resp["data"]["id"]
            
            # Send the question (non-streaming for simplicity)
            chat_resp = self.client._post(
                f"/api/v1/chats/{self.chat_id}/completions",
                json={
                    "session_id": session_id,
                    "question": question,
                    "stream": False
                }
            )
            
            if chat_resp.get("code") != 0:
                # Fallback to retrieval
                return await self._search_docs(question, 5)
            
            answer = chat_resp.get("data", {}).get("answer", "")
            references = chat_resp.get("data", {}).get("reference", {})
            
            # Format response with citations
            response_parts = [answer]
            
            if references.get("chunks"):
                response_parts.append("\n\n**Sources:**")
                for chunk in references["chunks"][:3]:
                    doc_name = chunk.get("document_name", "Unknown")
                    response_parts.append(f"- {doc_name}")
            
            return [TextContent(
                type="text",
                text="\n".join(response_parts)
            )]
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            # Fallback to search
            return await self._search_docs(question, 5)

    async def run_sse(self, host: str = "0.0.0.0", port: int = 9400):
        """Run as SSE server using Starlette."""
        if not HAS_STARLETTE:
            raise ImportError(
                "Starlette/uvicorn not installed. Install with: pip install starlette uvicorn"
            )
        
        transport = SseServerTransport("/sse")
        
        async def handle_sse(request):
            async with transport.connect_sse(
                request.scope,
                request.receive,
                request._send
            ) as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        
        async def health(request):
            return Response("OK", media_type="text/plain")
        
        app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
                Route("/health", endpoint=health, methods=["GET"]),
            ]
        )
        
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        
        logger.info(f"RAGFlow MCP Server running on http://{host}:{port}/sse")
        await server.serve()

    async def run_stdio(self):
        """Run as STDIO server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAGFlow MCP Server")
    parser.add_argument("--sse", action="store_true", help="Run as SSE server")
    parser.add_argument("--stdio", action="store_true", help="Run as STDIO server")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE server")
    parser.add_argument("--port", type=int, default=9400, help="Port for SSE server")
    
    args = parser.parse_args()
    
    if not HAS_MCP:
        print("Error: MCP SDK not installed. Install with: pip install mcp")
        sys.exit(1)
    
    try:
        server = RAGFlowMCPServer()
        
        if args.stdio:
            asyncio.run(server.run_stdio())
        else:
            # Default to SSE
            asyncio.run(server.run_sse(args.host, args.port))
            
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
