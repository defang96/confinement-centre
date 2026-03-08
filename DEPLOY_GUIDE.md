# 🌸 How to Deploy the Confinement Centre App Online

**Total cost: ~$5/month (Railway) + $0 (Netlify)**

---

## PART 1 — Deploy the Backend to Railway (~15 mins)

Railway hosts your Python backend and database online.

### Step 1: Create a free GitHub account
1. Go to **github.com** and sign up for a free account
2. Confirm your email

### Step 2: Upload your backend to GitHub
1. Go to **github.com/new** to create a new repository
2. Name it: `confinement-centre-backend`
3. Set it to **Private** (so your code is not public)
4. Click **Create repository**
5. On the next page, click **"uploading an existing file"**
6. Drag and drop ALL files from your `confinement-centre/backend/` folder:
   - main.py
   - requirements.txt
   - Procfile
   - railway.toml
7. Click **Commit changes**

### Step 3: Create a Railway account
1. Go to **railway.app**
2. Click **"Start a New Project"**
3. Sign up using your GitHub account

### Step 4: Deploy to Railway
1. In Railway, click **"New Project"**
2. Click **"Deploy from GitHub repo"**
3. Select your `confinement-centre-backend` repo
4. Railway will automatically detect it's a Python app and deploy it
5. Wait 2-3 minutes for the deployment to finish ✅

### Step 5: Add a persistent volume (so your database isn't lost)
1. In Railway, click on your deployed service
2. Click the **"Volumes"** tab
3. Click **"Add Volume"**
4. Set the mount path to: `/app`
5. Click **"Add"** — this saves your database permanently

### Step 6: Get your live URL
1. In Railway, click on your service → **"Settings"** tab
2. Under **Domains**, click **"Generate Domain"**
3. You'll get a URL like: `https://confinement-centre-production.up.railway.app`
4. **Copy this URL** — you'll need it in Part 2

---

## PART 2 — Update the Frontend with your live URL (~5 mins)

### Step 1: Edit index.html
1. Open your `confinement-centre/frontend/index.html` file in a text editor
   (Right-click → Open With → TextEdit on Mac, or Notepad on Windows)
2. Find this line near the top (around line 83):
   ```
   const API_BASE = "http://localhost:8000";
   ```
3. Replace it with your Railway URL:
   ```
   const API_BASE = "https://YOUR-RAILWAY-URL.up.railway.app";
   ```
4. Save the file

---

## PART 3 — Deploy the Frontend to Netlify (Free, ~5 mins)

Netlify hosts your HTML file so anyone can access it from a web link.

### Step 1: Create a Netlify account
1. Go to **netlify.com**
2. Sign up for free (use your email or GitHub account)

### Step 2: Deploy your frontend
1. Once logged in, you'll see a drag-and-drop area that says:
   **"Drag and drop your site folder here"**
2. Drag your entire `frontend` folder into that area
3. Wait 30 seconds — Netlify will give you a live URL like:
   `https://amazing-confinement-abc123.netlify.app`

### Step 3: Share the link!
That's your live app URL. Share it with your staff and mothers! 🎉

---

## 💡 Summary of Costs

| Service  | What it does           | Cost         |
|----------|------------------------|--------------|
| Railway  | Runs your backend + DB | ~$5/month    |
| Netlify  | Hosts your website     | Free         |
| GitHub   | Stores your code       | Free         |
| **Total**|                        | **~$5/month**|

---

## 🔒 Security Note

Once live, consider changing the default passwords for all accounts
(mother1, nurse1, chef1, etc.) through the Admin panel in the app.

---

## ❓ Need Help?

Just ask Claude in the Cowork app!
