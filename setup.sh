#!/bin/bash
VENV_DIR="$(pwd)/venv"
cd "$(dirname "$0")"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install -q secp256k1 bech32 pyyaml requests dnspython

# Build FIPS first (before starting it)
read -p "Ensure Cargo is installed! See: https://doc.rust-lang.org/cargo/ . Press 'Enter' to continue."
if [ ! -d "fips" ]; then
    git clone https://github.com/jmcorgan/fips.git 
fi
cd fips
cargo build --release
cd ..

read -p "Enter an alias to refer to this machine as. Keep it unique to distinguish yourself from your peers: " alias
python fips.py setup $alias

echo "FIPS was setup, start your node using 'bash start.sh'