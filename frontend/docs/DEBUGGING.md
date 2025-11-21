# Frontend Debugging Guide

**Date:** 2025-11-14

## Quick Debugging Strategies

### 1. **React DevTools**

Install React DevTools browser extension to inspect component state in
real-time:

- View component props and state
- Track state changes
- Inspect React Query cache

### 2. **Console Logging Helper**

Add temporary logging to track state changes:

```typescript
// In ControlPage.tsx
useEffect(() => {
  console.log("🔵 selectedMS:", selectedMS);
  console.log("🔵 selectedMSList:", selectedMSList);
  console.log("🔵 msMetadata:", msMetadata);
}, [selectedMS, selectedMSList, msMetadata]);
```

### 3. **Write Tests First (TDD)**

Before fixing bugs, write a failing test that reproduces the issue:

```typescript
// In MSTable.test.tsx
it('should deselect MS when checkbox is unchecked', () => {
  // Test the exact scenario that's failing
  const onSelectionChange = vi.fn();

  render(
    <MSTable
      data={mockData}
      selected={['/data/ms1.ms']}
      onSelectionChange={onSelectionChange}
    />
  );

  const checkbox = screen.getByRole('checkbox', { checked: true });
  fireEvent.click(checkbox);

  expect(onSelectionChange).toHaveBeenCalledWith([]);
});
```

### 4. **Run Tests in Watch Mode**

```bash
cd frontend
npm test  # Watch mode - reruns on file changes
```

### 5. **Use TypeScript Strict Mode**

Enable strict TypeScript checks to catch issues at compile time:

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true
  }
}
```

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode (auto-rerun on changes)
npm test -- --watch

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## Test Structure

- **Unit Tests**: Test pure functions and hooks in isolation (`*.test.ts`)
- **Component Tests**: Test React components with user interactions
  (`*.test.tsx`)
- **Integration Tests**: Test multiple components working together

## Common Patterns

### Testing State Updates

```typescript
const { result } = renderHook(() => {
  const [state, setState] = useState(initial);
  return { state, setState };
});

act(() => {
  result.current.setState(newValue);
});

expect(result.current.state).toBe(newValue);
```

### Testing Event Handlers

```typescript
const onSelectionChange = vi.fn();
render(<MSTable onSelectionChange={onSelectionChange} />);

fireEvent.click(checkbox);
expect(onSelectionChange).toHaveBeenCalledWith(expectedValue);
```

## Debugging Checklist

When fixing bugs:

1. ✅ Write a failing test first
2. ✅ Fix the code
3. ✅ Verify test passes
4. ✅ Check for edge cases
5. ✅ Run full test suite
6. ✅ Verify manually in browser
