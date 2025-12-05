import argparse

from dsa110_contimg.docsearch import DocSearch


def main():
    parser = argparse.ArgumentParser(
        description="Command-line interface for searching documentation."
    )
    parser.add_argument("query", type=str, help="The search query to find relevant documentation.")
    parser.add_argument(
        "--top-k", type=int, default=5, help="Number of top results to return (default: 5)."
    )

    args = parser.parse_args()

    search = DocSearch()
    results = search.search(args.query, top_k=args.top_k)

    for r in results:
        print(f"{r.score:.3f} - {r.file_path}: {r.heading}")
        print(r.content[:200])


if __name__ == "__main__":
    main()
