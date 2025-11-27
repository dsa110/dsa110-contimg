# SonarLint Language Server Fails to Start

**Date:** 2025-11-27  
**Severity:** Medium  
**Status:** Mitigated

## Issue

VS Code Output shows the extension cannot establish the Java-based language
server:

```
[Error - 1:48:46 PM] SonarLint Language Server client: couldn't create connection to server.
[object Object]
```

## Impact

- SonarLint does not analyze Python/TypeScript files in this workspace.
- No in-editor highlighting for code smells or security issues.
- Pre-commit quality checks lose an early feedback loop.

## Root Cause

The remote VS Code server session does not expose a default `JAVA_HOME`, so the
SonarLint extension cannot locate a JVM when it spawns the Java language server.
Although `java` exists on the PATH, the extension host launches in a minimal
environment and fails before producing a helpful stack trace, resulting in
`[object Object]`.

## Fix

1. **Pin the language server JRE path**

   Added `.vscode/settings.json` with:

   ```json
   {
     "sonarlint.ls.javaHome": "/usr/lib/jvm/java-17-openjdk-amd64",
     "sonarlint.trace.server": "messages",
     "sonarlint.output.showVerboseLogs": true
   }
   ```

   This forces SonarLint to use the system OpenJDK 17 that is already installed
   on the remote host and enables verbose logs for future diagnostics.

2. **Verify Java availability**

   ```bash
   java -version
   readlink -f $(which java)
   ```

   Expected binary path: `/usr/lib/jvm/java-17-openjdk-amd64/bin/java`.

3. **Restart the extension**
   - Run the VS Code command: `SonarLint: Restart SonarLint language server`.
   - If symptoms persist, reload the window (`Developer: Reload Window`).

4. **Optional cache reset**

   If the error repeats after the steps above, delete `~/.sonarlint/plugins` and
   let the extension re-download the analyzers.

## Validation

- After the settings update, trigger
  `SonarLint: Analyze all files in workspace`.
- The SonarLint Output panel should show
  `Connected to SonarLint Language Server` with no follow-up error messages.
- Open any Python/TypeScript file and confirm issues are highlighted inline.

## References

- File: `.vscode/settings.json`
- Vendor note:
  [SonarLint for VS Code - language server requirements](https://community.sonarsource.com/t/sonarlint-language-server-requirements/48080)
