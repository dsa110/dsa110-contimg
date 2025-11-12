# DSA-110 Frontend Setup - Complete ✓

**Date**: 2025-10-24  
**Status**: Database schema migrated, React project initialized and building successfully

---

## What Was Accomplished

### 1. Database Schema Design & Migration ✓

**Created comprehensive schema** for frontend requirements in `products.sqlite3`:

```sql
✓ variability_stats     - Pre-computed source variability statistics
✓ ese_candidates        - Auto-flagged ESE candidates (>5σ threshold)
✓ mosaics               - Metadata for hour-long mosaic images
✓ alert_history         - Slack alert log
✓ photometry            - Extended with source_id, MJD, SNR fields
✓ images                - Extended with format, center coords, field_name
✓ ms_index              - Extended with field_name, pointing coords
```

**Migration script** (`src/dsa110_contimg/database/migrations.py`):
- Safe to run multiple times (IF NOT EXISTS)
- Adds missing columns to existing tables
- Creates indices for efficient queries
- Successfully executed on `/data/dsa110-contimg/state/products.sqlite3`

**Documentation**: `/docs/reference/database_schema.md` (complete schema reference)

### 2. React + TypeScript Project Structure ✓

**Initialized with Vite** using Node v22.6.0 from `casa6` conda environment:

```bash
Location: /data/dsa110-contimg/frontend/
Build tool: Vite 7
Framework: React 18 + TypeScript
Status: ✓ Builds successfully (dist/ created)
```

**Dependencies installed**:
- Material-UI v7.3.4 (dark mode optimized)
- TanStack React Query (API state management)
- Axios (HTTP client)
- React Router v6 (navigation)
- Plotly.js, D3.js (visualization - ready for use)
- AG Grid (tables - ready for use)

**Project structure created**:
```
frontend/src/
├── api/
│   ├── client.ts       ✓ Axios instance configured
│   ├── types.ts        ✓ TypeScript interfaces matching backend
│   └── queries.ts      ✓ React Query hooks with 10s polling
├── components/         ✓ Directory structure ready
│   ├── Dashboard/
│   ├── Sky/
│   ├── Sources/
│   ├── Observing/
│   ├── Health/
│   └── shared/
├── pages/
│   └── DashboardPage.tsx  ✓ Functional dashboard implemented
├── theme/
│   └── darkTheme.ts    ✓ Dark mode theme (optimized for astronomy)
├── utils/              ✓ Ready for formatters, calculations
├── App.tsx             ✓ Routing & providers configured
└── main.tsx            ✓ Entry point
```

### 3. Functional Dashboard Page ✓

**Implemented features**:
- Pipeline Status panel (queue stats, calibration sets)
- System Health panel (CPU, memory, disk, load average)
- Recent Observations table
- Real-time polling (10s refresh via React Query)
- Error handling & loading states
- Fully responsive layout (Stack-based, MUI)

**API Integration**:
- `usePipelineStatus()` - Polls `/api/status`
- `useSystemMetrics()` - Polls `/api/metrics/system`
- Graceful error handling when API unavailable

**View the dashboard**:
```bash
# Start dev server
cd /data/dsa110-contimg/frontend
conda run -n casa6 npm run dev

# Access at http://localhost:5173
```

---

## Design Decisions Finalized

| Decision | Choice |
|----------|--------|
| **Source naming** | NVSS IDs (e.g., "NVSS J123456.7+420312") |
| **ESE threshold** | 5σ auto-flagging (χ²_ν > 5 or flux deviation > 5σ) |
| **Alerts** | In-app visual panel + Slack webhooks (Phase 2) |
| **Data retention** | Persistent (no expiration) |
| **Mosaic UI** | Display existing mosaics (no user generation UI for now) |
| **Current priority** | Query/display hour-long pre-generated mosaics |

---

## Tech Stack Rationale

### Why casa6 conda environment?

**Problem**: Ubuntu 18.x (cannot upgrade OS)  
**Solution**: casa6 has Node v22.6.0 - modern enough for React + Vite  
**Result**: Builds successfully despite minor version warning

### Why Stack instead of Grid?

**Problem**: MUI v7 changed Grid API, Grid2 not fully exported  
**Solution**: Use Stack for flexible layouts (cleaner, modern API)  
**Result**: Responsive, type-safe, simpler code

### Why SQLite over PostgreSQL?

**Current**: Photometry data manageable in SQLite  
**Future**: Migrate to Postgres if >100M measurements or multi-user needs

---

## Next Steps (Priority Order)

### Phase 1: Core Dashboards (This Week)
1. **ESE Candidates Panel** - Query `ese_candidates` table, display >5σ sources
2. **Mosaic Gallery** - Query `mosaics` table, display thumbnails
3. **System Health Charts** - Add Plotly time-series for CPU/mem/disk

### Phase 2: Source Monitoring (Weeks 2-3)
1. **Source Table** - AG Grid with NVSS IDs, variability stats
2. **Source Detail View** - Flux timeseries plot (Plotly)
3. **Backend endpoint**: `GET /api/ese_candidates`
4. **Backend endpoint**: `GET /api/mosaics?limit=20`
5. **Backend endpoint**: `GET /api/sources?sort=variability&limit=100`

### Phase 3: Advanced Features (Weeks 4-6)
1. **Slack integration** - Webhook alerts for >5σ events
2. **Sky page** - Image gallery, FITS viewer
3. **Observing page** - Telescope status, pointing history
4. **WebSocket** - Real-time updates (replace polling)

