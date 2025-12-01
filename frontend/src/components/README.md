# Components

This directory contains all React components organized by feature domain.

## Directory Structure

| Directory      | Purpose                                                   |
| -------------- | --------------------------------------------------------- |
| `common/`      | Shared UI primitives (Card, Modal, LoadingSpinner, etc.)  |
| `layout/`      | App-level layout components (navigation, page structure)  |
| `errors/`      | Error boundaries and error display components             |
| `filters/`     | Filter panels and filter controls                         |
| `query/`       | Query builders, search inputs, and advanced filters       |
| `fits/`        | FITS image viewer components (JS9 integration)            |
| `skymap/`      | Sky coverage maps (D3-Celestial, Aladin Lite)             |
| `widgets/`     | Specialty widgets (charts, viewers, interactive elements) |
| `provenance/`  | Data provenance and QA display                            |
| `catalogs/`    | Catalog overlay and cross-match display                   |
| `crossmatch/`  | Source cross-matching panels                              |
| `rating/`      | QA rating and scoring components                          |
| `stats/`       | Statistics dashboard components                           |
| `summary/`     | Summary cards and grids                                   |
| `variability/` | Variability analysis components                           |
| `download/`    | Bulk download functionality                               |

## Component Pattern

Each component typically includes:

- `ComponentName.tsx` - The component implementation
- `ComponentName.test.tsx` - Unit tests (Vitest + Testing Library)
- `ComponentName.stories.tsx` - Storybook stories for visual development
- `index.ts` - Barrel exports for clean imports

## Import Convention

```tsx
// Import from directory index for cleaner imports
import { Card, Modal, LoadingSpinner } from "@/components/common";
import { FilterPanel } from "@/components/filters";
```
