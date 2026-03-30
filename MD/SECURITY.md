# Security Policy

## Before Publishing

- Do not commit `.env` files or any credential-bearing config.
- Use the example env files in the repo as templates only.
- Remove generated bundles, local build outputs, and virtual environments from commits.
- Store production secrets in your deployment platform secret manager or GitHub Actions secrets.

## Credential Handling

- Frontend code must never contain client secrets.
- Backend secrets must be provided through environment variables at deploy time.
- If credentials were ever stored in this workspace, rotate them before publishing.

## Reporting

If you discover a security issue in this project, report it privately to the maintainers rather than opening a public issue with exploit details.
