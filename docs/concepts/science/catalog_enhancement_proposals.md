# Catalog Enhancement Proposals

**Status**: Design Proposals  
**Created**: 2025-11-19  
**Purpose**: Identify opportunities to better leverage the catalog system for
science, operations, and data products

---

## Overview

The DSA-110 pipeline integrates multiple astronomical catalogs (NVSS, FIRST,
RACS, VLASS, ATNF, Gaia, SIMBAD, NED) for calibration, validation, and source
identification. This document proposes enhancements to extract more value from
these catalogs.

**Current Catalog Documentation**:
`src/dsa110_contimg/catalog/CATALOG_OVERVIEW.md`

**Current Capabilities**:

- Calibrator selection from radio catalogs
- Source cross-matching for validation
- Flux scale validation
- Basic source classification via multi-wavelength queries

**Enhancement Focus Areas**:

1. Science value (spectral indices, transient detection, classifications)
2. Operational efficiency (smart calibrator selection, astrometric corrections)
3. Data products (VO-compliant catalogs, monitoring dashboards)

---

## Proposals

### 1. Automated Spectral Index Mapping

**Priority**: High  
**Effort**: Low  
**Science Value**: High  
**Implementation Complexity**: Low

#### Current State

- NVSS (1.4 GHz), VLASS (3 GHz), and RACS (888 MHz) catalogs available
- Cross-matching finds matches in multiple catalogs
- Spectral indices not systematically calculated or stored

#### Opportunity

Automatically compute spectral indices (α, where S ∝ ν^α) for every source
matched in multiple frequency catalogs:

- **Scientific Classification**:
  - α < -1.0: Steep-spectrum sources (high-z radio galaxies, relics)
  - -1.0 < α < -0.5: Normal radio sources
  - α > -0.5: Flat-spectrum sources (AGN cores, blazars)
  - α > 0.0: Inverted spectrum (compact self-absorbed sources)

- **Calibration Improvement**:
  - Predict expected flux at DSA-110 frequency (1.4 GHz)
  - Select calibrators with well-constrained spectral behavior
  - Avoid highly variable flat-spectrum blazars

- **Science Products**:
  - Generate "spectral index maps" alongside intensity mosaics
  - Enable queries like "find all α < -1.5 sources" (extreme steep-spectrum)
  - Identify synchrotron aging in extended sources

#### Implementation Design

**Database Schema Addition**:

```sql
-- Add to cross_matches table or create new table
ALTER TABLE cross_matches ADD COLUMN spectral_index REAL;
ALTER TABLE cross_matches ADD COLUMN spectral_index_err REAL;
ALTER TABLE cross_matches ADD COLUMN freq_ref_mhz REAL;  -- Reference frequency
ALTER TABLE cross_matches ADD COLUMN freq_compare_mhz REAL;  -- Comparison frequency

-- Or create dedicated spectral_indices table
CREATE TABLE spectral_indices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    alpha REAL NOT NULL,  -- Spectral index
    alpha_err REAL,
    freq1_mhz REAL NOT NULL,  -- Lower frequency
    freq2_mhz REAL NOT NULL,  -- Higher frequency
    flux1_mjy REAL NOT NULL,
    flux2_mjy REAL NOT NULL,
    catalog1 TEXT NOT NULL,  -- e.g., "racs"
    catalog2 TEXT NOT NULL,  -- e.g., "nvss"
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);
```

**Code Module**: `catalog/spectral_index.py`

```python
def calculate_spectral_index(
    flux1_mjy: float,
    freq1_mhz: float,
    flux2_mjy: float,
    freq2_mhz: float,
    flux1_err: Optional[float] = None,
    flux2_err: Optional[float] = None
) -> Tuple[float, Optional[float]]:
    """
    Calculate spectral index: S = S0 * (ν/ν0)^α

    Returns:
        (alpha, alpha_err) tuple
    """
    alpha = np.log10(flux1_mjy / flux2_mjy) / np.log10(freq1_mhz / freq2_mhz)

    if flux1_err and flux2_err:
        # Propagate uncertainty
        alpha_err = np.abs(alpha) * np.sqrt(
            (flux1_err/flux1_mjy)**2 + (flux2_err/flux2_mjy)**2
        )
        return alpha, alpha_err

    return alpha, None


def compute_spectral_indices_for_crossmatches(
    crossmatch_df: pd.DataFrame,
    catalog_frequencies: Dict[str, float]
) -> pd.DataFrame:
    """
    Compute spectral indices for sources matched in multiple catalogs.

    Args:
        crossmatch_df: DataFrame from multi_catalog_match()
        catalog_frequencies: Dict mapping catalog names to frequencies (MHz)
            e.g., {"nvss": 1400, "vlass": 3000, "racs": 888}

    Returns:
        DataFrame with columns: source_id, alpha, alpha_err, freq1, freq2, ...
    """
    # Group by source_id to find multi-catalog matches
    # Calculate spectral index for each pair
    # Return results
    pass
```

**Pipeline Integration**:

- Add to `CrossMatchStage` after multi-catalog matching
- Compute spectral indices when ≥2 frequency catalogs matched
- Store in database automatically

**Visualization**:

- Add `--spectral-index` option to mosaic creation
- Generate FITS image with α values per pixel (using nearest source)
- Color-coded maps: red (steep), white (normal), blue (flat)

**API Endpoint**:

```python
@router.get("/sources/{source_id}/spectral-index")
def get_spectral_index(source_id: str):
    """Get spectral index information for a source."""
    # Query spectral_indices table
    # Return alpha, frequencies, catalogs used
```

#### Benefits

- **Science**: Identify rare source populations (ultra-steep spectrum, inverted
  spectrum)
- **Calibration**: Better calibrator selection using spectral constraints
- **Validation**: Detect flux scale issues (systematic spectral index offsets)
- **Publications**: Spectral index distributions, extreme source catalogs

#### Risks / Limitations

- Requires matches in ≥2 catalogs at different frequencies
- Frequency coverage limited (888 MHz - 3 GHz)
- Assumes simple power-law spectrum (may not hold for all sources)
- RACS-VLASS baseline good (888 MHz - 3 GHz), NVSS-VLASS less ideal (1.4 - 3
  GHz)

