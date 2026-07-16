"""Tests for scripts/lib/series.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lib.series import RELEASE_KERNELS, Release, series_for_kver, series_range


class TestReleaseKernels:
    """Validate completeness and correctness of the RELEASE_KERNELS table."""

    def test_is_tuple_of_releases(self):
        assert isinstance(RELEASE_KERNELS, tuple)
        assert all(isinstance(r, Release) for r in RELEASE_KERNELS)

    def test_ascending_kver_order(self):
        nums = [r.kver_num for r in RELEASE_KERNELS]
        assert nums == sorted(nums), "RELEASE_KERNELS must be ascending by kver_num"

    def test_no_duplicate_codenames(self):
        codenames = [r.codename for r in RELEASE_KERNELS]
        assert len(codenames) == len(set(codenames)), "duplicate codenames found"

    def test_no_duplicate_kver_nums(self):
        nums = [r.kver_num for r in RELEASE_KERNELS]
        assert len(nums) == len(set(nums)), "duplicate kver_nums found"

    def test_ends_with_devel_sentinel(self):
        last = RELEASE_KERNELS[-1]
        assert last.codename == "devel"
        assert last.kver_num == 9999

    def test_known_lts_releases(self):
        """All releases marked lts=True must actually be LTS per ubuntu-distro-info."""
        import shutil
        import subprocess

        if not shutil.which("ubuntu-distro-info"):
            import pytest
            pytest.skip("ubuntu-distro-info not installed")

        result = subprocess.run(
            ["ubuntu-distro-info", "--all", "-f"],
            capture_output=True, text=True, check=True,
        )
        import re
        lts_codenames = set()
        for line in result.stdout.splitlines():
            if "LTS" in line:
                m = re.search(r'"(\w+)', line)
                if m:
                    lts_codenames.add(m.group(1).lower())

        for r in RELEASE_KERNELS:
            if r.codename == "devel":
                continue
            if r.lts:
                assert r.codename in lts_codenames, \
                    f"{r.codename} marked lts=True but not LTS per ubuntu-distro-info"
            else:
                assert r.codename not in lts_codenames, \
                    f"{r.codename} is LTS per ubuntu-distro-info but marked lts=False"

    def test_known_kver_mappings(self):
        """Spot-check well-known kernel version → codename pairs."""
        by_codename = {r.codename: r.kver_num for r in RELEASE_KERNELS}
        assert by_codename["precise"] == 302
        assert by_codename["trusty"] == 313
        assert by_codename["xenial"] == 404
        assert by_codename["bionic"] == 415
        assert by_codename["focal"] == 504
        assert by_codename["jammy"] == 515
        assert by_codename["noble"] == 608
        assert by_codename["oracular"] == 611
        assert by_codename["plucky"] == 614

    def test_latest_release_kver_matches_archive(self):
        """Verify the last real entry's kver_num matches the archive kernel version."""
        import shutil
        import subprocess

        if not shutil.which("rmadison"):
            import pytest
            pytest.skip("rmadison not installed")

        last = RELEASE_KERNELS[-2]  # last before devel sentinel
        result = subprocess.run(
            ["rmadison", "-u", "ubuntu", "-s", last.codename, "linux-image-generic"],
            capture_output=True, text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            import pytest
            pytest.skip(f"rmadison returned no data for {last.codename}")

        import re
        # Parse version like "7.0.0-14.14" → major.minor = 7.0
        m = re.search(r"\|\s*(\d+)\.(\d+)\.", result.stdout)
        assert m, f"could not parse kernel version from rmadison output"
        expected_kver_num = int(m.group(1)) * 100 + int(m.group(2))
        assert last.kver_num == expected_kver_num, \
            f"{last.codename}: expected kver_num {expected_kver_num}, got {last.kver_num}"

    def test_validates_against_distro_info(self):
        """If ubuntu-distro-info is available, verify all non-devel codenames exist."""
        import shutil
        import subprocess

        if not shutil.which("ubuntu-distro-info"):
            import pytest
            pytest.skip("ubuntu-distro-info not installed")

        result = subprocess.run(
            ["ubuntu-distro-info", "--all", "-c"],
            capture_output=True, text=True, check=True,
        )
        known = {line.strip().lower() for line in result.stdout.splitlines()}
        for r in RELEASE_KERNELS:
            if r.codename == "devel":
                continue
            assert r.codename in known, f"{r.codename} not in ubuntu-distro-info"


class TestSeriesForKver:
    """Test series_for_kver lookups."""

    def test_exact_match_boundary(self):
        # 5.4 → kver_num 504 == focal's 504
        assert series_for_kver("5.4") == "focal"

    def test_below_first_entry(self):
        # 2.6 → kver_num 206 < 300 (oneiric), should still return oneiric
        assert series_for_kver("2.6") == "oneiric"

    def test_between_releases(self):
        # 5.6 → kver_num 506, between focal(504) and groovy(508)
        assert series_for_kver("5.6") == "groovy"

    def test_above_all_real(self):
        # 99.0 → hits devel sentinel
        assert series_for_kver("99.0") == "devel"

    def test_three_part_version(self):
        # Only major.minor matters
        assert series_for_kver("6.1.177") == "lunar"
        assert series_for_kver("5.15.42") == "jammy"

    def test_known_series(self):
        assert series_for_kver("3.2") == "precise"
        assert series_for_kver("4.4") == "xenial"
        assert series_for_kver("4.15") == "bionic"
        assert series_for_kver("5.15") == "jammy"
        assert series_for_kver("6.8") == "noble"
        assert series_for_kver("6.14") == "plucky"

    def test_longterm_skips_non_lts(self):
        # 5.10 → kver_num 510, first LTS >= 510 is jammy(515)
        assert series_for_kver("5.10", longterm=True) == "jammy"
        # 6.1 → kver_num 601, first LTS >= 601 is noble(608)
        assert series_for_kver("6.1", longterm=True) == "noble"
        # 6.12 → kver_num 612, first LTS >= 612 is resolute(700)
        assert series_for_kver("6.12", longterm=True) == "resolute"

    def test_longterm_on_lts_boundary(self):
        # 5.4 exactly matches focal(504) which is LTS
        assert series_for_kver("5.4", longterm=True) == "focal"
        # 5.15 exactly matches jammy(515) which is LTS
        assert series_for_kver("5.15", longterm=True) == "jammy"

    def test_longterm_fallback_to_last(self):
        # devel is not LTS; last LTS is resolute(700)
        # 7.0 → kver_num 700 == resolute, which is LTS
        assert series_for_kver("7.0", longterm=True) == "resolute"


class TestSeriesRange:
    """Test series_range utility."""

    def test_basic_range(self):
        assert series_range("groovy", "jammy") == ["groovy", "hirsute", "impish"]

    def test_single_gap(self):
        assert series_range("lunar", "noble") == ["lunar", "mantic"]

    def test_same_codename(self):
        assert series_range("noble", "noble") == []

    def test_from_after_to(self):
        assert series_range("noble", "lunar") == []

    def test_unknown_codename(self):
        assert series_range("nonexistent", "noble") == []
        assert series_range("noble", "nonexistent") == []

    def test_wider_range(self):
        r = series_range("oracular", "resolute")
        assert r == ["oracular", "plucky", "questing"]


class TestLongtermSeriesJson:
    """Ensure longterm-series.json covers all active longterm kernels."""

    def test_all_active_longterm_covered(self):
        """Every active longterm kernel from kernel.org must be in longterm-series.json."""
        import json
        import urllib.request

        longterm_json = Path(__file__).resolve().parents[1] / "mainline" / "longterm-series.json"
        with open(longterm_json) as f:
            longterm_map = json.load(f)

        try:
            with urllib.request.urlopen(
                "https://www.kernel.org/releases.json", timeout=10
            ) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, OSError):
            import pytest
            pytest.skip("cannot reach kernel.org")

        import re
        missing = []
        for r in data["releases"]:
            if r["moniker"] != "longterm" or r["iseol"]:
                continue
            m = re.match(r"^(\d+\.\d+)", r["version"])
            if m and m.group(1) not in longterm_map:
                missing.append(m.group(1))

        assert not missing, \
            f"Active longterm kernels missing from longterm-series.json: {missing}"
