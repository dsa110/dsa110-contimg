# Linear Integration - Quick Start

## 5-Minute Setup

1. **Get your Linear API key:**
   - Go to Linear → Settings → API → Personal API keys
   - Create new key → Copy (starts with `lin_api_`)

2. **Get your team key:**
   - Usually a short code like `ENG`, `PROD`, `DEV`
   - Found in team URL or settings

3. **Create config file:**
   ```bash
   cp .linear_config.json.example .linear_config.json
   nano .linear_config.json
   ```
   Add your credentials:
   ```json
   {
     "api_key": "lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
     "team_key": "ENG"
   }
   ```

4. **Test the connection:**
   ```bash
   make sync-linear-dry-run
   ```

5. **Sync your TODO items:**
   ```bash
   make sync-linear
   ```

That's it! Your TODO items will be created as Linear issues and linked back to TODO.md.

---

## What Happens

- ✅ Unchecked TODO items → Linear issues
- ✅ Priority mapping: High/Medium/Low → Linear priorities
- ✅ Time estimates included in issue descriptions
- ✅ Linear issue IDs added to TODO.md automatically

---

## Need Help?

See `docs/LINEAR_INTEGRATION.md` for detailed documentation, troubleshooting, and advanced usage.

