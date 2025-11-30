# DSA-110 Continuum Imaging Frontend Architecture

> **Legend**: Solid lines = data flow | Dotted lines = external requests | Thick
> lines = primary path

---

## 1. Deployment Topology

Shows the physical layout of services and ports.

```mermaid
flowchart LR
    subgraph Client["Client Machine"]
        Browser["Browser"]
    end

    subgraph Server["lxd110h17"]
        Nginx["Nginx :80"]
        Vite["Vite Dev :3000"]
        API["FastAPI :8000"]
        Redis["Redis :6379"]
        Prom["Prometheus :9090"]
        Graf["Grafana :3030"]
    end

    Browser -->|":80 prod"| Nginx
    Browser -->|":3000 dev"| Vite
    Nginx -->|"proxy /api/"| API
    Nginx -->|"static /"| Static["/frontend/dist"]
    Vite -->|"proxy /api/"| API
    API --> Redis
    API -->|"/metrics"| Prom
    Prom --> Graf
```

---

## 2. Frontend Application Structure

Shows React component and data flow architecture.

```mermaid
flowchart TB
    subgraph App["main.tsx"]
        QCP["QueryClientProvider"]
        RP["RouterProvider"]
    end

    subgraph Router["router.tsx"]
        AL["AppLayout"]
    end

    subgraph Pages["Page Components"]
        HP["HomePage"]
        ILP["ImagesListPage"]
        IDP["ImageDetailPage"]
        SLP["SourcesListPage"]
        SDP["SourceDetailPage"]
        JLP["JobsListPage"]
        JDP["JobDetailPage"]
        MDP["MSDetailPage"]
    end

    subgraph Hooks["hooks/useQueries.ts"]
        uI["useImages"]
        uImg["useImage"]
        uS["useSources"]
        uSrc["useSource"]
        uJ["useJobs"]
        uMS["useMS"]
    end

    subgraph ApiClient["api/client.ts"]
        Axios["axios instance"]
    end

    App --> Router --> Pages
    Pages --> Hooks
    Hooks --> ApiClient
    ApiClient -->|"HTTP"| Backend["FastAPI :8000"]
```

---

## 3. Page to API Mapping

Which page calls which endpoints.

```mermaid
flowchart LR
    subgraph FrontendPages["Frontend Routes"]
        P1["/ Home"]
        P2["/images"]
        P3["/images/:id"]
        P4["/sources"]
        P5["/sources/:id"]
        P6["/jobs"]
        P7["/jobs/:runId"]
        P8["/ms/*"]
    end

    subgraph APIEndpoints["API Endpoints"]
        E2["GET /api/images"]
        E3["GET /api/images/:id"]
        E4["GET /api/images/:id/fits"]
        E5["GET /api/sources"]
        E6["GET /api/sources/:id"]
        E7["GET /api/sources/:id/lightcurve"]
        E8["GET /api/jobs"]
        E9["GET /api/jobs/:runId/provenance"]
        E10["GET /api/ms/:path/metadata"]
    end

    P1 --> E2 & E5 & E8
    P2 --> E2
    P3 --> E3 & E4
    P4 --> E5
    P5 --> E6 & E7
    P6 --> E8
    P7 --> E9
    P8 --> E10
```

---

## 4. Backend Data Layer

Shows actual SQLite databases and file storage.

```mermaid
flowchart TB
    subgraph API["FastAPI :8000"]
        Routes["API Routes"]
        Repos["Repositories"]
    end

    subgraph Cache["Cache Layer"]
        Redis["Redis :6379"]
    end

    subgraph SQLite["SQLite Databases in /state/db/"]
        DB1["products.sqlite3<br/>images and QA"]
        DB2["master_sources.sqlite3<br/>113 MB sources"]
        DB3["calibrators.sqlite3<br/>cal tables"]
        DB4["hdf5.sqlite3<br/>raw data index"]
        DB5["ingest.sqlite3<br/>pipeline state"]
    end

    subgraph Files["File Storage"]
        FITS["FITS Images<br/>/state/data/synth/images/*.fits"]
        MS["Measurement Sets<br/>/state/ms/science/"]
        CAL["Cal Tables<br/>/products/caltables/"]
    end

    Routes --> Repos
    Routes <--> Redis
    Repos --> SQLite
    Repos --> Files
```

---

## 5. External Service Integration

Frontend-initiated requests to astronomical services.

