import json
import re
import subprocess
import sys
import urllib.request

MAINLINE_BASE_URL = "https://kernel.ubuntu.com/mainline"
KERNEL_ORG_RELEASES_URL = "https://www.kernel.org/releases.json"
IMAGE_PREFIX = "ghcr.io/vicamo/linux-headers"

# OCI manifest annotation keys.
# ARCHIVE_ANNOTATION_VERSIONS_KEY: used on archive images.
#   JSON object mapping version → arch → flavours.
#   Example: {"6.14.0":{"all":["all"],"amd64":["generic"],"arm64":["generic"]}}
ARCHIVE_ANNOTATION_VERSIONS_KEY = "dev.mainline-kernel-headers.versions"
# MAINLINE_ANNOTATION_CREATED_KEY: used on mainline images.
#   ISO 8601 UTC timestamp of last archive build.
#   Example: "2025-07-15T01:10:43Z"
MAINLINE_ANNOTATION_CREATED_KEY = "dev.mainline-kernel-headers.archive-created"


def fetch_active_kernel_versions() -> list[str]:
    """Fetch active (non-EOL stable/longterm) kernel series from kernel.org."""
    with urllib.request.urlopen(KERNEL_ORG_RELEASES_URL) as resp:
        data = json.loads(resp.read())

    seen: set[str] = set()
    versions: list[str] = []
    for r in data["releases"]:
        if r["moniker"] not in ("stable", "longterm"):
            continue
        if r["iseol"]:
            continue
        m = re.match(r"^(\d+\.\d+)", r["version"])
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            versions.append(m.group(1))
    return versions


def get_index_annotation(image: str, key: str) -> str | None:
    """Read an annotation from the top-level image index (manifest list)."""
    r = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", image, "--raw"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None
    data = json.loads(r.stdout)
    return (data.get("annotations") or {}).get(key) or None


def enumerate_installed_headers_packages(
    image: str, platform: str, *, skip_arch_all: bool = True,
) -> list[str] | None:
    """List installed linux-headers-* package names from a platform image.

    Returns package names starting with linux-headers-, or None on failure.
    When skip_arch_all is True (default), packages with Architecture: all
    are excluded.
    """
    r = subprocess.run(
        ["docker", "run", "--rm", "--platform", platform, image,
         "cat", "/var/lib/dpkg/status"],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not r.stdout:
        return None

    packages: list[str] = []
    for block in r.stdout.split("\n\n"):
        if "Package: linux-headers-" not in block:
            continue
        pkg = arch = ""
        for line in block.splitlines():
            if line.startswith("Package: "):
                pkg = line[9:]
            elif line.startswith("Architecture: "):
                arch = line[14:]
        if not pkg.startswith("linux-headers-"):
            continue
        if skip_arch_all and arch == "all":
            continue
        packages.append(pkg)

    return packages or None


def inspect_platform_annotation(image: str, platform: str, key: str,
                                pushed: bool) -> str | None:
    """Read a per-platform annotation from an image."""
    if pushed:
        r = subprocess.run(
            ["docker", "buildx", "imagetools", "inspect", image, "--raw"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        for m in data.get("manifests", []):
            p = m.get("platform", {})
            plat_str = f"{p.get('os', '')}/{p.get('architecture', '')}"
            if p.get("variant"):
                plat_str += f"/{p['variant']}"
            if plat_str == platform:
                return (m.get("annotations") or {}).get(key) or None
    else:
        r = subprocess.run(
            ["docker", "image", "inspect", "--platform", platform, image,
             "--format", "{{index .Descriptor.Annotations \"" + key + "\"}}"],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip() or None
    return None


def detect_platforms(image: str) -> list[str]:
    """Auto-detect available platforms from a multi-platform image."""
    r = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", image, "--raw"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return []

    data = json.loads(r.stdout)
    platforms = []
    for m in data.get("manifests", []):
        ann = m.get("annotations") or {}
        if "attestation" in ann.get("vnd.docker.reference.type", ""):
            continue
        p = m.get("platform", {})
        if p.get("os") == "unknown":
            continue
        plat = f"{p.get('os', '')}/{p.get('architecture', '')}"
        if p.get("variant"):
            plat += f"/{p['variant']}"
        platforms.append(plat)
    return platforms


def check_containerd_snapshotter() -> None:
    """Verify containerd-snapshotter is enabled in Docker daemon."""
    r = subprocess.run(
        ["docker", "info", "-f", "{{.DriverStatus}}"],
        capture_output=True, text=True,
    )
    if "io.containerd" not in (r.stdout or ""):
        print("ERROR: containerd-snapshotter is not enabled in Docker daemon.",
              file=sys.stderr)
        print('Enable it with: {"features":{"containerd-snapshotter":true}} in daemon.json',
              file=sys.stderr)
        sys.exit(1)
