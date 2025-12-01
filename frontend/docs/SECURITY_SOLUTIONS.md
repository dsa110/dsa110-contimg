# Security Solutions Implementation Guide

This document provides detailed implementation steps for addressing the security
issues identified in `SECURITY_AUDIT.md`.

---

## 1. CSP Migration to Nonce-Based Policy

### Overview

Migrate from `unsafe-inline`/`unsafe-eval` to nonce-based CSP for better XSS
protection.

### Implementation Approach

#### Option A: Server-Side Nonce Generation (Recommended for Production)

**Step 1: Generate Nonce in Backend**

```python
# In FastAPI backend (or middleware)
import secrets
import base64

def generate_nonce():
    """Generate a cryptographically secure nonce"""
    return base64.b64encode(secrets.token_bytes(16)).decode('utf-8')

@app.middleware("http")
async def add_csp_nonce(request: Request, call_next):
    nonce = generate_nonce()
    request.state.csp_nonce = nonce
    response = await call_next(request)
    # Add nonce to CSP header
    csp = response.headers.get("Content-Security-Policy", "")
    csp = csp.replace("{NONCE}", nonce)
    response.headers["Content-Security-Policy"] = csp
    return response
```

**Step 2: Inject Nonce into HTML**

```html
<!-- In index.html template -->
<meta
  http-equiv="Content-Security-Policy"
  content="
  default-src 'self';
  script-src 'self' 'nonce-{{NONCE}}' https://code.jquery.com;
  style-src 'self' 'nonce-{{NONCE}}';
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

<script nonce="{{NONCE}}">
  // All inline scripts
</script>
```

#### Option B: Build-Time Nonce (For Static Deployment)

**Step 1: Generate Nonce at Build Time**

```typescript
// scripts/generate-nonce.ts
import crypto from "crypto";

const nonce = crypto.randomBytes(16).toString("base64");
console.log(`Generated nonce: ${nonce}`);

// Write to .env file or inject into index.html
```

**Step 2: Use Vite Plugin to Inject Nonce**

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import { readFileSync, writeFileSync } from "fs";
import crypto from "crypto";

function injectNoncePlugin() {
  return {
    name: "inject-nonce",
    transformIndexHtml(html: string) {
      const nonce = crypto.randomBytes(16).toString("base64");
      return html.replace(/{NONCE}/g, nonce);
    },
  };
}

export default defineConfig({
  plugins: [injectNoncePlugin(), react()],
  // ...
});
```

#### Option C: JS9 Isolation (Alternative Approach)

If JS9 requires `unsafe-eval`, isolate it in an iframe:

**Step 1: Create JS9 Iframe**

```html
<!-- js9-iframe.html -->
<!DOCTYPE html>
<html>
  <head>
    <meta
      http-equiv="Content-Security-Policy"
      content="
    script-src 'self' 'unsafe-inline' 'unsafe-eval' https://code.jquery.com;
    default-src 'self';
  "
    />
    <!-- Load JS9 here -->
  </head>
  <body>
    <div id="js9-container"></div>
    <script>
      // JS9 initialization
      window.addEventListener("message", (event) => {
        if (event.data.type === "loadFITS") {
          JS9.Load(event.data.path);
        }
      });
    </script>
  </body>
</html>
```

**Step 2: Main App Communication**

```typescript
// In React component
const js9Iframe = useRef<HTMLIFrameElement>(null);

const loadFITS = (path: string) => {
  js9Iframe.current?.contentWindow?.postMessage(
    {
      type: "loadFITS",
      path: path,
    },
    "*"
  );
};
```

### Testing Checklist

- [ ] All inline scripts have nonce attribute
- [ ] All inline styles have nonce attribute
- [ ] JS9 functionality works correctly
- [ ] No CSP violations in console
- [ ] Test in Chrome, Firefox, Safari

### Rollback Plan

Keep current CSP as fallback if nonce-based approach causes issues.

---

## 2. JS9 Patching Strategy

### Option A: Pre-patched JS9 Build (Recommended)

#### Implementation Steps

**Step 1: Create Build Script**

```bash
#!/bin/bash
# scripts/patch-js9.sh

set -e

JS9_VERSION="4.4"
JS9_DIR="public/js9"
TEMP_DIR=$(mktemp -d)

echo "Downloading JS9 ${JS9_VERSION}..."