#### Estimated Effort

- **Development**: 2-3 days
  - Database schema: 2 hours
  - Calculation functions: 4 hours
  - Pipeline integration: 8 hours
  - Testing: 4 hours
- **Documentation**: 4 hours

---

### 2. Transient Detection via Catalog Differencing

**Priority**: High  
**Effort**: Medium  
**Science Value**: Very High (core DSA-110 science goal)  
**Implementation Complexity**: Medium

#### Current State

- Catalogs used for validation but not systematically checked for new sources
- No automated flagging of catalog-absent sources
- No tracking of long-term variability (DSA-110 vs. NVSS 1993-1996 epoch)

#### Opportunity

Systematically detect transient and variable radio sources:

**Transient Types**:

- **New sources**: Detected by DSA-110, absent from all catalogs
- **Long-term variables**: Flux changed significantly since NVSS/FIRST epoch
- **Disappeared sources**: In catalog but not detected by DSA-110 (fading
  transients)

**Science Cases**:

- Tidal disruption events (TDEs)
- Supernovae (radio afterglows)
- Stellar flares / active binaries
- AGN variability
- Orphan afterglows (GRBs without detected optical/X-ray)
- Fast radio bursts (FRB) persistent sources

#### Implementation Design

**Database Schema**:

```sql
CREATE TABLE transient_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    detection_type TEXT NOT NULL,  -- "new", "variable", "fading"
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_dsa_mjy REAL NOT NULL,
    flux_catalog_mjy REAL,  -- NULL for new sources
    catalog_searched TEXT,  -- Comma-separated: "nvss,first,racs"
    flux_ratio REAL,  -- DSA/catalog for variables
    variability_timescale_days REAL,  -- Time since catalog epoch
    confidence_score REAL,  -- 0-1, based on SNR, match radius, etc.
    follow_up_priority TEXT,  -- "high", "medium", "low"
    status TEXT DEFAULT 'candidate',  -- "candidate", "confirmed", "rejected"
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE INDEX idx_transients_type ON transient_candidates(detection_type);
CREATE INDEX idx_transients_priority ON transient_candidates(follow_up_priority);
CREATE INDEX idx_transients_status ON transient_candidates(status);
CREATE INDEX idx_transients_created ON transient_candidates(created_at);
```

**Code Module**: `transients/detection.py`

```python
def detect_transient_candidates(
    detected_sources: pd.DataFrame,
    catalog_crossmatches: pd.DataFrame,
    catalogs_searched: List[str],
    min_snr: float = 7.0,
    min_flux_ratio: float = 2.0,
    max_match_radius_arcsec: float = 10.0
) -> pd.DataFrame:
    """
    Identify transient candidates from cross-match results.

    Transient types:
    1. "new": No match in any catalog within max_match_radius
    2. "variable": Matched but flux_ratio > min_flux_ratio
    3. "fading": Catalog source not detected by DSA-110

    Args:
        detected_sources: DSA-110 detected sources
        catalog_crossmatches: Results from multi_catalog_match()
        catalogs_searched: List of catalogs queried (e.g., ["nvss", "first"])
        min_snr: Minimum SNR for transient candidate
        min_flux_ratio: Minimum DSA/catalog flux ratio for variability
        max_match_radius_arcsec: Maximum radius for "no match" classification

    Returns:
        DataFrame with transient candidates
    """
    candidates = []

    for _, source in detected_sources.iterrows():
        if source['snr'] < min_snr:
            continue  # Low-confidence detection, skip

        # Check if source has catalog match
        matches = catalog_crossmatches[
            catalog_crossmatches['source_id'] == source['id']
        ]

        if len(matches) == 0:
            # New source (not in any catalog)
            candidates.append({
                'source_id': source['id'],
                'detection_type': 'new',
                'ra_deg': source['ra_deg'],
                'dec_deg': source['dec_deg'],
                'flux_dsa_mjy': source['flux_mjy'],
                'flux_catalog_mjy': None,
                'catalog_searched': ','.join(catalogs_searched),
                'confidence_score': min(source['snr'] / 10.0, 1.0),
                'follow_up_priority': 'high' if source['snr'] > 10 else 'medium'
            })

        else:
            # Check for significant variability
            for _, match in matches.iterrows():
                if match['separation_arcsec'] > max_match_radius_arcsec:
                    continue  # Poor match, likely different source

                flux_ratio = source['flux_mjy'] / match['flux_catalog_mjy']

                if flux_ratio > min_flux_ratio or flux_ratio < 1.0/min_flux_ratio:
                    # Significant variability
                    catalog_epoch = CATALOG_EPOCHS.get(match['catalog_type'], 2000.0)
                    obs_epoch = source.get('obs_epoch', 2025.0)
                    timescale_days = (obs_epoch - catalog_epoch) * 365.25

                    candidates.append({
                        'source_id': source['id'],
                        'detection_type': 'variable',
                        'ra_deg': source['ra_deg'],
                        'dec_deg': source['dec_deg'],
                        'flux_dsa_mjy': source['flux_mjy'],
                        'flux_catalog_mjy': match['flux_catalog_mjy'],
                        'catalog_searched': match['catalog_type'],
                        'flux_ratio': flux_ratio,
                        'variability_timescale_days': timescale_days,
                        'confidence_score': min(abs(flux_ratio - 1.0) / 2.0, 1.0),
                        'follow_up_priority': 'high' if flux_ratio > 5.0 else 'medium'
                    })

    return pd.DataFrame(candidates)


# Catalog epochs for variability timescale calculation
CATALOG_EPOCHS = {
    "nvss": 1994.5,  # ~1993-1996
    "first": 2002.0,  # ~1993-2011
    "vlass": 2020.0,  # ~2017-present
    "racs": 2020.0,  # ~2019-2021
}
```

**Pipeline Integration**:

Add new `TransientDetectionStage` after `CrossMatchStage`:

