# Graphiti Knowledge Graph Upload Log

**Date:** 2025-11-10  
**Group ID:** dsa110-contimg

## Summary
This document tracks episodes added to the Graphiti knowledge graph for CARTA and VAST project analysis.

---

## CARTA Episodes (Session 1 - Initial Analysis)

1. CARTA Project Overview
2. CARTA Backend Architecture Details
3. CARTA Backend Dependencies and Build
4. CARTA Backend Session Management
5. CARTA Frontend Architecture Details
6. CARTA Frontend Technologies and Dependencies
7. CARTA Controller Architecture
8. CARTA Protocol Buffers Interface
9. CARTA File Format Support
10. CARTA Rendering and Performance
11. CARTA Image Processing Features
12. CARTA Python Scripting Interface
13. CARTA Testing Infrastructure
14. CARTA Deployment and Installation
15. CARTA Advanced Features
16. CARTA Version History and Development
17. CARTA Authentication and Security
18. CARTA WebGL Rendering Implementation
19. CARTA Region System Details
20. CARTA Compression and Data Transfer
21. CARTA Catalog Integration

---

## CARTA Episodes (Session 2 - Deep Dive)

22. CARTA Test Infrastructure and Testing Frameworks
   - Robot Framework E2E tests
   - ICD-RxJS integration tests
   - Python API unit tests
   - Controller tests

23. CARTA Test Data Generation and Management
   - Image generator tool (make_image.py)
   - Test data organization
   - Regeneration scripts

24. CARTA Build Tools and Development Infrastructure
   - Code quality tools (style.py)
   - Build scripts (Docker, Singularity)
   - Third-party dependencies
   - Platform-specific Dockerfiles

25. CARTA WebAssembly Implementation
   - WASM libraries (AST, GSL, ZFP, Zstd)
   - Computation functions
   - Build process and integration

26. CARTA Python API Testing and Validation
   - Test suites (session, image, raster, etc.)
   - Mock-based testing
   - Validation and error handling

27. CARTA Authentication and Security Infrastructure
   - Token-based authentication
   - Linux PAM integration
   - User mapping
   - Security features

28. CARTA Documentation Structure and Manual Source
   - Sphinx-based documentation
   - User manual sections
   - Appendices and build system

---

## VAST Episodes

29. VAST Project Overview
   - Ecosystem overview
   - Key components introduction

30. VAST Pipeline Architecture and Features
   - Main pipeline details
   - Django web app
   - PostgreSQL with Q3C
   - Dask parallelization

31. VAST Tools Capabilities
   - vast-tools module
   - Interactive exploration
   - Pilot Survey tools

32. VASTER Intra-Observation Transient Detection
   - Fast transient pipeline
   - Configuration and deployment

33. VAST Multi-Wavelength Tools
   - Crossmatching capabilities
   - External catalog queries

34. VAST Post-Processing Tools
   - Image/catalogue processing
   - MOC generation

35. VAST Supporting Tools and Infrastructure
   - askap_surveys, casdapy, dstools
   - forced_phot, source_models
   - vaster-webapp, nectar-monitoring

---

## VAST Episodes (Session 3 - Detailed Analysis)

36. VAST Pipeline Core Architecture and Workflow
   - Pipeline class architecture
   - Processing workflow steps
   - Configuration schema
   - Image upload and measurement creation
   - Sky region grouping
   - Source association methods
   - New source detection
   - Forced extraction integration
   - Finalization operations

37. VAST Pipeline Database Models and Schema
   - Django ORM models (Run, Band, SkyRegion, Image, Measurement, Source, Association)
   - PostgreSQL with Q3C spatial indexing
   - Parquet file storage
   - Relationships and foreign keys
   - QuerySet methods (cone_search)
   - CommentableModel system

38. VAST Pipeline Source Association Algorithms
   - Basic association (nearest-neighbor matching)
   - Advanced association (uncertainty-weighted)
   - De Ruiter association (statistical method)
   - One-to-many and many-to-many handling
   - Parallel association processing
   - Epoch-based vs time-ordered association
   - Source ID correction

