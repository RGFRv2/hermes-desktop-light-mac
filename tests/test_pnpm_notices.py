import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from license_notices import locked_integrity, pnpm_integrity, stage_notices
import test_public_distribution


class PnpmNoticeTests(unittest.TestCase):
    def make_pnpm_source(self, root):
        source, resources = test_public_distribution.PublicDistributionTests().make_source(root)
        policy = Path(__file__).resolve().parents[1] / 'notices/reviewed-packages.json'
        record = json.loads(policy.read_text())['packages']['@audiowave/core@0.3.1']
        original = source / 'node_modules/@example/library'
        (original / 'LICENSE-MIT').unlink()
        (original / 'package.json').write_text(json.dumps({
            'name': '@audiowave/core', 'version': '0.3.1', 'license': 'MIT'}))
        package = source / 'node_modules/.pnpm/@audiowave+core@0.3.1_react@19.3.0/node_modules/@audiowave/core'
        package.parent.mkdir(parents=True)
        original.rename(package)
        desktop = source / 'apps/desktop'
        (desktop / 'package.json').write_text(json.dumps({
            'name': 'hermes', 'version': '0.0.0',
            'dependencies': {'@audiowave/core': '0.3.1'}}))
        link = desktop / 'node_modules/@audiowave/core'
        link.parent.mkdir(parents=True)
        link.symlink_to(package, target_is_directory=True)
        lock = ("lockfileVersion: '9.0'\n\nimporters:\n  apps/desktop: {}\n\npackages:\n\n"
                "  '@audiowave/core@0.3.1':\n"
                '    resolution: {integrity: ' + record['package_integrity'] + '}\n\n'
                'snapshots:\n  @audiowave/core@0.3.1: {}\n')
        (source / 'pnpm-lock.yaml').write_text(lock)
        return source, resources, package, lock

    def test_pnpm_virtual_store_uses_exact_registry_archive_for_reviewed_notice(self):
        with tempfile.TemporaryDirectory() as root:
            source, resources, package, _ = self.make_pnpm_source(Path(root))
            stage_notices(source, resources)
            inventory = json.loads((resources / 'licenses/npm-inventory.json').read_text())
            self.assertIn('@audiowave/core@0.3.1', inventory['publisher_declaration_only'])
            self.assertIn(package.relative_to(source).as_posix(),
                          [item['path'] for item in inventory['packages']])
            self.assertFalse((source / 'package-lock.json').exists())

    def test_changed_or_missing_pnpm_archive_cannot_reuse_reviewed_notice(self):
        for change in ('integrity', 'version', 'missing'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as root:
                source, resources, package, lock = self.make_pnpm_source(Path(root))
                if change == 'integrity':
                    lock = lock.replace('resolution: {integrity: sha512-', 'resolution: {integrity: sha512-changed')
                elif change == 'version':
                    lock = lock.replace('@audiowave/core@0.3.1', '@audiowave/core@0.3.2')
                else:
                    lock = lock[:lock.index('packages:')] + 'packages:\n\nsnapshots:\n'
                (source / 'pnpm-lock.yaml').write_text(lock)
                with self.assertRaisesRegex(ValueError, 'no longer matches'):
                    stage_notices(source, resources)

    def test_unsupported_or_ambiguous_pnpm_evidence_is_rejected(self):
        valid = "lockfileVersion: '9.0'\npackages:\n  example@1.0.0:\n    resolution: {integrity: sha512-YWJj}\nsnapshots:\n"
        self.assertEqual(pnpm_integrity(valid, 'example@1.0.0'), 'sha512-YWJj')
        self.assertIsNone(pnpm_integrity(valid, 'example@2.0.0'))
        cases = [valid.replace("'9.0'", "'10.0'"), valid + '---\npackages:\n',
                 valid + 'packages:\n',
                 valid.replace('snapshots:', '  example@1.0.0:\n    resolution: {integrity: sha512-YWJj}\nsnapshots:'),
                 valid.replace('sha512-YWJj}', "'sha512-YWJj'}"),
                 valid.replace('snapshots:', '    resolution: {integrity: sha512-YWJj}\nsnapshots:')]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                pnpm_integrity(text, 'example@1.0.0')

    def test_importers_and_peer_snapshots_cannot_supply_archive_integrity(self):
        text = ("lockfileVersion: '9.0'\nimporters:\n  example@1.0.0:\n"
                '    resolution: {integrity: sha512-YWJj}\npackages:\n'
                'snapshots:\n  example@1.0.0:\n    resolution: {integrity: sha512-YWJj}\n')
        self.assertIsNone(pnpm_integrity(text, 'example@1.0.0'))

    def test_missing_and_conflicting_lockfiles_have_explicit_errors(self):
        with tempfile.TemporaryDirectory() as root:
            source, _, package, _ = self.make_pnpm_source(Path(root))
            metadata = json.loads((package / 'package.json').read_text())
            (source / 'package-lock.json').write_text('{"packages": {}}')
            with self.assertRaisesRegex(ValueError, 'Ambiguous'):
                locked_integrity(source, package, metadata)
            (source / 'package-lock.json').unlink()
            (source / 'pnpm-lock.yaml').unlink()
            with self.assertRaisesRegex(ValueError, 'lockfile is missing'):
                locked_integrity(source, package, metadata)
