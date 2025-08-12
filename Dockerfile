# Use a Python image based on Debian (similar to Raspberry Pi OS)
FROM python:3.11-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required by the rgbmatrix library and git
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    python3-dev \
    cython3 \
    python3-pil \
    && rm -rf /var/lib/apt/lists/*

# --- Clone and install the rpi-rgb-led-matrix library FIRST ---
RUN git clone https://github.com/hzeller/rpi-rgb-led-matrix.git /app/rpi-rgb-led-matrix
WORKDIR /app/rpi-rgb-led-matrix/bindings/python
# This command builds and installs the library into the container's python environment
RUN pip install .

# Return to the main app directory
WORKDIR /app

# Clone your GitHub repository into the container
# Replace the URL with your actual repository URL
RUN git clone https://github.com/jterry73/TwitchTV_LED_Matrix.git .

# Install Python dependencies from your requirements.txt file
# IMPORTANT: Make sure 'rpi-rgb-led-matrix' is NOT listed in this file
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Command to run when the container starts
# This will run your daemon script with sudo privileges
CMD [ "sudo", "python", "matrix_daemon.py" ]