```mermaid
flowchart LR
    subgraph Frontend["Frontend Components"]
        FV["FitsViewer"]
        COP["CatalogOverlayPanel"]
        NOP["NearbyObjectsPanel"]
    end

    subgraph CDS["CDS Strasbourg"]
        VZ["VizieR TAP"]
        SB["SIMBAD TAP"]
    end

    subgraph SAO["SAO Harvard"]
        JS9["JS9 CDN"]
    end

    FV -.->|"Load library"| JS9
    COP -.->|"ADQL query"| VZ
    NOP -.->|"ADQL query"| SB

    JS9 -.->|"js9.min.js"| FV
    VZ -.->|"VOTable XML"| COP
    SB -.->|"JSON"| NOP
```

**External URLs:**

- JS9: `https://js9.si.edu/js9/js9-allinone.js`
- VizieR: `https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync`
- SIMBAD: `https://simbad.u-strasbg.fr/simbad/sim-tap/sync`

---

## 6. Image Detail Data Flow

Complete flow when viewing an image with FITS viewer.

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as FastAPI :8000
    participant Redis as Redis :6379
    participant DB as products.sqlite3
    participant FS as FITS Files
    participant CDN as JS9 CDN

    User->>FE: Navigate to /images/IMG001

    FE->>API: GET /api/images/IMG001
    API->>Redis: Check cache
    alt Cache Miss
        API->>DB: SELECT FROM images WHERE id=IMG001
        DB-->>API: Row data
        API->>Redis: SET cache
    end
    API-->>FE: JSON metadata

    opt First FITS load
        FE->>CDN: GET js9-allinone.js
        CDN-->>FE: JavaScript library
    end

    User->>FE: Click Show FITS Viewer
    FE->>API: GET /api/images/IMG001/fits
    API->>FS: Read /products/IMG001.fits
    FS-->>API: Binary FITS data
    API-->>FE: application/fits

    FE->>FE: JS9.Load data
    FE-->>User: Interactive FITS display
```

---

## 7. State Management

How client-side state is managed.

```mermaid
flowchart TB
    subgraph ReactQuery["React Query - Server State"]
        IQ["images query"]
        SQ["sources query"]
        JQ["jobs query"]
    end

    subgraph Zustand["Zustand - Client State"]
        UI["useUIStore<br/>sidebarOpen, theme"]
        Pref["usePreferencesStore<br/>colorMap, scale"]
        Sel["useSelectionStore<br/>selectedImages, selectedSources, selectedJobs"]
    end

    subgraph Pages["List Pages"]
        ILP["ImagesListPage"]
        SLP["SourcesListPage"]
        JLP["JobsListPage"]
    end

    ILP --> IQ
    SLP --> SQ
    JLP --> JQ

    ILP --> Sel
    SLP --> Sel
    JLP --> Sel

    Pages --> UI
    Pages --> Pref
```

---

## 8. Error Handling Flow

How errors propagate from API to user.

```mermaid
flowchart LR
    subgraph API["Backend"]
        Err["ErrorEnvelope<br/>code, http_status,<br/>user_message, action"]
    end

    subgraph Frontend["Frontend"]
        Int["axios interceptor<br/>api/client.ts"]
        Hook["useErrorHandler<br/>useErrorMapping"]
        Map["errorMappings.ts"]
        ED["ErrorDisplay<br/>component"]
    end

    API -->|"JSON error"| Int
    Int -->|"normalized"| Hook
    Hook --> Map
    Map -->|"user-friendly"| ED
    ED -->|"display"| User["User sees<br/>message and action"]
