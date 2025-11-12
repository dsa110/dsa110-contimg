# Troubleshooting Guide for Pipeline Stages

This guide helps diagnose and fix common issues when working with pipeline stages.

## Common Issues

### Issue: Stage Validation Fails

**Symptoms:**
- `validate()` returns `(False, error_message)`
- Stage doesn't execute
- Error message indicates missing inputs or invalid files

**Diagnosis:**
```python
stage = MyStage(config)
is_valid, error_msg = stage.validate(context)
if not is_valid:
    print(f"Validation failed: {error_msg}")
```

**Common Causes:**

1. **Missing Required Inputs**
   ```python
   # Problem: input_path not in context.inputs
   context = PipelineContext(config=config)
   
   # Solution: Add required inputs
   context = PipelineContext(
       config=config,
       inputs={"input_path": "/path/to/input"}
   )
   ```

2. **File Doesn't Exist**
   ```python
   # Problem: File path doesn't exist
   context = PipelineContext(
       config=config,
       inputs={"input_path": "/nonexistent/file"}
   )
   
   # Solution: Verify file exists
   from pathlib import Path
   input_path = Path("/path/to/input")
   if not input_path.exists():
       raise FileNotFoundError(f"Input file not found: {input_path}")
   ```

3. **Missing Dependencies from Previous Stage**
   ```python
   # Problem: Previous stage didn't produce required output
   context = PipelineContext(config=config)  # No ms_path
   stage = CalibrationStage(config)
   
   # Solution: Ensure previous stage executed successfully
   # Check that previous stage's outputs are in context
   assert "ms_path" in context.outputs
   ```

**Fix:**
- Check error message for specific missing input
- Verify file paths exist
- Ensure previous stages executed successfully
- Check context.outputs for required dependencies

### Issue: Stage Execution Fails

**Symptoms:**
- `execute()` raises exception
- Stage status is `FAILED`
- Error in logs

**Diagnosis:**
```python
try:
    result_context = stage.execute(context)
except Exception as e:
    print(f"Execution failed: {e}")
    import traceback
    traceback.print_exc()
```

**Common Causes:**

1. **External Dependency Failure**
   ```python
   # Problem: CASA function fails
   # Solution: Check CASA installation and data validity
   ```

2. **Insufficient Resources**
   ```python
   # Problem: Out of disk space or memory
   # Solution: Check disk space, reduce data size, or increase resources
   ```

3. **Invalid Data Format**
   ```python
   # Problem: Input data is corrupted or wrong format
   # Solution: Validate data before processing
   ```

**Fix:**
- Check logs for detailed error messages
- Verify external dependencies (CASA, databases)
- Check system resources (disk, memory)
- Validate input data format
- Review stage's `cleanup()` method for partial outputs

### Issue: Outputs Not Available to Next Stage

**Symptoms:**
- Next stage validation fails
- Missing outputs in context
- Stage chain breaks

**Diagnosis:**
```python
# Check outputs after stage execution
result_context = stage.execute(context)
print(f"Outputs: {list(result_context.outputs.keys())}")

# Check if expected output exists
if "expected_output" not in result_context.outputs:
    print("Expected output missing!")
```

**Common Causes:**

1. **Not Using `with_output()`**
   ```python
   # Problem: Mutating context directly
   context.outputs["key"] = value  # DON'T DO THIS
   
   # Solution: Use immutable update
   context = context.with_output("key", value)
   ```

2. **Output Key Mismatch**
   ```python
   # Problem: Output key doesn't match what next stage expects
   context = context.with_output("ms_path", "/path/to/ms")
   # Next stage expects "measurement_set_path"
   
   # Solution: Use consistent output keys
   # Check stage documentation for expected output keys
   ```

3. **Stage Failed Before Producing Output**
   ```python
   # Problem: Exception raised before output added
   # Solution: Ensure stage completes successfully
   # Check error handling and cleanup
   ```

**Fix:**
- Always use `context.with_output()` or `context.with_outputs()`
- Verify output keys match stage documentation
- Check that stage executed successfully
- Review stage's `validate_outputs()` method

### Issue: Context Immutability Violations

**Symptoms:**
- Unexpected behavior
- Side effects
- Difficult to debug

**Diagnosis:**
```python
# Verify immutability
original_context = PipelineContext(config=config)
new_context = stage.execute(original_context)

# Original should be unchanged
assert original_context is not new_context
assert "new_output" not in original_context.outputs
```

**Common Causes:**

1. **Mutating Context Directly**
   ```python
   # Problem: Modifying context in place
   context.outputs["key"] = value
   context.metadata["key"] = value
   
   # Solution: Always return new context
   return context.with_output("key", value)
   ```

