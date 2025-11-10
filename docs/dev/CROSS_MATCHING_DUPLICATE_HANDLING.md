# Cross-Matching Duplicate Handling Implementation

## Overview

This document describes the implementation of duplicate source handling across multiple catalogs in the DSA-110 cross-matching system. All four potential improvements have been implemented.

## Implemented Improvements

### 1. Multi-Catalog Matching

**Status:** ✅ Implemented

The `CrossMatchStage` now uses `multi_catalog_match()` to select the best match across all catalogs simultaneously, rather than matching each catalog independently.

**Benefits:**
- Ensures each detected source matches to the closest catalog source across all catalogs
- Prevents a source from matching to a distant catalog source when a closer match exists in another catalog
- More efficient matching process

**Implementation:**
- `CrossMatchStage.execute()` queries all catalogs first
- Prepares data dictionaries for `multi_catalog_match()`
- Uses multi-catalog results to build individual catalog match DataFrames
- Preserves per-catalog analysis while ensuring optimal matches

### 2. Master Catalog ID Field

**Status:** ✅ Implemented

Added `master_catalog_id` column to the `cross_matches` table to link entries referring to the same physical source.

**Database Schema:**
```sql
CREATE TABLE cross_matches (
    ...
    master_catalog_id TEXT,
    ...
)
```

**Index:**
```sql
CREATE INDEX idx_cross_matches_master ON cross_matches(master_catalog_id)
```

**Usage:**
- When multiple catalog entries refer to the same source, they share the same `master_catalog_id`
- Master ID priority: NVSS > FIRST > RACS
- Enables querying all catalog associations for a single physical source

**Example:**
```sql
-- Find all catalog associations for a source
SELECT catalog_type, catalog_source_id, master_catalog_id
FROM cross_matches
WHERE master_catalog_id = 'nvss:J123456+012345';
```

### 3. Deduplication Logic

**Status:** ✅ Implemented

Added `identify_duplicate_catalog_sources()` function to identify when multiple catalog entries refer to the same physical source.

**Algorithm:**
1. Collects all catalog entries with their positions
2. Uses `search_around_sky()` to find entries within deduplication radius (default: 2 arcsec)
3. Uses union-find algorithm to group duplicate entries
4. Assigns master catalog ID based on priority (NVSS > FIRST > RACS)

**Function Signature:**
```python
def identify_duplicate_catalog_sources(
    catalog_matches: Dict[str, pd.DataFrame],
    deduplication_radius_arcsec: float = 2.0,
) -> Dict[str, str]:
    """Identify when multiple catalog entries refer to the same physical source."""
```

**Returns:**
Dictionary mapping catalog entries to master IDs:
```python
{
    "nvss:J123456+012345": "nvss:J123456+012345",
    "first:J123456+012345": "nvss:J123456+012345",  # Same source, NVSS is master
    "rax:J123456+012345": "nvss:J123456+012345",   # Same source, NVSS is master
}
```

**Integration:**
- Called automatically in `CrossMatchStage.execute()`
- Master IDs assigned before database storage
- Configurable deduplication radius (default: 2 arcsec)

### 4. UNIQUE Constraint

**Status:** ✅ Implemented

Added `UNIQUE(source_id, catalog_type)` constraint to prevent duplicate entries for the same source-catalog combination.

**Database Schema:**
```sql
CREATE TABLE cross_matches (
    ...
    UNIQUE(source_id, catalog_type)
)
```

**Benefits:**
- Prevents duplicate matches for the same source-catalog pair
- Ensures data integrity
- Simplifies queries (no need to handle duplicates)

**Handling:**
- Uses `INSERT OR REPLACE` in `_store_matches_in_database()`
- Updates existing entries if a new match is found
- Preserves `master_catalog_id` when updating

## Implementation Details

### Database Schema Evolution

The schema evolution automatically:
1. Creates `cross_matches` table with new columns and constraints
2. Adds `master_catalog_id` column to existing tables (backward compatible)
3. Creates index on `master_catalog_id` for efficient queries

### CrossMatchStage Workflow

1. **Query Catalogs**: Query all configured catalogs (NVSS, FIRST, RACS)
2. **Multi-Catalog Match**: Use `multi_catalog_match()` to find best matches
3. **Build Match DataFrames**: Extract per-catalog matches from multi-catalog results
4. **Calculate Metrics**: Compute offsets and flux scales per catalog
5. **Deduplicate**: Identify duplicate catalog entries using `identify_duplicate_catalog_sources()`
6. **Store Results**: Store matches in database with master catalog IDs

