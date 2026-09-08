@echo off
setlocal EnableDelayedExpansion
title Kimodo - AzRigTool

set "KIMODO_VERSION=2.2.0"
set "KIMODO_AUTHOR=Alexander Antonov - AzRigTool"
set "REPO=https://github.com/azigo45/kimodo.cpp"
set "MODEL=soma-rp-v1.1"
set "REMEMBER=%~dp0kimodo-path.txt"

set "PF86=%ProgramFiles(x86)%"
set "VSWHERE=%PF86%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSBOOTSTRAP=https://aka.ms/vs/17/release/vs_BuildTools.exe"
set "VSARGS=--add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.CMake.Project --includeRecommended"

if /i "%~1"=="--wait-and-open" goto :wait_and_open

if not defined KIMODO_INNER (
    set "KIMODO_INNER=1"
    cmd /k call "%~f0" %*
    exit /b
)

echo.
echo   Kimodo %KIMODO_VERSION%
echo   build by %KIMODO_AUTHOR%
echo   ---------------------------------------------------------------

set "ROOT="
if not "%~1"=="" call :try_root "%~1"
if not defined ROOT if exist "%REMEMBER%" (
    for /f "usebackq delims=" %%r in ("%REMEMBER%") do call :try_root "%%r"
)
call :try_root "%~dp0."
call :try_root "%~dp0..\kimodo.cpp"
call :try_root "%~dp0.."
if not defined ROOT (
    for %%d in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
        if exist "%%d:\" (
            call :try_root "%%d:\kimodo.cpp"
            call :try_root "%%d:\kimodo"
            call :try_root "%%d:\dev\kimodo.cpp"
            call :try_root "%%d:\src\kimodo.cpp"
            call :try_root "%%d:\git\kimodo.cpp"
            call :try_root "%%d:\Projects\kimodo.cpp"
            call :try_root "%%d:\Users\%USERNAME%\kimodo.cpp"
            call :try_root "%%d:\Users\%USERNAME%\Documents\kimodo.cpp"
            call :try_root "%%d:\Users\%USERNAME%\Downloads\kimodo.cpp"
        )
    )
)

if defined ROOT (
    call :find_generator
    call :find_go
    if defined GEN if defined GO if exist "!ROOT!\models\kimodo-%MODEL%-f32.gguf" (
        echo   [ok] installed           !ROOT!
        goto :demo
    )
)

if not defined ROOT call :choose_target "%~1"
if not defined ROOT goto :fail
>"%REMEMBER%" 2>nul echo %ROOT%

echo   installing into: %ROOT%
echo.
echo   This is the long run. Windows will ask for permission once or twice -
echo   say yes. You can close it at any point and start again; whatever
echo   finished is kept.
echo.

call :step 1 "Git, Python and curl"

call :find_git
if not defined GIT (
    echo   Git is missing - installing through winget.
    winget install --id Git.Git --accept-package-agreements --accept-source-agreements --disable-interactivity
    call :find_git
)
if not defined GIT (
    echo   [X] Git still not found. Install it from https://git-scm.com/download/win
    goto :fail
)
echo   [ok] Git               %GIT%

set "GITBASH="
for %%g in ("%GIT%\..\..\bin\bash.exe") do if exist "%%~fg" set "GITBASH=%%~fg"
if not defined GITBASH for %%g in ("%GIT%\..\..\..\bin\bash.exe") do if exist "%%~fg" set "GITBASH=%%~fg"
if not defined GITBASH set "GITBASH=%ProgramFiles%\Git\bin\bash.exe"
if not exist "%GITBASH%" set "GITBASH=%PF86%\Git\bin\bash.exe"
if not exist "%GITBASH%" set "GITBASH=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"
if not exist "%GITBASH%" (
    echo   [X] Git Bash not found next to !GIT!
    echo       The weights script is a shell script and cannot run under cmd.
    echo       Install Git for Windows from https://git-scm.com/download/win
    goto :fail
)
echo   [ok] Git Bash

call :find_python
if not defined PY (
    echo   Python is missing - installing through winget.
    winget install --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --disable-interactivity
    call :find_python
)
if not defined PY (
    echo   [X] Python still not found. Install it from
    echo       https://www.python.org/downloads/ with "Add to PATH" ticked.
    goto :fail
)
echo   [ok] Python            %PY%

where curl >nul 2>nul
if errorlevel 1 (
    echo   [X] curl is missing. It ships with Windows 10 and 11 - this machine
    echo       is older than that, and the rest will not work either.
    goto :fail
)
echo   [ok] curl

call :step 2 "Visual Studio C++ build tools"
call :find_vs
if defined VS goto :vs_ready

echo   Not found, so it gets installed now. About 3 GB fetched and 7 GB on
echo   disk. Windows will ask for permission. This takes a while.
echo.
set "VSEXE=%TEMP%\vs_BuildTools.exe"
echo   downloading the Visual Studio installer...
curl -sSL -o "%VSEXE%" "%VSBOOTSTRAP%"
if errorlevel 1 (
    echo   [X] could not download the Visual Studio installer. Get it from
    echo       https://visualstudio.microsoft.com/downloads/ under
    echo       "Tools for Visual Studio" - "Build Tools for Visual Studio".
    goto :fail
)
if not exist "%VSEXE%" (
    echo   [X] the Visual Studio installer did not arrive.
    goto :fail
)

call :find_buildtools
if defined VSPARTIAL (
    echo   adding the C++ workload to the installation already at
    echo     !VSPARTIAL!
    "%VSEXE%" modify --installPath "!VSPARTIAL!" %VSARGS% --passive --wait --norestart
) else (
    echo   installing Build Tools for Visual Studio...
    "%VSEXE%" %VSARGS% --passive --wait --norestart
)
set "VSCODE=%ERRORLEVEL%"
del "%VSEXE%" >nul 2>nul

if "%VSCODE%"=="3010" (
    echo   [warn] installed, but Windows wants a restart to finish. If the
    echo          build below fails, restart and run this again.
) else if not "%VSCODE%"=="0" (
    echo   [X] the Visual Studio installer stopped with code %VSCODE%.
    if "%VSCODE%"=="1602" echo       That code means the permission prompt was declined.
    if "%VSCODE%"=="1618" echo       That code means another installation is already running.
    goto :fail
)

call :find_vs
if not defined VS (
    echo   [X] the installer finished but no C++ compiler turned up. Open the
    echo       Visual Studio Installer and tick "Desktop development with C++".
    goto :fail
)

:vs_ready
set "VCVARS=%VS%\VC\Auxiliary\Build\vcvars64.bat"
set "VSCMAKE=%VS%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
set "VSNINJA=%VS%\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja"
if not exist "%VCVARS%" (
    echo   [X] vcvars64.bat missing under !VS!
    echo       That installation has no 64-bit compiler. Open the Visual Studio
    echo       Installer, press Modify, and tick the C++ workload.
    goto :fail
)
echo   [ok] Visual Studio     %VS%

call :step 3 "Vulkan SDK"
call :find_vulkan
if not defined VULKAN_SDK (
    echo   installing through winget - accept the permission prompt.
    winget install --id KhronosGroup.VulkanSDK --accept-package-agreements --accept-source-agreements --disable-interactivity
    call :find_vulkan
)
if defined VULKAN_SDK (
    echo   [ok] %VULKAN_SDK%
    set "USE_VULKAN=ON"
) else (
    echo   [warn] Not found. The build falls back to the CPU - it works, but is
    echo          far slower. Install it from https://vulkan.lunarg.com/sdk/home
    echo          then delete "%ROOT%\build" and run this again to rebuild.
    set "USE_VULKAN=OFF"
)

