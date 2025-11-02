# Architectural Compatibility Analysis: Service Layer Proposal

## Analysis Date: 2025-01-XX

## Executive Summary

**The proposed service architecture is a natural evolution, not a disruption.** It aligns with existing architectural patterns and would primarily involve **organizing and extending** current functionality rather than replacing it. The codebase already demonstrates the foundational patterns needed for services.

---

## Current Architectural Characteristics

### 1. **Database Helper Pattern** (Already Established)

**Pattern**: Functional helpers that manage database connections and operations

**Examples**:
- `database/products.py::ensure_products_db()` - Returns connection, ensures schema
- `database/registry.py::ensure_db()` - Returns connection, ensures schema  
- `database/registry.py::get_active_applylist()` - Query function with database access
- `database/products.py::ms_index_upsert()` - Database operation helper

**Characteristics**:
- Functions return database connections or results
- Schema management handled internally
- No class-based services (functional pattern)
- Database operations abstracted behind helper functions

**Service Alignment**: ✓ **Perfect match**
- Proposed services would use the same pattern
- Would call existing `ensure_*()` functions
- Would extend existing query functions
- No architectural change required

### 2. **Modular Organization** (Clear Domain Separation)

**Structure**:
```
src/dsa110_contimg/
├── conversion/      # Conversion logic
├── calibration/    # Calibration logic
├── imaging/        # Imaging logic
├── database/       # Database helpers
├── api/            # API layer
├── qa/             # Quality assurance
└── utils/          # Shared utilities
```

**Characteristics**:
- Clear separation by domain/functionality
- Each module has focused responsibility
- Modules import from each other (loose coupling)
- Database layer already exists as separate module

**Service Alignment**: ✓ **Perfect match**
- Services would fit into existing module structure
- `database/` module already exists for database services
- Could add `services/` submodule or integrate into existing modules
- No structural disruption

### 3. **CLI + Library Pattern** (Dual Interface)

**Pattern**: Modules provide both CLI (`cli.py`) and library functions

**Examples**:
- `calibration/cli.py` + `calibration/calibration.py` (functions)
- `imaging/cli.py` + `imaging/cli.py::image_ms()` (function)
- `mosaic/cli.py` (CLI) + could add library functions

**Characteristics**:
- CLI scripts call library functions
- Library functions are reusable
- Functions can be imported and used programmatically
- Some modules already have service-like organization

**Service Alignment**: ✓ **Perfect match**
- Services would be library functions (existing pattern)
- CLI scripts would call service functions
- No change to CLI/library separation
- Enhances reusability (already a goal)

### 4. **Database-Driven Architecture** (Already Established)

**Current State**:
- SQLite databases: `products.sqlite3`, `cal_registry.sqlite3`, `ingest.sqlite3`
- Database helpers abstract connection management
- Query functions return structured data
- Schema migration support exists

**Examples**:
- `ingest_queue` table tracks file groups
- `ms_index` table tracks Measurement Sets
- `caltables` table tracks calibration tables
- Database queries replace file system scanning in some places

**Service Alignment**: ✓ **Perfect match**
- Services would use existing databases
- Would extend existing tables/schemas
- Database-driven approach already preferred
- Would reduce file system scanning (already a goal)

### 5. **Functional (Not Class-Based) Pattern**

**Current State**:
- Codebase uses functional programming patterns
- Very few classes (only `AlertManager` and `GraphitiRunLogger` found)
- Helper functions, not service classes
- Context managers for resource management

**Service Alignment**: ✓ **Perfect match**
- Services would be organized functions, not classes
- Would follow existing functional pattern
- Could use dataclasses for return types (already used: `CalTableRow`)
- No OOP paradigm shift required

---

## Proposed Services: Natural Evolution

### How Services Fit Current Architecture

#### 1. **TransitDataMatcher Service**

