import os
import asyncio
import json
import sys

try:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
except Exception as e:
    print(
        "Missing mcp client library. Run with: uv run --with mcp scripts/test_graphiti_mcp.py",
        file=sys.stderr,
    )
    raise


SERVER_COMMAND = "/home/ubuntu/.local/bin/uv"
SERVER_ARGS = [
    "-q",  # quiet uv to avoid stdout noise corrupting MCP stdio
    "run",
    "--isolated",
    "--directory",
    "/home/ubuntu/proj/mcps/graphiti/mcp_server",
    "graphiti_mcp_server.py",
    "--transport",
    "stdio",
    "--group-id",
    "dsa110-contimg",
]

SERVER_ENV = {
    "NEO4J_URI": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
    "NEO4J_USER": os.environ.get("NEO4J_USER", "neo4j"),
    "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", "demodemo"),
    "EMBEDDING_DIM": os.environ.get("EMBEDDING_DIM", "768"),
    "PYTHONPATH": os.environ.get("PYTHONPATH", "/home/ubuntu/proj/mcps/graphiti"),
    "GEMINI_USE_VERTEX": os.environ.get("GEMINI_USE_VERTEX", "true"),
    "VERTEX_BATCH": os.environ.get("VERTEX_BATCH", "64"),
}


async def main() -> int:
    params = StdioServerParameters(
        command=SERVER_COMMAND,
        args=SERVER_ARGS,
        env={**os.environ, **SERVER_ENV},
    )

    try:
        async with stdio_client(params) as (read, write):
            session = ClientSession(read, write)
            try:
                await asyncio.wait_for(session.initialize(), timeout=15)
            except asyncio.TimeoutError:
                print("Timed out waiting for MCP initialize()", file=sys.stderr)
                return 2

            print("Initialized connection to graphiti-memory MCP server.")

            tools = await session.list_tools()
            resources = await session.list_resources()
            prompts = await session.list_prompts()

            def tidy(obj):
                return json.dumps(obj, indent=2, ensure_ascii=False)

            print("\nTools:")
            print(tidy(tools.model_dump() if hasattr(tools, "model_dump") else tools))

            print("\nResources:")
            print(
                tidy(
                    resources.model_dump()
                    if hasattr(resources, "model_dump")
                    else resources
                )
            )

            print("\nPrompts:")
            print(
                tidy(
                    prompts.model_dump() if hasattr(prompts, "model_dump") else prompts
                )
            )

            # Try reading the status resource if available
            try:
                status_uri = "http://graphiti/status"
                status = await session.read_resource(status_uri)
                print("\nStatus resource:")
                print(
                    tidy(
                        status.model_dump() if hasattr(status, "model_dump") else status
                    )
                )
            except Exception as e:
                print(f"Failed to read status resource: {e}", file=sys.stderr)

            # Try a simple tool call
            try:
                call = await session.call_tool(
                    "embedding_sanity_check", {"text": "hello from mcp client"}
                )
                print("\nembedding_sanity_check:")
                print(tidy(call.model_dump() if hasattr(call, "model_dump") else call))
            except Exception as e:
                print(f"Failed calling embedding_sanity_check: {e}", file=sys.stderr)

            # Optional: list most recent episodes for default group
            try:
                eps = await session.call_tool("get_episodes", {"last_n": 5})
                print("\nget_episodes (last 5):")
                print(tidy(eps.model_dump() if hasattr(eps, "model_dump") else eps))
            except Exception as e:
                print(f"Failed calling get_episodes: {e}", file=sys.stderr)

            # Optional: try a node search in default group
            try:
                nodes = await session.call_tool(
                    "search_memory_nodes",
                    {"query": "calibration pipeline", "max_nodes": 5},
                )
                print("\nsearch_memory_nodes:")
                print(
                    tidy(nodes.model_dump() if hasattr(nodes, "model_dump") else nodes)
                )
            except Exception as e:
                print(f"Failed calling search_memory_nodes: {e}", file=sys.stderr)

            # Optional: try a fact search
            try:
                facts = await session.call_tool(
                    "search_memory_facts", {"query": "calibration", "max_facts": 5}
                )
                print("\nsearch_memory_facts:")
                print(
                    tidy(facts.model_dump() if hasattr(facts, "model_dump") else facts)
                )
            except Exception as e:
                print(f"Failed calling search_memory_facts: {e}", file=sys.stderr)

            # Close the session gracefully
            await session.close()

        return 0
    except Exception as e:
        print(f"Error communicating with graphiti-memory server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
