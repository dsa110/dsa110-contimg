# Moved

See `docs/how-to/dashboard.md`.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Code Style & Standards](#code-style-standards)
6. [Debugging](#debugging)
7. [Common Tasks](#common-tasks)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Node.js v22+** (available in `casa6` conda environment)
- **npm** (comes with Node.js)
- **Git** (for version control)
- **Backend API** running on `localhost:8000`

### Optional Tools

- **Docker** (for consistent testing environment)
- **VS Code** (recommended IDE)
- **React DevTools** (browser extension)
- **React Query DevTools** (built into app in dev mode)

---

## Development Environment Setup

### Step 1: Clone Repository

```bash
cd /data/dsa110-contimg
git clone <repository-url>
cd frontend
```

### Step 2: Install Dependencies

**Using casa6 conda environment (recommended):**

```bash
conda activate casa6
npm install
```

**Using Docker (alternative):**

```bash
docker run -it -v "$PWD:/app" -w /app node:22 npm install
```

### Step 3: Start Development Servers

**Terminal 1 - Backend API:**

```bash
cd /data/dsa110-contimg
conda activate casa6
uvicorn dsa110_contimg.api.server:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend Dev Server:**

```bash
cd /data/dsa110-contimg/frontend
conda activate casa6
npm run dev -- --host 0.0.0.0 --port 5173
```

### Step 4: Verify Setup

1. Open `http://localhost:5173` in browser
2. Check browser console for errors
3. Verify API connection (should see data loading)

---

## Project Structure

### Directory Layout

```
frontend/
├── src/
│   ├── api/                    # API client & React Query hooks
│   │   ├── client.ts           # Axios instance
│   │   ├── queries.ts          # React Query hooks
│   │   ├── types.ts            # TypeScript interfaces
│   │   └── websocket.ts        # WebSocket client
│   ├── components/             # React components
│   │   ├── Dashboard/          # Dashboard components
│   │   ├── Sky/               # Sky/image components
│   │   ├── Sources/           # Source monitoring components
│   │   └── shared/            # Shared components
│   ├── pages/                  # Page-level components
│   │   ├── DashboardPage.tsx
│   │   ├── ControlPage.tsx
│   │   └── ...
│   ├── contexts/              # React contexts
│   ├── hooks/                 # Custom hooks
│   ├── theme/                 # MUI theme
│   ├── utils/                 # Utility functions
│   ├── App.tsx                # Root component
│   └── main.tsx                # Entry point
├── public/                    # Static assets
├── tests/                     # Test files
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/new-feature-name
```

### 2. Make Changes

- Write code with TypeScript type safety
- Follow component patterns
- Add tests for new features
- Update documentation if needed

### 3. Test Locally

```bash
# Run tests
npm test

# Type check
npm run type-check

# Lint
npm run lint

# Build (verify no errors)
npm run build
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
```

**Commit Message Format:**

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting
- `refactor:` - Code refactoring
- `test:` - Tests
- `chore:` - Build/tooling

### 5. Push and Create PR

```bash
git push origin feature/new-feature-name
# Create PR on GitHub
```

---

## Code Style & Standards

### TypeScript

**Use TypeScript for all new code:**

```typescript
// Good
interface Props {
  data: PipelineStatus;
  onUpdate: (status: PipelineStatus) => void;
}

// Bad
const Component = (props: any) => { ... }
```

### Component Structure

**Standard Component Pattern:**

```typescript
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Box, Typography } from "@mui/material";

interface ComponentProps {
  id: string;
}

export default function Component({ id }: ComponentProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["resource", id],
    queryFn: () => apiClient.get(`/resource/${id}`),
  });

  if (isLoading) return <CircularProgress />;
  if (!data) return <Alert>No data</Alert>;

  return (
    <Box>
      <Typography>{data.name}</Typography>
    </Box>
  );
}
```

### Naming Conventions

- **Components:** PascalCase (`DashboardPage.tsx`)
- **Hooks:** camelCase starting with `use` (`usePipelineStatus`)
- **Utilities:** camelCase (`formatDate`, `classifyError`)
- **Constants:** UPPER_SNAKE_CASE (`API_BASE_URL`)

---

## Debugging

### React DevTools

**Install Browser Extension:**

- Chrome: React Developer Tools
- Firefox: React Developer Tools

**Features:**

- Component tree inspection
- Props and state viewing
- Performance profiling

### React Query DevTools

**Built-in DevTools (dev mode only):**

- Query cache inspection
- Query status monitoring
- Cache invalidation testing

### Browser Console

**Common Debugging:**

```typescript
// Log query data
console.log("Query data:", data);

// Log errors
console.error("Error:", error);

// Log WebSocket messages
wsClient.on("message", (data) => {
  console.log("WS message:", data);
});
```

### Network Tab

**Check API Calls:**

- Open browser DevTools :arrow_right: Network tab
- Filter by "Fetch/XHR"
- Inspect request/response
- Check for errors (4xx, 5xx)

---

## Common Tasks

### Adding a New Page

1. **Create Page Component:**

```typescript
// src/pages/NewPage.tsx
export default function NewPage() {
  return <Box>New Page</Box>;
}
```

2. **Add Route:**

```typescript
// src/App.tsx
import NewPage from "./pages/NewPage";

<Route path="/new-page" element={<NewPage />} />;
```

3. **Add Navigation Link:**

```typescript
// src/components/Navigation.tsx
<MenuItem component={Link} to="/new-page">
  New Page
</MenuItem>
```

### Adding a New API Hook

1. **Define Type:**

```typescript
// src/api/types.ts
export interface NewResource {
  id: string;
  name: string;
}
```

2. **Create Hook:**

```typescript
// src/api/queries.ts
export function useNewResource(id: string) {
  return useQuery({
    queryKey: ["resource", id],
    queryFn: () => apiClient.get<NewResource>(`/resource/${id}`),
  });
}
```

3. **Use in Component:**

```typescript
const { data } = useNewResource("123");
```

### Adding a New Component

1. **Create Component:**

```typescript
// src/components/NewComponent.tsx
interface Props {
  data: DataType;
}

export default function NewComponent({ data }: Props) {
  return <Box>{/* Component JSX */}</Box>;
}
```

2. **Export from index (if needed):**

```typescript
// src/components/index.ts
export { default as NewComponent } from "./NewComponent";
```

---

## Troubleshooting

### API Connection Issues

**Problem:** Frontend can't connect to backend

**Solutions:**

1. Check backend is running: `curl http://localhost:8000/api/status`
2. Check CORS settings in FastAPI backend
3. Verify `.env.development` has correct `VITE_API_URL`
4. Check browser console for CORS errors

### TypeScript Errors

**Problem:** TypeScript compilation errors

**Solutions:**

```bash
# Run type checking
npm run type-check

# Check specific file
npx tsc --noEmit src/pages/DashboardPage.tsx
```

### Build Errors

**Problem:** Production build fails

**Solutions:**

```bash
# Clean build
rm -rf dist node_modules/.vite
npm run build

# Check for missing dependencies
npm install
```

### Hot Reload Not Working

**Problem:** Changes not reflected in browser

**Solutions:**

1. Check Vite dev server is running
2. Hard refresh browser (Ctrl+Shift+R)
3. Restart dev server
4. Clear browser cache

### Port Already in Use

**Problem:** Port 5173 already in use

**Solutions:**

```bash
# Use different port (if 5173 is busy)
npm run dev -- --port 5174

# Or kill process using port
lsof -ti:5173 | xargs kill
```

---

## See Also

- [Frontend Architecture](../../architecture/dashboard/dashboard_frontend_architecture.md) -
  Architecture details
- [Testing Guide](./dashboard_development_workflow.md) - Testing setup
- [Deployment Guide](./dashboard_deployment.md) - Deployment steps
