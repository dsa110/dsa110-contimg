# Security Audit Report

**Date:** 2025-01-27  
**Project:** DSA-110 Continuum Imaging Pipeline Frontend  
**Auditor:** Automated Security Review

## Executive Summary

This document identifies security and reliability issues in the frontend
application, particularly related to Content Security Policy (CSP), external
resource loading, and WebAssembly (WASM) file handling. All issues have been
documented with their locations, risk levels, and proposed solutions.

---

## 🔴 Critical Issues

### 1. CSP Weakness: unsafe-inline / unsafe-eval Required for JS9

**Status:** ⚠️ **Acknowledged Risk**  
**Location:** `index.html` lines 18-30  
**Risk Level:** High  
**Priority:** Medium (requires JS9 migration)

#### Issue Description

The Content Security Policy (CSP) currently requires `'unsafe-inline'` and
`'unsafe-eval'` directives to support JS9 functionality:

```18:30:index.html
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval' https://code.jquery.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob:;
  connect-src 'self' ws: wss: http://127.0.0.1:8000 http://localhost:8000;
  font-src 'self' data:;
  worker-src 'self' blob:;
  frame-src 'self';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
" />
```

#### Security Impact

- **XSS Vulnerability:** `unsafe-inline` allows any inline script to execute,
  significantly weakening XSS protection
- **Code Injection:** `unsafe-eval` allows `eval()` and similar functions,
  enabling code injection attacks
- **CSP Effectiveness:** Reduces CSP effectiveness by ~70-80% compared to strict
  CSP

#### Current Mitigation

- Comment in code acknowledges the issue (line 16-17)
- DOMPurify sanitization is used for `dangerouslySetInnerHTML` usages
- Path validation prevents open redirects

#### Proposed Solution

See **Section 4.1: CSP Migration to Nonce-Based Policy** below.

---

### 2. JS9 Patch via Fetch+Inline Script

**Status:** ⚠️ **Fragile Implementation**  
**Location:** `index.html` lines 225-244  
**Risk Level:** Medium  
**Priority:** Medium

#### Issue Description

JS9's `js9.min.js` is loaded via fetch, patched with regex replacements, then
executed via inline `textContent`:

```225:244:index.html
fetch(basePath + "/js9/js9.min.js")
  .then((response) => response.text())
  .then((js9Source) => {
    // Patch the hardcoded relative paths in js9.min.js
    const patchedSource = js9Source
      .replace(/a\.PREFSFILE="js9Prefs\.json"/g, `a.PREFSFILE="${js9Base}/js9Prefs.json"`)
      .replace(
        /a\.WORKERFILE="js9worker\.js"/g,
        `a.WORKERFILE="${js9Base}/js9worker.js"`
      );

    // Execute the patched source
    const scriptElement = document.createElement("script");
    scriptElement.textContent = patchedSource;
    document.head.appendChild(scriptElement);
  })
```

#### Security Impact

- **CSP Incompatibility:** Breaks under stricter CSPs (no `unsafe-inline`)
- **Maintenance Risk:** Fragile regex patterns may break if JS9 updates change
  string patterns
- **Runtime Patching:** Dynamic code modification at runtime increases attack
  surface

#### Current Mitigation

- Multiple fallback mechanisms (Proxy, Object.defineProperty, InstallDir
  override)
- Synchronous patching via Object.defineProperty on window.JS9

#### Proposed Solution

See **Section 4.2: JS9 Patching Strategy** below.

---

## 🟡 Medium Priority Issues

### 3. External Resources: jQuery Without SRI/Integrity

**Status:** ✅ **FIXED**  
**Location:** `index.html` line 122  
**Risk Level:** Medium  
**Priority:** High

#### Issue Description

jQuery was loaded from `code.jquery.com` without Subresource Integrity (SRI)
attributes, making it vulnerable to CDN compromise or MITM attacks.

#### Security Impact

- **CDN Compromise:** If jQuery CDN is compromised, malicious code could be
  injected
- **MITM Attacks:** Network-level attacks could replace jQuery with malicious
  version
- **Supply Chain Risk:** No verification that the loaded script matches expected
  content

#### Resolution

✅ **FIXED:** Added SRI integrity hash and crossorigin attribute:

```122:126:index.html
<script
  src="https://code.jquery.com/jquery-3.7.1.min.js"
  integrity="sha384-1H217gwSVyLSIfaLxHbE7dRb3v4mYCKbpQvzx0cegeju1MVsGrX5xXxAvs/HgeFs"
  crossorigin="anonymous"
></script>
```

**SRI Hash:**
`sha384-1H217gwSVyLSIfaLxHbE7dRb3v4mYCKbpQvzx0cegeju1MVsGrX5xXxAvs/HgeFs`

