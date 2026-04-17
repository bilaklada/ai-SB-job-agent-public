#!/bin/bash
# =============================================================================
# VNC Entrypoint Script for Agent Container
# =============================================================================
#
# This script:
# 1. Starts VNC server with virtual display
# 2. Launches window manager (Fluxbox)
# 3. Runs the applicant agent
# 4. Allows developers to connect via VNC to watch browser automation
#
# =============================================================================

set -e

echo "=== VNC Agent Container Startup ==="
echo "Container user: $(whoami)"
echo "Display: $DISPLAY"
echo "VNC Resolution: ${VNC_RESOLUTION:-1920x1080}"

# -----------------------------------------------------------------------------
# Setup VNC Server
# -----------------------------------------------------------------------------

# Create VNC config directories
mkdir -p ~/.vnc
mkdir -p ~/.config/tigervnc

# Set VNC password from environment or a clearly unsafe placeholder
VNC_PASSWORD="${VNC_PASSWORD:-change-me-before-use}"
echo "$VNC_PASSWORD" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

echo "VNC password configured from VNC_PASSWORD"

# Create xstartup script for VNC
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec fluxbox &
EOF

chmod +x ~/.vnc/xstartup

# Create TigerVNC config file
cat > ~/.config/tigervnc/config << 'EOF'
SecurityTypes=VncAuth
EOF

# Start VNC server
echo "Starting VNC server on display $DISPLAY..."
vncserver "$DISPLAY" \
    -geometry "${VNC_RESOLUTION:-1920x1080}" \
    -depth "${VNC_DEPTH:-24}" \
    -localhost no \
    -SecurityTypes VncAuth \
    -rfbauth ~/.vnc/passwd \
    2>&1 | tee /tmp/vncserver.log

VNC_EXIT_CODE=$?
echo "vncserver exit code: $VNC_EXIT_CODE"

if [ $VNC_EXIT_CODE -ne 0 ]; then
    echo "❌ VNC server failed to start. Log:"
    cat /tmp/vncserver.log
    exit 1
fi

# Wait for VNC to be ready
sleep 3

# Verify VNC is running (check for both Xvnc and Xtigervnc)
if pgrep -x "Xvnc\|Xtigervnc" > /dev/null; then
    echo "✅ VNC server started successfully"
    echo "📺 Connect with VNC viewer to: localhost:5900"
elif [ -f ~/.vnc/*:0.pid ]; then
    echo "✅ VNC server PID file found"
    echo "📺 Connect with VNC viewer to: localhost:5900"
else
    echo "⚠️  VNC server status unclear (vncserver returned success)"
    echo "📺 Try connecting to: localhost:5900"
    echo ""
    echo "Checking VNC logs..."
    cat ~/.vnc/*:0.log 2>/dev/null || echo "No VNC logs found yet"
fi

# -----------------------------------------------------------------------------
# Start Window Manager
# -----------------------------------------------------------------------------

# Fluxbox is already started by xstartup
sleep 1

# -----------------------------------------------------------------------------
# Run Application
# -----------------------------------------------------------------------------

echo ""
echo "=== Starting Applicant Agent ==="
echo "Job ID: ${JOB_ID:-auto-select}"
echo "Headless mode: ${HEADLESS:-false}"
echo ""

# Execute the command passed to the container
# This allows flexibility in what gets run (agent, test script, etc.)
exec "$@"
