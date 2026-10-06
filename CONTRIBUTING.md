# Contributing

Keep this project useful as a small, reproducible desktop computer-use POC. Changes should make observed behavior easier to test or explain. Use synthetic data in all examples and artifacts.

Describe the visible problem, the resulting behavior, and any limitation the evidence leaves open. Keep native OS checks separate from fake-driver tests and model tests. A model proposal is a candidate action until an operator reviews it.

## For whoever builds this

Clone the repository and follow the platform setup in README.md. Work in a branch. Add both a unit test for changed logic and an integration or UI test for its visible behavior. Move inaccessible logic into a testable module if needed. Run `python3 scripts/verify.py` for core tests. Native suites are opt-in and take control of the synthetic fixture; follow the commands and requirements in README.md.

Before submitting a change, run a secret scan and inspect the files and screenshots included. Exclude runtime journals, local recordings of other apps, credentials, personal data, and model weights. Tests and documentation should say what each check actually establishes. Do not add healthcare readiness or application compatibility claims without scoped evidence.

Decisions still needed: the maintainer can confirm the scope of a proposed feature. Contributors with an interactive Windows test host can help verify the shipped native Windows test.
