#!/bin/bash
# Wrapper for macOS Automation
# This .command extension forces macOS to open Terminal and run the script.

cd "$(dirname "$0")"
./run_hybrid_workflow.sh