```python
class TransientDetectionStage(PipelineStage):
    """Detect transient candidates via catalog differencing."""

    def execute(self, context: PipelineContext) -> PipelineContext:
        if not self.config.transients.enabled:
            return context

        detected_sources = context.outputs['detected_sources']
        crossmatch_results = context.outputs['crossmatch_results']

        # Detect candidates
        candidates = detect_transient_candidates(
            detected_sources,
            crossmatch_results,
            catalogs_searched=self.config.crossmatch.catalog_types,
            min_snr=self.config.transients.min_snr,
            min_flux_ratio=self.config.transients.min_flux_ratio
        )

        # Store in database
        store_transient_candidates(candidates)

        # Send alerts for high-priority candidates
        if self.config.transients.send_alerts:
            high_priority = candidates[candidates['follow_up_priority'] == 'high']
            send_transient_alerts(high_priority)

        return context.with_output('transient_candidates', candidates)
```

**Configuration**:

```python
class TransientConfig(BaseModel):
    enabled: bool = False  # Enable transient detection
    min_snr: float = 7.0  # Minimum SNR for candidates
    min_flux_ratio: float = 2.0  # Minimum flux change for variability
    max_match_radius_arcsec: float = 10.0  # Maximum "no match" radius
    send_alerts: bool = False  # Send alerts for high-priority candidates
    alert_webhook_url: Optional[str] = None  # Slack/email webhook
```

**Alert System**:

```python
def send_transient_alerts(candidates: pd.DataFrame):
    """Send alerts for high-priority transient candidates."""
    for _, candidate in candidates.iterrows():
        message = format_transient_alert(candidate)

        # Send to Slack, email, or other notification system
        if ALERT_WEBHOOK_URL:
            requests.post(ALERT_WEBHOOK_URL, json={"text": message})

        # Log alert
        logger.warning(f"TRANSIENT CANDIDATE: {message}")


def format_transient_alert(candidate: dict) -> str:
    """Format transient candidate as alert message."""
    if candidate['detection_type'] == 'new':
        return (
            f"🌟 NEW TRANSIENT CANDIDATE\n"
            f"Position: RA={candidate['ra_deg']:.4f}°, Dec={candidate['dec_deg']:.4f}°\n"
            f"Flux: {candidate['flux_dsa_mjy']:.2f} mJy\n"
            f"Not found in: {candidate['catalog_searched']}\n"
            f"Priority: {candidate['follow_up_priority']}"
        )
    elif candidate['detection_type'] == 'variable':
        return (
            f"📈 VARIABLE SOURCE CANDIDATE\n"
            f"Position: RA={candidate['ra_deg']:.4f}°, Dec={candidate['dec_deg']:.4f}°\n"
            f"DSA Flux: {candidate['flux_dsa_mjy']:.2f} mJy\n"
            f"Catalog Flux: {candidate['flux_catalog_mjy']:.2f} mJy\n"
            f"Flux Ratio: {candidate['flux_ratio']:.1f}×\n"
            f"Timescale: {candidate['variability_timescale_days']:.0f} days\n"
            f"Priority: {candidate['follow_up_priority']}"
        )
```

**API Endpoints**:

```python
@router.get("/transients/candidates")
def list_transient_candidates(
    detection_type: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """List transient candidates with filters."""
    pass


@router.get("/transients/{candidate_id}")
def get_transient_details(candidate_id: int):
    """Get detailed information for a transient candidate."""
    pass


@router.post("/transients/{candidate_id}/status")
def update_transient_status(candidate_id: int, status: str, notes: str):
    """Update transient status (candidate → confirmed/rejected)."""
    pass
```

**Dashboard Integration**:

- Add "Transients" tab showing recent candidates
- Map view with candidate locations
- Light curves for variable sources (if multiple epochs available)
- Quick actions: mark as confirmed/rejected, trigger follow-up

#### Benefits

- **Science**: Core DSA-110 goal (transient discovery in radio)
- **Operations**: Automatic candidate identification reduces manual effort
- **Follow-up**: Prioritized list for rapid follow-up observations
- **Publications**: Transient catalogs, variability studies

#### Risks / Limitations

- False positives from:
  - Imaging artifacts (sidelobes, RFI)
  - Calibration errors (flux scale issues)
  - Catalog incompleteness (source in catalog but not in strip DB)
- Requires good flux calibration for variability detection
- Limited to long-term variability (days-years, not intra-observation)

#### Estimated Effort

- **Development**: 5-7 days
  - Database schema: 4 hours
  - Detection algorithm: 12 hours
  - Pipeline stage: 8 hours
  - Alert system: 8 hours
  - API endpoints: 8 hours
  - Dashboard integration: 16 hours
  - Testing: 8 hours
- **Documentation**: 8 hours

---

### 3. Smart Calibrator Pre-Selection

**Priority**: Medium  
**Effort**: Medium  
**Science Value**: Low (operational improvement)  
**Implementation Complexity**: Medium

#### Current State

- Calibrator selection queries catalogs at runtime for each MS
- Same queries repeated for nearby declinations (redundant)
- No caching or pre-computed lookup tables
- Variable sources (pulsars, blazars) not automatically excluded

#### Opportunity

Build a pre-computed calibrator registry to improve performance and reliability:

**Performance Gains**:

- Eliminate redundant catalog queries (10-30s per MS → <1s lookup)
- Pre-compute primary beam weights for declination strips
- Cache results for repeated observations at same declination

**Quality Improvements**:

- Blacklist known variable sources (blazars, pulsars)
- Prefer sources with multiple catalog matches (cross-validated)
- Include spectral index information (avoid steep-spectrum sources)
- Flag sources with known structure (resolved, double-lobed)

#### Implementation Design

**Database Schema**: `state/calibrator_registry.sqlite3`

```sql
CREATE TABLE calibrators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,  -- VLA calibrator name or catalog ID
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_1400_jy REAL NOT NULL,  -- Flux at 1.4 GHz
    spectral_index REAL,  -- α (S ∝ ν^α)
    is_variable BOOLEAN DEFAULT 0,  -- Known variable source
    is_resolved BOOLEAN DEFAULT 0,  -- Resolved by VLA
    quality_score REAL,  -- 0-1, based on multiple factors
    catalogs_matched TEXT,  -- Comma-separated: "nvss,first,vlass"
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE calibrator_strips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dec_center REAL NOT NULL,  -- Declination strip center
    dec_width REAL DEFAULT 1.0,  -- Strip width (degrees)
    calibrator_id INTEGER NOT NULL,
    pb_weight REAL NOT NULL,  -- Primary beam weight at strip center
    rank INTEGER,  -- Rank within strip (1 = best)
    FOREIGN KEY (calibrator_id) REFERENCES calibrators(id)
);

CREATE INDEX idx_calibrators_dec ON calibrators(dec_deg);
CREATE INDEX idx_calibrators_flux ON calibrators(flux_1400_jy DESC);
CREATE INDEX idx_strips_dec ON calibrator_strips(dec_center);
CREATE INDEX idx_strips_rank ON calibrator_strips(rank);
```

