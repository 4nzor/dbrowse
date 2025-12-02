#!/bin/bash
# Script to create a GitHub release for dbrowse

set -e

VERSION=${1:-"0.1.0"}
REPO="4nzor/dbrowse"

echo "🚀 Creating release v${VERSION} for ${REPO}"

# Check if version is provided
if [ -z "$1" ]; then
    echo "Usage: ./scripts/create_release.sh <version>"
    echo "Example: ./scripts/create_release.sh 0.1.0"
    exit 1
fi

# Check if git is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Warning: You have uncommitted changes"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    echo "⚠️  Tag v${VERSION} already exists"
    read -p "Delete and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d "v${VERSION}"
        git push origin ":refs/tags/v${VERSION}" 2>/dev/null || true
    else
        exit 1
    fi
fi

# Create and push tag
echo "📝 Creating tag v${VERSION}..."
git tag -a "v${VERSION}" -m "Release v${VERSION}"
git push origin "v${VERSION}"

# Create release (if gh is installed)
if command -v gh &> /dev/null; then
    echo "📦 Creating GitHub release..."
    gh release create "v${VERSION}" \
        --title "v${VERSION}" \
        --notes "Release v${VERSION} of dbrowse" \
        --latest
    
    echo "✅ Release created successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Get SHA256: curl -L https://github.com/${REPO}/archive/refs/tags/v${VERSION}.tar.gz | shasum -a 256"
    echo "2. Update Formula/dbrowse.rb with the SHA256"
    echo "3. Update version in update_checker.py and pyproject.toml for next release"
else
    echo "⚠️  GitHub CLI (gh) not installed"
    echo "📝 Tag created. Please create release manually:"
    echo "   https://github.com/${REPO}/releases/new?tag=v${VERSION}"
    echo ""
    echo "📋 After creating release, get SHA256:"
    echo "   curl -L https://github.com/${REPO}/archive/refs/tags/v${VERSION}.tar.gz | shasum -a 256"
fi

