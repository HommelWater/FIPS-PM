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

./packaging/systemd/build-tarball.sh
tar xzf deploy/fips-*-linux-*.tar.gz
cd fips-*-linux-*/
sudo ./install.sh

cd ../../
sudo cp ./template_config.yaml /etc/fips/fips.yaml