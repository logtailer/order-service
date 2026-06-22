#!/bin/bash
set -e

echo "Building and starting order-service..."
docker compose up --build -d

echo "Waiting for service to be healthy..."
until curl -sf http://localhost:5001/health > /dev/null; do
  sleep 2
done

echo "Service is up at http://localhost:5001"
