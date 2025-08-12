#!/bin/sh
# entrypoint.sh

# This script runs as the root user inside the container.
# It changes the ownership of the logs directory to root.
# Because this directory is a volume mounted from the host,
# this command effectively gives the container's root user
# permission to write to the host's ./logs directory.
chown root:root /app/logs

# Execute the main command passed to the container (e.g., "python matrix_daemon.py")
exec "$@"