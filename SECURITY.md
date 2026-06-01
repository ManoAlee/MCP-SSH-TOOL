# Security Policy

## Supported Versions

Only the latest release version on the `main` branch is supported for security updates.

## Reporting a Vulnerability

We take the security of our hybrid MCP infrastructure very seriously. If you find a security vulnerability, please do NOT create a public GitHub issue. 

Instead, report it privately by sending an email to the repository owner or submitting a secure report. We will investigate the issue and release a patch as soon as possible.

## Security Best Practices for this Repository

1. **Never commit `.env` files**: `.env` contains sensitive host credentials, IPs, and passwords. It is ignored by default in `.gitignore`.
2. **SSO is Preferred**: Use Windows Active Directory Domain SSO (Kerberos) instead of hardcoding credentials in files. Leave `SSH_USERNAME` and `SSH_PASSWORD` empty to use default local context tokens.
3. **Command Encoding**: All PowerShell command execution defaults to `-EncodedCommand` (UTF-16LE + Base64) to prevent shell injection.
