# 🚀 Hugging Face Spaces Deployment Guide

This guide walks you through deploying the Email Triage OpenEnv to Hugging Face Spaces.

## Prerequisites

- Hugging Face account (free): https://huggingface.co/join
- Git installed on your machine
- Your HF Space already created: https://huggingface.co/spaces/hharshhsaini/email-triage-env

## Step 1: Get Your Hugging Face Access Token

1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Name it (e.g., "email-triage-deploy")
4. Select "Write" permissions
5. Click "Generate token"
6. **Copy the token** - you'll need it as your password

## Step 2: Clone Your HF Space

```bash
# Clone the HF Space repository
git clone https://huggingface.co/spaces/hharshhsaini/email-triage-env hf-space
cd hf-space
```

When prompted for credentials:
- Username: `hharshhsaini`
- Password: `<paste your HF token here>`

## Step 3: Copy Project Files

From your project root directory:

```bash
# Copy all necessary files to the HF space
cp email-triage-env/app.py hf-space/
cp email-triage-env/baseline.py hf-space/
cp email-triage-env/Dockerfile hf-space/
cp email-triage-env/requirements.txt hf-space/
cp email-triage-env/openenv.yaml hf-space/
cp email-triage-env/README.md hf-space/

# Copy directories
cp -r email-triage-env/env hf-space/
cp -r email-triage-env/data hf-space/
cp -r email-triage-env/tests hf-space/
```

## Step 4: Commit and Push to HF Space

```bash
cd hf-space

# Configure git (if not already done)
git config user.email "your-email@example.com"
git config user.name "Harsh Saini"

# Add all files
git add .

# Commit
git commit -m "Deploy Email Triage OpenEnv"

# Push to HF Space
git push
```

When prompted for password, use your HF access token.

## Step 5: Wait for Build

- Go to https://huggingface.co/spaces/hharshhsaini/email-triage-env
- You'll see "Building..." status
- Wait 5-10 minutes for Docker build to complete
- Status will change to "Running" when ready

## Step 6: Verify Deployment

Test the deployed API:

```bash
# Health check
curl https://hharshhsaini-email-triage-env.hf.space/health

# Get available tasks
curl https://hharshhsaini-email-triage-env.hf.space/tasks

# Test reset endpoint
curl -X POST https://hharshhsaini-email-triage-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "priority_triage"}'
```

## Step 7: Submit to Competition

Once deployed and verified, submit both URLs:

1. **GitHub Repository**: https://github.com/hharshhsaini/email-triage-env
2. **Hugging Face Space**: https://huggingface.co/spaces/hharshhsaini/email-triage-env

## Troubleshooting

### Build Fails

- Check the "Logs" tab in your HF Space
- Common issues:
  - Missing files: Make sure all files were copied
  - Dockerfile errors: Verify Dockerfile syntax
  - Dependencies: Check requirements.txt

### Space Shows "Sleeping"

- HF Spaces on free tier sleep after inactivity
- First request will wake it up (may take 30 seconds)
- Consider upgrading to persistent hardware if needed

### API Not Responding

- Check if space is "Running" (not "Building" or "Error")
- Try the health endpoint first
- Check logs for errors

## Configuration Notes

### Space Settings

Your HF Space is configured with:
- **SDK**: Docker (required for OpenEnv)
- **Hardware**: CPU basic (free tier - sufficient for this environment)
- **Visibility**: Public (required for competition)

### Environment Variables

No environment variables needed for basic operation. If you want to enable the baseline script on HF:

1. Go to Space Settings
2. Add secret: `OPENAI_API_KEY` = `your-key`
3. Restart space

## Re-submission

You can re-submit to the competition multiple times. The competition evaluates your latest submission, so feel free to iterate and improve!

## Support

- HF Spaces Docs: https://huggingface.co/docs/hub/spaces
- OpenEnv Spec: https://github.com/OpenEnv-org/OpenEnv
- Issues: https://github.com/hharshhsaini/email-triage-env/issues
