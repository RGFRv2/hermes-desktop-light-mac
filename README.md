# Hermes Desktop Light for Mac

English · [Français](README.fr.md)

Unofficial **Hermes Desktop Light builds for Apple Silicon Macs**, packaged from stable releases of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

Light connects to an existing remote Hermes Gateway. The application **does not bundle the Hermes agent or a Python runtime**. This repository maintains the build automation; it is not an official Nous Research distribution.

[Download](https://github.com/RGFRv2/hermes-desktop-light-mac/releases/latest) · [Build status](https://github.com/RGFRv2/hermes-desktop-light-mac/actions/workflows/macos.yml) · [Report a bug](https://github.com/RGFRv2/hermes-desktop-light-mac/issues/new/choose)

## Compatibility

| Item | Scope |
|---|---|
| Architecture | ARM64, Apple Silicon (M1 and later) |
| Current CI | macOS 27, using GitHub's `xcode-27` ARM64 preview image |
| Application-declared minimum | Currently macOS 13.0; other OS versions have not been validated by this project |
| Connection | An existing remote Gateway |
| Updates | Download and replace the application manually |

Check each release's `build-manifest.json` for its actual source and environment.

## Install and update

1. Open the [latest release](https://github.com/RGFRv2/hermes-desktop-light-mac/releases/latest).
2. Download `HermesLight-X.Y.Z-mac-arm64.dmg`.
3. Open the disk image and drag **Hermes Light.app** into **Applications**.
4. Open the application and configure your remote Gateway.

For updates, quit Hermes Light before replacing the app. No local compilation is required. The app does not currently use this repository as an automatic update feed; the remote Gateway has its own update procedure.

Stable builds keep the same application identity. Earlier commit builds can use a separate settings folder; reconnect to the Gateway if switching from one of those builds. Back up settings before migrating profiles.

The ZIP is an alternative archive of the same application. Each release also provides `SHA256SUMS`, `build-manifest.json`, `validation.json` and release notes. Download the checksums alongside the installer and compare its matching entry with:

```sh
shasum -a 256 HermesLight-X.Y.Z-mac-arm64.dmg
```

### Signing and first launch

These builds have a complete **ad-hoc signature**, but **no Apple Developer ID certificate or notarization**. A valid ad-hoc signature checks package integrity; it does not establish an Apple-verified publisher. macOS may require approval in **System Settings → Privacy & Security** after the first launch attempt.

Only approve a build you trust. This project does not require disabling Gatekeeper globally. If macOS reports the app as damaged, report the release and consult its validation results before changing security settings. Checksums do not replace publisher verification.

## How builds work

- Checks for the latest official stable Hermes release run daily at **10:00 and 23:00, Europe/Paris time**, including daylight saving time changes. GitHub may delay scheduled runs.
- **Run workflow** accepts an optional upstream tag, such as `v0.23.0`.
- Native compilation is skipped when a complete release for the current packaging revision exists.
- The workflow verifies the exact upstream tag, commit and build-claim object where required, then builds the `light` variant from an unmodified checkout.
- Required notices are staged before nested code and bundles are signed inside-out. DMG and ZIP are created from the signed app.
- Publication requires integrity, ARM64 architecture, provenance, Light metadata, valid signatures inside both archives, required notices and native process startup with an isolated profile.
- PRs run automation tests without publishing; native validation runs when scripts, tests or workflows change. Interrupted publication leaves a retryable draft.

Tags such as **`vX.Y.Z-macos.N`** identify the Hermes version **X.Y.Z** and the Mac packaging revision **N**.

GitHub Actions dependencies use Node 24 and are pinned by SHA. The build's Node version is controlled separately by the upstream Hermes toolchain. Python and other compilation tools are build dependencies, not a runtime bundled into Light.

No personal GitHub token or Apple credentials are required. The temporary `GITHUB_TOKEN` is used automatically; only the publication job has `contents: write`. Runner availability, approval requirements and account limits follow GitHub's settings.

## License and attribution

This repository's automation is provided under the [MIT License](LICENSE). Hermes and redistributed dependencies retain their own copyright and license terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Built applications include redistribution notices.

Hermes and Nous Research names identify the upstream project. This community repository is not affiliated with, endorsed by or supported by Nous Research.

## References

- [Upstream Hermes](https://github.com/NousResearch/hermes-agent)
- [Desktop build documentation](https://github.com/NousResearch/hermes-agent/blob/main/apps/desktop/BUILDING.md)
- [GitHub runner images](https://github.com/actions/runner-images)
