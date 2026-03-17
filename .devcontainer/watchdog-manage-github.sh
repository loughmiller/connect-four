#!/bin/bash
# Watchdog that ensures start-manage-github.sh stays running.
# Checks every 30 seconds; restarts the process if it's not alive.

PIDFILE="/tmp/manage-github.pid"
LOGFILE="/tmp/manage-github-watchdog.log"
SCRIPT="/workspace/.devcontainer/start-manage-github.sh"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOGFILE"
}

start_process() {
    nohup bash "$SCRIPT" > /tmp/manage-github-start.log 2>&1 &
    echo $! > "$PIDFILE"
    log "Started manage-github (PID $!)"
}

is_running() {
    [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

log "Watchdog started"

# Initial start
if ! is_running; then
    start_process
fi

while true; do
    sleep 30
    if ! is_running; then
        log "manage-github is not running, restarting..."
        start_process
    fi
done
