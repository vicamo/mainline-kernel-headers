"""Tests for scripts/get-archive-annotation."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

# Import the module by exec since it has no .py extension
_script = Path(__file__).resolve().parents[1] / "scripts" / "get-archive-annotation"
_ns: dict = {}
exec(compile(_script.read_text(), _script, "exec"), _ns)

get_archive_annotation = _ns["get_archive_annotation"]
_from_registry = _ns["_from_registry"]
_from_local = _ns["_from_local"]
_run = _ns["_run"]


def _fake_run(returncode: int = 0, stdout: str = ""):
    def _inner(cmd, **kwargs):
        r = subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")
        return r
    return _inner


class TestFromRegistry:
    """Test _from_registry with mocked subprocess."""

    def test_returns_none_on_empty(self):
        with patch("subprocess.run", _fake_run(0, "")):
            assert _from_registry("img:tag", "some.key") is None

    def test_returns_none_on_failure(self):
        with patch("subprocess.run", _fake_run(1, "")):
            assert _from_registry("img:tag", "some.key") is None

    def test_direct_manifest_annotation(self):
        manifest = json.dumps({
            "annotations": {"some.key": "some-value"}
        })
        with patch("subprocess.run", _fake_run(0, manifest)):
            assert _from_registry("img:tag", "some.key") == "some-value"

    def test_missing_key_raises(self):
        manifest = json.dumps({
            "annotations": {"other.key": "other-value"}
        })
        with patch("subprocess.run", _fake_run(0, manifest)):
            try:
                _from_registry("img:tag", "some.key")
                assert False, "should have raised"
            except RuntimeError:
                pass

    def test_index_dereferences_first_non_attestation(self):
        index = json.dumps({
            "manifests": [
                {
                    "digest": "sha256:aaa",
                    "annotations": {"vnd.docker.reference.type": "attestation-manifest"}
                },
                {
                    "digest": "sha256:bbb",
                    "annotations": {}
                },
            ]
        })
        inner_manifest = json.dumps({
            "annotations": {"my.key": "found-it"}
        })

        calls = []
        def mock_run(cmd, **kwargs):
            calls.append(cmd)
            if "sha256:bbb" in " ".join(cmd):
                return subprocess.CompletedProcess(cmd, 0, stdout=inner_manifest, stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout=index, stderr="")

        with patch("subprocess.run", mock_run):
            assert _from_registry("img:tag", "my.key") == "found-it"


class TestFromLocal:
    """Test _from_local with mocked subprocess."""

    def test_returns_value(self):
        labels = json.dumps({"some.key": "local-value"})
        with patch("subprocess.run", _fake_run(0, labels)):
            assert _from_local("img:tag", "some.key") == "local-value"

    def test_returns_none_on_empty(self):
        with patch("subprocess.run", _fake_run(0, "")):
            assert _from_local("img:tag", "some.key") is None

    def test_returns_none_on_failure(self):
        with patch("subprocess.run", _fake_run(1, "")):
            assert _from_local("img:tag", "some.key") is None

    def test_missing_key_raises(self):
        labels = json.dumps({"other.key": "other-value"})
        with patch("subprocess.run", _fake_run(0, labels)):
            try:
                _from_local("img:tag", "some.key")
                assert False, "should have raised"
            except RuntimeError:
                pass


class TestGetArchiveAnnotation:
    """Test the combined get_archive_annotation function."""

    def test_prefers_registry_over_local(self):
        manifest = json.dumps({"annotations": {"k": "from-registry"}})
        with patch("subprocess.run", _fake_run(0, manifest)):
            assert get_archive_annotation("img:tag", "k") == "from-registry"

    def test_falls_back_to_local(self):
        labels = json.dumps({"k": "local-val"})
        def mock_run(cmd, **kwargs):
            # First call (imagetools inspect) fails
            if "imagetools" in cmd:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
            # Second call (docker inspect) succeeds
            return subprocess.CompletedProcess(cmd, 0, stdout=labels, stderr="")

        with patch("subprocess.run", mock_run):
            assert get_archive_annotation("img:tag", "k") == "local-val"

    def test_returns_none_when_both_fail(self):
        with patch("subprocess.run", _fake_run(1, "")):
            assert get_archive_annotation("img:tag", "k") is None
