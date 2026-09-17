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
pushd %~dp0

call :ResolvePath USD_PYTHON_DEPS_DIR ../pip-packages
call :ResolvePath USD_PYTHON_DIR ../python

set PATH=^
%USD_PYTHON_DIR%;^
%USD_PYTHON_DEPS_DIR%\bin;^
%PATH%

set PYTHONPATH=%USD_PYTHON_DEPS_DIR%;%PYTHONPATH%

popd

exit /b

:: Resolve path to absolute.
:: Param 1: Name of output variable.
:: Param 2: Path to resolve.
:: Return: Resolved absolute path.
:ResolvePath
    set %1=%~dpfn2
    exit /b