```

---

## 9. Component to Page Mapping

Verified imports from each page file.

| Page                 | Components Used                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------- |
| **HomePage**         | StatCardGrid, SkyCoverageMap, StatsDashboard                                                |
| **ImagesListPage**   | FilterPanel, FitsViewerGrid, BulkDownloadPanel, useSelectionStore                           |
| **ImageDetailPage**  | FitsViewer, RatingCard, AladinLiteViewer, GifPlayer, ProvenanceStrip, ErrorDisplay          |
| **SourcesListPage**  | AdvancedQueryPanel, EtaVPlot, AdvancedFilterPanel, Modal, useSelectionStore                 |
| **SourceDetailPage** | CatalogOverlayPanel, NearbyObjectsPanel, AladinLiteViewer, LightCurveChart, ProvenanceStrip |
| **JobsListPage**     | useSelectionStore                                                                           |
| **JobDetailPage**    | ProvenanceStrip                                                                             |

---

## Port Reference

| Port | Service    | Purpose                  | Config                                      | Verified |
| ---- | ---------- | ------------------------ | ------------------------------------------- | -------- |
| 80   | Nginx      | Production reverse proxy | `/etc/nginx/sites-available/dsa110-contimg` | -        |
| 3000 | Vite       | Dev server               | `vite.config.ts`                            | Yes      |
| 8000 | FastAPI    | Backend API              | `CONTIMG_API_PORT` env var                  | Yes      |
| 6379 | Redis      | Response caching         | `REDIS_PORT` env var                        | Yes      |
| 9090 | Prometheus | Metrics scraping         | `/etc/prometheus/prometheus.yml`            | Yes      |
| 3030 | Grafana    | Dashboards               | `/etc/grafana/grafana.ini`                  | Yes      |

---

## Quick Reference

### URLs in Development

| Resource | URL                              |
| -------- | -------------------------------- |
| Frontend | http://localhost:3000            |
| API Docs | http://localhost:8000/api/docs   |
| Health   | http://localhost:8000/api/health |
| Grafana  | http://localhost:3030            |

### Environment

```bash
# Frontend .env
VITE_API_URL=http://localhost:8000

# Backend systemd or shell
CONTIMG_API_PORT=8000
REDIS_PORT=6379
```

### Key Files

| Purpose            | Path                             |
| ------------------ | -------------------------------- |
| API client         | `src/api/client.ts`              |
| Resilience modules | `src/api/resilience/`            |
| Query hooks        | `src/hooks/useQueries.ts`        |
| Custom hooks       | `src/hooks/use*.ts`              |
| Router             | `src/router.tsx`                 |
| Route constants    | `src/constants/routes.ts`        |
| State stores       | `src/stores/appStore.ts`         |
| Error mappings     | `src/constants/errorMappings.ts` |
| API types          | `src/types/api.ts`               |
| Error boundaries   | `src/components/errors/`         |

---

## 10. Code Architecture Patterns

### Type System

All API response types are centralized in `src/types/api.ts`:

```typescript
// Base entity with common fields
interface BaseEntity {
  id: string;
  created_at?: string;
  updated_at?: string;
}

// Mixin types for composition
interface WithProvenance {
  job_id?: string;
  run_id?: string;
  ms_path?: string;
  cal_table?: string;
}

interface WithCoordinates {
  ra_deg: number;
  dec_deg: number;
}

// Entity types compose mixins
interface ImageSummary extends BaseEntity, WithProvenance { ... }
interface SourceDetail extends BaseEntity, WithCoordinates, WithProvenance { ... }
```

### Route Constants

Routes are centralized in `src/constants/routes.ts`:

```typescript
export const ROUTES = {
  HOME: "/",
  IMAGES: {
    LIST: "/images",
    DETAIL: (id: string) => `/images/${encodeURIComponent(id)}`,
  },
  SOURCES: {
    LIST: "/sources",
    DETAIL: (id: string) => `/sources/${encodeURIComponent(id)}`,
  },
  // ...
} as const;
```

### API Client Resilience

The API client uses a modular resilience layer in `src/api/resilience/`:

```
src/api/resilience/
├── types.ts          # RetryConfig, CircuitBreakerConfig
├── circuit-breaker.ts # Circuit breaker state machine
├── retry.ts          # Retry logic with exponential backoff
└── index.ts          # Barrel exports
```

### Custom Hooks

Complex page logic is extracted into focused hooks:

| Hook                 | Purpose                             | Status        |
| -------------------- | ----------------------------------- | ------------- |
| `useImageDetail`     | Image detail page data & operations | ✅ Integrated |
| `useUrlFilterState`  | URL-based filter state for sharing  | ✅ Integrated |
| `useSourceFiltering` | Source list filtering logic         | ✅ Integrated |

All hooks are fully integrated:

- `useImageDetail` in `ImageDetailPage` - handles delete, rating, recent items
- `useUrlFilterState` in `SourcesListPage` - shareable/bookmarkable filter URLs
- `useSourceFiltering` in `SourcesListPage` - centralized filtering logic

### Error Boundaries

Error boundaries wrap visualization widgets to prevent crashes:

```tsx
<WidgetErrorBoundary widgetName="FITS Viewer" minHeight={500}>
  <FitsViewer ... />
</WidgetErrorBoundary>
```

### Loading States

Consistent skeleton loading using `PageSkeleton`:

```tsx
if (isLoading) {
  return <PageSkeleton variant="detail" showHeader showSidebar />;
}
```

Variants: `list`, `detail`, `cards`, `table`