### Deduplication Algorithm

**Union-Find Data Structure:**
- Groups entries within deduplication radius
- Efficient O(n log n) complexity
- Handles transitive relationships (A matches B, B matches C → A, B, C grouped)

**Master ID Assignment:**
- Priority order: NVSS (0) > FIRST (1) > RACS (2)
- All entries in a group receive the same master ID
- Single entries use their own ID as master

## Usage Examples

### Query All Catalog Associations

```python
import sqlite3
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig.from_env()
products_db = config.paths.products_db

conn = sqlite3.connect(products_db)
cursor = conn.cursor()

# Find all catalog associations for a source
cursor.execute("""
    SELECT catalog_type, catalog_source_id, master_catalog_id, separation_arcsec
    FROM cross_matches
    WHERE master_catalog_id = 'nvss:J123456+012345'
    ORDER BY catalog_type
""")

for row in cursor.fetchall():
    catalog_type, catalog_id, master_id, separation = row
    print(f"{catalog_type}: {catalog_id} ({separation:.2f} arcsec)")
```

### Find Duplicate Catalog Entries

```python
# Find sources with matches in multiple catalogs
cursor.execute("""
    SELECT source_id, COUNT(DISTINCT catalog_type) as n_catalogs,
           GROUP_CONCAT(catalog_type) as catalogs
    FROM cross_matches
    GROUP BY source_id
    HAVING n_catalogs > 1
    ORDER BY n_catalogs DESC
""")
```

### Get Master Catalog Associations

```python
# Find all entries sharing the same master ID
cursor.execute("""
    SELECT catalog_type, catalog_source_id, master_catalog_id
    FROM cross_matches
    WHERE master_catalog_id IN (
        SELECT master_catalog_id
        FROM cross_matches
        GROUP BY master_catalog_id
        HAVING COUNT(*) > 1
    )
    ORDER BY master_catalog_id, catalog_type
""")
```

## Configuration

### Deduplication Radius

The deduplication radius is configurable in `CrossMatchStage.execute()`:

```python
master_catalog_ids = identify_duplicate_catalog_sources(
    catalog_matches=all_matches,
    deduplication_radius_arcsec=2.0,  # Default: 2 arcsec
)
```

**Recommendations:**
- **2 arcsec**: Default, good for most cases
- **1 arcsec**: Stricter, fewer false positives
- **5 arcsec**: More lenient, catches more duplicates but may have false positives

### Catalog Priority

Priority order is hardcoded in `identify_duplicate_catalog_sources()`:

```python
catalog_priority = {"nvss": 0, "first": 1, "rax": 2}
```

NVSS is prioritized because:
- Widest sky coverage
- Most complete catalog
- Standard reference catalog

## Testing

### Unit Tests

Tests for deduplication function:
- `tests/unit/test_crossmatch.py` - Basic functionality
- Tests for `identify_duplicate_catalog_sources()`

### Integration Tests

Tests for `CrossMatchStage`:
- `tests/integration/test_crossmatch_stage.py`
- Tests multi-catalog matching
- Tests database storage with master IDs

## Migration Notes

### Existing Databases

The schema evolution automatically:
1. Adds `master_catalog_id` column to existing `cross_matches` table
2. Adds UNIQUE constraint (may fail if duplicates exist - clean up first)
3. Creates index on `master_catalog_id`

### Data Migration

For existing cross-match data:
1. Run schema evolution to add `master_catalog_id` column
2. Re-run cross-matching to populate master IDs
3. Or manually populate master IDs based on position matching

## Future Enhancements

Potential improvements:
1. **Configurable catalog priority**: Allow users to set priority order
2. **Fuzzy matching**: Use flux information to improve duplicate detection
3. **Cross-match history**: Track how master IDs change over time
4. **Visualization**: Tools to visualize duplicate relationships
5. **API endpoints**: REST API for querying master catalog associations

## Related Documentation

- `docs/how-to/cross-matching-guide.md` - User guide
- `docs/dev/CROSS_MATCHING_IMPLEMENTATION.md` - Implementation details
- `docs/reference/CATALOG_CROSS_MATCHING_GUIDE.md` - Cross-matching strategies

