# Security policy

## Supported versions

aviscape is pre-1.0. Security fixes go into the latest release and `main`
only.

| Version | Supported |
| :-- | :-- |
| `main` and the latest release | yes |
| older releases | no |

## Reporting a vulnerability

Please report vulnerabilities **privately** through GitHub's private
vulnerability reporting: open the repository's **Security** tab and choose
**Report a vulnerability**. Do not open a public issue.

Include what you found, how to reproduce it, and what an attacker could do
with it. You can expect an acknowledgement within 7 days and a status update
within 14 days. Once a fix is released, the advisory is published with credit
to you, unless you prefer otherwise.

## Scope

In scope: the code in this repository, its container images, Helm charts and
GitHub Actions workflows.

Out of scope: the third-party services aviscape reads from (Locus Sonus,
Open-Meteo, GBIF, BirdWeather, xeno-canto); please report issues with those
to their operators.

## Secrets

If you find a credential in the repository or its history, report it the
same way. It will be revoked first and then removed from the history.
