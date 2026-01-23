
from typeshed_client import finder, parser
import sys
from pathlib import Path

def is_stdlib_module(stub_path):
    path_str = str(stub_path)
    # Check for likely stdlib locations
    if "stdlib" in path_str and "site-packages" in path_str:
         return True
    if "/typeshed/stdlib/" in path_str:
         return True
    # If it is directly in typeshed root (old structure or bundled?)
    if "typeshed_client/typeshed/" in path_str and "stubs" not in path_str:
         return True
    return False

print("Searching for modules...")
search_context = finder.get_search_context()
print(f"Search Context keys: {dir(search_context)}")

try:
    stub = finder.get_stub_file("re")
    print(f"Stub for 're': {stub}")
    if stub:
        print(f"Is re stdlib? {is_stdlib_module(stub)}")

    stub_yaml = finder.get_stub_file("yaml")
    print(f"Stub for 'yaml': {stub_yaml}")
    if stub_yaml:
        print(f"Is yaml stdlib? {is_stdlib_module(stub_yaml)}")

    stub_requests = finder.get_stub_file("requests")
    print(f"Stub for 'requests': {stub_requests}")
    if stub_requests:
        print(f"Is requests stdlib? {is_stdlib_module(stub_requests)}")

    stub_os = finder.get_stub_file("os")
    print(f"Stub for 'os': {stub_os}")

except Exception as e:
    print(f"Error: {e}")
