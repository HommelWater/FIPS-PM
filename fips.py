import yaml
import secrets
from typing import Dict, Optional, Tuple
import requests

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

def init_config_with_keys(alias, udp_port=2121, tcp_port=443, config_path="config.yaml") -> Dict:
    nsec, npub = generate_nostr_keys()
    addr = get_public_ip()
    with open("template_config.yaml", "r") as f:
        config_string = f.read()

    config_string = config_string.replace("{ALIAS}", alias)
    config_string = config_string.replace("{ADDR}", addr)
    config_string = config_string.replace("{TCP_PORT}", str(tcp_port))
    config_string = config_string.replace("{UDP_PORT}", str(udp_port))
    config_string = config_string.replace("{NPUB}", npub)
    config_string = config_string.replace("{NSEC}", nsec)

    with open(config_path, 'w') as f:
        f.write(config_string)
    return load_config(config_path)

def get_node_info(config_path: str = "config.yaml") -> Dict:
    config = load_config(config_path)
    try:
        info = config["node"]["identity"]["node_info"]
    except:
        print("Could not access your node's node_info!")
    return info

def load_config(config_path: str = "config.yaml") -> Dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def save_config(config: Dict, config_path: str = "config.yaml"):
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

def add_peer(peer_info, config_path: str = "config.yaml") -> Dict:
    config = load_config(config_path)
    config["peers"] = [p for p in config.get("peers", []) if p.get("npub") != peer_info["npub"]]
    if peer_info.get("alias", "") in config["peers"]:
        print("This alias already exists! Please enter a unique peer alias.")
        return config
    config["peers"].append(peer_info)
    save_config(config, config_path)
    return config

def remove_peer(alias: str, config_path: str = "config.yaml") -> Optional[Dict]:
    config = load_config(config_path)
    config["peers"] = [p for p in config["peers"] if p.get("alias") != alias]
    save_config(config, config_path)
    return config

def print_options():
    print("Options:")
    print("'python fips.py info' for your peer's info.")
    print("'python fips.py setup <alias>' to setup a new config.")
    print("'python fips.py add_peer <peer_info json string>' to add a new peer.")
    print("'python fips.py remove_peer <alias>' to remove a peer.")

def main():
    import sys
    arg_count = len(sys.argv)
    if arg_count == 1: 
        print_options()
        return
    arg = sys.argv[1]
    if arg == "info":
        info = get_node_info()
        print("Run the following command on another node to add this node to a node's peers:")
        print(f"python fips.py add_peer {str(info)}")
        print("")
        print("Connect to this node using your npub:")
        print(f"npub: '{info["npub"]}'")

    if arg == "setup":
        if arg_count < 3:
            print("Invalid argument count.")
            print("")
            print_options()
            return
        alias = sys.argv[2]
        init_config_with_keys(alias)

    if arg == "add_peer":
        if arg_count < 3:
            print("Invalid argument count.")
            print("")
            print_options()
            return
        import json
        peer_info_string = sys.argv[2]
        peer_info = json.loads(peer_info_string)
        add_peer(peer_info)
    
    if arg == "remove_peer":
        if arg_count < 3:
            print("Invalid argument count.")
            print("")
            print_options()
            return
        alias = sys.argv[2]
        remove_peer(alias)

if __name__ == "__main__":
    main()