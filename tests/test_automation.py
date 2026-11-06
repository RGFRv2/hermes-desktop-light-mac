import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import UPSTREAM, digest, distribution_tag, distribution_version, find_release, stable_version, validate_manifest, write_json
from package_macos import check_zip, validate_stamp
from publish import verify_downloads
from resolve import resolve
from repack_macos import verify_signature
from sign_macos import signing_plan


def manifest():
    return {'tag': 'v0.23.0', 'sha': 'a' * 40, 'tag_object': 'b' * 40,
            'release_tag': 'v0.23.0-macos.2', 'packaging_revision': 2,
            'upstream_repository': UPSTREAM,
            'claim': {'tag': 'rc.2-v0.23.0', 'object': 'c' * 40}}


def stamp():
    return {'payload': 'light', 'commit': 'a' * 40, 'tag': 'v0.23.0', 'dirty': False}


class AutomationTests(unittest.TestCase):
    def fake_api(self, published=False, complete=True, prerelease=False, wrong_commit=False):
        self.calls = []

        def get(path, missing_ok=False):
            self.calls.append(path)
            if path.startswith('/repos/example/builds/releases?'):
                return []
            if path.startswith('/repos/example/builds/releases/tags/'):
                if not published:
                    return None
                names = ['HermesLight-0.23.0-mac-arm64.dmg', 'HermesLight-0.23.0-mac-arm64.zip',
                         'SHA256SUMS', 'build-manifest.json', 'validation.json',
                         'RELEASE_NOTES.md', 'RELEASE_NOTES.fr.md']
                return {'draft': False, 'assets': [{'name': n} for n in names if complete or n != 'SHA256SUMS']}
            if '/releases/' in path:
                return {'tag_name': 'v0.23.0', 'draft': False, 'prerelease': prerelease,
                        'html_url': 'https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.0',
                        'published_at': '2026-11-05T21:32:33Z'}
            if '/git/ref/tags/' in path:
                return {'object': {'type': 'tag', 'sha': 'b' * 40}}
            if '/git/tags/' in path:
                return {'object': {'type': 'commit', 'sha': 'a' * 40},
                        'message': json.dumps({'claimTag': 'rc.2-v0.23.0',
                                               'claimTagObject': 'c' * 40,
                                               'commit': ('d' if wrong_commit else 'a') * 40})}
            raise AssertionError(path)
        return get

    def test_latest_uses_annotated_tag_commit_and_genuine_claim(self):
        value, tag = resolve('', 'example/builds', self.fake_api())
        self.assertEqual(tag, 'v0.23.0')
        self.assertEqual(value['sha'], 'a' * 40)
        self.assertEqual(value['claim'], manifest()['claim'])
        self.assertIn(f'/repos/{UPSTREAM}/releases/latest', self.calls)

    def test_draft_without_a_materialized_tag_is_found_in_release_listing(self):
        calls = []
        draft = {'id': 42, 'tag_name': 'v0.23.0', 'draft': True, 'assets': []}

        def get(path, missing_ok=False):
            calls.append(path)
            return None if '/releases/tags/' in path else [draft]

        self.assertEqual(find_release('example/builds', 'v0.23.0', get), draft)
        self.assertEqual(len(calls), 2)

    def test_draft_lookup_follows_release_listing_pagination(self):
        draft = {'id': 42, 'tag_name': 'v0.23.0', 'draft': True}

        def get(path, missing_ok=False):
            if '/releases/tags/' in path:
                return None
            if path.endswith('&page=1'):
                return [{'tag_name': 'v1.0.0'}] * 100
            return [draft]

        self.assertEqual(find_release('example/builds', 'v0.23.0', get), draft)

    def test_manual_tag_fetches_its_published_release(self):
        resolve('v0.23.0', 'example/builds', self.fake_api())
        self.assertIn(f'/repos/{UPSTREAM}/releases/tags/v0.23.0', self.calls)

    def test_complete_release_is_skipped_without_resolving_git_objects(self):
        value, _ = resolve('', 'example/builds', self.fake_api(published=True))
        self.assertIsNone(value)
        self.assertFalse(any('/git/' in path for path in self.calls))

    def test_pull_request_rebuilds_already_published_version_for_validation(self):
        value, _ = resolve('', 'example/builds', self.fake_api(published=True), validation_only=True)
        self.assertEqual(value['release_tag'], 'v0.23.0-macos.2')

    def test_packaging_repair_has_its_own_tag_and_version_order(self):
        self.assertEqual(distribution_tag('v0.23.0'), 'v0.23.0-macos.2')
        self.assertGreater(distribution_version('v0.23.0-macos.2'), distribution_version('v0.23.0'))
        self.assertGreater(distribution_version('v0.23.1-macos.1'), distribution_version('v0.23.0-macos.2'))

    def test_incomplete_published_release_is_not_silently_skipped(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            resolve('', 'example/builds', self.fake_api(published=True, complete=False))

    def test_prerelease_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'published stable'):
            resolve('', 'example/builds', self.fake_api(prerelease=True))

    def test_conflicting_annotation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            resolve('', 'example/builds', self.fake_api(wrong_commit=True))

    def test_unsafe_or_nonstable_tags_are_rejected_before_api(self):
        for tag in ('main', 'v1.0.0-rc.1', 'v01.2.3', '../v1.2.3', 'v1.2.3\nmalicious=true'):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                stable_version(tag)

    def test_claim_from_another_version_is_rejected(self):
        value = manifest()
        value['claim']['tag'] = 'rc.2-v0.22.7'
        with self.assertRaisesRegex(ValueError, 'Claim tag'):
            validate_manifest(value)

    def test_bundled_dirty_wrong_commit_and_runtime_stamps_are_rejected(self):
        for change in ({'payload': 'bundled'}, {'dirty': True}, {'commit': 'd' * 40},
                       {'runtime': {}}, {'tag': 'v0.22.7'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_stamp({**stamp(), **change}, manifest())

    def test_zip_contains_the_right_light_stamp_and_no_payload(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'app.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('Hermes Light.app/Contents/Resources/install-stamp.json', json.dumps(stamp()))
            check_zip(path, 'Hermes Light.app', manifest())
            with zipfile.ZipFile(path, 'a') as archive:
                archive.writestr('Hermes Light.app/Contents/Resources/agent-payload/python', 'runtime')
            with self.assertRaisesRegex(ValueError, 'agent payload'):
                check_zip(path, 'Hermes Light.app', manifest())

    def make_release(self, directory):
        write_json(directory / 'build-manifest.json', manifest())
        write_json(directory / 'validation.json', {
            'architecture': 'arm64', 'version': '0.23.0',
            'codesign_exit_code': 0, 'signature_type': 'ad-hoc',
            'archives_signature_verified': True, 'native_process_smoke_test': True, 'license_notices_included': True,
            'light_stamp_and_no_agent_payload': True, 'dmg_integrity': True, 'zip_integrity': True})
        for name in ('HermesLight-0.23.0-mac-arm64.dmg', 'HermesLight-0.23.0-mac-arm64.zip', 'RELEASE_NOTES.md', 'RELEASE_NOTES.fr.md'):
            (directory / name).write_text('fixture')
        self.rehash(directory)

    def rehash(self, directory):
        sums = ''.join(f'{digest(p)}  {p.name}\n' for p in sorted(directory.iterdir()) if p.name != 'SHA256SUMS')
        (directory / 'SHA256SUMS').write_text(sums)

    def test_complete_release_passes_integrity_check(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            self.make_release(directory)
            self.assertEqual(verify_downloads(directory)['tag'], 'v0.23.0')

    def test_tampered_installer_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            self.make_release(directory)
            (directory / 'HermesLight-0.23.0-mac-arm64.dmg').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Integrity check'):
                verify_downloads(directory)

    def test_missing_installer_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            self.make_release(directory)
            (directory / 'HermesLight-0.23.0-mac-arm64.zip').unlink()
            self.rehash(directory)
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                verify_downloads(directory)

    def test_failed_validation_cannot_be_published_even_with_correct_checksums(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            self.make_release(directory)
            write_json(directory / 'validation.json', {'architecture': 'x86_64'})
            self.rehash(directory)
            with self.assertRaisesRegex(ValueError, 'validation'):
                verify_downloads(directory)

    def test_invalid_signature_or_unchecked_archives_cannot_be_published(self):
        for invalid in ({'codesign_exit_code': 1}, {'archives_signature_verified': False},
                        {'native_process_smoke_test': False}, {'license_notices_included': False}):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as root:
                directory = Path(root)
                self.make_release(directory)
                validation = json.loads((directory / 'validation.json').read_text())
                write_json(directory / 'validation.json', {**validation, **invalid})
                self.rehash(directory)
                with self.assertRaisesRegex(ValueError, 'validation'):
                    verify_downloads(directory)

    def test_codesign_failure_is_fatal(self):
        import subprocess
        with patch('repack_macos.subprocess.run', side_effect=subprocess.CalledProcessError(1, ['codesign'])):
            with self.assertRaises(subprocess.CalledProcessError):
                verify_signature(Path('/example.app'))

    def test_signing_plan_signs_nested_code_before_containing_bundles_and_skips_symlinks(self):
        with tempfile.TemporaryDirectory() as root:
            app = Path(root) / 'Example.app'
            framework = app / 'Contents/Frameworks/Example.framework'
            binary = framework / 'Versions/A/Example'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(bytes.fromhex('cffaedfe') + b'fixture')
            (framework / 'Versions/Current').symlink_to('A')
            (framework / 'Example').symlink_to('Versions/Current/Example')
            plan = signing_plan(app)
            self.assertEqual(plan, [binary.resolve(), framework.resolve(), app.resolve()])

    def test_checksum_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            self.make_release(directory)
            (directory / 'SHA256SUMS').write_text('a' * 64 + '  ../unexpected\n')
            with self.assertRaisesRegex(ValueError, 'Invalid checksum'):
                verify_downloads(directory)


if __name__ == '__main__':
    unittest.main()
