# Security

Treat this project as a local learning POC. It has no production healthcare validation or compliance certification. Run it against the supplied synthetic app first. Every model action requires review, and a posted input event does not prove a correct saved outcome.

The console binds to loopback. Do not expose it through a tunnel, reverse proxy, or public network. Local model inference does not prove that the rest of the computer is isolated from the network. Screenshots can contain whatever the target application displays.

Report reproducible problems with synthetic examples. Never post real patient screenshots, credentials, personal information, or exploit details in a public issue. For a suspected security vulnerability, use private contact information offered on the repository maintainer's GitHub profile before sharing details.

## For whoever builds this

The runner checks its app allowlist, target identity, foreground, window geometry, exact screenshot freshness, single-use approval, review expiry, and bounded actions. These checks catch specific input-routing and review problems. They do not verify patient identity, authorize clinical decisions, or prove resistance to screenshot prompt injection. The prompt instructs the model to ignore embedded instructions; that is not an independently validated boundary.

The journal contains metadata only; screenshots, task text, OCR, and typed text remain in process memory. Public demo media contains only synthetic fixture data. Audit that boundary again before recording any additional application.

Decisions still needed: deployment outside a local synthetic test requires an owner to establish authorized workflow scope, patient-data handling, vendor terms, security review, and operational support.
