from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import ggo_no_hidden_installer as installer


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work = Path(tempfile.mkdtemp(prefix="ggo_no_hidden_installer_tests_", dir=Path(__file__).parent))
        installer.DATA_ROOT = self.work / "installer_data"
        installer.LOG_PATH = None
        installer.initialize_log()
        self.payload = self.work / "payload"
        self.archive = self.work / "DragonSword_GGO_No_Hidden_Heroes_20990101.zip"
        self._make_payload()
        self._zip_payload(self.archive)
        self.metadata = self.work / "release.json"
        self._metadata(self.metadata)

    def tearDown(self) -> None:
        shutil.rmtree(self.work, ignore_errors=True)

    def _write(self, relative: str, data: bytes) -> None:
        path = self.payload / Path(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _make_payload(self) -> None:
        self._write("INSTALL.cmd", b"@echo off\r\n")
        self._write("README_INSTALL.txt", b"fixture readme\r\n")
        self._write("UNINSTALL_CONTROL_PANEL.cmd", b"@echo off\r\n")
        self._write("VARIANT_MANIFEST.txt", b"no hidden hero acquisition\r\n")
        self._write("DS/Binaries/Win64/dwmapi.dll", b"proxy")
        self._write("DS/Binaries/Win64/ue4ss/UE4SS.dll", b"fixture ue4ss")
        self._write("DS/Binaries/Win64/ue4ss/UE4SS-settings.ini", b"ModsFolderPath = old\r\nControllingModsTxt = old\r\n")
        self._write("DS/Binaries/Win64/ue4ss/QualificationMods/mods.txt", b"NativeGachaGeneralController : 1\r\n")
        self._write("DS/Binaries/Win64/ue4ss/QualificationMods/NativeGachaGeneralController/README.md", b"fixture module")
        self._write("_modding/DragonSwordControlPlane/DragonSwordControlPlane.exe", b"fixture panel")
        self._write("DS/Content/Paks/mods/DS_GGO_RESTORATION_P.pak", os.urandom(1280 * 1024))
        (self.payload / "DS/Binaries/Win64/ue4ss/QualificationMods/DSLocalMailService/Backend").mkdir(parents=True)
        (self.payload / "DS/Binaries/Win64/ue4ss/QualificationMods/DSLocalSeasonPassPreview/Runtime").mkdir(parents=True)

    def _zip_payload(self, target: Path) -> None:
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as package:
            for path in sorted(self.payload.rglob("*")):
                relative = path.relative_to(self.payload).as_posix()
                if path.is_dir():
                    package.writestr(relative + "/", b"")
                else:
                    package.write(path, relative)
        self.assertGreater(target.stat().st_size, 1024 * 1024)

    def _metadata(self, target: Path, hash_override: str | None = None) -> None:
        value = {
            "tag_name": "fixture-1.0.0", "draft": False, "prerelease": False,
            "assets": [{
                "name": self.archive.name,
                "size": self.archive.stat().st_size,
                "digest": "sha256:" + (hash_override or digest(self.archive)),
                "browser_download_url": f"https://github.com/{installer.REPOSITORY}/releases/download/fixture-1.0.0/{self.archive.name}",
            }],
        }
        target.write_text(json.dumps(value), encoding="utf-8")

    def _game(self, name: str) -> Path:
        root = self.work / name
        (root / "DS" / "Binaries" / "Win64").mkdir(parents=True)
        (root / "DS" / "Content" / "Paks").mkdir(parents=True)
        (root / "DSClient.exe").write_bytes(b"launcher")
        (root / "DS" / "Binaries" / "Win64" / "DSClient-Win64-Shipping.exe").write_bytes(b"shipping")
        return root

    def test_release_selection(self) -> None:
        release = installer.resolve_release(self.metadata)
        self.assertEqual(release.tag, "fixture-1.0.0")
        self.assertEqual(release.main.sha256, digest(self.archive).upper())
        self.assertIsNone(release.guard)

    def test_happy_path_installs_and_configures(self) -> None:
        game = self._game("game_happy")
        events = []
        result, _ = installer.install_main(
            game, installer.Reporter(lambda *event: events.append(event)),
            skip_system=True, metadata_path=self.metadata, asset_file=self.archive,
        )
        self.assertEqual(result.files_verified, 11)
        self.assertGreater(len(events), 12)
        installed = game / "DS" / "Content" / "Paks" / "mods" / "DS_GGO_RESTORATION_P.pak"
        self.assertEqual(digest(installed), digest(self.payload / installed.relative_to(game)))
        config_path = game / "_modding" / "DragonSwordControlPlane" / "config.json"
        self.assertFalse(config_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(json.loads(config_path.read_text(encoding="utf-8"))["game_root"], str(installer.norm(game)))
        receipt = json.loads(installer.receipt_path(game).read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "installed")
        self.assertEqual(len(receipt["files"]), 11)
        self.assertTrue((game / "DS/Binaries/Win64/ue4ss/QualificationMods/DSLocalMailService/Backend").is_dir())
        self.assertTrue((game / "DS/Binaries/Win64/ue4ss/QualificationMods/DSLocalSeasonPassPreview/Runtime").is_dir())

    def test_uninstall_moves_owned_files_and_restores_preexisting_file(self) -> None:
        game = self._game("game_uninstall")
        saved = game / "DS" / "Saved" / "SaveGames" / "account.sav"
        saved.parent.mkdir(parents=True)
        saved.write_bytes(b"save must remain untouched")
        old = game / "DS" / "Binaries" / "Win64" / "ue4ss" / "UE4SS.dll"
        old.parent.mkdir(parents=True)
        old.write_bytes(b"preexisting ue4ss")
        installer.install_main(
            game, installer.Reporter(), skip_system=True,
            metadata_path=self.metadata, asset_file=self.archive,
        )
        runtime = game / "DS" / "Binaries" / "Win64" / "ue4ss" / "QualificationMods" / "NativeGachaGeneralController" / "Runtime" / "state.bin"
        runtime.parent.mkdir(parents=True)
        runtime.write_bytes(b"runtime state")

        result = installer.uninstall_main(game)

        deleted = Path(result.deleted_root)
        self.assertEqual(old.read_bytes(), b"preexisting ue4ss")
        self.assertEqual(saved.read_bytes(), b"save must remain untouched")
        self.assertFalse((game / "DS" / "Content" / "Paks" / "mods" / "DS_GGO_RESTORATION_P.pak").exists())
        self.assertFalse((game / "DS/Binaries/Win64/ue4ss/QualificationMods/DSLocalMailService/Backend").exists())
        self.assertFalse((game / "DS/Binaries/Win64/ue4ss/QualificationMods/DSLocalSeasonPassPreview/Runtime").exists())
        self.assertTrue((game / "DS" / "Content" / "Paks").is_dir())
        self.assertFalse((game / "_modding").exists())
        self.assertTrue((deleted / "DS" / "Content" / "Paks" / "mods" / "DS_GGO_RESTORATION_P.pak").is_file())
        self.assertTrue((deleted / runtime.relative_to(game)).is_file())
        receipt = json.loads(installer.receipt_path(game).read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "uninstalled")
        self.assertGreaterEqual(result.files_moved, 10)
        self.assertEqual(result.files_restored, 1)

    def test_uninstall_preserves_preexisting_empty_directory(self) -> None:
        game = self._game("game_uninstall_existing_directory")
        preexisting = game / "_modding"
        preexisting.mkdir()
        installer.install_main(
            game, installer.Reporter(), skip_system=True,
            metadata_path=self.metadata, asset_file=self.archive,
        )

        installer.uninstall_main(game)

        self.assertTrue(preexisting.is_dir())
        self.assertEqual(list(preexisting.iterdir()), [])

    def test_uninstall_finishes_root_writes_before_guard_relock(self) -> None:
        game = self._game("game_uninstall_guard_order")
        installer.install_main(
            game, installer.Reporter(), skip_system=True,
            metadata_path=self.metadata, asset_file=self.archive,
        )
        real_write_json = installer.write_json
        guard_locked = {"value": True}
        actions: list[str] = []

        def guard_active(_root: Path) -> bool:
            return guard_locked["value"]

        def run_guard(action: str, _root: Path) -> None:
            actions.append(action)
            guard_locked["value"] = action == "lock"

        def reject_root_write_after_lock(path: Path, value: object) -> None:
            if guard_locked["value"] and installer.inside(path, game):
                raise PermissionError(f"write attempted after Guard relock: {path}")
            real_write_json(path, value)

        with (
            mock.patch.object(installer, "guard_active_for", side_effect=guard_active),
            mock.patch.object(installer, "run_guard", side_effect=run_guard),
            mock.patch.object(installer, "write_json", side_effect=reject_root_write_after_lock),
        ):
            result = installer.uninstall_main(game, allow_guard_disable=True)

        report = json.loads((Path(result.deleted_root) / "uninstall-report.json").read_text(encoding="utf-8"))
        self.assertEqual(actions, ["unlock", "lock"])
        self.assertTrue(result.guard_was_restored)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["guard_restore_requested"])

    def test_public_ui_requires_executable_inside_game_root(self) -> None:
        game = self._game("game_executable_root")
        executable = game / "GGO_No_Hidden_Heroes_Installer.exe"
        executable.write_bytes(b"fixture")
        with mock.patch.object(installer.sys, "frozen", True, create=True), mock.patch.object(installer.sys, "executable", str(executable)):
            self.assertEqual(installer.executable_game_root(), installer.norm(game))
        outside = self.work / "outside" / "GGO_No_Hidden_Heroes_Installer.exe"
        outside.parent.mkdir()
        outside.write_bytes(b"fixture")
        with mock.patch.object(installer.sys, "frozen", True, create=True), mock.patch.object(installer.sys, "executable", str(outside)):
            self.assertIsNone(installer.executable_game_root())

    def test_frozen_cli_rejects_location_before_initializing_log(self) -> None:
        outside = self.work / "outside_cli" / "GGO_No_Hidden_Heroes_Installer.exe"
        outside.parent.mkdir()
        outside.write_bytes(b"fixture")
        result_path = outside.parent / "must-not-exist.json"
        arguments = [str(outside), "--non-interactive", "--check-only", "--result-json", str(result_path)]
        with (
            mock.patch.object(installer.sys, "frozen", True, create=True),
            mock.patch.object(installer.sys, "executable", str(outside)),
            mock.patch.object(installer.sys, "argv", arguments),
            mock.patch.object(installer, "initialize_log") as initialize_log,
            mock.patch.object(installer.sys, "stdout", mock.Mock()),
        ):
            self.assertEqual(installer.main(), 2)
        initialize_log.assert_not_called()
        self.assertFalse(result_path.exists())

    def test_install_creates_root_uninstall_shortcut_to_same_executable(self) -> None:
        game = self._game("game_uninstall_shortcut")
        executable = game / "GGO_No_Hidden_Heroes_Installer.exe"
        executable.write_bytes(b"fixture executable")
        target = game / "INSTALL.cmd"
        target.write_bytes(b"installed")
        staged = self.payload / "INSTALL.cmd"
        plan = installer.FilePlan("INSTALL.cmd", staged, staged.stat().st_size)
        backup = installer.DATA_ROOT / "backups" / "shortcut_fixture"
        backup.mkdir(parents=True)
        (backup / "backup_manifest.json").write_text("{}", encoding="utf-8")
        release = installer.Release(
            "fixture-1.0.0",
            installer.Asset(self.archive.name, "https://example.invalid/main.zip", self.archive.stat().st_size, digest(self.archive).upper()),
            None,
        )
        with mock.patch.object(installer.sys, "frozen", True, create=True), mock.patch.object(installer.sys, "executable", str(executable)), mock.patch.object(installer, "create_shortcut") as create:
            installer.write_install_receipt(
                installer.norm(game), release, [plan], backup,
                [{"relative": "INSTALL.cmd", "existed": False}], [], [], False,
            )
        create.assert_called_once()
        shortcut, shortcut_target, arguments, working, description = create.call_args.args
        self.assertEqual(shortcut, installer.norm(game) / installer.UNINSTALL_SHORTCUT)
        self.assertEqual(shortcut_target, executable.resolve())
        self.assertEqual(arguments, "--uninstall")
        self.assertEqual(working, installer.norm(game))
        self.assertIn(installer.DELETED_ROOT_NAME, description)

    def test_bad_digest_does_not_mutate_game(self) -> None:
        game = self._game("game_bad_digest")
        bad = self.work / "bad.json"
        self._metadata(bad, "0" * 64)
        with self.assertRaisesRegex(installer.InstallerError, "SHA-256 mismatch"):
            installer.install_main(game, installer.Reporter(), skip_system=True, metadata_path=bad, asset_file=self.archive)
        self.assertFalse((game / "DS" / "Content" / "Paks" / "mods" / "DS_GGO_RESTORATION_P.pak").exists())

    def test_traversal_is_rejected_before_extraction(self) -> None:
        traversal = self.work / "traversal.zip"
        shutil.copy2(self.archive, traversal)
        with zipfile.ZipFile(traversal, "a") as package:
            package.writestr("../escaped.txt", "escape")
        staging = self.work / "staging"
        with self.assertRaisesRegex(installer.InstallerError, "Unsafe ZIP path"):
            installer.extract_main_archive(traversal, staging, installer.Reporter())
        self.assertFalse((self.work / "escaped.txt").exists())

    def test_configuration_failure_rolls_back_files(self) -> None:
        game = self._game("game_rollback")
        old = game / "DS" / "Binaries" / "Win64" / "ue4ss" / "UE4SS.dll"
        old.parent.mkdir(parents=True)
        old.write_bytes(b"old ue4ss")
        with mock.patch.object(installer, "configure", side_effect=installer.InstallerError("forced configuration failure")):
            with self.assertRaisesRegex(installer.InstallerError, "forced configuration failure"):
                installer.install_main(game, installer.Reporter(), skip_system=True, metadata_path=self.metadata, asset_file=self.archive)
        self.assertEqual(old.read_bytes(), b"old ue4ss")
        self.assertFalse((game / "DS" / "Content" / "Paks" / "mods" / "DS_GGO_RESTORATION_P.pak").exists())
        self.assertFalse((game / "DS/Binaries/Win64/ue4ss/QualificationMods/DSLocalMailService/Backend").exists())
        self.assertFalse((game / "DS/Binaries/Win64/ue4ss/QualificationMods/DSLocalSeasonPassPreview/Runtime").exists())

    def test_guard_offer_requires_same_steam_root(self) -> None:
        game = self._game("game_guard_scope")
        with mock.patch.object(installer, "steam_games", return_value=[self.work / "different"]):
            self.assertFalse(installer.can_install_guard(game))
        with mock.patch.object(installer, "steam_games", return_value=[game]):
            self.assertTrue(installer.can_install_guard(game))

    def test_guard_v2_is_deployed_to_game_root_before_install(self) -> None:
        game = self._game("game_guard_v2")
        guard_zip = self.work / "DragonSword_Update_Guard.zip"
        guard_bytes = os.urandom(1024 * 1024)
        with zipfile.ZipFile(guard_zip, "w", zipfile.ZIP_STORED) as package:
            package.writestr("DragonSwordGuard.exe", guard_bytes)
        asset = installer.Asset(
            guard_zip.name, "https://example.invalid/guard.zip",
            guard_zip.stat().st_size, digest(guard_zip).upper(),
        )
        release = installer.Release("fixture", installer.resolve_release(self.metadata).main, asset)
        completed = mock.Mock(returncode=0)
        with (
            mock.patch.object(installer, "can_install_guard", return_value=True),
            mock.patch.object(installer, "guard_active_for", return_value=True),
            mock.patch.object(installer.subprocess, "run", return_value=completed) as run,
        ):
            installer.install_guard(release, game, installer.Reporter(), guard_zip)
        deployed = game / "DragonSwordGuard.exe"
        self.assertEqual(deployed.read_bytes(), guard_bytes)
        self.assertEqual(Path(run.call_args.args[0][0]), deployed)
        self.assertEqual(run.call_args.args[0][1], "install")
        with (
            mock.patch.object(installer, "can_install_guard", return_value=True),
            mock.patch.object(installer, "guard_active_for", return_value=False),
            mock.patch.object(installer.subprocess, "run", return_value=completed) as setup_run,
        ):
            installer.install_guard(release, game, installer.Reporter(), guard_zip, enable_now=False)
        self.assertEqual(setup_run.call_args.args[0][1], "setup")


if __name__ == "__main__":
    unittest.main(verbosity=2)
