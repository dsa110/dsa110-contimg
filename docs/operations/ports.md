# Port Configuration Reference

**Date:** 2025-11-17  
**Status:** ✅ Authoritative Reference

---

## Quick Reference

| Service          | Port     | URL                       | Config File      |
| ---------------- | -------- | ------------------------- | ---------------- |
| Frontend Dev     | **5173** | http://localhost:5173     | vite.config.ts   |
| Frontend Preview | **3210** | http://localhost:3210/ui/ | vite.config.ts   |
| Backend API      | **8000** | http://localhost:8000     | (backend config) |
| Vitest UI        | 5174     | http://localhost:5174     | vitest.config.ts |

---

## Port Usage

### Development Mode (npm run dev)

- ✅ `5173` - Frontend dev server (Vite default, hot reload)
- ✅ `8000` - Backend API

### Production Preview (npm run preview)

- ✅ `3210` - Frontend preview server (production build with /ui/ base path)
- ✅ `8000` - Backend API

### ❌ Common Mistakes

- ❌ `3000` - Common React default, NOT used here
- ❌ `8080` - Common dev default, NOT used here

---

## Why 5173 (dev) and 3210 (preview)?

- Dev mode uses Vite’s default **5173** for hot reload.
- Preview uses **3210** to avoid conflicts and mirror the `/ui/` base path used
  in production.

Dev server config (from `vite.config.ts`):

```typescript
server: {
  host: "0.0.0.0",
  port: parseInt(process.env.VITE_PORT || process.env.PORT || "5173", 10),
}
```

Preview config:

```typescript
preview: {
  port: parseInt(process.env.VITE_PORT || process.env.PORT || "3210", 10),
  host: "0.0.0.0",
  // ...
}
```

---

## Verification Commands

```bash
# Check what's actually running
lsof -i :5173   # Should show Vite dev server
lsof -i :3210   # Should show preview server (npm run preview)
lsof -i :8000   # Should show FastAPI backend

# Or use netstat
netstat -tlnp | grep -E "3210|5173|8000"

# Or use ss
ss -tlnp | grep -E "3210|5173|8000"
```

---

## In Documentation

When writing documentation or examples:

✅ **Correct for Development:**

```markdown
Navigate to http://localhost:5173 Frontend dev server at http://localhost:5173
API available at http://localhost:8000
```

✅ **Correct for Production Preview:**

```markdown
Navigate to http://localhost:3210/ui/ Frontend preview at
http://localhost:3210/ui/ API available at http://localhost:8000
```

---

## Environment Variables

Port can be overridden via environment variables:

```bash
# Override dev server port (not recommended)
VITE_PORT=4000 npm run dev

# Or
PORT=4000 npm run dev

# Defaults:
# - Dev mode (npm run dev): 5173
# - Preview mode (npm run preview): 3210
npm run dev
```

---

## Configuration Files

### Frontend: `vite.config.ts`

```typescript
export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: parseInt(process.env.VITE_PORT || process.env.PORT || "5173", 10),
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

- **2025-11-20:** Corrected port strategy to align with Vite conventions
  - Changed dev server default from 3210 → 5173 in `vite.config.ts`
  - Updated documentation to distinguish dev mode (5173) vs preview mode (3210)
  - Aligned with running Vite dev server and Vite ecosystem standards

- **2025-11-17:** Created authoritative reference after fixing port confusion
  - Fixed `.cursor/FIGMA_DESIGN_SYSTEM_RULES.md` (5173 → 3210)
  - Fixed `docs/README.md` (5173 → 3210)
  - Fixed `docs/health-check-fix.md` (5173 → 3210)
  - Created `.cursor/rules/project-ports.mdc`
  - Updated `.cursor/rules/frontend-focus.mdc`

---

**Remember:** Use **5173** for `npm run dev` and **3210** for preview. Avoid
generic defaults like 3000/8080 to stay consistent with the stack.
