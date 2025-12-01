# Frontend Project Documentation

## Overview

This project is a frontend application designed to handle and display provenance
information and error responses in a user-friendly manner. It utilizes React and
TypeScript to create reusable components and hooks that manage state and data
effectively.

## Project Structure

```text
frontend/
├── config/                    # Build configuration
│   └── build/                 # PostCSS and Tailwind configs
├── docs/                      # Frontend-specific documentation
├── e2e/                       # Playwright end-to-end tests
├── public/                    # Static assets
│   ├── celestial-data/        # D3-Celestial star/constellation data
│   └── docs/                  # Public documentation files
├── scripts/                   # Build and dev utility scripts
├── src/                       # Source code
│   ├── api/                   # API client and resilience patterns
│   │   └── resilience/        # Circuit breaker, retry logic
│   ├── components/            # Reusable React components
│   │   ├── catalogs/          # Catalog overlay components
│   │   ├── common/            # Shared UI components (Card, Modal, etc.)
│   │   ├── crossmatch/        # Source cross-matching panels
│   │   ├── download/          # Bulk download functionality
│   │   ├── errors/            # Error display and boundaries
│   │   ├── filters/           # Filter panels and controls
│   │   ├── fits/              # FITS image viewer components
│   │   ├── layout/            # App layout and navigation
│   │   ├── provenance/        # Data provenance display
│   │   ├── query/             # Query builders and filters
│   │   ├── rating/            # QA rating components
│   │   ├── skymap/            # Sky coverage visualization
│   │   ├── stats/             # Statistics dashboard
│   │   ├── summary/           # Summary cards and grids
│   │   ├── variability/       # Variability analysis components
│   │   └── widgets/           # Specialty widgets (Aladin, charts)
│   ├── config/                # Runtime configuration
│   ├── constants/             # Application constants
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Third-party library setup
│   ├── pages/                 # Page components (routes)
│   ├── stores/                # Zustand state stores
│   ├── testing/               # Test utilities and setup
│   ├── types/                 # TypeScript type definitions
│   └── utils/                 # Utility functions
├── vendor/                    # Vendored dependencies (aladin-lite)
├── eslint.config.js           # ESLint configuration
├── playwright.config.ts       # Playwright E2E test config
├── tailwind.config.js         # Tailwind CSS (symlink to config/build/)
├── tsconfig.json              # TypeScript configuration
├── tsconfig.test.json         # TypeScript config for tests
└── vite.config.ts             # Vite build configuration
```

### Key Directories

- **src/components/**: Organized by feature domain. Each subdirectory contains
  related components with their tests (`*.test.tsx`) and stories (`*.stories.tsx`).

- **src/pages/**: Route-level page components. Each page has a corresponding test file.

- **src/testing/**: Vitest setup and test utilities. Contains `setup.ts` for
  global test configuration.

- **config/build/**: CSS build configuration (PostCSS, Tailwind). Referenced by
  `vite.config.ts`.

- **e2e/**: Playwright end-to-end tests for full integration testing.

## Getting Started

> **📖 For a complete guide to dev vs production services, see
> [docs/ops/SERVICES.md](../docs/ops/SERVICES.md)**

To get started with the project, follow these steps:

1. **Install dependencies**:

   ```bash
   npm install
   ```

2. **Run the development server** (port 3000):

   ```bash
   npm run dev
   ```

3. **Build for production**:

   ```bash
   npm run build
   ```

4. **Run Storybook** (component development, port 6006):

   ```bash
   npm run storybook
   ```

   See the [Storybook Guide](../docs/STORYBOOK.md) for detailed documentation on
   developing components with Storybook.

5. **Run tests**:

   ```bash
   npm run test        # Watch mode
   npm run test:run    # Single run
   npm run test:e2e    # Playwright E2E tests
   ```

## Components

### Provenance Components

- **ProvenanceStrip**: Displays a compact strip showing provenance information.
- **ProvenanceBadge**: Displays a badge indicating the quality assessment (QA)
  grade.
- **ProvenanceLink**: Renders a link to the QA report or other relevant URLs.

### Error Components

- **ErrorDisplay**: Presents a normalized error response to the user.
- **ErrorDetailsExpander**: Allows users to expand and view detailed error
  information.
- **ErrorActionHint**: Provides actionable hints based on the displayed error.

## Hooks

- **useErrorHandler**: Manages error states and provides functions to handle
  errors.
- **useProvenance**: Retrieves and manages provenance data.
- **useErrorMapping**: Maps error codes to user-friendly messages and actions.

## Utilities

- **errorCodes**: Constants representing various error codes.
- **errorMapper**: Maps error responses to user-friendly messages.
- **coordinateFormatter**: Utility functions for formatting coordinates.
- **relativeTime**: Converts timestamps to relative time strings.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for
discussion.

## License

This project is licensed under the MIT License. See the LICENSE file for
details.
