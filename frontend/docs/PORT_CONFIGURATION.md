# Port Configuration Reference

**Date:** 2025-11-17  
**Status:** ✅ Authoritative Reference

---

## Quick Reference

| Service          | Port     | URL                       | Config File      |
| ---------------- | -------- | ------------------------- | ---------------- |
| Frontend Dev     | **3210** | http://localhost:3210     | vite.config.ts   |
| Frontend Preview | **3210** | http://localhost:3210/ui/ | vite.config.ts   |
| Backend API      | **8000** | http://localhost:8000     | (backend config) |
| Vitest UI        | 5174     | http://localhost:5174     | vitest.config.ts |

---

## ❌ Common Mistakes

### DON'T Use These Ports

- ❌ `5173` - This is Vite's DEFAULT, but NOT what this project uses
- ❌ `3000` - Common React default, NOT used here
- ❌ `8080` - Common dev default, NOT used here

### ✅ DO Use These Ports

- ✅ `3210` - Frontend dev and preview
- ✅ `8000` - Backend API

---

## Why Port 3210?

This project explicitly configures port 3210 in `vite.config.ts`:

```typescript
server: {
  port: parseInt(process.env.VITE_PORT || process.env.PORT || "3210", 10),
}
```

This avoids conflicts with other services and provides a consistent development
environment.

---

## Verification Commands

```bash
# Check what's actually running
lsof -i :3210   # Should show Vite dev server
lsof -i :8000   # Should show FastAPI backend

# Or use netstat
netstat -tlnp | grep -E "3210|8000"

# Or use ss
ss -tlnp | grep -E "3210|8000"
```

---

## In Documentation

When writing documentation or examples:

✅ **Correct:**

```markdown
Navigate to http://localhost:3210 Frontend available at http://localhost:3210
API available at http://localhost:8000
```

❌ **Wrong:**

```markdown
Navigate to http://localhost:5173 Frontend available at http://localhost:5173
```

---

## Environment Variables

Port can be overridden via environment variables:

```bash
# Override frontend port (not recommended)
VITE_PORT=4000 npm run dev

# Or
PORT=4000 npm run dev

# Default if not set: 3210
npm run dev
```

---

## Configuration Files

### Frontend: `vite.config.ts`

```typescript
export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: parseInt(process.env.VITE_PORT || process.env.PORT || "3210", 10),
    // ...
  },
  preview: {
    port: parseInt(process.env.VITE_PORT || process.env.PORT || "3210", 10),
    host: "0.0.0.0",
    // ...
  },
});
```

### Package Scripts: `package.json`

```json
{
  "scripts": {
    "dev": "bash scripts/start-dev.sh",
    "preview": "vite preview --port ${VITE_PORT:-3210} --host 0.0.0.0 --base /ui/"
  }
}
```

---

## Related Documentation

- `.cursor/rules/project-ports.mdc` - Cursor rule for AI agents
- `.cursor/rules/frontend-focus.mdc` - Frontend development rules
- `vite.config.ts` - Actual port configuration
- `package.json` - Script definitions

---

## Update History

- **2025-11-17:** Created authoritative reference after fixing port confusion
  - Fixed `.cursor/FIGMA_DESIGN_SYSTEM_RULES.md` (5173 → 3210)
  - Fixed `docs/README.md` (5173 → 3210)
  - Fixed `docs/health-check-fix.md` (5173 → 3210)
  - Created `.cursor/rules/project-ports.mdc`
  - Updated `.cursor/rules/frontend-focus.mdc`

---

**Remember:** Always use port **3210** for frontend, not 5173!
