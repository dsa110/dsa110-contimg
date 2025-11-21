# Security Recommendations

This document outlines additional security protections that should be considered
for the DSA-110 Continuum Imaging Pipeline frontend application.

## ✅ Already Implemented

### Current Security Measures

1. **XSS Protection**: DOMPurify sanitization for all `dangerouslySetInnerHTML`
   usages
2. **Path Validation**: `sanitizePath()` function prevents open redirects
3. **Circuit Breaker**: API request circuit breaker pattern implemented
4. **Input Validation**: Form validation utilities exist
   (`src/utils/formValidation.ts`)
5. **Error Handling**: Comprehensive error classification and user-friendly
   messages
6. **Retry Logic**: Exponential backoff for API retries
7. **React Security**: No hook violations, proper context handling

---

## 🔒 Recommended Additional Protections

### 1. **Content Security Policy (CSP)**

**Priority: High**

Add CSP headers to prevent XSS, data injection, and clickjacking attacks.

**Implementation:**

- Add CSP meta tag in `index.html`
- Configure CSP for inline scripts (JS9 requires some inline scripts)
- Consider nonce-based CSP for better security

**Example:**

```html
<meta
  http-equiv="Content-Security-Policy"
  content="
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval' https://code.jquery.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob:;
  connect-src 'self' ws: wss:;
  font-src 'self';
"
/>
```

**Note:** JS9 requires `'unsafe-inline'` and `'unsafe-eval'` which reduces CSP
effectiveness. Consider migrating to nonce-based CSP.

---

### 2. **HTTP Security Headers**

**Priority: High**

Configure security headers via server (nginx/reverse proxy) or add to
`index.html`.

**Recommended Headers:**

```html
<meta http-equiv="X-Content-Type-Options" content="nosniff" />
<meta http-equiv="X-Frame-Options" content="SAMEORIGIN" />
<meta http-equiv="X-XSS-Protection" content="1; mode=block" />
<meta http-equiv="Referrer-Policy" content="strict-origin-when-cross-origin" />
<meta
  http-equiv="Permissions-Policy"
  content="geolocation=(), microphone=(), camera=()"
/>
```

**Better:** Configure these on the server (nginx/Apache) for stronger
enforcement.

---

### 3. **API Request Security**

**Priority: Medium**

Add additional security measures for API requests:

#### A. Request Signing/CSRF Protection

- Implement CSRF tokens if backend supports them
- Add request signing for critical operations
- Implement request ID/timestamp to prevent replay attacks

#### B. Rate Limiting (Client-Side)

- Implement client-side rate limiting for API calls
- Add debouncing/throttling for user-triggered requests (already partially done)
- Consider request queuing for batch operations

**Example Implementation:**

```typescript
// src/utils/rateLimiter.ts
export function createRateLimiter(maxRequests: number, windowMs: number) {
  const requests: number[] = [];

  return function canMakeRequest(): boolean {
    const now = Date.now();
    // Remove old requests outside the window
    while (requests.length > 0 && requests[0] < now - windowMs) {
      requests.shift();
    }

    if (requests.length >= maxRequests) {
      return false;
    }

    requests.push(now);
    return true;
  };
}
```

#### C. Request Validation

- Validate all API request parameters before sending
- Sanitize user input before API calls
- Implement request size limits

---

### 4. **LocalStorage Security**

**Priority: Medium**

Current usage: Preferences and UI state stored in localStorage.

**Recommendations:**

- **Encryption**: Encrypt sensitive data in localStorage
- **Expiration**: Implement TTL for stored data
- **Validation**: Validate data retrieved from localStorage before use
- **Scope**: Avoid storing sensitive information (tokens, passwords, PII)

**Example:**

