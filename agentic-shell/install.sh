#!/usr/bin/env bash
# install.sh - One-liner installer for Agentic Shell 2.0

set -e

REPO="https://github.com/yourorg/agentic-shell.git"
INSTALL_DIR="${HOME}/agentic-shell"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Agentic Shell 2.0 - One-Line Installer    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check for git
if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Please install git first."
    exit 1
fi

# Check for curl
if ! command -v curl &> /dev/null; then
    echo "❌ Curl not found. Please install curl first."
    exit 1
fi

# Check for python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Check for docker
if ! command -v docker &> /dev/null; then
    echo "⚠️ Docker not found. Some features may be limited."
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"
echo ""

# Clone repository
echo -e "${YELLOW}Downloading Agentic Shell...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo "📁 Installation directory exists. Updating..."
    cd "$INSTALL_DIR"
    git pull
else
    git clone --depth 1 "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
echo -e "${GREEN}✅ Downloaded${NC}"
echo ""

# Run setup
echo -e "${YELLOW}Running setup...${NC}"
chmod +x setup.sh
./setup.sh

echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo -e "To start using Agentic Shell:"
echo -e "  cd ${INSTALL_DIR}"
echo -e "  make up"
echo -e "  ./agentic-shell"
echo ""
echo -e "Or add to PATH:"
echo -e "  export PATH=\"\$PATH:${INSTALL_DIR}\""
echo -e "  agentic-shell"