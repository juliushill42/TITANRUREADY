@echo off
setlocal

set "TARGET_DIR=C:\Users\juliu\Desktop\Titan_OS_Launch\titanu-os\frontend\electron"

echo Deleting node_modules...
if exist "%TARGET_DIR%\node_modules" (
    rmdir /s /q "%TARGET_DIR%\node_modules"
)

echo Deleting dist...
if exist "%TARGET_DIR%\dist" (
    rmdir /s /q "%TARGET_DIR%\dist"
)

echo Deleting dist-electron...
if exist "%TARGET_DIR%\dist-electron" (
    rmdir /s /q "%TARGET_DIR%\dist-electron"
)

echo Clean-up complete.
endlocal