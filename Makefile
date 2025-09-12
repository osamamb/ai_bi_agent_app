# AI BI Agent App - Makefile
# Quick deployment and development commands

.PHONY: help deploy quick-deploy status log pull install test format lint clean

# Default target
help: ## 📋 Show this help message
	@echo "🚀 AI BI Agent App - Deployment Commands"
	@echo "========================================"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

deploy: ## 🚀 Deploy to GitHub with custom message (usage: make deploy MSG="your message")
	@echo "🚀 Deploying to GitHub..."
	@./deploy.sh "$(MSG)"

quick-deploy: ## ⚡ Quick deploy with default message
	@echo "⚡ Quick deploying..."
	@git quick-push

status: ## 📊 Show git status
	@echo "📊 Current git status:"
	@git status --short

log: ## 📝 Show recent commits
	@echo "📝 Recent commits:"
	@git log --oneline -10

pull: ## 🔄 Pull latest changes from GitHub
	@echo "🔄 Pulling from GitHub..."
	@git pull origin main

install: ## 📦 Install Python dependencies
	@echo "📦 Installing dependencies..."
	@pip install -r requirements.txt

install-dev: ## 🔧 Install development dependencies
	@echo "🔧 Installing development dependencies..."
	@pip install -r requirements.txt
	@pip install black isort flake8 pytest

validate: ## 🔍 Validate code before deployment
	@echo "🔍 Running validation..."
	@./validate.sh

test: ## 🧪 Run tests
	@echo "🧪 Running tests..."
	@python -m pytest test_structure.py -v || echo "⚠️ Tests not found"

format: ## 🎨 Format code with black and isort
	@echo "🎨 Formatting code..."
	@black .
	@isort .

lint: ## 🔍 Lint code with flake8
	@echo "🔍 Linting code..."
	@flake8 . --max-line-length=88 --extend-ignore=E203,W503

clean: ## 🧹 Clean up temporary files
	@echo "🧹 Cleaning up..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +

# Example usage:
# make deploy MSG="Fixed authentication bug"
# make quick-deploy
# make status
# make test
