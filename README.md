# Docker images of Linux kernel headers

Multi-platform Docker images containing pre-installed Linux kernel headers
for out-of-tree module development (DKMS, custom drivers, eBPF, etc.).

Two families of images are built:

| Family | Source | Tags | Description |
|--------|--------|------|-------------|
| **Mainline** | [kernel.ubuntu.com/mainline](https://kernel.ubuntu.com/mainline/) | `<KVER>`, `<KVER>-archive` | Upstream mainline/stable kernel headers (5.19–7.0+) |
| **Ubuntu** | Official Ubuntu archive | `<SERIES>-generic`, `<SERIES>` | Ubuntu generic kernel headers for each active release |

Both families share multi-platform dkms base images (`<SERIES>-dkms`).

All images are published to GHCR under
[`ghcr.io/vicamo/linux-headers`](https://github.com/vicamo/mainline-kernel-headers/pkgs/container/linux-headers).

## Quick start

### Mainline headers

```sh
# List installed mainline kernel header versions
docker run --rm ghcr.io/vicamo/linux-headers:7.0

# Use as a base for out-of-tree module builds
docker run --rm ghcr.io/vicamo/linux-headers:7.0 \
  ls /usr/src/linux-headers-*
```

### Ubuntu headers

```sh
# List installed Ubuntu generic kernel headers
docker run --rm ghcr.io/vicamo/linux-headers:noble-generic \
  dpkg -l 'linux-headers-*-generic'

# Use as a base for DKMS module builds
docker run --rm ghcr.io/vicamo/linux-headers:noble-generic \
  ls /usr/src/linux-headers-*
```

### Building an out-of-tree module

```dockerfile
FROM ghcr.io/vicamo/linux-headers:noble-generic
RUN apt-get update && apt-get install -y build-essential dkms
# Build your module against any installed kernel version
```

---

## Mainline images

Kernel headers from [kernel.ubuntu.com/mainline](https://kernel.ubuntu.com/mainline/),
covering stable and longterm series (currently 5.19 through 7.0).

### Image tags

| Image | Purpose | Platforms |
|-------|---------|-----------|
| `ghcr.io/vicamo/linux-headers:<KVER>-archive` | Architecture-independent archive of all `.deb` files | linux/amd64 |
| `ghcr.io/vicamo/linux-headers:<KVER>` | Installed kernel headers (Ubuntu-based) | *(auto-detected from base)* |

### How it works

The build is split into two stages:

1. **Archive** (`mainline/Dockerfile.archive`) — fetches and stores all kernel
   header `.deb` packages for all architectures into a minimal image.
   Supports incremental builds.

2. **Mainline** (`mainline/Dockerfile.mainline`) — installs the appropriate `.deb`
   packages for the target architecture from the archive image using
   `dpkg --force-depends`. Multi-platform via Docker buildx.

### Build scripts

Scripts are under `scripts/`:

#### scripts/build-archive

Build the archive image for a single kernel series.

```sh
./scripts/build-archive <KVER> [--push] [--scratch] [--image PREFIX]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--push` | *(off)* | Push image to the registry; without it, image is loaded locally |
| `--scratch` | *(off)* | Ignore existing archive annotation (cold start) |
| `--image` | `ghcr.io/vicamo/linux-headers` | Image name prefix |

```sh
./scripts/build-archive 7.0 --push
```

#### scripts/build-mainline

Build the mainline image for a single kernel series. Requires the archive image.

```sh
./scripts/build-mainline <KVER> [--push] [--image PREFIX] [--platforms PLATFORMS] [--force] [--scratch] [--limit N]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--push` | *(off)* | Push to registry; without it, loaded locally |
| `--image` | `ghcr.io/vicamo/linux-headers` | Image name prefix |
| `--platforms` | *(auto-detected from base image)* | Target platforms |
| `--force` | *(off)* | Force rebuild even if archive is unchanged |
| `--scratch` | *(off)* | Build from scratch (dkms base) instead of previous headers image |
| `--limit` | *(Dockerfile default: 50)* | Max kernel versions to install per build (0 = unlimited) |

```sh
./scripts/build-mainline 7.0 --push
```

#### scripts/build-mainline-all

Build all active kernel versions (stable + longterm, not EOL).

```sh
./scripts/build-mainline-all [--push] [--image PREFIX] [--platforms PLATFORMS] [--force] [--scratch] [--limit N]
```

All flags are passed through to `build-mainline` for each series.

### Build args

#### mainline/Dockerfile.archive

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `KVER` | Yes | — | Kernel series, e.g. `6.14`, `7.0` |
| `ARCHIVE_IMAGE` | No | `ghcr.io/vicamo/linux-headers:<KVER>-archive` | Previous archive image; `scratch` for cold start |

#### mainline/Dockerfile.mainline

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `KVER` | Yes | — | Kernel series, e.g. `6.14`, `7.0` |
| `BASE_IMAGE` | No | `ghcr.io/vicamo/linux-headers:<KVER>` | Previous mainline image; `<SERIES>-dkms` for cold start |
| `ARCHIVE_IMAGE` | No | `ghcr.io/vicamo/linux-headers:<KVER>-archive` | Archive image containing the `.deb` files |
| `ARCHIVE_PLATFORM` | No | `linux/amd64` | Platform of the archive image |
| `MAX_KERNELS` | No | `50` | Max kernel versions to install per build (0 = unlimited) |

### Image annotations

| Level | Key | Description |
|-------|-----|-------------|
| Per-platform manifest | `dev.mainline-kernel-headers.versions` | JSON object mapping flavour to installed versions, e.g. `{"generic":["7.0.1","7.0.2"],"lowlatency":["7.0"]}` |

---

## Ubuntu images

Ubuntu generic kernel headers from the official Ubuntu package archive,
built for each active Ubuntu release (noble, questing, resolute, etc.).

### Image tags

| Image | Purpose | Platforms |
|-------|---------|-----------|
| `ghcr.io/vicamo/linux-headers:<SERIES>-generic` | All `linux-headers-*-generic` packages installed | *(auto-detected from base)* |
| `ghcr.io/vicamo/linux-headers:<SERIES>` | Alias for `<SERIES>-generic` | *(same)* |

### How it works

A single Dockerfile (`ubuntu/Dockerfile.ubuntu`) runs `apt-cache search` to
discover all available `linux-headers-*-generic` packages, filters out
already-installed ones, and installs the rest. Supports incremental builds —
new kernel ABIs are added on top of the previous image.

### Build script

#### scripts/build-ubuntu

```sh
./scripts/build-ubuntu <SERIES> [--push] [--image PREFIX] [--platforms PLATFORMS] [--scratch] [--limit N]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--push` | *(off)* | Push to registry; without it, loaded locally |
| `--image` | `ghcr.io/vicamo/linux-headers` | Image name prefix |
| `--platforms` | *(auto-detected from base image)* | Target platforms |
| `--scratch` | *(off)* | Build from scratch (dkms base) instead of previous generic image |
| `--limit` | *(Dockerfile default: 50)* | Max kernel packages to install per build (0 = unlimited) |

```sh
./scripts/build-ubuntu noble --push
```

### Build args

#### ubuntu/Dockerfile.ubuntu

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `SERIES` | No | `noble` | Ubuntu series codename |
| `BASE_IMAGE` | No | `ghcr.io/vicamo/linux-headers:<SERIES>-generic` | Previous image; `<SERIES>-dkms` for cold start |
| `MAX_KERNELS` | No | `50` | Max kernel packages to install per build (0 = unlimited) |

---

## Shared: dkms base images

Both families use a shared multi-platform base image per Ubuntu series:

| Image | Purpose | Platforms |
|-------|---------|-----------|
| `ghcr.io/vicamo/linux-headers:<SERIES>-dkms` | Ubuntu base with `dkms` pre-installed | *(auto-detected from `ghcr.io/vicamo/ubuntu:<SERIES>`)* |

Multiple kernel series may share the same dkms image (e.g. 6.17, 6.18, 6.19
all use `questing-dkms`).

#### dkms/Dockerfile.dkms

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `SERIES` | No | `noble` | Ubuntu series codename |

### Image annotations

| Level | Key | Description |
|-------|-----|-------------|
| Per-platform manifest | `dev.mainline-kernel-headers.versions` | JSON object mapping flavour to installed version-abi strings, e.g. `{"generic":["6.8.0-45","6.8.0-46"],"lowlatency":["6.8.0-45"]}` |

---

## Inspecting images

```sh
# Check available platforms
docker buildx imagetools inspect ghcr.io/vicamo/linux-headers:7.0

# View per-platform version annotations
docker buildx imagetools inspect ghcr.io/vicamo/linux-headers:7.0 --raw
```

## Status dashboard

A live status page showing upstream availability and build coverage
across all architectures (4.14–7.0) is published via GitHub Pages:

**https://vicamo.github.io/mainline-kernel-headers/**

The dashboard is updated automatically after each CI build run.

### Local preview

To preview the status page locally, serve the `gh-pages` branch:

```sh
git checkout gh-pages
python3 -m http.server 8080
```

Then open http://localhost:8080 in your browser.

## Repository layout

```
dkms/                        Shared dkms base image
  Dockerfile.dkms
mainline/                    Mainline kernel headers
  Dockerfile                 Headers image
  Dockerfile.archive         Archive image
  debs/                      Downloaded .deb staging
scripts/                     build-archive, build-mainline, build-mainline-all, build-ubuntu, etc.
ubuntu/                      Ubuntu generic kernel headers
  Dockerfile.ubuntu          Headers image
pages/                       GitHub Pages status dashboard
  index.html
  data/                      Pre-generated JSON reports
.github/workflows/
  mainline.yml               CI for mainline images
  ubuntu.yml                 CI for Ubuntu images
```

## License

The kernel header packages are distributed under the terms of the Linux kernel
license (GPL-2.0). The Dockerfiles in this repository are provided as-is.
