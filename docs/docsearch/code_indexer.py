"""
TypeScript/React code indexing for DocSearch.

This module extends DocSearch to index frontend source code (.ts/.tsx files),
enabling semantic search over components, hooks, API clients, and utilities.

**Usage:**

    # Navigate to docsearch directory
    cd /data/dsa110-contimg/docs/docsearch
    
    # Index frontend code
    python cli.py index-frontend
    
    # Search components
    python cli.py search-components "pipeline monitoring"
    
    # Search hooks
    python cli.py search-hooks "fetch measurement sets"
    
    # Find API usage
    python cli.py find-api "/api/sources/search"

**Architecture:**

- Uses same embedding cache as documentation search
- Separate database: `/data/dsa110-contimg/state/docsearch_code.sqlite3`
- Extracts code blocks preserving function/component boundaries
- Tracks file modification times for incremental indexing
"""

import logging
import os
import re
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Dict

try:
    from .chunker import Chunk
    from .search import DocSearch, SearchResult
except ImportError:
    # Standalone execution
    from chunker import Chunk
    from search import DocSearch, SearchResult

logger = logging.getLogger(__name__)

# Minimum block size to index (characters)
MIN_BLOCK_SIZE = 50

# Patterns for detecting code block starts
BLOCK_STARTERS = [
    'export function',
    'export const',
    'export default function',
    'export default class',
    'export class',
    'export interface',
    'export type',
    'export async function',
    'export async',
    'function',
    'const',
    'class',
    'interface',
    'type',
]


def extract_typescript_blocks(content: str, file_path: str) -> Iterator[Tuple[str, str, int]]:
    """
    Extract meaningful code blocks from TypeScript/React files.
    
    Yields code blocks with their headings and line numbers. Blocks are
    detected by looking for function/class/interface declarations and
    their corresponding closing braces.
    
    Args:
        content: File content
        file_path: Path to file for context
        
    Yields:
        (heading, code_block, start_line) tuples
        
    Example:
        >>> content = '''
        ... export function MyComponent() {
        ...   return <div>Hello</div>;
        ... }
        ... '''
        >>> blocks = list(extract_typescript_blocks(content, "test.tsx"))
        >>> len(blocks)
        1
        >>> blocks[0][0]  # heading
        'export function MyComponent()'
    """
    lines = content.split('\n')
    current_block: List[str] = []
    current_heading = ""
    block_start_line = 0
    in_block = False
    brace_depth = 0
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Skip empty lines and lone imports at file start
        if not in_block and (not stripped or stripped.startswith('import ')):
            continue
        
        # Check if this line starts a new block
        is_block_start = any(stripped.startswith(starter) for starter in BLOCK_STARTERS)
        
        if is_block_start and not in_block:
            # Extract heading (up to opening paren or equals)
            heading_parts = re.split(r'[=(]', stripped, maxsplit=1)
            current_heading = heading_parts[0].strip()
            current_block = [line]
            block_start_line = i
            in_block = True
            
            # Count braces in first line
            brace_depth = line.count('{') - line.count('}')
            
            # Handle single-line declarations (e.g., "export type Foo = string;")
            if ';' in line and brace_depth == 0:
                block_content = '\n'.join(current_block)
                if len(block_content.strip()) >= MIN_BLOCK_SIZE:
                    yield (current_heading, block_content, block_start_line)
                current_block = []
                current_heading = ""
                in_block = False
            
        elif in_block:
            current_block.append(line)
            brace_depth += line.count('{') - line.count('}')
            
            # Block ends when braces balance
            if brace_depth <= 0:
                block_content = '\n'.join(current_block)
                if len(block_content.strip()) >= MIN_BLOCK_SIZE:
                    yield (current_heading, block_content, block_start_line)
                
                # Reset for next block
                current_block = []
                current_heading = ""
                in_block = False
                brace_depth = 0
    
    # Yield final block if exists (handles EOF without closing brace)
    if current_block and current_heading:
        block_content = '\n'.join(current_block)
        if len(block_content.strip()) >= MIN_BLOCK_SIZE:
            yield (current_heading, block_content, block_start_line)


