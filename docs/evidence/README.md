# Verification evidence

These are dated measurements of synthetic tests. The public POC includes a successful recorded console action and an unresolved native bridge startup failure in a later test run. Read each report's measurement time and selected suites before drawing a conclusion.

## For whoever builds this

- `validation-macos-baseline.json`: earlier run, with 51 unit, 11 HTTP, 4 macOS native, and 1 live local-model test passing.
- `validation-macos.json`: publication rerun, with 51 unit and 11 HTTP tests passing, 1 of 4 native tests passing, and 4 errors across the remaining native/model cases. These errors were native bridge timeouts before completion.
- `validation-linux.json`: isolated Linux X11 run, with 51 unit, 11 HTTP, and 2 native fixture tests passing.
- `operator-console.png`: synthetic screenshot with a real pending local-model click; zero actions had executed before approval.

The saved measurement script is `scripts/verify.py`; reports record the source suites, unit, scope, timestamp, skips, failures, and errors. Re-run it to obtain current evidence. CI uses fake drivers for core checks and does not establish native support. Windows native verification remains unperformed.

Decisions still needed: the maintainer can investigate the fresh-process bridge timeout. A contributor with an interactive Windows desktop can verify the native Windows test.
