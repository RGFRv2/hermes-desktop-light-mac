"""Run the upstream Light builder with distribution signing disabled."""
import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from common import read_json, run, validate_manifest


def build(manifest, source):
    validate_manifest(manifest)
    if sys.platform != 'darwin' or platform.machine() != 'arm64':
        raise ValueError('A native macOS ARM64 runner is required')
    source = Path(source).resolve()
    if run(['git', 'rev-parse', 'HEAD'], cwd=source) != manifest['sha']:
        raise ValueError('Source checkout no longer matches selected release')
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('APPLE_', 'CSC_', 'AZURE_SIGN_', 'RELEASE_CLAIM_'))
           and key not in {'GH_TOKEN', 'GITHUB_TOKEN', 'CLOUDFLARE_R2_PUBLIC_URL',
                           'HERMES_MAC_SIGNATURE_CACHE', 'HERMES_BUNDLE_ENV_JSON',
                           'HERMES_BUILD_COMMIT', 'HERMES_PAYLOAD_TAG'}}
    env['CSC_IDENTITY_AUTO_DISCOVERY'] = 'false'
    if claim := manifest.get('claim'):
        env['RELEASE_CLAIM_TAG'] = claim['tag']
        env['RELEASE_CLAIM_OBJECT'] = claim['object']
    else:
        contract = (source / 'scripts/bundles/desktop_prepare.py').read_text()
        if 'stable preparation requires its exact claim tag' in contract:
            raise ValueError('Upstream release is missing the annotated build claim required by its builder')
    subprocess.run([sys.executable, 'scripts/bundles/desktop.py', '--tag=' + manifest['tag'],
                    '--variant=light', '--clean'],
                   cwd=source, env=env, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    build(read_json(args.manifest), args.source)
