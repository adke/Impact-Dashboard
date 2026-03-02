#!/usr/bin/env bash
set -euo pipefail

# Install backend dependencies
pip install -r backend/requirements.txt

# Build the frontend
cd frontend
npm install
npm run build
