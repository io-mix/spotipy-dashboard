#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r src/requirements.txt
#pip install -r tests/requirements-test.txt

export PYTHONPATH="$PROJECT_ROOT/src"

# check required libraries for greenlet
RED='\033[0;31m'
NC='\033[0m'

for lib in libgcc_s.so.1 libstdc++.so.6; do
    if ! ldconfig -p | grep -q "$lib"; then
        case $lib in
            libgcc_s.so.1)
                echo -e "${RED}WARNING: $lib not found. Greenlet may fail.${NC}"
                echo -e "${RED}Install with: sudo apt install libgcc-s1${NC}"
                ;;
            libstdc++.so.6)
                echo -e "${RED}WARNING: $lib not found. C++ extensions may fail.${NC}"
                echo -e "${RED}Install with: sudo apt install libstdc++6${NC}"
                ;;
        esac
    fi
done

echo "Starting spotipy dashboard..."
cd src
python3 main.py