**Current State**:
- Transit calculation: `calibration/schedule.py::previous_transits()` ✓ exists
- Pointing extraction: `conversion/strategies/hdf5_orchestrator.py::_peek_uvh5_phase_and_midtime()` ✓ exists
- Data availability: `database/products.py` (ingest queue) ✓ exists
- Catalog lookup: `calibration/catalogs.py::get_calibrator_radec()` ✓ exists

**Service Implementation**:
```python
# Would be: src/dsa110_contimg/services/transit_matcher.py
# OR: src/dsa110_contimg/calibration/transit_matcher.py

def find_transits_with_data(
    source_name: str,
    catalogs: List[str],
    pointing_db: Path,
    ingest_db: Path,
    *,
    start_time: Optional[Time] = None,
    end_time: Optional[Time] = None,
    n_transits: int = 10
) -> List[TransitMatch]:
    """Uses existing functions: previous_transits(), get_calibrator_radec(), 
    database queries for pointing/data availability."""
```

**Architectural Impact**: ✓ **Zero disruption**
- Calls existing functions
- Uses existing databases
- Functional pattern (matches codebase)
- Could live in `calibration/` or new `services/` module

#### 2. **SubbandGroupDiscovery Service**

**Current State**:
- File scanning: `hdf5_orchestrator.find_subband_groups()` ✓ exists
- Database tracking: `ingest_queue` table ✓ exists
- Group assembly logic: Multiple implementations ✓ exist

**Service Implementation**:
```python
# Would be: src/dsa110_contimg/services/group_discovery.py
# OR: src/dsa110_contimg/conversion/group_discovery.py

def scan_directory_and_update_db(
    input_dir: Path,
    ingest_db: Path,
    *,
    force_refresh: bool = False
) -> int:
    """Uses existing: find_subband_groups() logic, ingest_queue table."""
    
def find_groups_in_window(
    ingest_db: Path,
    start_time: Time,
    end_time: Time,
    *,
    tolerance_s: float = 30.0
) -> List[SubbandGroup]:
    """Queries ingest_queue table (database-driven, not file scanning)."""
```

**Architectural Impact**: ✓ **Minimal disruption**
- Extends existing `find_subband_groups()` logic
- Moves to database-backed queries (reduces file scanning)
- Could enhance `ingest_queue` schema if needed
- Follows existing database helper pattern

#### 3. **UnifiedConverter Service**

**Current State**:
- Conversion orchestrator: `hdf5_orchestrator.convert_subband_groups_to_ms()` ✓ exists
- Writer selection: Auto/manual selection logic ✓ exists
- Staging strategy: tmpfs/SSD logic ✓ exists

**Service Implementation**:
```python
# Would be: src/dsa110_contimg/conversion/converter.py
# OR: Enhance existing hdf5_orchestrator.py

def convert_group(
    file_list: List[Path],
    output_ms: Path,
    *,
    writer: str = "auto",
    stage_to_tmpfs: Optional[bool] = None
) -> Path:
    """Wraps existing: convert_subband_groups_to_ms() with consistent interface."""
```

**Architectural Impact**: ✓ **Zero disruption**
- Wraps existing conversion logic
- Provides consistent interface
- Scripts already import from `conversion/` module
- No changes to core conversion logic

#### 4. **CalibrationApplicationService**

**Current State**:
- Apply function: `calibration/applycal.py::apply_to_target()` ✓ exists
- Registry lookup: `database/registry.py::get_active_applylist()` ✓ exists
- Verification: Logic exists in multiple scripts

**Service Implementation**:
```python
# Would be: src/dsa110_contimg/calibration/apply_service.py
# OR: Enhance existing calibration/applycal.py

def apply_calibration_to_ms(
    ms_path: Path,
    registry_db: Path,
    *,
    set_name: Optional[str] = None,
    verify: bool = True
) -> bool:
    """Uses existing: get_active_applylist(), apply_to_target(), verification logic."""
```

**Architectural Impact**: ✓ **Zero disruption**
- Calls existing functions
- Organizes existing logic
- Uses existing database
- Functional pattern

