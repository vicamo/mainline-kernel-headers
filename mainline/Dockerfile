# syntax=docker/dockerfile:1
#
# Dockerfile — architecture-dependent install of mainline kernel headers.
#
#   Stage 1 "archive":  FROM mainline-kernel-headers:X.Y-archive
#                        Provides all archived .debs under /X.Y/X.Y.Z/.
#
#   Stage 2 "install":  FROM mainline-kernel-headers:X.Y
#                        Copies all .debs from archive, installs only those
#                        not yet installed (matching TARGETARCH).
#                        Tag as: mainline-kernel-headers:X.Y
#
# Build args:
#   KVER          - kernel series, e.g. "6.14" (required)
#   BASE_IMAGE    - override for cold start (default: mainline-kernel-headers:KVER)
#   ARCHIVE_IMAGE    - the archive image (default: mainline-kernel-headers:KVER-archive)
#   ARCHIVE_PLATFORM - platform of the archive image (default: linux/amd64)
#
# TARGETARCH is set automatically by Docker based on --platform.
#
# === Cold start ===
#
#   docker build --build-arg KVER=6.14 \
#     --build-arg BASE_IMAGE=ubuntu:24.04 \
#     -t mainline-kernel-headers:6.14 .
#
# === Cold start (multi-platform via buildx) ===
#
#   docker buildx build \
#     --platform linux/amd64,linux/arm64 \
#     --build-arg KVER=6.14 \
#     --build-arg BASE_IMAGE=ubuntu:24.04 \
#     -t mainline-kernel-headers:6.14 .
#
# === Incremental ===
#
#   docker build --build-arg KVER=6.14 \
#     -t mainline-kernel-headers:6.14 .
#

ARG KVER
ARG BASE_IMAGE=mainline-kernel-headers:${KVER}
ARG ARCHIVE_IMAGE=mainline-kernel-headers:${KVER}-archive
ARG ARCHIVE_PLATFORM=linux/amd64
ARG MAX_KERNELS=50

# ===========================================================================
# Stage 1: archive — source of all .debs under /X.Y/X.Y.Z/
# ===========================================================================
FROM --platform=${ARCHIVE_PLATFORM} ${ARCHIVE_IMAGE} AS archive

# ===========================================================================
# Stage 2: install — install only packages not yet installed
# ===========================================================================
FROM ${BASE_IMAGE} AS install

ARG KVER
ARG TARGETARCH
ARG MAX_KERNELS

SHELL ["/bin/bash", "-c"]
RUN --mount=from=archive,source=/${KVER},target=/tmp/archive/${KVER} <<'INSTALL'
set -euo pipefail

# Map Docker's TARGETARCH (OCI spec) to Debian architecture names
case "${TARGETARCH}" in
    amd64)   arch="amd64"  ;;
    arm64)   arch="arm64"  ;;
    arm)     arch="armhf"  ;;
    386)     arch="i386"   ;;
    ppc64le) arch="ppc64el";;
    s390x)   arch="s390x"  ;;
    riscv64) arch="riscv64";;
    *)       echo "ERROR: unsupported TARGETARCH=${TARGETARCH}"; exit 1 ;;
esac

shopt -s nullglob

# Enforce per-build kernel limit (0 = unlimited)
max_kernels="${MAX_KERNELS:-50}"

# Collect matching pairs: for each version dir, only install if BOTH
# the _all.deb (common headers) and _ARCH.deb (arch-specific) exist.
# A version dir may have multiple flavours (e.g. generic + generic-m68k).
to_install=()
new_versions=0
for verdir in /tmp/archive/${KVER}/*/; do
    all=("${verdir}"*_all.deb)
    arch_specific=("${verdir}"*_${arch}.deb)
    if [ ${#all[@]} -eq 0 ] || [ ${#arch_specific[@]} -eq 0 ]; then
        echo "  SKIP $(basename "${verdir}"): missing _all.deb or _${arch}.deb"
        continue
    fi

    # Filter out already-installed packages
    ver_debs=()
    for deb in "${all[@]}" "${arch_specific[@]}"; do
        pkg=$(dpkg-deb -f "${deb}" Package 2>/dev/null) || continue
        ver=$(dpkg-deb -f "${deb}" Version 2>/dev/null) || continue
        if dpkg-query -W -f='${Version}' "${pkg}" 2>/dev/null | grep -qxF "${ver}"; then
            echo "  SKIP ${pkg} ${ver} (already installed)"
        else
            ver_debs+=("${deb}")
        fi
    done

    [ ${#ver_debs[@]} -eq 0 ] && continue

    # Check kernel limit before adding this version
    if [ "${max_kernels}" -gt 0 ] && [ "${new_versions}" -ge "${max_kernels}" ]; then
        continue
    fi

    to_install+=("${ver_debs[@]}")
    ((new_versions++)) || true
done

if [ ${#to_install[@]} -eq 0 ]; then
    echo "=== All packages already installed for ${arch}. Up to date. ==="
    exit 0
fi

if [ "${max_kernels}" -gt 0 ] && [ "${new_versions}" -ge "${max_kernels}" ]; then
    echo ">>> Limited to ${max_kernels} kernel versions (MAX_KERNELS=${max_kernels})"
fi

echo ">>> Installing ${#to_install[@]} header package(s) for ${arch} (${new_versions} versions) ..."
apt-get update -qq && apt-get install -y --no-install-recommends "${to_install[@]}"

echo "=== Done installing kernel headers for ${arch} ==="
INSTALL