2. **Sharing Mutable Objects**
   ```python
   # Problem: Sharing mutable objects between contexts
   shared_list = []
   context1 = context.with_output("list", shared_list)
   shared_list.append("item")  # Affects context1!
   
   # Solution: Use immutable data or create copies
   new_list = list(shared_list)
   context1 = context.with_output("list", new_list)
   ```

**Fix:**
- Never modify context directly
- Always use `with_output()` or `with_outputs()`
- Be careful with mutable objects in outputs
- Test immutability in tests

### Issue: Cleanup Not Working

**Symptoms:**
- Temporary files accumulate
- Disk space issues
- Resources not released

**Diagnosis:**
```python
# Check cleanup method exists and is called
assert hasattr(stage, "cleanup")
assert callable(stage.cleanup)

# Manually call cleanup
stage.cleanup(context)
```

**Common Causes:**

1. **Cleanup Not Implemented**
   ```python
   # Problem: No cleanup method
   # Solution: Implement cleanup() method
   def cleanup(self, context: PipelineContext) -> None:
       if "temp_file" in context.metadata:
           Path(context.metadata["temp_file"]).unlink()
   ```

2. **Cleanup Not Called on Failure**
   ```python
   # Problem: Cleanup only called on success
   # Solution: Ensure cleanup is called in finally block
   try:
       result = process()
   finally:
       stage.cleanup(context)
   ```

3. **Incorrect Cleanup Logic**
   ```python
   # Problem: Cleanup doesn't handle all cases
   # Solution: Clean up all temporary resources
   def cleanup(self, context: PipelineContext) -> None:
       # Clean up temp files
       # Close connections
       # Release locks
   ```

**Fix:**
- Implement `cleanup()` method for all stages
- Ensure cleanup is called on both success and failure
- Clean up all temporary resources
- Test cleanup in tests

### Issue: Circular Dependencies

**Symptoms:**
- Orchestrator fails to start
- Topological sort error
- Stages can't execute

**Diagnosis:**
```python
# Check for circular dependencies
stages = [
    StageDefinition("stage1", Stage1(), ["stage2"]),
    StageDefinition("stage2", Stage2(), ["stage1"]),  # Circular!
]

# Orchestrator should detect this
try:
    orchestrator = PipelineOrchestrator(stages)
except ValueError as e:
    print(f"Circular dependency detected: {e}")
```

**Common Causes:**

1. **Bidirectional Dependencies**
   ```python
   # Problem: Stage1 depends on Stage2, Stage2 depends on Stage1
   # Solution: Redesign to remove circular dependency
   # Split into three stages or remove one dependency
   ```

2. **Self-Dependency**
   ```python
   # Problem: Stage depends on itself
   StageDefinition("stage", Stage(), ["stage"])  # DON'T DO THIS
   
   # Solution: Remove self-dependency
   ```

**Fix:**
- Review stage dependencies
- Remove circular dependencies
- Redesign stage structure if needed
- Use dependency graph visualization

## Debugging Strategies

### 1. Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Check Context State

```python
def debug_context(context: PipelineContext):
    print(f"Inputs: {list(context.inputs.keys())}")
    print(f"Outputs: {list(context.outputs.keys())}")
    print(f"Metadata: {list(context.metadata.keys())}")
```

### 3. Test Stages Individually

```python
# Test each stage in isolation
stage = MyStage(config)
is_valid, error = stage.validate(context)
if is_valid:
    result = stage.execute(context)
    print(f"Outputs: {list(result.outputs.keys())}")
```

### 4. Use Test Fixtures

```python
@pytest.fixture
def test_context():
    return PipelineContext(
        config=test_config,
        inputs={"input_path": "/test/input"}
    )

def test_my_stage(test_context):
    stage = MyStage(test_config)
    result = stage.execute(test_context)
    assert "output" in result.outputs
```

### 5. Check Stage Documentation

- Review stage docstrings for expected inputs/outputs
- Check examples in documentation
- Review pipeline architecture documentation

## Getting Help

If you're still stuck:

1. **Check Logs**: Review pipeline logs for detailed error messages
2. **Review Documentation**: Check stage documentation and examples
3. **Run Tests**: Run unit/integration tests to see expected behavior
4. **Check Mind Palace**: Query Graphiti memory for related issues
5. **Review Patterns**: Check `docs/concepts/pipeline_patterns.md` for best practices

## Related Documentation

- [Pipeline Stage Architecture](../concepts/pipeline_stage_architecture.md)
- [Pipeline Patterns](../concepts/pipeline_patterns.md)
- [Testing Guide](testing.md)
- [Creating Pipeline Stages](create_pipeline_stage.md)
