# Pipeline Visuals

This page illustrates the streaming continuum imaging pipeline from ingest to products, plus decision points and fast-path options for speed.

**For a comprehensive, detailed workflow visualization with complete stage breakdowns, see [Pipeline Workflow Visualization](pipeline_workflow_visualization.md).**

## End-to-end Flow

```mermaid
flowchart TB
  Ingest["Ingest Watcher"] --> Group["Group Subbands<br/>by time window"]
  Group --> Convert["Convert UVH5 to MS<br/>strategy orchestrator"]
  Convert --> CalSel{"Calibrator<br/>Field?"}
  CalSel -->|yes| Cal["Calibrate<br/>K, BP, G"]
  CalSel -->|no| Apply["Apply Latest<br/>Caltables"]
  Cal --> Reg["Register<br/>Caltables"]
  Reg --> Apply
  Apply --> Image["WSClean Image<br/>tclean available"]
  Image --> Index["Record in Products DB<br/>ms_index, images, qa_artifacts"]
  Index --> API["API/QA Views"]
  
  style Ingest fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#000
  style Group fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#000
  style Convert fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#000
  style CalSel fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
  style Cal fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
  style Reg fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
  style Apply fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#000
  style Image fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
  style Index fill:#E0F2F1,stroke:#00796B,stroke-width:2px,color:#000
  style API fill:#E1F5FE,stroke:#0277BD,stroke-width:2px,color:#000
```

Notes:
- Conversion uses a strategy pattern and can stage to tmpfs for speed.
- Calibration supports quality tiers with explicit trade-offs for different use cases.
- Imaging supports quality tiers: "standard" (recommended for science), "development" (⚠️ NON-SCIENCE), "high_precision" (enhanced quality).

## Conversion: Writer Selection and Staging

```mermaid
flowchart LR
  Auto["--writer auto"] --> N{"n_subbands<br/><= 2?"}
  N -->|yes| Mono["pyuvdata<br/>monolithic write<br/>TESTING ONLY"]
  N -->|no| Par["parallel-subband<br/>parallel per-subband writes<br/>PRODUCTION"]
  Par --> Stage{"--stage-to-tmpfs?"}
  Stage -->|yes| Tmp["tmpfs /dev/shm<br/>staging"]
  Stage -->|no| Disk["SSD NVMe<br/>scratch"]
  Tmp --> Concat["CASA concat<br/>full-band MS"]
  Disk --> Concat
  Mono --> MS["Final<br/>full-band MS"]
  Concat --> MS
  
  style Auto fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#000
  style N fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
  style Mono fill:#FFCDD2,stroke:#D32F2F,stroke-width:2px,color:#000
  style Par fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
  style Stage fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
  style Tmp fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#000
  style Disk fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#000
  style Concat fill:#E8EAF6,stroke:#3F51B5,stroke-width:2px,color:#000
  style MS fill:#C8E6C9,stroke:#388E3C,stroke-width:3px,color:#000
```

- **Production**: Always uses `parallel-subband` writer for 16 subbands (default).
- **Testing**: `pyuvdata` writer is available for testing scenarios with <=2 subbands only.
- `auto` mode selects `parallel-subband` for production (16 subbands) or `pyuvdata` for testing (<=2 subbands).
- **Note**: `direct-subband` is an alias for `parallel-subband` (backward compatibility).
- tmpfs staging reduces filesystem latency for part writes and final concat.

## Calibration: Fast Path

```mermaid
flowchart LR
  MSIn["Input MS"] --> Fast{"--fast<br/>flag?"}
  Fast -->|yes| Subset["mstransform subset<br/>timebin/chanbin"]
  Fast -->|no| Full["Use Full<br/>MS"]
  Subset --> K["solve_delay<br/>(K)"]
  Full --> K
  K --> BP["solve_bandpass<br/>(BP) uvrange?"]
  BP --> G["solve_gains<br/>(G) phase-only if fast"]
  G --> Tabs["Caltables"]
  Tabs --> Reg["Register<br/>+ apply"]
  
  style MSIn fill:#E8EAF6,stroke:#3F51B5,stroke-width:2px,color:#000
  style Fast fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
  style Subset fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#000
  style Full fill:#E8EAF6,stroke:#3F51B5,stroke-width:2px,color:#000
  style K fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
  style BP fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
  style G fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
  style Tabs fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
  style Reg fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
```

- Typical fast knobs: `--timebin 30s`, `--chanbin 4`, `--uvrange >1klambda`, phase-only gains.

## Imaging: Quick-look Options

```mermaid
flowchart LR
  CMS["Calibrated MS"] --> Quick{"--quick<br/>flag?"}
  Quick -->|yes| Small["Quick Look<br/>imsize <= 512<br/>niter <= 300<br/>robust ~ 0"]
  Quick -->|no| Def["Use Requested<br/>Defaults"]
  Small --> WSClean["WSClean<br/>default backend"]
  Def --> WSClean
  WSClean --> Fits{"--skip-fits<br/>flag?"}
  Fits -->|yes| Done["Stop after<br/>CASA images"]
  Fits -->|no| FITS["Export<br/>FITS"]
  
  style CMS fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
  style Quick fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
  style Small fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
  style Def fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
  style WSClean fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
  style Fits fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
  style Done fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
  style FITS fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
```

- Quick-look is for speed and operator QA; omit `--quick` and `--skip-fits` for full-quality products.
- **Imaging backend**: WSClean is the default (2-5x faster than tclean). tclean is available via `--backend tclean`.
