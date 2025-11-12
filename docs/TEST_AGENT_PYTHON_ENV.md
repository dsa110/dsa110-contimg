# Test Prompt for New Agent

**Status:** ✅ VALIDATED - Test confirmed that updated `.cursorrules` works correctly (2025-11-12)

Copy and paste this prompt to a new agent session:

---

**Prompt:**

I need to verify the Python environment setup for this project. Please run the test script at `scripts/test_python_env.py` and show me the output. The script will check which Python executable is being used and verify that required packages are available.

---

**Expected Behavior:**

If the agent follows the `.cursorrules` file correctly, they should:
1. Use `/opt/miniforge/envs/casa6/bin/python` to run the script
2. Show output indicating casa6 is being used
3. Show that CASA tools and scientific packages are available

**If agent uses wrong Python:**
- They'll use `python3` or `python` instead
- The script will show "✗ NOT using casa6 environment"
- CASA imports will fail
- This indicates the agent didn't follow the `.cursorrules` requirement

---

**Alternative Test (More Explicit):**

If you want to be more explicit, use this prompt instead:

---

**Prompt (Explicit):**

Run the Python script at `scripts/test_python_env.py` and tell me which Python executable it reports using.

---

**What to Look For:**

✓ **Good:** Agent uses `/opt/miniforge/envs/casa6/bin/python` automatically  
✗ **Bad:** Agent uses `python3` or `python` (system Python)

**Test Results (2025-11-12):**
- ✅ Agent automatically used casa6 without explicit instruction
- ✅ All CASA imports successful
- ✅ All scientific packages available
- ✅ Test script passed completely

**Conclusion:** The updated `.cursorrules` format (concise, action-oriented, explicit prohibition) successfully guides agents to use casa6 automatically.

---

**Quick Test Command:**

You can also test manually:

```bash
# Should use casa6
/opt/miniforge/envs/casa6/bin/python scripts/test_python_env.py

# Should fail (if you want to verify failure case)
python3 scripts/test_python_env.py  # Will fail CASA imports
```

