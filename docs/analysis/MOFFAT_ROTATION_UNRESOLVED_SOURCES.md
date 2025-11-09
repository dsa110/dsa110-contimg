# Moffat Rotation for Unresolved Compact Sources

## Science Context

**Key Information:**
- Looking at **unresolved compact sources** in the field
- Sources are point-like (not extended)
- Sources appear as the **beam shape** (beam convolution)

---

## How Unresolved Sources Appear

### Point Source + Beam = Beam Shape

For unresolved compact sources:
- **Source itself:** Point-like (circular)
- **Observed appearance:** Beam shape (may be elliptical)
- **Result:** Sources appear elliptical if beam is elliptical

### Beam Shape Matters

**If beam is circular:**
- Sources appear circular
- Circular fitting (Gaussian or Moffat) works fine
- Moffat rotation: **Not needed**

**If beam is elliptical:**
- Sources appear elliptical
- Need elliptical fitting for accurate flux
- Moffat rotation: **Potentially useful**

---

## Impact on Fitting

### Forced Photometry (Core Pipeline)

The core ESE detection pipeline uses **forced photometry** at catalog positions:
- Measures peak flux (Jy/beam)
- Beam shape is accounted for in normalization
- **Moffat rotation: Not relevant** (doesn't use fitting)

### Interactive Fitting (New Tools)

The 2D fitting tools are for **interactive analysis**:

**Scenario: Circular Beam**
- Sources appear circular
- Circular Moffat works fine
- Circular Gaussian works fine
- **Moffat rotation: Not needed**

**Scenario: Elliptical Beam**
- Sources appear elliptical
- Circular Moffat: **Wrong shape** → inaccurate flux
- Elliptical Gaussian: Works (already implemented)
- Elliptical Moffat: Would work (needs rotation)
- **Moffat rotation: Useful** (if you prefer Moffat over Gaussian)

---

## Key Question: What's Your Beam Shape?

### Check Your Images

Look at your image metadata:
- `beam_major_arcsec` vs `beam_minor_arcsec`
- If `beam_major != beam_minor`: **Beam is elliptical**
- If `beam_major == beam_minor`: **Beam is circular**

### Typical Radio Astronomy Beams

**Circular Beams:**
- Some telescopes have circular beams
- Sources appear circular
- Circular fitting sufficient

**Elliptical Beams:**
- Many radio telescopes have elliptical beams
- Due to dish shape, array configuration, etc.
- Sources appear elliptical
- Need elliptical fitting

---

## Value Assessment for Unresolved Sources

### If Beams Are Circular

**Moffat Rotation Value: LOW**
- Sources appear circular
- Circular Moffat works fine
- Circular Gaussian works fine
- No need for rotation

**Recommendation:** Skip Moffat rotation, focus on other priorities

### If Beams Are Elliptical

**Moffat Rotation Value: MEDIUM**
- Sources appear elliptical
- Need elliptical fitting
- Gaussian already supports rotation ✅
- Moffat needs rotation for parity ⚠️

**Recommendation:** 
- **Short-term:** Use Gaussian for elliptical sources (already works)
- **Long-term:** Add Moffat rotation for feature parity

---

## Practical Recommendation

### Step 1: Check Your Beam Shapes

```python
# Check if beams are elliptical
import sqlite3
conn = sqlite3.connect('state/products.sqlite3')
cursor = conn.cursor()
cursor.execute("""
    SELECT beam_major_arcsec, beam_minor_arcsec 
    FROM images 
    LIMIT 10
""")
for major, minor in cursor.fetchall():
    ratio = major / minor if minor > 0 else 1.0
    print(f"Beam ratio: {ratio:.3f} (1.0 = circular, >1.0 = elliptical)")
```

**If ratio ≈ 1.0:** Beams are circular → Moffat rotation not needed  
**If ratio > 1.1:** Beams are elliptical → Moffat rotation potentially useful

### Step 2: Decision Matrix

| Beam Shape | Current Tools | Moffat Rotation Value | Priority |
|------------|---------------|----------------------|----------|
| Circular   | Circular Moffat/Gaussian work | LOW | Skip |
| Elliptical | Gaussian works, Moffat doesn't | MEDIUM | Consider later |

### Step 3: Recommendation

**Given uncertainty about beam shapes:**

1. **Check beam shapes first** - Determine if beams are elliptical
2. **If circular:** Skip Moffat rotation, focus on Residual Visualization
3. **If elliptical:** 
   - Short-term: Use Gaussian (already works)
   - Long-term: Add Moffat rotation for parity

**Alternative Approach:**
- Document that Moffat is circular-only
- Recommend Gaussian for elliptical sources
- Add Moffat rotation later if users request it

---

## Comparison with Other Priorities

### Priority 2: Moffat Rotation
- **Value:** Depends on beam shape (unknown)
- **Effort:** Medium-High (4-8 hours)
- **Risk:** May not be needed if beams are circular

### Priority 3: Residual Visualization
- **Value:** High (universally useful)
- **Effort:** Medium (4-6 hours)
- **Risk:** Low (always useful)

**Recommendation:** Prioritize Residual Visualization (Priority 3) since it's universally useful regardless of beam shape.

---

## Bottom Line

**For unresolved compact sources:**

- **If beams are circular:** Moffat rotation not needed
- **If beams are elliptical:** Moffat rotation useful (but Gaussian already works)
- **Uncertainty:** Check beam shapes first, then decide

**Suggested Action:**
1. Check beam shapes in your images
2. If circular → Skip Moffat rotation
3. If elliptical → Use Gaussian for now, add Moffat rotation later if needed
4. Prioritize Residual Visualization (more universally useful)

