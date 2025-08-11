import time
import math
import random
import threading
import asyncio
import os
import sys
import json
import socket
from dotenv import load_dotenv
from queue import Queue
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.type import AuthScope, TwitchAPIException
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

load_dotenv()

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------
SOCKET_FILE = "/tmp/twitch_matrix.sock"

# LED Matrix Configuration
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'regular'
options.gpio_slowdown = 2

# Font file configuration
FONT_TITLE = "fonts/MinercraftoryRegular-18.bdf"
FONT_SUBS_NUMBER = "fonts/MinercraftoryRegular-30.bdf"

# Twitch Configuration stored in .env file
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME = os.environ.get("TWITCH_USERNAME")
TOKEN_FILE = f"/etc/twitch_matrix/{TWITCH_USERNAME}_tokens.json" # Using a standard location for app data

matrix = RGBMatrix(options=options)

# Animation Configuration
FIREWORK_DURATION = 5
HEART_DURATION = 6
SMILEY_DURATION = 6
HEART_COLOR = graphics.Color(255, 20, 147) # Deep Pink

# Firework Simulation Configuration
GRAVITY = 0.1
MAX_ROCKETS = 10
ROCKET_LIFESPAN = 40
PARTICLE_LIFESPAN = 50
TRAIL_LIFESPAN = 25
ROCKET_SIZE = 2
PARTICLE_SIZE = 2
TRAIL_SIZE = 1

# Font Colors
SUBS_COLOR = graphics.Color(255, 255, 0)
NUM_COLOR = graphics.Color(255, 255, 255)
SCROLL_COLOR = graphics.Color(0, 255, 0)
SCROLL_NUM_COLOR = graphics.Color(255, 105, 180)

# --- Global variables for state management ---
subscriber_count = 0
subscriber_lock = threading.Lock()
animation_queue = Queue()
# --- Events for controlling the main logic threads ---
twitch_logic_active = threading.Event()
twitch_shutdown_event = threading.Event()
daemon_shutdown_event = threading.Event()
twitch_thread = None