```typescript
// src/utils/secureStorage.ts
import CryptoJS from "crypto-js";

const ENCRYPTION_KEY =
  import.meta.env.VITE_STORAGE_KEY || "fallback-key-change-in-prod";

export function setSecureItem(key: string, value: any): void {
  const encrypted = CryptoJS.AES.encrypt(
    JSON.stringify(value),
    ENCRYPTION_KEY
  ).toString();
  localStorage.setItem(key, encrypted);
}

export function getSecureItem(key: string): any | null {
  try {
    const encrypted = localStorage.getItem(key);
    if (!encrypted) return null;
    const decrypted = CryptoJS.AES.decrypt(encrypted, ENCRYPTION_KEY);
    return JSON.parse(decrypted.toString(CryptoJS.enc.Utf8));
  } catch {
    return null;
  }
}
```

---

### 5. **Environment Variable Security**

**Priority: High**

**Current State:** Environment variables exposed to client (VITE\_\*)

**Recommendations:**

- **Never expose secrets**: Only expose public configuration via `VITE_*`
- **Validate env vars**: Add runtime validation for required environment
  variables
- **Document requirements**: Create `.env.example` with all required variables
- **Type safety**: Use TypeScript types for environment variables

**Example:**

```typescript
// src/config/env.ts
interface EnvConfig {
  VITE_API_URL?: string;
  VITE_SENTRY_DSN?: string;
  VITE_CARTA_FRONTEND_URL?: string;
  VITE_CARTA_BACKEND_URL?: string;
}

function validateEnv(): EnvConfig {
  const config: EnvConfig = {
    VITE_API_URL: import.meta.env.VITE_API_URL,
    VITE_SENTRY_DSN: import.meta.env.VITE_SENTRY_DSN,
    VITE_CARTA_FRONTEND_URL: import.meta.env.VITE_CARTA_FRONTEND_URL,
    VITE_CARTA_BACKEND_URL: import.meta.env.VITE_CARTA_BACKEND_URL,
  };

  // Validate required variables
  // Add validation logic here

  return config;
}

export const env = validateEnv();
```

---

### 6. **Input Validation & Sanitization**

**Priority: Medium**

**Current State:** Form validation utilities exist, but may not be used
everywhere.

**Recommendations:**

- **Consistent validation**: Use validation utilities for all user inputs
- **Server-side validation**: Never trust client-side validation alone
- **Sanitize outputs**: Sanitize all user-generated content before display
- **Type checking**: Use TypeScript strict mode to catch type issues

**Enhancement:**

```typescript
// src/utils/sanitize.ts
import DOMPurify from "dompurify";

export function sanitizeInput(input: string): string {
  // Remove potentially dangerous characters
  return DOMPurify.sanitize(input, {
    ALLOWED_TAGS: [], // Strip all tags for plain text
    ALLOWED_ATTR: [],
  });
}

export function sanitizeUrl(url: string): string | null {
  try {
    const parsed = new URL(url);
    // Only allow http/https
    if (!["http:", "https:"].includes(parsed.protocol)) {
      return null;
    }
    return url;
  } catch {
    return null;
  }
}
```

---

### 7. **Error Handling & Information Disclosure**

**Priority: Medium**

**Current State:** Error messages are user-friendly, but check for information
leakage.

**Recommendations:**

- **Logging**: Ensure sensitive data is not logged to console in production
- **Error messages**: Don't expose internal paths, stack traces, or API keys
- **Error boundaries**: Already implemented ✅
- **Monitoring**: Use Sentry or similar for error tracking (already configured
  ✅)

**Check:**

```typescript
// src/utils/logger.ts
// Ensure production logging doesn't expose sensitive info
if (import.meta.env.PROD) {
  // Sanitize logs in production
  logger.apiError = (message: string, error: any) => {
    // Strip sensitive information from errors
    const sanitized = {
      ...error,
      config: error.config
        ? {
            ...error.config,
            headers: {}, // Don't log headers in production
            data: undefined, // Don't log request data
          }
        : undefined,
    };
    console.error(message, sanitized);
  };
}
```

---

### 8. **Dependency Security**

**Priority: High**

**Recommendations:**

- **Regular audits**: Run `npm audit` regularly
- **Automated scanning**: Integrate dependency scanning in CI/CD
- **Pin versions**: Consider using exact versions for critical dependencies
- **Update strategy**: Keep dependencies updated, test thoroughly

**Automation:**

```bash
# Add to package.json scripts
"security:audit": "npm audit",
"security:fix": "npm audit fix",
"security:check": "npm audit --audit-level=moderate"
```

---

### 9. **Authentication & Authorization**

**Priority: High** (if applicable)

**Current State:** No authentication visible in frontend code.

**If authentication is added:**

- **Token storage**: Use httpOnly cookies (preferred) or secure localStorage
- **Token refresh**: Implement automatic token refresh
- **Logout**: Clear all tokens and stored data on logout
- **Route protection**: Protect routes that require authentication
- **Session management**: Implement session timeout

---

### 10. **Subresource Integrity (SRI)**

**Priority: Medium**

For external scripts (e.g., jQuery from CDN), add SRI hashes.

**Example:**

```html
<script
  src="https://code.jquery.com/jquery-3.7.1.min.js"
  integrity="sha256-...="
  crossorigin="anonymous"
></script>
```

---

### 11. **Production Build Security**

**Priority: Medium**

**Recommendations:**

- **Source maps**: Disable or exclude source maps in production builds
- **Minification**: Ensure code is minified (Vite does this ✅)
- **Tree shaking**: Remove unused code (Vite does this ✅)
- **Environment checks**: Ensure dev-only code is excluded from production

**Vite config:**

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    sourcemap: false, // Disable source maps in production
    minify: "terser", // Use terser for better minification
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
      },
    },
  },
});
```

---

### 12. **WebSocket Security**

**Priority: Medium**

**Current State:** WebSocket connections used for real-time updates.

**Recommendations:**

- **WSS**: Use `wss://` (secure WebSocket) in production
- **Origin validation**: Validate WebSocket origins
- **Message validation**: Validate all WebSocket messages
- **Reconnection**: Implement secure reconnection logic

---

### 13. **Logging & Monitoring**

**Priority: Low-Medium**

**Current State:** Sentry configured for error tracking.

**Recommendations:**

- **Structured logging**: Use structured logging format
- **Log levels**: Implement proper log levels (debug, info, warn, error)
- **Sensitive data**: Never log passwords, tokens, or PII
- **Performance monitoring**: Monitor API response times
- **User behavior**: Track security-relevant events (failed logins, etc.)

---

## 📋 Implementation Priority

### Immediate (High Priority)

1. HTTP Security Headers
2. Environment Variable Security
3. Dependency Security (audit)
4. Content Security Policy (CSP)

### Short-term (Medium Priority)

5. LocalStorage Security (encryption)
6. API Request Security enhancements
7. Input Validation improvements
8. Error Handling review

### Long-term (Low-Medium Priority)

9. Authentication/Authorization (if needed)
10. Subresource Integrity
11. Production Build Security
12. WebSocket Security
13. Logging & Monitoring enhancements

---

## 🔍 Security Testing

**Recommended Testing:**

- **Penetration testing**: Regular security audits
- **Dependency scanning**: Automated in CI/CD
- **Static analysis**: Continue using Codacy ✅
- **OWASP Top 10**: Review against OWASP Top 10
- **Security headers**: Test with securityheaders.com
- **CSP evaluation**: Use CSP evaluator tools

---

## 📚 Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Content Security Policy (CSP)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Web Security Best Practices](https://infosec.mozilla.org/guidelines/web_security)
- [React Security Best Practices](https://reactjs.org/docs/dom-elements.html#dangerouslysetinnerhtml)

---

## Notes

- **JS9 Compatibility**: JS9 requires `'unsafe-inline'` and `'unsafe-eval'` for
  CSP, which reduces CSP effectiveness. Consider migrating JS9 to use nonces or
  separate script tags.
- **Backend Dependency**: Some security measures (CSRF tokens, rate limiting)
  require backend support.
- **Balancing Security vs Usability**: Some recommendations may impact user
  experience. Test thoroughly before implementing.
