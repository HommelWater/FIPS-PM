import yaml
import secrets
from typing import Dict, Optional, Tuple
import requests

PORT = "2121"

def get_public_ip():
    """
    Retrieves the public IP address of the machine.

    Returns:
        str: The public IP address as a string.
        None: If the request fails or no IP is found.
    """
    try:
        # Using ipify.org
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if response.status_code == 200:
            return response.json().get('ip')
        else:
            print("Failed to fetch IP from ipify.org")
    except requests.RequestException as e:
        print(f"Error fetching public IP: {e}")

    try:
        # Fallback to ident.me
        response = requests.get('https://ident.me', timeout=5)
        if response.status_code == 200:
            return response.text.strip()
        else:
            print("Failed to fetch IP from ident.me")
    except requests.RequestException as e:
        print(f"Error fetching public IP: {e}")

    return None

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

def init_config_with_keys(alias="", bind_addr: str = "0.0.0.0", output_path: str = "config.yaml") -> Dict:
    """
    Initialize config with freshly generated keys.
    Returns config with nsec/npub and saves to file.
    """
    nsec, npub = generate_nostr_keys()
    
    config = {
        "node": {
            "identity": {
                "nsec": nsec,
                "npub": npub,
                "alias": alias,
                "public_addr": get_public_ip() + f":{PORT}"
            }
        },
        "transports": {
            "udp": {
                "bind_addr": bind_addr + f":{PORT}"
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
    config = load_config(config_path)
    
    identity = config.get("node", {}).get("identity", {})
    
    if "npub" in identity:
        return identity["npub"]
    
    nsec = identity.get("nsec", "")
    if nsec.startswith("nsec1"):
        return derive_npub_from_nsec(nsec)
    return None

def share_my_info(config_path: str = "config.yaml") -> Dict:
    """Get your public info to share with peers."""
    config = load_config(config_path)
    try:
        info = {
        "alias":config["node"]["identity"]["alias"],
        "npub": config["node"]["identity"]["npub"],
        "transport": "udp",
        "node_addr": config["node"]["identity"]["public_addr"]
    }
        return info
    except:
        print("Invalid config layout! Could not get config info.")
    return None

# Peer management functions (unchanged)
def load_config(config_path: str = "config.yaml") -> Dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def save_config(config: Dict, config_path: str = "config.yaml"):
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

def add_peer(npub: str, addr: str, alias, transport: str = "udp", config_path: str = "config.yaml") -> Dict:
    config = load_config(config_path)
    config["peers"] = [p for p in config.get("peers", []) if p.get("npub") != npub]
    config["peers"].append({
        "npub": npub,
        "alias":alias,
        "addresses": [{"transport": transport, "addr": addr}]
    })
    save_config(config, config_path)
    return config

def remove_peer(alias: str, config_path: str = "config.yaml") -> Optional[Dict]:
    config = load_config(config_path)
    original_len = len(config.get("peers", []))
    config["peers"] = [p for p in config["peers"] if p.get("alias") != alias]
    if len(config["peers"]) == original_len:
        return None
    save_config(config, config_path)
    return config

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup_config":
            if len(sys.argv) > 2:
                alias = sys.argv[2]
                init_config_with_keys(alias)
            else:
                print("Please provide an alias for this machine. Example 'python fips.py setup_config home-desktop'")
        if sys.argv[1] == "add_peer":
            if len(sys.argv) > 4:
                npub = sys.argv[2]
                addr = sys.argv[3]
                alias = sys.argv[4]
                add_peer(npub, addr, alias)
                print(f"Added peer '{alias}' with npub '{npub}' and address '{addr}'.")
            else:
                print("Please provide an npub and address for the peer to add. Example: 'python fips.py add_peer npub1ytfkfyjc86z36qyr7cq4trwchesecp89qw3ej9rmxp4mupfz8nfqf40cvh 12.34.56.789:2121 alias_B'.")
        if sys.argv[1] == "remove_peer":
            if len(sys.argv) > 2:
                alias = sys.argv[2]
                s = remove_peer(alias)
                if s is None:
                    print(f"Could not find peer with alias {alias}")
                else:
                    print(f"Removed peer '{alias}'.")
            else:
                print("Please provide an npub for the peer to remove. Example: 'python fips.py remove_peer npub1ytfkfyjc86z36qyr7cq4trwchesecp89qw3ej9rmxp4mupfz8nfqf40cvh'.")
        if sys.argv[1] == "info":
            info = share_my_info()
            if info:
                print("Connect your node using this information:")
                print(f"npub: {info["npub"]}")
                print("")
                print("Run the following command to add this node to a node's peers:")
                print(f"python fips.py add_peer {info["npub"]} {info["node_addr"]} {info["alias"]}")
    else:
        print("Options:")
        print("'python fips.py info' for your peer's info.")
        print("'python fips.py setup_config <alias>' to setup a new config.")
        print("'python fips.py add_peer <npub> <node_public_address> <alias>' to add a new peer.")
        print("'python fips.py remove_peer <alias>' to remove a peer.")
