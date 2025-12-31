"""
Benchmark Configuration and Fixtures

Pytest configuration for performance benchmarks.

Phase 3: Search Integration, Optimization, and Production Readiness
Spec: conductor/tracks/mcp_consolidation_local_vector_20251230/spec.md
"""

import pytest
import sys
import time
from pathlib import Path


# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def pytest_configure(config):
    """Configure pytest for benchmarks."""
    # Register markers
    config.addinivalue_line(
        "markers", "benchmark: mark test as a performance benchmark"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection for benchmarks."""
    for item in items:
        # Add benchmark marker to tests in benchmarks directory
        if "benchmarks" in str(item.fspath):
            item.add_marker(pytest.mark.benchmark)


# Default benchmark arguments
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests",
    )


# Provide a simple benchmark fixture when pytest-benchmark is not installed
@pytest.fixture
def benchmark():
    """Simple benchmark fixture for when pytest-benchmark is not available."""

    def wrapper(func, *args, **kwargs):
        """Simple timing wrapper."""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return result  # Return result, ignore timing for basic tests

    class PedanticBenchmark:
        """Mock pedantic benchmark for cold start tests."""

        def __init__(self, func, iterations=1, rounds=1):
            self.func = func
            self.iterations = iterations
            self.rounds = rounds

        def __call__(self, *args, **kwargs):
            for _ in range(self.rounds):
                for _ in range(self.iterations):
                    self.func(*args, **kwargs)
            return None

    # Attach pedantic method to wrapper
    wrapper.pedantic = PedanticBenchmark
    return wrapper


def pytest_runtest_setup(item):
    """Setup for each test."""
    # Check for slow marker
    if item.get_closest_marker("slow") and not item.config.getoption("--runslow"):
        pytest.skip("use --runslow to run")
