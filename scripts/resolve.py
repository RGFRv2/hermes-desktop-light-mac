"""Resolve a published stable release, its exact commit, and upstream claim."""
import argparse
import json
import os
from common import (UPSTREAM, PACKAGING_REVISION, api, distribution_tag, find_release,
                    github_output, stable_version, summary, validate_manifest, write_json)


def resolve(tag, repository, get=api, validation_only=False):
    if tag:
        stable_version(tag)
    endpoint = f'/releases/tags/{tag}' if tag else '/releases/latest'
    release = get(f'/repos/{UPSTREAM}' + endpoint)
    tag = release['tag_name']
    stable_version(tag)
    if release.get('draft') is not False or release.get('prerelease') is not False:
        raise ValueError('Only published stable releases may be built')
    release_tag = distribution_tag(tag)
    existing = find_release(repository, release_tag, get)
    if existing and not existing['draft']:
        names = {asset['name'] for asset in existing.get('assets', [])}
        required = {f'HermesLight-{tag[1:]}-mac-arm64.{extension}' for extension in ('dmg', 'zip')}
        required |= {'SHA256SUMS', 'build-manifest.json', 'validation.json',
                     'RELEASE_NOTES.md', 'RELEASE_NOTES.fr.md'}
        if not required <= names:
            raise ValueError(f'Published release {tag} is incomplete; inspect it rather than overwrite it')
        if not validation_only:
            return None, tag
    reference = get(f'/repos/{UPSTREAM}/git/ref/tags/{tag}')['object']
    tag_object = reference['sha']
    record = {}
    if reference['type'] == 'tag':
        annotated = get(f'/repos/{UPSTREAM}/git/tags/{tag_object}')
        try:
            record = json.loads(annotated.get('message', ''))
        except json.JSONDecodeError:
            pass
        if not isinstance(record, dict):
            record = {}
        reference = annotated['object']
    if reference['type'] != 'commit':
        raise ValueError('Expected a tag pointing directly to a commit')
    value = {'schema': 1, 'upstream_repository': UPSTREAM, 'tag': tag,
             'sha': reference['sha'], 'tag_object': tag_object,
             'upstream_release_url': release['html_url'], 'published_at': release['published_at'],
             'claim': None, 'variant': 'light', 'target': 'darwin-arm64',
             'release_tag': release_tag, 'packaging_revision': PACKAGING_REVISION,
             'distribution': 'no-developer-id-no-notarization'}
    if record.get('claimTag') or record.get('claimTagObject'):
        if record.get('commit') != value['sha']:
            raise ValueError('Upstream release annotation disagrees with its commit')
        value['claim'] = {'tag': record.get('claimTag'), 'object': record.get('claimTagObject')}
    return validate_manifest(value), tag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    value, tag = resolve(os.environ.get('REQUESTED_TAG', '').strip(), os.environ['GITHUB_REPOSITORY'],
                         validation_only=os.environ.get('VALIDATION_ONLY') == 'true')
    github_output(build='true' if value else 'false', tag=tag)
    if value:
        write_json(args.output, value)
        summary(f'Build **{tag}** from `{value["sha"]}` — Mac ARM64, Light, no Apple credentials.')
    else:
        summary(f'**{tag}** already has a complete published release. No Mac runner needed.')


if __name__ == '__main__':
    main()
