"""Tests for scripts/lib/__init__.py."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lib import check_containerd_snapshotter


class TestCheckContainerdSnapshotter:
    """Test check_containerd_snapshotter."""

    def test_passes_when_containerd_enabled(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout="[[io.containerd.snapshotter.v1]]", stderr="")
            check_containerd_snapshotter()

    def test_exits_when_not_enabled(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout="[[overlay2]]", stderr="")
            with pytest.raises(SystemExit):
                check_containerd_snapshotter()

    def test_exits_on_docker_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 1, stdout="", stderr="")
            with pytest.raises(SystemExit):
                check_containerd_snapshotter()
