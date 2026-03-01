import yaml
import secrets
from typing import Dict, Optional, Tuple

def generate_nostr_keys() -> Tuple[str, str]:
    """
    Generate a new Nostr keypair (nsec and npub).
    Requires: pip install secp256k1 bech32
    """
    # Generate 32 bytes of randomness for private key
    private_key_bytes = secrets.token_bytes(32)
    
    # Convert to bech32 nsec1... format
    nsec = bytes_to_bech32(private_key_bytes, 'nsec')
    
    # Derive public key using secp256k1
    import secp256k1
    priv_key = secp256k1.PrivateKey(private_key_bytes)
    pub_key_bytes = priv_key.pubkey.serialize()[1:]  # Remove 02/03 prefix
    npub = bytes_to_bech32(pub_key_bytes, 'npub')
    
    return nsec, npub

def bytes_to_bech32(data: bytes, hrp: str) -> str:
    """Convert bytes to bech32 format."""
    import bech32
    converted = bech32.convertbits(data, 8, 5)
    return bech32.bech32_encode(hrp, converted)

def init_config_with_keys(bind_addr: str = "0.0.0.0:2121", output_path: str = "config.yaml") -> Dict:
    """
    Initialize config with freshly generated keys.
    Returns config with nsec/npub and saves to file.
    """
    nsec, npub = generate_nostr_keys()
    
    config = {
        "node": {
            "identity": {
                "nsec": nsec,
                "npub": npub  # Store both for convenience
            }
        },
        "transports": {
            "udp": {
                "bind_addr": bind_addr
            }
        },
        "peers": []
    }
    
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Generated keys:\n  nsec: {nsec}\n  npub: {npub}")
    return config

def derive_npub_from_nsec(nsec: str) -> str:
    """Derive npub from nsec bech32 string."""
    import bech32, secp256k1
    
    hrp, data = bech32.bech32_decode(nsec)
    private_key_bytes = bytes(bech32.convertbits(data, 5, 8, False))
    
    priv_key = secp256k1.PrivateKey(private_key_bytes)
    pub_key_bytes = priv_key.pubkey.serialize()[1:]
    
    return bytes_to_bech32(pub_key_bytes, 'npub')

def get_npub_from_config(config_path: str = "config.yaml") -> Optional[str]:
    """Get npub from config (stored or derived from nsec)."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    identity = config.get("node", {}).get("identity", {})
    
    if "npub" in identity:
        return identity["npub"]
    
    nsec = identity.get("nsec", "")
    if nsec.startswith("nsec1"):
        return derive_npub_from_nsec(nsec)
    return None

def share_my_info(config_path: str = "config.yaml") -> Dict:
    """Get your public info to share with peers."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return {
        "npub": get_npub_from_config(config_path),
        "transport": "udp",
        "addr": config["transports"]["udp"]["bind_addr"]
    }

# Peer management functions (unchanged)
def load_config(config_path: str = "config.yaml") -> Dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def save_config(config: Dict, config_path: str = "config.yaml"):
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

def add_peer(npub: str, addr: str, transport: str = "udp", config_path: str = "config.yaml") -> Dict:
    config = load_config(config_path)
    config["peers"] = [p for p in config.get("peers", []) if p.get("npub") != npub]
    config["peers"].append({
        "npub": npub,
        "addresses": [{"transport": transport, "addr": addr}]
    })
    save_config(config, config_path)
    return config

def remove_peer(npub: str, config_path: str = "config.yaml") -> Optional[Dict]:
    config = load_config(config_path)
    original_len = len(config.get("peers", []))
    config["peers"] = [p for p in config["peers"] if p.get("npub") != npub]
    if len(config["peers"]) == original_len:
        return None
    save_config(config, config_path)
    return config

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup_config":
            init_config_with_keys()
        if sys.argv[1] == "add_peer":
            if len(sys.argv) > 2:
                npub = sys.argv[2]
                add_peer(npub)
            else:
                print("Please provide an npub for the peer to add. Example: 'python fips.py add_peer npub1ytfkfyjc86z36qyr7cq4trwchesecp89qw3ej9rmxp4mupfz8nfqf40cvh'.")
    else:
        print("Options:\nRun 'python fips.py setup_config' to setup a new config.")