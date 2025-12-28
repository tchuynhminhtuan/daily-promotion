#!/bin/bash

# --- 2_manually_run_now.command ---
# DOUBLE-CLICK THIS FILE to run the scraper manually in a Terminal window.

# Ensure we are in the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the core workflow
"$SCRIPT_DIR/1_core_workflow.sh"

# Keep Terminal open if there's an error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ERROR: Workflow failed. Check the logs above."
    read -p "Press Enter to close..."
fi
