#!/bin/sh
# AutoWOL 启动脚本（支持 OpenWrt/ImmortalWrt）

SCRIPT_DIR="/root/code/AutoWol"
PID_FILE="/var/run/autowol.pid"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps | grep -q "^[[:space:]]*$PID"; then
            echo "AutoWOL already running (PID: $PID)"
            return 1
        fi
        rm -f "$PID_FILE"
    fi
    
    echo "Starting AutoWOL..."
    cd "$SCRIPT_DIR"
    python3 app.py > /var/log/autowol.log 2>&1 &
    echo $! > "$PID_FILE"
    echo "AutoWOL started (PID: $(cat $PID_FILE))"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "AutoWOL is not running"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    echo "Stopping AutoWOL (PID: $PID)..."
    kill $PID 2>/dev/null
    rm -f "$PID_FILE"
    echo "AutoWOL stopped"
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps | grep -q "^[[:space:]]*$PID"; then
            echo "AutoWOL is running (PID: $PID)"
            return 0
        else
            echo "AutoWOL is not running (stale PID file)"
            return 1
        fi
    else
        echo "AutoWOL is not running"
        return 1
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
