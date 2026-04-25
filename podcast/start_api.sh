#!/bin/bash
# Script to start the Podcast Downloader API server

# Default values
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8002}  # Changed from 8000 (used by RMLJ Manga API)

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --localhost-only)
            HOST="127.0.0.1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--host HOST] [--port PORT] [--localhost-only]"
            echo "  --host HOST          Bind to specific host (default: 0.0.0.0)"
            echo "  --port PORT          Use specific port (default: 8002)"
            echo "  --localhost-only     Bind to localhost only (127.0.0.1)"
            exit 1
            ;;
    esac
done

# Activate virtual environment
cd "$(dirname "$0")"
source .venv/bin/activate

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Please edit .env and set PODCAST_API_KEY before starting the server."
        exit 1
    else
        echo "Error: .env.example not found. Please create .env file manually."
        exit 1
    fi
fi

echo "Starting Podcast Downloader API server..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Access: http://$HOST:$PORT"
if [ "$HOST" = "0.0.0.0" ]; then
    echo "  Public IP: http://159.195.45.195:$PORT"
fi
echo ""

python -m uvicorn app:app --host "$HOST" --port "$PORT"