call :step 4 "Hugging Face client"
"%PY%" -m pip install -q -U huggingface_hub
if errorlevel 1 (
    echo   [X] pip failed. Check that Python can reach the network.
    goto :fail
)
set "PYTMP=%TEMP%\kimodo_pyscripts.txt"
"%PY%" -c "import sys,sysconfig;sys.stdout.reconfigure(encoding='oem');print(sysconfig.get_path('scripts')+';'+sysconfig.get_path('scripts','nt_user'))" > "%PYTMP%" 2>nul
set "PYSCRIPTS="
if exist "%PYTMP%" set /p "PYSCRIPTS="<"%PYTMP%"
del "%PYTMP%" >nul 2>nul
if not defined PYSCRIPTS (
    echo   [X] Python could not report where it keeps installed programs.
    goto :fail
)
for /f "delims=;" %%s in ("%PYSCRIPTS%") do if not exist "%%~s\" (
    echo   [X] Python reports its programs at a folder that is not there:
    echo       %%~s
    goto :fail
)
echo   [ok] ready             %PYSCRIPTS%

call :step 5 "Source"
if exist "%ROOT%\.git" (
    echo   [ok] already cloned - refreshing the ggml submodule
    "%GIT%" -C "%ROOT%" submodule update --init --recursive
) else (
    echo   cloning, which pulls the ggml submodule too...
    "%GIT%" clone --recurse-submodules "%REPO%" "%ROOT%"
    if errorlevel 1 (
        echo   [X] clone failed.
        goto :fail
    )
)
if not exist "%ROOT%\ggml\CMakeLists.txt" (
    echo   [X] the ggml submodule is empty and the build needs it.
    goto :fail
)
echo   [ok] source ready      %ROOT%

set "WEIGHTS_MARKER=%ROOT%\.kimodo-weights-ok"
call :step 6 "Weights - about 19 GB, the long part"
if exist "%WEIGHTS_MARKER%" (
    echo   [ok] already downloaded and verified, skipping
    goto :build
)
echo   Hugging Face throttles anonymous downloads, so this is retried until
echo   the checksums verify. Interrupting is safe - finished files are kept.
for %%p in ("%PY%") do set "PATH=%PYSCRIPTS%;%%~dpp;%PATH%"
set "ROOT_SH=%ROOT:\=/%"
for /l %%a in (1,1,12) do (
    if not exist "%WEIGHTS_MARKER%" (
        echo.
        echo   --- attempt %%a of 12 ---
        "%GITBASH%" -lc "cd '%ROOT_SH%' && scripts/download_gguf_weights.sh --output \"$PWD\" --model %MODEL%"
        if not errorlevel 1 (
            echo done > "%WEIGHTS_MARKER%"
            echo   [ok] weights verified
        )
    )
)
if not exist "%WEIGHTS_MARKER%" (
    echo   [X] the weights did not finish after 12 attempts. Run this again
    echo       later - only what is missing gets fetched.
    goto :fail
)

:build
call :step 7 "Building"
call "%VCVARS%" >nul
set "PATH=%VSCMAKE%;%VSNINJA%;%PATH%"
if "%USE_VULKAN%"=="ON" set "PATH=%VULKAN_SDK%\Bin;%PATH%"
pushd "%ROOT%"
cmake -S . -B build/vulkan -G Ninja -DCMAKE_BUILD_TYPE=Release -DKIMODO_ENABLE_VULKAN=%USE_VULKAN%
if errorlevel 1 (
    popd
    echo   [X] cmake configure failed.
    goto :fail
)
cmake --build build/vulkan
if errorlevel 1 (
    popd
    echo   [X] build failed.
    goto :fail
)
popd

copy /y "%ROOT%\build\vulkan\bin\*.dll" "%ROOT%\build\vulkan\" >nul 2>nul
echo   [ok] built, libraries copied

call :find_generator
if not defined GEN (
    echo   [X] the build finished but kmd-generate.exe is not there.
    goto :fail
)
"%ROOT%\build\vulkan\kmd-inspect.exe" "%ROOT%\models\kimodo-%MODEL%-f32.gguf" >nul
if %ERRORLEVEL% NEQ 0 (
    if not exist "%ROOT%\build\vulkan\ggml-base.dll" (
        echo   [X] the ggml libraries did not land beside the programs.
    ) else (
        echo   [X] the model did not load - the build or the weights are wrong.
    )
    goto :fail
)
echo   [ok] the model loads

