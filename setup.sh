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
python fips.py setup_config $alias

# Restart systemd-resolved to be safe
sudo systemctl restart systemd-resolved

# Start FIPS in the background
echo "Starting FIPS node..."
sudo ./fips/target/release/fips -c config.yaml &
FIPS_PID=$!

# Wait for fips0 interface to appear (timeout after 30 seconds)
echo "Waiting for fips0 interface to come up..."
for i in {1..30}; do
    if ip link show fips0 &>/dev/null; then
        echo "fips0 interface is up!"
        break
    fi
    sleep 1
done

# Verify interface exists
if ! ip link show fips0 &>/dev/null; then
    echo "ERROR: fips0 interface did not come up in time"
    sudo kill $FIPS_PID 2>/dev/null
    exit 1
fi

# Configure DNS for fips0
echo "Configuring DNS resolver..."
sudo resolvectl dns fips0 127.0.0.1:5354
sudo resolvectl domain fips0 "~fips"

echo "FIPS node running (PID: $FIPS_PID)"
echo "DNS configured for .fips domains"
echo ""
echo "To stop FIPS: sudo kill $FIPS_PID"