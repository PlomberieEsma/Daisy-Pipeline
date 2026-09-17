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

set SCRIPT_DIR=%~dp0
set "PYTHON_ONLY=0"

goto :parseargs

:parseargs
    if not "%1"=="" (
        if "%1" == "--python-only" (
            set "PYTHON_ONLY=1"
        )

        shift
        goto :parseargs
    )

REM Find the python binary installation
set "PYTHON_VERSION=3.12"
set "PYTHON_BIN_NAME=python.exe"

REM allow for local development python
call :ResolvePath PYTHON_BIN ../python\%PYTHON_BIN_NAME%

if not exist "%PYTHON_BIN%" (
    for /f "delims=" %%i in ('where %PYTHON_BIN_NAME% 2^>nul') do (
        set "PYTHON_BIN=%%i"
        goto :FoundPython
    )
    if not defined PYTHON_BIN (
        echo ERROR: Python "%PYTHON_VERSION%" not found. Please install Python "%PYTHON_VERSION%" and try again.
        exit /b 1
    )
)

:FoundPython

REM Verify Python versions
for /f "delims=" %%v in ('%PYTHON_BIN% -c "import sys; print('.'.join(str(x) for x in sys.version_info[:2]))"') do set "FOUND_PYTHON_VERSION=%%v"
if "%FOUND_PYTHON_VERSION%" neq "%PYTHON_VERSION%" (
    echo ERROR: Python version "%FOUND_PYTHON_VERSION%" does not match "%PYTHON_VERSION%". Please install Python "%PYTHON_VERSION%" and try again.
    exit /b 1
)

if "%PYTHON_ONLY%" == "1" (
    exit /b 0
)

REM Check Python dependencies
call :ResolvePath PYTHON_DEPS_DIR %SCRIPT_DIR%../pip-packages
call :ResolvePath PYTHON_REQUIREMENTS_FILE %SCRIPT_DIR%../requirements.txt

if not exist "%PYTHON_REQUIREMENTS_FILE%" (
    echo ERROR: Python requirements file not found. Please check the USD installation and try again.
    exit /b 1
)

call :ResolvePath PYTHON_CHECK_DEPS_FILE %SCRIPT_DIR%check_python_dependencies.py
call "%PYTHON_BIN%" "%PYTHON_CHECK_DEPS_FILE%" -r "%PYTHON_REQUIREMENTS_FILE%"
exit /b !errorlevel!

:: Resolve path to absolute.
:: Param 1: Name of output variable.
:: Param 2: Path to resolve.
:: Return: Resolved absolute path.
:ResolvePath
    set %1=%~dpfn2
    exit /b