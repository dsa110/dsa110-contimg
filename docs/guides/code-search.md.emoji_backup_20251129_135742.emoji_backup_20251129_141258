# Frontend Code Search

**Find React components, hooks, and API usage across the codebase in seconds.**

---

## TL;DR

```bash
cd /data/dsa110-contimg/docs

# One-time setup (2-5 minutes)
python -m docsearch.cli index-frontend

# Search for stuff
python -m docsearch.cli search-components "pipeline monitoring"
python -m docsearch.cli search-hooks "fetch data"
python -m docsearch.cli find-api "/api/sources/search"
```

**Requirements:** `OPENAI_API_KEY` environment variable must be set.

---

## Common Tasks

### Find a Component

```bash
cd /data/dsa110-contimg/docs

# Find components related to pipeline monitoring
python -m docsearch.cli search-components "pipeline status monitoring"

# Find ESE detection components
python -m docsearch.cli search-components "ESE detection panel"

# Get more results
python -m docsearch.cli search-components "dashboard" --top-k 10
```

**Output shows:** Component name, file location, line number, and code snippet.

---

### Find a Hook

```bash
cd /data/dsa110-contimg/docs

# Find data fetching hooks
python -m docsearch.cli search-hooks "fetch measurement sets"

# Find WebSocket hooks
python -m docsearch.cli search-hooks "streaming service status"

# Get more results
python -m docsearch.cli search-hooks "query" --top-k 10
```

**Output shows:** Hook name, file location, line number, and code snippet.

---

### Track API Usage

```bash
cd /data/dsa110-contimg/docs

# Find everywhere an endpoint is called
python -m docsearch.cli find-api "/api/sources/search"

# Find streaming endpoints
python -m docsearch.cli find-api "/api/streaming/status"

# Get more results
python -m docsearch.cli find-api "/api/ms" --top-k 15
```

**Output shows:** File location, function context, and code snippet showing the
call.

---

## After Changing Code

Just re-run the index command. It only re-indexes changed files (fast):

```bash
cd /data/dsa110-contimg/docs
python -m docsearch.cli index-frontend  # Takes ~30 seconds for typical changes
```

---

## Index a Specific Directory

```bash
cd /data/dsa110-contimg/docs

# Index only components
python -m docsearch.cli index-frontend \
    --frontend-dir /data/dsa110-contimg/frontend/src/components

# Index only hooks
python -m docsearch.cli index-frontend \
    --frontend-dir /data/dsa110-contimg/frontend/src/hooks
```

---

## Troubleshooting

### "No results found"

**Solution:** Index first:

```bash
cd /data/dsa110-contimg/docs
python -m docsearch.cli index-frontend
```

### "Error: No module named 'openai'"

**Solution:** Activate casa6 environment:

```bash
conda activate casa6
cd /data/dsa110-contimg/docs
python -m docsearch.cli index-frontend
```

### "OpenAI API key not found"

**Solution:** Set the environment variable:

```bash
export OPENAI_API_KEY="your-key-here"
# Or add to ~/.bashrc or backend/.env
```

---

## How It Works

- **Indexes** TypeScript/React files into a searchable database
- **Uses** OpenAI embeddings for semantic search (understands meaning, not just
  keywords)
- **Stores** results locally in
  `/data/dsa110-contimg/state/docsearch_code.sqlite3`
- **Caches** embeddings to minimize API costs
- **Tracks** file changes to avoid re-indexing unchanged files

**Performance:**

- First index: 2-5 minutes (~87 files :arrow_right: ~500 code blocks)
- Re-index: <30 seconds (only changed files)
- Search: <2 seconds

---

## Advanced Usage

For Python API usage, detailed configuration, and troubleshooting, see:

**:arrow_right:
[Complete Frontend Code Search Guide](../how-to/development/frontend_code_search.md)**

---

## See Also

- [DocSearch README](../docsearch/README.md) - Core search system documentation
- [Frontend Architecture](../architecture/dashboard/dashboard_architecture.md) -
  Frontend structure overview
