# User Safeguards Proposal: Preventing First-Time User Mistakes

**Date:** 2025-11-05  
**Goal:** Prevent users from executing the pipeline in known-incorrect ways  
**Status:** Proposal for Implementation

---

## 🎯 **Critical Problems to Prevent**

### **1. Using `setjy` Without Rephasing (Edge Case)**
**Problem:** `setjy` → `ft()` → phase center bugs → incorrect MODEL_DATA  
**Current State:** Warnings only (lines 1835-1838), doesn't prevent execution  
**Impact:** Low (uncommon) but confusing when it happens

### **2. No Model Source Default**
**Problem:** `--model-source` is required but has no default  
**Current State:** Error if not provided (line 431-438)  
**Impact:** Users must know which model source to use

### **3. Missing Explicit Coordinates**
**Problem:** Without explicit coordinates, catalog model may fail or use wrong phase center  
**Current State:** Falls back to auto-fields, may silently use wrong approach  
**Impact:** Medium (works but may not be optimal)

### **4. Unclear Workflow Guidance**
**Problem:** No guidance on which parameters to use when  
**Current State:** Many parameters, unclear defaults  
**Impact:** High (users may choose wrong options)

---

## ✅ **Proposed Safeguards**

### **1. Make Catalog Model the Default (HIGH PRIORITY)**

**Change:**
```python
# Current (line 714):
pc.add_argument("--model-source", choices=[...], help=...)

# Proposed:
pc.add_argument(
    "--model-source",
    choices=["catalog", "setjy", "component", "image"],
    default="catalog",  # ADD DEFAULT
    help=(
        "Populate MODEL_DATA before bandpass using the specified strategy. "
        "Default: 'catalog' (recommended for production). "
        "Use 'setjy' only if calibrator is at phase center and no rephasing is needed."
    )
)
```

**Benefits:**
- ✅ Users don't need to specify `--model-source` (it just works)
- ✅ Defaults to safest option (catalog model → manual calculation)
- ✅ Prevents accidental use of `setjy` (edge case)

**Implementation:**
- Add `default="catalog"` to argument parser
- Update validation to handle default case
- Ensure catalog model works with minimal inputs

---

### **2. Early Validation for Problematic Combinations (HIGH PRIORITY)**

**Add Before MODEL_DATA Population:**

```python
def validate_model_source_usage(args, ms_was_rephased: bool) -> None:
    """Validate model source choice and warn about problematic combinations."""
    
    # Check for problematic setjy usage
    if args.model_source == "setjy":
        if ms_was_rephased:
            # ERROR: setjy with rephasing uses buggy ft()
            raise ValueError(
                "ERROR: --model-source=setjy cannot be used with rephasing.\n"
                "Reason: setjy uses ft() internally, which has phase center bugs after rephasing.\n"
                "Solution: Use --model-source=catalog (default) instead.\n"
                "Or: Use --skip-rephase if calibrator is at meridian phase center."
            )
        
        if not (hasattr(args, 'cal_ra_deg') and args.cal_ra_deg):
            # WARNING: setjy without explicit coordinates may have issues
            logger.warning(
                "WARNING: --model-source=setjy without explicit coordinates may have phase issues.\n"
                "Recommendation: Provide --cal-ra-deg and --cal-dec-deg for accurate MODEL_DATA.\n"
                "Or: Use --model-source=catalog (default) which handles this automatically."
            )
    
    # Check for catalog model without coordinates
    if args.model_source == "catalog":
        if not (hasattr(args, 'cal_ra_deg') and args.cal_ra_deg):
            # Not an error, but warn if auto-fields might fail
            logger.info(
                "INFO: Using catalog model without explicit coordinates.\n"
                "Will attempt --auto-fields to find calibrator in MS field of view.\n"
                "For best results, provide --cal-ra-deg, --cal-dec-deg, --cal-flux-jy."
            )
```

