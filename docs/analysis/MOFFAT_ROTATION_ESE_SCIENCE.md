# Moffat Rotation and ESE Science Goals

## ESE Detection Science Context

The DSA-110 pipeline's primary science goal is **ESE (Extreme Scattering Event) detection** through:

1. **Forced Photometry** - Peak flux measurements at catalog positions
2. **Differential Normalization** - Achieves 1-2% relative flux precision
3. **Variability Detection** - Identifies 10-50% flux variations over 14-180 days

**Key Point:** The core pipeline uses **forced photometry** (peak flux at known positions), not 2D model fitting.

---

## Where Does 2D Fitting Fit In?

The 2D fitting tools (Gaussian/Moffat) we're adding are for **interactive analysis**, not the core ESE detection pipeline:

1. **Source Verification** - Verify candidate sources visually
2. **Quality Assessment** - Check fit quality, residuals
3. **Manual Analysis** - Investigate specific sources of interest
4. **Morphology Studies** - Understand source structure

---

## How Moffat Rotation Relates to ESE Science

### Scenario 1: Elliptical Beam Shape

**Problem:**
- Radio astronomy beams are often **elliptical** (not circular)
- Sources appear elliptical due to beam convolution
- Circular fitting underestimates flux for elliptical sources

**Impact on ESE Detection:**
- **If using forced photometry:** Beam shape is accounted for in normalization
- **If using interactive fitting:** Circular Moffat gives wrong flux → wrong variability assessment

**Moffat Rotation Value:**
- ✅ Allows accurate elliptical source fitting
- ✅ Better flux measurements for manual analysis
- ✅ Correct morphology characterization

### Scenario 2: Extended Sources

**Problem:**
- Some sources are extended (galaxies, nebulae)
- Moffat profile better captures extended wings than Gaussian
- But if source is elliptical, circular Moffat fails

**Impact on ESE Detection:**
- Extended sources may show different variability patterns
- Need accurate morphology to understand variability

**Moffat Rotation Value:**
- ✅ Better fits for extended elliptical sources
- ✅ More accurate flux measurements
- ✅ Better understanding of source structure

### Scenario 3: Source Verification Workflow

**Typical Workflow:**
1. Pipeline flags ESE candidate
2. Scientist examines image interactively
3. Fits source to verify flux, check residuals
4. Confirms or rejects candidate

**Without Moffat Rotation:**
- Must use Gaussian for elliptical sources (works, but Moffat might be better)
- Or use circular Moffat (wrong for elliptical sources)

**With Moffat Rotation:**
- Can use Moffat for extended sources (better profile)
- Can handle elliptical sources correctly
- More accurate verification

---

## Direct Impact Assessment

### High Impact Scenarios

**1. Extended Elliptical Sources**
- Moffat better than Gaussian for extended sources
- Rotation needed for elliptical sources
- **Impact:** More accurate flux for extended elliptical sources

**2. Beam-Deconvolved Analysis**
- When analyzing deconvolved images
- Sources may appear elliptical
- **Impact:** Accurate morphology and flux

**3. Source Structure Studies**
- Understanding why sources vary
- Morphology affects variability interpretation
- **Impact:** Better science understanding

### Low Impact Scenarios

**1. Point Sources**
- Most radio sources are point-like
- Circular models work fine
- **Impact:** Minimal

**2. Core Pipeline**
- Pipeline uses forced photometry, not fitting
- Moffat rotation doesn't affect automated detection
- **Impact:** None

**3. Quick Verification**
- Gaussian already handles elliptical sources
- Works well for most cases
- **Impact:** Marginal improvement

---

## Conclusion: Value for ESE Science

### Does Moffat Rotation Help ESE Science Goals?

**Short Answer:** **Marginally, for specific use cases**

**Detailed Answer:**

**Direct Impact: LOW**
- Core ESE detection uses forced photometry (not fitting)
- Most sources are point-like (circular models work)
- Gaussian already handles elliptical sources

**Indirect Impact: MEDIUM**
- Better verification tools for ESE candidates
- More accurate analysis of extended elliptical sources
- Better morphology understanding

**When It Matters:**
1. **Extended elliptical sources** - Moffat better than Gaussian, rotation needed
2. **Detailed source analysis** - When investigating specific candidates
3. **Morphology studies** - Understanding source structure

**When It Doesn't Matter:**
1. **Core pipeline** - Uses forced photometry
2. **Point sources** - Circular models sufficient
3. **Quick checks** - Gaussian works fine

---

## Recommendation

**For ESE Science Goals:**

**Priority: MEDIUM-LOW**

Moffat rotation provides:
- Better tools for **interactive analysis** of ESE candidates
- More accurate fitting for **extended elliptical sources**
- Better **morphology characterization**

But:
- Doesn't affect **core ESE detection pipeline**
- Most sources don't need it
- Gaussian already handles elliptical sources

**Suggested Approach:**
1. **Document limitation** - Note that Moffat is circular only
2. **Recommend Gaussian** - For elliptical sources, use Gaussian
3. **Add later if needed** - If users frequently need Moffat for elliptical sources

**Alternative Priority:**
Consider **Residual Visualization** (Priority 3) first, as it provides more immediate value for:
- Verifying fit quality
- Identifying systematic issues
- Understanding residuals (important for ESE detection)

---

## Bottom Line

Moffat rotation helps with **interactive analysis** of ESE candidates, particularly for extended elliptical sources, but has **minimal direct impact** on the core ESE detection science goals since the pipeline uses forced photometry rather than 2D fitting.

