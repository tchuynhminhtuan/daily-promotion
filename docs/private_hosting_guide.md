# 🔒 Transition Guide: Private Repo + Public Site (Vercel)

Follow these steps to secure your code while keeping your reports accessible.

## Part 1: Make Repository Private
**⚠️ Warning:** This will immediately take down your current `github.io` site.

1.  Go to your Repository Settings: [Daily Promotion Settings](https://github.com/tchuynhminhtuan/daily-promotion/settings)
2.  Scroll to the bottom **"Danger Zone"**.
3.  Click **"Change visibility"**.
4.  Select **"Make private"**.
5.  Confirm by typing the repository name.
    *   *Result:* Your code is now hidden. Your GitHub Pages site is now 404.

---

## Part 2: Set Up Vercel (Free Static Hosting)
Vercel is the industry standard for deploying static sites from GitHub. It connects safely to private repos.

### Step A: Account & Connect
1.  Go to [vercel.com](https://vercel.com/) and **Sign Up**.
2.  Choose **"Continue with GitHub"**.
3.  Follow the prompts to authorize Vercel to access your repositories.

### Step B: Import Project
1.  On your Vercel Dashboard, click **"Add New..."** -> **"Project"**.
2.  You should see your `daily-promotion` repo in the list.
3.  Click **"Import"**.

### Step C: Configure Build (CRITICAL)
Vercel needs to know *what* to show (your `docs` folder).

1.  In the "Configure Project" screen:
    *   **Project Name:** `daily-promotion` (or whatever you like).
    *   **Framework Preset:** leave as `Other`.
2.  **Build and Output Settings** (Click to expand):
    *   **Root Directory:** LEAVE EMPTY (`./`).
    *   **Output Directory:** Click "Override" and type: `docs`
        *   *Why?* Because your HTML files live in the `docs/` folder.
3.  Click **"Deploy"**.

### Step D: Done!
*   Vercel will build your site (takes ~10 seconds).
*   It will give you a new URL like `https://daily-promotion-tchuynhminhtuan.vercel.app`.
*   **Bonus:** Every time your scraper runs and pushes to GitHub, Vercel detects the change and updates the site automatically!

---

## Part 3: Verify Links
Once deployed, check your new URLs:
*   **Main Report:** `https://<YOUR-VERCEL-URL>/index.html`
*   **Marshall Report:** `https://<YOUR-VERCEL-URL>/marshall.html`
