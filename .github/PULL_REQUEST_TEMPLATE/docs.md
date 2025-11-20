# Documentation PR Template

Thank you for improving the docs. Please fill out the checklist to help
reviewers.

## Summary

- Purpose of this change:
- Primary audience (dev | ops | science | user):
- Scope (new page | update | restructure):

## Placement

- Path of the document(s):
- Doc type (concept | how-to | reference | tutorial | operations | dev):
- Confirm placement matches the decision tree in
  `docs/DOCUMENTATION_QUICK_REFERENCE.md`: [ ]

## Naming & Metadata

- Filenames use lowercase_with_underscores and avoid dates/special chars: [ ]
- Front matter/metadata present with fields (status, owner, audience, tags): [ ]
- Title, last_updated/date fields set appropriately: [ ]

## Navigation & Cross‑Links

- If adding a new page, `mkdocs.yml` nav updated (include diff in PR): [ ]
- “See also” links added to related Concepts/How‑To/Reference pages: [ ]
- Backlinks added from referenced pages when appropriate: [ ]

## Diagrams & Assets

- Mermaid diagrams render locally (`mkdocs serve`) without syntax errors: [ ]
- Considered special characters; sanitized per
  `docs/javascripts/mermaid-init.js`: [ ]
- Images/attachments placed under `docs/images/` or page‑local folder and
  referenced with relative paths: [ ]

## Verification

- Built docs locally with `mkdocs build --strict`: [ ]
- Checked links (internal/external) locally or rely on CI link check: [ ]
- If code snippets included, ran them or marked clearly as illustrative: [ ]

## Notes for Reviewers

- Breaking changes or relocations to existing pages:
- Follow‑up issues or TODOs (if any):

---

### PR Checklist (maintainers)

- [ ] Correct placement per quick reference
- [ ] Naming rules followed
- [ ] Front matter complete (status, owner, audience, tags)
- [ ] Nav maintained and consistent
- [ ] Cross‑links present
- [ ] Mermaid diagrams render
- [ ] `mkdocs build --strict` passes in CI
- [ ] Link checker passes (or justified exceptions)