39. VAST Pipeline Forced Extraction Implementation
   - ForcedPhot integration
   - Extract_from_image function
   - Cluster photometry
   - Edge buffer handling
   - Monitoring mode (backward/forward)
   - Batch processing
   - Database integration

40. VAST Tools Architecture and Core Classes
   - PipeRun class (pipeline run interface)
   - Source class (individual source representation)
   - Query class (data querying interface)
   - VASTMOCS class (MOC operations)
   - Survey classes (Fields, Image)
   - Utilities and tools modules
   - Console scripts

41. VASTER Intra-Observation Transient Detection Implementation
   - Data preparation and download
   - Script generation for HPC
   - Candidate selection algorithms
   - Statistical analysis (chi-square, significance)
   - Cube class for 3D data
   - Imaging scripts (model making, short imaging)
   - Configuration and workflow

42. VAST Post-Processing Tools Implementation
   - Crop module (image and catalogue cropping)
   - Corrections module (astrometric and flux corrections)
   - Crossmatch module (catalogue matching)
   - Neighbours module (linking and convolving)
   - MOC generation
   - CLI interface (Typer-based)
   - Validation and quality control

43. VAST Supporting Tools Detailed Analysis
   - askap_surveys (survey parameters and MOCs)
   - casdapy (CASDA API)
   - dstools (dynamic spectrum processing)
   - forced_phot (forced photometry)
   - source_models (nova modeling)
   - vast-mw (multi-wavelength queries)
   - vaster-webapp (Django classification tool)
   - nectar-monitoring (Grafana/Prometheus)

---

## VAST Episodes (Session 4 - Reusable Patterns and Templates)

44. VAST Pipeline Utility Patterns and Reusable Functions
   - Coordinate transformation utilities (eq_to_cart, deg2dms, deg2hms, equ2gal)
   - Data type optimization (optimise_numeric)
   - Dictionary operations (dict_merge)
   - Timing utilities (StopWatch)
   - Memory management utilities
   - Worker and partition calculation
   - Sky region utilities
   - Image utilities (on_sky_sep, calc_error_radius, calc_condon_flux_errors)
   - Measurement loading utilities
   - Duplicate removal patterns

45. VAST Pipeline Data Storage and Parquet Patterns
   - Parquet file writing patterns
   - Measurement parquet structure
   - Arrow file creation patterns
   - Parquet reading patterns (selective columns, index-based, Dask)
   - DataFrame optimization before storage
   - Repartitioning patterns
   - Backup patterns
   - Temporary file handling
   - Memory-efficient processing

46. VAST Pipeline Database Bulk Operations Patterns
   - Bulk upload pattern (bulk_upload_model)
   - Model generator pattern
   - Bulk update pattern (SQL_update)
   - Batch deletion pattern
   - Transaction management
   - Memory management
   - ID mapping pattern
   - Add mode pattern

47. VAST Pipeline Dask Parallel Processing Patterns
   - Dask configuration
   - Partition calculation pattern
   - Parallel groupby pattern
   - Meta specification pattern
   - Parallel coordinate calculation
   - Measurement pairs calculation
   - Repartitioning pattern
   - Memory-aware processing
   - Worker management
   - Error handling

48. VAST Pipeline Variability Metrics and Statistical Calculations
   - Vs metric (t-statistic)
   - M metric (modulation index)
   - Eta metric (weighted variance)
   - Measurement pair generation
   - Aggregate pair metrics
   - Source aggregate statistics
   - Weighted average pattern
   - Statistical aggregation

49. VAST Pipeline Image Processing and FITS Handling Patterns
   - FITS image class hierarchy
   - FITS file opening pattern
   - Header extraction pattern
   - WCS coordinate extraction
   - Field of view calculation
   - Frequency extraction
   - Catalogue reading pattern
   - Measurement DataFrame creation

