"""Tests for filesystem snapshot system."""
import asyncio
import os
import tempfile
import pytest
from backend.sandbox.manager import SnapshotManager


class TestSnapshotManager:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manager = SnapshotManager()
        self.manager.SNAPSHOT_DIR = os.path.join(self.tmpdir, "snapshots")
        os.makedirs(self.manager.SNAPSHOT_DIR, exist_ok=True)
        self.workspace = os.path.join(self.tmpdir, "workspace")
        os.makedirs(self.workspace, exist_ok=True)
        with open(os.path.join(self.workspace, "test.py"), "w") as f:
            f.write("x = 1\n")
        with open(os.path.join(self.workspace, "config.json"), "w") as f:
            f.write('{"key": "value"}\n')

    @pytest.mark.asyncio
    async def test_create_snapshot(self):
        snap = await self.manager.create_snapshot("sess1", self.workspace, "before edit")
        assert snap is not None
        assert snap.files_captured == 2
        assert snap.session_id == "sess1"

    @pytest.mark.asyncio
    async def test_rollback_restores_files(self):
        snap = await self.manager.create_snapshot("sess1", self.workspace)
        with open(os.path.join(self.workspace, "test.py"), "w") as f:
            f.write("x = 999\n")
        await self.manager.rollback("sess1", snap.snapshot_id, self.workspace)
        with open(os.path.join(self.workspace, "test.py")) as f:
            assert f.read() == "x = 1\n"

    @pytest.mark.asyncio
    async def test_list_snapshots(self):
        await self.manager.create_snapshot("sess1", self.workspace)
        await self.manager.create_snapshot("sess1", self.workspace)
        snaps = self.manager.list_snapshots("sess1")
        assert len(snaps) == 2

    def test_cleanup_session(self):
        # We need to actually have snapshots to clean up
        # Manual population for speed in sync test
        from backend.sandbox.manager import Snapshot
        self.manager._snapshots["sess1"] = [Snapshot("snap1", "sess1", 1.0)]
        self.manager.cleanup_session("sess1")
        assert len(self.manager.list_snapshots("sess1")) == 0
