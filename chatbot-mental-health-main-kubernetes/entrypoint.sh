#!/bin/sh

apt-get update && apt-get install -y gettext-base && rm -rf /var/lib/apt/lists/*
envsubst < /app/.streamlit/secrets.toml.template > /app/.streamlit/secrets.toml

exec "$@"