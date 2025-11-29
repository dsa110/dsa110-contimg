# DSA-110 Continuum Imaging Frontend Architecture

## System Overview

```mermaid
flowchart TB
    subgraph Browser["🌐 Browser (User)"]
        subgraph Frontend["React Frontend :3000"]
            Router[React Router]
            
            subgraph Pages["📄 Pages"]
                HP["/  HomePage"]
                ILP["/images  ImagesListPage"]
                IDP["/images/:id  ImageDetailPage"]
                SLP["/sources  SourcesListPage"]
                SDP["/sources/:id  SourceDetailPage"]
                JLP["/jobs  JobsListPage"]
                JDP["/jobs/:id  JobDetailPage"]
                MDP["/ms/*  MSDetailPage"]
            end
            
            subgraph State["🗄️ State Management"]
                RQ["@tanstack/react-query<br/>Query Cache"]
                ZS["Zustand Stores<br/>• useUIStore<br/>• usePreferencesStore<br/>• useSelectionStore"]
            end
            
            subgraph Components["🧩 Key Components"]
                FV["FitsViewer<br/>(JS9 CDN)"]
                CO["CatalogOverlayPanel<br/>(VizieR)"]
                NO["NearbyObjectsPanel<br/>(SIMBAD)"]
                SC["SkyCoverageMap<br/>(D3.js)"]
                EV["EtaVPlot<br/>(ECharts)"]
                SD["StatsDashboard<br/>(ECharts)"]
            end
        end
    end
    
    subgraph External["☁️ External Services"]
        JS9["JS9 CDN<br/>js9.si.edu"]
        VZ["VizieR TAP<br/>tapvizier.cds.unistra.fr"]
        SB["SIMBAD TAP<br/>simbad.u-strasbg.fr"]
    end
    
    subgraph Server["🖥️ Server (lxd110h17)"]
        subgraph API["FastAPI Backend :8000"]
            Routes["API Routes<br/>/api/*"]
            Repos["Repositories<br/>• ImageRepository<br/>• SourceRepository<br/>• MSRepository<br/>• JobRepository"]
            Cache["Redis Cache<br/>:6379"]
        end
        
        subgraph Data["💾 Data Storage"]
            SQLite["SQLite DBs<br/>• images.db<br/>• sources.db<br/>• jobs.db"]
            FITS["FITS Files<br/>/data/dsa110-contimg/products/"]
            MS["Measurement Sets<br/>/data/dsa110-contimg/state/"]
        end
        
        subgraph Monitor["📊 Monitoring"]
            Prom["Prometheus<br/>:9090"]
            Graf["Grafana<br/>:3030"]
        end
        
        NGINX["Nginx<br/>:80<br/>Reverse Proxy"]
    end
    
    %% Frontend connections
    Router --> Pages
    Pages --> RQ
    Pages --> ZS
    Pages --> Components
    
    %% External service connections
    FV -.->|"Load FITS lib"| JS9
    CO -.->|"TAP Query"| VZ
    NO -.->|"TAP Query"| SB
    
    %% API connections  
    RQ -->|"HTTP :8000"| Routes
    Routes --> Repos
    Repos --> SQLite
    Repos --> FITS
    Repos --> MS
    Routes --> Cache
    
    %% Monitoring
    Routes -->|"/metrics"| Prom
    Prom --> Graf
    
    %% Production proxy
    NGINX -->|"proxy /api/"| Routes
    NGINX -->|"static files"| Frontend
```

## Page → API Endpoint Mapping

