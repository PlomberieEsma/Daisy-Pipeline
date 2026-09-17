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

this_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)"

if [ -f "${this_dir}/set_usd_python_env.sh" ]; then
    source "${this_dir}/set_usd_python_env.sh"
fi

export USD_INSTALL_DIR="$(dirname "${this_dir}")"

export PATH="$USD_INSTALL_DIR/bin${PATH:+:${PATH}}"
if [[ $(uname) == MINGW64* ]]; then
    export PATH="$USD_INSTALL_DIR/lib:$USD_INSTALL_DIR/plugin/usd${PATH:+:${PATH}}"
    export PYTHONPATH="$(cygpath -w "$USD_INSTALL_DIR/lib/python")${PYTHONPATH:+;${PYTHONPATH}}"
else
    export LD_LIBRARY_PATH="$USD_INSTALL_DIR/lib:$USD_INSTALL_DIR/plugin/usd${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
    export PYTHONPATH="$USD_INSTALL_DIR/lib/python:$USD_PYTHON_DEPS_DIR${PYTHONPATH:+:${PYTHONPATH}}"
fi

export PXR_MTLX_STDLIB_SEARCH_PATHS="$USD_INSTALL_DIR/libraries"

echo "Activated USD python/tools from" $USD_INSTALL_DIR
