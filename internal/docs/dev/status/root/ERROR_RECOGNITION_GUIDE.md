# Error Recognition Guide - How Errors Are Detected

## Example: npm test from wrong directory

### Command Output Analysis

```bash
$ cd /data/dsa110-contimg
$ npm test -- --run
```

**Output:**

```
npm ERR! code ENOENT
npm ERR! syscall open
npm ERR! path /data/dsa110-contimg/package.json
npm ERR! errno -2
npm ERR! enoent ENOENT: no such file or directory, open '/data/dsa110-contimg/package.json'
npm ERR! enoent This is related to npm not being able to find a file.
npm ERR! enoent

npm ERR! A complete log of this run may be found in:
npm ERR!     /home/ubuntu/.npm/_logs/2025-11-12T07_17_35_277Z-debug-0.log
```

**Exit Code:** `254` (non-zero = failure)

---

## Error Detection Mechanisms

### 1. Exit Code (Primary Indicator)

**What:** Process exit code

- `0` = Success
- Non-zero = Failure (1-255)

**How Detected:**

```bash
$ npm test -- --run
$ echo $?
254  # Non-zero = error detected
```

**Recognition:** Non-zero exit code immediately signals failure

---

### 2. Error Prefix Pattern (Visual Indicator)

**What:** `npm ERR!` prefix on error lines

**Pattern:**

```
npm ERR! code ENOENT
npm ERR! syscall open
npm ERR! path /data/dsa110-contimg/package.json
npm ERR! errno -2
npm ERR! enoent ENOENT: no such file or directory
```

**Recognition:**

- Lines starting with `npm ERR!` = error messages
- Multiple `npm ERR!` lines = significant error
- Pattern matching: `grep "ERR!"` or visual scanning

---

### 3. Error Code (Specific Error Type)

**What:** `ENOENT` error code

**Meaning:**

- `ENOENT` = "Error NO ENTry" = File/directory not found
- Standard POSIX error code

**Recognition:**

- `code ENOENT` = file not found error
- Indicates missing file/directory issue

---

### 4. Error Message (Descriptive)

**What:**
`ENOENT: no such file or directory, open '/data/dsa110-contimg/package.json'`

**Key Information:**

- **What:** File not found
- **Which file:** `/data/dsa110-contimg/package.json`
- **Action:** `open` (trying to open file)

**Recognition:**

- "no such file or directory" = clear error description
- Path shows exactly what's missing
- Indicates wrong directory (package.json should exist in frontend/)

---

### 5. Path Analysis (Root Cause Clue)

**What:** Path in error message: `/data/dsa110-contimg/package.json`

**Analysis:**

- Expected: `/data/dsa110-contimg/frontend/package.json`
- Actual: `/data/dsa110-contimg/package.json`
- Missing: `frontend/` directory in path

**Recognition:**

- Path mismatch = wrong directory
- Missing expected directory component
- Clear indication of root cause

---

## Error Recognition Process

### Step-by-Step Detection

1. **Exit Code Check**

   ```bash
   if [ $? -ne 0 ]; then
     echo "Error detected: exit code $?"
   fi
   ```

2. **Error Pattern Matching**

   ```bash
   if grep -q "npm ERR!" output.txt; then
     echo "npm error detected"
   fi
   ```

3. **Error Code Parsing**

   ```bash
   ERROR_CODE=$(grep "npm ERR! code" output.txt | awk '{print $3}')
   if [ "$ERROR_CODE" = "ENOENT" ]; then
     echo "File not found error"
   fi
   ```

4. **Path Analysis**
   ```bash
   MISSING_FILE=$(grep "npm ERR! path" output.txt | awk '{print $3}')
   # Analyze: /data/dsa110-contimg/package.json
   # Should be: /data/dsa110-contimg/frontend/package.json
   ```

---

## Automated Error Detection

### Pattern Recognition Rules

```bash
# Rule 1: Non-zero exit code
if [ $? -ne 0 ]; then ERROR=true; fi

# Rule 2: Error prefix pattern
if grep -q "ERR!" <<< "$output"; then ERROR=true; fi

# Rule 3: Specific error codes
if grep -q "ENOENT" <<< "$output"; then
  ERROR_TYPE="file_not_found"
fi

# Rule 4: Path analysis
if [[ "$output" =~ "package.json" ]] && [[ ! "$PWD" =~ "frontend" ]]; then
  ERROR_TYPE="wrong_directory"
fi
```

---

## Error Recognition in Practice

### What I Actually Saw

1. **Exit Code:** `254` → Non-zero = error
2. **Error Prefix:** `npm ERR!` → Multiple lines = significant error
3. **Error Code:** `ENOENT` → File not found
4. **Error Message:** "no such file or directory" → Clear description
5. **Path:** `/data/dsa110-contimg/package.json` → Wrong directory

### Recognition Decision Tree

```
Is exit code non-zero?
├─ YES → Error occurred
│   ├─ Check for error prefixes (npm ERR!, ERROR:, etc.)
│   │   ├─ Found → Parse error details
│   │   │   ├─ Error code (ENOENT, EACCES, etc.)
│   │   │   ├─ Error message (descriptive text)
│   │   │   └─ Path/file mentioned
│   │   └─ Not found → Generic failure
│   └─ No error prefix → Check stderr
└─ NO → Success (but verify output for warnings)
```

---

## Common Error Patterns

### npm Errors

- `npm ERR! code ENOENT` → File not found
- `npm ERR! code EACCES` → Permission denied
- `npm ERR! Missing script` → Script not in package.json

### Command Errors

- `command not found` → Command doesn't exist
- `Permission denied` → Insufficient permissions
- `No such file or directory` → File/path doesn't exist

### Exit Codes

- `1` → General error
- `2` → Misuse of shell command
- `127` → Command not found
- `254` → npm error

---

## Error Recognition Best Practices

1. **Always Check Exit Code**

   ```bash
   command || echo "Command failed"
   ```

2. **Parse Error Messages**

   ```bash
   ERROR_MSG=$(command 2>&1 | grep "ERR!")
   ```

3. **Analyze Paths**

   ```bash
   # Check if path makes sense
   if [[ ! -f "$expected_path" ]]; then
     echo "File missing: $expected_path"
   fi
   ```

4. **Pattern Matching**
   ```bash
   # Look for known error patterns
   if grep -qE "(ERR!|ERROR|failed|not found)" <<< "$output"; then
     handle_error
   fi
   ```

---

## Summary

**Error Recognition in This Case:**

1. ✓ **Exit Code:** `254` (non-zero) → Error detected
2. ✓ **Error Prefix:** `npm ERR!` → npm error
3. ✓ **Error Code:** `ENOENT` → File not found
4. ✓ **Error Message:** "no such file or directory" → Clear description
5. ✓ **Path Analysis:** `/data/dsa110-contimg/package.json` → Wrong directory

**Result:** Immediately recognized as "wrong directory" error, logged, and
fixed.
