"""Publish complete installer sets without replacing a published version."""
import argparse
import os
import re
import subprocess
from pathlib import Path
from common import api, digest, distribution_tag, distribution_version, find_release, read_json, summary, validate_manifest
from app_identity import BUNDLE_ID, PACKAGE_NAME, PROFILE_NAME


def verify_downloads(directory):
    directory = Path(directory)
    manifest = validate_manifest(read_json(directory / 'build-manifest.json'))
    version = manifest['tag'][1:]
    required = {f'HermesLight-{version}-mac-arm64.{suffix}' for suffix in ('dmg', 'zip')}
    required |= {'build-manifest.json', 'validation.json', 'RELEASE_NOTES.md', 'RELEASE_NOTES.fr.md'}
    checksums = {}
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  ([^/\\]+)', line)
        if not match or match[2] in checksums:
            raise ValueError('Invalid checksum manifest')
        checksums[match[2]] = match[1]
    if set(checksums) != required:
        raise ValueError('Incomplete release file set')
    if {path.name for path in directory.iterdir()} != required | {'SHA256SUMS'}:
        raise ValueError('Unexpected release files')
    for name, expected in checksums.items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f'Integrity check failed: {name}')
    validation = read_json(directory / 'validation.json')
    if (validation.get('architecture') != 'arm64' or validation.get('version') != version
            or validation.get('codesign_exit_code') != 0
            or validation.get('signature_type') != 'ad-hoc'
            or validation.get('archives_signature_verified') is not True
            or validation.get('native_process_smoke_test') is not True
            or validation.get('license_notices_included') is not True
            or validation.get('stable_application_identity') != {
                'bundle_id': BUNDLE_ID, 'package_name': PACKAGE_NAME, 'profile_name': PROFILE_NAME}
            or not all(validation.get(key) is True for key in
                       ('light_stamp_and_no_agent_payload', 'dmg_integrity', 'zip_integrity'))):
        raise ValueError('Package validation did not pass')
    return manifest


def require_publication_context(env=None):
    env = os.environ if env is None else env
    if (env.get('GITHUB_REF') != 'refs/heads/main'
            or env.get('GITHUB_EVENT_NAME') not in {'push', 'schedule', 'workflow_dispatch'}):
        raise ValueError('Publication requires an approved event on refs/heads/main')


def verify_draft(release, tag, release_id=None):
    if (not release or release.get('draft') is not True
            or release.get('tag_name') != tag or release.get('immutable') is True
            or not isinstance(release.get('id'), int)
            or (release_id is not None and release['id'] != release_id)):
        raise ValueError('Release identity changed or release is no longer a mutable draft')
    return release['id']


def verify_uploaded_assets(release, directory):
    files = {path.name: path for path in Path(directory).iterdir()}
    assets = release.get('assets', [])
    if len(assets) != len(files) or {a.get('name') for a in assets} != set(files):
        raise ValueError('Uploaded release assets are missing or unexpected')
    for asset in assets:
        path = files[asset['name']]
        if (asset.get('state') != 'uploaded' or asset.get('size') != path.stat().st_size
                or asset.get('digest') != 'sha256:' + digest(path)):
            raise ValueError(f'Uploaded asset integrity failed: {path.name}')


def publish(directory):
    require_publication_context()
    directory = Path(directory).resolve()
    manifest = verify_downloads(directory)
    repository = os.environ['GITHUB_REPOSITORY']
    tag = manifest['release_tag']
    if tag != distribution_tag(manifest['tag']):
        raise ValueError('Distribution tag does not match upstream version')
    existing = find_release(repository, tag)
    if existing and not existing['draft']:
        raise ValueError('Release is already published; refusing to replace its bytes')
    if existing:
        verify_draft(existing, tag)
    files = [str(path) for path in sorted(directory.iterdir())]
    command = ['gh', 'release']
    common = ['--repo', repository]
    if not existing:
        existing = api(f'/repos/{repository}/releases', method='POST', payload={
            'tag_name': tag, 'target_commitish': os.environ['GITHUB_SHA'], 'draft': True,
            'name': f'Hermes Light {tag} — Mac ARM64',
            'body': (directory / 'RELEASE_NOTES.md').read_text()})
    # The creation response is authoritative even before tag/list indexing catches up.
    release_id = verify_draft(existing, tag)
    release_path = f'/repos/{repository}/releases/{release_id}'
    current = api(release_path)
    verify_draft(current, tag, release_id)
    subprocess.run([*command, 'upload', tag, *common, '--clobber', *files], check=True)
    current = api(release_path)
    verify_draft(current, tag, release_id)
    verify_uploaded_assets(current, directory)
    latest = api(f'/repos/{repository}/releases/latest', missing_ok=True)
    promote = latest is None or distribution_version(tag) >= distribution_version(latest['tag_name'])
    current = api(release_path)
    verify_draft(current, tag, release_id)
    verify_uploaded_assets(current, directory)
    subprocess.run([*command, 'edit', tag, *common, '--draft=false',
                    '--latest=' + str(promote).lower(), '--target', os.environ['GITHUB_SHA'],
                    '--notes-file', str(directory / 'RELEASE_NOTES.md')],
                   check=True)
    summary(f'Installers: https://github.com/{repository}/releases/tag/{tag}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    publish(args.directory)
