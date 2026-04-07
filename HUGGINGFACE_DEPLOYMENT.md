# Hugging Face Spaces Deployment Guide

## 🚀 Step-by-Step Deployment Instructions

### Prerequisites
- Hugging Face account (create at https://huggingface.co/join)
- GitHub repository already set up ✓ (https://github.com/hharshhsaini/email-triage-env)

---

## Method 1: Direct GitHub Integration (Recommended)

### Step 1: Create New Space
1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"** button
3. Fill in the details:
   - **Space name:** `email-triage-env`
   - **License:** MIT
   - **Select SDK:** Choose **"Docker"**
   - **Space hardware:** CPU basic (free tier is fine)
   - **Visibility:** Public

4. Click **"Create Space"**

### Step 2: Connect to GitHub
1. After creating the space, you'll see the space page
2. Click on **"Settings"** tab (top right)
3. Scroll down to **"Repository"** section
4. Click **"Link to GitHub"**
5. Authorize Hugging Face to access your GitHub
6. Select repository: `hharshhsaini/email-triage-env`
7. Click **"Link repository"**

### Step 3: Configure Sync
1. In Settings, find **"Sync from GitHub"**
2. Enable **"Automatic sync"**
3. Set branch to: `main`
4. Click **"Save"**

### Step 4: Wait for Build
1. Go back to **"App"** tab
2. Space will automatically build from your Dockerfile
3. Wait 5-10 minutes for first build
4. You'll see build logs in real-time

### Step 5: Verify Deployment
Once built, test your endpoints:
```bash
# Replace YOUR_USERNAME with your HF username
curl https://YOUR_USERNAME-email-triage-env.hf.space/health
curl https://YOUR_USERNAME-email-triage-env.hf.space/demo
```

---

## Method 2: Manual Git Push (Alternative)

### Step 1: Create New Space
1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Fill in details (same as Method 1)
4. Click **"Create Space"**

### Step 2: Clone HF Space Repository
```bash
# Install git-lfs if not already installed
git lfs install

# Clone your new space
git clone https://huggingface.co/spaces/YOUR_USERNAME/email-triage-env
cd email-triage-env
```

### Step 3: Copy Files from GitHub Repo
```bash
# Copy all files from your GitHub repo
cp -r /path/to/email-triage-env/* .

# Make sure these files are present:
ls -la
# Should see: Dockerfile, README.md, app.py, env/, tests/, etc.
```

### Step 4: Push to Hugging Face
```bash
git add .
git commit -m "Initial deployment"
git push
```

### Step 5: Wait for Build
Space will automatically build and deploy.

---

## 🔍 Verification Checklist

After deployment, verify everything works:

### 1. Health Check
```bash
curl https://YOUR_USERNAME-email-triage-env.hf.space/health
# Expected: {"status":"ok"}
```

### 2. Tasks Endpoint
```bash
curl https://YOUR_USERNAME-email-triage-env.hf.space/tasks
# Expected: JSON array with 3 tasks
```

### 3. Demo Endpoint
```bash
curl https://YOUR_USERNAME-email-triage-env.hf.space/demo
# Expected: Demo transcript JSON
```

### 4. Reset Endpoint
```bash
curl -X POST https://YOUR_USERNAME-email-triage-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "priority_triage", "seed": 42}'
# Expected: Observation JSON with email data
```

### 5. Validate Endpoint
```bash
curl -X POST https://YOUR_USERNAME-email-triage-env.hf.space/validate
# Expected: {"status": "valid", "detail": "Environment fully OpenEnv compliant."}
```

---

## 📝 Your URLs for Submission

Once deployed, you'll have:

**GitHub Repository URL:**
```
https://github.com/hharshhsaini/email-triage-env
```

**Hugging Face Space URL:**
```
https://huggingface.co/spaces/YOUR_USERNAME/email-triage-env
```

Replace `YOUR_USERNAME` with your actual Hugging Face username.

---

## 🐛 Troubleshooting

### Issue: Build Fails
**Solution:** Check build logs in HF Space
- Go to "Settings" → "Logs"
- Look for error messages
- Common issues:
  - Missing dependencies in requirements.txt
  - Dockerfile syntax errors
  - Port not exposed correctly

### Issue: Space Shows "Building..."
**Solution:** Wait 5-10 minutes for first build
- Docker builds can take time
- Check logs for progress
- If stuck >15 minutes, restart build

### Issue: Endpoints Return 404
**Solution:** Check if app is running
- Verify Dockerfile CMD is correct
- Check logs for startup errors
- Ensure port 7860 is exposed

### Issue: Health Check Fails
**Solution:** 
```bash
# Check if server started
curl https://YOUR_SPACE_URL/
# Should return API info

# Check logs in HF Space settings
```

---

## 🎯 Competition Submission

After successful deployment:

1. **GitHub Repository URL:**
   ```
   https://github.com/hharshhsaini/email-triage-env
   ```

2. **Hugging Face Space URL:**
   ```
   https://huggingface.co/spaces/YOUR_USERNAME/email-triage-env
   ```

3. **Verify automated checks pass:**
   - Space deploys ✓
   - Health endpoint responds ✓
   - Reset endpoint works ✓
   - Step endpoint works ✓
   - Validate endpoint returns "valid" ✓

4. **Submit both URLs to competition**

---

## 📊 Expected Build Time

- **First build:** 5-10 minutes
- **Subsequent builds:** 2-5 minutes (cached layers)

---

## 🔄 Updating Your Space

### If using GitHub integration:
```bash
# Make changes locally
git add .
git commit -m "Update description"
git push origin main

# HF Space will auto-sync and rebuild
```

### If using manual push:
```bash
cd email-triage-env  # Your HF space repo
# Make changes
git add .
git commit -m "Update description"
git push
```

---

## 💡 Tips

1. **Use GitHub integration** - Easier to maintain
2. **Enable auto-sync** - Automatic updates from GitHub
3. **Check logs** - If something fails, logs tell you why
4. **Test locally first** - Run `docker build` before pushing
5. **Free tier is fine** - CPU basic is sufficient for this project

---

## 🎓 What Happens During Build

1. HF pulls your repository
2. Reads Dockerfile
3. Builds Docker image
4. Installs dependencies from requirements.txt
5. Starts uvicorn server on port 7860
6. Runs health check
7. Makes space publicly accessible

---

## ✅ Success Indicators

You'll know deployment succeeded when:
- ✅ Space shows "Running" status (not "Building")
- ✅ Green checkmark next to space name
- ✅ `/health` endpoint returns `{"status":"ok"}`
- ✅ `/demo` endpoint returns demo transcript
- ✅ No errors in logs

---

## 📞 Need Help?

If you encounter issues:
1. Check HF Space logs (Settings → Logs)
2. Verify Dockerfile builds locally: `docker build -t test .`
3. Test locally: `docker run -p 7860:7860 test`
4. Check HF Spaces documentation: https://huggingface.co/docs/hub/spaces

---

## 🎉 After Successful Deployment

Your space will be live at:
```
https://huggingface.co/spaces/YOUR_USERNAME/email-triage-env
```

You can:
- Share the link
- Embed in websites
- Use API endpoints
- Submit to competition

**Ready to deploy!** 🚀
