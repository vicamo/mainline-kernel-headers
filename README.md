# mainline-kernel-headers

Docker images containing pre-installed Ubuntu mainline kernel headers from
[kernel.ubuntu.com/mainline](https://kernel.ubuntu.com/mainline/).

Two image types are produced for each kernel series (e.g. `7.0`):

| Image | Purpose | Platforms |
|-------|---------|-----------|
| `vicamo/mainline-kernel-headers:<KVER>-archive` | Architecture-independent archive of all `.deb` files | linux/amd64 |
| `vicamo/mainline-kernel-headers:<KVER>` | Installed kernel headers (Ubuntu-based) | linux/amd64, linux/arm64, linux/arm/v7, linux/ppc64le, linux/s390x |

## Quick start

List installed kernel header versions:

```sh
docker run --rm vicamo/mainline-kernel-headers:7.0
```

Use as a base image for out-of-tree module builds:

```dockerfile
FROM vicamo/mainline-kernel-headers:7.0
RUN apt-get update && apt-get install -y build-essential
# Build your module against any installed kernel version
```

## How it works

The build is split into two Dockerfiles. `Dockerfile` produces the install
image (the primary artifact); `Dockerfile.archive` produces the intermediate
archive image.

### Dockerfile.archive

Stores **all** kernel header `.deb` packages (for all architectures) from a
local `debs/<KVER>/` directory into a minimal image. This image is
architecture-independent and supports incremental builds. The actual fetching
is performed by `scripts/build-archive` before invoking Docker.

```sh
# Typically invoked via scripts/build-archive, but can be run manually
# after populating debs/<KVER>/:
docker build -f Dockerfile.archive --build-arg KVER=7.0 \
  --build-arg ARCHIVE_IMAGE=scratch \
  -t vicamo/mainline-kernel-headers:7.0-archive .
```

### Dockerfile

Takes an archive image and installs the appropriate `.deb` packages for the
target architecture using `dpkg --force-depends`. Supports multi-platform
builds via Docker buildx.

```sh
# Cold start (no previous install image)
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7,linux/ppc64le,linux/s390x \
  --build-arg KVER=7.0 \
  --build-arg BASE_IMAGE=ubuntu:24.04 \
  --build-arg ARCHIVE_IMAGE=vicamo/mainline-kernel-headers:7.0-archive \
  -t vicamo/mainline-kernel-headers:7.0 .

# Incremental build (installs only new versions on top of existing image)
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7,linux/ppc64le,linux/s390x \
  --build-arg KVER=7.0 \
  --build-arg ARCHIVE_IMAGE=vicamo/mainline-kernel-headers:7.0-archive \
  -t vicamo/mainline-kernel-headers:7.0 .
```

## Build scripts

Three helper scripts are provided under `scripts/`:

### scripts/build-archive

Build the archive image for a single kernel series.

```sh
./scripts/build-archive <KVER> [--push] [--image PREFIX]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--push` | *(off)* | Push image to the registry; without it, image is loaded locally |
| `--image` | `vicamo/mainline-kernel-headers` | Image name prefix |

Examples:

```sh
# Build locally
./scripts/build-archive 7.0

# Build and push to Docker Hub
./scripts/build-archive 7.0 --push
```

The script fetches all kernel header `.deb` packages from kernel.ubuntu.com
into `debs/<KVER>/`, then builds the archive Docker image. It automatically
detects whether a previous archive image exists and performs an incremental
build when possible. Already-downloaded versions are skipped on subsequent runs.

### scripts/build-version

Build the archive and install images for a single kernel series.

```sh
./scripts/build-version <KVER> [--push] [--image PREFIX] [--platforms PLATFORMS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--push` | *(off)* | Push images to the registry; without it, images are loaded locally (native platform only) |
| `--image` | `vicamo/mainline-kernel-headers` | Image name prefix |
| `--platforms` | `linux/amd64,linux/arm64,linux/arm/v7,linux/ppc64le,linux/s390x` | Target platforms for the install image (only with `--push`) |

Examples:

```sh
# Build locally for testing
./scripts/build-version 7.0

# Build and push to Docker Hub
./scripts/build-version 7.0 --push

# Push to a custom registry with fewer platforms
./scripts/build-version 7.0 --push --image myrepo/kernel-headers --platforms linux/amd64,linux/arm64
```

The script delegates archive building to `build-archive`, then builds the
multi-platform install image. It automatically detects whether a previous
install image exists and performs an incremental build when possible.

### scripts/build-all

Build all active kernel versions (stable + longterm, not EOL) as reported by
[kernel.org](https://www.kernel.org/releases.json).

```sh
./scripts/build-all [--push] [--image PREFIX] [--platforms PLATFORMS]
```

All flags are passed through to `build-version` for each kernel series.
A summary is printed at the end with any failures.

```sh
# Build and push all active versions
./scripts/build-all --push
```

## Build args

### Dockerfile.archive

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `KVER` | Yes | — | Kernel series, e.g. `6.14`, `7.0` |
| `ARCHIVE_IMAGE` | No | `mainline-kernel-headers:<KVER>-archive` | Previous archive image for incremental builds; set to `scratch` for cold start |

### Dockerfile

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `KVER` | Yes | — | Kernel series, e.g. `6.14`, `7.0` |
| `BASE_IMAGE` | No | `mainline-kernel-headers:<KVER>` | Previous install image; set to `ubuntu:24.04` for cold start |
| `ARCHIVE_IMAGE` | No | `mainline-kernel-headers:<KVER>-archive` | Archive image containing the `.deb` files |
| `ARCHIVE_PLATFORM` | No | `linux/amd64` | Platform of the archive image (archive is arch-independent, pinned to amd64 by default) |

## Inspecting images

Check available platforms:

```sh
docker buildx imagetools inspect vicamo/mainline-kernel-headers:7.0
```

## Available versions

Images are available from kernel series `5.19` through `7.0`.

## License

The kernel header packages are distributed under the terms of the Linux kernel
license (GPL-2.0). The Dockerfiles in this repository are provided as-is.
