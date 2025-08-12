# Twitch LED Matrix Display

This project turns a Raspberry Pi-powered RGB LED matrix into a dynamic, interactive display for your Twitch channel. It features a real-time subscriber counter and triggers custom animations for events like new subscribers, gift subscriptions, and follows. The entire application is containerized with Docker for easy setup and reliable operation.

The application is split into two components:

1.  A **daemon** that runs with elevated privileges to control the hardware and communicate with the Twitch API.
2.  A **control panel** that runs as a simple web server, allowing you to start, stop, and trigger animations on demand.

---
## Features

* **Real-Time Subscriber Counter:** Displays your current subscriber count on the LED matrix.
* **Event-Driven Animations:**
    * **Fireworks:** Celebrates new subscribers, gifts, and follows.
    * **Pulsating Heart:** A fun, on-demand animation.
    * **Smiley Face:** Another on-demand animation.
* **Scrolling Text Alerts:** Displays custom messages for new events, such as "(user) just subscribed!"
* **Web Control Panel:**
    * `/start`: Connects to Twitch and starts displaying events.
    * `/stop`: Disconnects from Twitch.
    * `/fireworks`, `/heart`, `/smiley`: Trigger animations manually.
* **Dockerized:** The entire application runs in two isolated containers, managed by Docker Compose for stability and easy deployment.

---
## Hardware Requirements

This project is built on the excellent [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) library by Henner Zeller.

* **Raspberry Pi:** The rpi-rgb-led-matrix library supports up to the Raspberry Pi 4, which is what is used here. The Raspberry Pi 5 is currently not supported. The OS used is **Raspberry Pi OS Lite (64-bit)** based on Debian Bookworm.
* **RGB LED Matrix:** A [Waveshare RGB-Matrix-P3-64x64](https://www.waveshare.com/wiki/RGB-Matrix-P3-64x64) is used in this project.
* **Power Supply:** A reliable 5V power supply capable of delivering at least 4A.
* **Wiring:** This setup uses direct wiring between the Raspberry Pi 4 and the RGB Matrix. It is preferrable to use an adapter board between the raspberry pi and the matrix. Unfortunately, the Adafruit single adapter bonnet requires soldering a jumper in order to use a 64x64 matrix which is why direct wiring is used here. I have a few Electrodragon adapter's ordered and and will update this repo when they eventually arrive. 

For [wiring details](https://github.com/hzeller/rpi-rgb-led-matrix/blob/master/wiring.md), see the information provided by the rpi-rgb-led-matrix repository.

---
## Software Prerequisites

Before you begin, make sure you have the following installed on your Raspberry Pi:

* **Git:** For cloning the repository.
* **Docker:** The containerization platform.
* **Docker Compose:** The tool for defining and running multi-container Docker applications.

---
## Disclaimer

This project involves connecting directly to the GPIO pins of a Raspberry Pi and requires a separate, powerful electrical supply for the LED matrix. Incorrect wiring or power management can potentially damage your Raspberry Pi, the LED matrix, or both.

The author of this project is not responsible for any damage to your hardware. This software is provided "as is", without warranty of any kind, express or implied. The author makes no claims about the stability or completeness of the code. **<u>Use at your own risk.</u>**

---
## Setup and Installation

### 1. Configure Your Raspberry Pi

Before running the application, you need to enable the necessary hardware interfaces on your Raspberry Pi. This is a one-time setup.

* **Edit `/boot/firmware/config.txt`:**
    * Change `dtparam=audio=on` to `dtparam=audio=off`.
    * Add the line `dtparam=spi=on`.
* **Edit `/boot/firmware/cmdline.txt`:**
    * Remove the text `console=serial0,115200`.
    * Add `isolcpus=3` to the end of the line to dedicate a CPU core to the matrix, improving stability.
* **(Optional) Blacklist the Sound Module:** To be extra cautious, you can prevent the audio kernel module from loading. Create a new file:
    ```bash
    sudo nano /etc/modprobe.d/blacklist-snd_bcm2835.conf
    ```
    Add the following line to the file:
    ```
    blacklist snd_bcm2835
    ```
* **Reboot** your Raspberry Pi for the changes to take effect.

### 2. Set Up Your Twitch Application

You need to register a new application in the Twitch Developer Console to get the necessary credentials.

* Go to the [Twitch Developer Console](https://dev.twitch.tv/console/apps) and create a new application.
* For the **OAuth Redirect URL**, you must add `http://localhost:17563`.
* Note your **Client ID** and **Client Secret**.

### 3. Clone the Repository and Configure

Clone this repository to your Raspberry Pi, create your `.env` file, and install the Python dependencies needed for the authentication script.

```bash
git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
cd your-repository-name

# Create a .env file with your Twitch credentials
cp .env.example .env
nano .env

# Install dependencies into a virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt