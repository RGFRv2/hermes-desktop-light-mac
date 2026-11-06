# Contribution workflow

- Track each code change in a GitHub issue, or refer to an existing issue covering the change.
- Work on a dedicated branch and open a pull request linked to that issue.
- Do not push code changes directly to `main`.
- Run relevant tests and the native Mac package checks before merging a packaging change.
- Describe the behavior, validation and remaining limitations in the PR.
- Keep upstream Hermes source tags and commits intact. Record any artifact processing separately.
- Never replace the bytes of an already published release. Use a new packaging revision for a rebuilt installer.
- These builds use ad-hoc signing without Apple credentials. Do not add Apple secrets or notarization requirements unless requested.
- Use English for default public documentation and release notes. Keep the French companion documents in sync and linked from the English versions.
- Keep personal machine details, credentials and private Gateway configuration out of tracked files and public reports.
