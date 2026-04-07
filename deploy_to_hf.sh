#!/bin/bash

# Email Triage OpenEnv - Hugging Face Deployment Script
# This script automates the deployment to HF Spaces

set -e  # Exit on error

echo "🚀 Email Triage OpenEnv - HF Spaces Deployment"
echo "=============================================="
echo ""

# Check if hf-space directory exists
if [ -d "hf-space" ]; then
    echo "⚠️  hf-space directory already exists. Remove it? (y/n)"
    read -r response
    if [ "$response" = "y" ]; then
        rm -rf hf-space
        echo "✅ Removed existing hf-space directory"
    else
        echo "❌ Deployment cancelled"
        exit 1
    fi
fi

# Clone HF Space
echo ""
echo "📥 Cloning HF Space repository..."
git clone https://huggingface.co/spaces/hharshhsaini/email-triage-env hf-space

# Copy files
echo ""
echo "📋 Copying project files..."
cp app.py hf-space/
cp baseline.py hf-space/
cp Dockerfile hf-space/
cp requirements.txt hf-space/
cp openenv.yaml hf-space/
cp README.md hf-space/

echo "📁 Copying directories..."
cp -r env hf-space/
cp -r data hf-space/
cp -r tests hf-space/

# Navigate to hf-space
cd hf-space

# Git configuration
echo ""
echo "⚙️  Configuring git..."
git config user.email "harsh@example.com"
git config user.name "Harsh Saini"

# Add and commit
echo ""
echo "💾 Committing files..."
git add .
git commit -m "Deploy Email Triage OpenEnv - $(date '+%Y-%m-%d %H:%M:%S')"

# Push
echo ""
echo "🚀 Pushing to HF Space..."
echo "⚠️  You'll be prompted for your HF username and token"
echo "   Username: hharshhsaini"
echo "   Password: <paste your HF access token>"
echo ""
git push

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔗 Your HF Space: https://huggingface.co/spaces/hharshhsaini/email-triage-env"
echo ""
echo "⏳ Wait 5-10 minutes for the build to complete"
echo ""
echo "🧪 Test your deployment:"
echo "   curl https://hharshhsaini-email-triage-env.hf.space/health"
echo ""
