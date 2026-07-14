"""Tests for scripts/build-archive."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

_script = Path(__file__).resolve().parents[1] / "scripts" / "build-archive"
_ns: dict = {"__file__": str(_script)}
exec(compile(_script.read_text(), _script, "exec"), _ns)

extract_versions_json = _ns["extract_versions_json"]


class TestExtractVersionsJson:
    """Test extract_versions_json with mocked docker run output."""

    def test_parses_single_version(self):
        ls_output = (
            "/6.14/6.14.0:\n"
            "linux-headers-6.14.0-061400-generic_6.14.0-061400.202504_amd64.deb\n"
            "linux-headers-6.14.0-061400_6.14.0-061400.202504_all.deb\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=ls_output, stderr="")
            result = extract_versions_json("img:tag", "6.14")

        parsed = json.loads(result)
        assert "6.14.0" in parsed
        assert "generic" in parsed["6.14.0"]["amd64"]
        assert "all" in parsed["6.14.0"]["all"]

    def test_parses_multiple_versions(self):
        ls_output = (
            "/6.14/6.14.0:\n"
            "linux-headers-6.14.0-061400-generic_6.14.0-061400.202504_amd64.deb\n"
            "\n"
            "/6.14/6.14.1:\n"
            "linux-headers-6.14.1-061401-generic_6.14.1-061401.202505_amd64.deb\n"
            "linux-headers-6.14.1-061401-generic_6.14.1-061401.202505_arm64.deb\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=ls_output, stderr="")
            result = extract_versions_json("img:tag", "6.14")

        parsed = json.loads(result)
        assert "6.14.0" in parsed
        assert "6.14.1" in parsed
        assert "generic" in parsed["6.14.1"]["amd64"]
        assert "generic" in parsed["6.14.1"]["arm64"]

    def test_multiple_flavours(self):
        ls_output = (
            "/5.15/5.15.0:\n"
            "linux-headers-5.15.0-051500-generic_5.15.0-051500.202110_amd64.deb\n"
            "linux-headers-5.15.0-051500-lowlatency_5.15.0-051500.202110_amd64.deb\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=ls_output, stderr="")
            result = extract_versions_json("img:tag", "5.15")

        parsed = json.loads(result)
        assert sorted(parsed["5.15.0"]["amd64"]) == ["generic", "lowlatency"]

    def test_returns_none_on_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 1, stdout="", stderr="error")
            assert extract_versions_json("img:tag", "6.14") is None

    def test_returns_none_on_empty_output(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout="", stderr="")
            assert extract_versions_json("img:tag", "6.14") is None

    def test_ignores_non_deb_lines(self):
        ls_output = (
            "/6.14/6.14.0:\n"
            "BUILD.LOG\n"
            "CHANGES\n"
            "linux-headers-6.14.0-061400-generic_6.14.0-061400.202504_amd64.deb\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=ls_output, stderr="")
            result = extract_versions_json("img:tag", "6.14")

        parsed = json.loads(result)
        assert parsed == {"6.14.0": {"amd64": ["generic"]}}

    def test_returns_none_when_no_matching_debs(self):
        ls_output = (
            "/6.14/6.14.0:\n"
            "linux-image-6.14.0-061400-generic_6.14.0-061400.202504_amd64.deb\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=ls_output, stderr="")
            assert extract_versions_json("img:tag", "6.14") is None