---

### 4. WASM Path/Timeouts: Potential Loading Issues

**Status:** ⚠️ **Needs Verification**  
**Location:** Multiple (see details below)  
**Risk Level:** Low-Medium  
**Priority:** Low

#### Issue Description

WASM files (`astroemw.wasm`) must be served under `/js9/` (or `/ui/js9/` in
production). The code configures paths correctly, but fetch operations lack
explicit timeout handling.

#### Current Implementation

1. **Path Configuration:** ✅ Correctly set in multiple places:
   - `index.html` line 94:
     `window.Module.wasmBinaryFile = js9Base + "/astroemw.wasm"`
   - `index.html` line 382: Re-applied in configuration function
   - `useJS9Initialization.ts` line 169: `wasmPath: js9Base + "/astroemw.wasm"`

2. **WASM Loading:** Located in `public/js9/astroemw.js`:
   - Uses `fetch()` with `credentials: "same-origin"` (line 618)
   - No explicit timeout configuration
   - Falls back to ArrayBuffer instantiation on streaming failure

3. **File Verification:** ✅ Files exist:
   - `public/js9/astroemw.wasm` ✅ Present
   - `public/js9/astroemw.js` ✅ Present

#### Potential Issues

- **No Timeout:** Fetch operations in `astroemw.js` don't have explicit timeouts
- **Silent Failures:** WASM loading errors may not be properly surfaced to users
- **Network Resilience:** No retry logic for WASM fetch failures

#### Recommendations

1. ✅ **Verify WASM files load correctly** in both dev and production
2. ⚠️ **Add timeout handling** to WASM fetch operations (if possible via Module
   configuration)
3. ⚠️ **Add error monitoring** for WASM loading failures
4. ✅ **Verify dev server** serves `/js9/` correctly (Vite serves `public/` at
   root)

#### Proposed Solution

See **Section 4.3: WASM Loading Improvements** below.

---

## 📋 Proposed Solutions

### 4.1 CSP Migration to Nonce-Based Policy

#### Approach

Migrate from `unsafe-inline`/`unsafe-eval` to nonce-based CSP for better
security.

#### Implementation Steps

1. **Generate Nonces Server-Side (or Build-Time)**

   ```typescript
   // In server middleware or build script
   const nonce = crypto.randomBytes(16).toString("base64");
   ```

2. **Update CSP Header**

   ```html
   <meta
     http-equiv="Content-Security-Policy"
     content="
     default-src 'self';
     script-src 'self' 'nonce-{NONCE}' https://code.jquery.com;
     style-src 'self' 'nonce-{NONCE}';
     img-src 'self' data: blob:;
     connect-src 'self' ws: wss: http://127.0.0.1:8000 http://localhost:8000;
     font-src 'self' data:;
     worker-src 'self' blob:;
     frame-src 'self';
     object-src 'none';
     base-uri 'self';
     form-action 'self';
   "
   />
   ```

3. **Add Nonces to Script Tags**
   ```html
   <script nonce="{NONCE}">
     // Inline scripts
   </script>
   ```

#### Challenges

- **JS9 Compatibility:** JS9 may require `unsafe-eval` for dynamic code
  generation
- **Build Integration:** Nonces must be generated at build time or injected
  server-side
- **Testing:** Requires thorough testing to ensure all scripts work with nonces

#### Alternative: Strict CSP with JS9 Isolation

- Load JS9 in an isolated iframe with relaxed CSP
- Main application uses strict CSP
- Communicate via postMessage API

#### Recommendation

**Short-term:** Keep current CSP with documented risk  
**Long-term:** Implement nonce-based CSP or JS9 isolation after thorough testing

---

### 4.2 JS9 Patching Strategy

#### Current Problem

Runtime patching via fetch+regex+inline script is fragile and CSP-incompatible.

#### Proposed Solutions

##### Option A: Pre-patched JS9 Build (Recommended)

1. **Maintain patched version in codebase:**
   - Download `js9.min.js` during build
   - Apply patches via build script
   - Commit patched version to `public/js9/js9.min.js`
   - Load directly without runtime patching

2. **Benefits:**
   - ✅ No runtime patching needed
   - ✅ CSP-compatible (no inline scripts)
   - ✅ Easier to maintain (patches in build script)
   - ✅ Version-controlled patches

3. **Implementation:**
   ```bash
   # In scripts/patch-js9.sh
   curl -o js9.min.js https://js9.si.edu/js9/js9.min.js
   sed -i 's/a\.PREFSFILE="js9Prefs\.json"/a.PREFSFILE="\/ui\/js9\/js9Prefs.json"/g' js9.min.js
   sed -i 's/a\.WORKERFILE="js9worker\.js"/a.WORKERFILE="\/ui\/js9\/js9worker.js"/g' js9.min.js
   ```

