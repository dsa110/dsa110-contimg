# External Tools Evaluation Framework

**Purpose**: Systematic evaluation of external software tools for potential integration into `dsa110-contimg`

---

## Evaluation Criteria

### 1. **Functional Fit**
- Does it solve a specific problem we have?
- Does it complement or replace existing functionality?
- Is it designed for similar use cases (radio astronomy, interferometry)?

### 2. **Technical Compatibility**
- Python compatibility (version, dependencies)
- CASA compatibility
- Integration complexity (API, CLI, library)
- Performance characteristics

### 3. **Maintenance & Support**
- Active development?
- Community support?
- Documentation quality?
- License compatibility (MIT, Apache, GPL, etc.)

### 4. **Integration Strategy**
- **Algorithm borrowing**: Extract specific algorithms/methods
- **Library integration**: Use as dependency
- **Tool repurposing**: Adapt for our use case
- **Inspiration**: Learn from design patterns

### 5. **Risk Assessment**
- Maintenance burden
- Breaking changes risk
- Vendor lock-in concerns
- Migration complexity

---

## Tools Under Evaluation

### 1. RadioPadre ⭐ **HIGH PRIORITY**

**What it is**: Jupyter notebook framework for radio astronomy visualization with JS9 and CARTA integration

**Key Features**:
- Custom Jupyter kernel for radio astronomy
- JS9 integration (FITS viewing in browser)
- CARTA integration (remote FITS viewing)
- Automated reporting from pipeline outputs
- Designed for remote cluster workflows

**Potential Use Cases**:
1. **QA Visualization**: Replace/enhance current `qa/fast_plots.py` with interactive notebooks
2. **Pipeline Reports**: Automated QA reports from structured pipeline outputs
3. **Remote Visualization**: View FITS images over slow SSH connections
4. **Collaboration**: Share notebooks with explanatory text and visualizations

**Integration Strategy**:
- **Option A**: Library integration - Use RadioPadre notebooks for QA reports
- **Option B**: Tool repurposing - Adapt notebook templates for our pipeline structure
- **Option C**: Algorithm borrowing - Extract visualization patterns

**Pros**:
- Solves real problem (remote visualization)
- JS9/CARTA integration is valuable
- Designed for pipeline outputs
- Active development (RATT-RU)

**Cons**:
- Additional dependency
- May require client script setup
- Learning curve for team

**Recommendation**: **Evaluate for QA/visualization use case** - Could significantly improve QA workflow

---

### 2. ASKAP Continuum Validation

**What it is**: Catalog validation tools for comparing radio images against known catalogs

**Key Features**:
- Multi-catalog support (NVSS, FIRST, SUMSS, TGSS, VLSSr, etc.)
- Flux scale validation
- Source matching
- Configurable validation criteria

**Potential Use Cases**:
1. **Catalog Validation**: Enhance `qa/catalog_validation.py` with multi-catalog support
2. **Flux Scale Verification**: Compare our images against multiple reference catalogs
3. **Cross-survey Validation**: Validate against ASKAP, ATCA, etc.

**Integration Strategy**:
- **Option A**: Algorithm borrowing - Extract catalog matching logic
- **Option B**: Library integration - Use as standalone validation tool
- **Option C**: Inspiration - Learn validation patterns

**Pros**:
- Proven validation approach
- Multi-catalog support
- Configurable thresholds

**Cons**:
- May be ASKAP-specific
- Need to verify catalog formats match

**Recommendation**: **Review catalog matching algorithms** - Could improve our catalog validation

---

### 3. Codex Africanus

**What it is**: Radio astronomy building blocks library (SKA-SA project)

**Key Features**:
- Low-level radio astronomy algorithms
- Dask integration
- GPU support (CuPy)
- Gridding, degridding, calibration building blocks

**Potential Use Cases**:
1. **Algorithm Library**: Use gridding/degridding algorithms
2. **GPU Acceleration**: Leverage GPU support for performance
3. **Building Blocks**: Extract specific algorithms for our use cases

**Integration Strategy**:
- **Option A**: Algorithm borrowing - Extract specific algorithms
- **Option B**: Library integration - Use as dependency for specific operations
- **Option C**: Inspiration - Learn algorithm implementations

**Pros**:
- Well-tested algorithms
- GPU support
- Active development (SKA-SA)
- Good documentation

**Cons**:
- May be overkill for our needs
- Dask integration complexity
- Focus on SKA use cases

**Recommendation**: **Evaluate specific algorithms** - Could provide GPU-accelerated building blocks

---

### 4. WABIFAT ✅ **ALREADY IMPLEMENTED**

**What it is**: WSClean/Aegean integration for creating spectra and light curves

**Key Features**:
- Adaptive channel binning ✅ **IMPLEMENTED**
- Forced fitting with Aegean ✅ **IMPLEMENTED** (via `photometry/aegean_fitting.py`)
- Circular polarization fraction calculation (not yet implemented)
- Stokes I/V plotting (not yet implemented)

**Current Implementation Status**:
- ✅ **Adaptive Binning**: Fully implemented in `photometry/adaptive_binning.py`
  - Implements WABIFAT's adaptive binning algorithm
  - Integrated with photometry workflow (`photometry/adaptive_photometry.py`)
  - Pipeline stage support (`AdaptivePhotometryStage`)
  - CLI support (`photometry/cli.py`)
- ✅ **Aegean Integration**: Implemented in `photometry/aegean_fitting.py`
  - Follows WABIFAT approach for extended/blended sources
  - Forced fitting capabilities

**Remaining Potential Use Cases**:
1. **Circular Polarization**: Extract circular polarization fraction calculation
2. **Light Curves**: Create time-series plots for variable sources (may already exist)
3. **Spectra Plotting**: Generate frequency spectra visualization from adaptive binning results
4. **Stokes I/V Analysis**: Add Stokes parameter analysis

