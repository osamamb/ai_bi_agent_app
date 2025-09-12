#!/bin/bash

# AI BI Agent App - Local Validation Script
# Run this before deploying to catch issues early

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 AI BI Agent App - Local Validation${NC}"
echo -e "${BLUE}====================================${NC}"

# Check Python syntax
echo -e "${YELLOW}📝 Checking Python syntax...${NC}"
if python3 -m py_compile app.py; then
    echo -e "${GREEN}✅ app.py syntax OK${NC}"
else
    echo -e "${RED}❌ app.py has syntax errors${NC}"
    exit 1
fi

if python3 -m py_compile langchain_agents.py; then
    echo -e "${GREEN}✅ langchain_agents.py syntax OK${NC}"
else
    echo -e "${RED}❌ langchain_agents.py has syntax errors${NC}"
    exit 1
fi

if python3 -m py_compile langchain_tools.py; then
    echo -e "${GREEN}✅ langchain_tools.py syntax OK${NC}"
else
    echo -e "${RED}❌ langchain_tools.py has syntax errors${NC}"
    exit 1
fi

# Check if requirements.txt exists
if [[ -f "requirements.txt" ]]; then
    echo -e "${GREEN}✅ requirements.txt found${NC}"
else
    echo -e "${YELLOW}⚠️ requirements.txt not found${NC}"
fi

# Check if app.yaml exists
if [[ -f "app.yaml" ]]; then
    echo -e "${GREEN}✅ app.yaml found${NC}"
else
    echo -e "${YELLOW}⚠️ app.yaml not found${NC}"
fi

# Check GitHub Actions workflow
if [[ -f ".github/workflows/deploy.yml" ]]; then
    echo -e "${GREEN}✅ GitHub Actions workflow found${NC}"
else
    echo -e "${YELLOW}⚠️ GitHub Actions workflow not found${NC}"
fi

echo -e "${GREEN}🎉 Local validation completed successfully!${NC}"
echo -e "${BLUE}Your code is ready for deployment.${NC}"
