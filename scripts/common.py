"""Small standard-library helpers shared by the build controller."""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

UPSTREAM = 'NousResearch/hermes-agent'
API = 'https://api.github.com'
TAG = re.compile(r'v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z')
SHA = re.compile(r'[a-f0-9]{40}\Z')
PACKAGING_REVISION = 3


def require_python(version=None):
    if (version or sys.version_info) < (3, 12):
        raise RuntimeError('Python 3.12 or newer is required; use python3.12 to match CI')


require_python()


def stable_version(tag):
    match = TAG.fullmatch(tag or '')
    if not match:
        raise ValueError(f'Expected an official stable tag vX.Y.Z, got {tag!r}')
    return tuple(int(value) for value in match.groups())


def distribution_tag(tag):
    stable_version(tag)
    return f'{tag}-macos.{PACKAGING_REVISION}'


def distribution_version(tag):
    match = re.fullmatch(r'(v\d+\.\d+\.\d+)(?:-macos\.([1-9]\d*))?', tag)
    if not match:
        raise ValueError('Invalid distribution release tag')
    return (*stable_version(match[1]), int(match[2] or 0))


def api(path, missing_ok=False):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'hermes-light-mac-builds',
               'X-GitHub-Api-Version': '2022-11-28'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    request = Request(API + path, headers=headers)
    try:
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    except HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        raise RuntimeError(f'GitHub API {error.code} for {path}') from error


def run(argv, cwd=None, env=None):
    return subprocess.check_output(argv, cwd=cwd, env=env, text=True).strip()


def find_release(repository, tag, get=api):
    """Draft releases may not be returned by /releases/tags before their tag exists."""
    found = get(f'/repos/{repository}/releases/tags/{tag}', missing_ok=True)
    if found:
        return found
    page = 1
    while True:
        releases = get(f'/repos/{repository}/releases?per_page=100&page={page}')
        for release in releases:
            if release['tag_name'] == tag:
                return release
        if len(releases) < 100:
            return None
        page += 1


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_manifest(value):
    stable_version(value.get('tag'))
    if value.get('upstream_repository') != UPSTREAM or not SHA.fullmatch(value.get('sha', '')):
        raise ValueError('Invalid upstream source identity')
    if not SHA.fullmatch(value.get('tag_object', '')):
        raise ValueError('Missing upstream tag object')
    if value.get('release_tag') is not None:
        if (value['release_tag'] != distribution_tag(value['tag'])
                or value.get('packaging_revision') != PACKAGING_REVISION):
            raise ValueError('Invalid packaging revision')
    claim = value.get('claim')
    if claim:
        if not re.fullmatch(r'rc\.[1-9]\d*-' + re.escape(value['tag']), claim.get('tag', '')):
            raise ValueError('Claim tag does not match release')
        if not SHA.fullmatch(claim.get('object', '')):
            raise ValueError('Invalid upstream claim object')
    return value


def github_output(**values):
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with Path(path).open('a') as stream:
            for name, value in values.items():
                stream.write(f'{name}={value}\n')


def summary(message):
    print(message)
    if path := os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(path).open('a') as stream:
            stream.write(message + '\n')