**Building the Registry**:

```python
def build_calibrator_registry(
    output_path: str = "state/calibrator_registry.sqlite3",
    dec_range: Tuple[float, float] = (-30.0, 70.0),
    dec_step: float = 1.0,
    min_flux_jy: float = 1.0,
    force: bool = False
):
    """
    Build calibrator registry for all declination strips.

    Steps:
    1. Query VLA calibrator catalog + NVSS/FIRST/VLASS
    2. Cross-match to find multi-catalog sources
    3. Compute spectral indices (if multiple frequencies matched)
    4. Flag variable sources (cross-match with ATNF, WISE AGN)
    5. Compute primary beam weights for each declination strip
    6. Rank calibrators within each strip
    7. Store in SQLite database
    """
    pass
```

**Query Interface**:

```python
def query_calibrators(
    dec_deg: float,
    min_flux_jy: float = 1.0,
    max_results: int = 20,
    exclude_variable: bool = True,
    exclude_resolved: bool = False,
    registry_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Query pre-built calibrator registry for a declination.

    Fast lookup (<1s) replacing real-time catalog queries.

    Returns:
        DataFrame with columns: source_name, ra_deg, dec_deg, flux_1400_jy,
                               spectral_index, pb_weight, rank, quality_score
    """
    if registry_path is None:
        registry_path = "state/calibrator_registry.sqlite3"

    conn = sqlite3.connect(registry_path)

    query = """
        SELECT c.*, s.pb_weight, s.rank
        FROM calibrator_strips s
        JOIN calibrators c ON s.calibrator_id = c.id
        WHERE s.dec_center BETWEEN ? AND ?
          AND c.flux_1400_jy >= ?
    """

    params = [dec_deg - 0.5, dec_deg + 0.5, min_flux_jy]

    if exclude_variable:
        query += " AND c.is_variable = 0"

    if exclude_resolved:
        query += " AND c.is_resolved = 0"

    query += " ORDER BY s.rank LIMIT ?"
    params.append(max_results)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    return df
```

**Integration**:

```python
# Replace in calibration/selection.py
def select_bandpass_from_catalog(
    ms_path: str,
    catalog_path: Optional[str] = None,
    **kwargs
) -> Tuple[str, List[int], np.ndarray, Tuple[str, float, float, float], int]:
    """
    Select bandpass fields by scanning a VLA calibrator catalog.

    Now uses pre-built registry if available, falls back to dynamic queries.
    """
    ra_field, dec_field = _read_field_dirs(ms_path)
    dec_center = np.median(dec_field)

    # Try registry first (fast path)
    try:
        calibrators = query_calibrators(
            dec_deg=dec_center,
            min_flux_jy=kwargs.get('min_flux_jy', 1.0),
            max_results=20,
            exclude_variable=True
        )

        if not calibrators.empty:
            logger.info(f"Using pre-built calibrator registry ({len(calibrators)} candidates)")
            return _select_from_calibrator_df(calibrators, ra_field, dec_field, **kwargs)

    except FileNotFoundError:
        logger.debug("Calibrator registry not found, falling back to dynamic query")

    # Fallback to dynamic catalog query (original code path)
    return _select_from_dynamic_query(ms_path, catalog_path, **kwargs)
```

**Maintenance**:

```bash
# Rebuild registry periodically (monthly for ATNF updates)
python -m dsa110_contimg.calibration.build_calibrator_registry \
    --output state/calibrator_registry.sqlite3 \
    --force
```

#### Benefits

- **Performance**: 10-30× speedup in calibrator selection (30s → <1s)
- **Reliability**: Blacklist variable sources, prefer well-characterized sources
- **Quality**: Include spectral indices, multi-catalog validation
- **Efficiency**: Eliminate redundant queries for nearby observations

#### Risks / Limitations

- Registry becomes stale (ATNF adds new pulsars, VLA updates calibrators)
- Requires periodic rebuilding (monthly/quarterly)
- Storage overhead (~100 MB for full registry)
- Fallback to dynamic queries needed if registry missing

#### Estimated Effort

- **Development**: 4-5 days
  - Database schema: 4 hours
  - Builder script: 16 hours
  - Query interface: 8 hours
  - Integration: 8 hours
  - Testing: 8 hours
- **Documentation**: 4 hours

---

### 4. Multi-wavelength Source Classification Pipeline

**Priority**: Medium  
**Effort**: High  
**Science Value**: High  
**Implementation Complexity**: High

#### Current State

- External catalogs (Gaia, SIMBAD, NED) queryable via API
- Multi-wavelength checks available in `catalog/multiwavelength.py`
- No systematic classification of all detected sources
- Classification results not stored persistently

#### Opportunity

Automatically classify every detected source using multi-wavelength information:

**Classification Scheme**:

- **Stars**: Gaia match + weak radio (stellar contamination)
- **AGN/Quasars**: SIMBAD "QSO" or NED extragalactic + flat spectrum
- **Radio Galaxies**: NED match + steep spectrum + extended morphology
- **Pulsars**: ATNF match
- **Transients**: No catalog match + high SNR
- **Unknown**: No classification possible

**Science Value**:

- Generate science-ready source catalogs with types, redshifts, spectral indices
- Enable population studies (AGN fraction, pulsar detections, stellar
  contamination rate)
- Prioritize interesting sources for follow-up
- Filter out contamination (stars) from radio source samples

#### Implementation Design

**Database Schema**:

```sql
CREATE TABLE source_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL UNIQUE,
    classification TEXT NOT NULL,  -- "star", "agn", "galaxy", "pulsar", "transient", "unknown"
    confidence REAL NOT NULL,  -- 0-1

    -- External catalog matches
    gaia_id TEXT,
    gaia_separation_arcsec REAL,
    gaia_g_mag REAL,

    simbad_id TEXT,
    simbad_type TEXT,
    simbad_separation_arcsec REAL,

    ned_name TEXT,
    ned_type TEXT,
    ned_redshift REAL,
    ned_separation_arcsec REAL,

    atnf_name TEXT,
    atnf_separation_arcsec REAL,

    -- Additional properties
    has_optical_counterpart BOOLEAN,
    has_xray_counterpart BOOLEAN,
    notes TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE INDEX idx_classifications_class ON source_classifications(classification);
CREATE INDEX idx_classifications_confidence ON source_classifications(confidence);
CREATE INDEX idx_classifications_redshift ON source_classifications(ned_redshift);
```

**Code Module**: `classification/classify.py`

```python
def classify_source(
    source: dict,
    match_radius_arcsec: float = 10.0,
    gaia_priority: bool = True
) -> dict:
    """
    Classify a source using multi-wavelength catalogs.

    Classification logic:
    1. Gaia match → star (if radio weak) or AGN (if radio strong)
    2. ATNF match → pulsar
    3. SIMBAD QSO → quasar/AGN
    4. NED match + z > 0 → galaxy/AGN
    5. No matches + high SNR → transient candidate
    6. Otherwise → unknown

    Returns:
        {
            'classification': str,
            'confidence': float,
            'gaia_match': dict or None,
            'simbad_match': dict or None,
            'ned_match': dict or None,
            'atnf_match': dict or None
        }
    """
    from dsa110_contimg.catalog.external import search_all_external
    from dsa110_contimg.catalog.multiwavelength import check_atnf
    from astropy.coordinates import SkyCoord
    import astropy.units as u

    coord = SkyCoord(ra=source['ra_deg']*u.deg, dec=source['dec_deg']*u.deg)

    # Query external catalogs
    external = search_all_external(coord, radius_arcsec=match_radius_arcsec)
    atnf = check_atnf(coord, radius=match_radius_arcsec*u.arcsec)

    # Classification logic
    if atnf:
        # Pulsar (highest priority for radio astronomy)
        return {
            'classification': 'pulsar',
            'confidence': 0.95,
            'atnf_match': atnf,
            **external
        }

    if external['gaia']:
        gaia = external['gaia']
        # Star if faint radio (< 10 mJy) or AGN if bright radio
        if source.get('flux_mjy', 0) < 10:
            return {
                'classification': 'star',
                'confidence': 0.85,
                'gaia_match': gaia,
                **external
            }
        else:
            # Bright radio + optical → likely AGN
            return {
                'classification': 'agn',
                'confidence': 0.75,
                'gaia_match': gaia,
                **external
            }

    if external['simbad']:
        simbad = external['simbad']
        if simbad.get('otype') in ['QSO', 'AGN', 'Blazar']:
            return {
                'classification': 'agn',
                'confidence': 0.90,
                'simbad_match': simbad,
                **external
            }

    if external['ned']:
        ned = external['ned']
        # Extragalactic source
        if ned.get('redshift', 0) > 0.1:
            # High-z → likely radio galaxy
            return {
                'classification': 'radio_galaxy',
                'confidence': 0.80,
                'ned_match': ned,
                **external
            }
        else:
            # Low-z → could be AGN or star-forming galaxy
            return {
                'classification': 'galaxy',
                'confidence': 0.70,
                'ned_match': ned,
                **external
            }

    # No external matches
    if source.get('snr', 0) > 10:
        # High SNR + no catalog match → transient candidate
        return {
            'classification': 'transient',
            'confidence': 0.60,
            **external
        }

    # Unknown
    return {
        'classification': 'unknown',
        'confidence': 0.50,
        **external
    }
```

**Pipeline Stage**: `ClassificationStage`

```python
class ClassificationStage(PipelineStage):
    """Classify detected sources using multi-wavelength catalogs."""

    def execute(self, context: PipelineContext) -> PipelineContext:
        if not self.config.classification.enabled:
            return context

        detected_sources = context.outputs['detected_sources']

        classifications = []
        for _, source in detected_sources.iterrows():
            try:
                result = classify_source(
                    source.to_dict(),
                    match_radius_arcsec=self.config.classification.match_radius_arcsec
                )
                classifications.append(result)
            except Exception as e:
                logger.warning(f"Classification failed for {source['id']}: {e}")
                continue

        # Store in database
        store_classifications(classifications)

        return context.with_output('source_classifications', classifications)
```

**API Endpoints**:

```python
@router.get("/sources/{source_id}/classification")
def get_source_classification(source_id: str):
    """Get multi-wavelength classification for a source."""
    pass


@router.get("/sources/by-class/{classification}")
def list_sources_by_class(
    classification: str,
    min_confidence: float = 0.5,
    limit: int = 100
):
    """List sources of a specific classification."""
    pass
```

#### Benefits

- **Science**: Science-ready catalogs with source types, redshifts
- **Population Studies**: AGN fraction, pulsar detections, stellar contamination
- **Follow-up Prioritization**: Focus on interesting source types
- **Data Quality**: Identify and filter stellar contamination

#### Risks / Limitations

- Requires external API access (Gaia, SIMBAD, NED)
- Classification accuracy limited by catalog completeness
- False positives (e.g., AGN misclassified as star)
- Slow (external queries take 1-10s per source)

#### Estimated Effort

- **Development**: 7-10 days
  - Database schema: 4 hours
  - Classification logic: 16 hours
  - Pipeline stage: 12 hours
  - API endpoints: 8 hours
  - Testing: 16 hours
  - Dashboard integration: 16 hours
- **Documentation**: 8 hours

---

### 5. Astrometric Self-Calibration

**Priority**: Low  
**Effort**: Medium  
**Science Value**: Medium  
**Implementation Complexity**: Medium

#### Current State

- Positional offsets calculated during cross-matching
- Offsets not applied back to images
- No iterative astrometric refinement

#### Opportunity

