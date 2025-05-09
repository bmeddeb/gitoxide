"""
Configuration for pytest.
"""
import pytest
import time

# The pytest_plugins configuration has been moved to the top-level conftest.py
# as required by newer versions of pytest


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Print test name and docstring at the start of each test."""
    # Get the module name (file), class name, and test name
    module_name = item.module.__name__
    class_name = item.cls.__name__ if item.cls else "None"
    test_name = item.name
    test_doc = item.obj.__doc__ or "No docstring provided"

    # Format the test information
    print(f"\n{'='*80}")
    print(f"RUNNING TEST: {module_name}.{class_name}.{test_name}")
    print(f"DESCRIPTION: {test_doc.strip()}")
    print(f"START TIME: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    """Print test completion message."""
    # Get the module name (file), class name, and test name
    module_name = item.module.__name__
    class_name = item.cls.__name__ if item.cls else "None"
    test_name = item.name

    # Format the test completion information
    print(f"\n{'-'*80}")
    print(f"COMPLETED: {module_name}.{class_name}.{test_name}")
    print(f"END TIME: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'-'*80}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        # Get the module name (file), class name, and test name
        module_name = item.module.__name__
        class_name = item.cls.__name__ if item.cls else "None"
        test_name = item.name

        # Format the test result
        status = "PASSED" if report.passed else "FAILED" if report.failed else "SKIPPED"
        print(f"\nRESULT: {status} - {module_name}.{class_name}.{test_name}")

        # If the test failed, print the error information
        if report.failed:
            if hasattr(report, "longrepr"):
                print(f"ERROR: {report.longreprtext}")
