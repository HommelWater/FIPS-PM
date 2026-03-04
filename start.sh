#!/bin/bash

# Kill existing programs on fips port
sudo kill -9 $(sudo lsof -t -i :5354) 2>/dev/null || true

# Restart systemd-resolved to be safe
sudo systemctl restart systemd-resolved

# Check if NetworkManager is active and add exception for fips0
if systemctl is-active --quiet NetworkManager; then
    echo "NetworkManager is active, adding exception for fips0..."
    
    # Method 1: Create NetworkManager config to ignore fips0
    sudo mkdir -p /etc/NetworkManager/conf.d
    sudo tee /etc/NetworkManager/conf.d/99-fips0-ignore.conf > /dev/null <<'EOF'
[keyfile]
unmanaged-devices=interface-name:fips0
EOF
    
    # Method 2: Also ensure fips0 connection is unmanaged if it exists
    if nmcli connection show fips0 &>/dev/null; then
        sudo nmcli connection modify fips0 connection.autoconnect no
        sudo nmcli connection down fips0 2>/dev/null || true
    fi
    
    # Reload NetworkManager to apply changes
    sudo systemctl reload NetworkManager
    sleep 1
    echo "NetworkManager will ignore fips0 interface"
else
    echo "NetworkManager is not active"
fi

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