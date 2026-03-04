VENV_DIR="$(pwd)/venv"
cd "$(dirname "$0")"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install -q secp256k1 bech32 pyyaml requests dnspython

sudo systemctl restart systemd-resolved
sudo resolvectl dns fips0 127.0.0.1:5354
sudo resolvectl domain fips0 "~fips"

read -p "Ensure Cargo is installed! See: https://doc.rust-lang.org/cargo/. Press 'Enter' to continue."
git clone https://github.com/jmcorgan/fips.git
cd fips
cargo build --release
cd ..
read -p "Enter an alias to refer to this machine as. Keep it unique to distinguish yourself from your peers: " alias
python fips.py setup_config $alias