# EveryBeam Artifacts

These headers and libraries were staged from the `wsclean-everybeam:0.7.4`
Docker image (built from
`/home/ubuntu/proj/wsclean/Dockerfile.everybeam-0.7.4`).

- `include/EveryBeam/` – public C++ headers installed into
  `/usr/local/include/EveryBeam`
- `lib/libeverybeam*.so` – shared libraries installed into `/usr/local/lib`
- `lib/everybeam/EveryBeamConfig*.cmake` – CMake package metadata

They allow us to compile a lightweight pybind11 wrapper without depending on the
full Docker build during development. When the Docker image is refreshed,
re-stage the artifacts with the helper script:

```bash
./scripts/refresh_everybeam_artifacts.sh
```

or manually:

```bash
docker build -f Dockerfile.everybeam-0.7.4 -t wsclean-everybeam:0.7.4 /home/ubuntu/proj/wsclean
container=$(docker create wsclean-everybeam:0.7.4)
docker cp "$container:/usr/local/include/EveryBeam" vendor/everybeam/include/
for lib in libeverybeam.so libeverybeam-core.so libeverybeam-hamaker.so \
           libeverybeam-oskar.so libeverybeam-skamidbeam.so; do
    docker cp "$container:/usr/local/lib/$lib" vendor/everybeam/lib/
done
docker cp "$container:/usr/local/lib/everybeam" vendor/everybeam/lib/
docker rm "$container"
```
