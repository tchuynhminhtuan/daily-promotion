# 🤖 Mac Automation Guide

Welcome to your automated price tracking center. This directory contains the scripts and configurations that keep your daily scrapers running smoothly on your Mac and synced with GitHub.

## 🕒 The Two Workflows

| Workout Name | Time | Primary Purpose | Result Location |
| :--- | :--- | :--- | :--- |
| **Apple Scrape** | **9:00 AM** | Tracks all Apple products (iPhone, iPad, Mac, etc.) | `content/YYYY-MM-DD/` |
| **Marshall Tracker** | **9:30 AM** | Tracks Marshall speakers via core scrapers | `projects/marshall_daily/content/` |

---

## 📂 File Hierarchy (How it works)

Everything follows a 3-layer structure. If you need to change ONE thing, you usually only need to look at ONE layer.

### Layer 1: The Schedulers (`.plist` files)
These are macOS "LaunchAgents" that tell your computer *when* to wake up and work.
*   `com.brucehuynh.dailyscrape.plist`: Schedules the 9:00 AM run.
*   `com.brucehuynh.marshall_daily.plist`: Schedules the 9:30 AM run.
*   **Location**: Active copies are stored in `~/Library/LaunchAgents/`.

### Layer 2: The User Launchers (`.command` files)
These are the "Play" buttons. You can double-click these in Finder to run a scraper right now.
*   `2_manually_run_now.command`: Opens a terminal and runs the main Apple scrape.
*   `2b_marshall_run_now.command`: Opens a terminal and runs the Marshall tracker.

### Layer 3: The Core Logic (`.sh` scripts)
These scripts do the "heavy lifting": navigating folders, running Python, and pushing to GitHub.
*   `1_core_workflow.sh`: Logic for Apple scrape.
*   `1b_marshall_workflow.sh`: Logic for Marshall tracker.

---

## 🛠️ Common Tasks

### How do I run a scraper manually?
Just double-click **`2_manually_run_now.command`** or **`2b_marshall_run_now.command`**. A terminal window will pop up showing you the progress.

### How do I update the schedule time?
1.  Open the `.plist` file (e.g., `com.brucehuynh.dailyscrape.plist`).
2.  Change the `<integer>` values for `<key>Hour</key>` and `<key>Minute</key>`.
3.  Run the installer script: `bash scripts/automation/3_install_mac_scheduler.sh`.

### Where are the logs?
If a scheduled run fails quietly, check these files in your Terminal:
*   Apple Logs: `tail -f /tmp/daily_scrape.out` (or `.err` for errors)
*   Marshall Logs: `tail -f /tmp/marshall_daily.out` (or `.err` for errors)

---

## ⚠️ Important Notes
*   **Stay Plugged In**: Automation only runs if your Mac is awake or in "Power Nap" mode.
*   **Git Sync**: Both workflows will automatically commit and push to GitHub. If you have "Conflicts," the scripts will try to `stash` your changes and `rebase` to keep things clean.
