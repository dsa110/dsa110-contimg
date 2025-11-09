# Data Product Organization Design

**Status:** Design Proposal (Not Current Implementation)

**Note:** This document describes a proposed organizational structure. The **current implementation** uses a different structure documented in `docs/concepts/DIRECTORY_ARCHITECTURE.md` and `docs/concepts/STREAMING_MOSAIC_WORKFLOW.md`.

**Current Implementation:**
- MS files organized as: `/stage/dsa110-contimg/ms/{calibrators,science,failed}/YYYY-MM-DD/`
- Images stored in: `/stage/dsa110-contimg/images/`
- Mosaics stored in: `/stage/dsa110-contimg/mosaics/`
- See `DIRECTORY_ARCHITECTURE.md` for the actual structure in use.

---

## Overview

This document defines a proposed organizational structure for DSA-110 pipeline data products, from staging through final published data.

## 1. Directory Structure and Labeling

### Storage Hierarchy

```
/scratch/                    # Playground for testing/development (manual use only)
└── [unstructured testing]   # NOT used by automated pipeline

/stage/                      # Tier 1: Staging (All Pipeline Outputs)
└── dsa110-contimg/
    ├── ms/                  # Raw/converted MS files
    ├── calib_ms/            # Calibrated MS files
    ├── caltables/           # Calibration tables
    ├── images/              # Single-epoch images
    ├── mosaics/             # Multi-epoch mosaics
    ├── catalogs/            # Source catalogs
    ├── qa/                  # Quality assessment reports
    │   ├── cal_qa/         # Calibration QA
    │   ├── ms_qa/          # MS QA
    │   └── image_qa/       # Image QA
    └── metadata/            # Pipeline metadata
        ├── pipe_meta/      # Pipeline run metadata
        ├── cal_meta/       # Calibration metadata
        ├── ms_meta/        # MS metadata
        ├── catalog_meta/  # Catalog metadata
        ├── image_meta/     # Image metadata
        └── mosaic_meta/    # Mosaic metadata

/data/dsa110-contimg/        # Tier 2: Published Data (Final, Immutable)
└── products/
    ├── ms/                  # Published MS files
    ├── calib_ms/           # Published calibrated MS
    ├── caltables/          # Published calibration solutions
    ├── images/             # Published images
    ├── mosaics/            # Published mosaics
    ├── catalogs/           # Published source catalogs
    ├── qa/                 # Published QA reports
    │   ├── cal_qa/
    │   ├── ms_qa/
    │   └── image_qa/
    └── metadata/           # Published metadata
        ├── pipe_meta/
        ├── cal_meta/
        ├── ms_meta/
        ├── catalog_meta/
        ├── image_meta/
        └── mosaic_meta/
```

### Data Types and Definitions

#### 1. **MS Files** (`ms/`)
- **Definition**: Raw/converted measurement sets
- **Staging**: `/stage/dsa110-contimg/ms/{timestamp}/`
  - Contains: `.ms` directory, conversion metadata
- **Published**: `/data/dsa110-contimg/products/ms/{timestamp}/`
  - Validated MS files ready for calibration

#### 2. **Calibrated MS** (`calib_ms/`)
- **Definition**: Final calibrated measurement sets ready for science
- **Staging**: `/stage/dsa110-contimg/calib_ms/{timestamp}/`
  - Contains: `.cal.ms` directory, calibration metadata
- **Published**: `/data/dsa110-contimg/products/calib_ms/{timestamp}/`
  - Validated, documented calibrated MS

#### 3. **Calibration Tables** (`caltables/`)
- **Definition**: Final calibration solutions (K, BP, G tables)
- **Staging**: `/stage/dsa110-contimg/caltables/{set_name}/`
  - Contains: K, BP, G tables, validation report
- **Published**: `/data/dsa110-contimg/products/caltables/{set_name}/`
  - Validated calibration sets with validity windows

#### 4. **Images** (`images/`)
- **Definition**: Single-epoch continuum images
- **Staging**: `/stage/dsa110-contimg/images/{timestamp}/`
  - Contains: image FITS, beam FITS, residual FITS, image metadata
- **Published**: `/data/dsa110-contimg/products/images/{timestamp}/`
  - Validated, QA-passed images

