# Contributing

English · [Français](CONTRIBUTING.fr.md)

This repository maintains unofficial macOS Light build automation. Report application or Gateway bugs to [upstream Hermes](https://github.com/NousResearch/hermes-agent) if they reproduce independently of this packaging.

Use Python 3.12 to match CI; Python 3.12 or newer is required. Apple’s system Python may be older.

1. Open or reference an issue describing the problem and expected behavior.
2. Use a dedicated branch and open a PR linked to the issue.
3. Update both README languages when user-facing behavior changes.
4. Run `python3.12 -m unittest discover -s tests -v`.
5. Wait for relevant CI checks before merging. Packaging changes require native macOS validation.

English is the default documentation language. French reports and contributions are welcome.

Keep upstream source revisions intact and record artifact processing separately. Increment `PACKAGING_REVISION` if an installer changes; never overwrite published binaries. Documentation-only changes do not require rebuilding an existing installer.

Do not include API keys, certificates, Gateway credentials, private addresses or unredacted personal logs. See [SECURITY.md](SECURITY.md) and [AGENTS.md](AGENTS.md).

## Schedule maintenance

In public repositories, GitHub may disable scheduled workflows after 60 days without repository activity. If automatic release checks stop, verify that the workflow is still enabled. [GitHub schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
