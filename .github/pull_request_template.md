# Pull Request

## Description

<!-- Describe your changes -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation
- [ ] Test improvement
- [ ] Other (please describe)

## Environment Setup

- [ ] Ran `./scripts/setup-dev.sh` after cloning
- [ ] Verified environment with `./scripts/check-environment.sh`
- [ ] Using casa6 Python environment (not system Python)
- [ ] All dependencies installed

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All tests passing
- [ ] Tests follow organization in `docs/concepts/TEST_ORGANIZATION.md`

## Code Review Checklist

### Anti-Pattern Prevention

- [ ] No dismissive language ("doesn't matter", "ignore", "edge case")
- [ ] No rationalizing language ("works in practice", "probably fine")
- [ ] Edge cases handled
- [ ] Error cases tested
- [ ] No magic numbers (use named constants)
- [ ] No code duplication
- [ ] Complexity is reasonable

### Code Quality

- [ ] Code follows project style guidelines
- [ ] Comments explain "why", not "what"
- [ ] Functions are focused and single-purpose
- [ ] No hardcoded values
- [ ] Error handling is appropriate
- [ ] Logging is appropriate

### Testing

- [ ] Tests cover happy path
- [ ] Tests cover error cases
- [ ] Tests cover edge cases
- [ ] Tests are not brittle (no sleeps, timeouts)
- [ ] Tests are isolated and independent

### Documentation

- [ ] Code is self-documenting
- [ ] Complex logic is commented
- [ ] README/docs updated if needed
- [ ] API changes documented
- [ ] **No markdown files in root directory** (must be in docs/ structure)
- [ ] Documentation follows structure in `docs/DOCUMENTATION_QUICK_REFERENCE.md`
- [ ] New features have documentation
- [ ] Breaking changes are documented

## Related Issues

<!-- Link to related issues -->

## Additional Notes

<!-- Any additional information for reviewers -->