#### 5. **Mosaics** (`mosaics/`)
- **Definition**: Combined images from multiple time integrations
- **Staging**: `/stage/dsa110-contimg/mosaics/{name}/`
  - Contains: mosaic FITS, thumbnail, mosaic metadata, QA report
- **Published**: `/data/dsa110-contimg/products/mosaics/{name}/`
  - Same structure, but validated and immutable

#### 6. **Source Catalogs** (`catalogs/`)
- **Definition**: Extracted source lists from images
- **Staging**: `/stage/dsa110-contimg/catalogs/{timestamp}/`
  - Contains: catalog CSV/VOTable, cross-match results, catalog metadata
- **Published**: `/data/dsa110-contimg/products/catalogs/{timestamp}/`
  - Validated source catalogs

#### 7. **QA Reports** (`qa/`)
- **Definition**: Quality assessment reports organized by data type
- **Subdirectories**:
  - `cal_qa/`: Calibration quality assessments
  - `ms_qa/`: MS quality assessments
  - `image_qa/`: Image quality assessments
- **Staging**: `/stage/dsa110-contimg/qa/{type}/{id}/`
  - Contains: QA JSON, plots, validation results
- **Published**: `/data/dsa110-contimg/products/qa/{type}/{id}/`
  - Final QA documentation

#### 8. **Metadata** (`metadata/`)
- **Definition**: Pipeline run metadata and provenance organized by data type
- **Subdirectories**:
  - `pipe_meta/`: Pipeline run metadata
  - `cal_meta/`: Calibration metadata
  - `ms_meta/`: MS metadata
  - `catalog_meta/`: Catalog metadata
  - `image_meta/`: Image metadata
  - `mosaic_meta/`: Mosaic metadata
- **Staging**: `/stage/dsa110-contimg/metadata/{type}/{id}/`
  - Contains: metadata JSON, configs, logs, provenance
- **Published**: `/data/dsa110-contimg/products/metadata/{type}/{id}/`
  - Finalized metadata for reproducibility

### Status Lifecycle

```
staging → published (auto or manual)
   ↓              ↓
/stage (SSD)   /data/dsa110-contimg/products (HDD)
```

**Status Values:**
- `staging`: In `/stage/dsa110-contimg/` (SSD), being finalized/validated
- `published`: In `/data/dsa110-contimg/products/` (HDD), final and immutable

**Storage Rationale:**
- `/stage/` (SSD): Fast access for active processing, QA, validation
- `/data/` (HDD): Long-term storage with large capacity for archival

**Publishing Modes:**
- **Auto-publish**: Automatically moves to `/data/` when finalization criteria are met
- **Manual publish**: User-initiated move to `/data/` via dashboard

**Note**: `/scratch/` is NOT part of the automated pipeline workflow. It is reserved for manual testing and development work only.

## 2. Database and Registry Integration

### Data Registry Database Schema

```sql
-- Data registry (tracks all data instances regardless of status)
CREATE TABLE IF NOT EXISTS data_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT NOT NULL,  -- 'ms', 'calib_ms', 'caltable', 'image', 'mosaic', 'catalog', 'qa', 'metadata'
    data_id TEXT NOT NULL UNIQUE,  -- Unique identifier (e.g., mosaic name, timestamp)
    base_path TEXT NOT NULL,  -- Base directory path
    status TEXT NOT NULL DEFAULT 'staging',  -- 'staging', 'published'
    stage_path TEXT NOT NULL,  -- Path in /stage/dsa110-contimg/ (SSD)
    published_path TEXT,  -- Path in /data/dsa110-contimg/products/ if published (HDD)
    created_at REAL NOT NULL,
    staged_at REAL NOT NULL,  -- When created in staging
    published_at REAL,  -- When published (NULL if not published)
    publish_mode TEXT,  -- 'auto', 'manual', NULL if not published
    metadata_json TEXT,  -- JSON blob with data-specific metadata
    qa_status TEXT,  -- 'pending', 'passed', 'failed', 'warning'
    validation_status TEXT,  -- 'pending', 'validated', 'invalid'
    finalization_status TEXT DEFAULT 'pending',  -- 'pending', 'finalized', 'failed'
    auto_publish_enabled INTEGER DEFAULT 1,  -- 1 = enabled, 0 = disabled (manual only)
    UNIQUE(data_type, data_id)
);

-- Data relationships (e.g., mosaic contains images, image derived from MS)
CREATE TABLE IF NOT EXISTS data_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_data_id TEXT NOT NULL,
    child_data_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,  -- 'contains', 'derived_from', 'uses', 'calibrated_with'
    FOREIGN KEY (parent_data_id) REFERENCES data_registry(data_id),
    FOREIGN KEY (child_data_id) REFERENCES data_registry(data_id),
    UNIQUE(parent_data_id, child_data_id, relationship_type)
);

-- Data tags (for organization/search)
CREATE TABLE IF NOT EXISTS data_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (data_id) REFERENCES data_registry(data_id),
    UNIQUE(data_id, tag)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_data_registry_type_status ON data_registry(data_type, status);
CREATE INDEX IF NOT EXISTS idx_data_registry_status ON data_registry(status);
CREATE INDEX IF NOT EXISTS idx_data_registry_published_at ON data_registry(published_at);
CREATE INDEX IF NOT EXISTS idx_data_relationships_parent ON data_relationships(parent_data_id);
CREATE INDEX IF NOT EXISTS idx_data_relationships_child ON data_relationships(child_data_id);
```

