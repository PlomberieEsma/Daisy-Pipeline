# Getting started with pre-built OpenUSD libraries and tools

This document describes how to get started using the pre-built OpenUSD libraries and tools available from [developer.nvidia.com](https://developer.nvidia.com/usd#section-getting-started). 

These comes fully bootstrapped with a Python environment, letting you immediately execute `usdview` and any other bundled OpenUSD tool.

## Quickstart Instructions

> **NOTE**: The following steps assume that the contents of the archives downloaded from [developer.nvidia.com/usd](https://developer.nvidia.com/usd#section-getting-started) have been extracted to a single folder, referenced in this section as the shell variable `USDROOT`.

### Windows

#### Launching `usdview`

To launch `usdview`, execute the `%USDROOT%\scripts\usdview_gui.bat` script from Explorer, or invoke the executable from a Batch prompt using:
```bat
%USDROOT%\scripts\usdview.bat %USDROOT%\share\usd\tutorials\traversingStage\HelloWorld.usda
```

In both cases `usdview` should launch, displaying a simple sphere.

#### Running `usdcat`

To execute `usdcat` and inspect the contents of a USD stage, invoke the executable from a Batch prompt using:
```bat
%USDROOT%\scripts\usdcat.bat %USDROOT%\share\usd\tutorials\convertingLayerFormats\Sphere.usd
```

The contents of the `Sphere.usd` provided as argument to the executable should print the following output:
```
#usda 1.0

def Sphere "sphere"
{
}
```

#### Setting up prompt environment variables

If you wish to configure a Batch prompt with environment variables defined to use OpenUSD tools without the need for wrapper scripts, you may start by executing this script within your session:
```bat
%USDROOT%\scripts\set_usd_env.bat
```

This will allow you to invoke the provided compiled tools and libraries located in `%USDROOT%\bin`, without having to execute the wrapper scripts in `%USDROOT%\scripts` ahead of time.

#### Launching the Python interpreter

To launch the Python interpreter included with the pre-built tools and libraries, start by configuring environment variable for the session using a Batch prompt before invoking Python:
```bat
%USDROOT%\scripts\set_usd_env.bat
python
```

The Python interpreter will then resolve OpenUSD imports, allowing OpenUSD APIs to be used in the prompt:
```python
from pxr import Usd, UsdGeom
stage = Usd.Stage.CreateInMemory()
cube = UsdGeom.Cube.Define(stage, "/myCube")
cube.GetSizeAttr().Set(3)
print(stage.ExportToString())
```

Invoking the Python code should then output the content of the composed OpenUSD stage:
```
#usda 1.0
(
    doc = """Generated from Composed Stage of root layer
"""
)

def Cube "myCube"
{
    double size = 3
}
```

### Linux

#### Launching `usdview`

To launch `usdview`, execute the `$USDROOT/scripts/usdview_gui.sh` script, or invoke the executable from a bash terminal using:
```shell
$USDROOT/scripts/usdview.sh $USDROOT/share/usd/tutorials/traversingStage/HelloWorld.usda
```

In both cases `usdview` should launch, displaying a simple sphere.

#### Running `usdcat`

To execute `usdcat` and inspect the contents of a USD stage, invoke the executable from a bash terminal using:
```shell
$USDROOT/scripts/usdcat.sh $USDROOT/share/usd/tutorials/convertingLayerFormats/Sphere.usd
```

The contents of the `Sphere.usd` provided as argument to the executable should print the following output:
```
#usda 1.0

def Sphere "sphere"
{
}
```

#### Setting up prompt environment variables

If you wish to configure a bash terminal with environment variables defined to use OpenUSD tools without the need for wrapper scripts, you may start by executing this script within your session:
```shell
. $USDROOT/scripts/set_usd_env.sh
```

This will allow you to invoke the provided compiled tools and libraries located in `$USDROOT/bin`, without having to execute the wrapper scripts in `$USDROOT/scripts` ahead of time.

#### Launching the Python interpreter

To launch the Python interpreter included with the pre-built tools and libraries, start by configuring environment variable for the session using a Batch prompt before invoking Python:
```shell
. $USDROOT/scripts.set_usd_env.sh
python
```

The Python interpreter will then resolve OpenUSD imports, allowing OpenUSD APIs to be used in the prompt:
```python
from pxr import Usd, UsdGeom
stage = Usd.Stage.CreateInMemory()
cube = UsdGeom.Cube.Define(stage, "/myCube")
cube.GetSizeAttr().Set(3)
print(stage.ExportToString())
```

Invoking the Python code should then output the content of the composed OpenUSD stage:
```
#usda 1.0
(
    doc = """Generated from Composed Stage of root layer
"""
)

def Cube "myCube"
{
    double size = 3
}
```