call :step 8 "Go, which runs the web demo"
call :find_go
if not defined GO (
    echo   installing through winget - accept the permission prompt.
    winget install --id GoLang.Go --accept-package-agreements --accept-source-agreements --disable-interactivity
    call :find_go
)
if not defined GO (
    echo   [X] Go is still not there. Install it from https://go.dev/dl/ and
    echo       run this again.
    goto :fail
)
echo   [ok] Go                %GO%

:demo
call :step 9 "Starting the demo"
>"%REMEMBER%" 2>nul echo %ROOT%

if not defined GEN call :find_generator
if not defined GO call :find_go
if not defined GEN (
    echo   [X] kmd-generate.exe is missing under !ROOT!\build - nothing is
    echo       built. Delete that build folder and run this again.
    goto :fail
)
if not defined GO (
    echo   [X] Go is missing and it runs the web demo. Install it from
    echo       https://go.dev/dl/ and run this again.
    goto :fail
)

set "WANT=%~2"
if "%WANT%"=="" set "WANT=8090"
call :free_port %WANT%
if not defined PORT (
    echo   [X] ports !WANT! to the next nine are all busy. Pass one yourself:
    echo         kimodo.bat "%ROOT%" 9100
    goto :fail
)
set "URL=http://127.0.0.1:!PORT!/"
if not "!PORT!"=="%WANT%" echo   [warn] %WANT% was taken, using !PORT! instead
echo   [ok] address           !URL!
echo.
echo   The browser opens by itself once the server answers - the first run
echo   compiles it, so give it a few seconds. Leave this window open; closing
echo   it stops the demo.
echo.
start "" /b cmd /c ""%~f0" --wait-and-open "!URL!""
pushd "%ROOT%"
"%GO%" run ./demo -addr 127.0.0.1:!PORT! -generator "%GEN%"
popd

echo.
echo   The demo has stopped.
echo.
pause
exit /b 0

:step
echo.
echo   [%~1/9] %~2
exit /b 0

:try_root
if defined ROOT exit /b 0
if "%~1"=="" exit /b 0
for %%d in ("%~1") do set "CANDIDATE=%%~fd"
if not exist "!CANDIDATE!\demo\main.go" exit /b 0
if not exist "!CANDIDATE!\go.mod" exit /b 0
set "ROOT=!CANDIDATE!"
exit /b 0

:choose_target
set "SUGGEST=%~d0\kimodo.cpp"
if not exist "%~d0\" set "SUGGEST=%SystemDrive%\kimodo.cpp"
if not "%~1"=="" for %%d in ("%~1") do set "SUGGEST=%%~fd"
echo.
echo   Kimodo is not installed on this machine yet.
echo.
echo   It needs about 30 GB free: 19 for the weights, the rest for the source,
echo   the build and the compiler.
call :free_space "%SUGGEST%"
echo.
echo   Press Enter to install into
echo     %SUGGEST%
echo   or type another folder. It will be created.
echo.
set "TYPED="
set /p "TYPED=   folder: "
if not defined TYPED (
    set "ROOT=%SUGGEST%"
) else (
    set "TYPED=!TYPED:"=!"
    for %%d in ("!TYPED!\.") do set "ROOT=%%~fd"
)
if not defined ROOT exit /b 0
set "FULL="
if exist "!ROOT!\" for /f "delims=" %%x in ('dir /b "!ROOT!" 2^>nul') do set "FULL=1"
if defined FULL for %%d in ("!ROOT!\kimodo.cpp") do set "ROOT=%%~fd"
if not exist "!ROOT!" mkdir "!ROOT!" 2>nul
if not exist "!ROOT!" (
    echo   [X] cannot create !ROOT!
    set "ROOT="
)
exit /b 0