### Integration with Existing Tables

The data registry **references** (via foreign key relationships) existing tables that contain detailed information about each data type:

1. **MS Files** (`ms_index` table)
   - Contains: All MS file instances with detailed metadata
   - Relationship: `data_registry.data_id` references `ms_index.path`
   - Tracks: Which MS files have been used to create images/mosaics

2. **Calibration Tables** (`caltables` table)
   - Contains: All calibration table instances with validity windows
   - Relationship: `data_registry.data_id` references `caltables.set_name` or `caltables.table_id`
   - Tracks: Which calibration sets are used by calibrated MS

3. **Images** (`images` table)
   - Contains: All image instances with detailed metadata
   - Relationship: `data_registry.data_id` references `images.path` or `images.id`
   - Tracks: Image status through lifecycle
   - **Note**: Table name kept as `images` (not renamed to `images_all`) for consistency with codebase

4. **Mosaics** (`mosaics` table)
   - Contains: All mosaic instances with composition details
   - Relationship: `data_registry.data_id` references `mosaics.name` or `mosaics.id`
   - Tracks: Mosaic composition (which images are included)
   - **Note**: Table name kept as `mosaics` (not renamed to `mosaics_all`) for consistency with codebase

**Note on "Links"**: When we say "links" or "references", we mean:
- Foreign key relationships in the database
- The `data_registry` table acts as a central index that references detailed tables
- The `data_relationships` table tracks how data instances relate to each other
- This allows querying "what MS files produced this image?" or "what images are in this mosaic?"

### API Functions

```python
# Data lifecycle management
def register_data(data_type: str, data_id: str, stage_path: str, metadata: dict, auto_publish: bool = True) -> str
def finalize_data(data_id: str) -> bool  # Marks data as finalized, triggers auto-publish if enabled
def publish_data(data_id: str, published_path: str, mode: str = 'manual') -> bool  # mode: 'auto' or 'manual'
def get_data(data_id: str) -> DataRecord
def list_data(data_type: Optional[str] = None, status: Optional[str] = None) -> List[DataRecord]

# Auto-publish configuration
def enable_auto_publish(data_id: str) -> bool
def disable_auto_publish(data_id: str) -> bool
def check_auto_publish_criteria(data_id: str) -> Dict[str, bool]  # Returns criteria status

# Data relationships
def link_data(parent_id: str, child_id: str, relationship_type: str) -> bool
def get_data_lineage(data_id: str) -> Dict[str, List[str]]

# Data discovery
def discover_staging_data() -> List[DataRecord]
def discover_published_data() -> List[DataRecord]

# Auto-publish trigger (called when data is finalized)
def trigger_auto_publish(data_id: str) -> bool
```

## 3. Dashboard Integration

### Data Management Views

#### 1. **Data Browser** (`/data`)
- **Overview**: List all data organized by type and status
- **Key Features**:
  - **Quick Filters**:
    - Data type (ms, calib_ms, image, mosaic, catalog, etc.)
    - Status (staging, published)
    - Date range (created, published)
    - QA status (pending, passed, failed, warning)
    - Validation status
  - **View Options**:
    - Table view (compact, sortable columns)
    - Card view (visual, with thumbnails for images/mosaics)
    - Timeline view (chronological)
  - **Actions**:
    - View data details
    - Publish data manually (move to published)
    - Download data
    - View QA report
    - View lineage
    - Enable/disable auto-publish
    - Bulk operations (select multiple, bulk publish)
  - **Auto-Publish Indicators**:
    - Visual indicator if auto-publish is enabled
    - Show auto-publish criteria status
    - Show if data is pending auto-publish
  - **User Workflows**:
    - "Show me all images from last week"
    - "Show me all staging mosaics ready to publish"
    - "Show me all data that failed QA"