#### 5. **ImagingService**

**Current State**:
- Core function: `imaging/cli.py::image_ms()` ✓ exists
- Parameter handling: Already functional
- Product registration: `database/products.py::images_insert()` ✓ exists

**Service Implementation**:
```python
# Would be: src/dsa110_contimg/imaging/service.py
# OR: Enhance existing imaging/cli.py

def image_ms_with_preset(
    ms_path: Path,
    output_dir: Path,
    *,
    preset: str = "quick"
) -> List[Path]:
    """Calls existing: image_ms() with preset parameters, images_insert()."""
```

**Architectural Impact**: ✓ **Zero disruption**
- Wraps existing `image_ms()` function
- Adds preset configuration (new feature)
- Uses existing product registration
- No changes to core imaging logic

#### 6. **MosaicService**

**Current State**:
- Planning: `mosaic/cli.py::cmd_plan()` ✓ exists
- Building: `mosaic/cli.py::cmd_build()` ✓ exists
- Database queries: `mosaic/cli.py::_fetch_tiles()` ✓ exists

**Service Implementation**:
```python
# Would be: src/dsa110_contimg/mosaic/service.py
# OR: Enhance existing mosaic/cli.py

def plan_mosaic(
    products_db: Path,
    name: str,
    *,
    since: Optional[float] = None,
    until: Optional[float] = None
) -> str:
    """Calls existing: _fetch_tiles(), creates mosaic plan."""
    
def build_mosaic(
    products_db: Path,
    name: str,
    output_path: Path
) -> Path:
    """Calls existing: cmd_build() logic (extract from CLI)."""
```

**Architectural Impact**: ✓ **Minimal disruption**
- Extracts CLI logic to library functions
- Adds Python API (currently CLI-only)
- Uses existing database queries
- Follows CLI + library pattern

---

## Migration Impact Assessment

### What Changes?

1. **New Module Organization** (Optional)
   - Could add `src/dsa110_contimg/services/` submodule
   - OR: Integrate services into existing modules
   - **Impact**: Low - organizational only

2. **Enhanced Database Usage**
   - More queries, less file scanning
   - Could enhance schemas (additive only)
   - **Impact**: Low - extends existing pattern

3. **Script Refactoring**
   - Replace duplicate code with service calls
   - Maintain backward compatibility during transition
   - **Impact**: Medium - gradual migration possible

### What Doesn't Change?

1. **Core Processing Logic**
   - Conversion algorithms unchanged
   - Calibration algorithms unchanged
   - Imaging algorithms unchanged
   - **Impact**: Zero - services wrap existing logic

2. **Database Schema**
   - No breaking changes
   - Additive enhancements only
   - **Impact**: Zero - backward compatible

3. **CLI Interfaces**
   - Existing CLIs continue to work
   - Services add Python API layer
   - **Impact**: Zero - additive only

4. **Module Structure**
   - Same domain separation
   - Same import patterns
   - **Impact**: Zero - organizational only

5. **Architectural Patterns**
   - Functional programming (not OOP)
   - Database helpers
   - CLI + library pattern
   - **Impact**: Zero - matches existing patterns

---

## Natural Evolution Characteristics

### 1. **Building on Existing Foundations**

**Current State**:
- Database helpers exist
- Query functions exist
- Core processing functions exist
- Module organization exists

**Service Layer**:
- Organizes existing functions
- Adds consistent interfaces
- Reduces duplication
- Enhances reusability

**Conclusion**: ✓ **Natural extension**, not replacement

### 2. **Following Established Patterns**

**Current Patterns**:
- Functional helpers (`ensure_*()`, `get_*()`, `*_upsert()`)
- Database-driven queries
- Module-based organization
- CLI + library interfaces

**Service Layer**:
- Same functional pattern
- Same database usage
- Same module structure
- Same dual interface

**Conclusion**: ✓ **Follows existing patterns**, not introducing new ones