Use high-resolution catalogs (FIRST at 5") as astrometric reference:

- Calculate systematic RA/Dec offsets from cross-matching
- Automatically correct WCS headers in FITS images
- Iterative refinement: initial mosaic → cross-match → refine WCS → re-mosaic
- Track astrometric accuracy over time (correlate with ionospheric conditions)

**Benefits**:

- Improve astrometric accuracy from ~2-3" to <1" (FIRST-limited)
- Enable precise source localization for multi-wavelength follow-up
- Detect systematic errors (antenna position errors, ionospheric refraction)

**Implementation**: Add WCS correction in `mosaic/orchestrator.py` based on
cross-match offsets

---

### 6. Flux Calibration Monitoring & Alerts

**Priority**: Medium  
**Effort**: Low  
**Science Value**: Low (operational quality)  
**Implementation Complexity**: Low

#### Current State

- Flux validation runs but results not systematically tracked
- No trending or alerting for flux scale drift

#### Opportunity

Build operational monitoring for flux calibration health:

- Store validation results in `calibration_monitoring` table
- Track median flux ratio over time (daily/weekly trends)
- Alert when ratio drifts outside 0.9-1.1 range
- Correlate flux issues with weather, calibrator selection, antenna performance

**Benefits**:

- Early detection of calibration issues
- Data quality assurance
- Reduced need for manual validation checks

**Implementation**: Add monitoring database table, trending dashboard, Slack
alerts

---

### 7. Proper Motion Corrections for Long-Term Studies

**Priority**: Low  
**Effort**: Low  
**Science Value**: Low (niche use case)  
**Implementation Complexity**: Low

#### Current State

- Gaia/ATNF proper motions available but not systematically applied
- Catalog positions not epoch-corrected

#### Opportunity

Automatically epoch-correct all catalog positions:

- Apply proper motion from Gaia/ATNF to catalog positions
- Critical for pulsars (some have PM > 100 mas/yr)
- Enables accurate matching to historical surveys (NVSS 1993)

**Benefits**:

- Accurate matching for high-PM sources
- Enable long-term variability studies

**Implementation**: Add `epoch` parameter to all catalog queries, use
`astropy.coordinates` PM correction

---

### 8. Coverage-Aware Catalog Selection

**Priority**: Low  
**Effort**: Medium  
**Science Value**: Low (optimization)  
**Implementation Complexity**: Medium

#### Current State

- Manual declination-based catalog selection
- No optimization for resolution, frequency match, completeness

#### Opportunity

Build "catalog recommendation engine":

- Input: RA, Dec, purpose (calibration/validation/cross-matching)
- Output: Ranked list of best catalogs for that location
- Factors: declination coverage, resolution, frequency match, completeness

**Benefits**:

- Optimal catalog selection for each observation
- Better cross-matching results (use highest-resolution available)

**Implementation**: Add `recommend_catalogs(ra, dec, purpose)` function with
coverage maps

---

### 9. Pulsar Timing Integration

**Priority**: Low  
**Effort**: High  
**Science Value**: High (specialized)  
**Implementation Complexity**: High

#### Current State

- ATNF identifies pulsars but timing info (period, DM) not used
- Pulsar flux variability not tracked

#### Opportunity

Integrate pulsar timing information:

- Use period/DM to predict visibility windows
- Flag expected flux variability
- Build pulsar light curves from DSA-110 observations
- Contribute flux measurements to pulsar community

**Benefits**:

- Pulsar science (timing, flux monitoring)
- Community contributions (flux measurements)

**Implementation**: Requires pulsar-specific processing, light curve database

---

### 10. Science-Ready Catalog Products

**Priority**: Medium  
**Effort**: Medium  
**Science Value**: High  
**Implementation Complexity**: Medium

#### Current State

- Cross-match results stored in database
- No export as VO-compliant catalogs
- Not discoverable by external astronomers

#### Opportunity

Generate Virtual Observatory (VO) compliant catalogs:

- Export as FITS tables with standardized columns
- Include all cross-matches, spectral indices, classifications
- Publish to VO registries (discoverable worldwide)
- Enable queries: "All z > 1 radio galaxies in DSA-110"

**Benefits**:

- Community access to DSA-110 catalogs
- Enable multi-wavelength studies by external researchers
- Increased visibility and citations

**Implementation**: Add `export_vo_catalog()` function, generate during
publishing, upload to VO registry

---

## Implementation Roadmap

**User-Prioritized Implementation Order**:

1. Flux Calibration Monitoring & Alerts (Proposal #6)
2. Spectral Index Mapping (Proposal #1)
3. Coverage-Aware Catalog Selection (Proposal #8)
4. Smart Calibrator Pre-Selection (Proposal #3)
5. Transient Detection (Proposal #2)
6. Astrometric Self-Calibration (Proposal #5)
7. Science-Ready Catalog Products (Proposal #10)

---

### Phase 1: Operational Foundation (Months 1-2)

**Goal**: Establish monitoring and basic catalog enhancements for operational
quality

**Deliverables**:

1. **Flux Calibration Monitoring & Alerts** (Proposal #6) - PRIORITY 1
   - Monitoring database table (`calibration_monitoring`)
   - Trending calculations (daily/weekly flux ratios)
   - Alert system (Slack/email when drift > 20%)
   - Dashboard integration with plots
   - **Effort**: 3 days
   - **Rationale**: Critical for operational health, detects calibration issues
     early

2. **Spectral Index Mapping** (Proposal #1) - PRIORITY 2
   - Database schema (`spectral_indices` table)
   - Calculation functions for multi-frequency matches
   - Pipeline integration in `CrossMatchStage`
   - API endpoints for queries
   - **Effort**: 3 days
   - **Rationale**: Low effort, enables source classification and better
     calibrator selection

3. **Documentation**
   - User guides for new features
   - API documentation updates
   - Operations runbooks
   - **Effort**: 2 days

**Total Effort**: ~8 days

**Key Outcomes**:

- Real-time flux calibration health monitoring
- Automated spectral index calculations for all multi-catalog matches
- Foundation for advanced catalog features

---

### Phase 2: Intelligent Catalog Management (Months 3-4)

**Goal**: Optimize catalog queries and improve calibrator selection

**Deliverables**:

1. **Coverage-Aware Catalog Selection** (Proposal #8) - PRIORITY 3
   - Coverage map generation for all catalogs
   - `recommend_catalogs(ra, dec, purpose)` function
   - Integration with query functions (auto-select best catalog)
   - Documentation of catalog coverage limits
   - **Effort**: 4 days
   - **Rationale**: Ensures optimal catalog selection, improves cross-match
     quality

2. **Smart Calibrator Pre-Selection** (Proposal #3) - PRIORITY 4
   - Build calibrator registry (`calibrator_registry.sqlite3`)
   - Pre-compute primary beam weights per declination strip
   - Blacklist variable sources (ATNF pulsars, WISE AGN blazars)
   - Integration with `select_bandpass_from_catalog()`
   - **Effort**: 5 days
   - **Rationale**: 10× speedup in calibrator selection, improved reliability

**Total Effort**: ~9 days

**Key Outcomes**:

- Automatic optimal catalog selection based on coverage and purpose
- Cached calibrator lookup (30s → 3s per MS)
- Improved calibration quality (blacklisted variable sources)

---

### Phase 3: Science Detection Pipeline (Months 5-6)

**Goal**: Enable transient detection and astrometric refinement

**Deliverables**:

1. **Transient Detection** (Proposal #2) - PRIORITY 5
   - Database schema (`transient_candidates` table)
   - Detection algorithm (new sources, variables, fading)
   - `TransientDetectionStage` pipeline stage
   - Alert system for high-priority candidates
   - API endpoints and dashboard integration
   - **Effort**: 7 days (includes dashboard work)
   - **Rationale**: Core DSA-110 science goal, automated candidate
     identification

2. **Astrometric Self-Calibration** (Proposal #5) - PRIORITY 6
   - Calculate systematic RA/Dec offsets from FIRST cross-matches
   - WCS header correction functions
   - Integration in mosaic stage (optional iterative refinement)
   - Tracking of astrometric accuracy over time
   - **Effort**: 4 days
   - **Rationale**: Improve positional accuracy from ~2-3" to <1"

**Total Effort**: ~11 days

**Key Outcomes**:

- Automated transient candidate identification with alerts
- Sub-arcsecond astrometric accuracy (FIRST-limited)
- Transient database for tracking source variability

---

### Phase 4: Publication-Quality Products (Months 7-8)

**Goal**: Generate community-accessible, VO-compliant data products

**Deliverables**:

1. **Science-Ready Catalog Products** (Proposal #10) - PRIORITY 7
   - VO-compliant FITS table export
   - Include all metadata: cross-matches, spectral indices, classifications
   - VO registry submission (IVOA standards)
   - TAP service integration (queryable via VO tools)
   - Documentation for external users
   - **Effort**: 4 days
   - **Rationale**: Community access, increased citations, multi-wavelength
     studies

2. **Testing and Validation**
   - End-to-end testing of all new features
   - Science validation (use on real observations)
   - Performance benchmarking
   - **Effort**: 3 days

3. **Final Documentation**
   - Comprehensive user guides
   - Science case examples
   - Publication-ready documentation
   - **Effort**: 2 days

**Total Effort**: ~9 days

**Key Outcomes**:

- VO-published DSA-110 source catalogs (discoverable worldwide)
- Science-ready products with types, redshifts, spectral indices
- Increased community engagement and citations

---

### Phase 5: Advanced Features (Months 9+)

**Goal**: Implement remaining specialized capabilities as needed

**Deliverables** (lower priority, implement based on science needs):

- **Multi-wavelength Classification** (Proposal #4)
  - Full classification pipeline with Gaia/SIMBAD/NED
  - Effort: 10 days

- **Proper Motion Corrections** (Proposal #7)
  - Epoch-correct all catalog positions
  - Effort: 2 days

- **Pulsar Timing Integration** (Proposal #9)
  - Use ATNF period/DM for predictions
  - Build pulsar light curve database
  - Effort: 10+ days

---

### Total Implementation Timeline

**Phase 1**: 8 days (Months 1-2)  
**Phase 2**: 9 days (Months 3-4)  
**Phase 3**: 11 days (Months 5-6)  
**Phase 4**: 9 days (Months 7-8)  
**Total Core Implementation**: ~37 days (~7.5 weeks of development)

**Milestones**:

- **Month 2**: Operational monitoring active, spectral indices computed
  automatically
- **Month 4**: Smart calibrator selection operational, 10× speedup achieved
- **Month 6**: Transient detection active with alerts, astrometric accuracy <1"
- **Month 8**: VO-published catalogs available to community

---

## Priority Ranking

### User-Prioritized Implementation Order

**Approved for Implementation** (in order):

1. **Flux Calibration Monitoring & Alerts** (#6) - PHASE 1
   - **Rationale**: Critical operational health monitoring
   - Effort: 3 days
   - **Value**: Early detection of calibration issues, data quality assurance
   - **Impact**: Reduced manual validation, improved reliability

2. **Spectral Index Mapping** (#1) - PHASE 1
   - **Rationale**: Low effort, high science value, foundational
   - Effort: 3 days
   - **Value**: Source classification, better calibrator selection
   - **Impact**: Enables advanced catalog features, science publications

3. **Coverage-Aware Catalog Selection** (#8) - PHASE 2
   - **Rationale**: Optimize catalog usage, improve cross-match quality
   - Effort: 4 days
   - **Value**: Automatic optimal catalog selection
   - **Impact**: Better results, fewer failed queries

4. **Smart Calibrator Pre-Selection** (#3) - PHASE 2
   - **Rationale**: 10× speedup, improved calibration reliability
   - Effort: 5 days
   - **Value**: Operational efficiency, quality improvement
   - **Impact**: Faster processing, fewer variable source issues

5. **Transient Detection** (#2) - PHASE 3
   - **Rationale**: Core DSA-110 science goal
   - Effort: 7 days
   - **Value**: Automated discovery of variable/transient sources
   - **Impact**: High-impact science, publications

6. **Astrometric Self-Calibration** (#5) - PHASE 3
   - **Rationale**: Improve positional accuracy for follow-up
   - Effort: 4 days
   - **Value**: Sub-arcsecond astrometry (2-3" → <1")
   - **Impact**: Better multi-wavelength associations

7. **Science-Ready Catalog Products** (#10) - PHASE 4
   - **Rationale**: Community access, increased impact
   - Effort: 4 days
   - **Value**: VO-published catalogs, external citations
   - **Impact**: Community engagement, broader science use

### Lower Priority (Future Implementation)

**Deferred to Phase 5+**:

8. **Multi-wavelength Classification** (#4)
   - High effort (10 days), requires external API access
   - Consider after Phase 4 completion

9. **Proper Motion Corrections** (#7)
   - Low effort (2 days) but specialized use case
   - Implement as needed for specific science cases

10. **Pulsar Timing Integration** (#9)
    - High effort (10+ days), highly specialized
    - Consider for dedicated pulsar studies

---

## Success Metrics

### Technical Metrics

- **Spectral Index**: 80% of multi-catalog matches have computed α
- **Transients**: <5% false positive rate on high-priority candidates
- **Calibrator Selection**: 10× speedup (30s → 3s)
- **Classification**: 70% of sources classified with confidence > 0.7
- **Flux Monitoring**: Alert within 1 hour of >20% flux drift

### Science Metrics

- **Publications**: ≥2 papers using enhanced catalog features
- **Transient Discoveries**: ≥5 confirmed transients per year
- **Catalog Products**: ≥1 VO-published catalog with external citations
- **Community Engagement**: ≥10 external researchers using DSA-110 catalogs

---

## Next Steps

### Immediate Actions (Week 1)

1. **Phase 1 Kickoff**: Flux Monitoring & Spectral Indices
   - Create feature branches: `feature/flux-monitoring`,
     `feature/spectral-index`
   - Set up database migrations for new tables
   - Assign developers to proposals #6 and #1

2. **Architecture Review**
   - Review database schemas with team
   - Validate integration points in pipeline
   - Confirm API endpoint designs

3. **Development Environment Setup**
   - Ensure test data available for validation
   - Set up CI/CD for new features
   - Create test suites for each proposal

### Phase 1 Implementation (Months 1-2)

**Week 1-2**: Flux Calibration Monitoring

- Database schema implementation
- Trending calculation functions
- Basic alert system (logging)
- Testing with historical data

**Week 3-4**: Spectral Index Mapping

- Database schema implementation
- Calculation functions (multi-frequency)
- Pipeline integration in `CrossMatchStage`
- API endpoint implementation
- Testing with NVSS/VLASS/RACS matches

**Week 5-6**: Testing & Documentation

- End-to-end testing
- Dashboard integration
- User documentation
- Operations runbooks

**Deliverable**: Operational flux monitoring + automatic spectral index
calculations

### Phase 2 Implementation (Months 3-4)

**Week 1-2**: Coverage-Aware Catalog Selection

- Generate coverage maps
- Implement recommendation engine
- Integrate with query functions
- Testing across declination range

**Week 3-5**: Smart Calibrator Registry

- Build registry for all declination strips
- Blacklist generation (ATNF pulsars, blazars)
- Integration with calibration pipeline
- Performance benchmarking (verify 10× speedup)

**Week 6**: Testing & Documentation

- End-to-end testing
- Performance validation
- Documentation updates

**Deliverable**: Optimized catalog queries + fast calibrator selection

### Phase 3 Implementation (Months 5-6)

**Week 1-4**: Transient Detection

- Database schema
- Detection algorithm implementation
- Pipeline stage integration
- Alert system (Slack/email webhooks)
- API endpoints
- Dashboard integration
- Testing with simulated transients

**Week 5-6**: Astrometric Self-Calibration

- Offset calculation from FIRST
- WCS correction functions
- Mosaic integration
- Testing and validation

**Deliverable**: Automated transient detection + improved astrometry

### Phase 4 Implementation (Months 7-8)

**Week 1-3**: VO Catalog Products

- FITS export functions
- VO metadata generation (IVOA compliant)
- TAP service integration
- VO registry submission
- External user documentation

**Week 4**: Final Testing & Validation

- Science validation with real observations
- Performance benchmarking
- Community beta testing

**Deliverable**: VO-published catalogs accessible to community

### Success Criteria

**Phase 1 Complete When**:

- ✅ Flux monitoring dashboard shows real-time trends
- ✅ Alerts triggered for >20% flux scale drift
- ✅ 80%+ of multi-catalog matches have spectral indices
- ✅ All tests passing

**Phase 2 Complete When**:

- ✅ Catalog selection automatic based on coverage
- ✅ Calibrator selection <5s (down from 30s)
- ✅ Variable sources blacklisted from calibrator pool
- ✅ All tests passing

**Phase 3 Complete When**:

- ✅ Transient candidates automatically flagged
- ✅ High-priority alerts sent within 1 hour
- ✅ Astrometric accuracy <1" RMS (FIRST-limited)
- ✅ All tests passing

**Phase 4 Complete When**:

- ✅ DSA-110 catalogs published in VO registry
- ✅ External researchers can query via TAP
- ✅ Documentation complete for community use
- ✅ All tests passing

### Risk Management

**Potential Risks**:

1. **External API dependencies** (Gaia, SIMBAD, NED)
   - Mitigation: Cache results, implement timeouts, graceful degradation

2. **Database performance** (large cross-match tables)
   - Mitigation: Proper indexing, query optimization, archival strategy

3. **Alert fatigue** (too many transient candidates)
   - Mitigation: Tune detection thresholds, implement confidence scoring

4. **Catalog registry staleness** (ATNF updates)
   - Mitigation: Automated monthly rebuilds, version tracking

### Resource Requirements

**Development**:

- 1-2 developers for ~8 weeks (Phases 1-4)
- Part-time for Phase 5+ (as needed)

**Infrastructure**:

- Additional database storage: ~500 MB (spectral indices, transients,
  monitoring)
- Calibrator registry: ~100 MB
- VO catalog products: ~1 GB per major data release

**Testing**:

- Test data sets at multiple declinations
- Historical observations for validation
- Simulated transients for detection testing

---

## References

- **Catalog Documentation**: `src/dsa110_contimg/catalog/CATALOG_OVERVIEW.md`
- **ATNF Usage**: `src/dsa110_contimg/catalog/ATNF_USAGE.md`
- **Cross-matching**: `src/dsa110_contimg/catalog/crossmatch.py`
- **Pipeline Stages**: `src/dsa110_contimg/pipeline/stages_impl.py`

---

## Document History

- **v1.0** (2025-11-19): Initial proposals based on catalog system review
