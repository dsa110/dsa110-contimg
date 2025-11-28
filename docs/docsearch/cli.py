"""
Command-line interface for local documentation search.

**Location:** This script has been moved to `docs/docsearch/` and should be run
directly from that directory.

Usage:
    # Navigate to the directory
    cd /data/dsa110-contimg/docs/docsearch

    # Index documentation
    python cli.py index

    # Search
    python cli.py search "how to convert uvh5"

    # Show stats
    python cli.py stats
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_index(args):
    """Index documentation directory."""
    from search import DocSearch

    search = DocSearch()

    stats = search.index_directory(
        directory=Path(args.docs_dir),
        extensions=tuple(args.extensions.split(",")),
        force=args.force,
    )

    print(f"\nIndexing complete:")
    print(f"  Files processed: {stats['files_processed']}")
    print(f"  Files skipped: {stats['files_skipped']}")
    print(f"  Chunks indexed: {stats['chunks_indexed']}")

    if stats['errors']:
        print(f"  Errors: {len(stats['errors'])}")
        for err in stats['errors'][:5]:
            print(f"    - {err['file']}: {err['error']}")


def cmd_search(args):
    """Search indexed documentation."""
    from .search import DocSearch

    search = DocSearch()

    results = search.search(
        query=args.query,
        top_k=args.top_k,
        min_score=args.min_score,
    )

    if not results:
        print("No results found.")
        return

    print(f"\nFound {len(results)} results:\n")

    for i, r in enumerate(results, 1):
        print(f"━━━ Result {i} (score: {r.score:.3f}) ━━━")
        print(f"File: {r.file_path}")
        if r.heading:
            print(f"Section: {r.heading}")
        print(f"Lines: {r.start_line}-{r.end_line}")
        print()

        # Truncate long content
        content = r.content
        if len(content) > 500 and not args.full:
            content = content[:500] + "..."

        print(content)
        print()


def cmd_stats(args):
    """Show index statistics."""
    from .search import DocSearch

    search = DocSearch()
    stats = search.get_stats()

    print("\nIndex Statistics:")
    print(f"  Database: {stats['db_path']}")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Indexed files: {stats['indexed_files']}")

    if stats.get('embedding_cache'):
        cache = stats['embedding_cache']
        print(f"\nEmbedding Cache:")
        print(f"  Location: {cache['cache_db']}")
        print(f"  Total cached: {cache['total_cached']}")
        if cache.get('by_model'):
            for model, count in cache['by_model'].items():
                print(f"    {model}: {count}")


def cmd_clear(args):
    """Clear the index."""
    from .search import DocSearch

    if not args.yes:
        response = input("Are you sure you want to clear the index? [y/N] ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    search = DocSearch()
    search.clear()
    print("Index cleared.")


def cmd_index_frontend(args):
    """Index frontend TypeScript/React code."""
    from .code_indexer import CodeDocSearch

    code_search = CodeDocSearch()
    frontend_dir = Path(args.frontend_dir)

    if not frontend_dir.exists():
        print(f"Error: Frontend directory not found: {frontend_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Indexing frontend code in {frontend_dir}...")
    stats = code_search.index_frontend_directory(
        frontend_dir=frontend_dir,
        extensions=tuple(args.extensions),
        exclude_patterns=tuple(args.exclude),
        force=args.force,
    )

    print(f"\nIndexing complete!")
    print(f"  Files processed: {stats['files_processed']}")
    print(f"  Chunks indexed: {stats['chunks_indexed']}")
    print(f"  Files skipped: {stats['files_skipped']}")

    if stats['errors']:
        print(f"  Errors: {len(stats['errors'])}")
        for err in stats['errors'][:5]:
            print(f"    - {err['file']}: {err['error']}")


def cmd_search_components(args):
    """Search for React components."""
    from .code_indexer import CodeDocSearch

    code_search = CodeDocSearch()
    results = code_search.search_components(args.query, top_k=args.top_k)

    if not results:
        print("No components found.")
        return

    print(f"\nFound {len(results)} components:\n")

    for i, r in enumerate(results, 1):
        print(f"━━━ {i}. {r['component']} ━━━")
        print(f"File: {r['file']}:{r['line']}")
        print(f"Score: {r['score']:.3f}")
        print()
        print(r['snippet'])
        print()


def cmd_search_hooks(args):
    """Search for React hooks."""
    from .code_indexer import CodeDocSearch

    code_search = CodeDocSearch()
    results = code_search.search_hooks(args.query, top_k=args.top_k)

    if not results:
        print("No hooks found.")
        return

    print(f"\nFound {len(results)} hooks:\n")

    for i, r in enumerate(results, 1):
        print(f"━━━ {i}. {r['hook']} ━━━")
        print(f"File: {r['file']}:{r['line']}")
        print(f"Score: {r['score']:.3f}")
        print()
        print(r['snippet'])
        print()


def cmd_find_api(args):
    """Find where an API endpoint is used."""
    from .code_indexer import CodeDocSearch

    code_search = CodeDocSearch()
    results = code_search.search_api_calls(args.endpoint, top_k=args.top_k)

    if not results:
        print(f"No usage found for endpoint: {args.endpoint}")
        return

    print(f"\nFound {len(results)} usages of {args.endpoint}:\n")

    for i, r in enumerate(results, 1):
        print(f"━━━ {i}. {r['location']} ━━━")
        print(f"Context: {r['context']}")
        print(f"Score: {r['score']:.3f}")
        print()
        print(r['snippet'])
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Local documentation search using SQLite and embeddings"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Index command
    index_parser = subparsers.add_parser("index", help="Index documentation")
    index_parser.add_argument(
        "--docs-dir",
        default="/data/dsa110-contimg/docs",
        help="Documentation directory"
    )
    index_parser.add_argument(
        "--extensions",
        default=".md,.txt,.rst",
        help="File extensions to index (comma-separated)"
    )
    index_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-index all files even if unchanged"
    )
    index_parser.set_defaults(func=cmd_index)

    # Search command
    search_parser = subparsers.add_parser("search", help="Search documentation")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results"
    )
    search_parser.add_argument(
        "--min-score",
        type=float,
        default=0.3,
        help="Minimum similarity score"
    )
    search_parser.add_argument(
        "--full",
        action="store_true",
        help="Show full content (don't truncate)"
    )
    search_parser.set_defaults(func=cmd_search)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show index statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear the index")
    clear_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation"
    )
    clear_parser.set_defaults(func=cmd_clear)

    # Index frontend code
    index_frontend_parser = subparsers.add_parser(
        "index-frontend",
        help="Index frontend TypeScript/React code"
    )
    index_frontend_parser.add_argument(
        "--frontend-dir",
        type=str,
        default="/data/dsa110-contimg/frontend/src",
        help="Frontend source directory (default: /data/dsa110-contimg/frontend/src)"
    )
    index_frontend_parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".ts", ".tsx"],
        help="File extensions to index (default: .ts .tsx)"
    )
    index_frontend_parser.add_argument(
        "--exclude",
        nargs="+",
        default=["node_modules", "dist", "build", ".test.", ".spec.", "__tests__"],
        help="Patterns to exclude"
    )
    index_frontend_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-index all files even if unchanged"
    )
    index_frontend_parser.set_defaults(func=cmd_index_frontend)

    # Search components
    search_components_parser = subparsers.add_parser(
        "search-components",
        help="Search for React components"
    )
    search_components_parser.add_argument("query", type=str, help="Search query")
    search_components_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results"
    )
    search_components_parser.set_defaults(func=cmd_search_components)

    # Search hooks
    search_hooks_parser = subparsers.add_parser(
        "search-hooks",
        help="Search for React hooks"
    )
    search_hooks_parser.add_argument("query", type=str, help="Search query")
    search_hooks_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results"
    )
    search_hooks_parser.set_defaults(func=cmd_search_hooks)

    # Find API usage
    find_api_parser = subparsers.add_parser(
        "find-api",
        help="Find API endpoint usage"
    )
    find_api_parser.add_argument("endpoint", type=str, help="API endpoint path")
    find_api_parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of results"
    )
    find_api_parser.set_defaults(func=cmd_find_api)

    args = parser.parse_args()

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