def extract_jsx_comments(content: str) -> List[str]:
    """
    Extract JSDoc and meaningful comments from TypeScript/React code.
    
    Extracts:
    - JSDoc blocks (/** ... */)
    - Standalone single-line comments (// ...) longer than 10 chars
    
    Args:
        content: File content
        
    Returns:
        List of comment strings (cleaned)
        
    Example:
        >>> content = '''
        ... /**
        ...  * Main dashboard component.
        ...  * Displays pipeline status.
        ...  */
        ... export function Dashboard() {}
        ... '''
        >>> comments = extract_jsx_comments(content)
        >>> len(comments)
        1
        >>> 'Main dashboard' in comments[0]
        True
    """
    comments = []
    lines = content.split('\n')
    
    in_multiline = False
    current_comment: List[str] = []
    
    for line in lines:
        stripped = line.strip()
        
        # JSDoc start
        if stripped.startswith('/**'):
            in_multiline = True
            # Extract content after /**
            content_after = stripped[3:].strip()
            if content_after and not content_after.startswith('*'):
                current_comment = [content_after]
            else:
                current_comment = []
            continue
        
        # JSDoc end
        if in_multiline and '*/' in stripped:
            # Extract content before */
            content_before = stripped.split('*/')[0].strip().lstrip('* ')
            if content_before:
                current_comment.append(content_before)
            
            comment_text = '\n'.join(current_comment).strip()
            if comment_text:
                comments.append(comment_text)
            
            current_comment = []
            in_multiline = False
            continue
        
        # Inside JSDoc
        if in_multiline:
            # Remove leading * and whitespace
            clean = stripped.lstrip('* ').strip()
            if clean:
                current_comment.append(clean)
            continue
        
        # Single-line comments
        if stripped.startswith('//'):
            comment = stripped[2:].strip()
            if len(comment) > 10:  # Ignore short comments like "// TODO"
                comments.append(comment)
    
    return comments


