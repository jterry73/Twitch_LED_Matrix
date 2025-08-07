import time
import math
import random
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

# LED Matrix Configuration
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'regular'  # Or 'adafruit-hat', 'adafruit-hat-pwm', etc.
options.gpio_slowdown = 2 # Needed for faster Raspberry Pi models

# Font file configuration
FONT_TITLE = "fonts/ErasBD-18.bdf"
FONT_SUBS_NUMBER = "fonts/ErasBD-30.bdf"

matrix = RGBMatrix(options=options)

# Firework Simulation Configuration
GRAVITY = 0.1
MAX_ROCKETS = 10 # More rockets for a celebration
ROCKET_LIFESPAN = 40
PARTICLE_LIFESPAN = 50
TRAIL_LIFESPAN = 25
ROCKET_SIZE = 2
PARTICLE_SIZE = 2
TRAIL_SIZE = 1

# Font Colors
FONT_COLOR = graphics.Color(255, 255, 255)  # White for the main text
SUBS_COLOR = graphics.Color(255, 255, 0)  # Yellow for "SUBS"
NUM_COLOR = graphics.Color(255, 255, 255)  # White for the subscriber count
SCROLL_COLOR = graphics.Color(0, 255, 0)  # Green for scrolling text
SCROLL_NUM_COLOR = graphics.Color(255, 105, 180) # Pink for the number in the scroll

# -------------------------------------------------------------------------
# Classes
# -------------------------------------------------------------------------