#### 2. **Staging Area** (`/data/staging`)
- **Overview**: Data being finalized, ready for review
- **Key Features**:
  - **Organized by Type**: Tabs or sections for each data type
  - **Status Indicators**: Visual badges for QA status, validation status
  - **Quick Actions**:
    - "Publish Selected" button (bulk manual publish)
    - "View QA" button (opens QA report)
    - "View Details" button
    - "Finalize Selected" button (marks as finalized, triggers auto-publish)
    - Auto-publish status indicator (enabled/disabled, criteria status)
  - **Filters**:
    - By QA status (show only passed, show warnings, etc.)
    - By validation status
    - By date
  - **User Workflows**:
    - "Review all new images from today"
    - "Publish all validated mosaics"
    - "Check what's blocking publication"

#### 3. **Published Data** (`/data/published`)
- **Overview**: Final, validated, immutable data
- **Key Features**:
  - **Browse by Type**: Organized sections/tabs
  - **Search**: Full-text search across metadata
  - **Advanced Filters**:
    - Date range
    - Data type
    - Tags
    - Related data (e.g., "show images from this MS")
  - **Lineage Visualization**: 
    - Tree view showing data relationships
    - "What produced this?" and "What was produced from this?"
  - **Download Options**:
    - Individual files
    - Entire data package
    - Metadata only
  - **User Workflows**:
    - "Find all mosaics from October"
    - "Download all images for a specific MS"
    - "See what data was used to create this mosaic"

#### 4. **Data Details** (`/data/{type}/{id}`)
- **Overview**: Comprehensive view of a single data instance
- **Sections**:
  - **Header**:
    - Data ID, type, status
    - Quick actions (download, publish if staging, finalize)
    - Status badges (QA, validation, finalization, auto-publish)
    - Auto-publish indicator (enabled/disabled, criteria status)
  - **Metadata Tab**:
    - All metadata fields (organized, searchable)
    - Creation/publish dates
    - File listing with sizes
  - **QA Tab**:
    - QA report (if available)
    - QA plots/visualizations
    - Validation results
  - **Lineage Tab**:
    - **Derived From**: What data was used to create this
      - For images: source MS files
      - For mosaics: component images
      - For calibrated MS: source MS + calibration tables
    - **Produces**: What data was created from this
      - For MS: images, mosaics
      - For images: mosaics, catalogs
    - Visual graph/tree representation
  - **Related Data Tab**:
    - Other data instances related to this one
    - Same MS, same time range, etc.
  - **Files Tab**:
    - Complete file listing
    - Download individual files
    - File sizes and checksums
  - **User Workflows**:
    - "I want to see what MS files created this image"
    - "I want to download all files for this mosaic"
    - "I want to see the QA report for this data"

### API Endpoints

```python
# Data listing
GET /api/data
  Query params: type, status, qa_status, validation_status, date_from, date_to, tag
  Returns: DataList

# Data details
GET /api/data/{data_id}
  Returns: DataDetail

# Data lifecycle
POST /api/data/{data_id}/finalize
  Marks data as finalized, triggers auto-publish if enabled
  Returns: {finalized: bool, auto_published: bool}

POST /api/data/{data_id}/publish
  Body: {published_path: str, mode: 'manual'}
  Manually publishes data (moves from staging to published)

# Auto-publish configuration
POST /api/data/{data_id}/auto-publish/enable
  Enables auto-publish for this data instance

POST /api/data/{data_id}/auto-publish/disable
  Disables auto-publish for this data instance

GET /api/data/{data_id}/auto-publish/status
  Returns: {enabled: bool, criteria_met: bool, criteria_details: dict}

# Data relationships
GET /api/data/{data_id}/lineage
  Returns: DataLineage (parents and children)

# Data discovery
POST /api/data/discover
  Discovers new data in staging/published directories

# Bulk operations
POST /api/data/bulk-publish
  Body: {data_ids: List[str]}
  Bulk publish multiple data instances
```

