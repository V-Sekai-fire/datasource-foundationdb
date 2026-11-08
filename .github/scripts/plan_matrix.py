"""The build matrix of .github/workflows/fdb-portability.yml, and the `only` filter over it.

A job-level `if` cannot see a matrix, so the workflow's plan job calls this and the build job reads
the result with fromJSON. Kept in a file, not inline in the workflow, so a desk can test it.
"""

import json
import os
import sys

ENTRIES = [
    {
        "os": "linux",
        "runner": "ubuntu-latest",
        "container": "foundationdb/build:rockylinux9-latest",
        "build_jobs": 2,
    },
    # Apple silicon, so this is the arm64 build. CMAKE_SYSTEM_PROCESSOR is "arm64",
    # not "aarch64", so ConfigureCompiler.cmake:428 does not add -march=armv8.2-a,
    # and USE_AVX finds no ^x86 and disables itself. 3 cores and 7 GB, the least
    # memory in the matrix.
    {"os": "macos", "runner": "macos-latest", "container": "", "build_jobs": 3},
    {"os": "windows", "runner": "windows-latest", "container": "", "build_jobs": 4},
    # FLOWQUIC=ON on Windows: the same clang-cl, Boost 1.86 and vcpkg setup as the windows
    # entry, building flow_quic_echo and running it. It publishes nothing and the desk is
    # not involved.
    {
        "os": "windows",
        "label": "windows-flowquic",
        "flowquic": "ON",
        "runner": "windows-latest",
        "container": "",
        "build_jobs": 4,
    },
]


def name_of(entry):
    return entry.get("label", entry["os"])


def plan(only=""):
    """The entries to build: all of them for a blank `only`, else the one it names."""
    only = only.strip()
    if not only:
        return list(ENTRIES)
    chosen = [e for e in ENTRIES if name_of(e) == only]
    if not chosen:
        names = ", ".join(name_of(e) for e in ENTRIES)
        raise SystemExit(
            "::error::no matrix entry is named %s (have: %s)" % (only, names)
        )
    return chosen


def main():
    chosen = plan(os.environ.get("ONLY", ""))
    print("entries:", [name_of(e) for e in chosen])
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write("include=" + json.dumps(chosen) + "\n")


if __name__ == "__main__":
    sys.exit(main())