```mermaid
flowchart LR
    subgraph Pages["Frontend Pages"]
        HP["/ HomePage"]
        ILP["/images"]
        IDP["/images/:id"]
        SLP["/sources"]  
        SDP["/sources/:id"]
        JLP["/jobs"]
        JDP["/jobs/:runId"]
        MDP["/ms/*"]
    end
    
    subgraph Hooks["React Query Hooks"]
        uI["useImages()"]
        uImg["useImage(id)"]
        uS["useSources()"]
        uSrc["useSource(id)"]
        uJ["useJobs()"]
        uJob["useJob(runId)"]
        uMS["useMS(path)"]
        uStat["useStats()"]
    end
    
    subgraph API["Backend API :8000"]
        EI["GET /api/images"]
        EID["GET /api/images/:id"]
        EIDP["GET /api/images/:id/provenance"]
        EIDF["GET /api/images/:id/fits"]
        ES["GET /api/sources"]
        ESD["GET /api/sources/:id"]
        ESDL["GET /api/sources/:id/lightcurve"]
        ESDV["GET /api/sources/:id/variability"]
        EJ["GET /api/jobs"]
        EJD["GET /api/jobs/:runId/provenance"]
        EJL["GET /api/jobs/:runId/logs"]
        EM["GET /api/ms/:path/metadata"]
        EST["GET /api/stats"]
        EQ["GET /api/qa/*"]
        EC["GET /api/cal/*"]
    end
    
    HP --> uI & uS & uJ & uStat
    ILP --> uI
    IDP --> uImg
    SLP --> uS
    SDP --> uSrc
    JLP --> uJ
    JDP --> uJob
    MDP --> uMS
    
    uI --> EI
    uImg --> EID & EIDP & EIDF
    uS --> ES
    uSrc --> ESD & ESDL & ESDV
    uJ --> EJ
    uJob --> EJD & EJL
    uMS --> EM
    uStat --> EST
```

## Port Reference

| Port | Service | Protocol | Purpose |
|------|---------|----------|---------|
| **80** | Nginx | HTTP | Production reverse proxy |
| **3000** | Vite Dev | HTTP | Frontend dev server |
| **8000** | FastAPI | HTTP | Backend REST API |
| **6379** | Redis | TCP | API response caching |
| **9090** | Prometheus | HTTP | Metrics collection |
| **3030** | Grafana | HTTP | Metrics dashboards |

## Data Flow: Image Detail View

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend :3000
    participant A as FastAPI :8000
    participant R as Redis :6379
    participant DB as SQLite
    participant FS as FITS Files
    participant J as JS9 CDN
    
    U->>F: Navigate to /images/IMG001
    F->>A: GET /api/images/IMG001
    A->>R: Check cache
    alt Cache hit
        R-->>A: Return cached
    else Cache miss
        A->>DB: Query image metadata
        DB-->>A: Return record
        A->>R: Store in cache
    end
    A-->>F: ImageDetail JSON
    
    F->>J: Load JS9 library (first time)
    J-->>F: JS9.min.js
    
    F->>A: GET /api/images/IMG001/fits
    A->>FS: Read FITS file
    FS-->>A: Binary data
    A-->>F: FITS file
    
    F->>F: JS9.Load(fits_data)
    F-->>U: Display interactive FITS viewer
```

## External Service Integration

```mermaid
flowchart LR
    subgraph Frontend
        COP["CatalogOverlayPanel"]
        NOP["NearbyObjectsPanel"]
        FV["FitsViewer"]
    end
    
    subgraph CDS["CDS Services (Strasbourg)"]
        VZ["VizieR TAP<br/>tapvizier.cds.unistra.fr"]
        SB["SIMBAD TAP<br/>simbad.u-strasbg.fr"]
    end
    
    subgraph SAO["SAO (Harvard)"]
        JS9["JS9 CDN<br/>js9.si.edu"]
    end
    
    COP -->|"ADQL Cone Search<br/>NVSS, FIRST, VLASS"| VZ
    NOP -->|"ADQL Cone Search<br/>Nearby objects"| SB
    FV -->|"Load JS9.min.js<br/>+ CSS"| JS9
    
    VZ -->|"VOTable XML"| COP
    SB -->|"JSON"| NOP
    JS9 -->|"JS library"| FV
