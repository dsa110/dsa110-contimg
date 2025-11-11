# DSA-110 Dashboard: Testing & Quality Assurance

**Date:** 2025-01-XX  
**Status:** Consolidated testing documentation  
**Audience:** Frontend developers, QA engineers

---

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Test Setup](#test-setup)
3. [Unit Tests](#unit-tests)
4. [Component Tests](#component-tests)
5. [Integration Tests](#integration-tests)
6. [E2E Tests](#e2e-tests)
7. [Test Coverage](#test-coverage)
8. [CI/CD Integration](#cicd-integration)

---

## Testing Overview

### Testing Strategy

**Multi-Layer Approach:**
1. **Unit Tests** - Pure functions and utilities
2. **Component Tests** - React components with user interactions
3. **Integration Tests** - API hooks and data flow
4. **E2E Tests** - Full user workflows (Playwright)

### Current Test Coverage

**Test Files:**
- `useSelectionState.test.ts` - Selection logic unit tests
- `MSTable.test.tsx` - Component tests
- `ControlPage.test.tsx` - Integration tests
- `ImageBrowser.test.tsx` - Component tests

**Coverage Status:** Limited (needs expansion)

---

## Test Setup

### Option 1: Docker (Recommended)

**Benefits:**
- Consistent environment
- No Node version conflicts
- Isolated dependencies

**Quick Start:**
```bash
cd frontend

# Run tests once
./test.sh

# Run tests in watch mode
./test.sh watch

# Run tests with UI
./test.sh ui

# Run tests with coverage
./test.sh coverage
```

**Manual Docker:**
```bash
# Build image
docker build -t dsa110-frontend-test -f Dockerfile.dev .

# Run tests
docker run --rm -v "$PWD:/app" -v /app/node_modules dsa110-frontend-test npm test

# Watch mode
docker run --rm -it -v "$PWD:/app" -v /app/node_modules dsa110-frontend-test npm test -- --watch
```

---

### Option 2: Conda Environment

**Using casa6:**
```bash
conda activate casa6
cd frontend
npm install
npm test
```

**Requirements:**
- Node.js v22+ (available in casa6)
- npm dependencies installed

---

### Option 3: Docker Compose

**Using docker-compose:**
```bash
docker-compose -f docker-compose.test.yml run --rm frontend-test

# Watch mode
docker-compose -f docker-compose.test.yml run --rm frontend-test -- --watch

# UI mode
docker-compose -f docker-compose.test.yml run --rm -p 51204:51204 frontend-test -- --ui
```

---

## Unit Tests

### Testing Pure Functions

**Example (`useSelectionState.test.ts`):**
```typescript
import { computeSelectedMS } from '../utils/selectionLogic';

describe('computeSelectedMS', () => {
  it('should handle unchecking checkbox', () => {
    const result = computeSelectedMS(
      [],                    // paths (empty after uncheck)
      ['/data/ms1.ms'],      // prevList (had one selected)
      '/data/ms1.ms'         // currentSelectedMS
    );
    expect(result).toBe(''); // Should be empty
  });
  
  it('should handle selecting new MS', () => {
    const result = computeSelectedMS(
      ['/data/ms2.ms'],      // paths (new selection)
      ['/data/ms1.ms'],      // prevList (old selection)
      '/data/ms2.ms'         // currentSelectedMS
    );
    expect(result).toBe('/data/ms2.ms');
  });
});
```

### Testing Utilities

**Error Utils:**
```typescript
import { classifyError, getUserFriendlyMessage } from '../utils/errorUtils';

describe('classifyError', () => {
  it('should classify network errors', () => {
    const error = new AxiosError('Network Error');
    const classification = classifyError(error);
    expect(classification.type).toBe('network');
    expect(classification.retryable).toBe(true);
  });
});
```

---

## Component Tests

### Testing React Components

**Example (`MSTable.test.tsx`):**
```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MSTable from '../components/MSTable';

describe('MSTable', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  
  it('should render MS list', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MSTable msList={mockMSList} />
      </QueryClientProvider>
    );
    
    expect(screen.getByText('/data/ms1.ms')).toBeInTheDocument();
  });
  
  it('should handle selection', () => {
    const { getByRole } = render(
      <QueryClientProvider client={queryClient}>
        <MSTable msList={mockMSList} />
      </QueryClientProvider>
    );
    
    const checkbox = getByRole('checkbox', { name: '/data/ms1.ms' });
    fireEvent.click(checkbox);
    
    expect(checkbox).toBeChecked();
  });
});
```

### Testing with React Query

**Mocking Queries:**
```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
};

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};
```

---

## Integration Tests

### Testing API Hooks

**Example (`ControlPage.test.tsx`):**
```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMSList } from '../api/queries';

describe('useMSList', () => {
  it('should fetch MS list', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
    
    const { result } = renderHook(() => useMSList(), { wrapper });
    
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    
    expect(result.current.data).toBeDefined();
  });
});
```

### Testing Mutations

**Example:**
```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useCreateJob } from '../api/queries';

describe('useCreateJob', () => {
  it('should create job', async () => {
    const { result } = renderHook(() => useCreateJob(), { wrapper });
    
    result.current.mutate({
      job_type: 'image',
      ms_paths: ['/data/ms1.ms'],
    });
    
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    
    expect(result.current.data?.job_id).toBeDefined();
  });
});
```

---

## E2E Tests

### Playwright Setup

**Configuration (`playwright.config.ts`):**
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:5173',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

### E2E Test Example

**Example (`e2e/dashboard.spec.ts`):**
```typescript
import { test, expect } from '@playwright/test';

test('should display pipeline status', async ({ page }) => {
  await page.goto('/dashboard');
  
  await expect(page.getByText('Pipeline Status')).toBeVisible();
  await expect(page.getByText('Queue')).toBeVisible();
});

test('should navigate to sources page', async ({ page }) => {
  await page.goto('/dashboard');
  await page.click('text=Sources');
  
  await expect(page).toHaveURL('/sources');
  await expect(page.getByText('Source Monitoring')).toBeVisible();
});
```

---

## Test Coverage

### Coverage Reports

**Generate Coverage:**
```bash
npm test -- --coverage
```

**Coverage Targets:**
- Statements: >80%
- Branches: >75%
- Functions: >80%
- Lines: >80%

### Coverage Gaps

**Current Gaps:**
- API hooks (limited coverage)
- Error handling (needs expansion)
- WebSocket client (no tests)
- Complex components (needs more tests)

---

## CI/CD Integration

### GitHub Actions

**Example Workflow:**
```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '22'
      - run: cd frontend && npm ci
      - run: cd frontend && npm test
      - run: cd frontend && npm run build
```

---

## Best Practices

### Writing Tests

1. **Test Behavior, Not Implementation**
   - Focus on what users see and do
   - Avoid testing internal implementation details

2. **Use Descriptive Test Names**
   - `should display error message when API fails`
   - Not: `test1` or `works`

3. **Arrange-Act-Assert Pattern**
   ```typescript
   it('should handle selection', () => {
     // Arrange
     const msList = [{ path: '/data/ms1.ms' }];
     
     // Act
     const result = computeSelectedMS([], [], '/data/ms1.ms');
     
     // Assert
     expect(result).toBe('/data/ms1.ms');
   });
   ```

4. **Mock External Dependencies**
   - Mock API calls
   - Mock WebSocket connections
   - Use test doubles for complex dependencies

5. **Keep Tests Fast**
   - Avoid real network calls
   - Use mocks and stubs
   - Parallelize when possible

---

## See Also

- [Frontend Architecture](../concepts/dashboard_frontend_architecture.md) - Component architecture
- [Development Workflow](./dashboard_development_workflow.md) - Development setup
- [Error Handling](../concepts/dashboard_error_handling.md) - Error handling patterns

