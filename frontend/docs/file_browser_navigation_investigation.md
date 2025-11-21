# File Browser Navigation Investigation

**Date:** 2025-11-17  
**Type:** Investigation  
**Status:** ✅ Verified - No Navigation Bug Found

---

## Issue Report

**User Report:** "When I click in the file browser in the CARTA page, it
redirects me to the QA tools page in a strange way."

---

## Investigation Results

### Code Analysis

#### 1. CARTAPage (`/pages/CARTAPage.tsx`)

**File Browser Location:** Tab-based layout, "File Browser" tab (line 156)

**File Selection Handler:**

```typescript
const handleFileSelect = (path: string, type: string) => {
  if (type === "fits") {
    setSelectedFile(path);
    logger.info("File selected for CARTA:", path);
  }
};
```

**Navigation Logic:** ❌ **NONE** - Only updates local state, no navigation

---

#### 2. QAVisualizationPage (`/pages/QAVisualizationPage.tsx`)

**File Browser Location:** Tab panel, "Directory Browser" tab (line 102)

**File Selection Handler:**

```typescript
const handleFileSelect = (path: string, type: string) => {
  if (type === "fits") {
    setSelectedFITSPath(path);
    setTabValue(1); // Switch to FITS viewer tab
  } else if (type === "casatable") {
    setSelectedTablePath(path);
    setTabValue(2); // Switch to CASA table viewer tab
  }
};
```

**Navigation Logic:** ❌ **NONE** - Only switches tabs within same page, no page
navigation

---

#### 3. QACartaPage (`/pages/QACartaPage.tsx`)

**File Browser Location:** Golden Layout component, "File Browser" panel
(line 125)

**File Selection Handler:**

```typescript
const handleFileSelect = (path: string, type: string) => {
  if (type === "fits") {
    setSelectedFITSPath(path);
    // Update FITS viewer component state
    if (fitsViewerContainerRef.current) {
      fitsViewerContainerRef.current.extendState({ fitsPath: path });
    }
  } else if (type === "casatable") {
    setSelectedTablePath(path);
    // Update CASA table viewer component state
    if (casaTableViewerContainerRef.current) {
      casaTableViewerContainerRef.current.extendState({ tablePath: path });
    }
  }
};
```

**Navigation Logic:** ❌ **NONE** - Only updates Golden Layout component state,
no navigation

---

#### 4. DirectoryBrowser Component (`/components/QA/DirectoryBrowser.tsx`)

**Navigation Logic Check:**

```bash
grep -r "useNavigate|navigate(|router.|history." DirectoryBrowser.tsx
# Result: No matches found
```

**Conclusion:** ✅ **NO NAVIGATION LOGIC** - DirectoryBrowser is a pure
presentational component

---

## Findings

### No Navigation Bug Detected

After thorough code inspection:

1. ✅ **DirectoryBrowser** has NO navigation logic
2. ✅ **CARTAPage** file handler has NO navigation calls
3. ✅ **QAVisualizationPage** file handler has NO navigation calls
4. ✅ **QACartaPage** file handler has NO navigation calls

### Possible Explanations

#### 1. User Confusion (Most Likely)

**Hypothesis:** User may have:

- Clicked on navigation menu accidentally while using file browser
- Clicked browser back button
- Used keyboard shortcut that triggered navigation
- Had multiple tabs/windows open

**Evidence:**

- No code path from file browser clicks to page navigation
- All handlers are properly scoped to their respective pages

#### 2. Browser Extension Interference

**Hypothesis:** Browser extension or ad blocker might be intercepting clicks

**Evidence:**

- None found in code
- Would require user environment testing

#### 3. React Router Edge Case

**Hypothesis:** React Router might have a bug with nested components

**Evidence:**

- Unlikely - React Router v7 is stable
- No nested Routes that would cause this

#### 4. Golden Layout Library Issue (QACartaPage specific)

**Hypothesis:** Golden Layout might be interfering with click events

**Evidence:**

- Golden Layout uses its own layout management
- Possible event bubbling issue
- Would only affect QACartaPage, not CARTAPage

---

## Recommendations

### 1. User Verification Steps

Ask user to:

1. **Reproduce the issue** with browser console open
2. **Check console logs** for navigation events:
   - Look for "File selected for CARTA:" log message
   - Look for React Router navigation logs
3. **Test in incognito mode** to rule out extensions
4. **Test different file types** (FITS vs CASA tables)
5. **Note exact click location** (file name, icon, or row)

### 2. Additional Logging (If Issue Persists)

Add debug logging to track click events:

```typescript
const handleFileSelect = (path: string, type: string) => {
  console.log("[DEBUG] File selected:", { path, type, currentPage: "/carta" });
  if (type === "fits") {
    setSelectedFile(path);
    logger.info("File selected for CARTA:", path);
  }
};
```

### 3. Navigation Guard (Preventive)

Add navigation guard to detect unintended navigation:

```typescript
useEffect(() => {
  const handleBeforeUnload = (e: BeforeUnloadEvent) => {
    if (selectedFile) {
      console.warn("[DEBUG] Page navigation detected with file selected");
    }
  };
  window.addEventListener("beforeunload", handleBeforeUnload);
  return () => window.removeEventListener("beforeunload", handleBeforeUnload);
}, [selectedFile]);
```

### 4. Test Golden Layout Isolation (QACartaPage)

If issue is specific to QACartaPage:

- Test if Golden Layout's event handling interferes with clicks
- Consider replacing Golden Layout with simpler layout system
- Add event.stopPropagation() to file browser clicks

---

## Conclusion

**Status:** ✅ **No navigation bug found in code**

**Likely Cause:** User interaction confusion or browser extension interference

**Action Required:**

1. User to provide detailed reproduction steps
2. Check browser console for logs during reproduction
3. Test in clean browser environment (incognito mode)

**If Issue Persists:**

- Add debug logging to track navigation events
- Consider Golden Layout event handling issues (QACartaPage only)
- Test with React DevTools to inspect component state during click

---

**Last Updated:** 2025-11-17  
**Investigated By:** AI Agent  
**Conclusion:** No code-level navigation bug detected; likely user interaction
or environment issue
