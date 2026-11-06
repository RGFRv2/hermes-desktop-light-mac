import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from license_notices import stage_notices, verify_notices
from release_notes import render_notes
import test_automation
from publish import verify_downloads


class PublicDistributionTests(unittest.TestCase):
    def make_source(self, root, chromium=True):
        source, resources = root / 'source', root / 'resources'
        source.mkdir()
        resources.mkdir()
        (source / 'LICENSE').write_text('Upstream Hermes fixture license\n')
        prepared = source / '.build/desktop-job/packager'
        prepared.mkdir(parents=True)
        electron = prepared / 'electron.zip'
        with zipfile.ZipFile(electron, 'w') as archive:
            archive.writestr('LICENSE', 'Electron fixture license\n')
            if chromium:
                archive.writestr('LICENSES.chromium.html', '<html>Chromium fixture notices</html>')
        (prepared / 'prepared.json').write_text(json.dumps({'electron': str(electron)}))
        desktop = source / 'apps/desktop'
        desktop.mkdir(parents=True)
        (desktop / 'package.json').write_text(json.dumps({'name': 'hermes', 'version': '1.0.0',
            'dependencies': {'@example/library': '1.0.0'}}))
        package = source / 'node_modules/@example/library'
        package.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps(
            {'name': '@example/library', 'version': '1.0.0', 'license': 'MIT'}))
        (package / 'LICENSE-MIT').write_text('npm fixture license\n')
        fixture = package / 'test/invalid-package'
        fixture.mkdir(parents=True)
        (fixture / 'package.json').write_text('intentionally not a valid installed package')
        (source / 'node_modules/linked-package').symlink_to(package, target_is_directory=True)
        return source, resources

    def test_notices_come_from_locked_inputs_without_absolute_inventory_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, resources = self.make_source(Path(temporary))
            stage_notices(source, resources)
            licenses = resources / 'licenses'
            self.assertEqual((licenses / 'HERMES-LICENSE.txt').read_bytes(), (source / 'LICENSE').read_bytes())
            self.assertEqual((licenses / 'electron/LICENSE.txt').read_text(), 'Electron fixture license\n')
            inventory = json.loads((licenses / 'npm-inventory.json').read_text())
            self.assertEqual(len(inventory['packages']), 2)
            self.assertIn('@example/library', [p['name'] for p in inventory['packages']])
            self.assertIn('node_modules/@example/library/LICENSE-MIT', inventory['notice_files'])
            self.assertNotIn(str(source), json.dumps(inventory))
            verify_notices(resources)

    def test_missing_locked_chromium_notices_fail_packaging(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, resources = self.make_source(Path(temporary), chromium=False)
            with self.assertRaisesRegex(ValueError, 'LICENSES.chromium.html'):
                stage_notices(source, resources)

    def test_removed_notice_is_detected_after_archiving(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, resources = self.make_source(Path(temporary))
            stage_notices(source, resources)
            (resources / 'licenses/electron/LICENSE.txt').unlink()
            with self.assertRaisesRegex(ValueError, 'Missing redistribution notice'):
                verify_notices(resources)

    def test_external_notice_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, resources = self.make_source(Path(temporary))
            stage_notices(source, resources)
            inventory = resources / 'licenses/npm-inventory.json'
            data = json.loads(inventory.read_text())
            data['notice_files'].append('../HERMES-LICENSE.txt')
            inventory.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Invalid npm notice path'):
                verify_notices(resources)

    def test_french_notes_are_required_before_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fixtures = test_automation.AutomationTests()
            fixtures.make_release(directory)
            (directory / 'RELEASE_NOTES.fr.md').unlink()
            fixtures.rehash(directory)
            with self.assertRaisesRegex(ValueError, 'Incomplete release file set'):
                verify_downloads(directory)

    def test_english_release_has_french_link_and_shared_provenance(self):
        value = {**test_automation.manifest(), 'upstream_release_url': 'https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.0'}
        french_url = 'https://github.com/example/builds/releases/download/v0.23.0-macos.3/RELEASE_NOTES.fr.md'
        english, french = render_notes(value, 'Hermes Light.app', 'https://github.com/example/builds/actions/runs/123', french_url)
        self.assertIn(f'[Français]({french_url})', english)
        self.assertIn('Download the DMG', english)
        self.assertIn('Télécharger le DMG', french)
        for text in (english, french):
            self.assertIn(value['sha'], text)
            self.assertIn(value['upstream_release_url'], text)
            self.assertIn('Contents/Resources/licenses/', text)


if __name__ == '__main__':
    unittest.main()