# Download JS9 files
curl -L "https://js9.si.edu/js9/js9.min.js" -o "${TEMP_DIR}/js9.min.js"
curl -L "https://js9.si.edu/js9/js9support.js" -o "${TEMP_DIR}/js9support.js"
curl -L "https://js9.si.edu/js9/js9support.css" -o "${TEMP_DIR}/js9support.css"

echo "Patching js9.min.js..."

# Detect base path (dev vs production)
# In production, paths should be /ui/js9/
# In dev, paths should be /js9/

# Patch for production paths (default)
sed -i.bak \
  -e 's/a\.PREFSFILE="js9Prefs\.json"/a.PREFSFILE="\/ui\/js9\/js9Prefs.json"/g' \
  -e 's/a\.WORKERFILE="js9worker\.js"/a.WORKERFILE="\/ui\/js9\/js9worker.js"/g' \
  "${TEMP_DIR}/js9.min.js"

# Copy to public directory
cp "${TEMP_DIR}/js9.min.js" "${JS9_DIR}/js9.min.js"
cp "${TEMP_DIR}/js9support.js" "${JS9_DIR}/js9support.js"
cp "${TEMP_DIR}/js9support.css" "${JS9_DIR}/js9support.css"

echo "JS9 patched and copied to ${JS9_DIR}/"
rm -rf "${TEMP_DIR}"
```

**Step 2: Update package.json**

```json
{
  "scripts": {
    "patch-js9": "bash scripts/patch-js9.sh",
    "prebuild": "npm run patch-js9"
  }
}
```

**Step 3: Update index.html**

```html
<!-- Remove fetch+patch logic, load directly -->
<script src="/js9/js9support.js"></script>
<script src="/js9/js9.min.js"></script>
```

**Step 4: Remove Runtime Patching Code** Remove lines 215-260 from `index.html`
(fetch+patch logic).

#### Benefits

- ✅ No runtime patching
- ✅ CSP-compatible
- ✅ Easier to maintain
- ✅ Version-controlled

#### Maintenance

- Run `npm run patch-js9` when updating JS9
- Test thoroughly after patching
- Document any new patterns that need patching

---

### Option B: Vite Plugin for Build-Time Patching

**Step 1: Create Vite Plugin**

```typescript
// vite-plugins/js9-patcher.ts
import { Plugin } from "vite";
import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

export function js9Patcher(): Plugin {
  return {
    name: "js9-patcher",
    buildStart() {
      const js9Path = join(process.cwd(), "public/js9/js9.min.js");
      const js9Source = readFileSync(js9Path, "utf-8");

      // Patch for production paths
      const patched = js9Source
        .replace(
          /a\.PREFSFILE="js9Prefs\.json"/g,
          'a.PREFSFILE="/ui/js9/js9Prefs.json"'
        )
        .replace(
          /a\.WORKERFILE="js9worker\.js"/g,
          'a.WORKERFILE="/ui/js9/js9worker.js"'
        );

      writeFileSync(js9Path, patched);
    },
  };
}
```

**Step 2: Add to vite.config.ts**

```typescript
import { js9Patcher } from "./vite-plugins/js9-patcher";

export default defineConfig({
  plugins: [js9Patcher(), react() /* ... */],
});
```

---

## 3. WASM Loading Improvements

### Add Timeout and Error Handling

**Step 1: Enhanced Module Configuration**

```typescript
// src/utils/js9/wasmLoader.ts
export function configureWASMLoader(js9Base: string) {
  if (typeof window.Module === "undefined") {
    window.Module = {};
  }

  const originalInstantiateWasm = window.Module.instantiateWasm;

  window.Module.instantiateWasm = function (
    imports: any,
    receiveInstance: Function
  ) {
    const controller = new AbortController();
    const timeout = 30000; // 30 seconds
    const timeoutId = setTimeout(() => {
      controller.abort();
      console.error("WASM loading timeout after", timeout, "ms");
    }, timeout);

    return fetch(js9Base + "/astroemw.wasm", {
      signal: controller.signal,
      credentials: "same-origin",
    })
      .then((response) => {
        clearTimeout(timeoutId);
        if (!response.ok) {
          throw new Error(
            `WASM fetch failed: ${response.status} ${response.statusText}`
          );
        }
        return response.arrayBuffer();
      })
      .then((bytes) => WebAssembly.instantiate(bytes, imports))
      .then((result) => {
        receiveInstance(result.instance, result.module);
        return result.exports;
      })
      .catch((error) => {
        clearTimeout(timeoutId);
        console.error("WASM loading error:", error);

        // Fallback to original if available
        if (originalInstantiateWasm) {
          return originalInstantiateWasm(imports, receiveInstance);
        }

        throw error;
      });
  };

  window.Module.wasmBinaryFile = js9Base + "/astroemw.wasm";
}
```

**Step 2: Update index.html**

```html
<script>
  // Configure WASM loader before astroemw.js loads
  (function () {
    const basePath = window.location.pathname.startsWith("/ui/") ? "/ui" : "";
    const js9Base = basePath + "/js9";

    // This will be called by astroemw.js if Module.instantiateWasm is defined
    if (typeof window.Module === "undefined") {
      window.Module = {};
    }
    window.Module.wasmBinaryFile = js9Base + "/astroemw.wasm";
  })();
