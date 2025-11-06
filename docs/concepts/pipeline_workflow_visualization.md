# DSA-110 Continuum Imaging Pipeline: Complete Workflow Visualization

**Purpose:** Comprehensive, instructive visualization of the pipeline workflow from raw UVH5 data ingestion to final calibrated continuum images.

**Last Updated:** 2025-01-15

---

## Table of Contents

1. [End-to-End Pipeline Overview](#end-to-end-pipeline-overview)
2. [Detailed Stage Breakdown](#detailed-stage-breakdown)
3. [State Machine & Queue Management](#state-machine--queue-management)
4. [Data Products & Artifacts](#data-products--artifacts)
5. [Database Interactions](#database-interactions)
6. [Performance Optimization Paths](#performance-optimization-paths)

---

## End-to-End Pipeline Overview

### Complete Data Flow

```mermaid
flowchart TB
    subgraph INGEST["Stage 1: Ingest & Grouping"]
        Files[UVH5 Subband Files<br/>*_sb??.hdf5<br/>16 subbands per group]
        Watch[Directory Watcher<br/>streaming_converter.py]
        Queue[Queue DB<br/>ingest.sqlite3]
        Files --> Watch
        Watch --> Queue
    end
    
    subgraph CONVERT["Stage 2: Conversion (UVH5 → MS)"]
        Group[Group Assembly<br/>5-minute time windows<br/>16 subbands required]
        Orch[Orchestrator<br/>hdf5_orchestrator.py]
        Writer{Writer Selection<br/>--writer auto}
        Par[parallel-subband<br/>PRODUCTION]
        Mono[pyuvdata<br/>TESTING ONLY]
        Stage[Staging<br/>tmpfs /dev/shm<br/>or SSD scratch]
        Concat[CASA concat<br/>to full-band MS]
        MS[Measurement Set<br/>with all columns]
        Queue --> Group
        Group --> Orch
        Orch --> Writer
        Writer -->|>2 subbands| Par
        Writer -->|≤2 subbands| Mono
        Par --> Stage
        Stage --> Concat
        Mono --> MS
        Concat --> MS
    end
    
    subgraph PREP["Stage 3: MS Preparation"]
        Validate[Validate MS<br/>readable, not empty]
        Config[Configure for Imaging<br/>MODEL_DATA, CORRECTED_DATA<br/>WEIGHT_SPECTRUM]
        Flag[RFI Flagging<br/>reset, zeros, statistical]
        MS --> Validate
        Validate --> Config
        Config --> Flag
    end
    
    subgraph CAL["Stage 4: Calibration"]
        CalSel{Calibrator<br/>Field?}
        SkyModel[Sky Model Seeding<br/>NVSS sources ≥10 mJy]
        KCal[K-Calibration<br/>Delay/Phase<br/>SKIPPED by default]
        BPCal[BP-Calibration<br/>Bandpass<br/>Frequency-dependent]
        GCal[G-Calibration<br/>Gains<br/>Time-variable]
        Reg[Register Caltables<br/>cal_registry.sqlite3]
        Flag --> CalSel
        CalSel -->|Yes| SkyModel
        CalSel -->|No| Apply
        SkyModel --> KCal
        KCal --> BPCal
        BPCal --> GCal
        GCal --> Reg
        Reg --> Apply
    end
    
    subgraph APPLY["Stage 5: Apply Calibration"]
        Apply[Apply Caltables<br/>to CORRECTED_DATA]
        Verify[Verify Corrected Data<br/>non-zero values]
        Apply --> Verify
    end
    
    subgraph IMAGE["Stage 6: Imaging"]
        Clean[tclean<br/>CASA deconvolution]
        Quick{Quick Mode?}
        Full[Full Quality<br/>imsize, niter from config]
        QuickImg[Quick Look<br/>imsize≤512, niter≤300]
        Fits{Export FITS?}
        FITS[FITS Export<br/>.pbcor.fits]
        Verify --> Clean
        Clean --> Quick
        Quick -->|Yes| QuickImg
        Quick -->|No| Full
        QuickImg --> Fits
        Full --> Fits
        Fits -->|Yes| FITS
        Fits -->|No| ImgFiles[CASA Image Files<br/>.image, .pb, etc.]
    end
    
    subgraph PRODUCT["Stage 7: Products & Indexing"]
        Products[Products DB<br/>products.sqlite3]
        MSIdx[MS Index<br/>ms_index table]
        ImgIdx[Image Index<br/>images table]
        QA[QA Artifacts<br/>plots, thumbnails]
        Products --> MSIdx
        Products --> ImgIdx
        Products --> QA
        FITS --> Products
        ImgFiles --> Products
    end
    
    subgraph API["Stage 8: Monitoring & Access"]
        FastAPI[FastAPI Server<br/>Monitoring endpoints]
        Status[Status Endpoints<br/>queue, calibration, products]
        QAView[QA Views<br/>thumbnails, plots]
        Products --> FastAPI
        FastAPI --> Status
        FastAPI --> QAView
    end
    
    style INGEST fill:#e1f5ff
    style CONVERT fill:#fff4e1
    style PREP fill:#f0f0f0
    style CAL fill:#e1ffe1
    style APPLY fill:#ffe1f5
    style IMAGE fill:#f5e1ff
    style PRODUCT fill:#ffe1e1
    style API fill:#e1e1ff
```

**Key Points:**
- **Stage 1**: Continuous monitoring of incoming UVH5 files, grouping by timestamp
- **Stage 2**: Conversion uses strategy pattern with automatic writer selection
- **Stage 3**: MS must be properly configured before calibration
- **Stage 4**: Calibration is optional (calibrator field required) or uses existing caltables
- **Stage 5**: Applies calibration to create CORRECTED_DATA column
- **Stage 6**: Imaging with optional development tier for speed (⚠️ NON-SCIENCE)
- **Stage 7**: All products indexed in SQLite database
- **Stage 8**: API provides monitoring and access to all products

---

## Detailed Stage Breakdown

### Stage 1: Ingest & Grouping

```mermaid
flowchart LR
    subgraph INGEST_DETAIL["Ingest Process"]
        Files[UVH5 Files<br/>*_sb00.hdf5<br/>*_sb01.hdf5<br/>...<br/>*_sb15.hdf5]
        Watch[File System Watcher<br/>watchdog or polling]
        Parse[Parse Timestamp<br/>YYYY-MM-DDTHH:MM:SS]
        Group[Group by Time<br/>5-minute windows]
        Check[Check Completeness<br/>16 subbands required]
        State[Update Queue State<br/>collecting → pending]
    end
    
    Files --> Watch
    Watch --> Parse
    Parse --> Group
    Group --> Check
    Check -->|Complete| State
    Check -->|Incomplete| Wait[Wait for more subbands]
    Wait --> Check
    
    style State fill:#90EE90
    style Wait fill:#FFB6C1
```

**Details:**
- **Input**: `*_sb??.hdf5` files in `/data/incoming/`
- **Pattern**: `YYYY-MM-DDTHH:MM:SS_sb??.hdf5`
- **Grouping**: 5-minute time windows (configurable via `--chunk-duration`)
- **Completeness**: All 16 subbands must arrive before processing
- **Database**: `state/ingest.sqlite3` tracks `subband_files` and `ingest_queue`

---

### Stage 2: Conversion (UVH5 → MS)

```mermaid
flowchart TB
    subgraph CONVERT_DETAIL["Conversion Process"]
        Start[Group Acquired<br/>state: pending → in_progress]
        Orch[Orchestrator CLI<br/>hdf5_orchestrator.py]
        WriterSel{Writer Selection}
        Auto[Auto Mode<br/>--writer auto]
        
        subgraph PROD_PATH["Production Path (>2 subbands)"]
            Par[parallel-subband Writer]
            Subbands[Parallel Per-Subband Writes<br/>16 concurrent workers]
            Staging[Staging Decision]
            Tmpfs[tmpfs /dev/shm<br/>3-5x speedup]
            Disk[SSD Scratch<br/>fallback]
            Concat[CASA concat<br/>combine subbands]
        end
        
        subgraph TEST_PATH["Testing Path (≤2 subbands)"]
            Mono[pyuvdata Writer<br/>monolithic write]
        end
        
        Ops[Operations Applied]
        Identity[Set Telescope Identity<br/>DSA_110]
        Phase[Meridian Phasing<br/>at midpoint]
        UVW[Compute UVW Coordinates]
        Init[Initialize Columns<br/>MODEL_DATA<br/>CORRECTED_DATA<br/>WEIGHT_SPECTRUM]
        
        Output[Full-Band MS<br/>all 16 subbands<br/>all columns]
    end
    
    Start --> Orch
    Orch --> WriterSel
    WriterSel -->|Auto| Auto
    Auto -->|>2 subbands| Par
    Auto -->|≤2 subbands| Mono
    Par --> Subbands
    Subbands --> Staging
    Staging -->|tmpfs available| Tmpfs
    Staging -->|fallback| Disk
    Tmpfs --> Concat
    Disk --> Concat
    Mono --> Ops
    Concat --> Ops
    Ops --> Identity
    Identity --> Phase
    Phase --> UVW
    UVW --> Init
    Init --> Output
    
    style PROD_PATH fill:#E6F3FF
    style TEST_PATH fill:#FFF4E1
    style Output fill:#90EE90
```

**Details:**
- **Entry Point**: `hdf5_orchestrator.py` CLI (called by streaming worker)
- **Writer Selection**:
  - Production: `parallel-subband` (16 subbands) - default
  - Testing: `pyuvdata` (≤2 subbands only)
- **Staging**: tmpfs (`/dev/shm`) preferred for 3-5x speedup
- **Operations**: All applied during conversion to ensure MS is ready for imaging
- **Output**: Single full-band MS with all columns preallocated

---

### Stage 3: MS Preparation

```mermaid
flowchart LR
    subgraph PREP_DETAIL["MS Preparation"]
        MSIn[MS from Conversion]
        Validate[Validate MS<br/>- Readable<br/>- Not empty<br/>- Required columns exist]
        Config[Configure for Imaging<br/>- MODEL_DATA<br/>- CORRECTED_DATA<br/>- WEIGHT_SPECTRUM]
        Flag[RFI Flagging<br/>1. Reset flags<br/>2. Flag zeros<br/>3. Statistical RFI]
        MSOut[Ready MS]
    end
    
    MSIn --> Validate
    Validate -->|Pass| Config
    Validate -->|Fail| Error[Error: Invalid MS]
    Config --> Flag
    Flag --> MSOut
    
    style Validate fill:#FFE4E1
    style Config fill:#E6F3FF
    style Flag fill:#FFF4E1
    style MSOut fill:#90EE90
```

**Details:**
- **Validation**: Ensures MS is readable and contains required data
- **Configuration**: Initializes imaging columns (CASA requirement)
- **Flagging**: Removes bad data before calibration
- **Critical**: MS must pass all checks before proceeding

---

### Stage 4: Calibration

```mermaid
flowchart TB
    subgraph CAL_DETAIL["Calibration Process"]
        MSIn[Prepared MS]
        Check{Has Calibrator<br/>Field?}
        
        subgraph CAL_PATH["Calibrator Path"]
            SkyModel[NVSS Sky Model<br/>≥10 mJy sources<br/>0.2 deg radius]
            FT[ft: Populate MODEL_DATA<br/>with sky model]
            K{K-Calibration?<br/>--do-k flag}
            KCal[K-Calibration<br/>Delay/Phase<br/>Frequency-independent]
            SkipK[Skip K-Cal<br/>Default for DSA-110<br/>short baselines]
            BPCal[BP-Calibration<br/>Bandpass<br/>Frequency-dependent<br/>uvrange cut optional]
            GCal[G-Calibration<br/>Gains<br/>Time-variable<br/>phase-only in fast mode]
            Reg[Register Caltables<br/>cal_registry.sqlite3<br/>validity windows]
        end
        
        subgraph NO_CAL_PATH["No Calibrator Path"]
            Query[Query Active Caltables<br/>by MS mid-MJD]
            UseExisting[Use Existing Caltables]
        end
        
        MSIn --> Check
        Check -->|Yes| SkyModel
        Check -->|No| Query
        SkyModel --> FT
        FT --> K
        K -->|--do-k| KCal
        K -->|Default| SkipK
        KCal --> BPCal
        SkipK --> BPCal
        BPCal --> GCal
        GCal --> Reg
        Query --> UseExisting
        Reg --> Apply
        UseExisting --> Apply
        
        style CAL_PATH fill:#E6F3FF
        style NO_CAL_PATH fill:#FFF4E1
    end
    
    Apply[Apply Caltables]
    style Apply fill:#90EE90
```

**Details:**
- **K-Calibration**: Skipped by default (short baselines, delays <0.5 ns absorbed into gains)
- **BP-Calibration**: Frequency-dependent gains, uses "G" mode
- **G-Calibration**: Time-variable atmospheric effects, uses "p" (phase-only) mode in development tier
- **Fast Mode**: Time/channel binning, phase-only gains, uvrange cuts
- **Registry**: All caltables registered with validity windows for automatic selection

---

### Stage 5: Apply Calibration

```mermaid
flowchart LR
    subgraph APPLY_DETAIL["Apply Calibration"]
        MSIn[MS with Caltables]
        Apply[applycal<br/>Apply to CORRECTED_DATA]
        Verify[Verify CORRECTED_DATA<br/>non-zero values]
        MSOut[Calibrated MS]
    end
    
    MSIn --> Apply
    Apply --> Verify
    Verify -->|Valid| MSOut
    Verify -->|Invalid| Warn[Warning: All zeros]
    
    style Apply fill:#E6F3FF
    style Verify fill:#FFE4E1
    style MSOut fill:#90EE90
```

**Details:**
- **Process**: `applycal` writes calibrated visibilities to `CORRECTED_DATA`
- **Validation**: Ensures corrected data is populated (not all zeros)
- **Registry**: Queries active caltables by MS mid-MJD for automatic selection

---

### Stage 6: Imaging

```mermaid
flowchart TB
    subgraph IMAGE_DETAIL["Imaging Process"]
        MSIn[Calibrated MS<br/>CORRECTED_DATA]
        Clean[tclean<br/>CASA deconvolution]
        Mode{Imaging Mode}
        
        subgraph QUICK_MODE["Quick Mode (--quick)"]
            Quick[Quick Imaging<br/>- imsize ≤ 512<br/>- niter ≤ 300<br/>- robust ~ 0<br/>- PB correction]
        end
        
        subgraph FULL_MODE["Full Mode"]
            Full[Full Quality<br/>- imsize from config<br/>- niter from config<br/>- robust from config<br/>- PB correction]
        end
        
        Fits{Export FITS?<br/>--skip-fits}
        FITS[FITS Export<br/>.pbcor.fits]
        CASA[CASA Images<br/>.image, .pb, etc.]
    end
    
    MSIn --> Clean
    Clean --> Mode
    Mode -->|--quick| Quick
    Mode -->|Default| Full
    Quick --> Fits
    Full --> Fits
    Fits -->|No| CASA
    Fits -->|Yes| FITS
    
    style QUICK_MODE fill:#FFF4E1
    style FULL_MODE fill:#E6F3FF
    style FITS fill:#90EE90
    style CASA fill:#90EE90
```

**Details:**
- **Quick Mode**: For speed and operator QA, reduced parameters
- **Full Mode**: Production quality with full deconvolution
- **PB Correction**: Primary beam correction always applied
- **FITS Export**: Optional for speed (CASA images sufficient for CASA tools)

---

### Stage 7: Products & Indexing

```mermaid
flowchart TB
    subgraph PRODUCT_DETAIL["Products & Indexing"]
        Images[Image Files<br/>.image, .pb, .pbcor.fits]
        MSFiles[MS Files<br/>.ms directory]
        QAArt[QA Artifacts<br/>plots, thumbnails]
        
        subgraph DB["Products DB (products.sqlite3)"]
            MSIdx[ms_index Table<br/>- path (PRIMARY KEY)<br/>- start_mjd, end_mjd, mid_mjd<br/>- processed_at, status, stage<br/>- cal_applied, imagename]
            ImgIdx[images Table<br/>- id, path, ms_path<br/>- created_at, type<br/>- beam_major_arcsec<br/>- noise_jy, pbcor]
            QAIdx[QA Index<br/>- qa_artifacts table<br/>- links to images]
        end
        
        Images --> MSIdx
        MSFiles --> MSIdx
        Images --> ImgIdx
        QAArt --> QAIdx
    end
    
    style DB fill:#E6F3FF
```

**Details:**
- **MS Index**: Tracks all Measurement Sets with metadata and processing status
- **Image Index**: Tracks all images with quality metrics
- **QA Index**: Links QA artifacts (plots, thumbnails) to images
- **Status Tracking**: `status` field tracks processing state, `stage` tracks current stage

---

### Stage 8: Monitoring & Access

```mermaid
flowchart LR
    subgraph API_DETAIL["FastAPI Monitoring"]
        Products[Products DB]
        FastAPI[FastAPI Server<br/>uvicorn]
        
        subgraph ENDPOINTS["API Endpoints"]
            Status[/api/status<br/>queue, calibration, products]
            ProductsEP[/api/ms_index<br/>filtered MS index]
            ImagesEP[/api/images<br/>image metadata]
            QAEP[/api/qa<br/>QA artifacts]
            Reprocess[/api/reprocess/{group_id}<br/>reprocess group]
        end
        
        Products --> FastAPI
        FastAPI --> ENDPOINTS
    end
    
    style FastAPI fill:#E6F3FF
    style ENDPOINTS fill:#90EE90
```

**Details:**
- **Status Endpoints**: Real-time queue and system status
- **Product Endpoints**: Filtered access to MS index and images
- **QA Endpoints**: Serve QA plots and thumbnails
- **Reprocessing**: Manual trigger to reprocess failed groups

---

## State Machine & Queue Management

### Queue State Transitions

```mermaid
stateDiagram-v2
    [*] --> collecting: New subband file detected
    
    collecting --> collecting: More subbands arriving (waiting for 16)
    collecting --> pending: All 16 subbands arrived (complete group)
    collecting --> failed: Timeout exceeded (collecting_timeout)
    
    pending --> in_progress: Worker acquires group
    pending --> failed: Max retries exceeded
    
    in_progress --> processing_fresh: First conversion attempt
    in_progress --> resuming: Recovery from checkpoint
    
    processing_fresh --> processing_fresh: Checkpoint saved
    processing_fresh --> completed: Conversion successful
    processing_fresh --> failed: Conversion failed
    
    resuming --> resuming: Checkpoint saved
    resuming --> completed: Conversion successful
    resuming --> failed: Conversion failed
    
    completed --> [*]
    failed --> [*]
    
    note right of collecting
        Waiting for all 16 subbands
        in 5-minute time window
    end note
    
    note right of pending
        Ready for processing
        Worker will pick up
    end note
    
    note right of in_progress
        Worker claimed group
        Processing starting
    end note
    
    note right of completed
        MS written successfully
        Products indexed
    end note
```

**State Details:**
- **collecting**: Waiting for all 16 subbands to arrive
- **pending**: Complete group ready for processing
- **in_progress**: Worker has claimed the group
- **processing_fresh**: First conversion attempt (no checkpoint)
- **resuming**: Recovery from existing checkpoint
- **completed**: Successfully processed and indexed
- **failed**: Exceeded retry budget or unrecoverable error

### Stage Tracking

```mermaid
flowchart LR
    subgraph STAGES["Processing Stages"]
        S1[Stage 1: Ingest]
        S2[Stage 2: Conversion]
        S3[Stage 3: MS Prep]
        S4[Stage 4: Calibration]
        S5[Stage 5: Apply Cal]
        S6[Stage 6: Imaging]
        S7[Stage 7: Indexing]
    end
    
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5
    S5 --> S6
    S6 --> S7
    S7 --> Done[Complete]
    
    style S1 fill:#E6F3FF
    style S2 fill:#FFF4E1
    style S3 fill:#F0F0F0
    style S4 fill:#E1FFE1
    style S5 fill:#FFE1F5
    style S6 fill:#F5E1FF
    style S7 fill:#FFE1E1
    style Done fill:#90EE90
```

**Stage Field**: Tracks current processing stage in `ms_index` table for monitoring and debugging.

---

## Data Products & Artifacts

### File Structure

```
/data/ms/
├── 2025-11-02T13:40:03.ms/          # Measurement Set (directory)
│   ├── ANTENNA
│   ├── DATA
│   ├── FIELD
│   ├── SPECTRAL_WINDOW
│   └── ...
├── 2025-11-02T13:40:03.bpcal/       # Bandpass calibration table
├── 2025-11-02T13:40:03.gcal/        # Gain calibration table
├── 2025-11-02T13:40:03.image/       # CASA image (directory)
│   ├── image
│   ├── mask
│   └── ...
├── 2025-11-02T13:40:03.pb/          # Primary beam image
└── 2025-11-02T13:40:03.pbcor.fits   # Primary beam corrected FITS
```

### Database Schema

**Queue DB (`ingest.sqlite3`):**
- `ingest_queue`: Group state and metadata
- `subband_files`: Individual file tracking
- `performance_metrics`: Conversion timings and writer type

**Cal Registry DB (`cal_registry.sqlite3`):**
- `caltables`: Calibration table registry with validity windows

**Products DB (`products.sqlite3`):**
- `ms_index`: MS metadata and processing status
- `images`: Image metadata and quality metrics
- `qa_artifacts`: QA plots and thumbnails

---

## Database Interactions

### Data Flow Through Databases

```mermaid
flowchart TB
    subgraph QUEUE["Queue DB (ingest.sqlite3)"]
        Queue[ingest_queue<br/>Group state tracking]
        Files[subband_files<br/>File arrival tracking]
        Perf[performance_metrics<br/>Timing metrics]
    end
    
    subgraph REGISTRY["Cal Registry DB (cal_registry.sqlite3)"]
        CalReg[caltables<br/>Calibration table registry<br/>Validity windows]
    end
    
    subgraph PRODUCTS["Products DB (products.sqlite3)"]
        MSIdx[ms_index<br/>MS metadata<br/>Processing status]
        ImgIdx[images<br/>Image metadata<br/>Quality metrics]
        QAIdx[qa_artifacts<br/>QA plots/thumbnails]
    end
    
    Queue --> MSIdx
    Files --> Queue
    Perf --> Queue
    CalReg --> MSIdx
    MSIdx --> ImgIdx
    ImgIdx --> QAIdx
    
    style QUEUE fill:#E6F3FF
    style REGISTRY fill:#FFF4E1
    style PRODUCTS fill:#E1FFE1
```

**Key Interactions:**
1. **Queue DB**: Tracks ingestion and conversion state
2. **Cal Registry**: Manages calibration table validity and selection
3. **Products DB**: Central repository for all processing products

---

## Performance Optimization Paths

### Fast Path Options

```mermaid
flowchart TB
    subgraph OPTIMIZATIONS["Performance Optimization Options"]
        Start[Pipeline Start]
        
        subgraph CONVERT_OPT["Conversion Optimizations"]
            Tmpfs[tmpfs Staging<br/>/dev/shm<br/>3-5x speedup]
            Par[Parallel Writes<br/>16 concurrent workers]
        end
        
        subgraph CAL_OPT["Calibration Optimizations"]
            Fast[Fast Mode<br/>--fast flag]
            Timebin[Time Binning<br/>--timebin 30s]
            Chanbin[Channel Binning<br/>--chanbin 4]
            UVRange[UV Range Cut<br/>--uvrange >1klambda]
            PhaseOnly[Phase-Only Gains<br/>--phase-only]
        end
        
        subgraph IMAGE_OPT["Imaging Optimizations"]
            Quick[Quick Mode<br/>--quick flag]
            SmallImg[Small Image Size<br/>imsize ≤ 512]
            FewIter[Fewer Iterations<br/>niter ≤ 300]
            SkipFITS[Skip FITS Export<br/>--skip-fits]
        end
        
        Start --> Tmpfs
        Start --> Par
        Tmpfs --> Fast
        Par --> Fast
        Fast --> Timebin
        Fast --> Chanbin
        Fast --> UVRange
        Fast --> PhaseOnly
        Timebin --> Quick
        Chanbin --> Quick
        UVRange --> Quick
        PhaseOnly --> Quick
        Quick --> SmallImg
        Quick --> FewIter
        Quick --> SkipFITS
    end
    
    style CONVERT_OPT fill:#E6F3FF
    style CAL_OPT fill:#FFF4E1
    style IMAGE_OPT fill:#E1FFE1
```

**Optimization Summary:**
- **Conversion**: tmpfs staging + parallel writes = 3-5x speedup
- **Calibration**: Fast mode with binning and cuts = 2-3x speedup
- **Imaging**: Quick mode with reduced parameters = 2-4x speedup
- **Combined**: Can achieve 10-20x overall speedup for quick-look processing

---

## Summary

This visualization provides a comprehensive view of the DSA-110 continuum imaging pipeline workflow:

1. **Continuous Ingestion**: Automated monitoring and grouping of UVH5 files
2. **Efficient Conversion**: Strategy-based conversion with performance optimizations
3. **Robust Calibration**: Flexible calibration with automatic table management
4. **Quality Imaging**: Configurable imaging with quick-look options
5. **Complete Indexing**: All products tracked in SQLite databases
6. **Full Monitoring**: API access to all pipeline components and products

**Key Design Principles:**
- **Modular**: Each stage is independent and testable
- **Resilient**: State tracking and checkpointing for recovery
- **Flexible**: Multiple optimization paths for different use cases
- **Observable**: Comprehensive logging and API monitoring

---

**Related Documentation:**
- `docs/pipeline.md` - Pipeline overview with decision points
- `docs/quickstart.md` - Quick start guide
- `docs/howto/PIPELINE_TESTING_GUIDE.md` - Testing procedures
- `MEMORY.md` - Codebase understanding and design decisions

