# ASKAP Continuum Validation Assessment

## Executive Summary

This document assesses the ASKAP-continuum-validation repository (https://github.com/Jordatious/ASKAP-continuum-validation) for potential integration into the DSA-110 continuum imaging pipeline. The ASKAP validation script generates HTML reports summarizing validation tests for astrometry, flux scale, and source counts.

**Key Finding**: DSA-110 already has substantial catalog validation functionality, but ASKAP's HTML report generation and structured validation framework could enhance our QA capabilities.

---

## 1. ASKAP Validation Overview

### 1.1 Core Functionality

The ASKAP validation script:
- **Input**: ASKAP continuum image (FITS)
- **Output**: HTML validation report
- **Validation Tests**:
  1. **Astrometry**: Cross-matches sources with NVSS/SUMSS, reports positional offsets
  2. **Flux Scale**: Compares measured fluxes with reference catalogues
  3. **Source Counts**: Evaluates completeness and reliability vs. flux density

### 1.2 Key Features

- **HTML Report Generation**: Comprehensive, web-viewable reports with tables and plots
- **Automated Integration**: Runs within ASKAPsoft pipeline after source extraction
- **Configurable**: Uses config files for catalogues, filters, and thresholds
- **CASDA Integration**: Reports uploaded to CSIRO ASKAP Science Data Archive

### 1.3 Technical Implementation

- Python-based script
- Cross-matches with NVSS/SUMSS catalogues
- Applies quality filters (flux density, SNR thresholds)
- Generates diagnostic plots and metrics
- HTML output for easy review

---

## 2. DSA-110 Current Validation Capabilities

### 2.1 Existing Validation Modules

**Catalog Validation** (`qa/catalog_validation.py`):
- ✅ **Astrometry validation**: `validate_astrometry()`
  - Cross-matches detected sources with NVSS/VLASS
  - Calculates mean/RMS/max offsets
  - Reports RA/Dec offsets separately
  - Quality flags (issues/warnings)

- ✅ **Flux scale validation**: `validate_flux_scale()`
  - Uses forced photometry at catalog positions
  - Flux ratio analysis
  - Spectral index scaling support
  - Flux range filtering

- ✅ **Source extraction**: `extract_sources_from_image()`
  - Simple threshold-based detection
  - Local maxima finding
  - SNR-based filtering

**MS Quality Assurance** (`qa/casa_ms_qa.py`):
- ✅ Structural validation
- ✅ Flagging summaries
- ✅ Visibility statistics
- ✅ Calibration dry-run
- ✅ Imaging smoke test
- ✅ Markdown report generation (`write_report()`)

**Calibration Quality** (`qa/calibration_quality.py`):
- ✅ Caltable SNR analysis
- ✅ Solution stability metrics
- ✅ Antenna coverage validation

**Image Quality** (`qa/image_quality.py`):
- ✅ Beam shape analysis
- ✅ Noise estimation
- ✅ Dynamic range calculation

### 2.2 Current Reporting

- **Markdown reports**: `qa/casa_ms_qa.py::write_report()` generates `.md` files
- **API endpoints**: `/api/qa/images/{image_id}/catalog-validation`
- **JSON metrics**: Structured data via `CatalogValidationResult` dataclass
- **Diagnostic plots**: Via `qa/fast_plots.py` and `qa/plotting.py`

### 2.3 Gaps Identified

1. **No HTML report generation**: Only Markdown reports exist
2. **No comprehensive validation report**: Tests are separate, not unified
3. **No pass/fail summary**: Missing overall assessment framework
4. **Limited visualization**: Diagnostic plots exist but not integrated into reports
5. **No source counts completeness analysis**: Missing detailed completeness metrics

---

## 3. Comparison: ASKAP vs DSA-110

| Feature | ASKAP | DSA-110 | Gap |
|---------|-------|---------|-----|
| **Astrometry Validation** | ✅ Cross-match with NVSS/SUMSS | ✅ Cross-match with NVSS/VLASS | None |
| **Flux Scale Validation** | ✅ Flux ratio comparison | ✅ Forced photometry + flux ratios | None |
| **Source Counts** | ✅ Completeness analysis | ⚠️ Basic source extraction | **Missing completeness metrics** |
| **HTML Reports** | ✅ Comprehensive HTML | ❌ Only Markdown | **Missing HTML generation** |
| **Pass/Fail Framework** | ✅ Overall assessment | ⚠️ Individual test results | **Missing unified framework** |
| **Visualization** | ✅ Integrated plots | ✅ Separate plots | **Not integrated into reports** |
| **Configuration** | ✅ Config files | ⚠️ Hard-coded defaults | **Could use config files** |
| **Automation** | ✅ Pipeline integration | ✅ API + pipeline hooks | None |

---

## 4. Recommended Integrations

### 4.1 High Priority: HTML Report Generation

**What to Borrow**:
- HTML report template structure
- Pass/fail visualization (color-coded sections)
- Integrated plots and tables
- Summary dashboard format

**Implementation Approach**:
```python
# New module: qa/html_reports.py
def generate_validation_html_report(
    image_path: str,
    astrometry_result: CatalogValidationResult,
    flux_scale_result: CatalogValidationResult,
    source_counts_result: Optional[CatalogValidationResult] = None,
    output_path: Optional[str] = None
) -> str:
    """Generate comprehensive HTML validation report."""
    # Template-based HTML generation
    # Include plots, tables, pass/fail indicators
    # Similar structure to ASKAP but adapted for DSA-110
```

**Benefits**:
- Web-viewable reports for easy sharing
- Professional presentation for data releases
- Better visualization than Markdown
- Can be served via API or static files

**Integration Points**:
- Extend `qa/catalog_validation.py` with HTML output option
- Add API endpoint: `/api/qa/images/{image_id}/validation-report.html`
- Integrate into imaging stage for automatic report generation

### 4.2 Medium Priority: Source Counts Completeness Analysis

**What to Borrow**:
- Completeness limit calculation (e.g., 95% completeness at ~3 mJy)
- Source count statistics vs. flux density
- Reliability metrics

**Implementation Approach**:
```python
# Enhance qa/catalog_validation.py
def validate_source_counts(
    image_path: str,
    catalog: str = "nvss",
    completeness_threshold: float = 0.95
) -> CatalogValidationResult:
    """Analyze source counts completeness.
    
    Calculates:
    - Completeness limit (flux density at which completeness drops below threshold)
    - Source count statistics vs. flux bins
    - Comparison with expected counts from catalog
    """
    # Extract sources from image
    # Bin by flux density
    # Calculate completeness fraction per bin
    # Compare with catalog expectations
    # Report completeness limit
```

**Benefits**:
- Quantitative completeness assessment
- Better understanding of detection limits
- Standard metric for survey validation

**Integration Points**:
- Add to `qa/catalog_validation.py`
- Include in HTML report
- Add to API endpoints

### 4.3 Medium Priority: Unified Validation Framework

**What to Borrow**:
- Overall pass/fail assessment
- Weighted scoring system
- Threshold-based decision making

**Implementation Approach**:
```python
# New module: qa/validation_framework.py
@dataclass
class ValidationReport:
    """Unified validation report combining all tests."""
    image_path: str
    astrometry: CatalogValidationResult
    flux_scale: CatalogValidationResult
    source_counts: Optional[CatalogValidationResult]
    
    # Overall assessment
    overall_status: str  # "PASS", "FAIL", "WARNING"
    score: float  # 0.0 to 1.0
    issues: List[str]
    warnings: List[str]
    
    def to_html(self) -> str:
        """Generate HTML report."""
        ...
    
    def to_json(self) -> Dict:
        """Export as JSON."""
        ...
```

**Benefits**:
- Single unified report instead of separate tests
- Clear pass/fail decision
- Weighted scoring for nuanced assessment
- Better integration with pipeline (can fail pipeline stage)

**Integration Points**:
- Create new validation orchestrator
- Integrate into imaging stage
- Add to API as unified endpoint

### 4.4 Low Priority: Configuration Files

**What to Borrow**:
- Config file format for validation parameters
- Catalogue selection via config
- Threshold customization

**Implementation Approach**:
```python
# New: config/validation_config.yaml
validation:
  astrometry:
    max_offset_arcsec: 5.0
    search_radius_arcsec: 10.0
    min_snr: 5.0
  
  flux_scale:
    max_flux_ratio_error: 0.2
    flux_range_jy: [0.01, 10.0]
    spectral_index: -0.7
  
  source_counts:
    completeness_threshold: 0.95
    min_flux_jy: 0.001
  
  catalogues:
    default: "nvss"
    available: ["nvss", "vlass", "sumss"]
```

**Benefits**:
- Easier customization without code changes
- Per-survey configuration
- Better reproducibility

**Integration Points**:
- Extend `pipeline/config.py` with validation config
- Load from YAML or environment variables
- Use in validation functions

### 4.5 Low Priority: Enhanced Visualization

**What to Borrow**:
- Integrated plot generation in HTML
- Diagnostic plots for each validation test
- Interactive visualizations (if using JavaScript)

**Implementation Approach**:
- Use matplotlib/plotly for plot generation
- Embed plots as base64-encoded images in HTML
- Or use static plot files referenced in HTML
- Consider Plotly for interactive plots (optional)

**Benefits**:
- Better visual assessment
- Integrated reports (plots + tables)
- Professional presentation

**Integration Points**:
- Enhance `qa/plotting.py` with HTML embedding
- Integrate into HTML report generation
- Add to API endpoints

---

## 5. Implementation Plan

### Phase 1: HTML Report Generation (2-3 weeks)

1. **Create HTML template system**:
   - Design HTML template with DSA-110 branding
   - Include sections for astrometry, flux scale, source counts
   - Add pass/fail indicators (color-coded)
   - Include summary dashboard

2. **Implement report generator**:
   - `qa/html_reports.py`: Core HTML generation
   - Template-based approach (Jinja2 or string formatting)
   - Embed plots as base64 or static files

3. **Integrate with existing validation**:
   - Extend `validate_astrometry()`, `validate_flux_scale()` to support HTML output
   - Create unified `generate_validation_report()` function
   - Add to imaging stage for automatic generation

4. **API integration**:
   - Add endpoint: `GET /api/qa/images/{image_id}/validation-report.html`
   - Return HTML directly or file path
   - Include in image QA endpoints

### Phase 2: Source Counts Completeness (1-2 weeks)

1. **Implement completeness analysis**:
   - Enhance `validate_source_counts()` in `qa/catalog_validation.py`
   - Calculate completeness limit
   - Bin sources by flux density
   - Compare with catalog expectations

2. **Add to HTML report**:
   - Include completeness plot
   - Report completeness limit
   - Add to summary dashboard

3. **Integration**:
   - Add to unified validation framework
   - Include in API endpoints

### Phase 3: Unified Validation Framework (1-2 weeks)

1. **Create validation orchestrator**:
   - `qa/validation_framework.py`: Unified report class
   - Run all validation tests
   - Calculate overall score
   - Generate pass/fail decision

2. **Integrate with pipeline**:
   - Add validation stage to imaging workflow
   - Fail pipeline if validation fails (configurable)
   - Store reports in products database

3. **API integration**:
   - Unified endpoint: `GET /api/qa/images/{image_id}/validation`
   - Returns complete validation report (JSON + HTML)

### Phase 4: Configuration and Polish (1 week)

1. **Add configuration support**:
   - Extend `pipeline/config.py` with validation config
   - Support YAML config files
   - Environment variable overrides

2. **Enhanced visualization**:
   - Improve plot quality
   - Add more diagnostic plots
   - Consider interactive plots (optional)

3. **Documentation**:
   - Update API documentation
   - Add validation guide
   - Example reports

---

## 6. Code Structure Recommendations

### 6.1 New Modules

```
qa/
├── html_reports.py          # HTML report generation
├── validation_framework.py  # Unified validation orchestrator
├── completeness.py          # Source counts completeness analysis (if separate)
└── templates/              # HTML templates (if using Jinja2)
    └── validation_report.html
```

### 6.2 Enhanced Modules

```
qa/
├── catalog_validation.py    # Add HTML output, completeness analysis
└── image_quality.py        # Add HTML report integration
```

### 6.3 Configuration

```
config/
└── validation_config.yaml   # Validation parameters
```

---

## 7. Dependencies to Add

**For HTML Generation**:
- `Jinja2` (optional, for templating) OR
- Built-in string formatting (simpler, no new dependency)

**For Enhanced Visualization**:
- `plotly` (optional, for interactive plots)
- `matplotlib` (already used)

**No new critical dependencies required** - can use existing libraries.

---

## 8. Compatibility Considerations

### 8.1 ASKAP vs DSA-110 Differences

**Catalogue Differences**:
- ASKAP uses NVSS/SUMSS
- DSA-110 uses NVSS/VLASS
- **Solution**: DSA-110 already supports multiple catalogues via `catalog/query.py`

**Image Format**:
- Both use FITS format
- **Compatible**: No changes needed

**Frequency Ranges**:
- ASKAP: ~700-1800 MHz
- DSA-110: ~1311-1499 MHz
- **Solution**: Spectral index scaling already implemented

**Source Finding**:
- ASKAP: Uses selavy (ASKAPsoft)
- DSA-110: Simple threshold-based extraction
- **Solution**: Can enhance with PyBDSF if needed, but current approach sufficient

### 8.2 Integration Challenges

**Low Risk**:
- HTML generation is straightforward
- Validation logic is similar
- Catalogue access already implemented

**Medium Risk**:
- Completeness analysis requires careful binning and statistics
- Need to validate against DSA-110 data characteristics

**Mitigation**:
- Start with HTML reports (low risk)
- Test completeness analysis on sample data
- Iterate based on results

---

## 9. Benefits Summary

### 9.1 Immediate Benefits

1. **Professional HTML Reports**: Web-viewable validation reports
2. **Better Visualization**: Integrated plots and tables
3. **Unified Framework**: Single validation report instead of separate tests
4. **Pass/Fail Clarity**: Clear overall assessment

### 9.2 Long-term Benefits

1. **Data Release Readiness**: Professional reports for public data releases
2. **Automated QA**: Integrated into pipeline for automatic validation
3. **Better Monitoring**: HTML reports accessible via API/web interface
4. **Standardization**: Aligns with ASKAP best practices

### 9.3 Scientific Benefits

1. **Completeness Metrics**: Quantitative assessment of detection limits
2. **Better Flux Scale Validation**: More comprehensive analysis
3. **Astrometry Verification**: Enhanced positional accuracy checks
4. **Survey Quality**: Standard metrics for survey validation

---

## 10. Recommendations

### 10.1 Priority Actions

1. **✅ Implement HTML Report Generation** (High Priority)
   - Most visible improvement
   - Relatively straightforward
   - Immediate value

2. **✅ Add Source Counts Completeness** (Medium Priority)
   - Fills gap in current validation
   - Important for survey validation
   - Moderate complexity

3. **✅ Create Unified Validation Framework** (Medium Priority)
   - Better organization
   - Easier integration
   - Professional presentation

4. **⚠️ Configuration Files** (Low Priority)
   - Nice to have
   - Can be added later
   - Not critical for initial implementation

### 10.2 Implementation Strategy

**Start Small**:
1. Begin with HTML report generation for existing validation tests
2. Add completeness analysis incrementally
3. Build unified framework on top of working components

**Iterate**:
- Test on sample DSA-110 images
- Gather feedback from users
- Refine based on real-world usage

**Maintain Compatibility**:
- Keep existing API endpoints
- Add new endpoints alongside old ones
- Don't break existing functionality

---

## 11. Conclusion

The ASKAP continuum validation repository provides valuable patterns and approaches that can enhance DSA-110's validation capabilities. While DSA-110 already has strong validation functionality, ASKAP's HTML report generation and unified framework would significantly improve the user experience and professional presentation of validation results.

**Key Takeaways**:
- ✅ DSA-110 has solid validation foundation
- ✅ HTML reports would be valuable addition
- ✅ Completeness analysis fills current gap
- ✅ Unified framework improves organization
- ✅ Low risk, high value improvements

**Recommended Next Steps**:
1. Review ASKAP repository code structure (if accessible)
2. Implement HTML report generation (Phase 1)
3. Add completeness analysis (Phase 2)
4. Build unified framework (Phase 3)
5. Iterate based on feedback

The integration would enhance DSA-110's QA capabilities while maintaining compatibility with existing systems and following established best practices from the radio astronomy community.

