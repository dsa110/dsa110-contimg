# TypeScript Types

Centralized type definitions for the application.

## Importing Types

```tsx
import type { ImageSummary, SourceDetail, ErrorResponse } from "@/types";
```

## Type Categories

### API Entity Types (`api.ts`)

Core data types matching backend API responses:

| Type            | Description                   |
| --------------- | ----------------------------- |
| `ImageSummary`  | Image list item               |
| `ImageDetail`   | Full image with metadata      |
| `SourceSummary` | Source list item              |
| `SourceDetail`  | Full source with observations |
| `MSMetadata`    | Measurement Set metadata      |
| `JobSummary`    | Pipeline job list item        |
| `JobDetail`     | Full job with logs            |

Common base types:

| Type              | Description                                         |
| ----------------- | --------------------------------------------------- |
| `QAGrade`         | `"good" \| "warn" \| "fail"`                        |
| `JobStatus`       | `"pending" \| "running" \| "completed" \| "failed"` |
| `BaseEntity`      | Common `id` field                                   |
| `WithTimestamps`  | `created_at`, `updated_at`                          |
| `WithProvenance`  | QA grade and summary                                |
| `WithCoordinates` | `ra`, `dec` fields                                  |

### Error Types (`errors.ts`)

```tsx
import type { ErrorResponse, MappedError } from "@/types";
```

| Type            | Description                           |
| --------------- | ------------------------------------- |
| `ErrorResponse` | Normalized API error shape            |
| `ErrorSeverity` | `"error" \| "warning" \| "info"`      |
| `MappedError`   | User-friendly error with action hints |

### Provenance Types (`provenance.ts`)

```tsx
import type { ProvenanceStripProps } from "@/types";
```

Props for provenance display components.

### Third-Party Type Declarations

Type definitions for libraries without TypeScript support:

| File                     | Library                |
| ------------------------ | ---------------------- |
| `aladin-lite.d.ts`       | Aladin Lite sky viewer |
| `d3-celestial.d.ts`      | D3-Celestial star maps |
| `d3-geo-projection.d.ts` | D3 geo projections     |
| `js9.d.ts`               | JS9 FITS viewer        |

## Conventions

1. **Use `type` over `interface`** for consistency
2. **Export from `index.ts`** for clean imports
3. **Match backend naming** for API types
4. **Use discriminated unions** for status fields
