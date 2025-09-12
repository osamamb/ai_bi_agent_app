#!/bin/bash

# AI BI Agent App - Deployment Setup Script
# This script sets up your GitHub token for easy deployment

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 AI BI Agent App - Deployment Setup${NC}"
echo -e "${BLUE}====================================${NC}"

# Check if token is provided as argument
if [[ -n "$1" ]]; then
    GITHUB_TOKEN="$1"
else
    echo -e "${YELLOW}Please provide your GitHub token as an argument:${NC}"
    echo -e "${YELLOW}./setup-deployment.sh YOUR_GITHUB_TOKEN${NC}"
    echo ""
    echo -e "${YELLOW}Or export it as an environment variable:${NC}"
    echo -e "${YELLOW}export GITHUB_TOKEN=YOUR_GITHUB_TOKEN${NC}"
    exit 1
fi

# Create or update .env file
echo -e "${YELLOW}📝 Setting up environment variables...${NC}"
echo "GITHUB_TOKEN=$GITHUB_TOKEN" > .env

# Add .env to .gitignore if not already there
if ! grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo ".env" >> .gitignore
    echo -e "${GREEN}✅ Added .env to .gitignore${NC}"
fi

# Create deployment alias script
cat > deploy-quick.sh << 'EOF'
#!/bin/bash
# Quick deployment script that sources .env file

if [[ -f .env ]]; then
    source .env
fi

if [[ -z "$GITHUB_TOKEN" ]]; then
    echo "❌ GITHUB_TOKEN not found. Run ./setup-deployment.sh YOUR_TOKEN first"
    exit 1
fi

export GITHUB_TOKEN
./deploy.sh "$@"
EOF

chmod +x deploy-quick.sh

echo -e "${GREEN}✅ Deployment setup complete!${NC}"
echo ""
echo -e "${BLUE}📋 You can now deploy using:${NC}"
echo -e "${GREEN}  ./deploy-quick.sh \"Your commit message\"${NC}"
echo -e "${GREEN}  ./deploy-quick.sh${NC} (for default message)"
echo ""
echo -e "${YELLOW}⚠️  Your GitHub token is stored in .env (which is git-ignored)${NC}"
echo -e "${YELLOW}   Keep this file secure and don't share it!${NC}"
