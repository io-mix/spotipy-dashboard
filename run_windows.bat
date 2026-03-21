@echo off

setlocal
cd /d %~dp0

if not exist "data" (
    echo Creating data directory...
    mkdir data
)

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
echo Installing/Updating dependencies...
pip install -q -r src\requirements.txt
:: pip install -q -r tests\requirements-test.txt

set PYTHONPATH=%CD%\src

echo Starting Spotipy Dashboard...
cd src
python main.py
pause
