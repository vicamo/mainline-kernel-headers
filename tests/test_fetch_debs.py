"""Tests for scripts/fetch-debs."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

_script = Path(__file__).resolve().parents[1] / "scripts" / "fetch-debs"
_ns: dict = {"__file__": str(_script)}
exec(compile(_script.read_text(), _script, "exec"), _ns)

fetch = _ns["fetch"]
download = _ns["download"]
validate_debs = _ns["validate_debs"]
flavour_from_deb = _ns["flavour_from_deb"]
discover_version = _ns["discover_version"]


class TestFlavourFromDeb:
    """Test flavour_from_deb filename parsing."""

    def test_generic_amd64(self):
        assert flavour_from_deb(
            "linux-headers-6.14.3-061403-generic_6.14.3-061403.202504230834_amd64.deb"
        ) == ("generic", "amd64")

    def test_generic_arm64(self):
        assert flavour_from_deb(
            "linux-headers-6.14.3-061403-generic_6.14.3-061403.202504230834_arm64.deb"
        ) == ("generic", "arm64")

    def test_all_arch(self):
        assert flavour_from_deb(
            "linux-headers-6.14.3-061403_6.14.3-061403.202504230834_all.deb"
        ) == ("all", "all")

    def test_derived_headers(self):
        assert flavour_from_deb(
            "linux-oem-headers-5.14.0-1001-generic_5.14.0-1001.1_amd64.deb"
        ) == ("generic", "amd64")

    def test_non_header_returns_none(self):
        assert flavour_from_deb("linux-image-6.14.3-061403-generic_amd64.deb") is None

    def test_random_string_returns_none(self):
        assert flavour_from_deb("not-a-deb.txt") is None

    def test_lowlatency_flavour(self):
        assert flavour_from_deb(
            "linux-headers-5.15.0-051500-lowlatency_5.15.0-051500.202110312130_amd64.deb"
        ) == ("lowlatency", "amd64")


class TestFetch:
    """Test fetch() with mocked urlopen."""

    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"hello"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            # Need to patch in the script's namespace
            with patch.dict(_ns, {"urlopen": lambda *a, **k: mock_resp}):
                # Direct call using original urlopen mock
                pass

        # Simpler: patch at module level via the _ns dict
        original_urlopen = _ns.get("urlopen")
        _ns["urlopen"] = lambda *a, **k: mock_resp
        try:
            result = fetch("http://example.com")
            assert result == "hello"
        finally:
            _ns["urlopen"] = original_urlopen

    def test_returns_none_on_failure(self):
        def raise_error(*a, **k):
            raise Exception("network error")

        original_urlopen = _ns.get("urlopen")
        _ns["urlopen"] = raise_error
        try:
            result = fetch("http://example.com", retries=1)
            assert result is None
        finally:
            _ns["urlopen"] = original_urlopen


class TestDownload:
    """Test download() with mocked urlopen."""

    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"deb-content"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        original_urlopen = _ns.get("urlopen")
        _ns["urlopen"] = lambda *a, **k: mock_resp
        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                dest = f.name
            assert download("http://example.com/file.deb", dest) is True
            assert Path(dest).read_bytes() == b"deb-content"
        finally:
            _ns["urlopen"] = original_urlopen
            os.unlink(dest)

    def test_returns_false_on_failure(self):
        def raise_error(*a, **k):
            raise Exception("network error")

        original_urlopen = _ns.get("urlopen")
        _ns["urlopen"] = raise_error
        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                dest = f.name
            result = download("http://example.com/file.deb", dest, retries=1)
            assert result is False
        finally:
            _ns["urlopen"] = original_urlopen
            os.unlink(dest)


class TestDiscoverVersion:
    """Test discover_version with mocked network."""

    def test_no_new_debs_no_local(self):
        """Empty version page with no debs → not changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = os.path.join(tmpdir, "6.14")
            original_fetch = _ns["fetch"]
            _ns["fetch"] = lambda url, **k: '<html><a href="amd64/">amd64/</a></html>'

            # arch page has no header debs
            call_count = [0]
            def mock_fetch(url, **k):
                call_count[0] += 1
                if call_count[0] == 1:
                    return '<html><a href="amd64/">amd64/</a></html>'
                return "<html></html>"

            _ns["fetch"] = mock_fetch
            try:
                vnum, changed, error = discover_version(
                    "http://example.com", "v6.14", "6.14", out_dir, {})
                assert vnum == "6.14"
                assert changed is False
                assert error is None
            finally:
                _ns["fetch"] = original_fetch

    def test_skips_archived_flavours(self):
        """Debs already in archive are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = os.path.join(tmpdir, "6.14")
            page = (
                '<html>'
                '<a href="linux-headers-6.14.0-061400-generic_6.14.0-061400.202504_amd64.deb">'
                'linux-headers-6.14.0-061400-generic_6.14.0-061400.202504_amd64.deb</a>'
                '</html>'
            )

            call_count = [0]
            def mock_fetch(url, **k):
                call_count[0] += 1
                if call_count[0] == 1:
                    return '<html><a href="amd64/">amd64/</a></html>'
                return page

            original_fetch = _ns["fetch"]
            _ns["fetch"] = mock_fetch
            try:
                vnum, changed, error = discover_version(
                    "http://example.com", "v6.14", "6.14", out_dir,
                    {"amd64": ["generic"]})  # already archived
                assert changed is False
            finally:
                _ns["fetch"] = original_fetch

    def test_downloads_new_debs(self):
        """New debs are downloaded and version is marked changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = os.path.join(tmpdir, "6.14")
            deb_name = "linux-headers-6.14.0-061400-generic_6.14.0-061400.202504_amd64.deb"
            page = f'<html><a href="{deb_name}">{deb_name}</a></html>'

            call_count = [0]
            def mock_fetch(url, **k):
                call_count[0] += 1
                if call_count[0] == 1:
                    return '<html><a href="amd64/">amd64/</a></html>'
                return page

            original_fetch = _ns["fetch"]
            original_download = _ns["download"]
            _ns["fetch"] = mock_fetch
            _ns["download"] = lambda url, dest, **k: (
                Path(dest).write_bytes(b"fake") or True)
            try:
                vnum, changed, error = discover_version(
                    "http://example.com", "v6.14", "6.14", out_dir, {})
                assert changed is True
                assert error is None
                assert (Path(out_dir) / deb_name).exists()
            finally:
                _ns["fetch"] = original_fetch
                _ns["download"] = original_download

    def test_local_debs_count_as_changed(self):
        """Pre-existing local debs mark the version as changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = os.path.join(tmpdir, "6.14")
            os.makedirs(out_dir)
            (Path(out_dir) / "some-headers.deb").write_bytes(b"fake")

            # Page with no new debs to download
            original_fetch = _ns["fetch"]
            _ns["fetch"] = lambda url, **k: "<html></html>"
            try:
                vnum, changed, error = discover_version(
                    "http://example.com", "v6.14", "6.14", out_dir, {})
                assert changed is True
            finally:
                _ns["fetch"] = original_fetch

    def test_fetch_failure_returns_error(self):
        """Network failure returns error string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = os.path.join(tmpdir, "6.14")
            original_fetch = _ns["fetch"]
            _ns["fetch"] = lambda url, **k: None
            try:
                vnum, changed, error = discover_version(
                    "http://example.com", "v6.14", "6.14", out_dir, {})
                assert changed is False
                assert error is not None
                assert "cannot fetch" in error
            finally:
                _ns["fetch"] = original_fetch
