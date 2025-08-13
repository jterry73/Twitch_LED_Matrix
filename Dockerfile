# Use a Python image based on Debian (similar to Raspberry Pi OS)
FROM python:3.11-slim-bookworm

# Set the main working directory
WORKDIR /app

# Install system dependencies required by the rgbmatrix library and git
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    python3-dev \
    python3-pil \
    && rm -rf /var/lib/apt/lists/*

# --- Clone and build the rpi-rgb-led-matrix library FIRST ---
RUN git clone https://github.com/hzeller/rpi-rgb-led-matrix.git /rpi-rgb-led-matrix
WORKDIR /rpi-rgb-led-matrix
RUN make build-python PYTHON=$(which python)
RUN make install-python PYTHON=$(which python)

# --- Copy your application into the container ---
WORKDIR /app
# This command copies all files from your local project directory
# into the container's /app directory.
COPY . .

# --- Install Python dependencies from your requirements.txt file ---
RUN pip install --no-cache-dir -r requirements.txt

# Create the directory for logs
RUN mkdir /app/logs

# --- Set up the entrypoint script ---
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# The default command to run when the container starts.
CMD [ "python", "matrix_daemon.py" ]
