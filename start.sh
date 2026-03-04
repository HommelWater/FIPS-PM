#!/bin/bash

# Kill existing programs on fips port
sudo kill -9 $(sudo lsof -t -i :5354) 2>/dev/null || true
set -e

FIPS_BIN="./fips/target/release/fips"
CONFIG_FILE="config.yaml"
DNS_PORT="5354"
INTERFACE="fips0"

echo "=== Starting FIPS node ==="

# Kill anything using DNS port (only if exists)
if lsof -ti :"$DNS_PORT" >/dev/null 2>&1; then
    echo "Freeing DNS port $DNS_PORT..."
    sudo kill -9 $(lsof -ti :"$DNS_PORT") || true
fi

# Restart systemd-resolved (safe reset)
sudo systemctl restart systemd-resolved

# ---- NetworkManager handling (idempotent) ----
if systemctl is-active --quiet NetworkManager; then
    echo "Ensuring NetworkManager ignores $INTERFACE..."

    CONF_FILE="/etc/NetworkManager/conf.d/99-fips0-ignore.conf"

    if [ ! -f "$CONF_FILE" ]; then
        sudo mkdir -p /etc/NetworkManager/conf.d
        echo "[keyfile]
unmanaged-devices=interface-name:$INTERFACE" | sudo tee "$CONF_FILE" >/dev/null
        sudo systemctl reload NetworkManager
        echo "NetworkManager ignore rule created."
    else
        echo "NetworkManager already configured."
    fi
fi

# ---- Start FIPS ----
echo "Starting FIPS..."
sudo "$FIPS_BIN" -c "$CONFIG_FILE" &
FIPS_PID=$!

# Wait for interface
echo "Waiting for $INTERFACE to appear..."
for i in {1..30}; do
    if ip link show "$INTERFACE" &>/dev/null; then
        echo "$INTERFACE is up."
        break
    fi
    sleep 1
done

if ! ip link show "$INTERFACE" &>/dev/null; then
    echo "ERROR: $INTERFACE did not appear."
    sudo kill "$FIPS_PID" 2>/dev/null || true
    exit 1
fi

# ---- DNS config (safe overwrite) ----
echo "Configuring DNS for .fips"
sudo resolvectl dns "$INTERFACE" 127.0.0.1:$DNS_PORT
sudo resolvectl domain "$INTERFACE" "~fips"

# ---- Enable IPv6 forwarding (only if needed) ----
CURRENT_FORWARD=$(sysctl -n net.ipv6.conf.all.forwarding)
if [ "$CURRENT_FORWARD" -ne 1 ]; then
    echo "Enabling IPv6 forwarding..."
    sudo sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null
fi

# ---- Disable offloading (ignore errors silently) ----
sudo ethtool -K "$INTERFACE" tx-checksum-ipv6 off 2>/dev/null || true
sudo ethtool -K "$INTERFACE" rx-checksum-ipv6 off 2>/dev/null || true
sudo ethtool -K "$INTERFACE" tso off 2>/dev/null || true
sudo ethtool -K "$INTERFACE" gso off 2>/dev/null || true

# ---- firewalld integration (idempotent) ----
if systemctl is-active --quiet firewalld; then
    echo "Ensuring $INTERFACE is in trusted zone..."

    if ! firewall-cmd --zone=trusted --query-interface="$INTERFACE" >/dev/null; then
        sudo firewall-cmd --permanent --zone=trusted --add-interface="$INTERFACE"
        sudo firewall-cmd --reload
        echo "$INTERFACE added to trusted zone."
    else
        echo "$INTERFACE already trusted."
    fi
fi

echo ""
echo "FIPS node running (PID: $FIPS_PID)"
echo "To stop: sudo kill $FIPS_PID"