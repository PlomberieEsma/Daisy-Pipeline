#!/bin/bash

# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_ONLY=0

while [ $# -gt 0 ]
do
    if [[ "$1" == "--python-only" ]]
    then
        PYTHON_ONLY=1
    fi

    shift
done

# Find the python binary installation
PYTHON_VERSION="3.12"
PYTHON_BIN_NAME="python3"
PYTHON_BIN="$(realpath -m "${THIS_DIR}/../python/bin/${PYTHON_BIN_NAME}")"
if [ ! -f "${PYTHON_BIN}" ]; then
    PYTHON_BIN="$(which ${PYTHON_BIN_NAME})"
    if [ ! -f "${PYTHON_BIN}" ]; then
        echo "ERROR: Python ${PYTHON_VERSION} not found. Please install Python ${PYTHON_VERSION} and try again."
        exit 1
    fi
fi

# Verify the python version
FOUND_PYTHON_VERSION="$("${PYTHON_BIN}" \
    -c 'import sys; print(".".join(str(x) for x in sys.version_info[:2]))')"

if [[ "${FOUND_PYTHON_VERSION}" != "${PYTHON_VERSION}" ]]; then
    echo "ERROR: Python version ${FOUND_PYTHON_VERSION} does not match ${PYTHON_VERSION}. Please install Python ${PYTHON_VERSION} and try again."
    exit 1
fi

if [[ "${PYTHON_ONLY}" -eq 1 ]]; then
    exit 0
fi

# Check Python dependencies
PYTHON_DEPS_DIR="$(realpath -m "${THIS_DIR}/../pip-packages")"
PYTHON_REQUIREMENTS_FILE="$(realpath -m "${THIS_DIR}/../requirements.txt")"

if [ ! -f "${PYTHON_REQUIREMENTS_FILE}" ]; then
    echo "ERROR: Python requirements file not found. Please check the USD installation and try again."
    exit 1
fi

# Check for any missing dependencies
PYTHON_CHECK_DEPS_FILE="$(realpath -m "${THIS_DIR}/check_python_dependencies.py")"
"${PYTHON_BIN}" "${PYTHON_CHECK_DEPS_FILE}" -r "${PYTHON_REQUIREMENTS_FILE}"