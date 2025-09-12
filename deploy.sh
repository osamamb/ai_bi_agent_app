#!/bin/bash

# AI BI Agent App - Deployment Script
# Usage: ./deploy.sh [commit_message]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default commit message
COMMIT_MSG="${1:-Auto-deploy from Cursor $(date '+%Y-%m-%d %H:%M:%S')}"

echo -e "${BLUE}🚀 AI BI Agent App Deployment Script${NC}"
echo -e "${BLUE}====================================${NC}"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

# Run validation if script exists
if [[ -f "validate.sh" ]]; then
    echo -e "${BLUE}🔍 Running pre-deployment validation...${NC}"
    if ./validate.sh; then
        echo -e "${GREEN}✅ Validation passed${NC}"
    else
        echo -e "${RED}❌ Validation failed${NC}"
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}❌ Deployment cancelled${NC}"
            exit 1
        fi
    fi
fi

# Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}📝 Found uncommitted changes${NC}"
    
    # Show status
    echo -e "${BLUE}Current status:${NC}"
    git status --short
    
    # Add all changes
    echo -e "${YELLOW}📦 Adding all changes...${NC}"
    git add .
    
    # Commit changes
    echo -e "${YELLOW}💾 Committing with message: '${COMMIT_MSG}'${NC}"
    git commit -m "$COMMIT_MSG"
else
    echo -e "${GREEN}✅ No uncommitted changes found${NC}"
fi

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    echo -e "${YELLOW}⚠️  Warning: You're on branch '$CURRENT_BRANCH', not 'main'${NC}"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Deployment cancelled${NC}"
        exit 1
    fi
fi

# Push to GitHub
echo -e "${YELLOW}🌐 Pushing to GitHub repository...${NC}"

# Check if GITHUB_TOKEN is set, otherwise use regular git push
if [[ -n "$GITHUB_TOKEN" ]]; then
    REPO_URL="https://${GITHUB_TOKEN}@github.com/osamamb/ai_bi_agent_app.git"
else
    REPO_URL="origin"
fi

if git push "$REPO_URL" "$CURRENT_BRANCH"; then
    echo -e "${GREEN}✅ Successfully deployed to GitHub!${NC}"
    echo -e "${GREEN}🔗 Repository: https://github.com/osamamb/ai_bi_agent_app${NC}"
    
    # Show latest commit
    echo -e "${BLUE}📋 Latest commit:${NC}"
    git log --oneline -1
else
    echo -e "${RED}❌ Failed to push to GitHub${NC}"
    echo -e "${YELLOW}💡 You might need to authenticate or check your internet connection${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
