# Graphiti Schema: dsa110-contimg Project

This document defines the schema for the `dsa110-contimg` project's Graphiti knowledge graph. It outlines the types of entities and relationships used to represent project knowledge.

## Entities

- **`SoftwareComponent`**: Represents a library, application, or service within the project.
- **`ContainerImage`**: Represents a Docker/OCI image.
- **`BuildProcess`**: Represents the process for building a container image (e.g., from a Dockerfile).
- **`ConfigurationFile`**: Represents a file that configures the project (e.g., `Dockerfile`, `docker-compose.yml`, `package.json`).
- **`Decision`**: Represents a significant architectural or implementation decision.
- **`Requirement`**: Represents a functional or non-functional requirement for the project.
- **`StorageLocation`**: Represents a filesystem path or mount where pipeline data is written or read (e.g., `/data`, `/dev/shm`, `/scratch`).
- **`DataPipelineStage`**: Represents a logical stage in the data flow (e.g., "Raw Visibilities", "Staging", "Processing Outputs").
- **`DataProduct`**: Represents a concrete artifact produced by the pipeline (e.g., UVH5 chunks, Measurement Sets, QA plots).

## Relationships

- **`DEPENDS_ON`**: A `SoftwareComponent` has a dependency on another `SoftwareComponent`.
- **`CONTAINS`**: A `ContainerImage` includes a `SoftwareComponent`.
- **`BUILT_FROM`**: A `ContainerImage` is built from a `BuildProcess`.
- **`DEFINED_IN`**: A `BuildProcess` is defined in a `ConfigurationFile`.
- **`DOCUMENTS`**: A file or document provides information about a `Decision` or `Requirement`.
- **`WRITES_TO`**: A `DataPipelineStage` or `DataProduct` writes data to a `StorageLocation`.
- **`READS_FROM`**: A `DataPipelineStage` or `DataProduct` consumes data from a `StorageLocation`.
- **`PRODUCES`**: A `DataPipelineStage` outputs a `DataProduct`.
- **`CONSUMES`**: A `DataPipelineStage` consumes a `DataProduct`.
- **`PRIMARY_LOCATION`**: A `DataPipelineStage` has a primary `StorageLocation` where it executes by default.
- **`ALTERNATE_LOCATION`**: A `StorageLocation` that can be used as a fallback or alternative for a given `DataPipelineStage`.
