import subprocess
import sys

MAINLINE_BASE_URL = "https://kernel.ubuntu.com/mainline"
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
