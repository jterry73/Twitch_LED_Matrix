# Use a Python image based on Debian (similar to Raspberry Pi OS)
FROM python:3.11-slim-bookworm

# Set the main working directory
WORKDIR /app

# Install system dependencies required by the rgbmatrix library and git
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    python3-dev \
    cython3 \
    python3-pil \
    && rm -rf /var/lib/apt/lists/*

# --- Clone and build the rpi-rgb-led-matrix library FIRST ---
RUN git clone https://github.com/hzeller/rpi-rgb-led-matrix.git /rpi-rgb-led-matrix
WORKDIR /rpi-rgb-led-matrix
RUN make build-python PYTHON=$(which python)
RUN make install-python PYTHON=$(which python)

# --- Clone your public application repository NEXT ---
WORKDIR /app
RUN git clone https://github.com/jterry73/Twitch-LED-Matrix.git .

# --- Install Python dependencies from your cloned repository ---
RUN pip install --no-cache-dir -r requirements.txt

# Create the directory for logs
RUN mkdir /app/logs

# --- Set up the entrypoint script ---
# Copy the script into the container and make it executable
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]

# The default command to run when the container starts.
# This is passed to the entrypoint script.
# Note: sudo is not needed as the container runs as root by default.
CMD [ "python", "matrix_daemon.py" ]
