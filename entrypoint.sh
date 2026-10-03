#!/bin/sh
set -e

# Auto-initialize config.ini if absent in persistent volume
if [ ! -f /app/config.ini ] && [ -f /app/config.ini.default ]; then
    echo "[Entrypoint] Initializing default config.ini..."
    cp /app/config.ini.default /app/config.ini
fi

# Auto-initialize users.json in persistent data volume
mkdir -p /app/data /app/logs /app/sdr_cache
if [ ! -f /app/data/users.json ] && [ -f /app/src/users.json ]; then
    echo "[Entrypoint] Initializing default users.json into persistent volume..."
    cp /app/src/users.json /app/data/users.json
fi

export YUNSHU_USERS_FILE=/app/data/users.json

exec "$@"
