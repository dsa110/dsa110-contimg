# Commit Message Format

## Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature change or bug fix)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, tooling)
- `perf`: Performance improvements
- `ci`: CI/CD changes
- `build`: Build system changes

## Scope (Optional)

Examples:

- `feat(frontend)`: Frontend feature
- `fix(api)`: API bug fix
- `docs(readme)`: README documentation
- `chore(deps)`: Dependency update

## Subject

- Use imperative mood ("add" not "added" or "adds")
- First line should be 50 characters or less
- No period at the end
- Capitalize first letter

## Body (Optional)

- Explain what and why, not how
- Wrap at 72 characters
- Can include multiple paragraphs

## Footer (Optional)

- Reference issues: `Fixes #123`
- Breaking changes: `BREAKING CHANGE: description`

## Examples

### Good

```
feat(frontend): add unified search component

Implements search across all consolidated pages with debouncing
and keyboard shortcuts.

Fixes #456
```

```
fix(api): handle missing calibration tables gracefully

Previously, missing calibration tables would cause pipeline to crash.
Now returns appropriate error message.

Closes #789
```

```
docs(readme): add quick start section

Makes setup instructions more prominent for new developers.
```

### Bad

```
fixed bug  # Too vague, no type
```

```
feat: Added new feature  # Wrong mood, missing scope
```

```
fix(api): handle missing calibration tables gracefully.  # Period at end
```

## Pre-commit Validation

The pre-commit hook checks for:

- Anti-patterns in commit messages (dismissive language)
- Does NOT enforce format (yet)

## Future Enhancement

Consider adding format enforcement to pre-commit hook if needed.

## Related Documentation

- `.cursor/rules/error-acknowledgment.mdc` - Error handling rules
- `docs/how-to/DEVELOPER_HANDOFF_WARNINGS.md` - Developer warnings
