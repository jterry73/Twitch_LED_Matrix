import time
import math
import random
import threading
import asyncio
import os
import json
from dotenv import load_dotenv
from queue import Queue
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.object.eventsub import ChannelFollowEvent
from twitchAPI.type import AuthScope, TwitchAPIException
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

load_dotenv()  # Load environment variables from .env file 
# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

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

# Firework Simulation Configuration
GRAVITY = 0.1
MAX_ROCKETS = 10
ROCKET_LIFESPAN = 40
PARTICLE_LIFESPAN = 50
TRAIL_LIFESPAN = 25
ROCKET_SIZE = 2
PARTICLE_SIZE = 2
TRAIL_SIZE = 1
FIREWORK_DURATION = 5 # Duration of the firework celebration in seconds

# Font Colors
SUBS_COLOR = graphics.Color(255, 255, 0)
NUM_COLOR = graphics.Color(255, 255, 255)
SCROLL_COLOR = graphics.Color(0, 255, 0)
SCROLL_NUM_COLOR = graphics.Color(255, 105, 180)

# Global variables for cross-thread communication
subscriber_count = 0
subscriber_lock = threading.Lock()
follower_count = 0
follower_lock = threading.Lock()
animation_queue = Queue()

# -------------------------------------------------------------------------
# Classes
# -------------------------------------------------------------------------

class FireworkShow:
    """Manages the firework simulation."""
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
        while time.time() - start_time < duration_seconds:
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

class StaticTextDisplay:
    def __init__(self, matrix):
        self.matrix = matrix
        self.font_subs = graphics.Font(); self.font_subs.LoadFont(FONT_TITLE)
        self.font_num = graphics.Font(); self.font_num.LoadFont(FONT_SUBS_NUMBER)
        self.canvas = self.matrix.CreateFrameCanvas()
    def update(self, count):
        self.canvas.Clear()
        text_subs = "SUBS"; x_subs = (self.matrix.width - sum(self.font_subs.CharacterWidth(ord(c)) for c in text_subs)) // 2
        y_subs = int(self.matrix.height * 0.30)
        graphics.DrawText(self.canvas, self.font_subs, x_subs, y_subs, SUBS_COLOR, text_subs)
        text_num = str(count); x_num = (self.matrix.width - sum(self.font_num.CharacterWidth(ord(c)) for c in text_num)) // 2
        y_num = int(self.matrix.height * 0.85)
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
        while pos + total_width > 0:
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
    """Callback for when a subscription event is received."""
    global subscriber_count
    user_name = data.event.user_name
    print(f"New subscriber: {user_name}")
    with subscriber_lock:
        subscriber_count += 1
    
    # Add the animation sequence to the queue
    scroll_text = [ (f"{user_name} just subscribed!", SCROLL_COLOR) ]
    animation_queue.put(('fireworks', FIREWORK_DURATION))
    animation_queue.put(('scroll', scroll_text))

async def on_sub_gift(data: dict):
    """Callback for when a subscription gift event is received."""
    global subscriber_count
    user_name = data.event.user_name
    gift_count = data.event.total
    print(f"{user_name} gifted {gift_count} subs!")
    with subscriber_lock:
        subscriber_count += gift_count
    
    # Add the animation sequence to the queue
    scroll_text = [
        (f"{user_name} just gifted ", SCROLL_COLOR),
        (str(gift_count), SCROLL_NUM_COLOR),
        (" subs!", SCROLL_COLOR)
    ]
    animation_queue.put(('fireworks', FIREWORK_DURATION))
    animation_queue.put(('scroll', scroll_text))

async def on_follow(data: dict):
    """Callback for when a follow event is received."""
    global follower_count
    user_name = data.event.user_name
    print(f"New Follower: {user_name}")
    with follower_lock:
        follower_count += 1
    
    # Add the animation sequence to the queue
    scroll_text = [ (f"{user_name} just Followed!", SCROLL_COLOR) ]
    animation_queue.put(('fireworks', FIREWORK_DURATION))
    animation_queue.put(('scroll', scroll_text))

def token_update_callback(token: str, refresh_token: str):
    """Callback for when the user token is refreshed."""
    print("User token refreshed, saving to file...")
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'token': token, 'refresh_token': refresh_token}, f)

async def twitch_events_task():
    """The asynchronous task that connects to Twitch and listens for events."""
    twitch = await Twitch(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    twitch.user_auth_refresh_callback = token_update_callback

    target_scope = [AuthScope.CHANNEL_READ_SUBSCRIPTIONS, AuthScope.MODERATOR_READ_FOLLOWERS]
    
    if os.path.exists(TOKEN_FILE):
        print("Found token file, attempting to refresh...")
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.load(f)
        try:
            token, refresh_token = await refresh_access_token(tokens['refresh_token'], TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
            await twitch.set_user_authentication(token, target_scope, refresh_token)
            print("Successfully refreshed and set user token.")
        except TwitchAPIException:
            print("Failed to refresh token, starting manual auth flow.")
            os.remove(TOKEN_FILE)
            await twitch_events_task() # Restart this task
            return
    else:
        auth = UserAuthenticator(twitch, target_scope, force_verify=False)
        print("Please open the following URL in a browser to authorize the application:")
        url = auth.return_auth_url()
        print(url)
        code = input("Please paste the code from the redirected URL here: ")
        token, refresh_token = await auth.authenticate(user_token=code)
        await twitch.set_user_authentication(token, target_scope, refresh_token)
        token_update_callback(token, refresh_token)
    
    user_info_gen = twitch.get_users(logins=[TWITCH_USERNAME])
    user_info = [u async for u in user_info_gen]
    if not user_info:
        print(f"Could not find user: {TWITCH_USERNAME}")
        await twitch.close()
        return
    broadcaster_id = user_info[0].id

    eventsub = EventSubWebsocket(twitch)
    eventsub.start()
    
    await eventsub.listen_channel_follow_v2(broadcaster_id, broadcaster_id, on_follow)
    await eventsub.listen_channel_subscribe(broadcaster_id, on_subscribe)
    await eventsub.listen_channel_subscription_gift(broadcaster_id, on_sub_gift)
    print("Successfully subscribed to channel.subscribe and channel.subscription.gift events.")

    # Keep the connection alive
    try:
        await asyncio.Event().wait()
    finally:
        print("Stopping EventSub and closing Twitch connection.")
        await eventsub.stop()
        await twitch.close()

def main():
    """Main synchronous function to handle animations and display."""
    # Start the async Twitch task in a background thread
    twitch_thread = threading.Thread(target=lambda: asyncio.run(twitch_events_task()), daemon=True)
    twitch_thread.start()

    static_display = StaticTextDisplay(matrix)
    
    try:
        print("Starting main loop. Press CTRL-C to stop.")
        while True:
            try:
                # Check for an animation task without blocking
                task_type, data = animation_queue.get_nowait()
                
                # If there's a task, run the animation
                if task_type == 'fireworks':
                    fireworks = FireworkShow(matrix)
                    fireworks.run(duration_seconds=data)
                elif task_type == 'scroll':
                    scroll_font = graphics.Font(); scroll_font.LoadFont(FONT_SUBS_NUMBER)
                    scroller = ScrollingText(matrix, data, scroll_font)
                    scroller.run()

            except Exception: # queue.Empty is the expected exception
                # If no animation is running, update the static display
                with subscriber_lock:
                    static_display.update(subscriber_count)
                time.sleep(0.1) # Small delay to prevent high CPU usage

    except KeyboardInterrupt:
        print("\nExiting main application.")
    finally:
        matrix.Clear()

if __name__ == '__main__':
    main()
