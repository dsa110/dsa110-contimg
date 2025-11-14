# Moffat Rotation: Value Analysis

## Current State

**Gaussian Fitting:**
- ✅ Supports rotation (position angle)
- ✅ Supports ellipticity (major/minor axes)
- ✅ Can fit elliptical sources accurately

**Moffat Fitting:**
- ⚠️ Only circular (no rotation)
- ⚠️ Fixed `pa = 0.0`
- ⚠️ Less accurate for elliptical sources

## The Value Proposition

### 1. **Parity with Gaussian**
- Both models should support the same features
- Users shouldn't have to choose between "accurate shape" (Gaussian) and "better profile" (Moffat)
- Consistency in the API

### 2. **Accuracy for Elliptical Sources**
- Radio astronomy sources are often elliptical (due to beam shape, source structure, etc.)
- Moffat profile can be better than Gaussian for extended sources (wings)
- But without rotation, it's only useful for circular sources
- **Real impact:** If a source is elliptical, circular Moffat will give poor fit

### 3. **Model Selection Flexibility**
- Users can choose the best model for their source
- Not constrained by "Gaussian if elliptical, Moffat if circular"
- Can use Moffat for extended elliptical sources

## The Reality Check

### When is Moffat Rotation Actually Needed?

**High Value Scenarios:**
1. **Extended elliptical sources** - Moffat better captures wings than Gaussian
2. **Beam-deconvolved sources** - When beam is elliptical, sources appear elliptical
3. **Galaxy fitting** - Extended sources with elliptical profiles

**Low Value Scenarios:**
1. **Point sources** - Circular models work fine
2. **Circular sources** - No rotation needed
3. **Quick fits** - Gaussian is usually sufficient

### The Trade-off

**Current Workaround:**
- Use Gaussian for elliptical sources (works well)
- Use Moffat for circular/extended sources (works well)
- Users can choose the right tool for the job

**With Moffat Rotation:**
- More flexibility
- Better fits for extended elliptical sources
- But: More complex implementation, more parameters to fit

## Assessment

### Is It Worth It?

**Arguments FOR:**
- Completeness/parity with Gaussian
- Better fits for specific use cases (extended elliptical sources)
- Professional astronomy software standard (CARTA, CASA, etc. support it)

**Arguments AGAINST:**
- Gaussian already handles elliptical sources well
- Most sources can be fit adequately with existing tools
- Medium-high effort (4-8 hours) for medium value
- Lower priority than other features (residual visualization, parameter locking)

### Recommendation

**Priority 2 is reasonable IF:**
- You frequently fit extended elliptical sources
- You need the best possible fit quality
- You want feature parity with professional tools

**Consider Deferring IF:**
- Gaussian fits are sufficient for your use cases
- You have limited development time
- Other features (residual viz, parameter locking) are more valuable

**Alternative Approach:**
- Document the limitation clearly
- Recommend Gaussian for elliptical sources
- Add Moffat rotation later if users request it

## Conclusion

Moffat rotation is a **"nice to have"** feature that provides:
- Feature parity with Gaussian
- Better fits for extended elliptical sources
- Professional tool compatibility

But it's **not critical** because:
- Gaussian already handles elliptical sources
- Most use cases are covered by existing tools
- Medium-high effort for medium value

**Recommendation:** Keep it as Priority 2, but consider prioritizing Residual Visualization (Priority 3) first if it provides more immediate user value.

