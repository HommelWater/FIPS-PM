VENV_DIR="$(pwd)/venv"
cd "$(dirname "$0")"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install -q secp256k1 bech32 pyyaml requests

read -p "Ensure Cargo is installed! See: https://doc.rust-lang.org/cargo/. Press 'Enter' to continue."
git clone https://github.com/jmcorgan/fips.git
cd fips
cargo build --release
cd ..
python fips.py setup_config