**Call Before MODEL_DATA Population:**
```python
# In cli.py, around line 1498 (before MODEL_DATA population)
if needs_model and args.model_source:
    # Validate model source usage BEFORE populating MODEL_DATA
    validate_model_source_usage(args, ms_was_rephased)
```

**Benefits:**
- ✅ Prevents problematic combinations before wasting time
- ✅ Clear error messages with solutions
- ✅ Guides users to correct workflow

---

### **3. Better Error Messages with Solutions (MEDIUM PRIORITY)**

**Current Error Messages:**
```python
# Current (line 1815):
p.error("Catalog model requested but calibrator info unavailable...")
```

**Proposed:**
```python
# Proposed:
p.error(
    "ERROR: Catalog model requires calibrator information.\n\n"
    "Options:\n"
    "  1. Use --auto-fields (finds calibrator in MS field of view)\n"
    "     python -m ... calibrate --ms MS.ms --auto-fields\n\n"
    "  2. Provide explicit coordinates (recommended for production)\n"
    "     python -m ... calibrate --ms MS.ms --cal-ra-deg <RA> --cal-dec-deg <DEC> --cal-flux-jy <FLUX>\n\n"
    "  3. Use --model-source=setjy (only if calibrator at phase center)\n"
    "     python -m ... calibrate --ms MS.ms --model-source=setjy --model-field 0\n\n"
    "For more information, see: docs/howto/CALIBRATION_DETAILED_PROCEDURE.md"
)
```

**Benefits:**
- ✅ Users see clear solutions, not just problems
- ✅ Copy-paste ready commands
- ✅ Links to documentation

---

### **4. Workflow Presets (MEDIUM PRIORITY)**

**Add Workflow Presets:**

```python
pc.add_argument(
    "--workflow",
    choices=["standard", "quick", "production"],
    default="standard",
    help=(
        "Calibration workflow preset.\n"
        "  standard: Recommended defaults for most cases (default)\n"
        "  quick: Fast calibration with lower SNR requirements\n"
        "  production: Production-ready with full validation\n"
        "Presets can be overridden by explicit parameter flags."
    )
)

# Apply preset after argument parsing:
def apply_workflow_preset(args):
    """Apply workflow preset defaults."""
    if args.workflow == "standard":
        # Standard production workflow
        if args.model_source is None:
            args.model_source = "catalog"
        # Ensure catalog model has coordinates or auto-fields
        if args.model_source == "catalog":
            if not (args.cal_ra_deg or args.auto_fields):
                # Default to auto-fields if nothing specified
                args.auto_fields = True
                logger.info("Using --auto-fields as default for catalog model")
    
    elif args.workflow == "quick":
        # Quick calibration (lower thresholds)
        if args.model_source is None:
            args.model_source = "catalog"
        # Set quick defaults
        args.bp_minsnr = getattr(args, 'bp_minsnr', 2.0) or 2.0
        args.gain_minsnr = getattr(args, 'gain_minsnr', 2.0) or 2.0
    
    elif args.workflow == "production":
        # Production workflow (full validation)
        if args.model_source is None:
            args.model_source = "catalog"
        # Require explicit coordinates for production
        if args.model_source == "catalog" and not args.cal_ra_deg:
            raise ValueError(
                "Production workflow requires explicit calibrator coordinates.\n"
                "Provide: --cal-ra-deg, --cal-dec-deg, --cal-flux-jy"
            )
```

**Benefits:**
- ✅ Users choose workflow, not individual parameters
- ✅ Safe defaults for each workflow
- ✅ Can still override with explicit flags

---

### **5. Interactive Mode / Wizard (LOW PRIORITY - FUTURE)**