50. VAST Post-Processing Configuration and Pipeline Patterns
   - Priority-based configuration
   - Configuration variable types
   - Pipeline orchestration pattern
   - Path discovery pattern
   - Corresponding path resolution
   - Error handling pattern
   - Logging pattern
   - File output pattern
   - MOC generation pattern

51. VASTER Significance Cube and Statistical Analysis Patterns
   - Significance map generation (Map class)
   - Kernel types (gaussian, psf, combine)
   - Gaussian kernel generation
   - Cube class (3D data cube)
   - Statistical map generation
   - Candidate selection pattern
   - G2D class (2D Gaussian)
   - Data structure pattern (DataBasic)

52. VAST Tools Query and Data Access Patterns
   - Query class pattern
   - Field finding pattern
   - Source finding pattern
   - Data loading pattern
   - Parallel processing
   - Source object creation
   - PipeRun class pattern
   - MOC operations pattern

53. VAST Pipeline Association Data Structure Patterns
   - Sources DataFrame structure
   - Skyc1 sources DataFrame
   - Association result structure
   - Related sources structure
   - One-to-many handling
   - Many-to-one handling
   - Reconstruction pattern
   - Ideal coverage analysis
   - Sky region grouping
   - Parallel association data flow

54. VAST Pipeline Error Handling and Validation Patterns
   - Configuration validation pattern
   - Input validation
   - File path validation
   - Error classes
   - Database validation
   - Data validation patterns
   - Try-except patterns
   - Transaction rollback
   - Graceful degradation
   - Error logging
   - Status management

55. VAST Pipeline Association Algorithm Implementation Details
   - Basic association implementation
   - Advanced association implementation
   - De Ruiter calculation
   - One-to-many handling (basic and advanced)
   - Many-to-many handling
   - Many-to-one handling
   - Parallel association pattern
   - Source ID management
   - Relationship tracking
   - Epoch duplicate detection

56. VAST Post-Processing Crossmatch and Correction Patterns
   - Crossmatch pattern (crossmatch_qtables)
   - Positional offset calculation
   - Flux offset calculation (Huber regressor)
   - Correction application pattern
   - Condon error calculation
   - Robust regression pattern
   - Neighbour processing pattern

57. VAST Tools Survey Data and Field Management Patterns
   - Survey classes (Fields, Image)
   - Field loading pattern
   - Field centre loading
   - Epoch information
   - MOC integration
   - Data directory structure
   - Image access pattern

58. VAST Pipeline Command-Line Interface and Management Patterns
   - Management command pattern
   - Pipeline execution function
   - Status management
   - Configuration handling
   - Add mode detection
   - Error handling
   - Logging setup
   - Full rerun pattern

59. VAST Pipeline External Query and Crossmatching Patterns
   - SIMBAD query pattern
   - NED query pattern
   - Error handling
   - Result formatting

---

## Status

- **Total Episodes Added:** 59
- **CARTA Episodes:** 28
- **VAST Episodes:** 31 (7 overview + 8 detailed + 16 reusable patterns)
- **Processing Status:** Asynchronous (episodes queued, entity extraction in progress)

---

## Verification Commands

To check episode status in Neo4j:

```cypher
// Count all episodes
MATCH (n:Episodic) RETURN count(*) as total

// List CARTA episodes
MATCH (n:Episodic) WHERE toLower(n.name) CONTAINS "carta" 
RETURN n.name ORDER BY n.created_at DESC

// List VAST episodes
MATCH (n:Episodic) WHERE toLower(n.name) CONTAINS "vast" 
RETURN n.name ORDER BY n.created_at DESC

// Check for extracted entities
MATCH (n:Entity) WHERE toLower(n.name) CONTAINS "carta" OR toLower(n.name) CONTAINS "vast"
RETURN n.name, labels(n) ORDER BY n.name LIMIT 50
```

---

## Notes

- Episodes are processed sequentially by the async system
- Entity extraction happens automatically during processing
- Processing time depends on episode size and system load
- All episodes use group_id: "dsa110-contimg"