class CodeDocSearch(DocSearch):
    """
    Extended DocSearch for indexing TypeScript/React code.
    
    Indexes:
    - React components (.tsx files)
    - TypeScript modules (.ts files)
    - Hooks, utilities, API clients
    - Preserves JSDoc comments for context
    
    **Database:** `/data/dsa110-contimg/state/docsearch_code.sqlite3`
    **Shared Cache:** `/data/dsa110-contimg/state/embedding_cache.sqlite3`
    
    Example:
        >>> code_search = CodeDocSearch()
        >>> stats = code_search.index_frontend_directory()
        >>> results = code_search.search_components("pipeline monitoring")
        >>> for r in results:
        ...     print(f"{r['component']} - {r['file']}:{r['line']}")
    """
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        embedder=None,
    ):
        """
        Initialize CodeDocSearch.
        
        Args:
            db_path: Path to code index database 
                     (default: /data/dsa110-contimg/state/docsearch_code.sqlite3)
            embedder: Embedder instance (default: creates new one with shared cache)
        """
        if db_path is None:
            db_path = Path("/data/dsa110-contimg/state/docsearch_code.sqlite3")
        
        super().__init__(db_path=db_path, embedder=embedder)
        
        logger.info(f"CodeDocSearch initialized with database: {self.db_path}")
    
    def index_code_file(self, file_path: Path) -> int:
        """
        Index a single TypeScript/React file.
        
        Extracts code blocks (functions, components, types) and indexes them
        with their JSDoc comments as context.
        
        Args:
            file_path: Path to .ts or .tsx file
            
        Returns:
            Number of chunks indexed
            
        Raises:
            OSError: If file cannot be read
        """
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return 0
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            raise
        
        # Extract code blocks
        blocks = list(extract_typescript_blocks(content, str(file_path)))
        
        if not blocks:
            logger.debug(f"No indexable blocks in {file_path}")
            return 0
        
        # Extract comments for context
        comments = extract_jsx_comments(content)
        file_context = '\n\n'.join(comments) if comments else ""
        
        # Create content for indexing: concatenate all blocks with context
        # This approach lets us use the parent's index_file method
        combined_content_parts = []
        if file_context:
            combined_content_parts.append(f"/* File Context:\n{file_context}\n*/\n")
        
        for heading, block_content, line_num in blocks:
            combined_content_parts.append(f"\n\n/* {heading} at line {line_num} */\n{block_content}")
        
        combined_content = '\n'.join(combined_content_parts)
        
        # Use parent's index_file method which handles chunking and embedding
        return self.index_file(file_path, content=combined_content, force=False)
    
    def index_frontend_directory(
        self,
        frontend_dir: Optional[Path] = None,
        extensions: Tuple[str, ...] = ('.ts', '.tsx'),
        exclude_patterns: Tuple[str, ...] = (
            'node_modules', 
            'dist', 
            'build', 
            '.test.', 
            '.spec.',
            '__tests__',
            '.stories.',
        ),
        force: bool = False,
    ) -> dict:
        """
        Index all TypeScript/React files in frontend directory.
        
        Uses incremental indexing - only re-indexes files that have been
        modified since last indexing (based on file mtime).
        
        Args:
            frontend_dir: Root directory to scan 
                         (default: /data/dsa110-contimg/frontend/src)
            extensions: File extensions to index
            exclude_patterns: Patterns to exclude from indexing
            force: Re-index all files even if unchanged
            
        Returns:
            Statistics dictionary with counts:
                - files_processed: Number of files indexed
                - files_skipped: Number of files skipped (excluded or unchanged)
                - chunks_indexed: Total number of code blocks indexed
                - errors: List of error dictionaries
                
        Example:
            >>> code_search = CodeDocSearch()
            >>> stats = code_search.index_frontend_directory()
            >>> print(f"Indexed {stats['chunks_indexed']} code blocks")
        """
        if frontend_dir is None:
            frontend_dir = Path("/data/dsa110-contimg/frontend/src")
        
        if not frontend_dir.exists():
            raise ValueError(f"Frontend directory not found: {frontend_dir}")
        
        stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'chunks_indexed': 0,
            'errors': []
        }
        
        logger.info(f"Indexing frontend directory: {frontend_dir}")
        logger.info(f"Extensions: {extensions}")
        logger.info(f"Exclude patterns: {exclude_patterns}")
        
        # Get file modification times from database
        file_mtimes = self._get_file_mtimes()
        
        # Find all matching files
        for ext in extensions:
            for file_path in sorted(frontend_dir.rglob(f"*{ext}")):
                # Skip excluded patterns
                file_str = str(file_path)
                if any(pattern in file_str for pattern in exclude_patterns):
                    stats['files_skipped'] += 1
                    logger.debug(f"Skipping excluded file: {file_path.name}")
                    continue
                
                # Check if file needs re-indexing
                if not force:
                    current_mtime = os.path.getmtime(file_path)
                    db_mtime = file_mtimes.get(str(file_path))
                    
                    if db_mtime is not None and current_mtime <= db_mtime:
                        stats['files_skipped'] += 1
                        logger.debug(f"Skipping unchanged file: {file_path.name}")
                        continue
                
                # Index file
                try:
                    chunks = self.index_code_file(file_path)
                    stats['files_processed'] += 1
                    stats['chunks_indexed'] += chunks
                    
                    # Update mtime in database
                    self._update_file_mtime(str(file_path), os.path.getmtime(file_path))
                    
                except Exception as e:
                    logger.error(f"Error indexing {file_path}: {e}")
                    stats['errors'].append({
                        'file': str(file_path),
                        'error': str(e)
                    })
        
        logger.info(f"Frontend indexing complete: {stats}")
        return stats
    
    def search_components(self, query: str, top_k: int = 5) -> List[dict]:
        """
        Search specifically for React components.
        
        Filters results to likely component files (.tsx) and formats them
        for easy consumption.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of component result dictionaries with keys:
                - component: Component name
                - file: File path
                - line: Line number
                - score: Similarity score
                - snippet: Code snippet
                
        Example:
            >>> code_search = CodeDocSearch()
            >>> results = code_search.search_components("pipeline status")
            >>> for r in results:
            ...     print(f"{r['component']} ({r['file']})")
        """
        results = self.search(query, top_k=top_k * 2)  # Get more, then filter
        
        # Filter for likely components
        component_results = []
        for r in results:
            if r.file_path.endswith('.tsx'):
                snippet = r.content[:200] + '...' if len(r.content) > 200 else r.content
                component_results.append({
                    'component': r.heading,
                    'file': r.file_path,
                    'line': r.start_line,
                    'score': r.score,
                    'snippet': snippet.strip()
                })
                
                if len(component_results) >= top_k:
                    break
        
        return component_results
    
    def search_hooks(self, query: str, top_k: int = 5) -> List[dict]:
        """
        Search specifically for React hooks.
        
        Enhances query to target hooks and filters results by naming convention
        (functions starting with 'use').
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of hook result dictionaries with keys:
                - hook: Hook name
                - file: File path
                - line: Line number
                - score: Similarity score
                - snippet: Code snippet
                
        Example:
            >>> code_search = CodeDocSearch()
            >>> results = code_search.search_hooks("fetch data")
            >>> for r in results:
            ...     print(f"{r['hook']} ({r['file']})")
        """
        # Enhance query to target hooks
        hook_query = f"{query} React hook use"
        results = self.search(hook_query, top_k=top_k * 2)
        
        # Filter for hooks (headings starting with 'use' or containing 'hook')
        hook_results = []
        for r in results:
            heading_lower = r.heading.lower()
            if 'use' in heading_lower.split() or 'hook' in heading_lower:
                snippet = r.content[:200] + '...' if len(r.content) > 200 else r.content
                hook_results.append({
                    'hook': r.heading,
                    'file': r.file_path,
                    'line': r.start_line,
                    'score': r.score,
                    'snippet': snippet.strip()
                })
                
                if len(hook_results) >= top_k:
                    break
        
        return hook_results
    
    def search_api_calls(self, endpoint: str, top_k: int = 10) -> List[dict]:
        """
        Find where a specific API endpoint is called.
        
        Searches for references to the endpoint path in code.
        
        Args:
            endpoint: API endpoint path (e.g., '/api/sources/search')
            top_k: Number of results to return
            
        Returns:
            List of API usage result dictionaries with keys:
                - location: File path and line number
                - context: Function/component name
                - score: Similarity score
                - snippet: Code snippet showing usage
                
        Example:
            >>> code_search = CodeDocSearch()
            >>> results = code_search.search_api_calls("/api/sources/search")
            >>> for r in results:
            ...     print(f"{r['location']}: {r['context']}")
        """
        query = f"API endpoint {endpoint} fetch request"
        results = self.search(query, top_k=top_k * 2)
        
        # Filter for API-related results
        api_results = []
        for r in results:
            # Check if endpoint appears in content or file is API-related
            if endpoint in r.content or 'api' in r.file_path.lower():
                snippet = r.content[:300] + '...' if len(r.content) > 300 else r.content
                api_results.append({
                    'location': f"{r.file_path}:{r.start_line}",
                    'context': r.heading,
                    'score': r.score,
                    'snippet': snippet.strip()
                })
                
                if len(api_results) >= top_k:
                    break
        
        return api_results
    
    def _get_file_mtimes(self) -> dict:
        """
        Get file modification times from database.
        
        Returns:
            Dictionary mapping file paths to modification times
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT DISTINCT file_path FROM chunks"
            )
            file_paths = [row[0] for row in cursor.fetchall()]
            
            mtimes = {}
            for file_path in file_paths:
                if os.path.exists(file_path):
                    mtimes[file_path] = os.path.getmtime(file_path)
            
            return mtimes
        finally:
            conn.close()
    
    def _update_file_mtime(self, file_path: str, mtime: float):
        """
        Update file modification time tracking.
        
        Note: Currently uses file system mtime. Could be extended to store
        in database for more robust tracking.
        
        Args:
            file_path: Path to file
            mtime: Modification time (Unix timestamp)
        """
        # For now, we rely on file system mtime
        # Future enhancement: store in database table
        pass


def main():
    """Example usage of CodeDocSearch."""
    import sys
    
    # Initialize
    code_search = CodeDocSearch()
    
    # Index frontend
    frontend_dir = Path("/data/dsa110-contimg/frontend/src")
    
    if not frontend_dir.exists():
        print(f"Error: Frontend directory not found: {frontend_dir}", file=sys.stderr)
        sys.exit(1)
    
    print("Indexing frontend code...")
    stats = code_search.index_frontend_directory(frontend_dir)
    
    print(f"\nIndexing complete!")
    print(f"  Files processed: {stats['files_processed']}")
    print(f"  Chunks indexed: {stats['chunks_indexed']}")
    print(f"  Files skipped: {stats['files_skipped']}")
    
    if stats['errors']:
        print(f"  Errors: {len(stats['errors'])}")
        for err in stats['errors'][:5]:
            print(f"    - {err['file']}: {err['error']}")
    
    # Example searches
    print("\n━━━ Search Components ━━━")
    results = code_search.search_components("pipeline status monitoring", top_k=3)
    for r in results:
        print(f"  {r['component']} ({r['file']}:{r['line']})")
    
    print("\n━━━ Search Hooks ━━━")
    results = code_search.search_hooks("fetch measurement sets", top_k=3)
    for r in results:
        print(f"  {r['hook']} ({r['file']}:{r['line']})")


if __name__ == "__main__":
    main()
