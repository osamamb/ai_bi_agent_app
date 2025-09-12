# 🚀 Deployment Guide - AI BI Agent App

This guide provides multiple ways to deploy your AI BI Agent App from Cursor to GitHub repository: [https://github.com/osamamb/ai_bi_agent_app.git](https://github.com/osamamb/ai_bi_agent_app.git)

## 🎯 Quick Start

### Method 1: Using the Deployment Script (Recommended)
```bash
# Deploy with custom message
./deploy.sh "Added new feature"

# Deploy with default timestamp message
./deploy.sh
```

### Method 2: Using Git Aliases
```bash
# Deploy with custom message
git deploy "Your commit message"

# Quick deploy with default message
git quick-push
```

### Method 3: Using Makefile
```bash
# Deploy with custom message
make deploy MSG="Your commit message"

# Quick deploy
make quick-deploy

# Show help
make help
```

### Method 4: Using Cursor/VS Code Tasks
1. Open Command Palette (`Cmd+Shift+P` on Mac, `Ctrl+Shift+P` on Windows/Linux)
2. Type "Tasks: Run Task"
3. Select one of:
   - `🚀 Deploy to GitHub` (with custom message)
   - `⚡ Quick Deploy` (with default message)

## 📋 Available Commands

### Git Aliases
- `git deploy "message"` - Deploy with custom commit message
- `git quick-push` - Quick deploy with default message

### Deployment Script
- `./deploy.sh` - Deploy with timestamp
- `./deploy.sh "message"` - Deploy with custom message

### Makefile Commands
- `make deploy MSG="message"` - Deploy with custom message
- `make quick-deploy` - Quick deploy
- `make status` - Show git status
- `make log` - Show recent commits
- `make pull` - Pull latest changes
- `make install` - Install dependencies
- `make test` - Run tests
- `make format` - Format code
- `make lint` - Lint code
- `make clean` - Clean temporary files

### Cursor/VS Code Tasks
- `🚀 Deploy to GitHub` - Deploy with custom message prompt
- `⚡ Quick Deploy` - Quick deploy with default message
- `📊 Git Status` - Show current git status
- `📝 Git Log` - Show last 10 commits
- `🔄 Pull from GitHub` - Pull latest changes

## 🔄 GitHub Actions Workflow

The repository includes a GitHub Actions workflow that automatically:

1. **Tests & Validates** on every push/PR:
   - Code formatting check (Black)
   - Import sorting check (isort)
   - Linting (flake8)
   - Runs tests if available

2. **Deployment Notification** on main branch:
   - Confirms successful deployment
   - Provides deployment summary
   - Shows changed files

## 🛠️ Setup Instructions

### One-Time Setup
The deployment tools are already configured! Just make sure the deployment script is executable:

```bash
chmod +x deploy.sh
```

### Authentication
Make sure you have GitHub authentication set up:

1. **Personal Access Token** (if using HTTPS)
2. **SSH Keys** (if using SSH)
3. **GitHub CLI** authentication

## 📁 Files Created

The deployment setup includes these new files:

```
ai_bi_telstra_agent/
├── deploy.sh                    # Main deployment script
├── Makefile                     # Make commands for deployment
├── DEPLOYMENT.md               # This documentation
├── .vscode/
│   └── tasks.json              # Cursor/VS Code tasks
└── .github/
    └── workflows/
        └── deploy.yml          # GitHub Actions workflow
```

## 🎨 Customization

### Modify Deployment Script
Edit `deploy.sh` to customize:
- Default commit messages
- Pre-deployment checks
- Post-deployment actions

### Add New Tasks
Edit `.vscode/tasks.json` to add new Cursor/VS Code tasks.

### Extend Makefile
Add new commands to `Makefile` for additional functionality.

### GitHub Actions
Modify `.github/workflows/deploy.yml` to:
- Add more tests
- Deploy to different environments
- Send notifications

## 🚨 Troubleshooting

### Permission Denied
```bash
chmod +x deploy.sh
```

### Authentication Issues
1. Check your GitHub token/SSH keys
2. Verify repository permissions
3. Test with: `git push origin main`

### Script Not Found
Make sure you're in the project directory:
```bash
cd /path/to/ai_bi_telstra_agent
```

## 💡 Tips

1. **Use descriptive commit messages** for better project history
2. **Test locally** before deploying with `make test`
3. **Format code** before deploying with `make format`
4. **Check status** with `make status` or `git status`
5. **Pull regularly** with `make pull` to stay updated

## 🔗 Repository Links

- **GitHub Repository**: [https://github.com/osamamb/ai_bi_agent_app](https://github.com/osamamb/ai_bi_agent_app)
- **Actions**: [https://github.com/osamamb/ai_bi_agent_app/actions](https://github.com/osamamb/ai_bi_agent_app/actions)
- **Issues**: [https://github.com/osamamb/ai_bi_agent_app/issues](https://github.com/osamamb/ai_bi_agent_app/issues)

---

*Happy deploying! 🚀*
