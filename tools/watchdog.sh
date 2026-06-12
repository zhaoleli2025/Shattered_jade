#!/usr/bin/env bash
# Keeps the dev server alive on port 7788. Called by cron every 5 minutes
# and at @reboot; safe to run by hand. The pgrep bracket-trick stops the
# pattern from matching this script's own command line.
cd /data/zhaoleli/game01_demo || exit 1
pgrep -f "tools/serve[.]py 7788" >/dev/null && exit 0
setsid python3 tools/serve.py 7788 >> /tmp/serve_sj.log 2>&1 &
echo "$(date '+%F %T') watchdog: server restarted" >> /tmp/serve_sj.log