**Future Enhancement:**
```python
pc.add_argument(
    "--interactive",
    action="store_true",
    help="Interactive calibration setup wizard"
)

def run_calibration_wizard():
    """Interactive wizard to guide first-time users."""
    print("=== Calibration Setup Wizard ===\n")
    
    # Step 1: MS path
    ms_path = input("Measurement Set path: ").strip()
    
    # Step 2: Calibrator info
    print("\nCalibrator information:")
    print("  1. Use auto-detection (recommended)")
    print("  2. Provide explicit coordinates")
    choice = input("Choice [1]: ").strip() or "1"
    
    if choice == "1":
        # Auto-fields
        print("Using auto-detection to find calibrator...")
    else:
        ra = input("Calibrator RA (deg): ").strip()
        dec = input("Calibrator Dec (deg): ").strip()
        flux = input("Calibrator flux (Jy): ").strip()
    
    # Step 3: Workflow
    print("\nWorkflow:")
    print("  1. Standard (recommended)")
    print("  2. Quick (fast, lower SNR)")
    print("  3. Production (full validation)")
    workflow = input("Choice [1]: ").strip() or "1"
    
    # Generate command
    cmd = generate_command(ms_path, ...)
    print(f"\nGenerated command:\n{cmd}")
    confirm = input("\nRun this command? [y/N]: ").strip().lower()
    
    if confirm == "y":
        return cmd
    else:
        print("Command not executed. Copy and modify as needed.")
        return None
```

**Benefits:**
- ✅ Guides users through setup step-by-step
- ✅ Prevents mistakes by asking questions
- ✅ Generates correct command

---

### **6. Documentation Links in Errors (LOW PRIORITY)**

**Add to All Error Messages:**
```python
def format_error_with_help(error_msg: str, doc_link: str = None) -> str:
    """Format error message with help link."""
    base = error_msg
    if doc_link:
        base += f"\n\nFor more information: {doc_link}"
    base += "\n\nCommon solutions:\n"
    base += "  - See docs/howto/CALIBRATION_DETAILED_PROCEDURE.md\n"
    base += "  - See docs/reports/EDGE_CASE_DOCUMENTATION.md\n"
    base += "  - Run: python -m dsa110_contimg.calibration.cli calibrate --help"
    return base
```

---

## 📋 **Implementation Priority**

### **Phase 1: Critical (Implement Immediately)**
1. ✅ **Make catalog model default** (30 min)
2. ✅ **Early validation for setjy+rephasing** (1 hour)
3. ✅ **Better error messages** (1 hour)

### **Phase 2: Important (Next Sprint)**
4. ⚠️ **Workflow presets** (2-3 hours)
5. ⚠️ **Documentation links in errors** (1 hour)

### **Phase 3: Nice to Have (Future)**
6. 📋 **Interactive wizard** (1-2 days)
7. 📋 **Parameter recommendations** (2-3 hours)

---

## 🎯 **Expected Impact**

### **Before Safeguards:**
- ❌ Users must know to specify `--model-source=catalog`
- ❌ Users can accidentally use `setjy` with rephasing (gets warnings)
- ❌ Users see generic errors without solutions
- ❌ Users must understand all parameters

### **After Safeguards:**
- ✅ `--model-source` defaults to safe option (catalog)
- ✅ Error prevents `setjy`+rephasing before execution
- ✅ Error messages include solutions
- ✅ Workflow presets guide users

---

## 📝 **Example: Before vs After**

### **Before (Current):**
```bash
# User tries:
python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms

# Gets error:
ERROR: --model-source is required

# User confused - which one to use?
```

### **After (With Safeguards):**
```bash
# User tries:
python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms

# Works! Uses catalog model by default
# If calibrator info missing, gets helpful error:
ERROR: Catalog model requires calibrator information.

Options:
  1. Use --auto-fields (finds calibrator in MS)
  2. Provide explicit coordinates (recommended)
  3. Use --model-source=setjy (only if at phase center)

# User knows what to do
```

---

## ✅ **Summary**

**Key Safeguards:**
1. **Default to catalog model** - Prevents accidental use of setjy
2. **Early validation** - Prevents problematic combinations before execution
3. **Better error messages** - Users see solutions, not just problems
4. **Workflow presets** - Guide users to correct workflow

**Implementation Time:** ~4-5 hours for Phase 1 (critical)

**Expected Outcome:** Users can't accidentally use known-incorrect workflows

