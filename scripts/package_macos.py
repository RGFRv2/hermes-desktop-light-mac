"""Validate final Mac packages and produce the downloadable release set."""
import argparse
import json
import os
import plistlib
import shutil
import subprocess
import zipfile
from pathlib import Path
from common import digest, read_json, run, summary, validate_manifest, write_json
from sign_macos import sign_app
from repack_macos import archive_app, smoke_launch, verify_archive_signatures, verify_signature
from license_notices import stage_notices
from release_notes import render_notes


def validate_stamp(stamp, manifest):
    if (stamp.get('payload') != 'light' or stamp.get('commit') != manifest['sha']
            or stamp.get('tag') != manifest['tag'] or stamp.get('dirty') is not False):
        raise ValueError('Packaged stamp is not the selected clean Light release')
    if 'runtime' in stamp:
        raise ValueError('Light package unexpectedly declares a local Python runtime')


def check_zip(path, app_name, manifest):
    with zipfile.ZipFile(path) as archive:
        if bad := archive.testzip():
            raise ValueError(f'Corrupt ZIP member: {bad}')
        stamp_path = f'{app_name}/Contents/Resources/install-stamp.json'
        validate_stamp(json.loads(archive.read(stamp_path)), manifest)
        prefix = f'{app_name}/Contents/Resources/agent-payload'
        if any(name == prefix or name.startswith(prefix + '/') for name in archive.namelist()):
            raise ValueError('ZIP includes a local agent payload')


def package(manifest, source, output):
    validate_manifest(manifest)
    release = Path(source).resolve() / 'apps/desktop/release'
    apps = list((release / 'mac-arm64').glob('*.app'))
    if len(apps) != 1:
        raise ValueError(f'Expected exactly one top-level ARM64 app, found {apps}')
    app = apps[0]
    resources = app / 'Contents/Resources'
    stamp = read_json(resources / 'install-stamp.json')
    validate_stamp(stamp, manifest)
    if (resources / 'agent-payload').exists():
        raise ValueError('Light app includes an agent payload')
    with (app / 'Contents/Info.plist').open('rb') as stream:
        plist = plistlib.load(stream)
    executable = plist['CFBundleExecutable']
    if Path(executable).name != executable:
        raise ValueError('Invalid bundle executable name')
    arch = run(['lipo', '-archs', str(app / 'Contents/MacOS' / executable)])
    if arch != 'arm64':
        raise ValueError(f'Expected native arm64 app, found {arch!r}')
    if plist.get('CFBundleShortVersionString') != manifest['tag'][1:]:
        raise ValueError('Application version differs from the release tag')
    policy = Path(source).resolve() / 'apps/desktop/electron'
    stage_notices(source, resources)
    sign_app(app, policy / 'entitlements.mac.plist', policy / 'entitlements.mac.inherit.plist')
    smoke_launch(app)
    dmg_path, zip_path = archive_app(app, release, manifest['tag'][1:])
    verify_archive_signatures(dmg_path, zip_path, app.name)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Use a fresh release output directory')
    output.mkdir()
    version = manifest['tag'][1:]
    for extension in ('dmg', 'zip'):
        path = release / f'HermesLight-{version}-mac-arm64.{extension}'
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Missing or empty installer: {path}')
        if extension == 'dmg':
            subprocess.run(['hdiutil', 'verify', str(path)], check=True)
        else:
            check_zip(path, app.name, manifest)
        shutil.copy2(path, output / path.name)
    verify_signature(app)
    write_json(output / 'validation.json', {
        'architecture': arch, 'application': app.name, 'version': version,
        'runner_macos_version': run(['sw_vers', '-productVersion']),
        'light_stamp_and_no_agent_payload': True, 'dmg_integrity': True, 'zip_integrity': True,
        'codesign_exit_code': 0,
        'signature_type': 'ad-hoc', 'archives_signature_verified': True,
        'native_process_smoke_test': True,
        'license_notices_included': True,
        'developer_id': False, 'notarized': False,
        'interactive_install_and_launch_test': 'not performed by CI',
    })
    provenance = {**manifest, 'workflow_repository': os.environ.get('GITHUB_REPOSITORY'),
                  'workflow_sha': os.environ.get('GITHUB_SHA'),
                  'workflow_run_url': f'https://github.com/{os.environ.get("GITHUB_REPOSITORY")}/actions/runs/{os.environ.get("GITHUB_RUN_ID")}',
                  'source_modifications': [],
                  'artifact_processing': ['stage redistribution notices', 'inside-out ad-hoc signing',
                                          'repack signed app', 'verify archive signatures'],
                  'app_bundle_id': plist.get('CFBundleIdentifier'),
                  'runner_macos_version': run(['sw_vers', '-productVersion']),
                  'minimum_macos': plist.get('LSMinimumSystemVersion')}
    write_json(output / 'build-manifest.json', provenance)
    french_url = (f'https://github.com/{os.environ.get("GITHUB_REPOSITORY")}/releases/download/'
                  f'{manifest["release_tag"]}/RELEASE_NOTES.fr.md')
    english, french = render_notes(manifest, app.name, provenance['workflow_run_url'], french_url)
    (output / 'RELEASE_NOTES.md').write_text(english)
    (output / 'RELEASE_NOTES.fr.md').write_text(french)
    checksums = ''.join(f'{digest(path)}  {path.name}\n' for path in sorted(output.iterdir()))
    (output / 'SHA256SUMS').write_text(checksums)
    summary(f'Validated **{manifest["tag"]}** for Mac ARM64. DMG, ZIP and SHA-256 checksums are ready.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    package(read_json(args.manifest), args.source, args.output)
