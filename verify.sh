#!/bin/bash


docker compose up -d > /dev/null 2>&1


TIMEOUT=60
ELAPSED=0
HEALTHY=false

while [ $ELAPSED -lt $TIMEOUT ]; do
    STATUS=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' serving-stack-serving-1 2>/dev/null)
    if [ "$STATUS" = "healthy" ]; then
        HEALTHY=true
        break
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
done

if [ "$HEALTHY" = true ]; then

    docker compose down > /dev/null 2>&1
    echo "GREEN CHECK: PASS"
    exit 0
else
    docker compose down > /dev/null 2>&1
    echo "GREEN CHECK: FAIL (healthcheck timed out or failed)"
    exit 1
fi
