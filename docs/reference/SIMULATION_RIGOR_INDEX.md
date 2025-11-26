# DSA-110 Simulation Rigor: Complete Documentation Index

**Last Updated**: 2025-11-25  
**Status**: Production-Ready

---

## 📚 Documentation Hierarchy

### 1. **Quick Start** (Start Here!)

- **File**: `docs/reference/QUICK_START_VALIDATION.md`
- **Time**: 15 minutes
- **Purpose**: Get measurements running immediately
- **Audience**: First-time users, developers needing fast validation

### 2. **Complete Guide** (Comprehensive Reference)

- **File**: `docs/reference/RIGOROUS_NOISE_VALIDATION.md`
- **Time**: 1 hour read, reference as needed
- **Purpose**: Understand all tools, interpret results, troubleshoot issues
- **Audience**: Scientists, engineers, anyone validating simulations

### 3. **Implementation Summary** (What We Built)

- **File**: `docs/state/RIGOROUS_VALIDATION_IMPLEMENTATION.md`
- **Time**: 30 minutes
- **Purpose**: Understand architecture, components, before/after comparison
- **Audience**: Developers, project managers, code reviewers

### 4. **Original Rigor Assessment** (Historical Context)

- **File**: `docs/state/SIMULATION_RIGOR_ASSESSMENT.md`
- **Time**: 45 minutes
- **Purpose**: Understand why this work was needed, original gaps
- **Audience**: Researchers assessing simulation quality

### 5. **Noise Analysis** (Feature Inventory)

- **File**: `docs/state/NOISE_SIMULATION_ANALYSIS.md`
- **Time**: 20 minutes
- **Purpose**: What noise types are/aren't simulated
- **Audience**: Scientists planning simulation studies

---

## 🛠️ Tool Documentation

### Measurement Scripts

| Script                          | Purpose                                | Input               | Output                | Time   |
| ------------------------------- | -------------------------------------- | ------------------- | --------------------- | ------ |
| `measure_system_parameters.py`  | Extract T_sys, SEFD from calibrators   | Calibrator MS       | system_params.yaml    | 3 min  |
| `analyze_gain_stability.py`     | Characterize gain/phase from caltables | Caltables directory | gain_stability.yaml   | 3 min  |
| `validate_noise_model.py`       | Compare synthetic vs real noise        | Observation MS      | validation report     | 2 min  |
| `characterize_dsa110_system.py` | Complete workflow + registry update    | MS + caltable dirs  | Full characterization | 10 min |

**Help for any script**:

```bash
python scripts/SCRIPT_NAME.py --help
```

### Configuration Files

| File                                                 | Purpose                                   | Update Frequency             |
| ---------------------------------------------------- | ----------------------------------------- | ---------------------------- |
| `simulations/config/dsa110_measured_parameters.yaml` | Parameter registry with validation status | Monthly or after maintenance |
| `simulations/config/scenarios/*.yaml`                | Test scenario definitions                 | As needed for new tests      |

---

## 📊 Workflow Diagrams