# -------------------------------------------------------------------------
# Animation and Display Classes
# -------------------------------------------------------------------------
class FireworkShow:
    def __init__(self, matrix):
        self.matrix = matrix
        self.rockets = []
        self.particles = []
        self.trails = []
        self.canvas = self.matrix.CreateFrameCanvas()

    class Particle:
        def __init__(self, x, y, vx, vy, color, lifespan):
            self.x, self.y, self.vx, self.vy, self.color, self.lifespan = x, y, vx, vy, color, lifespan
        def update(self):
            self.x += self.vx; self.y += self.vy; self.vy += GRAVITY; self.lifespan -= 1
        def is_alive(self):
            return self.lifespan > 0

    class Rocket(Particle):
        def __init__(self, x, y, color):
            super().__init__(x, y, 0, -random.uniform(1.5, 2.5), color, ROCKET_LIFESPAN)
        def explode(self, parent):
            particles = []
            for _ in range(random.randint(50, 80)):
                angle, speed = random.uniform(0, 2 * math.pi), random.uniform(0.5, 4.5)
                vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
                color = graphics.Color(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
                particles.append(parent.Particle(self.x, self.y, vx, vy, color, PARTICLE_LIFESPAN))
            return particles

    def run(self, duration_seconds=10):
        start_time = time.time()
        print("Starting firework celebration!")
        while time.time() - start_time < duration_seconds and not daemon_shutdown_event.is_set():
            self.canvas.Clear()
            if len(self.rockets) < MAX_ROCKETS and random.random() < 0.2:
                self.rockets.append(self.Rocket(random.randint(0, self.matrix.width - 1), self.matrix.height - 1, graphics.Color(255, 255, 255)))
            for rocket in self.rockets[:]:
                rocket.update()
                if not rocket.is_alive() or rocket.vy >= 0:
                    self.particles.extend(rocket.explode(self))
                    self.rockets.remove(rocket)
                else:
                    self.trails.append(self.Particle(rocket.x, rocket.y, 0, 0, rocket.color, TRAIL_LIFESPAN))
                    for i in range(ROCKET_SIZE): graphics.DrawLine(self.canvas, int(rocket.x), int(rocket.y) + i, int(rocket.x) + ROCKET_SIZE - 1, int(rocket.y) + i, rocket.color)
            for particle in self.particles[:]:
                particle.update()
                if not particle.is_alive(): self.particles.remove(particle)
                else:
                    fade = particle.lifespan / PARTICLE_LIFESPAN
                    color = graphics.Color(int(particle.color.red*fade), int(particle.color.green*fade), int(particle.color.blue*fade))
                    for i in range(PARTICLE_SIZE): graphics.DrawLine(self.canvas, int(particle.x), int(particle.y) + i, int(particle.x) + PARTICLE_SIZE - 1, int(particle.y) + i, color)
            for trail in self.trails[:]:
                trail.lifespan -= 1
                if not trail.is_alive(): self.trails.remove(trail)
                else:
                    fade = trail.lifespan / TRAIL_LIFESPAN
                    color = graphics.Color(int(trail.color.red*fade*0.5), int(trail.color.green*fade*0.5), int(trail.color.blue*fade*0.5))
                    for i in range(TRAIL_SIZE): graphics.DrawLine(self.canvas, int(trail.x), int(trail.y) + i, int(trail.x) + TRAIL_SIZE - 1, int(trail.y) + i, color)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            time.sleep(0.04)
        print("Firework celebration finished.")

class PulsatingHeart:
    """Manages the pulsating heart animation."""
    def __init__(self, matrix):
        self.matrix = matrix
        self.canvas = self.matrix.CreateFrameCanvas()

    def run(self, duration_seconds=10):
        start_time = time.time()
        print("Starting heart animation!")
        
        while time.time() - start_time < duration_seconds and not daemon_shutdown_event.is_set():
            self.canvas.Clear()
            
            pulse = (math.sin(time.time() * 5) + 1) / 2
            
            center_x = self.matrix.width / 2
            center_y = self.matrix.height / 2
            min_scale = 1.2
            max_scale = 1.6
            
            scale = min_scale + (max_scale - min_scale) * pulse
            
            for s in range(100, 0, -5):
                inner_scale = scale * (s / 100.0)
                step = 5 if s < 80 else 1 
                for i in range(0, 360, step):
                    t = math.radians(i)
                    x = inner_scale * (16 * math.pow(math.sin(t), 3))
                    y = -inner_scale * (13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
                    self.canvas.SetPixel(int(center_x + x), int(center_y + y - 5), HEART_COLOR.red, HEART_COLOR.green, HEART_COLOR.blue)

            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            time.sleep(0.04)
        print("Heart animation finished.")

class SmileyFace:
    """Manages the smiley face animation."""
    def __init__(self, matrix):
        self.matrix = matrix
        self.canvas = self.matrix.CreateFrameCanvas()

    def run(self, duration_seconds=10):
        start_time = time.time()
        print("Starting smiley face animation!")
        yellow = graphics.Color(255, 255, 0)
        black = graphics.Color(0, 0, 0)

        center_x = self.matrix.width / 2
        center_y = self.matrix.height / 2
        radius = 24

        while time.time() - start_time < duration_seconds and not daemon_shutdown_event.is_set():
            self.canvas.Clear()
            
            # Draw filled yellow circle for the face
            for r in range(radius, 0, -1):
                graphics.DrawCircle(self.canvas, int(center_x), int(center_y), r, yellow)

            # Eyes (ovals)
            eye_offset_x = 10
            eye_offset_y = 8
            eye_radius_h = 4
            eye_radius_v = 6
            for r_v in range(eye_radius_v, 0, -1):
                for r_h in range(eye_radius_h, 0, -1):
                    graphics.DrawCircle(self.canvas, int(center_x - eye_offset_x), int(center_y - eye_offset_y), r_h, black)
                    graphics.DrawCircle(self.canvas, int(center_x + eye_offset_x), int(center_y - eye_offset_y), r_h, black)


            # Smile (arc)
            smile_radius = 15
            smile_center_y = center_y + 5
            for i in range(-12, 13):
                # Simple circle equation to create an arc
                y_offset = math.sqrt(max(0, smile_radius**2 - i**2))
                graphics.DrawLine(self.canvas, int(center_x + i), int(smile_center_y + y_offset - 5), int(center_x + i), int(smile_center_y + y_offset - 3), black)


            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            time.sleep(0.1)
        print("Smiley face animation finished.")


class StaticTextDisplay:
    def __init__(self, matrix):
        self.matrix = matrix
        self.font_subs = graphics.Font(); self.font_subs.LoadFont(FONT_TITLE)
        self.font_num = graphics.Font(); self.font_num.LoadFont(FONT_SUBS_NUMBER)
        self.canvas = self.matrix.CreateFrameCanvas()
    def update(self, count):
        self.canvas.Clear()
        text_subs = "SUBS"; x_subs = (self.matrix.width - sum(self.font_subs.CharacterWidth(ord(c)) for c in text_subs)) // 2
        y_subs = int(self.matrix.height * 0.25)
        graphics.DrawText(self.canvas, self.font_subs, x_subs, y_subs, SUBS_COLOR, text_subs)
        text_num = str(count); x_num = (self.matrix.width - sum(self.font_num.CharacterWidth(ord(c)) for c in text_num)) // 2
        y_num = int(self.matrix.height * 0.75)
        graphics.DrawText(self.canvas, self.font_num, x_num, y_num, NUM_COLOR, text_num)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

class ScrollingText:
    def __init__(self, matrix, text_parts, font):
        self.matrix, self.text_parts, self.font = matrix, text_parts, font
        self.canvas = self.matrix.CreateFrameCanvas()
    def run(self):
        total_width = sum(sum(self.font.CharacterWidth(ord(c)) for c in text) for text, color in self.text_parts)
        pos = self.canvas.width
        print("Scrolling text...")
        while pos + total_width > 0 and not daemon_shutdown_event.is_set():
            self.canvas.Clear()
            current_x, y = pos, int((self.matrix.height * 0.5) + (self.font.height / 3))
            for text, color in self.text_parts: current_x += graphics.DrawText(self.canvas, self.font, current_x, y, color, text)
            pos -= 1; time.sleep(0.03)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
        print("Scrolling text finished.")

# -------------------------------------------------------------------------
# Twitch and Main Application Logic
# -------------------------------------------------------------------------

async def on_subscribe(data: dict):
    global subscriber_count
    user_name = data.event.user_name
    print(f"New subscriber: {user_name}")
    with subscriber_lock:
        subscriber_count += 1
    
    scroll_text = [ (f"{user_name} just subscribed!", SCROLL_COLOR) ]
    animation_queue.put(('fireworks', FIREWORK_DURATION))
    animation_queue.put(('scroll', scroll_text))

async def on_sub_gift(data: dict):
    global subscriber_count
    user_name = data.event.user_name
    gift_count = data.event.total
    print(f"{user_name} gifted {gift_count} subs!")
    with subscriber_lock:
        subscriber_count += gift_count
    
    scroll_text = [
        (f"{user_name} just gifted ", SCROLL_COLOR),
        (str(gift_count), SCROLL_NUM_COLOR),
        (" subs!", SCROLL_COLOR)
    ]
    animation_queue.put(('fireworks', FIREWORK_DURATION))
    animation_queue.put(('scroll', scroll_text))

async def on_follow(data: dict):
    user_name = data.event.user_name
    print(f"New follower: {user_name}")
    scroll_text = [ (f"{user_name} just followed!", SCROLL_COLOR) ]
    animation_queue.put(('fireworks', FIREWORK_DURATION))
    animation_queue.put(('scroll', scroll_text))
    
def token_update_callback(token: str, refresh_token: str):
    print("User token refreshed, saving to file...")
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'token': token, 'refresh_token': refresh_token}, f)

