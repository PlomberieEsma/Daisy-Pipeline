# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# No hashbang - should be sourced

function ResolvePath() {
    (cd "$1" > /dev/null; pwd -P)
}

this_dir="$(ResolvePath "$(dirname "${BASH_SOURCE[0]}")")"

export USD_PYTHON_DEPS_DIR="$(ResolvePath "${this_dir}/../pip-packages")"
export USD_PYTHON_DIR="$(ResolvePath "${this_dir}/../python")"

# we add both $USD_PYTHON_DIR and $USD_PYTHON_DIR/bin, because $USD_PYTHON_DIR/bin doesn't
# have a "python" binary, only a "python3" one, but $USD_PYTHON_DIR does have a "python"
# symlink to bin/python3
export PATH="$USD_PYTHON_DIR/bin:$USD_PYTHON_DIR:$USD_PYTHON_DEPS_DIR/bin${PATH:+:${PATH}}"
if [[ $(uname) == MINGW64* ]]; then
    export PYTHONPATH="$(cygpath -w "$USD_PYTHON_DEPS_DIR")${PYTHONPATH:+;${PYTHONPATH}}"
else
    export LD_LIBRARY_PATH="$USD_PYTHON_DIR/lib"
    export PYTHONPATH="$USD_INSTALL_DIR/lib/python:$USD_PYTHON_DEPS_DIR${PYTHONPATH:+:${PYTHONPATH}}"
fi