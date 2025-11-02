# Elegant Calibrator MS Generation Design

## Current Design Issues

1. **Monolithic Script**: All logic in one script, hard to reuse
2. **No Database Integration**: MS not registered in products DB automatically
3. **Tight Coupling**: Transit finding + conversion + configuration all mixed
4. **No Idempotency**: Can't safely check if MS already exists in DB
5. **Limited Composability**: Hard to use parts independently
6. **No Progress Tracking**: Minimal feedback during long operations
7. **Manual Path Management**: Output path must be specified manually

## Elegant Design Principles

### 1. **Service-Oriented Architecture**

Create a `CalibratorMSGenerator` service that orchestrates the workflow:

```python
# src/dsa110_contimg/conversion/calibrator_ms_service.py

@dataclass
class CalibratorMSResult:
    """Result of calibrator MS generation."""
    success: bool
    ms_path: Optional[Path]
    transit_info: Optional[dict]
    group_id: Optional[str]
    already_exists: bool
    error: Optional[str] = None
    metrics: Optional[dict] = None

class CalibratorMSGenerator:
    """Service for generating MS files from calibrator transits."""
    
    def __init__(
        self,
        *,
        input_dir: Path,
        output_dir: Path,
        products_db: Path,
        catalogs: List[Path],
        scratch_dir: Optional[Path] = None
    ):
        """Initialize generator with configuration."""
        
    def generate_from_transit(
        self,
        calibrator_name: str,
        transit_time: Optional[Time] = None,
        *,
        window_minutes: int = 60,
        max_days_back: int = 14,
        dec_tolerance_deg: float = 2.0,
        auto_naming: bool = True,
        output_name: Optional[str] = None,
        configure_for_imaging: bool = True,
        register_in_db: bool = True,
        stage_to_tmpfs: bool = True
    ) -> CalibratorMSResult:
        """Generate MS from calibrator transit.
        
        Returns:
            CalibratorMSResult with success status and details
        """
```

### 2. **Automatic Database Registration**

```python
def _register_ms_in_db(
    self,
    ms_path: Path,
    transit_info: dict,
    *,
    status: str = "converted",
    stage: str = "converted"
) -> None:
    """Register MS in products database."""
    conn = ensure_products_db(self.products_db)
    
    # Extract time range from MS
    start_mjd, end_mjd, mid_mjd = _ms_time_range(os.fspath(ms_path))
    
    # Use transit time if MS extraction fails
    if mid_mjd is None:
        from astropy.time import Time
        mid_mjd = Time(transit_info['transit_iso']).mjd
    
    ms_index_upsert(
        conn,
        os.fspath(ms_path),
        start_mjd=start_mjd,
        end_mjd=end_mjd,
        mid_mjd=mid_mjd,
        status=status,
        stage=stage,
        processed_at=time.time(),
    )
    conn.commit()
    conn.close()
```

### 3. **Smart Naming and Path Management**

```python
def _derive_output_path(
    self,
    calibrator_name: str,
    transit_info: dict,
    *,
    auto_naming: bool = True,
    output_name: Optional[str] = None
) -> Path:
    """Derive output MS path intelligently."""
    if output_name:
        return self.output_dir / output_name
    
    if auto_naming:
        # Use calibrator name + transit time
        cal_safe = calibrator_name.replace('+', '_').replace('-', '_')
        transit_iso = transit_info['transit_iso'].replace(':', '-').replace('T', '_')
        return self.output_dir / f"{cal_safe}_{transit_iso}.ms"
    
    # Fallback: use group ID
    return self.output_dir / f"{transit_info['group_id']}.ms"
```

### 4. **Idempotent Operations**

```python
def _check_existing_ms(
    self,
    ms_path: Path,
    transit_info: dict
) -> Tuple[bool, Optional[dict]]:
    """Check if MS already exists (filesystem or database)."""
    # Check filesystem
    if ms_path.exists():
        return True, {"reason": "filesystem"}
    
    # Check database
    conn = ensure_products_db(self.products_db)
    row = conn.execute(
        "SELECT path, status FROM ms_index WHERE path = ?",
        (os.fspath(ms_path),)
    ).fetchone()
    conn.close()
    
    if row:
        return True, {"reason": "database", "status": row[1]}
    
    return False, None
```

### 5. **Composable Workflow Functions**

