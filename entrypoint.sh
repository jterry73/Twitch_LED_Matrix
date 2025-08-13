#!/bin/sh
# entrypoint.sh

# This script runs as the root user inside the container.
# Instead of changing ownership, we change the permissions of the logs
# directory to be world-writable (777).
# This allows the container's root user to create log files, while the
# user on the host machine retains ownership and can manage the directory.
chmod 777 /app/logs

# Execute the main command passed to the container (e.g., "python matrix_daemon.py")
exec "$@"