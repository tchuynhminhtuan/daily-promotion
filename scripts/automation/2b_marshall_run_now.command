#!/bin/bash

# --- 2b_marshall_run_now.command ---
# DOUBLE-CLICK THIS FILE to run the Marshall tracker manually in a Terminal window.

# Ensure we are in the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the Marshall workflow
"$SCRIPT_DIR/1b_marshall_workflow.sh"

# Keep Terminal open if there's an error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ERROR: Marshall Workflow failed. Check the logs above."
    read -p "Press Enter to close..."
fi
