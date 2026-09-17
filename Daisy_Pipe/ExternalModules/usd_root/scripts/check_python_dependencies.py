# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

#!/usr/bin/env python
import argparse
import os
import sys

from importlib.metadata import PackageNotFoundError, version as package_version


def parse_requirement(requirement_str):
    """Parse a requirement string into package name and version specifier.

    Args:
        requirement_str: A string like 'package>=1.0.0', 'package~=2.0', etc.
    Returns:
        tuple: (package_name, version_specifier) or (package_name, None) if no version specified
    """
    # Remove comments and clean whitespace
    requirement_str = requirement_str.split("#")[0].strip()
    if not requirement_str:
        return None, None, None

    # Split on first occurrence of any comparison operator
    operators = [">=", "<=", "!=", "==", "~=", ">", "<", "="]
    name = requirement_str
    version = None
    version_op = None

    for op in operators:
        if op in requirement_str:
            parts = requirement_str.split(op, 1)
            name = parts[0].strip()
            version = parts[1].strip()
            version_op = op
            break

    # Remove any extras or markers (e.g., package[extra]; python_version > '3.7')
    name = name.split("[")[0].split(";")[0].strip()
    if version:
        version = version.split(";")[0].strip()

    return name, version, version_op


def parse_version(version_str: str) -> tuple:
    """Parse version string into a tuple of integers and strings.

    Args:
        version_str: Version string (e.g., '1.0.0', '2.1.0.dev1', '1.0b2')
    Returns:
        tuple: Tuple of version components
    """
    # Split version into parts (handling a, b, rc, dev, post suffixes)
    parts = []
    for part in version_str.replace("-", ".").split("."):
        # Extract any numeric prefix
        numeric = ""
        suffix = ""
        for char in part:
            if char.isdigit():
                numeric += char
            else:
                suffix = part[len(numeric) :]
                break

        # Convert numeric part to integer
        if numeric:
            parts.append(int(numeric))
        # Add any remaining suffix
        if suffix:
            parts.append(suffix)

    return tuple(parts)


def conatains_version(installed_version: str, required_version: str, version_op: str) -> bool:
    """Compare two version strings based on the operator without using packaging module.

    Args:
        installed_version: Currently installed version string (e.g., '1.0.0')
        required_version: Required version string (e.g., '2.0.0')
        version_op: Version comparison operator ('>=', '<=', '==', '!=', '>', '<', '~=')
    Returns:
        bool: True if the installed version satisfies the requirement
    """
    installed = parse_version(installed_version)
    required = parse_version(required_version)

    def compare(v1, v2):
        """Compare two version tuples."""
        # Compare all parts
        for p1, p2 in zip(v1, v2):  # noqa: B905
            # If types differ, strings are considered lower than integers
            if isinstance(p1, int) and isinstance(p2, str):
                return 1
            if isinstance(p1, str) and isinstance(p2, int):
                return -1
            if p1 < p2:
                return -1
            if p1 > p2:
                return 1
        # If all common parts match, longer version is considered greater
        return len(v1) - len(v2)

    result = compare(installed, required)

    if version_op == "~=":
        # Compatible release: same major.minor and installed >= required
        if len(installed) < 2 or len(required) < 2:
            return False
        return installed[0] == required[0] and installed[1] == required[1] and result >= 0

    operators = {
        ">=": lambda r: r >= 0,
        "<=": lambda r: r <= 0,
        "==": lambda r: r == 0,
        "!=": lambda r: r != 0,
        ">": lambda r: r > 0,
        "<": lambda r: r < 0,
        "=": lambda r: r == 0,  # Handle = same as ==
    }

    return operators[version_op](result)


def check_requirements(requirements_file) -> int:
    if not os.path.isfile(requirements_file):
        print(f"ERROR: Requirements file {requirements_file} not found.")
        return 1

    with open(requirements_file, encoding="utf-8") as f:
        requirements = f.readlines()

    missing_packages = []
    for requirement in requirements:
        requirement = requirement.strip()
        if not requirement or requirement.startswith("#"):
            continue

        try:
            name, required_version, version_op = parse_requirement(requirement)
            if not name:
                missing_packages.append(f"{requirement} (error: invalid requirement format)")
                continue

            installed_version = package_version(name)
            if required_version and not conatains_version(installed_version, required_version, version_op):
                missing_packages.append(
                    f"{name} (version conflict: required: {required_version}, installed: {installed_version})"
                )
        except PackageNotFoundError:
            missing_packages.append(requirement)
        except Exception as error:
            missing_packages.append(f"{requirement} (error: {error!s})")

    if missing_packages:
        print("The following packages are missing or have version conflicts:")
        for package in missing_packages:
            print("  -", package)
        print(f"Please install the missing packages using {requirements_file}")
        return 1

    print("All required python packages are installed.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Checks if the required python packages are installed.")
    parser.add_argument(
        "-r",
        "--requirement",
        required=True,
        dest="requirement",
        type=str,
        help="Specify the requirements file for checking required dependencies.",
    )
    opts = parser.parse_args()
    result = check_requirements(opts.requirement)
    sys.exit(result)


if __name__ == "__main__":
    main()
