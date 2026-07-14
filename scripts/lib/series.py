"""Ubuntu series ↔ kernel version mapping.

Canonical source of truth for the releases table. All scripts that need
series lookups import from here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Release:
    kver_num: int   # major*100 + minor
    codename: str
    lts: bool


# Ascending order: oldest first.
RELEASE_KERNELS: tuple[Release, ...] = (
    Release(300, "oneiric", False),
    Release(302, "precise", True),
    Release(305, "quantal", False),
    Release(308, "raring", False),
    Release(311, "saucy", False),
    Release(313, "trusty", True),
    Release(316, "utopic", False),
    Release(319, "vivid", False),
    Release(402, "wily", False),
    Release(404, "xenial", True),
    Release(408, "yakkety", False),
    Release(410, "zesty", False),
    Release(413, "artful", False),
    Release(415, "bionic", True),
    Release(418, "cosmic", False),
    Release(500, "disco", False),
    Release(503, "eoan", False),
    Release(504, "focal", True),
    Release(508, "groovy", False),
    Release(511, "hirsute", False),
    Release(513, "impish", False),
    Release(515, "jammy", True),
    Release(519, "kinetic", False),
    Release(602, "lunar", False),
    Release(605, "mantic", False),
    Release(608, "noble", True),
    Release(611, "oracular", False),
    Release(614, "plucky", False),
    Release(617, "questing", False),
    Release(700, "resolute", True),
    Release(9999, "devel", False),
)


def series_for_kver(kver: str, *, longterm: bool = False) -> str:
    """Return the Ubuntu series codename for a kernel version.

    With longterm=False (default): picks the first release whose kernel >= kver.
    With longterm=True: picks the first LTS release whose kernel >= kver.
    """
    parts = kver.split(".")
    ver_num = int(parts[0]) * 100 + int(parts[1])
    for r in RELEASE_KERNELS:
        if ver_num <= r.kver_num:
            if longterm and not r.lts:
                continue
            return r.codename
    return RELEASE_KERNELS[-1].codename
