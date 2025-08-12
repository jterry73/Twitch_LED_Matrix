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
# This is a dependency that changes infrequently, so we install it early.
RUN git clone https://github.com/hzeller/rpi-rgb-led-matrix.git /rpi-rgb-led-matrix
WORKDIR /rpi-rgb-led-matrix
# Reverted to the default make install instructions
RUN make build-python PYTHON=$(which python)
RUN make install-python PYTHON=$(which python)

# --- Clone your public application repository NEXT ---
# Return to the main app directory before cloning
WORKDIR /app
# This now uses a standard git clone command for a public repository.
# Replace the URL with your actual repository URL.
RUN git clone https://github.com/jterry73/TwitchTV_LED_Matrix.git .

# --- Install Python dependencies from your cloned repository ---
# This layer is cached and only re-run if requirements.txt changes.
RUN pip install --no-cache-dir -r requirements.txt

# The CMD will run the script from the cloned repository.
# Note: sudo is not needed inside the container
# as the container itself is run with --privileged.
CMD [ "python", "matrix_daemon.py" ]