```python
def find_transit(
    self,
    calibrator_name: str,
    *,
    transit_time: Optional[Time] = None,
    window_minutes: int = 60,
    max_days_back: int = 14
) -> Optional[dict]:
    """Find transit (reusable component)."""
    
def locate_group(
    self,
    transit_info: dict,
    *,
    dec_tolerance_deg: float = 2.0
) -> Optional[List[str]]:
    """Locate subband group for transit (reusable component)."""
    
def convert_group(
    self,
    file_list: List[str],
    output_ms: Path,
    *,
    stage_to_tmpfs: bool = True
) -> bool:
    """Convert group to MS (reusable component)."""
```

### 6. **Progress Reporting**

```python
class ProgressReporter:
    """Progress reporting for long operations."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.steps = []
    
    def step(self, message: str, status: str = "info"):
        """Report a workflow step."""
        timestamp = time.time()
        self.steps.append({
            "timestamp": timestamp,
            "message": message,
            "status": status
        })
        if self.verbose:
            print(f"[{status.upper()}] {message}")
    
    def get_summary(self) -> dict:
        """Get summary of all steps."""
        return {
            "total_steps": len(self.steps),
            "steps": self.steps
        }
```

### 7. **Configuration-Driven**

```python
@dataclass
class CalibratorMSConfig:
    """Configuration for calibrator MS generation."""
    input_dir: Path
    output_dir: Path
    products_db: Path
    catalogs: List[Path]
    scratch_dir: Optional[Path] = None
    default_window_minutes: int = 60
    default_max_days_back: int = 14
    default_dec_tolerance_deg: float = 2.0
    auto_configure: bool = True
    auto_register: bool = True
    auto_stage_tmpfs: bool = True
    
    @classmethod
    def from_env(cls) -> CalibratorMSConfig:
        """Create config from environment variables."""
        return cls(
            input_dir=Path(os.getenv("CONTIMG_INPUT_DIR", "/data/incoming")),
            output_dir=Path(os.getenv("CONTIMG_OUTPUT_DIR", "/scratch/dsa110-contimg/ms")),
            products_db=Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")),
            catalogs=[
                Path("/data/dsa110-contimg/data-samples/catalogs/vla_calibrators_parsed.csv"),
                Path("/data/dsa110-contimg/sim-data-samples/catalogs/vla_calibrators_parsed.csv"),
            ],
            scratch_dir=Path(os.getenv("CONTIMG_SCRATCH_DIR")),
        )
```

## Proposed Implementation Structure

```
src/dsa110_contimg/conversion/
├── calibrator_ms_service.py    # Main service class
├── progress.py                  # Progress reporting utilities
└── config.py                    # Configuration dataclasses
```

## Usage Examples

### Simple Usage (Auto-everything)

```python
from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig

config = CalibratorMSConfig.from_env()
generator = CalibratorMSGenerator(**config.__dict__)

result = generator.generate_from_transit("0834+555")

if result.success:
    print(f"MS ready: {result.ms_path}")
    print(f"Already existed: {result.already_exists}")
else:
    print(f"Error: {result.error}")
```

### Advanced Usage (Custom Configuration)

```python
result = generator.generate_from_transit(
    "0834+555",
    window_minutes=120,
    max_days_back=30,
    output_name="custom_0834.ms",
    configure_for_imaging=True,
    register_in_db=True
)
```

### Composable Usage (Step-by-step)

```python
# Find transit
transit_info = generator.find_transit("0834+555")

# Locate group
file_list = generator.locate_group(transit_info)

# Convert
output_ms = generator._derive_output_path("0834+555", transit_info)
success = generator.convert_group(file_list, output_ms)

# Register
if success:
    generator._register_ms_in_db(output_ms, transit_info)
```

## Benefits of Elegant Design

1. **Reusability**: Service can be used from scripts, API, notebooks
2. **Database Integration**: Automatic registration in products DB
3. **Idempotency**: Safe to run multiple times
4. **Composability**: Functions can be used independently
5. **Progress Tracking**: Clear feedback during operations
6. **Configuration**: Environment-based defaults, easy to override
7. **Error Handling**: Structured errors with diagnostics
8. **Testability**: Each component can be tested independently
9. **Maintainability**: Clear separation of concerns
10. **Extensibility**: Easy to add new features (e.g., auto-calibration)

## Integration Points

- **Products DB**: Automatic MS registration
- **Future Services**: Will integrate with TransitDataMatcher, UnifiedConverter
- **API**: Can be called from FastAPI endpoints
- **CLI**: Simple wrapper script that uses service
- **Notebooks**: Can be used interactively

## Migration Path

1. **Phase 1**: Create service class (keep existing script)
2. **Phase 2**: Update script to use service internally
3. **Phase 3**: Add API endpoint using service
4. **Phase 4**: Deprecate script, promote service usage