</script>
```

**Step 3: Add Error Monitoring**

```typescript
// src/utils/js9/wasmErrorHandler.ts
import { logger } from "../logger";

export function setupWASMErrorHandling() {
  // Global error handler for WASM-related errors
  window.addEventListener("error", (event) => {
    if (
      event.message?.includes("wasm") ||
      event.message?.includes("WebAssembly") ||
      event.filename?.includes("astroemw") ||
      event.filename?.includes("js9")
    ) {
      logger.error("WASM/JS9 error detected:", {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error,
      });

      // Optionally report to error tracking service
      // reportErrorToService(event);
    }
  });

  // Unhandled promise rejection handler
  window.addEventListener("unhandledrejection", (event) => {
    if (
      event.reason?.message?.includes("wasm") ||
      event.reason?.message?.includes("WebAssembly")
    ) {
      logger.error("Unhandled WASM promise rejection:", event.reason);
    }
  });
}
```

**Step 4: Call in App Initialization**

```typescript
// src/main.tsx or App.tsx
import { setupWASMErrorHandling } from "./utils/js9/wasmErrorHandler";

setupWASMErrorHandling();
```

### Verification Script

**Add Test for WASM Loading**

```typescript
// src/utils/js9/__tests__/wasmLoader.test.ts
import { describe, it, expect, beforeEach } from "vitest";

describe("WASM Loader", () => {
  it("should verify WASM file exists", async () => {
    const response = await fetch("/js9/astroemw.wasm");
    expect(response.ok).toBe(true);
    expect(response.headers.get("content-type")).toContain("wasm");
  });

  it("should handle timeout gracefully", async () => {
    // Mock fetch to simulate timeout
    const originalFetch = window.fetch;
    window.fetch = jest.fn(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve(new Response()), 35000)
        )
    );

    // Test timeout handling
    // ...

    window.fetch = originalFetch;
  });
});
```

---

## Implementation Priority

### Phase 1: Immediate (This Sprint)

1. ✅ Add jQuery SRI (Completed)
2. ✅ Document issues (Completed)
3. ⚠️ Verify WASM loading in production
4. ⚠️ Add WASM error monitoring

### Phase 2: Short-term (Next Sprint)

1. Implement pre-patched JS9 build process
2. Remove runtime patching code
3. Test CSP with nonce-based approach in dev

### Phase 3: Long-term (Future Release)

1. Migrate to nonce-based CSP or JS9 isolation
2. Comprehensive WASM loading improvements
3. Full security audit and penetration testing

---

## Testing Requirements

### CSP Migration Testing

- [ ] Test all inline scripts work with nonces
- [ ] Verify JS9 functionality
- [ ] Check browser console for CSP violations
- [ ] Test in Chrome, Firefox, Safari, Edge

### JS9 Patching Testing

- [ ] Verify patched JS9 loads correctly
- [ ] Test FITS file loading
- [ ] Verify paths resolve correctly in dev and production
- [ ] Test after JS9 version updates

### WASM Loading Testing

- [ ] Test WASM loads in dev environment
- [ ] Test WASM loads in production
- [ ] Test timeout handling
- [ ] Test error recovery
- [ ] Test on slow network connections

---

## Rollback Procedures

### CSP Rollback

If nonce-based CSP causes issues:

1. Revert to `unsafe-inline`/`unsafe-eval` in CSP
2. Document specific issues encountered
3. Plan alternative approach

### JS9 Patching Rollback

If pre-patched build fails:

1. Revert to runtime patching
2. Investigate patching script issues
3. Update patching patterns if needed

### WASM Loading Rollback

If timeout handling causes issues:

1. Remove custom timeout logic
2. Rely on browser defaults
3. Improve error messages instead

---

**Last Updated:** 2025-01-27