**Integration Strategy**:
- **Option A**: Algorithm borrowing - Extract circular polarization calculation
- **Option B**: Tool repurposing - Adapt plotting/visualization components
- **Option C**: Inspiration - Learn spectra/light curve generation patterns

**Pros**:
- Core algorithms already implemented
- Could enhance with visualization components
- Uses tools we already have (WSClean, Aegean)

**Cons**:
- Not user-friendly (per author)
- May need significant adaptation for visualization
- LOFAR-specific assumptions?

**Recommendation**: **Low priority** - Core functionality already implemented. Consider extracting visualization/plotting components if needed.

---

### 5. Stimela

**What it is**: Workflow management framework for radio interferometry pipelines

**Key Features**:
- Declarative workflow definitions
- Docker-based task execution
- Pipeline orchestration
- YAML-based configuration

**Potential Use Cases**:
1. **Workflow Inspiration**: Compare with our `pipeline/orchestrator.py`
2. **Docker Integration**: Learn Docker-based task execution patterns
3. **Configuration Patterns**: YAML-based pipeline configuration

**Integration Strategy**:
- **Option A**: Inspiration - Learn workflow patterns
- **Option B**: Algorithm borrowing - Extract configuration patterns
- **Option C**: Not applicable - We have our own pipeline framework

**Pros**:
- Proven workflow framework
- Docker integration
- Active development

**Cons**:
- We already have pipeline framework
- May be redundant
- Different execution model (Docker vs direct)

**Recommendation**: **Low priority** - Review for inspiration only, not integration

---

### 6. dask-ms

**What it is**: Dask-based Measurement Set processing

**Key Features**:
- Distributed MS processing
- Lazy evaluation
- Parallel I/O
- Chunked operations

**Potential Use Cases**:
1. **Distributed Processing**: Scale conversion/calibration across nodes
2. **Parallel I/O**: Improve MS reading/writing performance
3. **Chunked Operations**: Process large MS files in chunks

**Integration Strategy**:
- **Option A**: Library integration - Use for distributed MS operations
- **Option B**: Algorithm borrowing - Extract parallel I/O patterns
- **Option C**: Future consideration - For scaling needs

**Pros**:
- Distributed processing capability
- Proven for large datasets
- Active development

**Cons**:
- Current single-node architecture works
- Adds complexity
- May require significant refactoring

**Recommendation**: **Future consideration** - Evaluate when scaling becomes a bottleneck

---

### 7. Other Tools (Need Investigation)

**ragavi**: Radio astronomy visualization (need to check)
**shadeMS**: MS visualization/analysis (need to check)
**crystalball**: (need to check purpose)
**xarray-fits**: FITS file handling with xarray (could be useful for image analysis)

---

## Priority Assessment

### High Priority (Immediate Evaluation)

1. **RadioPadre**: QA visualization and reporting

### Already Implemented ✅

2. **WABIFAT**: Adaptive binning and Aegean integration already implemented
   - `photometry/adaptive_binning.py` - WABIFAT adaptive binning algorithm
   - `photometry/adaptive_photometry.py` - Integration with photometry workflow
   - `photometry/aegean_fitting.py` - WABIFAT-style forced fitting

### Medium Priority (Evaluate Soon)

3. **ASKAP Continuum Validation**: Catalog validation improvements
4. **Codex Africanus**: Algorithm library for specific needs

### Low Priority (Future Consideration)

5. **dask-ms**: Distributed processing (when needed)
6. **Stimela**: Workflow inspiration only

---

## Evaluation Process

### Phase 1: Quick Assessment (1-2 days per tool)
1. Read documentation
2. Check license compatibility
3. Assess technical compatibility
4. Identify specific use cases
5. Document integration options

### Phase 2: Proof of Concept (3-5 days per tool)
1. Install in test environment
2. Create minimal integration test
3. Evaluate performance
4. Assess integration complexity
5. Document findings

### Phase 3: Integration Decision
1. Review findings with team
2. Decide on integration strategy
3. Plan implementation
4. Create integration branch
5. Test thoroughly

---

## Integration Patterns

### Pattern 1: Algorithm Borrowing
- Extract specific algorithms/methods
- Adapt to our codebase style
- Minimal external dependencies
- **Example**: Catalog matching from ASKAP validation

### Pattern 2: Library Integration
- Add as dependency
- Wrap in our API
- Maintain compatibility
- **Example**: RadioPadre for visualization

### Pattern 3: Tool Repurposing
- Adapt tool for our use case
- May require significant modification
- Maintain upstream compatibility
- **Example**: WABIFAT for photometry

### Pattern 4: Inspiration Only
- Learn design patterns
- Implement similar functionality
- No direct integration
- **Example**: Stimela workflow patterns

---

## Next Steps

1. **Start with RadioPadre**: Evaluate for QA visualization
2. **Review WABIFAT**: Assess adaptive binning for photometry
3. **Investigate other tools**: Complete assessment of remaining tools
4. **Create integration branches**: Test integrations in isolation
5. **Document decisions**: Record what we adopt and why

---

## Questions to Answer

For each tool:
- [ ] What specific problem does it solve?
- [ ] How does it compare to our current approach?
- [ ] What's the integration complexity?
- [ ] What are the maintenance implications?
- [ ] What's the performance impact?
- [ ] What's the license compatibility?
- [ ] Is it actively maintained?

---

## Notes

- **Don't reinvent the wheel**: If a tool solves our problem well, use it
- **Maintain flexibility**: Prefer algorithms over full tool integration when possible
- **Consider maintenance**: Active projects are preferable
- **Test thoroughly**: Always evaluate in test environment first
- **Document decisions**: Record what we adopt and why