class FireworkShow:
    """Manages the firework simulation, with nested Particle and Rocket classes."""

    def __init__(self, matrix):
        self.matrix = matrix
        self.rockets = []
        self.particles = []
        self.trails = []

        # Nested classes for encapsulation
        class Particle:
            """A single point of light in our firework simulation."""
            def __init__(self, x, y, vx, vy, color, lifespan):
                self.x = x
                self.y = y
                self.vx = vx
                self.vy = vy
                self.color = color
                self.lifespan = lifespan

            def update(self):
                """Update the particle's position and lifespan."""
                self.x += self.vx
                self.y += self.vy
                self.vy += GRAVITY
                self.lifespan -= 1

            def is_alive(self):
                """Check if the particle is still active."""
                return self.lifespan > 0

        class Rocket(Particle):
            """A special particle that represents a firework rocket."""
            def __init__(self, x, y, color):
                super().__init__(x, y, 0, -random.uniform(1.5, 2.5), color, ROCKET_LIFESPAN)

            def explode(self):
                """Create a burst of particles when the rocket explodes."""
                particles = []
                num_particles = random.randint(50, 80)
                for _ in range(num_particles):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(0.5, 4.5)
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    color = graphics.Color(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
                    # 'Particle' is available from the enclosing scope of the __init__ method
                    particles.append(Particle(self.x, self.y, vx, vy, color, PARTICLE_LIFESPAN))
                return particles
        
        # Store the nested classes on the instance
        self._Particle = Particle
        self._Rocket = Rocket


    def run(self, duration_seconds=10):
        """The main loop for the firework simulation."""
        canvas = self.matrix.CreateFrameCanvas()
        start_time = time.time()

        print("Starting firework celebration!")
        while time.time() - start_time < duration_seconds:
            canvas.Clear()

            if len(self.rockets) < MAX_ROCKETS and random.random() < 0.2: # Higher chance of rockets
                self.rockets.append(self._Rocket(random.randint(0, self.matrix.width - 1), self.matrix.height - 1, graphics.Color(255, 255, 255)))

            for rocket in self.rockets[:]:
                rocket.update()
                if not rocket.is_alive() or rocket.vy >= 0:
                    self.particles.extend(rocket.explode())
                    self.rockets.remove(rocket)
                else:
                    self.trails.append(self._Particle(rocket.x, rocket.y, 0, 0, rocket.color, TRAIL_LIFESPAN))
                    for i in range(ROCKET_SIZE):
                        graphics.DrawLine(canvas, int(rocket.x), int(rocket.y) + i, int(rocket.x) + ROCKET_SIZE - 1, int(rocket.y) + i, rocket.color)


            for particle in self.particles[:]:
                particle.update()
                if not particle.is_alive():
                    self.particles.remove(particle)
                else:
                    fade_factor = particle.lifespan / PARTICLE_LIFESPAN
                    faded_color = graphics.Color(
                        int(particle.color.red * fade_factor),
                        int(particle.color.green * fade_factor),
                        int(particle.color.blue * fade_factor)
                    )
                    for i in range(PARTICLE_SIZE):
                        graphics.DrawLine(canvas, int(particle.x), int(particle.y) + i, int(particle.x) + PARTICLE_SIZE - 1, int(particle.y) + i, faded_color)


            for trail in self.trails[:]:
                trail.lifespan -= 1
                if not trail.is_alive():
                    self.trails.remove(trail)
                else:
                    fade_factor = trail.lifespan / TRAIL_LIFESPAN
                    faded_color = graphics.Color(
                        int(trail.color.red * fade_factor * 0.5),
                        int(trail.color.green * fade_factor * 0.5),
                        int(trail.color.blue * fade_factor * 0.5)
                    )
                    for i in range(TRAIL_SIZE):
                         graphics.DrawLine(canvas, int(trail.x), int(trail.y) + i, int(trail.x) + TRAIL_SIZE - 1, int(trail.y) + i, faded_color)


            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(0.04)
        print("Firework celebration finished.")

class StaticTextDisplay:
    """Manages the display of static text and a counter."""
    def __init__(self, matrix):
        self.matrix = matrix
        self.font_subs = graphics.Font()
        self.font_subs.LoadFont(FONT_TITLE)
        self.font_num = graphics.Font()
        self.font_num.LoadFont(FONT_SUBS_NUMBER)
        self.subsColor = SUBS_COLOR
        self.numColor = NUM_COLOR

    def update(self, count):
        """Draws the static text and the current count to the canvas."""
        canvas = self.matrix.CreateFrameCanvas()
        canvas.Clear()
        
        # Display "SUBS"
        text_subs = "SUBS"
        text_width_subs = sum(self.font_subs.CharacterWidth(ord(c)) for c in text_subs)
        x_subs = (self.matrix.width - text_width_subs) // 2
        y_subs = int(self.matrix.height * 0.25)
        graphics.DrawText(canvas, self.font_subs, x_subs + 1, y_subs, self.subsColor, text_subs)
        graphics.DrawText(canvas, self.font_subs, x_subs, y_subs + 1, self.subsColor, text_subs)
        graphics.DrawText(canvas, self.font_subs, x_subs + 1, y_subs + 1, self.subsColor, text_subs)
        graphics.DrawText(canvas, self.font_subs, x_subs, y_subs, self.subsColor, text_subs)

        # Display the current count
        text_num = str(count)
        text_width_num = sum(self.font_num.CharacterWidth(ord(c)) for c in text_num)
        x_num = (self.matrix.width - text_width_num) // 2
        y_num = int(self.matrix.height * 0.75)
        graphics.DrawText(canvas, self.font_num, x_num + 1, y_num, self.numColor, text_num)
        graphics.DrawText(canvas, self.font_num, x_num, y_num + 1, self.numColor, text_num)
        graphics.DrawText(canvas, self.font_num, x_num + 1, y_num + 1, self.numColor, text_num)
        graphics.DrawText(canvas, self.font_num, x_num, y_num, self.numColor, text_num)
        
        self.matrix.SwapOnVSync(canvas)

class ScrollingText:
    """Manages displaying scrolling text with multiple colors."""
    def __init__(self, matrix, text_parts, font):
        self.matrix = matrix
        self.text_parts = text_parts # Expects a list of (text, color) tuples
        self.font = font

    def run(self):
        """The main loop for the scrolling text animation."""
        canvas = self.matrix.CreateFrameCanvas()
        
        # Calculate the total width of all text parts
        total_width = 0
        for text, color in self.text_parts:
            total_width += sum(self.font.CharacterWidth(ord(c)) for c in text)

        pos = canvas.width

        print("Scrolling text...")
        while pos + total_width > 0:
            canvas.Clear()
            
            current_x = pos
            y = int((self.matrix.height * 0.5) + (self.font.height / 3))

            # Draw each part of the text with its own color
            for text, color in self.text_parts:
                text_len = graphics.DrawText(canvas, self.font, current_x, y, color, text)
                current_x += text_len

            pos -= 1
            time.sleep(0.03)
            canvas = self.matrix.SwapOnVSync(canvas)
        print("Scrolling text finished.")


if __name__ == '__main__':
    subscriber_count = 0
    static_display = StaticTextDisplay(matrix)
    
    try:
        print("Starting subscriber counter. Press CTRL-C to stop.")
        while True:
            static_display.update(subscriber_count)

            # --- SIMULATED EVENT ---
            time.sleep(1)
            subscriber_count += 1
            print(f"New subscriber! Total: {subscriber_count}")
            # --- END SIMULATED EVENT ---
            
            # Trigger fireworks every 5 subscribers
            if subscriber_count > 0 and subscriber_count % 1 == 0:
                fireworks = FireworkShow(matrix)
                fireworks.run(duration_seconds=15)

            # Trigger scrolling text every 10 subscribers
            if subscriber_count > 0 and subscriber_count % 2 == 0:
                scroll_font = graphics.Font()
                scroll_font.LoadFont(FONT_SUBS_NUMBER)
                
                # Create a list of text parts with their colors
                text_parts = [
                    ("Thank you for ", SCROLL_COLOR),
                    (str(subscriber_count), SCROLL_NUM_COLOR),
                    (" subs!", SCROLL_COLOR)
                ]
                
                scroller = ScrollingText(matrix, text_parts, scroll_font)
                scroller.run()


    except KeyboardInterrupt:
        print("Exiting.")
        matrix.Clear()