### Frontend Components

1. **DataTable** - Lists data with filters, sorting, bulk selection
2. **DataCard** - Card view for data (with thumbnails for images/mosaics)
3. **DataDetail** - Comprehensive data detail view with tabs
4. **StagingPanel** - Staging area management with quick actions
5. **DataLineage** - Visualize data relationships (tree/graph view)
6. **DataActions** - Actions menu (publish, download, view QA, etc.)
7. **DataFilters** - Advanced filtering component
8. **DataTimeline** - Chronological view of data creation
9. **BulkActionsBar** - Appears when items selected, shows bulk actions
10. **QAStatusBadge** - Visual indicator for QA status
11. **ValidationStatusBadge** - Visual indicator for validation status

### Workflow Integration

1. **Pipeline Output**:
   - Pipeline creates data in `/stage/dsa110-contimg/` (SSD)
   - Data automatically registered in database with `status='staging'`
   - `auto_publish_enabled=1` by default (configurable)
   - Dashboard shows new data in staging area
   - QA/validation runs automatically (or triggered)

2. **Finalization and Auto-Publish**:
   - When data is finalized (QA passed, validation complete):
     - `finalization_status` set to `'finalized'`
     - If `auto_publish_enabled=1` and all criteria met:
       - Data automatically moved from `/stage/` (SSD) to `/data/dsa110-contimg/products/` (HDD)
       - Database updated: `status='published'`, `publish_mode='auto'`, `published_at` set
       - Data becomes immutable (read-only)
       - Dashboard shows in published view
   - Auto-publish criteria (configurable per data type):
     - QA status = 'passed'
     - Validation status = 'validated'
     - All required metadata present
     - No blocking issues

3. **Manual Publishing**:
   - User can manually publish data via dashboard
   - User selects data and clicks "Publish" (single or bulk)
   - Data moved to `/data/dsa110-contimg/products/` (HDD)
   - Database updated: `status='published'`, `publish_mode='manual'`, `published_at` set
   - Works even if auto-publish is disabled or criteria not met

4. **Auto-Publish Configuration**:
   - Per-data-type configuration for auto-publish criteria
   - Users can disable auto-publish for specific data instances
   - Dashboard shows auto-publish status and criteria

## Implementation Plan

### Phase 1: Database Schema
- [ ] Add `data_registry` table to database
- [ ] Add `data_relationships` table
- [ ] Add `data_tags` table
- [ ] Rename existing tables (`ms_index` → `ms_all`, `images` → `images_all`, etc.)
- [ ] Create migration script
- [ ] Update foreign key relationships

### Phase 2: Directory Structure
- [ ] Create directory structure in `/stage/dsa110-contimg/`
  - [ ] `ms/`, `calib_ms/`, `caltables/`, `images/`, `mosaics/`, `catalogs/`
  - [ ] `qa/` with subdirs: `cal_qa/`, `ms_qa/`, `image_qa/`
  - [ ] `metadata/` with subdirs: `pipe_meta/`, `cal_meta/`, `ms_meta/`, `catalog_meta/`, `image_meta/`, `mosaic_meta/`
- [ ] Create directory structure in `/data/dsa110-contimg/products/` (same structure)
- [ ] Add configuration for base paths
- [ ] Update pipeline to write to `/stage/` instead of `/scratch/`

### Phase 3: Data Management Functions
- [ ] Implement data registration functions
- [ ] Implement finalization function (marks data as finalized)
- [ ] Implement auto-publish logic (checks criteria, moves data)
- [ ] Implement manual publish function
- [ ] Implement auto-publish configuration (enable/disable per instance)
- [ ] Implement data discovery
- [ ] Implement relationship tracking
- [ ] Update existing functions to use new table names

### Phase 4: API Integration
- [ ] Add data endpoints to API (`/api/data/*`)
- [ ] Integrate with existing endpoints (update to use new table names)
- [ ] Add data discovery endpoint
- [ ] Add bulk operations endpoint

### Phase 5: Dashboard Integration
- [ ] Create data browser page (`/data`)
- [ ] Create staging area page (`/data/staging`)
- [ ] Create published data page (`/data/published`)
- [ ] Create data detail page (`/data/{type}/{id}`)
- [ ] Add data actions to existing views
- [ ] Implement lineage visualization

