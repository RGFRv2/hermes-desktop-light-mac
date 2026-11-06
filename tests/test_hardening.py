import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import publish
from app_identity import validate_identity, BUNDLE_ID
from common import digest, require_python
from license_notices import stage_notices, runtime_packages, verify_notices
import test_public_distribution
import test_automation


class HardeningTests(unittest.TestCase):
    def test_manual_main_is_allowed_other_refs_and_events_fail_before_io(self):
        for event in ('push', 'schedule', 'workflow_dispatch'):
            publish.require_publication_context({'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_NAME': event})
        for ref, event in [('refs/heads/topic', 'workflow_dispatch'),
                           ('refs/tags/main', 'workflow_dispatch'), ('refs/heads/main', 'pull_request')]:
            with patch.dict('os.environ', {'GITHUB_REF': ref, 'GITHUB_EVENT_NAME': event}), \
                 patch.object(publish, 'verify_downloads') as validate, self.assertRaises(ValueError):
                publish.publish('absent')
            validate.assert_not_called()

    def test_remote_digests_states_and_duplicate_assets_are_checked(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / 'artifact').write_bytes(b'abc')
            asset = {'name': 'artifact', 'state': 'uploaded', 'size': 3,
                     'digest': 'sha256:' + digest(directory / 'artifact')}
            publish.verify_uploaded_assets({'assets': [asset]}, directory)
            for change in ({'digest': 'sha256:' + '0' * 64}, {'digest': None},
                           {'state': 'new'}, {'size': 2}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    publish.verify_uploaded_assets({'assets': [{**asset, **change}]}, directory)
            with self.assertRaises(ValueError):
                publish.verify_uploaded_assets({'assets': [asset, asset]}, directory)

    def test_draft_identity_and_status_are_checked(self):
        release = {'id': 1, 'tag_name': 'v1.0.0-macos.3', 'draft': True}
        self.assertEqual(publish.verify_draft(release, release['tag_name']), 1)
        for change in ({'draft': False}, {'immutable': True}, {'id': 2}, {'tag_name': 'other'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                publish.verify_draft({**release, **change}, release['tag_name'], 1)

    def test_publication_does_not_promote_a_draft_with_wrong_remote_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            test_automation.AutomationTests().make_release(directory)
            draft = {'id': 1, 'draft': True, 'tag_name': 'v0.23.0-macos.3',
                     'assets': [{'name': p.name, 'size': p.stat().st_size, 'state': 'uploaded',
                                 'digest': 'sha256:' + '0' * 64} for p in directory.iterdir()]}
            with patch.dict('os.environ', {'GITHUB_REF': 'refs/heads/main',
                     'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REPOSITORY': 'example/builds'}), \
                 patch.object(publish, 'find_release', return_value=draft), \
                 patch.object(publish.subprocess, 'run') as invoke, self.assertRaises(ValueError):
                publish.publish(directory)
            self.assertFalse(any('--draft=false' in c.args[0] for c in invoke.call_args_list))

    def test_changed_application_or_profile_identity_is_rejected(self):
        plist = {'CFBundleIdentifier': BUNDLE_ID, 'CFBundleExecutable': 'Hermes Light'}
        package = {'name': 'HermesLight', 'productName': 'Hermes', 'desktopName': BUNDLE_ID}
        validate_identity('Hermes Light.app', plist, package)
        for name, info, meta in [('Other.app', plist, package),
                 ('Hermes Light.app', {**plist, 'CFBundleIdentifier': 'other'}, package),
                 ('Hermes Light.app', plist, {**package, 'productName': 'HermesLight'}),
                 ('Hermes Light.app', plist, {**package, 'name': 'HermesLightCommit1234567'})]:
            with self.assertRaises(ValueError):
                validate_identity(name, info, meta)

    def test_python_version_has_clear_failure(self):
        require_python((3, 12))
        with self.assertRaisesRegex(RuntimeError, 'Python 3.12'):
            require_python((3, 9))

    def test_runtime_package_without_notice_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            source, resources = test_public_distribution.PublicDistributionTests().make_source(Path(root))
            (source / 'node_modules/@example/library/LICENSE-MIT').unlink()
            with self.assertRaisesRegex(ValueError, 'require review'):
                stage_notices(source, resources)

    def test_nested_runtime_dependencies_are_collected(self):
        with tempfile.TemporaryDirectory() as root:
            source, resources = test_public_distribution.PublicDistributionTests().make_source(Path(root))
            library = source / 'node_modules/@example/library'
            metadata = json.loads((library / 'package.json').read_text())
            metadata['dependencies'] = {'nested': '1.0.0'}
            (library / 'package.json').write_text(json.dumps(metadata))
            nested = library / 'node_modules/nested'
            nested.mkdir(parents=True)
            (nested / 'package.json').write_text(json.dumps({'name': 'nested', 'version': '1.0.0', 'license': 'MIT'}))
            (nested / 'LICENSE').write_text('Nested license text')
            stage_notices(source, resources)
            inventory = json.loads((resources / 'licenses/npm-inventory.json').read_text())
            self.assertIn('nested', [p['name'] for p in inventory['packages']])

    def test_external_dependency_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            source, _ = test_public_distribution.PublicDistributionTests().make_source(Path(root))
            external = Path(root) / 'external'
            external.mkdir()
            (external / 'package.json').write_text('{}')
            (source / 'apps/desktop/node_modules').mkdir()
            (source / 'apps/desktop/node_modules/@example').mkdir()
            (source / 'apps/desktop/node_modules/@example/library').symlink_to(external)
            with self.assertRaisesRegex(ValueError, 'escapes'):
                list(runtime_packages(source))

    def test_missing_package_coverage_fails_archive_validation(self):
        with tempfile.TemporaryDirectory() as root:
            source, resources = test_public_distribution.PublicDistributionTests().make_source(Path(root))
            stage_notices(source, resources)
            inventory = resources / 'licenses/npm-inventory.json'
            data = json.loads(inventory.read_text())
            data['packages'][0]['notice_files'] = []
            inventory.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'notice coverage'):
                verify_notices(resources)
