#!/usr/bin/env python3
"""
Extract Mermaid diagrams from markdown files for debugging in online editors.
"""

import re
import sys
from pathlib import Path

def extract_mermaid_blocks(file_path):
    """Extract all Mermaid code blocks from a markdown file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find all mermaid blocks
    pattern = r'```mermaid\n(.*?)```'
    blocks = re.findall(pattern, content, re.DOTALL)
    
    return blocks

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_mermaid_for_debug.py <markdown_file> [diagram_index]")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    blocks = extract_mermaid_blocks(file_path)
    
    if len(sys.argv) >= 3:
        # Extract specific diagram
        idx = int(sys.argv[2])
        if idx < 0 or idx >= len(blocks):
            print(f"Error: Diagram index {idx} out of range (0-{len(blocks)-1})")
            sys.exit(1)
        print(f"=== Diagram {idx} ===")
        print(blocks[idx].strip())
    else:
        # List all diagrams
        print(f"Found {len(blocks)} Mermaid diagrams in {file_path}")
        print("\nTo extract a specific diagram, run:")
        print(f"  {sys.argv[0]} {file_path} <index>")
        print("\nRecommended online debuggers:")
        print("  1. Mermaid Live Editor: https://mermaid.live")
        print("  2. Maid (linting): https://maid-site.pages.dev")
        print("  3. SimpleMermaid: https://simplemermaid.com")
        print("\nDiagram indices:")
        for i, block in enumerate(blocks):
            first_line = block.strip().split('\n')[0] if block.strip() else ''
            print(f"  {i}: {first_line[:60]}...")

if __name__ == '__main__':
    main()