async def twitch_events_task():
    twitch = await Twitch(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    twitch.user_auth_refresh_callback = token_update_callback

    target_scope = [AuthScope.CHANNEL_READ_SUBSCRIPTIONS, AuthScope.MODERATOR_READ_FOLLOWERS]
    
    if not os.path.exists(TOKEN_FILE):
        print("Token file not found. Please authenticate via the control panel first.")
        return

    print("Found token file, attempting to refresh...")
    with open(TOKEN_FILE, 'r') as f:
        tokens = json.load(f)
    try:
        token, refresh_token = await refresh_access_token(tokens['refresh_token'], TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
        await twitch.set_user_authentication(token, target_scope, refresh_token)
        print("Successfully refreshed and set user token.")
    except TwitchAPIException:
        print("Failed to refresh token. Please re-authenticate via the control panel.")
        return
    
    user_info_gen = twitch.get_users(logins=[TWITCH_USERNAME])
    user_info = [u async for u in user_info_gen]
    if not user_info:
        print(f"Could not find user: {TWITCH_USERNAME}")
        await twitch.close()
        return
    broadcaster_id = user_info[0].id

    eventsub = EventSubWebsocket(twitch)
    eventsub.start()
    
    await eventsub.listen_channel_subscribe(broadcaster_id, on_subscribe)
    await eventsub.listen_channel_subscription_gift(broadcaster_id, on_sub_gift)
    await eventsub.listen_channel_follow_v2(broadcaster_id, broadcaster_id, on_follow)
    print("Successfully subscribed to all events.")

    try:
        while not twitch_shutdown_event.is_set():
            await asyncio.sleep(0.1)
    finally:
        print("Stopping EventSub and closing Twitch connection.")
        await eventsub.stop()
        await twitch.close()

def display_and_animation_loop():
    """Main synchronous loop to handle animations and display."""
    static_display = StaticTextDisplay(matrix)
    
    try:
        print("Starting display and animation loop.")
        while not daemon_shutdown_event.is_set():
            try:
                task_type, data = animation_queue.get(timeout=0.1)
                
                if task_type == 'fireworks':
                    fireworks = FireworkShow(matrix)
                    fireworks.run(duration_seconds=data)
                elif task_type == 'scroll':
                    scroll_font = graphics.Font(); scroll_font.LoadFont(FONT_SUBS_NUMBER)
                    scroller = ScrollingText(matrix, data, scroll_font)
                    scroller.run()
                elif task_type == 'heart':
                    heart = PulsatingHeart(matrix)
                    heart.run(duration_seconds=data)
                elif task_type == 'smiley':
                    smiley = SmileyFace(matrix)
                    smiley.run(duration_seconds=data)

            except Exception: # queue.Empty
                if twitch_logic_active.is_set():
                    with subscriber_lock:
                        static_display.update(subscriber_count)
                else:
                    matrix.Clear()
                    time.sleep(0.1)

    except KeyboardInterrupt:
        daemon_shutdown_event.set()
    finally:
        print("\nExiting display and animation loop.")
        matrix.Clear()

# -------------------------------------------------------------------------
# Socket Server for Commands
# -------------------------------------------------------------------------

def handle_command(command):
    global twitch_thread
    cmd = command.get('command')
    
    if cmd == 'start':
        if twitch_logic_active.is_set():
            print("Received start command, but logic is already running.")
            return
        print("Received start command.")
        twitch_logic_active.set()
        twitch_shutdown_event.clear()
        twitch_thread = threading.Thread(target=lambda: asyncio.run(twitch_events_task()), daemon=True)
        twitch_thread.start()

    elif cmd == 'stop':
        if not twitch_logic_active.is_set():
            print("Received stop command, but logic is not running.")
            return
        print("Received stop command.")
        twitch_shutdown_event.set()
        twitch_logic_active.clear()

    elif cmd == 'fireworks':
        print("Received fireworks command, adding to queue.")
        animation_queue.put(('fireworks', FIREWORK_DURATION))
        
    elif cmd == 'heart':
        print("Received heart command, adding to queue.")
        animation_queue.put(('heart', HEART_DURATION))
        
    elif cmd == 'smiley':
        print("Received smiley command, adding to queue.")
        animation_queue.put(('smiley', SMILEY_DURATION))

def socket_server_thread():
    try:
        os.unlink(SOCKET_FILE)
    except OSError:
        if os.path.exists(SOCKET_FILE):
            raise

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(SOCKET_FILE)
    os.chmod(SOCKET_FILE, 0o777)
    sock.listen(1)
    print(f"Socket server listening on {SOCKET_FILE}")

    while not daemon_shutdown_event.is_set():
        connection, client_address = sock.accept()
        try:
            data = connection.recv(1024)
            if data:
                command = json.loads(data.decode('utf-8'))
                handle_command(command)
        except Exception as e:
            print(f"Error handling command: {e}")
        finally:
            connection.close()

if __name__ == '__main__':
    # This daemon must be run with sudo
    socket_thread = threading.Thread(target=socket_server_thread, daemon=True)
    socket_thread.start()
    
    display_thread = threading.Thread(target=display_and_animation_loop, daemon=True)
    display_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down daemon.")
        daemon_shutdown_event.set()
        twitch_shutdown_event.set()
        matrix.Clear()
