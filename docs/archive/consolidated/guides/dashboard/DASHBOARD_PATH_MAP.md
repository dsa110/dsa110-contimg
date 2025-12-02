# Dashboard Path Map

Quick reference for navigating to and starting the dashboard from any location
in the project.

## Current Location

- **You are here**: `/data/dsa110-contimg/docs` (or any subdirectory)

## Path to Dashboard Frontend

```bash
# From docs/ directory
cd ../frontend

# From project root
cd frontend

# Absolute path
cd /data/dsa110-contimg/frontend
```

## Starting the Dashboard

### Prerequisites

1. Backend API must be running on `localhost:8000`
2. Use `casa6` conda environment

### Step 1: Start Backend (Terminal 1)

```bash
cd /data/dsa110-contimg
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6
uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Start Frontend (Terminal 2)

```bash
cd /data/dsa110-contimg/frontend
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6
npm run dev
```

### Step 3: Access Dashboard

Open in browser: **http://localhost:3000**

## Quick Navigation Commands

### From docs/ directory:

```bash
cd ../frontend && conda activate casa6 && npm run dev
```

### From project root:

```bash
cd frontend && conda activate casa6 && npm run dev -- --host 0.0.0.0 --port 5173
```

### One-liner from anywhere:

```bash
cd /data/dsa110-contimg/frontend && source /opt/miniforge/etc/profile.d/conda.sh && conda activate casa6 && npm run dev -- --host 0.0.0.0 --port 5173
```

## Directory Structure

```
/data/dsa110-contimg/
├── docs/                    # You are here (or in a subdirectory)
├── frontend/                # Dashboard frontend code
│   ├── src/                 # Source code
│   ├── package.json        # npm scripts
│   └── vite.config.ts      # Vite configuration
├── dsa110_contimg/         # Backend API code
└── ...
```

## Alternative: Safe Start Script

If available, use the safe start script:

```bash
cd /data/dsa110-contimg/frontend
conda activate casa6
npm run dev:safe
```

## Troubleshooting

### Port already in use?

Change the port:

```bash
npm run dev -- --host 0.0.0.0 --port 5174
```

### Backend not responding?

Verify backend is running:

```bash
curl http://localhost:8000/api/health
```

### Dependencies not installed?

```bash
cd /data/dsa110-contimg/frontend
conda activate casa6
npm install
```
