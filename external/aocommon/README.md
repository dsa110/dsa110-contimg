# aocommon headers

This directory contains the header-only `aocommon` library staged from the
`wsclean-everybeam:0.7.4` Docker image (same source as the EveryBeam artifacts).
Use `./scripts/refresh_everybeam_artifacts.sh` to re-sync both EveryBeam and
`aocommon` in one go, or run the manual commands below.

```
docker build -f Dockerfile.everybeam-0.7.4 -t wsclean-everybeam:0.7.4 /home/ubuntu/proj/wsclean
container=$(docker create wsclean-everybeam:0.7.4)
docker cp "$container:/src/external/aocommon/include" external/aocommon/aocommon
# (optional) remove stale copy first: rm -rf external/aocommon/aocommon
```

The pybind11 wrapper consumes these headers via `-DAOCOMMON_ROOT`, keeping our
beam bindings in sync with the version of EveryBeam bundled with WSClean.
