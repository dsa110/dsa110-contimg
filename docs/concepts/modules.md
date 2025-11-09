# Module Interconnections

This diagram shows high-level dependencies among actively used modules, ops scripts, and docs.

```mermaid
graph TB
  subgraph Ops["Operations & Scripts"]
    OPS_STREAM["contimg-stream.service"]
    OPS_DOCKER["docker-compose.yml"]
    OPS_PIPE_BUILD["build_central_calibrator_group.py"]
    OPS_PIPE_IMAGE["image_groups_in_timerange.py"]
    OPS_PIPE_OFFSETS["build_calibrator_transit_offsets.py"]
    OPS_PIPE_CURATE["curate_transit.py"]
    OPS_RUN_CONV["run_conversion.sh"]
    OPS_CAL_BP["calibrate_bandpass.sh"]
    OPS_IMAGE_MS["image_ms.sh"]
  end

  subgraph Conversion["Conversion Module"]
    CLI_CONV["cli.py"]
    UVH5_TO_MS["uvh5_to_ms.py"]
    HDF5_ORCH["hdf5_orchestrator.py"]
    STREAMING["streaming_converter.py"]
    MS_UTILS["ms_utils.py"]
    HELPERS["helpers.py"]
    DS_FAST["downsample_hdf5_fast.py"]
    DS_SINGLE["downsample_hdf5.py"]
    DS_BATCH["downsample_hdf5_batch.py"]
  end

  subgraph Calibration["Calibration Module"]
    CAL_CLI["cli.py"]
    CAL_CORE["calibration.py"]
    CAL_MODEL["model.py"]
  end

  subgraph Imaging["Imaging Module"]
    IMG_CLI["cli.py"]
    IMG_WORKER["worker.py"]
  end

  subgraph DB["Database Module"]
    DB_REG["registry.py"]
    DB_REG_CLI["registry_cli.py"]
    DB_PRODUCTS["products_db.py"]
  end

  subgraph QA["QA Module"]
    QA_FAST["fast_plots.py"]
  end

  subgraph API["API Module"]
    API_ROUTES["routes.py"]
    API_MODELS["models.py"]
    API_DA["data_access"]
  end

  subgraph Docs["Documentation"]
    DOCS_CLI["cli.md"]
    DOCS_PIPE["README_uvh5_to_ms.md"]
    DOCS_DEP_SYS["deploy-systemd.md"]
    DOCS_DEP_DOCK["deploy-docker.md"]
  end

  %% Ops -> Modules
  OPS_STREAM --> STREAMING
  OPS_DOCKER --> STREAMING
  OPS_RUN_CONV --> HDF5_ORCH
  OPS_PIPE_BUILD --> UVH5_TO_MS
  OPS_PIPE_BUILD --> HDF5_ORCH
  OPS_PIPE_IMAGE --> UVH5_TO_MS
  OPS_PIPE_IMAGE --> HDF5_ORCH
  OPS_PIPE_OFFSETS --> UVH5_TO_MS
  OPS_PIPE_CURATE --> HDF5_ORCH
  OPS_CAL_BP --> CAL_CLI
  OPS_IMAGE_MS --> IMG_CLI

  %% Conversion internals
  HDF5_ORCH --> MS_UTILS
  HDF5_ORCH --> HELPERS
  UVH5_TO_MS --> MS_UTILS
  UVH5_TO_MS --> HELPERS
  STREAMING --> HDF5_ORCH
  STREAMING --> DB_PRODUCTS

  %% Calibration flow
  CAL_CLI --> CAL_CORE
  CAL_CLI --> CAL_MODEL
  CAL_CORE --> DB_REG
  CAL_CORE --> QA_FAST

  %% Imaging flow
  IMG_CLI --> IMG_WORKER
  IMG_WORKER --> DB_PRODUCTS

  %% Downsample tools
  DS_BATCH --> DS_FAST
  DS_SINGLE -. optional .-> DS_FAST

  %% Docs
  DOCS_CLI --> STREAMING
  DOCS_CLI --> HDF5_ORCH
  DOCS_CLI --> IMG_WORKER
  DOCS_CLI --> DB_REG_CLI
  DOCS_PIPE --> UVH5_TO_MS
  DOCS_DEP_SYS --> STREAMING
  DOCS_DEP_DOCK --> STREAMING
  API_ROUTES --> DB_PRODUCTS
  API_ROUTES --> DB_REG
  API_ROUTES --> STREAMING

  style Ops fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#000
  style Conversion fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#000
  style Calibration fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
  style Imaging fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
  style DB fill:#E0F2F1,stroke:#00796B,stroke-width:2px,color:#000
  style QA fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
  style API fill:#E1F5FE,stroke:#0277BD,stroke-width:2px,color:#000
  style Docs fill:#F5F5F5,stroke:#616161,stroke-width:2px,color:#000
```