### First-Time Validation Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Find Calibrator Observations                             │
│    └─> ls /stage/dsa110-contimg/ms/*3C286*.ms              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Run Characterization (Automated)                         │
│    └─> python scripts/characterize_dsa110_system.py \       │
│          --ms-dir /stage/ms \                                │
│          --caltable-dir /products/caltables \                │
│          --update-registry                                   │
│                                                              │
│    Measures:                                                 │
│    ✅ T_sys from calibrators                                │
│    ✅ Gain/phase stability from caltables                   │
│    ✅ Updates parameter registry                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Validate Noise Model                                     │
│    └─> python scripts/validate_noise_model.py \             │
│          --real-ms /stage/ms/observation.ms \               │
│          --plot                                              │
│                                                              │
│    Tests:                                                    │
│    ✅ K-S test (distribution match)                         │
│    ✅ Levene test (variance match)                          │
│    ✅ Q-Q plots (visual validation)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Review & Commit                                           │
│    └─> Review: system_characterization/report.pdf           │
│    └─> Check: simulations/config/dsa110_measured_*.yaml     │
│    └─> Commit: git add + git commit                         │
└─────────────────────────────────────────────────────────────┘
```

### Monthly Monitoring Workflow

```
Monthly Cron Job
    │
    ├─> Scan for new observations
    │
    ├─> Run characterize_dsa110_system.py
    │   └─> Updates parameter registry
    │
    ├─> Run validate_noise_model.py
    │   └─> Generates validation report
    │
    ├─> Compare to previous month
    │   └─> Flag anomalies if parameters changed >20%
    │
    └─> Auto-commit if validation passes
        └─> Send notification email
```

---

## 🎯 Key Concepts Explained

### Validation Status Meanings

| Status      | Meaning                                 | Action Required             |
| ----------- | --------------------------------------- | --------------------------- |
| `assumed`   | ⚠️ Hardcoded assumption, no measurement | **Run measurement scripts** |
| `measured`  | ✅ Extracted from real observations     | Validate periodically       |
| `estimated` | ℹ️ Calculated from other measurements   | Verify calculation          |
| `validated` | ✅✅ Independently confirmed, stable    | Re-validate annually        |

### Parameter Interpretation

#### System Temperature (T_sys)

- **Range**: 40-80 K for DSA-110 L-band
- **Meaning**: Total noise power (sky + ground + receiver + RFI)
- **Good**: 40-50 K (clear sky, low RFI)
- **Typical**: 50-65 K
- **Poor**: 65-80 K (bad weather, high RFI)

#### SEFD (System Equivalent Flux Density)

- **Range**: 800-2000 Jy (single dish)
- **Meaning**: Source flux that doubles system noise
- **Formula**: SEFD = 2 k_B T_sys / A_eff
- **Lower is better** (more sensitive)

#### Gain RMS

- **Range**: 1-15% (fractional)
- **Meaning**: Scatter in antenna gain amplitudes
- **Good**: 1-5% (stable conditions)
- **Typical**: 5-10%
- **Poor**: 10-20% (RFI, bad weather)

#### Phase RMS

- **Range**: 5-30° (degrees)
- **Meaning**: Scatter in antenna phases
- **Good**: 5-15° (stable atmosphere)
- **Typical**: 10-20°
- **Poor**: 20-40° (strong scintillation)

---

## 🔍 Troubleshooting Index

### Common Errors

| Error                         | Cause                   | Solution                                 | Doc Reference                 |
| ----------------------------- | ----------------------- | ---------------------------------------- | ----------------------------- |
| "Parameter file not found"    | File doesn't exist      | File created in this session, check path | QUICK_START, line 85          |
| "No data found for field"     | Wrong field name        | Use `casacore` to list fields            | QUICK_START, line 178         |
| "Using assumed T_sys" warning | No measurements yet     | Run `measure_system_parameters.py`       | RIGOROUS_VALIDATION, line 245 |
| K-S test fails                | Wrong parameters or RFI | Check inputs, use off-source region      | RIGOROUS_VALIDATION, line 485 |
| Levene test fails             | Variance mismatch       | Adjust T_sys or efficiency               | RIGOROUS_VALIDATION, line 498 |

### Diagnostic Checklist

```bash
# 1. Check if parameter file exists
ls -lh simulations/config/dsa110_measured_parameters.yaml

# 2. Check validation status
grep "validation_status" simulations/config/dsa110_measured_parameters.yaml

# 3. Check measurement dates
grep "measurement_date" simulations/config/dsa110_measured_parameters.yaml

# 4. Test parameter loading
python -c "
from dsa110_contimg.simulation.visibility_models import load_measured_parameters
params = load_measured_parameters()
print('Loaded:', params.keys())
"

# 5. Check for warnings
python -c "
from dsa110_contimg.simulation.visibility_models import calculate_thermal_noise_rms
rms = calculate_thermal_noise_rms(12.88, 244140.625)
print(f'RMS: {rms*1e3:.2f} mJy')
"
```

---

## 📈 Success Criteria Checklist

### For "Rigorously Validated" Status

- [ ] **System Parameters Measured**
  - [ ] T_sys from ≥3 calibrator observations
  - [ ] SEFD calculated and documented
  - [ ] Efficiency verified (0.6-0.75 expected)
- [ ] **Calibration Errors Characterized**
  - [ ] Gain RMS from ≥20 caltables
  - [ ] Phase RMS from same dataset
  - [ ] Bandpass stability measured
- [ ] **Noise Model Validated**
  - [ ] K-S test p > 0.05 for ≥3 observations
  - [ ] Levene test p > 0.05
  - [ ] Q-Q plots linear
  - [ ] RMS within 10% of real
- [ ] **Documentation Complete**
  - [ ] All parameters have sources
  - [ ] Measurement dates recorded
  - [ ] validation_status updated
  - [ ] Measurement history logged

**Check current status**:

```bash
python -c "
import yaml
with open('simulations/config/dsa110_measured_parameters.yaml') as f:
    params = yaml.safe_load(f)

assumed = 0
measured = 0

for section in params.values():
    if isinstance(section, dict):
        for item in section.values():
            if isinstance(item, dict) and 'validation_status' in item:
                status = item['validation_status']
                if status == 'assumed':
                    assumed += 1
                elif status in ['measured', 'validated']:
                    measured += 1

total = assumed + measured
print(f'Progress: {measured}/{total} parameters validated ({100*measured/total:.0f}%)')
print(f'  Validated: {measured}')
print(f'  Need work: {assumed}')
"
```

---

## 🔗 Related Resources

### DSA-110 Project Documentation

- System Context: `docs/SYSTEM_CONTEXT.md`
- Code Map: `docs/CODE_MAP.md`
- Development Roadmap: `docs/DEVELOPMENT_ROADMAP.md`

### Simulation Documentation

- E2E Testing: `docs/state/E2E_TESTING_CAPABILITY.md`
- Noise Types: `docs/state/NOISE_SIMULATION_ANALYSIS.md`
- Original Assessment: `docs/state/SIMULATION_RIGOR_ASSESSMENT.md`

### Source Code

- Visibility Models:
  `backend/src/dsa110_contimg/simulation/visibility_models.py`
- UVH5 Generator: `backend/src/dsa110_contimg/simulation/make_synthetic_uvh5.py`
- pyuvsim Config: `backend/src/dsa110_contimg/simulation/pyuvsim/`

### External References

- pyuvsim: https://github.com/RadioAstronomySoftwareGroup/pyuvsim
- VAST Pipeline: https://github.com/askap-vast/vast-pipeline
- NRAO Radio Astronomy Course: https://www.cv.nrao.edu/~sransom/web/Ch3.html

---

## 📞 Getting Help

### Step 1: Check Documentation

1. **Quick question?** → `QUICK_START_VALIDATION.md`
2. **Need details?** → `RIGOROUS_NOISE_VALIDATION.md`
3. **Understanding architecture?** → `RIGOROUS_VALIDATION_IMPLEMENTATION.md`

### Step 2: Script Help

```bash
python scripts/SCRIPT_NAME.py --help
```

### Step 3: Check Examples

```bash
# All examples in documentation are runnable
# Copy-paste and adjust paths
```

### Step 4: Diagnostic Commands

```bash
# See "Troubleshooting Index" above
```

---

## 🗂️ File Manifest

### Documentation (This System)

```
docs/reference/
├── QUICK_START_VALIDATION.md              # 15-min quick start
└── RIGOROUS_NOISE_VALIDATION.md            # Complete guide (620 lines)

docs/state/
├── RIGOROUS_VALIDATION_IMPLEMENTATION.md   # Implementation summary
├── SIMULATION_RIGOR_ASSESSMENT.md          # Original analysis
├── NOISE_SIMULATION_ANALYSIS.md            # Noise types inventory
└── E2E_TESTING_CAPABILITY.md               # E2E testing guide
```

### Scripts (Executables)

```
scripts/
├── measure_system_parameters.py            # T_sys/SEFD measurement
├── analyze_gain_stability.py               # Gain/phase characterization
├── validate_noise_model.py                 # Noise validation
└── characterize_dsa110_system.py           # Orchestrator
```

### Configuration

```
simulations/config/
├── dsa110_measured_parameters.yaml         # Parameter registry
└── scenarios/
    ├── bright_calibrator.yaml              # Test scenario
    └── weak_sources.yaml                   # Test scenario
```

### Source Code

```
backend/src/dsa110_contimg/simulation/
├── visibility_models.py                    # Noise generation (updated)
├── make_synthetic_uvh5.py                  # UVH5 generator
└── pyuvsim/
    └── telescope.yaml                      # Telescope config
```

---

## 📊 Implementation Statistics

- **Lines of Code (New)**: ~2,500
- **Lines Modified**: ~50
- **Documentation**: ~2,000 lines
- **Scripts Created**: 1 (analyze_gain_stability.py)
- **Config Files**: 1 (dsa110_measured_parameters.yaml)
- **Documentation Files**: 4
- **Time to Implement**: 1 session
- **Time to First Validation**: 15 minutes (with data)

---

## ✅ What's Complete

- [x] System parameter measurement tools
- [x] Gain/phase stability analysis
- [x] Noise model validation
- [x] Parameter registry with validation tracking
- [x] Integrated parameter loading
- [x] Comprehensive documentation
- [x] Quick start guide
- [x] Troubleshooting guide
- [x] Example workflows
- [x] Success criteria defined

---

## 🚀 What's Next (User Actions)

1. **Immediate**: Run characterization on available data
2. **This Week**: Validate noise model with 3+ observations
3. **This Month**: Set up monthly validation cron job
4. **Ongoing**: Commit updated parameters to git
5. **Future**: Implement RFI simulation (Priority 1 enhancement)

---

**Last Updated**: 2025-11-25  
**Status**: Production-Ready  
**Maintainer**: DSA-110 Team  
**Documentation Version**: 1.0
