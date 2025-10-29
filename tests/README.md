# Info & Quick Reference for `pytest`

## Commands

*Note*: To run a test, make sure that you are currently in the repo's source directory!

### Running all Test Files

**Command**: `pytest`
> The default command to run all pytests

### Running a Specific Test File

**Command**: `pytest test/[test-file.py]`

> Runs only the specified test file.

### Flags
You can mix & match flags and append them after the `pytest` command to modify how the tests are ran.

**Example**: `pytest -s -q`
****

**Flag**: `-s`

> This tells pytest not to capture stdout/stderr, so `print()` statements are in your test functions appear in the console.

**Flag**: `-q`

> Runs tests in "quiet" mode, which reduces the amount of output that gets printed to the console.

**Flag**: `v`

> Runs tests in "verbose" mode, which shows each function's result.

Example: `pytest tests/test_analyzer.py` returns
``` txt
======================================================= test session starts =======================================
cachedir: .pytest_cache
rootdir: /workspaces/capstone-project-team-18
collected 3 items

tests/test_analyzer.py::test_base_file_analyzer_analyze_returns_filereport_with_core_stats PASSED           [ 33%]
tests/test_analyzer.py::test_base_file_analyzer_nonexistent_file_logs_and_returns_empty PASSED              [ 66%]
tests/test_analyzer.py::test_text_file_analyzer_analyze_raises_unimplemented PASSED                         [100%]
======================================================== 3 passed in 0.01s =======================================
```