:free_space
set "FREEGB="
for %%d in ("%~1") do set "SPDRIVE=%%~dd"
if not defined SPDRIVE exit /b 0
for /f "usebackq delims=" %%g in (`powershell -NoProfile -Command "try{[math]::Floor((Get-PSDrive '%SPDRIVE:~0,1%').Free/1GB)}catch{''}" 2^>nul`) do set "FREEGB=%%g"
if not defined FREEGB exit /b 0
echo   %SPDRIVE% has %FREEGB% GB free.
if %FREEGB% LSS 30 echo   [warn] that is tight - the download may run out part way.
exit /b 0

:find_git
set "GIT="
for /f "usebackq delims=" %%g in (`where git 2^>nul`) do if not defined GIT set "GIT=%%g"
if not defined GIT if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%PF86%\Git\cmd\git.exe" set "GIT=%PF86%\Git\cmd\git.exe"
if not defined GIT if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
exit /b 0

:find_python
set "PY="
for /f "usebackq delims=" %%g in (`where python 2^>nul`) do call :try_python "%%g"
for /f "usebackq delims=" %%g in (`where python3 2^>nul`) do call :try_python "%%g"
for /d %%p in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :try_python "%%p\python.exe"
for /d %%p in ("%ProgramFiles%\Python3*") do call :try_python "%%p\python.exe"
call :try_python "%LOCALAPPDATA%\Python\bin\python.exe"
exit /b 0

:try_python
if defined PY exit /b 0
if "%~1"=="" exit /b 0
if not exist "%~1" exit /b 0
"%~1" -c "import sys" >nul 2>nul
if errorlevel 1 exit /b 0
set "PY=%~1"
exit /b 0

:find_go
set "GO="
for /f "usebackq delims=" %%g in (`where go 2^>nul`) do if not defined GO set "GO=%%g"
if not defined GO if exist "%ProgramFiles%\Go\bin\go.exe" set "GO=%ProgramFiles%\Go\bin\go.exe"
exit /b 0

:find_vs
set "VS="
if not exist "%VSWHERE%" exit /b 0
for /f "usebackq tokens=*" %%p in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2^>nul`) do set "VS=%%p"
exit /b 0

:find_buildtools
set "VSPARTIAL="
if not exist "%VSWHERE%" exit /b 0
for /f "usebackq tokens=*" %%p in (`"%VSWHERE%" -products Microsoft.VisualStudio.Product.BuildTools -property installationPath 2^>nul`) do set "VSPARTIAL=%%p"
exit /b 0

:find_vulkan
if defined VULKAN_SDK if exist "%VULKAN_SDK%\Include\vulkan\vulkan.h" exit /b 0
set "VULKAN_SDK="
if not exist "C:\VulkanSDK\" exit /b 0
for /f "delims=" %%v in ('dir /b /ad /on "C:\VulkanSDK" 2^>nul') do set "VULKAN_SDK=C:\VulkanSDK\%%v"
if defined VULKAN_SDK if not exist "!VULKAN_SDK!\Include\vulkan\vulkan.h" set "VULKAN_SDK="
exit /b 0

:find_generator
set "GEN="
if not defined ROOT exit /b 0
for %%g in (
    "build\vulkan\kmd-generate.exe"
    "build\release\kmd-generate.exe"
    "build\debug\kmd-generate.exe"
) do if not defined GEN if exist "!ROOT!\%%~g" set "GEN=%%~g"
exit /b 0

:free_port
set "PORT="
for /l %%p in (0,1,9) do (
    if not defined PORT (
        set /a "TRY=%~1+%%p"
        netstat -ano -p tcp | findstr /c:":!TRY! " | findstr /c:"LISTENING" >nul 2>nul
        if errorlevel 1 set "PORT=!TRY!"
    )
)
exit /b 0

:wait_and_open
set "URL=%~2"
set "OPENED="
for /l %%a in (1,1,150) do (
    if not defined OPENED (
        curl -s -o nul --max-time 2 "!URL!" >nul 2>nul
        if errorlevel 1 (
            >nul ping -n 2 127.0.0.1
        ) else (
            set "OPENED=1"
            start "" "!URL!"
        )
    )
)
exit /b 0

:fail
echo.
echo   Stopped. Whatever finished is kept - starting this again picks up from
echo   where it left off.
echo.
pause
exit /b 1