---

## How to Run

### Development

```bash
# Terminal 1: Start backend (if not running)
cd /data/dsa110-contimg
conda run -n casa6 uvicorn dsa110_contimg.api:app --reload --port 8000

# Terminal 2: Start frontend
cd /data/dsa110-contimg/frontend
conda run -n casa6 npm run dev

# Access UI at http://localhost:5173
# Access API at http://localhost:8000/api/status
```

### Production Build

```bash
cd /data/dsa110-contimg/frontend
conda run -n casa6 npm run build

# Outputs to dist/ directory
# Serve with Nginx or FastAPI StaticFiles
```

### Serve with FastAPI

Add to `src/dsa110_contimg/api/routes.py`:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/ui", StaticFiles(directory="frontend/dist", html=True), name="ui")
```

Access at: `http://your-server/ui`

---

## Troubleshooting

### Frontend won't build
```bash
# Check Node version
conda run -n casa6 node --version  # Should be v22.6.0

# Clean install
cd /data/dsa110-contimg/frontend
rm -rf node_modules package-lock.json
conda run -n casa6 npm install
conda run -n casa6 npm run build
```

### API connection errors
```bash
# Verify backend is running
curl http://localhost:8000/api/status

# Check CORS settings in FastAPI
# Add to create_app():
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Database migration issues
```bash
# Re-run migration
cd /data/dsa110-contimg
conda run -n casa6 python src/dsa110_contimg/database/migrations.py

# Verify tables exist
sqlite3 state/products.sqlite3 ".tables"
# Should see: variability_stats, ese_candidates, mosaics, alert_history
```

---

## Files Created/Modified

### Documentation
- ✓ `/docs/reference/database_schema.md` - Complete schema reference
- ✓ `/docs/concepts/frontend_design.md` - Updated with finalized decisions
- ✓ `/docs/concepts/frontend_next_steps.md` - Implementation guide
- ✓ `/docs/concepts/frontend_setup_complete.md` - This document

### Database
- ✓ `/src/dsa110_contimg/database/migrations.py` - Migration script
- ✓ `/state/products.sqlite3` - Migrated with new tables

### Frontend
- ✓ `/frontend/` - Complete React project
  - ✓ `src/api/` - API client & types
  - ✓ `src/theme/` - Dark mode theme
  - ✓ `src/pages/DashboardPage.tsx` - Functional dashboard
  - ✓ `src/App.tsx` - Main app with routing
  - ✓ `package.json` - Dependencies installed
  - ✓ `.env.development` - API URL configuration
  - ✓ `README.md` - Frontend documentation

---

## Success Metrics

✓ **Database schema**: 4 new tables, migrations successful  
✓ **React build**: Compiles without errors, dist/ created  
✓ **Dashboard**: Renders successfully, polls API every 10s  
✓ **TypeScript**: All type errors resolved  
✓ **Dark mode**: Optimized color palette for astronomy  
✓ **Documentation**: Complete specs for development kickoff  

---

## Ubuntu 18.x Compatibility Notes

**Challenge**: Ubuntu 18.x cannot upgrade OS, may have old system packages  
**Solution**: Use `casa6` conda environment which provides:
- Node.js v22.6.0 (modern enough for Vite/React)
- Python 3.11+
- All required dependencies isolated

**Alternative if issues arise**:
```bash
# Use Docker for Node.js
docker run -it -v /data/dsa110-contimg:/workspace -w /workspace/frontend \
  node:22 npm install

docker run -it -v /data/dsa110-contimg:/workspace -w /workspace/frontend \
  node:22 npm run dev
```

---

## What's Left to Build

### Backend API Endpoints Needed
```python
# In api/routes.py, add:

@router.get("/api/ese_candidates")
def get_ese_candidates(status: str = 'active', limit: int = 50):
    """Get ESE candidate sources (>5σ variability)."""
    # Query variability_stats JOIN ese_candidates
    pass

@router.get("/api/mosaics")
def get_mosaics(limit: int = 20, start_mjd: float = None, end_mjd: float = None):
    """Get mosaic metadata with optional time filtering."""
    # Query mosaics table
    pass

@router.get("/api/sources")
def get_sources(sort: str = 'variability', limit: int = 100):
    """Get source list with variability stats."""
    # Query variability_stats table
    pass

@router.get("/api/sources/{source_id}/timeseries")
def get_source_timeseries(source_id: str):
    """Get flux measurements for a source."""
    # Query photometry table WHERE source_id = X
    pass
```

### Frontend Components Needed
1. **ESECandidatesPanel.tsx** - Display >5σ sources with links to detail
2. **MosaicGallery.tsx** - Grid of mosaic thumbnails
3. **SourceTable.tsx** - AG Grid with NVSS IDs, sortable by variability
4. **SourceDetail.tsx** - Flux vs. time plot with Plotly

---

## Summary

**✓ Database schema designed and migrated**  
**✓ React project initialized with all dependencies**  
**✓ Functional dashboard with real-time polling**  
**✓ Dark mode optimized for astronomy**  
**✓ TypeScript type-safe throughout**  
**✓ Builds successfully despite Ubuntu 18.x constraints**  
**✓ Ready for Phase 1 feature development**

**Next**: Implement ESE candidates panel and mosaic gallery (backend endpoints + frontend components).

---

**Document Version**: 1.0  
**Status**: Setup Complete, Ready for Feature Development

