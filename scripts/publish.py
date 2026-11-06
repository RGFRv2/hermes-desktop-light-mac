"""Publish complete installer sets without replacing a published version."""
import argparse
import os
import re
import subprocess
from pathlib import Path
from common import api, digest, distribution_tag, distribution_version, find_release, read_json, summary, validate_manifest


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
            or not all(validation.get(key) is True for key in
                       ('light_stamp_and_no_agent_payload', 'dmg_integrity', 'zip_integrity'))):
        raise ValueError('Package validation did not pass')
    return manifest


def publish(directory):
    directory = Path(directory).resolve()
    manifest = verify_downloads(directory)
    repository = os.environ['GITHUB_REPOSITORY']
    tag = manifest['release_tag']
    if tag != distribution_tag(manifest['tag']):
        raise ValueError('Distribution tag does not match upstream version')
    existing = find_release(repository, tag)
    if existing and not existing['draft']:
        raise ValueError('Release is already published; refusing to replace its bytes')
    files = [str(path) for path in sorted(directory.iterdir())]
    command = ['gh', 'release']
    common = ['--repo', repository]
    if not existing:
        subprocess.run([*command, 'create', tag, *common, '--target', os.environ['GITHUB_SHA'],
                        '--draft', '--title', f'Hermes Light {tag} — Mac ARM64',
                        '--notes-file', str(directory / 'RELEASE_NOTES.md')], check=True)
    # Only a draft is mutable. A retry may replace partial uploads in that draft.
    subprocess.run([*command, 'upload', tag, *common, '--clobber', *files], check=True)
    current = find_release(repository, tag)
    if not current:
        raise ValueError('Draft release could not be read back after upload')
    assets = {asset['name']: asset['size'] for asset in current['assets']}
    if assets != {Path(path).name: Path(path).stat().st_size for path in files}:
        raise ValueError('Uploaded release assets are missing or unexpected; leaving the release as a draft')
    latest = api(f'/repos/{repository}/releases/latest', missing_ok=True)
    promote = latest is None or distribution_version(tag) >= distribution_version(latest['tag_name'])
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
