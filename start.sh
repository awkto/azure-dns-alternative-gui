#!/bin/bash
set -e

DATA_DIR="${AZURE_DNS_DATA_DIR:-$(pwd)/azure-data}"
IMAGE="${AZURE_DNS_IMAGE:-ghcr.io/altanc/azure-dns-alternative-gui:latest}"
PORT="${AZURE_DNS_PORT:-5000}"

docker run -d \
    --name azure-dns-manager \
    --restart unless-stopped \
    -p "${PORT}:5000" \
    -v "${DATA_DIR}:/app/data" \
    "$IMAGE"

echo "Started. Visit http://$(hostname -I | awk '{print $1}'):${PORT}"
