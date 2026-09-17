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


set -e
this_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd)"

source "${this_dir}/set_usd_env.sh"

if [ -f "${this_dir}/check_python_dependencies.sh" ]; then
    "${this_dir}/check_python_dependencies.sh"
fi

if [ $# -eq 0 ]; then
    usdview "${USD_INSTALL_DIR}/share/usd/tutorials/traversingStage/HelloWorld.usda"
else
    usdview "$@"
fi
