#!/usr/bin/env python3
"""
Diagnostic script to test the search_code_advanced tool and identify issues.
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index_mcp.search.zoekt import ZoektStrategy
from code_index_mcp.search_utils import SearchBackendSelector, BackendHealthChecker
from code_index_mcp.storage.dal_factory import get_dal_instance

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_zoekt_availability():
    """Test if zoekt is available on the system."""
    print("=== Testing Zoekt Availability ===")

    zoekt = ZoektStrategy()
    is_available = zoekt.is_available()

    print(f"Zoekt available: {is_available}")

    if is_available:
        info = zoekt.get_index_info()
        print(f"Zoekt path: {info.get('zoekt_path')}")
        print(f"Zoekt index path: {info.get('zoekt_index_path')}")
        print(f"Index directory: {info.get('index_dir')}")
        print(f"Index exists: {info.get('index_exists')}")
        print(f"Index initialized: {info.get('index_initialized')}")
    else:
        print("Zoekt is not available on this system")

    return is_available

def test_dal_backend():
    """Test the DAL backend configuration."""
    print("\n=== Testing DAL Backend ===")

    try:
        dal = get_dal_instance()
        print(f"DAL instance created: {type(dal)}")

        if dal and hasattr(dal, 'search'):
            print(f"DAL has search attribute: {type(dal.search)}")

            # Test backend selection
            search_backend = SearchBackendSelector.get_search_backend(dal)
            print(f"Selected search backend: {search_backend}")

            if search_backend:
                backend_type = SearchBackendSelector._get_backend_type(search_backend)
                print(f"Backend type: {backend_type}")

                # Test backend health
                health = BackendHealthChecker.check_backend_health(search_backend)
                print(f"Backend health: {health}")
            else:
                print("No search backend available")
        else:
            print("DAL does not have search attribute")

        return dal, search_backend if 'search_backend' in locals() else None

    except Exception as e:
        print(f"Error testing DAL backend: {e}")
        return None, None

def test_zoekt_index_creation():
    """Test zoekt index creation."""
    print("\n=== Testing Zoekt Index Creation ===")

    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")

    zoekt = ZoektStrategy()

    # Test index creation
    success = zoekt._ensure_index_exists(current_dir)
    print(f"Index creation successful: {success}")

    if success:
        info = zoekt.get_index_info()
        print(f"Index files: {info.get('index_files', [])}")
        print(f"Index file count: {info.get('index_file_count', 0)}")
        print(f"Index corrupted: {info.get('index_corrupted', False)}")

    return success

def test_zoekt_search():
    """Test zoekt search functionality."""
    print("\n=== Testing Zoekt Search ===")

    current_dir = os.getcwd()
    zoekt = ZoektStrategy()

    # Ensure index exists
    if not zoekt._ensure_index_exists(current_dir):
        print("Failed to create index, cannot test search")
        return False

    # Test search for "Hello, World!"
    try:
        results = zoekt.search(
            pattern="Hello, World!",
            base_path=current_dir,
            case_sensitive=False
        )

        print(f"Search results count: {len(results)}")
        for file_path, matches in results.items():
            print(f"  {file_path}: {len(matches)} matches")
            for line_num, line_content in matches:
                print(f"    Line {line_num}: {line_content.strip()}")

        return len(results) > 0

    except Exception as e:
        print(f"Error during zoekt search: {e}")
        return False

def test_file_content():
    """Test if test file contains expected content."""
    print("\n=== Testing File Content ===")

    test_file = "test_hello_world.py"

    if not os.path.exists(test_file):
        print(f"Test file {test_file} does not exist")
        return False

    try:
        with open(test_file, 'r') as f:
            content = f.read()

        print(f"File content length: {len(content)} characters")
        print("File content:")
        print(content)

        # Check for "Hello, World!"
        has_hello_world = "Hello, World!" in content
        print(f"Contains 'Hello, World!': {has_hello_world}")

        return has_hello_world

    except Exception as e:
        print(f"Error reading test file: {e}")
        return False

def main():
    """Run all diagnostic tests."""
    print("Search Diagnostic Tool")
    print("=" * 50)

    # Test file content first
    file_ok = test_file_content()

    # Test zoekt availability
    zoekt_available = test_zoekt_availability()

    # Test DAL backend
    dal, search_backend = test_dal_backend()

    # Test zoekt index creation
    if zoekt_available:
        index_ok = test_zoekt_index_creation()

        # Test zoekt search
        if index_ok:
            search_ok = test_zoekt_search()
        else:
            search_ok = False
    else:
        index_ok = False
        search_ok = False

    # Summary
    print("\n=== Diagnostic Summary ===")
    print(f"File content OK: {file_ok}")
    print(f"Zoekt available: {zoekt_available}")
    print(f"DAL backend OK: {dal is not None}")
    print(f"Search backend OK: {search_backend is not None}")
    print(f"Zoekt index OK: {index_ok}")
    print(f"Zoekt search OK: {search_ok}")

    if not file_ok:
        print("\nRECOMMENDATION: Create test file with 'Hello, World!' content")
    elif not zoekt_available:
        print("\nRECOMMENDATION: Install zoekt binaries (zoekt and zoekt-index)")
    elif not index_ok:
        print("\nRECOMMENDATION: Check zoekt index creation and permissions")
    elif not search_ok:
        print("\nRECOMMENDATION: Investigate zoekt search query building or index content")
    else:
        print("\nAll diagnostics passed - search should work correctly")

if __name__ == "__main__":
    main()