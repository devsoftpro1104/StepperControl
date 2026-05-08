@echo off
setlocal
pushd "%~dp0\.."
python -m PyInstaller packaging\pyinstaller.spec --noconfirm
popd