### Phase 6: Pipeline Integration
- [ ] Update pipeline to write to `/stage/dsa110-contimg/` (SSD)
- [ ] Update pipeline to register data in `data_registry`
- [ ] Update pipeline to track relationships
- [ ] Update pipeline to call `finalize_data()` when data is complete
- [ ] Integrate auto-publish trigger into pipeline completion workflow
- [ ] Add automatic data discovery
- [ ] Remove all `/scratch/` usage from automated pipeline
- [ ] Add monitoring/logging for auto-publish operations

## Configuration

Add to `config.py` or environment:

```python
# Base paths
STAGE_BASE = Path("/stage/dsa110-contimg")  # SSD - fast access for active work
PRODUCTS_BASE = Path("/data/dsa110-contimg/products")  # HDD - long-term storage

# Auto-publish configuration
AUTO_PUBLISH_ENABLED_BY_DEFAULT = True
AUTO_PUBLISH_DELAY_SECONDS = 0  # Delay before auto-publish (0 = immediate)

# Data type configurations
DATA_TYPES = {
    "ms": {
        "staging_dir": STAGE_BASE / "ms",
        "published_dir": PRODUCTS_BASE / "ms",
        "auto_publish_criteria": {
            "qa_required": False,  # MS files don't need QA
            "validation_required": True,
        },
    },
    "calib_ms": {
        "staging_dir": STAGE_BASE / "calib_ms",
        "published_dir": PRODUCTS_BASE / "calib_ms",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "caltable": {
        "staging_dir": STAGE_BASE / "caltables",
        "published_dir": PRODUCTS_BASE / "caltables",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "image": {
        "staging_dir": STAGE_BASE / "images",
        "published_dir": PRODUCTS_BASE / "images",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "mosaic": {
        "staging_dir": STAGE_BASE / "mosaics",
        "published_dir": PRODUCTS_BASE / "mosaics",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "catalog": {
        "staging_dir": STAGE_BASE / "catalogs",
        "published_dir": PRODUCTS_BASE / "catalogs",
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": True,
        },
    },
    "qa": {
        "staging_dir": STAGE_BASE / "qa",
        "published_dir": PRODUCTS_BASE / "qa",
        "subdirs": ["cal_qa", "ms_qa", "image_qa"],
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": False,  # QA reports auto-publish with their data
        },
    },
    "metadata": {
        "staging_dir": STAGE_BASE / "metadata",
        "published_dir": PRODUCTS_BASE / "metadata",
        "subdirs": ["pipe_meta", "cal_meta", "ms_meta", "catalog_meta", "image_meta", "mosaic_meta"],
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": False,  # Metadata auto-publishes with its data
        },
    },
}
```

**Note**: `/scratch/` is NOT configured here as it is not part of the automated pipeline workflow.

**Auto-Publish Behavior**:
- When data is finalized and all criteria are met, it automatically moves from SSD (`/stage/`) to HDD (`/data/`)
- This provides fast access during active work (SSD) and long-term storage (HDD)
- Users can disable auto-publish for specific data instances if manual control is needed
- Manual publish always available regardless of auto-publish settings

**Auto-Publish Trigger Logic**:
1. Pipeline completes data creation → data registered in `data_registry` with `status='staging'`
2. QA/validation runs → updates `qa_status` and `validation_status`
3. When QA/validation complete → pipeline calls `finalize_data(data_id)`
4. `finalize_data()` checks:
   - Is `auto_publish_enabled=1`?
   - Are all auto-publish criteria met (per data type config)?
   - If yes → calls `trigger_auto_publish(data_id)`
5. `trigger_auto_publish()`:
   - Moves data from `/stage/` (SSD) to `/data/dsa110-contimg/products/` (HDD)
   - Updates database: `status='published'`, `publish_mode='auto'`, `published_at=now()`
   - Sets data as immutable
   - Logs the operation

**Auto-Publish Criteria (per data type)**:
- **Science data** (images, mosaics, calib_ms, caltables): Requires QA passed + validation
- **Diagnostic data** (qa reports, metadata): Auto-publishes with parent data or immediately
- **Raw data** (ms): Requires validation only (no QA needed)
- **Catalogs**: Requires validation only

**Benefits**:
- Automatic archival: Finalized data automatically moves to long-term storage
- SSD space management: Keeps SSD free for active work
- No manual intervention: Science products auto-archive when ready
- Flexibility: Can disable per-instance if needed

