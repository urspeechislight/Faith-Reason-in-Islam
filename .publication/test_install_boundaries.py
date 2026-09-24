"""Independent unpublished installation and synchronization boundary regressions."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("boundary_installer", ROOT / "install_toolchain.py")
I = importlib.util.module_from_spec(spec)
spec.loader.exec_module(I)


class InstallationBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "agents"
        self.target.mkdir()

    def install(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            return I.main(["--target", str(self.target), *map(str, extra)])

    def fixture(self):
        sources = self.root / "sources"
        sources.mkdir()
        files = {}
        for name in ("first.py", "second.py"):
            src = sources / name
            src.write_text("new " + name)
            dest = self.target / "prose" / name
            dest.parent.mkdir(exist_ok=True)
            dest.write_text("old " + name)
            files["prose/" + name] = src
        return files

    def test_clean_install_contains_mandatory_instruction_dependencies(self):
        self.assertEqual(self.install(), 0)
        self.assertEqual(self.install("--check"), 0)
        required = [
            "skills/islamic-note/references/markdown.md",
            "skills/faith-reason-note/references/website.md",
            "skills/faith-reason-research/SKILL.md",
        ]
        missing = [name for name in required if not (self.target / name).is_file()]
        self.assertEqual(missing, [], "Successful clean installation must include mandatory instructions")

    def test_late_directory_conflict_leaves_earlier_file_unchanged(self):
        files = self.fixture()
        second = self.target / "prose/second.py"
        second.unlink()
        second.mkdir()
        with patch.object(I, "inventory", return_value=files), patch.object(I, "ALIASES", {}):
            self.assertNotEqual(self.install(), 0)
        self.assertEqual((self.target / "prose/first.py").read_text(), "old first.py")
        self.assertTrue(second.is_dir())

    def test_second_replacement_failure_rolls_back_first_replacement(self):
        files = self.fixture()
        replace = Path.replace
        failure = []
        def fail_later(path, target):
            if Path(target) == self.target / "prose/second.py" and not failure:
                failure.append(True)
                raise PermissionError("synthetic destination permission failure")
            return replace(path, target)
        with patch.object(I, "inventory", return_value=files), patch.object(I, "ALIASES", {}), patch.object(Path, "replace", fail_later):
            self.assertNotEqual(self.install(), 0)
        self.assertTrue(failure, "Failure injection must reach the real replacement path")
        for name in ("first.py", "second.py"):
            self.assertEqual((self.target / "prose" / name).read_text(), "old " + name)

    def test_expected_snapshot_rejects_drift_before_any_replacement(self):
        files = self.fixture()
        expected = self.root / "expected.json"
        expected.write_text(json.dumps({name: I.digest(self.target / name) for name in files}))
        (self.target / "prose/second.py").write_text("concurrent edit")
        with patch.object(I, "inventory", return_value=files), patch.object(I, "ALIASES", {}):
            self.assertNotEqual(self.install("--expected", expected), 0)
        self.assertEqual((self.target / "prose/first.py").read_text(), "old first.py")
        self.assertEqual((self.target / "prose/second.py").read_text(), "concurrent edit")

    def test_expected_snapshot_rechecked_during_install_preserves_concurrent_edit(self):
        files = self.fixture()
        expected = self.root / "expected.json"
        expected.write_text(json.dumps({name: I.digest(self.target / name) for name in files}))
        replace = Path.replace
        injected = []
        def edit_later(path, target):
            result = replace(path, target)
            if Path(target) == self.target / "prose/first.py" and not injected:
                injected.append(True)
                (self.target / "prose/second.py").write_text("concurrent edit")
            return result
        with patch.object(I, "inventory", return_value=files), patch.object(I, "ALIASES", {}), patch.object(Path, "replace", edit_later):
            self.assertNotEqual(self.install("--expected", expected), 0)
        self.assertTrue(injected)
        self.assertEqual((self.target / "prose/first.py").read_text(), "old first.py")
        self.assertEqual((self.target / "prose/second.py").read_text(), "concurrent edit")

    def test_existing_parent_symlink_cannot_redirect_install_outside_target(self):
        files = self.fixture()
        outside = self.root / "outside"
        shutil.move(str(self.target / "prose"), str(outside))
        (self.target / "prose").symlink_to(outside, target_is_directory=True)
        with patch.object(I, "inventory", return_value=files), patch.object(I, "ALIASES", {}):
            self.assertNotEqual(self.install(), 0)
        self.assertEqual((outside / "first.py").read_text(), "old first.py")
        self.assertEqual((outside / "second.py").read_text(), "old second.py")

    def test_interrupted_install_is_detected_and_recovered_before_use(self):
        files=self.fixture();directory=self.target/'.toolchain-backups'/'interrupted';directory.mkdir(parents=True)
        entries={}
        for name,source in files.items():
            dest=self.target/name;backup=directory/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(dest.read_bytes())
            entries[name]={'kind':'file','before':I.digest(dest),'after':I.digest(source),'backup':str(backup)}
        (self.target/'prose/first.py').write_bytes(files['prose/first.py'].read_bytes())
        active=self.target/'.toolchain-install-active.json';active.write_text(json.dumps({'schema':1,'directory':str(directory),'entries':entries}))
        with patch.object(I,'inventory',return_value=files),patch.object(I,'ALIASES',{}):
            self.assertNotEqual(self.install('--check'),0)
            self.assertEqual(self.install(),0)
            self.assertEqual(self.install('--check'),0)
        self.assertFalse(active.exists());self.assertTrue((directory/'recovery.json').exists())

    def test_sync_does_not_overwrite_divergent_packaged_edits(self):
        package = self.root / "package"
        shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns("__pycache__"))
        with patch.object(I, "ROOT", package):
            self.assertEqual(self.install(), 0)
        edited = package / "runtime/scripture_alignment.py"
        edited.write_text(edited.read_text() + "\n# unpublished synthetic packaged edit\n")
        before = edited.read_bytes()
        result = subprocess.run([sys.executable, str(package / "sync_runtime.py"), "--agents-root", str(self.target)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(edited.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
