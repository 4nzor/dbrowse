#!/bin/bash
# Get SHA256 hash for a GitHub release

VERSION=${1:-"0.1.0"}
REPO="4nzor/dbrowse"

if [ -z "$1" ]; then
    echo "Usage: ./scripts/get_sha256.sh <version>"
    echo "Example: ./scripts/get_sha256.sh 0.1.0"
    exit 1
fi

echo "📥 Downloading release archive..."
URL="https://github.com/${REPO}/archive/refs/tags/v${VERSION}.tar.gz"

# Download and calculate SHA256
SHA256=$(curl -sL "$URL" | shasum -a 256 | awk '{print $1}')

if [ -z "$SHA256" ]; then
    echo "❌ Error: Could not download or calculate SHA256"
    echo "   Make sure the release exists: https://github.com/${REPO}/releases/tag/v${VERSION}"
    exit 1
fi

echo ""
echo "✅ SHA256 for v${VERSION}:"
echo ""
echo "   sha256 \"${SHA256}\""
echo ""
echo "📋 Copy this to Formula/dbrowse.rb"

