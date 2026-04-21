# Security Policy

## Supported versions

Etz Chaim AI is currently in beta (v0.1.x). Security fixes are applied to the
latest minor version only. Pre-1.0 API stability is not guaranteed but security
vulnerabilities are treated as priority bugs.

| Version | Supported |
|:-------:|:---------:|
| 0.2.x   | Yes (current) |
| 0.1.x   | Community support only — upgrade recommended |
| < 0.1   | No (development builds) |

## Reporting a vulnerability

Please DO NOT open a public GitHub issue for security-related reports.

Instead, please email : `security@etz-chaim-ai.example` (placeholder — to be
replaced with a real monitored address before v1.0).

For now, open a GitHub issue marked `[SECURITY]` with minimal technical detail
and we will contact you through a private channel for the full report.

Include in your report :

- A description of the vulnerability.
- Steps to reproduce (proof of concept if possible).
- Impact assessment (what an attacker could do).
- Suggested remediation if known.

## Response timeline

- Acknowledgment of receipt : within 72 hours.
- Initial assessment : within 7 days.
- Fix or mitigation plan : within 30 days for critical issues.

## Scope

In scope :

- Code under `bridge/`, `mazalengine/`, `partzufim/`, `explorationengine/`,
  `causalengine/`, `insightforge/`, `daemon.py`, `main.py`, `ohr_yashar.py`.
- Web dashboard (`web/`).
- Installation and CI scripts.

Out of scope :

- Third-party dependencies (report directly to upstream).
- Sandbox experiments (`sandbox/`) and research code (`halom/`).
- Documentation corrections (open a regular issue instead).

## Disclosure policy

We follow coordinated disclosure. Reporters who allow us time to fix a
vulnerability will be credited in the release notes (unless anonymity is
requested).
