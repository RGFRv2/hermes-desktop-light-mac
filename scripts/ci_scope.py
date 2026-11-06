"""Select native validation while keeping automation checks on every PR."""
import os
from common import SHA, github_output, run


def requires_native(base, head):
    if not SHA.fullmatch(base or '') or not SHA.fullmatch(head or ''):
        raise ValueError('Expected exact PR base and head commit SHAs')
    paths = run(['git', 'diff', '--name-only', '-z', base, head, '--']).split('\0')
    return any(path.startswith(('scripts/', 'tests/', 'notices/', '.github/workflows/')) for path in paths)


if __name__ == '__main__':
    native = (os.environ.get('GITHUB_EVENT_NAME') != 'pull_request'
              or requires_native(os.environ.get('PR_BASE'), os.environ.get('PR_HEAD')))
    github_output(native=str(native).lower())