### 3. **Additive Enhancement**

**Current State**:
- Scripts work independently
- Functions work independently
- Databases work independently

**Service Layer**:
- Adds coordination layer
- Doesn't break existing code
- Can be adopted gradually
- Backward compatible

**Conclusion**: ✓ **Additive only**, no breaking changes

### 4. **Addressing Existing Pain Points**

**Current Pain Points**:
- Code duplication across scripts
- Repeated file system scanning
- Inconsistent interfaces
- Hardcoded workflows

**Service Layer**:
- Eliminates duplication
- Database-driven (less scanning)
- Consistent interfaces
- Flexible workflows

**Conclusion**: ✓ **Solves existing problems**, not creating new ones

---

## Compatibility Matrix

| Architectural Aspect | Current State | Service Layer | Compatibility |
|---------------------|---------------|---------------|---------------|
| **Programming Paradigm** | Functional | Functional | ✅ Perfect match |
| **Database Pattern** | Helper functions | Helper functions | ✅ Perfect match |
| **Module Organization** | Domain-based | Domain-based | ✅ Perfect match |
| **CLI + Library** | Both exist | Both exist | ✅ Perfect match |
| **Database-Driven** | SQLite heavy | SQLite heavy | ✅ Perfect match |
| **Class Usage** | Minimal (2 classes) | Minimal (0 classes) | ✅ Perfect match |
| **Import Patterns** | Module imports | Module imports | ✅ Perfect match |
| **Error Handling** | Try/except | Try/except | ✅ Perfect match |
| **Type Hints** | Used | Used | ✅ Perfect match |
| **Context Managers** | Used | Used | ✅ Perfect match |

**Overall Compatibility**: ✅ **100% Compatible**

---

## Conclusion

### Is This Disruptive? **No**

**Reasons**:
1. **Same Patterns**: Services follow existing functional helper pattern
2. **Same Databases**: Uses existing SQLite databases and schemas
3. **Same Modules**: Fits into existing module structure
4. **Same Interfaces**: Maintains CLI + library pattern
5. **Additive Only**: No breaking changes, gradual adoption

### Is This Natural Evolution? **Yes**

**Reasons**:
1. **Organizes Existing Code**: Services are organized helper functions
2. **Reduces Duplication**: Addresses known code duplication issues
3. **Enhances Reusability**: Makes existing functions more accessible
4. **Database-Driven**: Moves toward more database queries (already a trend)
5. **Consistent Interfaces**: Standardizes how scripts interact with core functions

### Recommended Approach

**Phase 1: Extract and Organize** (Low Risk)
- Create service functions in existing modules
- Extract duplicate logic to shared functions
- Add Python APIs to CLI-only modules

**Phase 2: Enhance Databases** (Low Risk)
- Add query functions to database helpers
- Enhance schemas if needed (additive only)
- Reduce file system scanning

**Phase 3: Migrate Scripts** (Medium Risk, Gradual)
- Update scripts to use services
- Maintain backward compatibility
- Test incrementally

**Risk Level**: ✅ **Low to Medium** - Services are organizational layer, not architectural change

**Disruption Level**: ✅ **Minimal** - Additive enhancement, follows existing patterns

**Adoption Strategy**: ✅ **Gradual** - Can adopt incrementally, no big-bang migration needed

---

## Final Verdict

**The service architecture is the natural next stage of development.**

It represents **maturation** of the codebase:
- Moving from ad-hoc scripts to organized services
- Reducing duplication through shared functions
- Enhancing reusability through consistent interfaces
- Leveraging database-driven architecture more fully

**It does NOT represent**:
- Architectural paradigm shift
- Breaking changes
- Complete rewrite
- New technology stack

**It IS**:
- Code organization improvement
- Duplication elimination
- Interface standardization
- Natural evolution of existing patterns

**Recommendation**: ✅ **Proceed with confidence** - This is the right direction for the codebase.
