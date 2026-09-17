REM SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
REM SPDX-License-Identifier: LicenseRef-NvidiaProprietary
REM
REM NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
REM property and proprietary rights in and to this material, related
REM documentation and any modifications thereto. Any use, reproduction,
REM disclosure or distribution of this material and related documentation
REM without an express license agreement from NVIDIA CORPORATION or
REM its affiliates is strictly prohibited.

@echo off
setlocal enabledelayedexpansion

call %~dp0set_usd_env.bat

if exist "%~dp0check_python_dependencies.bat" (
    call %~dp0check_python_dependencies.bat --python-only
    if !errorlevel! neq 0 (exit /b 1)
)

call "%USD_INSTALL_DIR%\bin\usdfixbrokenpixarschemas.cmd" %*

exit /b
