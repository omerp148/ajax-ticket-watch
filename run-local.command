#!/bin/bash
set -euo pipefail
umask 077
TASK_SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_APP_DIR="$HOME/Library/Application Support/ajax-ticket-watch"
mkdir -p "$TASK_APP_DIR/code"
chmod 700 "$TASK_APP_DIR"
cd "$TASK_SOURCE_DIR"
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
  echo "Python 3.10 or newer is required."
  echo "Install Python from python.org, then open this file again."
  open "https://www.python.org/downloads/macos/"
  read -r -p "Press Enter to close this window."
  exit 1
fi
if [ ! -d "/Applications/Google Chrome.app" ] && [ ! -d "$HOME/Applications/Google Chrome.app" ]; then
  echo "Google Chrome must be installed before running this watcher."
  read -r -p "Press Enter to close."
  exit 1
fi
cp monitor.py local_watch.py "$TASK_APP_DIR/code/"
if [ ! -x "$TASK_APP_DIR/.venv/bin/python" ]; then
  python3 -m venv "$TASK_APP_DIR/.venv"
fi
"$TASK_APP_DIR/.venv/bin/python" -m pip install --disable-pip-version-check playwright keyring
echo "Dependencies installed. Chrome login stays in a dedicated local profile."
echo "Email app password is saved only in macOS Keychain."
echo "The watcher keeps your Mac awake while this Terminal is running."
echo "Press Ctrl+C at any time to stop monitoring."
cd "$TASK_APP_DIR"
caffeinate -i "$TASK_APP_DIR/.venv/bin/python" "$TASK_APP_DIR/code/local_watch.py"
