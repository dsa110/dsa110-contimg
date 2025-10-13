# Concepts: Architecture

```mermaid
flowchart LR
  A[UVH5 Subbands] --> B(Grouping)
  B --> C(Converter
Orchestrator)
  C -->|direct-subband| D[Group MS]
  D --> E{Calibrator?}
  E -->|Yes| F[Solve Cal Tables]
  F --> G[Registry]
  E -->|No| H[Apply Cal]
  G --> H
  H --> I[tclean Image]
  I --> J[Products DB
ms_index + images]
  J --> K[Monitoring API]
```
