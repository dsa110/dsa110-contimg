# Deprecated Scripts

These scripts were archived on 2025-12-05 because they depend on APIs that no longer exist
after the major refactoring described in `docs/design/COMPLEXITY_REDUCTION.md`.

## Archived Scripts

| Script                                                   | Original Location      | Reason                                                                                   |
| -------------------------------------------------------- | ---------------------- | ---------------------------------------------------------------------------------------- |
| `test_new_pipeline_e2e.py`                               | `scripts/ops/tests/`   | Missing `run_workflow_job` from `api.job_runner`; missing `fetch_observation_timeline`   |
| `get_first_two_tiles_from_earliest_calibrator_window.py` | `scripts/ops/imaging/` | Missing `api.data_access` module; missing `CalibratorMSConfig`, `StreamingMosaicManager` |
| `build_60min_mosaic.py`                                  | `scripts/ops/imaging/` | Uses deprecated CLI approach; `find_subband_groups` not in current API                   |
| `init_databases.py`                                      | `scripts/ops/utils/`   | `QueueDB` moved; `ensure_registry_db` removed; `evolve_all_schemas` doesn't exist        |
| `find_earliest_data.py`                                  | `scripts/ops/utils/`   | Missing `api.data_access`; undefined `repo_root` variable                                |
| `run_mosaic_test.py`                                     | `scripts/ops/test/`    | `precalculate_transits_for_calibrator` import path changed; old database paths           |
| `build_transit_mosaic.py`                                | `scripts/ops/`         | Uses `write_ms_from_subbands` which may not exist                                        |
| `build_central_calibrator_group.py`                      | `scripts/ops/`         | `find_subband_groups` doesn't exist; undefined function references                       |
| `build_calibrator_transit_offsets.py`                    | `scripts/ops/`         | Same issues as `build_central_calibrator_group.py`                                       |

## Key Missing/Changed APIs

- `dsa110_contimg.api.data_access` - Module doesn't exist
- `dsa110_contimg.api.job_runner.run_workflow_job` - Function doesn't exist
- `dsa110_contimg.database.registry.ensure_db` → moved to `dsa110_contimg.database.unified.ensure_db`
- `dsa110_contimg.conversion.streaming.QueueDB` → moved to `streaming_converter.QueueDB`
- `dsa110_contimg.conversion.strategies.hdf5_orchestrator.find_subband_groups` - Removed
- `dsa110_contimg.mosaic.streaming_mosaic.StreamingMosaicManager` - Class doesn't exist

## If You Need This Functionality

Consult the new pipeline architecture in:

- `docs/design/COMPLEXITY_REDUCTION.md`
- `docs/design/COMPLEXITY_REDUCTION_NOTES.md`
- `backend/src/dsa110_contimg/conversion/streaming/` for the new streaming pipeline
- `backend/src/dsa110_contimg/database/unified.py` for the consolidated database API
