# Guide: Securing Google Colab Access to Private Repositories

Since your repository is now **Private**, standard `git clone` commands will fail in Google Colab because they require authentication. To solve this securely without hardcoding your password or token, we use **GitHub Personal Access Tokens (PAT)** and **Colab Secrets**.

## Step 1: Generate a GitHub Personal Access Token (PAT)

1.  Go to [GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)](https://github.com/settings/tokens).
2.  Click **"Generate new token"** (select **Generate new token (classic)**).
3.  Give it a name (e.g., "Colab Access").
4.  Select the **`repo`** scope (this allows full control of private repositories).
5.  Set an expiration date (e.g., 90 days).
6.  Click **"Generate token"**.
7.  **Copy the token immediately.** You won't see it again!

## Step 2: Add the Token to Colab Secrets

1.  Open your Google Colab notebook.
2.  Click the **Key icon (Secrets)** in the left sidebar.
3.  Click **"+ Add new secret"**.
4.  Set the Name to `GITHUB_TOKEN`.
5.  Paste your GitHub PAT into the Value field.
6.  **Enable "Notebook access"** for this secret.

## Step 3: Update your Notebook Code

Replace your current cloning/pulling code with the following snippet. This code retrieves the token from Colab's secure storage and uses it for authentication.

```python
from google.colab import userdata
import os

# 1. Retrieve the secret securely
try:
    GITHUB_TOKEN = userdata.get('GITHUB_TOKEN')
except:
    print("❌ Error: 'GITHUB_TOKEN' not found in Colab Secrets.")
    print("Please follow the guide to add it.")
    raise

# 2. Define the remote URL with the token
REPO_NAME = "daily-promotion"
GITHUB_USER = "tchuynhminhtuan"
REPO_URL = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{REPO_NAME}.git"

# 3. Clone or Pull
if os.path.exists(REPO_NAME):
    print(f"🔄 Updating {REPO_NAME}...")
    !cd {REPO_NAME} && git pull {REPO_URL}
else:
    print(f"📥 Cloning {REPO_NAME}...")
    !git clone {REPO_URL}
```

## Security Benefits
- **No Hardcoding**: Your token is never saved in the `.ipynb` file or committed to GitHub.
- **Revocable**: If your token is compromised, you can delete it in GitHub settings without changing your code.
- **Secure Storage**: Only authorized notebooks can access the token via the `userdata` API.