```

## Component Hierarchy

```mermaid
flowchart TB
    subgraph App["App (main.tsx)"]
        QP["QueryClientProvider"]
        RP["RouterProvider"]
    end
    
    subgraph Layout["AppLayout"]
        Nav["Navigation Sidebar"]
        Main["Main Content Area"]
    end
    
    subgraph HomePage
        SCG["StatCardGrid"]
        SCM["SkyCoverageMap"]
        SDB["StatsDashboard"]
    end
    
    subgraph ImagesListPage
        FP1["FilterPanel"]
        IT["Image Table"]
        FVG["FitsViewerGrid"]
        BDP["BulkDownloadPanel"]
    end
    
    subgraph ImageDetailPage
        IC["Image Card"]
        FV2["FitsViewer"]
        RC["RatingCard"]
        PS["ProvenanceStrip"]
    end
    
    subgraph SourcesListPage
        AQP["AdvancedQueryPanel"]
        AFP["AdvancedFilterPanel"]
        ST["Sources Table"]
        EVP["EtaVPlot"]
    end
    
    subgraph SourceDetailPage
        SCard["Source Card"]
        COP2["CatalogOverlayPanel"]
        NOP2["NearbyObjectsPanel"]
        PS2["ProvenanceStrip"]
    end
    
    subgraph JobsListPage
        JT["Jobs Table"]
        Sel["Selection Actions"]
    end
    
    subgraph JobDetailPage
        JCard["Job Card"]
        Logs["Log Viewer"]
        PS3["ProvenanceStrip"]
    end
    
    App --> Layout
    Layout --> Main
    Main --> HomePage & ImagesListPage & ImageDetailPage & SourcesListPage & SourceDetailPage & JobsListPage & JobDetailPage
```

## State Management

```mermaid
flowchart TB
    subgraph Zustand["Zustand Stores (appStore.ts)"]
        UI["useUIStore<br/>• sidebarOpen<br/>• theme"]
        Pref["usePreferencesStore<br/>• defaultColorMap<br/>• defaultScale"]
        Sel["useSelectionStore<br/>• selectedImages: Set<br/>• selectedSources: Set<br/>• selectedJobs: Set"]
    end
    
    subgraph RQ["React Query Cache"]
        IC2["images cache"]
        SC2["sources cache"]
        JC["jobs cache"]
        MC["ms cache"]
    end
    
    subgraph Pages
        ILP2["ImagesListPage"]
        SLP2["SourcesListPage"]
        JLP2["JobsListPage"]
    end
    
    Pages --> Zustand
    Pages --> RQ
    
    ILP2 -->|"toggle selection"| Sel
    SLP2 -->|"toggle selection"| Sel
    JLP2 -->|"toggle selection"| Sel
    
    ILP2 -->|"fetch data"| IC2
    SLP2 -->|"fetch data"| SC2
    JLP2 -->|"fetch data"| JC
```

## Development vs Production

```mermaid
flowchart TB
    subgraph Dev["Development Mode"]
        VD["Vite Dev Server<br/>:3000"]
        API1["FastAPI<br/>:8000"]
        VD -->|"proxy /api"| API1
    end
    
    subgraph Prod["Production Mode"]
        NG["Nginx<br/>:80"]
        Static["Static Files<br/>/frontend/dist"]
        API2["FastAPI<br/>:8000"]
        NG -->|"/ serves"| Static
        NG -->|"/api/ proxy"| API2
    end
```

## Quick Reference

### Frontend URLs (Development)
- **Dashboard**: http://localhost:3000/
- **Images List**: http://localhost:3000/images
- **Image Detail**: http://localhost:3000/images/:id
- **Sources List**: http://localhost:3000/sources
- **Source Detail**: http://localhost:3000/sources/:id
- **Jobs List**: http://localhost:3000/jobs
- **Job Detail**: http://localhost:3000/jobs/:runId

### Backend URLs
- **API Base**: http://localhost:8000/api/
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/api/health
- **Metrics**: http://localhost:8000/metrics

### External Services
- **JS9 CDN**: https://js9.si.edu/
- **VizieR TAP**: https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync
- **SIMBAD TAP**: https://simbad.u-strasbg.fr/simbad/sim-tap/sync

### Environment Variables
```bash
# Frontend (.env)
VITE_API_URL=http://localhost:8000

# Backend
CONTIMG_API_PORT=8000
REDIS_PORT=6379
```
