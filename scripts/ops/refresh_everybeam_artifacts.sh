#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-wsclean-everybeam:0.7.4}"
DOCKERFILE_PATH="${DOCKERFILE_PATH:-/home/ubuntu/proj/wsclean/Dockerfile.everybeam-0.7.4}"
DOCKER_BUILD_CONTEXT="${DOCKER_BUILD_CONTEXT:-$(dirname "${DOCKERFILE_PATH}")}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
EVERYBEAM_DIR="${REPO_ROOT}/vendor/everybeam"
AOCOMMON_DIR="${REPO_ROOT}/vendor/aocommon"

if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
  echo "[refresh_everybeam] Building ${IMAGE_NAME} from ${DOCKERFILE_PATH}"
  docker build -f "${DOCKERFILE_PATH}" -t "${IMAGE_NAME}" "${DOCKER_BUILD_CONTEXT}"
fi

container_id="$(docker create "${IMAGE_NAME}")"
cleanup() {
  docker rm -f "${container_id}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

mkdir -p "${EVERYBEAM_DIR}/include" "${EVERYBEAM_DIR}/lib" "${AOCOMMON_DIR}"
rm -rf "${EVERYBEAM_DIR}/include/EveryBeam" "${EVERYBEAM_DIR}/lib/everybeam" "${AOCOMMON_DIR}/aocommon"

libs=(
  libeverybeam.so
  libeverybeam-core.so
  libeverybeam-hamaker.so
  libeverybeam-oskar.so
  libeverybeam-skamidbeam.so
)

echo "[refresh_everybeam] Copying EveryBeam headers"
docker cp "${container_id}:/usr/local/include/EveryBeam" "${EVERYBEAM_DIR}/include/"

echo "[refresh_everybeam] Copying EveryBeam shared libraries"
for lib in "${libs[@]}"; do
  docker cp "${container_id}:/usr/local/lib/${lib}" "${EVERYBEAM_DIR}/lib/"
done

echo "[refresh_everybeam] Copying EveryBeam CMake package metadata"
docker cp "${container_id}:/usr/local/lib/everybeam" "${EVERYBEAM_DIR}/lib/"

echo "[refresh_everybeam] Copying aocommon headers"
docker cp "${container_id}:/src/vendor/aocommon/include" "${AOCOMMON_DIR}/aocommon"

echo "[refresh_everybeam] Done. Staged artifacts under vendor/"
