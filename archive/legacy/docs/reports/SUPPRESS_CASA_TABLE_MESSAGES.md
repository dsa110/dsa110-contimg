# How to Suppress CASA Table Open Messages

**Date:** 2025-11-05  
**Context:** Suppressing "Successful readonly open" diagnostic messages

---

## Quick Answer

Add `ack=False` parameter to `table()` calls where you want to suppress messages:

```python
# Before (generates message)
with table(ms_path, readonly=True) as tb:
    ...

# After (suppresses message)
with table(ms_path, readonly=True, ack=False) as tb:
    ...
```

---

## Specific Locations for the 4 Messages

The 4 identical messages you see come from these locations:

### 1. Post-Flagging Validation
**File:** `src/dsa110_contimg/calibration/cli.py`  
**Line:** 1043  
**Change:**
```python
# Before
with table(ms_in, readonly=True) as tb:

# After
with table(ms_in, readonly=True, ack=False) as tb:
```

### 2. MODEL_DATA Flux Validation
**File:** `src/dsa110_contimg/calibration/cli.py`  
**Line:** 1492  
**Change:**
```python
# Before
with table(ms_in, readonly=True) as tb:

# After
with table(ms_in, readonly=True, ack=False) as tb:
```

### 3. MODEL_DATA Precondition in `solve_gains`
**File:** `src/dsa110_contimg/calibration/calibration.py`  
**Line:** 704  
**Change:**
```python
# Before
with table(ms) as tb:

# After
with table(ms, readonly=True, ack=False) as tb:
```
**Note:** This one doesn't explicitly set `readonly=True`, but it defaults to readonly. Adding both makes it explicit and suppresses the message.

### 4. Dry-Run Flagging Estimate (if using --dry-run)
**File:** `src/dsa110_contimg/calibration/cli.py`  
**Line:** 978  
**Change:**
```python
# Before
with table(ms_in, readonly=True) as tb:

# After
with table(ms_in, readonly=True, ack=False) as tb:
```

---

## Complete Fix: Update All Three Main Locations

To suppress all 4 messages, update these three locations:

### File 1: `src/dsa110_contimg/calibration/cli.py`

**Location 1: Line 978 (Dry-run)**
```python
                with table(ms_in, readonly=True, ack=False) as tb:
```

**Location 2: Line 1043 (Post-flagging validation)**
```python
                with table(ms_in, readonly=True, ack=False) as tb:
```

**Location 3: Line 1492 (MODEL_DATA flux validation)**
```python
                with table(ms_in, readonly=True, ack=False) as tb:
```

### File 2: `src/dsa110_contimg/calibration/calibration.py`

**Location: Line 704 (MODEL_DATA precondition)**
```python
    with table(ms, readonly=True, ack=False) as tb:
```

---

## Example: Patch for All Locations

Here's a patch showing all changes:

```diff
--- a/src/dsa110_contimg/calibration/cli.py
+++ b/src/dsa110_contimg/calibration/cli.py
@@ -975,7 +975,7 @@ def main():
             try:
                 from casacore.tables import table
                 import numpy as np
-                with table(ms_in, readonly=True) as tb:
+                with table(ms_in, readonly=True, ack=False) as tb:
                     n_rows = tb.nrows()
                     sample_size = min(10000, n_rows)
                     if sample_size > 0:
@@ -1040,7 +1040,7 @@ def main():
             try:
                 from casacore.tables import table
                 import numpy as np
-                with table(ms_in, readonly=True) as tb:
+                with table(ms_in, readonly=True, ack=False) as tb:
                     n_rows = tb.nrows()
                     # Sample up to 10000 rows to estimate flagging fraction
@@ -1489,7 +1489,7 @@ def main():
             try:
                 from casacore.tables import table
                 import numpy as np
-                with table(ms_in, readonly=True) as tb:
+                with table(ms_in, readonly=True, ack=False) as tb:
                     if "MODEL_DATA" in tb.colnames():
                         n_rows = tb.nrows()

--- a/src/dsa110_contimg/calibration/calibration.py
+++ b/src/dsa110_contimg/calibration/calibration.py
@@ -700,7 +700,7 @@ def solve_gains(
     # for consistent, reliable calibration across all calibrators (bright or faint).
     print(f"Validating MODEL_DATA for gain solve on field(s) {cal_field}...")
-    with table(ms) as tb:
+    with table(ms, readonly=True, ack=False) as tb:
         if "MODEL_DATA" not in tb.colnames():
             raise ValueError(
```

---

## What `ack=False` Does

- **`ack=True` (default):** CASA prints diagnostic messages like "Successful readonly open..."
- **`ack=False`:** Suppresses these diagnostic messages

**Note:** `ack` stands for "acknowledge" - it controls whether CASA acknowledges table operations with messages.

---

## Other Locations (Optional)

If you want to suppress messages everywhere, you can also add `ack=False` to:

- `src/dsa110_contimg/calibration/validate.py` (lines 44, 94, 107, 116, 129)
- `src/dsa110_contimg/calibration/model.py` (lines 79, 88)
- `src/dsa110_contimg/calibration/flagging.py` (line 323)
- `src/dsa110_contimg/calibration/calibration.py` (lines 30, 103)

**Note:** Some of these already use `ack=False` (like `qa.py:318` and `apply_service.py:148`), so they're already quiet.

---

## Recommendation

**Suppress only the 4 main validation checks** (the ones that generate the messages you're seeing). This keeps the output clean while still showing important CASA messages elsewhere.

**Don't suppress everywhere** - some messages can be useful for debugging table access issues.

---

## Testing

After making these changes, re-run calibration:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /data/ms/2025-10-29T13:54:17.ms \
  --field 0 --refant 103 \
  --auto-fields --model-source catalog \
  --combine-spw
```

You should no longer see the 4 "Successful readonly open" messages.