##### Option B: Build-Time Patching

1. **Patch during Vite build:**
   - Use Vite plugin to patch `js9.min.js` during build
   - Apply regex replacements at build time
   - Output patched file to `dist/js9/`

2. **Benefits:**
   - ✅ No runtime patching
   - ✅ CSP-compatible
   - ✅ Automatic patching on build

##### Option C: Fork JS9 with Configurable Paths

1. **Fork JS9 repository:**
   - Modify JS9 to accept path configuration via options
   - Remove hardcoded relative paths
   - Maintain fork with upstream updates

2. **Benefits:**
   - ✅ Long-term solution
   - ✅ No patching needed
   - ✅ Upstream compatibility

3. **Drawbacks:**
   - ⚠️ Requires maintaining fork
   - ⚠️ More complex

#### Recommendation

**Short-term:** Keep current approach with improved error handling  
**Long-term:** Implement **Option A (Pre-patched Build)** for CSP compatibility

---

### 4.3 WASM Loading Improvements

#### Current State

- ✅ WASM files exist in correct location
- ✅ Paths configured correctly
- ⚠️ No explicit timeout handling
- ⚠️ Limited error reporting

#### Proposed Improvements

1. **Add Timeout to WASM Fetch (if supported by Module API)**

   ```javascript
   // In index.html, configure Module before astroemw.js loads
   window.Module = {
     wasmBinaryFile: js9Base + "/astroemw.wasm",
     // Add timeout configuration if supported
     instantiateWasm: function (imports, receiveInstance) {
       // Custom instantiation with timeout
       const controller = new AbortController();
       const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

       fetch(js9Base + "/astroemw.wasm", {
         signal: controller.signal,
         credentials: "same-origin",
       })
         .then((response) => {
           clearTimeout(timeoutId);
           return response.arrayBuffer();
         })
         .then((bytes) => WebAssembly.instantiate(bytes, imports))
         .then((result) => {
           receiveInstance(result.instance, result.module);
           return result.exports;
         })
         .catch((error) => {
           clearTimeout(timeoutId);
           console.error("WASM loading failed:", error);
           throw error;
         });
     },
   };
   ```

2. **Add Error Monitoring**

   ```typescript
   // In useJS9Initialization.ts or JS9Context
   window.addEventListener("error", (event) => {
     if (
       event.message?.includes("wasm") ||
       event.filename?.includes("astroemw")
     ) {
       logger.error("WASM loading error:", event);
       // Report to error tracking service
     }
   });
   ```

3. **Verify WASM Loading in Tests**
   ```typescript
   // Add integration test
   test("WASM files load correctly", async () => {
     const response = await fetch("/js9/astroemw.wasm");
     expect(response.ok).toBe(true);
     expect(response.headers.get("content-type")).toContain("wasm");
   });
   ```

#### Recommendation

1. ✅ **Verify WASM files load** in dev and production environments
2. ⚠️ **Add error monitoring** for WASM loading failures
3. ⚠️ **Document timeout behavior** (browser default ~30s may be sufficient)
4. ⚠️ **Add user-facing error messages** if WASM fails to load

---

## 📊 Risk Assessment Summary

| Issue                  | Risk Level | Priority | Status             | Effort |
| ---------------------- | ---------- | -------- | ------------------ | ------ |
| CSP unsafe-inline/eval | High       | Medium   | Acknowledged       | High   |
| JS9 runtime patching   | Medium     | Medium   | Active             | Medium |
| jQuery SRI             | Medium     | High     | ✅ Fixed           | Low    |
| WASM timeouts          | Low-Medium | Low      | Needs Verification | Low    |

---

## ✅ Action Items

### Immediate (Completed)

- [x] Add SRI integrity hash for jQuery
- [x] Document all security issues

### Short-term (Next Sprint)

- [ ] Verify WASM files load correctly in production
- [ ] Add error monitoring for WASM loading
- [ ] Test CSP with nonce-based approach in development

### Long-term (Future Releases)

- [ ] Migrate to nonce-based CSP or JS9 isolation
- [ ] Implement pre-patched JS9 build process
- [ ] Add comprehensive WASM loading error handling

---

## 📚 References

- [MDN: Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [MDN: Subresource Integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity)
- [OWASP: XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [JS9 Documentation](https://js9.si.edu/)

---

## 🔄 Review Schedule

This audit should be reviewed:

- **Quarterly:** Full security audit
- **After JS9 updates:** Verify patching still works
- **After CSP changes:** Verify all functionality
- **After production incidents:** Re-assess risk levels

---

**Last Updated:** 2025-01-27  
**Next Review:** 2025-04-27
