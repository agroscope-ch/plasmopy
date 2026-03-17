#!/usr/bin/env bash
# Plasmopy scheduler: runs the model immediately on start, then at every
# 00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00 (local time).
#
# Start in background:  nohup ./run_cron.sh &
# Stop:                 kill <PID>   (PID is printed and logged on startup)
#
# Logs are written to: logs/cron.log

set -uo pipefail

PLASMOPY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGDIR="$PLASMOPY_DIR/logs"
LOGFILE="$LOGDIR/cron.log"
INTERVAL=$((3 * 3600))   # 3 hours in seconds

FTP_HOST="dy3bg.ftp.infomaniak.com/sites/arialight.ch"
FTP_USER="dy3bg_jeromekasparian"
FTP_PASS="4TW100fs_Infomaniak"

mkdir -p "$LOGDIR"

# Returns the path to the combined HTML output file by reading config/main.yaml.
get_html_output_path() {
    cd "$PLASMOPY_DIR"
    poetry run python3 - <<'EOF'
import yaml, pathlib
with open("config/main.yaml") as f:
    cfg = yaml.safe_load(f)
out      = cfg.get("output", {})
out_dir  = (out.get("directory") or "data/output").strip()
run_name = (out.get("run_name") or "").strip()
meteo    = (cfg.get("input_data", {}).get("meteo") or "").strip()
basename = run_name or (pathlib.Path(meteo).stem if meteo else "")
if basename:
    print(pathlib.Path(out_dir) / basename / (basename + ".html"))
EOF
}

upload_html() {
    local html_file="$1"
    if [ ! -f "$html_file" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] FTP upload skipped: HTML file not found ($html_file)" >> "$LOGFILE"
        return 1
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Uploading $(basename "$html_file") to ftp://$FTP_HOST/ ..." >> "$LOGFILE"
    if curl --silent --show-error \
            -T "$html_file" \
            "ftp://$FTP_HOST/$(basename "$html_file")" \
            --user "$FTP_USER:$FTP_PASS" >> "$LOGFILE" 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] FTP upload successful" >> "$LOGFILE"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] FTP upload FAILED" >> "$LOGFILE"
    fi
}

run_model() {
    echo "----------------------------------------" >> "$LOGFILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Plasmopy run" >> "$LOGFILE"
    cd "$PLASMOPY_DIR"
    if make run >> "$LOGFILE" 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Run completed successfully" >> "$LOGFILE"
        HTML_FILE=$(get_html_output_path)
        if [ -n "$HTML_FILE" ]; then
            upload_html "$PLASMOPY_DIR/$HTML_FILE"
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] FTP upload skipped: could not resolve HTML output path from config" >> "$LOGFILE"
        fi
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Run FAILED (exit code $?)" >> "$LOGFILE"
    fi
}

seconds_until_next_slot() {
    # Seconds to sleep until the next 3-hour boundary in local time.
    local now_h now_m now_s seconds_into_day remainder
    now_h=$(date +%-H)
    now_m=$(date +%-M)
    now_s=$(date +%-S)
    seconds_into_day=$(( now_h * 3600 + now_m * 60 + now_s ))
    remainder=$(( seconds_into_day % INTERVAL ))
    if [ "$remainder" -eq 0 ]; then
        echo $INTERVAL   # exactly on a boundary → wait a full interval
    else
        echo $(( INTERVAL - remainder ))
    fi
}

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Plasmopy scheduler started (PID $$)" | tee -a "$LOGFILE"

# Run immediately on startup
run_model

# Then loop: sleep until the next 3-hour boundary, then run again
while true; do
    SLEEP_SECS=$(seconds_until_next_slot)
    NEXT=$(date -d "now + ${SLEEP_SECS} seconds" '+%Y-%m-%d %H:%M:%S')
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Next run at $NEXT (sleeping ${SLEEP_SECS}s)" | tee -a "$LOGFILE"
    sleep "$SLEEP_SECS"
    run_model
done
