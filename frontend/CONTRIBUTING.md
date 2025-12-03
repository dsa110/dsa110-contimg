# Contributing to the DSA-110 Frontend

Welcome! This guide will help you get started contributing to the frontend.

## Quick Start (5 minutes)

```bash
# 1. Install dependencies
npm install

# 2. Start the dev server (http://localhost:3000)
npm run dev

# 3. Run tests in watch mode
npm test

# 4. Start Storybook for component development (http://localhost:6006)
npm run storybook
```

## Development URLs

| Service     | URL                         | Notes                      |
| ----------- | --------------------------- | -------------------------- |
| Frontend    | http://localhost:3000       | Vite dev server with HMR   |
| Login Page  | http://localhost:3000/login | Authentication entry point |
| Backend API | http://localhost:8000       | FastAPI server             |
| Storybook   | http://localhost:6006       | Component development      |

## Demo Login Credentials

For local development, use these pre-configured accounts:

| Username   | Password   | Role     | Access Level                   |
| ---------- | ---------- | -------- | ------------------------------ |
| `admin`    | `admin`    | Admin    | Full access (read/write/admin) |
| `operator` | `operator` | Operator | Read + write access            |
| `viewer`   | `viewer`   | Viewer   | Read-only access               |

## Where to Find Things

| What you're looking for     | Where to look               |
| --------------------------- | --------------------------- |
| Page components (routes)    | `src/pages/`                |
| Reusable UI components      | `src/components/common/`    |
| Feature-specific components | `src/components/{feature}/` |
| Custom React hooks          | `src/hooks/`                |
| API client & data fetching  | `src/api/`                  |
| TypeScript types            | `src/types/`                |
| Utility functions           | `src/utils/`                |
| Test setup & utilities      | `src/testing/`              |
| E2E tests (Playwright)      | `e2e/`                      |
| Build configuration         | `config/build/`             |

## Component Organization

Each component directory follows this pattern:

```
src/components/example/
├── ExampleComponent.tsx       # Main component
├── ExampleComponent.test.tsx  # Unit tests (Vitest)
├── ExampleComponent.stories.tsx  # Storybook stories
└── index.ts                   # Barrel exports
```

## Common Tasks

### Adding a New Component

1. Create the component file in the appropriate `src/components/` subdirectory
2. Add tests in a `.test.tsx` file
3. Add Storybook stories in a `.stories.tsx` file
4. Export from the directory's `index.ts`

### Adding a New Page

1. Create the page component in `src/pages/`
2. Add the route in `src/router.tsx`
3. Add tests in a `.test.tsx` file

### Working with the API

```tsx
// Use React Query hooks from src/hooks/useQueries.ts
import { useImages, useSources } from "@/hooks/useQueries";

function MyComponent() {
  const { data, isLoading, error } = useImages();
  // ...
}
```

### Running Specific Tests

```bash
# Run tests for a specific file
npm test -- src/components/common/Card.test.tsx

# Run tests matching a pattern
npm test -- --grep "Card"

# Run E2E tests
npm run test:e2e
```

## Code Style

- **TypeScript**: Strict mode enabled
- **Formatting**: ESLint handles formatting (`npm run lint:fix`)
- **CSS**: Tailwind CSS utility classes
- **Testing**: Vitest + React Testing Library

## Key Libraries

| Library      | Purpose                 | Docs                                                 |
| ------------ | ----------------------- | ---------------------------------------------------- |
| React Query  | Server state management | [tanstack.com/query](https://tanstack.com/query)     |
| React Router | Client-side routing     | [reactrouter.com](https://reactrouter.com)           |
| Zustand      | Client state management | [zustand-demo.pmnd.rs](https://zustand-demo.pmnd.rs) |
| Tailwind CSS | Utility-first CSS       | [tailwindcss.com](https://tailwindcss.com)           |
| Vitest       | Unit testing            | [vitest.dev](https://vitest.dev)                     |
| Playwright   | E2E testing             | [playwright.dev](https://playwright.dev)             |
| Storybook    | Component development   | [storybook.js.org](https://storybook.js.org)         |

## Getting Help

- Check the [Architecture docs](docs/ARCHITECTURE.md)
- Browse existing components in Storybook (`npm run storybook`)
- Look at similar components for patterns to follow
