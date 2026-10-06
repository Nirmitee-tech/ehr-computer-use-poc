# Optional CI template

The repository ships the core test workflow as a template. The publishing credential could create the public repository but could not write GitHub Actions workflow files. No GitHub Actions result is claimed for this release.

## For whoever builds this

Copy `docs/ci/tests.yml` to `.github/workflows/tests.yml` using an account or credential authorized to manage workflows, then commit it. The template runs unit and HTTP integration checks with fake drivers on macOS, Windows, and Linux. Native desktop and Ollama tests require their own opted-in host validation.

Decisions still needed: the maintainer can enable the workflow when workflow access is available.
