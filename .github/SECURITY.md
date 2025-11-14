# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| develop | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **Email:** [jakobtfaber@gmail.com](mailto:jakobtfaber@gmail.com)
2. **Private Security Advisory:** Use GitHub's private security advisory feature

### What to Include

When reporting a vulnerability, please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Time

We will acknowledge receipt of your report within 48 hours and provide an
initial assessment within 7 days.

### Disclosure Policy

- We will work with you to understand and resolve the issue quickly
- We will not disclose the vulnerability publicly until a fix is available
- We will credit you for the discovery (if desired)

## Security Best Practices

### For Developers

1. **Never commit secrets:**
   - API keys
   - Passwords
   - Tokens
   - Private keys

2. **Use environment variables:**
   - Store secrets in `.env` files (not committed)
   - Use GitHub Secrets for CI/CD
   - Use secure secret management in production

3. **Keep dependencies updated:**
   - Review Dependabot PRs promptly
   - Update dependencies regularly
   - Check for known vulnerabilities

4. **Follow secure coding practices:**
   - Validate all input
   - Use parameterized queries
   - Implement proper authentication
   - Follow principle of least privilege

5. **Review code changes:**
   - All PRs require code review
   - Security-sensitive changes require additional review
   - Use security checklist in PR template

### Pre-commit Checks

Our pre-commit hook automatically checks for:

- Hardcoded secrets (basic pattern matching)
- Large files that might contain secrets
- Environment files that shouldn't be committed

### CI/CD Security

- All workflows use GitHub Secrets for sensitive data
- No secrets are logged or exposed in CI output
- Dependencies are scanned for vulnerabilities

## Known Security Considerations

### Python Environment

- Always use casa6 Python environment
- System Python is not supported and may have vulnerabilities

### Frontend

- All API calls use HTTPS
- No sensitive data stored in localStorage
- Environment variables prefixed with `VITE_` are exposed to client

### Backend

- API uses FastAPI security features
- Database connections use secure credentials
- File system access is restricted to specific directories

## Security Updates

Security updates are released as needed. Critical security fixes are released
immediately.

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [Python Security](https://python.readthedocs.io/en/stable/library/security_warnings.html)
