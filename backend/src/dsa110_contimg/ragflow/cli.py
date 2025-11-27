#!/usr/bin/env python3
"""
RAGFlow document upload CLI for DSA-110.

Upload documentation to RAGFlow knowledge base for retrieval.

Usage:
    # Upload all docs with default settings
    python -m dsa110_contimg.ragflow.cli upload --api-key YOUR_KEY
    
    # Upload specific directory
    python -m dsa110_contimg.ragflow.cli upload \
        --docs-dir /data/dsa110-contimg/docs \
        --dataset "My Dataset" \
        --api-key YOUR_KEY
    
    # List datasets
    python -m dsa110_contimg.ragflow.cli list-datasets --api-key YOUR_KEY
    
    # Test retrieval
    python -m dsa110_contimg.ragflow.cli query \
        --question "How do I convert UVH5 files?" \
        --api-key YOUR_KEY
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .client import RAGFlowClient, RAGFlowError
from .config import RAGFlowConfig
from .uploader import DocumentUploader, upload_dsa110_docs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_upload(args: argparse.Namespace) -> int:
    """Upload documents to RAGFlow."""
    try:
        config = RAGFlowConfig(
            api_key=args.api_key,
            base_url=args.base_url,
        )
        
        if not config.api_key:
            logger.error("API key required. Set RAGFLOW_API_KEY or use --api-key")
            return 1
        
        client = RAGFlowClient(config=config)
        
        # Health check
        if not client.health_check():
            logger.error(f"Cannot connect to RAGFlow at {config.base_url}")
            return 1
        
        logger.info(f"Connected to RAGFlow at {config.base_url}")
        
        # Get or create dataset
        dataset = client.get_or_create_dataset(
            name=args.dataset,
            description=args.description or f"Documentation from {args.docs_dir}",
            chunk_method=args.chunk_method,
        )
        
        dataset_id = dataset["id"]
        logger.info(f"Using dataset: {args.dataset} (ID: {dataset_id})")
        
        # Upload documents
        uploader = DocumentUploader(
            client=client,
            batch_size=args.batch_size,
            parse_after_upload=not args.no_parse,
            wait_for_parsing=not args.no_wait,
        )
        
        stats = uploader.upload_directory(
            args.docs_dir,
            dataset_id,
            recursive=not args.no_recursive,
        )
        
        # Report results
        print("\n" + "=" * 60)
        print("Upload Summary")
        print("=" * 60)
        print(f"Total files:    {stats.total_files}")
        print(f"Uploaded:       {stats.uploaded}")
        print(f"Failed:         {stats.failed}")
        print(f"Total chunks:   {stats.total_chunks}")
        print(f"Duration:       {stats.duration_seconds:.1f}s")
        print(f"Success rate:   {stats.success_rate:.1f}%")
        
        if stats.failed > 0:
            print("\nFailed files:")
            for result in stats.results:
                if not result.success:
                    print(f"  - {result.file_path}: {result.error}")
        
        return 0 if stats.failed == 0 else 1
        
    except RAGFlowError as e:
        logger.error(f"RAGFlow error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


def cmd_list_datasets(args: argparse.Namespace) -> int:
    """List available datasets."""
    try:
        config = RAGFlowConfig(api_key=args.api_key, base_url=args.base_url)
        
        if not config.api_key:
            logger.error("API key required")
            return 1
        
        client = RAGFlowClient(config=config)
        datasets = client.list_datasets()
        
        if not datasets:
            print("No datasets found")
            return 0
        
        print(f"\nFound {len(datasets)} dataset(s):\n")
        for ds in datasets:
            print(f"ID:          {ds.get('id')}")
            print(f"Name:        {ds.get('name')}")
            print(f"Description: {ds.get('description', 'N/A')}")
            print(f"Documents:   {ds.get('document_count', 0)}")
            print(f"Chunks:      {ds.get('chunk_count', 0)}")
            print(f"Model:       {ds.get('embedding_model', 'N/A')}")
            print("-" * 40)
        
        return 0
        
    except RAGFlowError as e:
        logger.error(f"RAGFlow error: {e}")
        return 1


def cmd_list_documents(args: argparse.Namespace) -> int:
    """List documents in a dataset."""
    try:
        config = RAGFlowConfig(api_key=args.api_key, base_url=args.base_url)
        
        if not config.api_key:
            logger.error("API key required")
            return 1
        
        client = RAGFlowClient(config=config)
        
        # Find dataset by name or ID
        dataset = client.get_dataset(args.dataset)
        if not dataset:
            # Try as ID
            datasets = client.list_datasets()
            dataset = next((d for d in datasets if d.get("id") == args.dataset), None)
        
        if not dataset:
            logger.error(f"Dataset not found: {args.dataset}")
            return 1
        
        docs = client.list_documents(dataset["id"], page_size=100)
        
        if not docs:
            print("No documents found")
            return 0
        
        print(f"\nFound {len(docs)} document(s):\n")
        for doc in docs:
            status = doc.get("run", "unknown").upper()
            progress = doc.get("progress", 0) * 100
            print(f"  {doc.get('name'):<40} {status:>8} {progress:>5.0f}% {doc.get('chunk_count', 0):>5} chunks")
        
        return 0
        
    except RAGFlowError as e:
        logger.error(f"RAGFlow error: {e}")
        return 1


def cmd_query(args: argparse.Namespace) -> int:
    """Query the knowledge base."""
    try:
        config = RAGFlowConfig(api_key=args.api_key, base_url=args.base_url)
        
        if not config.api_key:
            logger.error("API key required")
            return 1
        
        client = RAGFlowClient(config=config)
        
        # Get dataset IDs
        if args.dataset:
            dataset = client.get_dataset(args.dataset)
            if not dataset:
                logger.error(f"Dataset not found: {args.dataset}")
                return 1
            dataset_ids = [dataset["id"]]
        else:
            # Search all datasets
            datasets = client.list_datasets()
            dataset_ids = [d["id"] for d in datasets]
        
        if not dataset_ids:
            logger.error("No datasets available")
            return 1
        
        # Perform retrieval
        results = client.retrieve(
            dataset_ids=dataset_ids,
            question=args.question,
            page_size=args.top_k,
            similarity_threshold=args.threshold,
        )
        
        if not results:
            print("No results found")
            return 0
        
        print(f"\nFound {len(results)} result(s) for: {args.question}\n")
        print("=" * 70)
        
        for i, chunk in enumerate(results, 1):
            score = chunk.get("similarity", chunk.get("score", 0))
            doc_name = chunk.get("document_name", chunk.get("docnm_kwd", "Unknown"))
            content = chunk.get("content", chunk.get("content_ltks", ""))
            
            print(f"\n[{i}] Score: {score:.4f} | Document: {doc_name}")
            print("-" * 70)
            
            # Truncate long content
            if len(content) > 500:
                content = content[:500] + "..."
            print(content)
            print()
        
        return 0
        
    except RAGFlowError as e:
        logger.error(f"RAGFlow error: {e}")
        return 1


def cmd_create_chat(args: argparse.Namespace) -> int:
    """Create a chat assistant."""
    try:
        config = RAGFlowConfig(api_key=args.api_key, base_url=args.base_url)
        
        if not config.api_key:
            logger.error("API key required")
            return 1
        
        client = RAGFlowClient(config=config)
        
        # Get dataset IDs
        datasets = client.list_datasets()
        if args.datasets:
            # Filter by names
            dataset_ids = [
                d["id"] for d in datasets
                if d.get("name") in args.datasets
            ]
        else:
            # Use all datasets
            dataset_ids = [d["id"] for d in datasets]
        
        if not dataset_ids:
            logger.error("No datasets found")
            return 1
        
        chat = client.create_chat(
            name=args.name,
            dataset_ids=dataset_ids,
            system_prompt=args.prompt,
        )
        
        print(f"\nCreated chat assistant:")
        print(f"  Name: {chat.get('name')}")
        print(f"  ID:   {chat.get('id')}")
        print(f"  Datasets: {len(dataset_ids)}")
        
        return 0
        
    except RAGFlowError as e:
        logger.error(f"RAGFlow error: {e}")
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAGFlow document management for DSA-110",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Global arguments
    parser.add_argument(
        "--api-key",
        default=os.environ.get("RAGFLOW_API_KEY"),
        help="RAGFlow API key (or set RAGFLOW_API_KEY)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:9380",
        help="RAGFlow API base URL",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Upload command
    upload_parser = subparsers.add_parser(
        "upload",
        help="Upload documents to RAGFlow",
    )
    upload_parser.add_argument(
        "--docs-dir",
        default="/data/dsa110-contimg/docs",
        help="Documentation directory",
    )
    upload_parser.add_argument(
        "--dataset",
        default="DSA-110 Documentation",
        help="Dataset name",
    )
    upload_parser.add_argument(
        "--description",
        help="Dataset description",
    )
    upload_parser.add_argument(
        "--chunk-method",
        default="naive",
        choices=[
            "naive", "book", "email", "laws", "manual", "one",
            "paper", "picture", "presentation", "qa", "table", "tag",
        ],
        help="Document chunking method",
    )
    upload_parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Files per upload batch",
    )
    upload_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't scan subdirectories",
    )
    upload_parser.add_argument(
        "--no-parse",
        action="store_true",
        help="Don't parse documents after upload",
    )
    upload_parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for parsing to complete",
    )
    upload_parser.set_defaults(func=cmd_upload)
    
    # List datasets command
    list_ds_parser = subparsers.add_parser(
        "list-datasets",
        help="List available datasets",
    )
    list_ds_parser.set_defaults(func=cmd_list_datasets)
    
    # List documents command
    list_docs_parser = subparsers.add_parser(
        "list-documents",
        help="List documents in a dataset",
    )
    list_docs_parser.add_argument(
        "dataset",
        help="Dataset name or ID",
    )
    list_docs_parser.set_defaults(func=cmd_list_documents)
    
    # Query command
    query_parser = subparsers.add_parser(
        "query",
        help="Query the knowledge base",
    )
    query_parser.add_argument(
        "question",
        help="Question to search for",
    )
    query_parser.add_argument(
        "--dataset",
        help="Dataset name to search (default: all)",
    )
    query_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to return",
    )
    query_parser.add_argument(
        "--threshold",
        type=float,
        default=0.2,
        help="Minimum similarity threshold",
    )
    query_parser.set_defaults(func=cmd_query)
    
    # Create chat command
    chat_parser = subparsers.add_parser(
        "create-chat",
        help="Create a chat assistant",
    )
    chat_parser.add_argument(
        "name",
        help="Chat assistant name",
    )
    chat_parser.add_argument(
        "--datasets",
        nargs="+",
        help="Dataset names to include (default: all)",
    )
    chat_parser.add_argument(
        "--prompt",
        help="Custom system prompt",
    )
    chat_parser.set_defaults(func=cmd_create_chat)
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.command:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
