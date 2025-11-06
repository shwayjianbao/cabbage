import pygame, sys, time, random
import os
import math # Added for blade projectile rotation
#v3.0.1-audio
pygame.init()
# Initialize audio mixer
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception:
    pass
WIDTH, HEIGHT = 1100, 700
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Forsaken")

# Global variables

# Colors
WHITE = (255,255,255)
BLACK = (0,0,0)
SKY = (20,24,48)  # night sky
YELLOW = (255,255,0)
BLUE = (0,0,255)
GREEN = (0,200,0)
RED = (200,0,0)
GRAY = (150,150,150)
SKIN = (255,224,189)
GOLD = (255,215,0)
PURPLE = (140, 0, 140)
DARK_RED = (120, 0, 0)
MID_BLUE = (40, 60, 160)

clock = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 24)
BIG = pygame.font.SysFont("Arial", 72, bold=True)
PRESS_FONT = pygame.font.SysFont("Arial", 28, bold=True)

# Map / platforms
# Three full-width floors (ground + 2 upper solid floors) - PROPERLY 3x higher gaps
platforms = [
    pygame.Rect(0, HEIGHT-50, 3000, 50),   # Floor 1: ground (y=650)
    pygame.Rect(0, 250, 3000, 60),         # Floor 2: middle (y=250) - 400px gap from ground
    pygame.Rect(0, -150, 3000, 60),        # Floor 3: top (y=-150) - 400px gap from middle
]
# clouds (for parallax) -> convert to stars for night
stars = [(random.randint(0, 3000), random.randint(20, 180), random.randint(1,3)) for _ in range(120)]

# Map boundaries - barriers to prevent falling off
barriers = [
    pygame.Rect(0, 0, 20, HEIGHT),  # Left edge barrier
    pygame.Rect(2980, 0, 20, HEIGHT),  # Right edge barrier
    pygame.Rect(50, HEIGHT-150, 20, 100)  # Original middle barrier
]

# Game constants
GRAVITY = 0.65
NOOB_MAX_HP = 100
GAME_DURATION = 180  # seconds to survive

# cooldown dict stores next-ready timestamps
cooldowns = {
    "noob_speed": 0.0,     # Q: duration 5s, cd 10s
    "noob_invis": 0.0,     # E: duration 5s, cd 10s
    "noob_reduce": 0.0,    # R: duration 5s, cd 30s (slow + 90% damage reduction)
    "coolkid_dash": 0.0,   # /: duration 4s, cd 40s OR used as 1x1x1x1 blade cooldown
    "coolkid_slash": 0.0,  # ,: cd 1s (CoolKid slash)
    "coolkid_clone": 0.0,  # m: cd 10s
    "clone_slash": 0.0,    # clone own slash cd 1s
    "one_stun": 0.0,       # 1x1x1x1 comma stun blade cooldown
    "one_slash": 0.0,      # 1x1x1x1 period melee slash cooldown
    "one_arrow": 0.0,      # 1x1x1x1 M arrow ping cooldown
    # NEW: Survivor special abilities
    "bloxy_cola": 0.0, "slateskin_potion": 0.0, "ghostburger": 0.0,
    "clone": 0.0, "c00lgui": 0.0, "inject": 0.0,
    "slash": 0.0, "fried_chicken": 0.0,
    "block": 0.0, "charge": 0.0, "punch": 0.0,
    "sacrificial_dagger": 0.0, "crouch": 0.0, "ritual": 0.0,
    "coil_flip": 0.0, "one_shot": 0.0, "reroll": 0.0, "hat_fix": 0.0,
    "pizza_throw": 0.0, "rush_hour": 0.0,
    "spawn_protection": 0.0, "plasma_beam": 0.0,
    "sentry_construction": 0.0, "dispenser_construction": 0.0,
    "tripwire": 0.0, "subspace_tripmine": 0.0
}

ability_colors = {
    "noob_speed": (0,255,0),
    "noob_invis": (0,0,0),
    "coolkid_dash": (255,0,0),
    "coolkid_clone": (255,165,0),
    "coolkid_slash": (0,0,0),
    "clone_slash": (80,80,80),
    # NEW: Survivor special ability colors
    "bloxy_cola": (255,255,0), "slateskin_potion": (100,100,100), "ghostburger": (0,0,0),
    "clone": (0,0,0), "c00lgui": (0,0,0), "inject": (0,0,0),
    "slash": (255,0,0), "fried_chicken": (255,165,0),
    "block": (128,128,128), "charge": (128,128,128), "punch": (128,128,128),
    "sacrificial_dagger": (139,69,19), "crouch": (139,69,19), "ritual": (139,69,19),
    "coil_flip": (255,20,147), "one_shot": (255,20,147), "reroll": (255,20,147), "hat_fix": (255,20,147),
    "pizza_throw": (0,255,127), "rush_hour": (0,255,127),
    "spawn_protection": (75,0,130), "plasma_beam": (75,0,130),
    "sentry_construction": (0,100,200), "dispenser_construction": (0,100,200),
    "tripwire": (200,100,0), "subspace_tripmine": (200,100,0)
}

# Helper: draw cooldown bars at bottom of screen
def draw_cooldowns_bottom(abil_list, screen_x, screen_y, screen_width, is_noob=True):
    bar_w, bar_h = 60, 8  # bigger bars
    total_bars = len(abil_list)
    spacing = 10
    total_width = total_bars * bar_w + (total_bars - 1) * spacing
    start_x = screen_x + (screen_width - total_width) // 2  # center the bars
    start_y = screen_y - 40  # 40px from bottom

    for i, ab in enumerate(abil_list):
        now = time.time()
        cd_left = max(0, cooldowns.get(ab,0) - now)
        # define expected max cooldowns for bar lengths
        if ab in ("coolkid_slash","clone_slash"):
            max_cd = 1
        elif ab == "coolkid_dash":
            max_cd = 40
        elif ab == "noob_reduce":
            max_cd = 30
        elif ab == "one_arrow":
            max_cd = 40
        else:
            max_cd = 10
        ratio = 1 - min(1, cd_left / max_cd)  # filled ratio

        bar_x = start_x + i * (bar_w + spacing)
        # background
        pygame.draw.rect(win, GRAY, (bar_x, start_y, bar_w, bar_h))
        pygame.draw.rect(win, ability_colors.get(ab,(255,255,255)),
                         (bar_x, start_y, int(bar_w * ratio), bar_h))
        pygame.draw.rect(win, WHITE, (bar_x, start_y, bar_w, bar_h), 1)  # border

        # ability labels - BLACK AND BOLD with WHITE OUTLINE for better visibility
        label_map = {
            "noob_speed": "Q", "noob_invis": "E", "noob_reduce": "R",
            "coolkid_dash": "/", "coolkid_clone": "M", "coolkid_slash": ",",
            "one_stun": ",", "one_slash": ".", "one_arrow": "M", "clone_slash": ","
        }
        label = label_map.get(ab, "?")

        # Create BIGGER bold font for better visibility
        bold_font = pygame.font.SysFont("Arial", 28, bold=True)  # Much bigger font size

        # Draw white outline by rendering the text multiple times with offset
        label_center = (bar_x + bar_w//2, start_y - 12)
        outline_offsets = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]

        # Draw white outline
        for dx, dy in outline_offsets:
            outline_surf = bold_font.render(label, True, WHITE)
            outline_rect = outline_surf.get_rect(center=(label_center[0] + dx, label_center[1] + dy))
            win.blit(outline_surf, outline_rect)

        # Draw black text on top
        label_surf = bold_font.render(label, True, BLACK)
        label_rect = label_surf.get_rect(center=label_center)
        win.blit(label_surf, label_rect)

# Player classes
class Player:
    def __init__(self, x, y, is_noob=False):
        self.x = x
        self.y = y
        self.w = 40
        self.h = 60
        self.is_noob = is_noob
        self.base_speed = 5
        self.speed = self.base_speed
        self.vel_y = 0
        self.on_ground = False
        self.invisible = False
        self.hp = NOOB_MAX_HP if is_noob else 999
        self.stun_until = 0.0
        # slash visuals
        self.slash_line = None
        self.slash_end_time = 0.0
        self.slash_spawn_time = 0.0
        self.has_hit = False
        # clone flag
        self.is_clone = False
        # dash flags for coolkid
        self.dash_active = False
        self.dash_end = 0.0
        self.dash_has_hit = False
        # facing: -1 left, 1 right
        self.facing_dir = 1
        # last frame y for top-landing detection
        self.last_y = y
        self.variant = "CoolKid"  # or "1x1x1x1"
        
        # New attributes for survivor abilities
        self.last_move_time = time.time()
        self.fried_chicken_charges = 2  # For Shedletsky
        self.punch_channeling = False
        self.punch_channel_end = 0.0
        self.dagger_active = False
        self.dagger_end = 0.0
        self.crouching = False
        self.respawn_beacon = None
        self.weakness_stacks = 0
        self.weakness_until = 0.0
        self.sentry_construction_end = 0.0
        self.dispenser_construction_end = 0.0
        self.tripwire_active = False
        self.tripwire_end = 0.0
        self.tripwire_location = None
        self.movement_type = 0  # For 007n7 clones: 0=aimless, 1=pathfinding, 2=cursor
        # NPC AI state tracking
        self.ai_decision_until = 0.0  # When to make next AI decision
        self.ai_move_direction = 0  # -1 left, 0 idle, 1 right
        self.ai_last_jump_time = 0.0  # Track last jump to prevent spam

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def apply_gravity(self):
        # remember last y before moving
        self.last_y = self.y
        self.y += self.vel_y
        self.vel_y += GRAVITY
        if self.vel_y > 12:
            self.vel_y = 12

    def check_platforms(self, plats):
        r = self.rect()
        self.on_ground = False
        for p in plats:
            # vertical landing check: crossed top this frame while moving downward
            last_bottom = self.last_y + self.h
            cur_bottom = r.bottom
            if self.vel_y >= 0 and last_bottom <= p.top + 2 and cur_bottom >= p.top and r.right > p.left and r.left < p.right:
                # snap on top
                self.y = p.top - self.h
                self.vel_y = 0
                self.on_ground = True
                # refresh rect after snapping to avoid multiple triggers
                r = self.rect()
            # ceiling collision: prevent jumping up through floors
            last_top = self.last_y
            cur_top = r.top
            if self.vel_y < 0 and last_top >= p.bottom - 2 and cur_top <= p.bottom and r.right > p.left and r.left < p.right:
                # hit the underside; stop upward movement and place just below
                self.y = p.bottom
                self.vel_y = 0
                r = self.rect()

    def move_input(self, keys, left_key, right_key, jump_key, barriers_list=None):
        # don't move if stunned
        if time.time() < self.stun_until:
            return
        
        moved = False
        if keys[left_key]:
            # check all barriers
            can_move_left = True
            if barriers_list:
                for barrier in barriers_list:
                    if (self.x - self.speed) <= (barrier.x + barrier.w) and (self.x - self.speed + self.w) > barrier.x and (self.y + self.h) > barrier.y and self.y < (barrier.y + barrier.h):
                        can_move_left = False
                        break
            if can_move_left:
                self.x -= self.speed
                self.facing_dir = -1
                moved = True
        if keys[right_key]:
            # check all barriers
            can_move_right = True
            if barriers_list:
                for barrier in barriers_list:
                    if (self.x + self.w + self.speed) >= barrier.x and (self.x + self.speed) < (barrier.x + barrier.w) and (self.y + self.h) > barrier.y and self.y < (barrier.y + barrier.h):
                        can_move_right = False
                        break
            if can_move_right:
                self.x += self.speed
                self.facing_dir = 1
                moved = True
        if keys[jump_key] and self.on_ground:
            self.vel_y = -18
            self.on_ground = False
            moved = True
        
        # Update last_move_time if player moved
        if moved:
            self.last_move_time = time.time()

    def draw(self, offset_x, offset_y=0):
        # draw player; if survivor, use unique appearance based on type
        if self.is_noob:
            # Get survivor type colors and special features
            survivor_type = getattr(self, 'survivor_type', 'Noob')
            type_data = getattr(self, 'type_data', SURVIVOR_TYPES['Noob'])
            main_color = type_data['color']

            # head with type-specific color
            head_x = self.x - offset_x + 4
            head_y = self.y - offset_y
            head_w = self.w-8
            head_h = 18
            pygame.draw.rect(win, main_color, (head_x, head_y, head_w, head_h))
            # face on head (eyes + mouth)
            eye_r = 2
            # squint if stunned
            is_squint = time.time() < self.stun_until
            eye_y = head_y + head_h//2 - (1 if is_squint else 3)
            eye_lx = head_x + head_w//3
            eye_rx = head_x + 2*head_w//3
            if is_squint:
                pygame.draw.line(win, BLACK, (int(eye_lx-2), int(eye_y)), (int(eye_lx+2), int(eye_y)), 2)
                pygame.draw.line(win, BLACK, (int(eye_rx-2), int(eye_y)), (int(eye_rx+2), int(eye_y)), 2)
            else:
                pygame.draw.circle(win, BLACK, (int(eye_lx), int(eye_y)), eye_r)
                pygame.draw.circle(win, BLACK, (int(eye_rx), int(eye_y)), eye_r)
            mouth_y = head_y + head_h - 5
            pygame.draw.line(win, BLACK, (head_x + head_w//3, mouth_y), (head_x + 2*head_w//3, mouth_y), 2)
            # subtle top shadow on head
            shadow = pygame.Surface((head_w, head_h//2), pygame.SRCALPHA)
            shadow.fill((0,0,0,40))
            win.blit(shadow, (head_x, head_y))
            # torso and pants with type-specific styling
            if survivor_type == "007n7":
                # Light-skinned Robloxian with Burger Bob hat, blue shirt, black pants, smiley rock face
                pygame.draw.rect(win, (255,220,177), (head_x, head_y, head_w, head_h))  # Light skin
                pygame.draw.rect(win, (0,0,255), (self.x - offset_x, self.y - offset_y + 18, self.w, 26))  # Blue shirt
                pygame.draw.rect(win, (0,0,0), (self.x - offset_x, self.y - offset_y + 44, self.w, 16))  # Black pants
                # Burger Bob hat (brown)
                pygame.draw.rect(win, (139,69,19), (head_x - 2, head_y - 8, head_w + 4, 8))
                # Smiley rock face on torso
                pygame.draw.circle(win, (100,100,100), (self.x - offset_x + self.w//2, self.y - offset_y + 30), 8)
                pygame.draw.circle(win, (255,255,255), (self.x - offset_x + self.w//2 - 3, self.y - offset_y + 28), 2)  # Left eye
                pygame.draw.circle(win, (255,255,255), (self.x - offset_x + self.w//2 + 3, self.y - offset_y + 28), 2)  # Right eye
                pygame.draw.arc(win, (255,255,255), (self.x - offset_x + self.w//2 - 4, self.y - offset_y + 30, 8, 6), 0, 3.14, 2)  # Smile
            elif survivor_type == "Shedletsky":
                # Brown hair, sword, red outfit
                pygame.draw.rect(win, (139,69,19), (head_x, head_y, head_w, head_h))  # Brown hair
                pygame.draw.rect(win, (255,0,0), (self.x - offset_x, self.y - offset_y + 18, self.w, 26))  # Red shirt
                pygame.draw.rect(win, (200,0,0), (self.x - offset_x, self.y - offset_y + 44, self.w, 16))  # Red pants
                # Sword
                pygame.draw.line(win, (192,192,192), (self.x - offset_x + self.w + 5, self.y - offset_y + 20), (self.x - offset_x + self.w + 5, self.y - offset_y + 40), 3)
                pygame.draw.rect(win, (139,69,19), (self.x - offset_x + self.w + 3, self.y - offset_y + 40, 4, 8))  # Sword handle
            elif survivor_type == "Guest 1337":
                # War uniform, blue hair
                pygame.draw.rect(win, (0,0,255), (head_x, head_y, head_w, head_h))  # Blue hair
                pygame.draw.rect(win, (100,100,100), (self.x - offset_x, self.y - offset_y + 18, self.w, 26))  # Gray uniform
                pygame.draw.rect(win, (80,80,80), (self.x - offset_x, self.y - offset_y + 44, self.w, 16))  # Gray pants
                # Military details
                pygame.draw.rect(win, (255,255,255), (self.x - offset_x + 5, self.y - offset_y + 20, 8, 4))  # Button
                pygame.draw.rect(win, (255,255,255), (self.x - offset_x + 5, self.y - offset_y + 26, 8, 4))  # Button
                pygame.draw.rect(win, (255,255,255), (self.x - offset_x + 5, self.y - offset_y + 32, 8, 4))  # Button
            elif survivor_type == "Two Time":
                # Pale skin, messy black hair, black shirt, grey pants, manic expression
                pygame.draw.rect(win, (255,240,220), (head_x, head_y, head_w, head_h))  # Pale skin
                pygame.draw.rect(win, (0,0,0), (self.x - offset_x, self.y - offset_y + 18, self.w, 26))  # Black shirt
                pygame.draw.rect(win, (128,128,128), (self.x - offset_x, self.y - offset_y + 44, self.w, 16))  # Grey pants
                # Messy black hair
                pygame.draw.rect(win, (0,0,0), (head_x - 2, head_y - 5, head_w + 4, 6))
                # Manic expression (wide eyes)
                pygame.draw.circle(win, (0,0,0), (head_x + head_w//3, head_y + head_h//2), 3)
                pygame.draw.circle(win, (0,0,0), (head_x + 2*head_w//3, head_y + head_h//2), 3)
                # Fingerless gloves (hands)
                pygame.draw.rect(win, (139,69,19), (self.x - offset_x - 5, self.y - offset_y + 25, 8, 12))
                pygame.draw.rect(win, (139,69,19), (self.x - offset_x + self.w - 3, self.y - offset_y + 25, 8, 12))
            elif survivor_type == "Chance Forsaken":
                # Black hat with sunglasses
                pygame.draw.rect(win, (255,220,177), (head_x, head_y, head_w, head_h))  # Light skin
                pygame.draw.rect(win, (255,20,147), (self.x - offset_x, self.y - offset_y + 18, self.w, 26))  # Pink shirt
                pygame.draw.rect(win, (200,10,120), (self.x - offset_x, self.y - offset_y + 44, self.w, 16))  # Pink pants
                # Black hat
                pygame.draw.rect(win, (0,0,0), (head_x - 2, head_y - 8, head_w + 4, 8))
                # Sunglasses
                pygame.draw.rect(win, (0,0,0), (head_x + 2, head_y + 4, head_w - 4, 6))
                pygame.draw.rect(win, (100,100,100), (head_x + 4, head_y + 5, head_w//2 - 2, 4))  # Left lens
                pygame.draw.rect(win, (100,100,100), (head_x + head_w//2 + 2, head_y + 5, head_w//2 - 2, 4))  # Right lens
            elif survivor_type == "Elliot":
                # Yellow skin, red visor with ROBLOX logo, red employee uniform, black undershirt and pants
                pygame.draw.rect(win, (255,255,0), (head_x, head_y, head_w, head_h))  # Yellow skin
                pygame.draw.rect(win, (0,0,0), (self.x - offset_x, self.y - offset_y + 18, self.w, 26))  # Black undershirt
                pygame.draw.rect(win, (0,0,0), (self.x - offset_x, self.y - offset_y + 44, self.w, 16))  # Black pants
                # Red visor
                pygame.draw.rect(win, (255,0,0), (head_x, head_y + 2, head_w, 6))
                # ROBLOX logo on visor (simplified as white text area)
                pygame.draw.rect(win, (255,255,255), (head_x + 2, head_y + 3, head_w - 4, 4))
                # Red employee uniform over black
                pygame.draw.rect(win, (255,0,0), (self.x - offset_x + 2, self.y - offset_y + 20, self.w - 4, 22))
            elif survivor_type == "Dusekkar":
                # Blue pumpkin with staff
                pygame.draw.rect(win, (0,0,255), (head_x, head_y, head_w, head_h))  # Blue pumpkin head
                pygame.draw.rect(win, (0,100,200), (self.x - offset_x, self.y - offset_y + 18, self.w, 26))  # Blue body
                pygame.draw.rect(win, (0,80,160), (self.x - offset_x, self.y - offset_y + 44, self.w, 16))  # Blue pants
                # Pumpkin face
                pygame.draw.circle(win, (255,255,0), (head_x + head_w//3, head_y + head_h//3), 2)  # Left eye
                pygame.draw.circle(win, (255,255,0), (head_x + 2*head_w//3, head_y + head_h//3), 2)  # Right eye
                pygame.draw.arc(win, (255,255,0), (head_x + head_w//4, head_y + 2*head_h//3, head_w//2, head_h//3), 0, 3.14, 2)  # Mouth
                # Staff
                pygame.draw.line(win, (139,69,19), (self.x - offset_x - 10, self.y - offset_y + 20), (self.x - offset_x - 10, self.y - offset_y + 50), 4)
                pygame.draw.circle(win, (255,0,0), (self.x - offset_x - 10, self.y - offset_y + 15), 6)  # Staff orb
            elif survivor_type == "Builderman":
                # Builder hat, grey skin, happy face
                pygame.draw.rect(win, (128,128,128), (head_x, head_y, head_w, head_h))  # Grey skin
                pygame.draw.rect(win, (0,100,200), (self.x - offset_x, self.y - offset_y + 18, self.w, 26))  # Blue shirt
                pygame.draw.rect(win, (0,80,160), (self.x - offset_x, self.y - offset_y + 44, self.w, 16))  # Blue pants
                # Builder hat (yellow hard hat)
                pygame.draw.rect(win, (255,255,0), (head_x - 2, head_y - 8, head_w + 4, 8))
                # Happy face
                pygame.draw.circle(win, (0,0,0), (head_x + head_w//3, head_y + head_h//3), 2)  # Left eye
                pygame.draw.circle(win, (0,0,0), (head_x + 2*head_w//3, head_y + head_h//3), 2)  # Right eye
                pygame.draw.arc(win, (0,0,0), (head_x + head_w//4, head_y + 2*head_h//3, head_w//2, head_h//3), 0, 3.14, 2)  # Smile
            elif survivor_type == "Taph":
                # Black cloak with yellow lines
                pygame.draw.rect(win, (0,0,0), (self.x - offset_x, self.y - offset_y + 18, self.w, 26))  # Black cloak
                pygame.draw.rect(win, (20,20,20), (self.x - offset_x, self.y - offset_y + 44, self.w, 16))  # Black pants
                # Yellow lines on cloak
                pygame.draw.line(win, (255,255,0), (self.x - offset_x + 5, self.y - offset_y + 20), (self.x - offset_x + self.w - 5, self.y - offset_y + 20), 2)
                pygame.draw.line(win, (255,255,0), (self.x - offset_x + 5, self.y - offset_y + 30), (self.x - offset_x + self.w - 5, self.y - offset_y + 30), 2)
                pygame.draw.line(win, (255,255,0), (self.x - offset_x + 5, self.y - offset_y + 40), (self.x - offset_x + self.w - 5, self.y - offset_y + 40), 2)
            else:  # Noob (default)
                # Classic Noob (blue torso, green pants)
                pygame.draw.rect(win, BLUE, (self.x - offset_x, self.y - offset_y + 18, self.w, 26))
                pygame.draw.rect(win, GREEN, (self.x - offset_x, self.y - offset_y + 44, self.w, 16))
            if self.invisible:
                # overlay to show invisibility
                s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
                s.fill((255,255,255,120))
                win.blit(s, (self.x - offset_x, self.y - offset_y))
        else:
            # killer visuals
            if getattr(self, 'variant', 'CoolKid') == '1x1x1x1':
                # BLACK body (changed from green)
                body_rect = pygame.Rect(self.x - offset_x, self.y - offset_y, self.w, self.h)
                pygame.draw.rect(win, (30,30,30), body_rect)  # dark black/gray
                pygame.draw.rect(win, (0,0,0), body_rect, 2)  # black outline

                # GREEN hat with dominos
                hat_rect = pygame.Rect(self.x - offset_x - 2, self.y - offset_y - 15, self.w + 4, 18)
                pygame.draw.rect(win, (0,180,0), hat_rect)  # green hat
                pygame.draw.rect(win, (0,120,0), hat_rect, 2)  # darker green outline

                # Three BIGGER dominos on TOP of green hat (left-middle-right)
                domino_positions = [self.w//4, self.w//2, 3*self.w//4]  # left, middle, right
                for i, pos in enumerate(domino_positions):
                    domino_x = self.x - offset_x + pos - 6  # center each domino
                    domino_y = self.y - offset_y - 20  # ON TOP of hat
                    pygame.draw.rect(win, (20,20,20), (domino_x, domino_y, 12, 16))  # BIGGER domino body
                    pygame.draw.rect(win, (255,255,255), (domino_x, domino_y, 12, 16), 1)  # white outline
                    # domino dots (bigger spacing)
                    pygame.draw.circle(win, (255,255,255), (domino_x + 6, domino_y + 4), 1)
                    pygame.draw.circle(win, (255,255,255), (domino_x + 6, domino_y + 12), 1)

                # BIGGER Asymmetric red cross eye (only on LEFT side)
                eye_x = self.x - offset_x + self.w//3  # left side of face
                eye_y = self.y - offset_y + self.h//3
                pygame.draw.line(win, (220,0,0), (eye_x-8, eye_y), (eye_x+8, eye_y), 4)  # bigger horizontal line
                pygame.draw.line(win, (220,0,0), (eye_x, eye_y-8), (eye_x, eye_y+8), 4)  # bigger vertical line

                # Right side has nothing (just black)
                # NO MOUTH - removed for cleaner look
            else:
                # original CoolKid red face
                body_rect = pygame.Rect(self.x - offset_x, self.y - offset_y, self.w, self.h)
                pygame.draw.rect(win, RED, body_rect)
                pygame.draw.rect(win, (120,0,0), body_rect, 2)
                shade = pygame.Surface((self.w//3, self.h), pygame.SRCALPHA)
                shade.fill((0,0,0,60))
                win.blit(shade, (self.x - offset_x + 2*self.w//3, self.y - offset_y))
                eye_r = 6
                eye_y = self.y - offset_y + self.h//3
                eye_lx = self.x - offset_x + self.w//3
                eye_rx = self.x - offset_x + 2*self.w//3
                pygame.draw.circle(win, BLACK, (int(eye_lx), int(eye_y)), eye_r)
                pygame.draw.circle(win, BLACK, (int(eye_rx), int(eye_y)), eye_r)
                pygame.draw.circle(win, WHITE, (int(eye_lx - 2), int(eye_y - 2)), 2)
                pygame.draw.circle(win, WHITE, (int(eye_rx - 2), int(eye_y - 2)), 2)
                mouth_y = self.y - offset_y + 2*self.h//3
                pygame.draw.line(win, BLACK, (self.x - offset_x + self.w//4, mouth_y), (self.x - offset_x + 3*self.w//4, mouth_y), 3)
        # slash drawing (if active)
        if self.slash_line:
            a, b = self.slash_line
            pygame.draw.line(win, BLACK, (a[0] - offset_x, a[1] - offset_y), (b[0] - offset_x, b[1] - offset_y), 8)

# Slash as lightweight struct in this code base (we draw lines directly on owner.slash_line)
# We'll keep slashes attached to owners

# SURPRISE! Multiple Survivor Types with unique abilities!
SURVIVOR_TYPES = {
    "Noob": {"color": (255,255,0), "speed": 5, "hp": 100, "price": "Free", "abilities": ["bloxy_cola", "slateskin_potion", "ghostburger"]},
    "007n7": {"color": (0,0,0), "speed": 6, "hp": 90, "price": "Free", "abilities": ["clone", "c00lgui", "inject"]},
    "Shedletsky": {"color": (255,0,0), "speed": 5, "hp": 100, "price": "Free", "abilities": ["slash", "fried_chicken"]},
    "Guest 1337": {"color": (128,128,128), "speed": 5, "hp": 115, "price": "Free", "abilities": ["block", "charge", "punch"]},
    "Two Time": {"color": (139,69,19), "speed": 5, "hp": 100, "price": "Free", "abilities": ["sacrificial_dagger", "crouch", "ritual"]},
    "Chance Forsaken": {"color": (255,20,147), "speed": 5, "hp": 80, "price": "Free", "abilities": ["coil_flip", "one_shot", "reroll", "hat_fix"]},
    "Elliot": {"color": (0,255,127), "speed": 5, "hp": 100, "price": "Free", "abilities": ["pizza_throw", "rush_hour"]},
    "Dusekkar": {"color": (75,0,130), "speed": 5, "hp": 100, "price": "Free", "abilities": ["spawn_protection", "plasma_beam"]},
    "Builderman": {"color": (0,100,200), "speed": 4, "hp": 100, "price": "Free", "abilities": ["sentry_construction", "dispenser_construction"]},
    "Taph": {"color": (200,100,0), "speed": 5, "hp": 100, "price": "Free", "abilities": ["tripwire", "subspace_tripmine"]}
}

# Random spawn points for all survivors - CORRECTED for equal 400px gaps
SURVIVOR_SPAWNS = [
    # Floor 1 (ground) spawns
    (120, HEIGHT-110), (600, HEIGHT-110), (1200, HEIGHT-110), (1800, HEIGHT-110), (2400, HEIGHT-110),
    # Floor 2 (middle) spawns - CORRECTED for y=250 floor
    (300, 190), (800, 190), (1400, 190), (2000, 190), (2600, 190),
    # Floor 3 (top) spawns
    (400, -210), (1000, -210), (1600, -210), (2200, -210)
]

# Create MULTIPLE SURVIVORS with different types!
survivors = []
selected_survivor_types = []
selected_killer = "CoolKid"  # default
coolkid = None
clones = []
main_character = None  # Player-controlled character
npcs = []  # AI-controlled NPCs

# Survivors will be created after selection screens
import random

# Title screen with killer selection

def title_screen():
    global win, WIDTH, HEIGHT
    # splash
    while True:
        win.fill(SKY)
        # Centered moon
        pygame.draw.circle(win, (255,255,0), (WIDTH//2, 120), 35)
        pygame.draw.circle(win, SKY, (WIDTH//2 + 12, 108), 15)  # crescent effect
        for sx, sy, sr in stars:
            pygame.draw.circle(win, (240, 240, 200), (sx, sy), sr)

        # Centered title with better positioning
        title_text = BIG.render("FORSAKEN", True, WHITE)
        title_rect = title_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 80))
        win.blit(title_text, title_rect)

        # Centered subtitle
        subtitle = PRESS_FONT.render("A Survival Horror Game", True, GOLD)
        subtitle_rect = subtitle.get_rect(center=(WIDTH//2, HEIGHT//2 - 20))
        win.blit(subtitle, subtitle_rect)

        # Centered press button
        press = PRESS_FONT.render("Press ENTER to Continue", True, WHITE)
        press_rect = press.get_rect(center=(WIDTH//2, HEIGHT//2 + 60))
        win.blit(press, press_rect)
        pygame.display.update()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN:
                    break
        else:
            continue
        break
    # selection menu
    killer_select()

def killer_select():
    global selected_killer, win, WIDTH, HEIGHT
    options = ["CoolKid", "1x1x1x1"]
    idx = 0
    while True:
        win.fill(SKY)
        # Centered moon
        pygame.draw.circle(win, (255,255,0), (WIDTH//2, 80), 25)
        pygame.draw.circle(win, SKY, (WIDTH//2 + 8, 72), 10)  # crescent effect
        for sx, sy, sr in stars:
            pygame.draw.circle(win, (240, 240, 200), (sx, sy), sr)

        # Centered title
        title_text = PRESS_FONT.render("Choose Your Killer", True, GOLD)
        title_rect = title_text.get_rect(center=(WIDTH//2, 150))
        win.blit(title_text, title_rect)

        # Centered options with proper spacing
        total_width = len(options) * 180  # reduced spacing for better centering
        start_x = WIDTH//2 - total_width//2

        for i, name in enumerate(options):
            col = GOLD if i == idx else WHITE
            txt = PRESS_FONT.render(name, True, col)

            # Center each option within its allocated space
            option_center_x = start_x + i * 180 + 90
            txt_rect = txt.get_rect(center=(option_center_x, 220))
            win.blit(txt, txt_rect)

            # Centered preview box
            preview = pygame.Rect(option_center_x - 40, 260, 80, 100)
            pygame.draw.rect(win, (255,255,255), preview, 2)

            if name == 'CoolKid':
                pygame.draw.rect(win, RED, (preview.x+10, preview.y+20, 60, 60))
                pygame.draw.circle(win, BLACK, (preview.x+28, preview.y+46), 6)
                pygame.draw.circle(win, BLACK, (preview.x+52, preview.y+46), 6)
            else:  # 1x1x1x1 preview
                # Black body
                pygame.draw.rect(win, (30,30,30), (preview.x+10, preview.y+20, 60, 60))
                pygame.draw.rect(win, (0,0,0), (preview.x+10, preview.y+20, 60, 60), 2)

                # Green hat
                pygame.draw.rect(win, (0,180,0), (preview.x+8, preview.y+10, 64, 15))
                pygame.draw.rect(win, (0,120,0), (preview.x+8, preview.y+10, 64, 15), 1)

                # BIGGER Dominos on TOP of hat (left-middle-right)
                domino_positions = [18, 32, 46]  # left, middle, right positions
                for i, pos in enumerate(domino_positions):
                    domino_x = preview.x + pos
                    pygame.draw.rect(win, (20,20,20), (domino_x, preview.y+5, 10, 12))  # BIGGER
                    pygame.draw.rect(win, (255,255,255), (domino_x, preview.y+5, 10, 12), 1)

                # BIGGER Asymmetric red cross (left side only)
                eye_x = preview.x + 28  # left side
                eye_y = preview.y + 45
                pygame.draw.line(win, (220,0,0), (eye_x-5, eye_y), (eye_x+5, eye_y), 3)  # bigger horizontal
                pygame.draw.line(win, (220,0,0), (eye_x, eye_y-5), (eye_x, eye_y+5), 3)  # bigger vertical

        # Centered instructions
        instructions = FONT.render("Use ← → arrows to select", True, WHITE)
        instructions_rect = instructions.get_rect(center=(WIDTH//2, 400))
        win.blit(instructions, instructions_rect)

        # Centered confirm button
        button = PRESS_FONT.render("Press ENTER to Confirm", True, WHITE)
        button_rect = button.get_rect(center=(WIDTH//2, 450))
        win.blit(button, button_rect)
        pygame.display.update()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LEFT:
                    idx = (idx - 1) % len(options)
                elif ev.key == pygame.K_RIGHT:
                    idx = (idx + 1) % len(options)
                elif ev.key == pygame.K_RETURN:
                    selected_killer = options[idx]
                    return

def survivor_select():
    """Let player choose their survivor team"""
    global selected_survivor_types, win, WIDTH, HEIGHT
    available_types = list(SURVIVOR_TYPES.keys())
    selected_survivor_types = []
    current_idx = 0

    while len(selected_survivor_types) < 3:  # Select 3 survivors
        win.fill(SKY)
        # Centered moon
        pygame.draw.circle(win, (255,255,0), (WIDTH//2, 60), 20)
        pygame.draw.circle(win, SKY, (WIDTH//2 + 6, 54), 8)
        for sx, sy, sr in stars:
            pygame.draw.circle(win, (240, 240, 200), (sx, sy), sr)

        # Title
        title_text = PRESS_FONT.render(f"Choose Survivor {len(selected_survivor_types)+1}/3", True, GOLD)
        title_rect = title_text.get_rect(center=(WIDTH//2, 120))
        win.blit(title_text, title_rect)

        # Show available survivors - layout for 10 survivors
        cols = 3  # 3 columns for 10 survivors
        for i, survivor_type in enumerate(available_types):
            if survivor_type in selected_survivor_types:
                continue  # Skip already selected

            col = GOLD if i == current_idx else WHITE
            type_data = SURVIVOR_TYPES[survivor_type]

            # Position - 3 column layout
            x = WIDTH//2 - 300 + (i % cols) * 200  # 200px spacing between columns
            y = 160 + (i // cols) * 160  # 160px spacing between rows

            # Survivor name
            txt = FONT.render(survivor_type, True, col)
            txt_rect = txt.get_rect(center=(x, y))
            win.blit(txt, txt_rect)

            # Preview box - bigger for better visibility
            preview = pygame.Rect(x - 50, y + 25, 100, 100)
            pygame.draw.rect(win, WHITE, preview, 3)

            # Draw mini survivor - bigger
            main_color = type_data['color']
            pygame.draw.rect(win, main_color, (preview.x + 15, preview.y + 15, 70, 20))  # head

            if survivor_type == "007n7":
                # Light skin, blue shirt, black pants, burger hat
                pygame.draw.rect(win, (255,220,177), (preview.x + 15, preview.y + 15, 70, 20))  # Light skin head
                pygame.draw.rect(win, (0,0,255), (preview.x + 15, preview.y + 35, 70, 30))  # Blue shirt
                pygame.draw.rect(win, (0,0,0), (preview.x + 15, preview.y + 65, 70, 20))  # Black pants
                pygame.draw.rect(win, (139,69,19), (preview.x + 13, preview.y + 7, 74, 8))  # Burger hat
                # Smiley rock face
                pygame.draw.circle(win, (100,100,100), (preview.x + 50, preview.y + 50), 6)
            elif survivor_type == "Shedletsky":
                # Brown hair, red outfit, sword
                pygame.draw.rect(win, (139,69,19), (preview.x + 15, preview.y + 15, 70, 20))  # Brown hair
                pygame.draw.rect(win, (255,0,0), (preview.x + 15, preview.y + 35, 70, 30))  # Red shirt
                pygame.draw.rect(win, (200,0,0), (preview.x + 15, preview.y + 65, 70, 20))  # Red pants
                # Sword
                pygame.draw.line(win, (192,192,192), (preview.x + 90, preview.y + 40), (preview.x + 90, preview.y + 60), 2)
            elif survivor_type == "Guest 1337":
                # Blue hair, gray uniform
                pygame.draw.rect(win, (0,0,255), (preview.x + 15, preview.y + 15, 70, 20))  # Blue hair
                pygame.draw.rect(win, (100,100,100), (preview.x + 15, preview.y + 35, 70, 30))  # Gray uniform
                pygame.draw.rect(win, (80,80,80), (preview.x + 15, preview.y + 65, 70, 20))  # Gray pants
            elif survivor_type == "Two Time":
                # Pale skin, black shirt, gray pants, messy hair
                pygame.draw.rect(win, (255,240,220), (preview.x + 15, preview.y + 15, 70, 20))  # Pale skin
                pygame.draw.rect(win, (0,0,0), (preview.x + 15, preview.y + 35, 70, 30))  # Black shirt
                pygame.draw.rect(win, (128,128,128), (preview.x + 15, preview.y + 65, 70, 20))  # Gray pants
                pygame.draw.rect(win, (0,0,0), (preview.x + 13, preview.y + 10, 74, 6))  # Messy hair
            elif survivor_type == "Chance Forsaken":
                # Light skin, pink outfit, black hat, sunglasses
                pygame.draw.rect(win, (255,220,177), (preview.x + 15, preview.y + 15, 70, 20))  # Light skin
                pygame.draw.rect(win, (255,20,147), (preview.x + 15, preview.y + 35, 70, 30))  # Pink shirt
                pygame.draw.rect(win, (200,10,120), (preview.x + 15, preview.y + 65, 70, 20))  # Pink pants
                pygame.draw.rect(win, (0,0,0), (preview.x + 13, preview.y + 7, 74, 8))  # Black hat
                pygame.draw.rect(win, (0,0,0), (preview.x + 17, preview.y + 19, 66, 6))  # Sunglasses
            elif survivor_type == "Elliot":
                # Yellow skin, red visor, red uniform over black
                pygame.draw.rect(win, (255,255,0), (preview.x + 15, preview.y + 15, 70, 20))  # Yellow skin
                pygame.draw.rect(win, (0,0,0), (preview.x + 15, preview.y + 35, 70, 30))  # Black undershirt
                pygame.draw.rect(win, (0,0,0), (preview.x + 15, preview.y + 65, 70, 20))  # Black pants
                pygame.draw.rect(win, (255,0,0), (preview.x + 15, preview.y + 17, 70, 6))  # Red visor
                pygame.draw.rect(win, (255,0,0), (preview.x + 17, preview.y + 37, 66, 26))  # Red uniform
            elif survivor_type == "Dusekkar":
                # Blue pumpkin, staff
                pygame.draw.rect(win, (0,0,255), (preview.x + 15, preview.y + 15, 70, 20))  # Blue pumpkin head
                pygame.draw.rect(win, (0,100,200), (preview.x + 15, preview.y + 35, 70, 30))  # Blue body
                pygame.draw.rect(win, (0,80,160), (preview.x + 15, preview.y + 65, 70, 20))  # Blue pants
                # Pumpkin face
                pygame.draw.circle(win, (255,255,0), (preview.x + 35, preview.y + 25), 2)  # Left eye
                pygame.draw.circle(win, (255,255,0), (preview.x + 55, preview.y + 25), 2)  # Right eye
                # Staff
                pygame.draw.line(win, (139,69,19), (preview.x + 5, preview.y + 40), (preview.x + 5, preview.y + 70), 3)
                pygame.draw.circle(win, (255,0,0), (preview.x + 5, preview.y + 35), 4)  # Staff orb
            elif survivor_type == "Builderman":
                # Gray skin, blue outfit, builder hat, happy face
                pygame.draw.rect(win, (128,128,128), (preview.x + 15, preview.y + 15, 70, 20))  # Gray skin
                pygame.draw.rect(win, (0,100,200), (preview.x + 15, preview.y + 35, 70, 30))  # Blue shirt
                pygame.draw.rect(win, (0,80,160), (preview.x + 15, preview.y + 65, 70, 20))  # Blue pants
                pygame.draw.rect(win, (255,255,0), (preview.x + 13, preview.y + 7, 74, 8))  # Builder hat
                # Happy face
                pygame.draw.circle(win, (0,0,0), (preview.x + 35, preview.y + 25), 2)  # Left eye
                pygame.draw.circle(win, (0,0,0), (preview.x + 55, preview.y + 25), 2)  # Right eye
            elif survivor_type == "Taph":
                # Black cloak with yellow lines
                pygame.draw.rect(win, (0,0,0), (preview.x + 15, preview.y + 35, 70, 30))  # Black cloak
                pygame.draw.rect(win, (20,20,20), (preview.x + 15, preview.y + 65, 70, 20))  # Black pants
                # Yellow lines
                pygame.draw.line(win, (255,255,0), (preview.x + 20, preview.y + 40), (preview.x + 80, preview.y + 40), 2)
                pygame.draw.line(win, (255,255,0), (preview.x + 20, preview.y + 50), (preview.x + 80, preview.y + 50), 2)
                pygame.draw.line(win, (255,255,0), (preview.x + 20, preview.y + 60), (preview.x + 80, preview.y + 60), 2)
            else:  # Noob (default)
                pygame.draw.rect(win, BLUE, (preview.x + 15, preview.y + 35, 70, 30))
                pygame.draw.rect(win, GREEN, (preview.x + 15, preview.y + 65, 70, 20))

            # Stats - positioned below the bigger preview box
            stats = FONT.render(f"HP:{type_data['hp']} SPD:{type_data['speed']}", True, WHITE)
            stats_rect = stats.get_rect(center=(x, y + 140))
            win.blit(stats, stats_rect)

        # Instructions - positioned lower to accommodate bigger layout
        if selected_survivor_types:
            selected_text = f"Selected: {', '.join(selected_survivor_types)}"
            selected_surf = FONT.render(selected_text, True, (0,255,0))
            selected_rect = selected_surf.get_rect(center=(WIDTH//2, HEIGHT - 100))
            win.blit(selected_surf, selected_rect)

        instructions = FONT.render("Use ← → arrows, ENTER to select, BACKSPACE to remove last, or CLICK to select", True, WHITE)
        instructions_rect = instructions.get_rect(center=(WIDTH//2, HEIGHT - 70))
        win.blit(instructions, instructions_rect)

        pygame.display.update()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                available_indices = [i for i, t in enumerate(available_types) if t not in selected_survivor_types]
                if ev.key == pygame.K_LEFT and available_indices:
                    current_idx = (current_idx - 1) % len(available_types)
                    while current_idx not in available_indices:
                        current_idx = (current_idx - 1) % len(available_types)
                elif ev.key == pygame.K_RIGHT and available_indices:
                    current_idx = (current_idx + 1) % len(available_types)
                    while current_idx not in available_indices:
                        current_idx = (current_idx + 1) % len(available_types)
                elif ev.key == pygame.K_RETURN and available_indices:
                    if current_idx < len(available_types):
                        survivor_type = available_types[current_idx]
                        if survivor_type not in selected_survivor_types:
                            selected_survivor_types.append(survivor_type)
                elif ev.key == pygame.K_BACKSPACE and selected_survivor_types:
                    selected_survivor_types.pop()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:  # Left mouse button
                    mouse_x, mouse_y = ev.pos
                    # Check if click is on a survivor preview
                    for i, survivor_type in enumerate(available_types):
                        if survivor_type in selected_survivor_types:
                            continue  # Skip already selected

                        # Calculate position for this survivor
                        x = WIDTH//2 - 300 + (i % cols) * 200
                        y = 160 + (i // cols) * 160

                        # Check if click is within preview area
                        preview_rect = pygame.Rect(x - 50, y + 25, 100, 100)
                        if preview_rect.collidepoint(mouse_x, mouse_y):
                            selected_survivor_types.append(survivor_type)
                            break
                elif ev.button == 3 and selected_survivor_types:  # Right mouse button to remove last
                    selected_survivor_types.pop()

def create_survivors():
    """Create survivor instances after selection"""
    global survivors, noob, main_character, npcs
    survivors.clear()
    npcs = []  # NPC survivors

    # Create survivors based on player selection
    for i, survivor_type in enumerate(selected_survivor_types):
        spawn_pos = random.choice(SURVIVOR_SPAWNS)
        survivor = Player(spawn_pos[0], spawn_pos[1], is_noob=True)
        survivor.survivor_type = survivor_type
        survivor.type_data = SURVIVOR_TYPES[survivor_type]
        survivor.base_speed = survivor.type_data["speed"]
        survivor.speed = survivor.base_speed
        survivor.hp = survivor.type_data["hp"]
        survivor.max_hp = survivor.type_data["hp"]
        survivor.special_cooldown = 0.0

        if i == 0:
            # First choice is the main character (player controlled)
            survivor.is_main_character = True
            main_character = survivor
            noob = survivor  # Keep for compatibility
        else:
            # Other choices are NPCs (AI controlled)
            survivor.is_main_character = False
            survivor.is_npc = True
            npcs.append(survivor)

        survivors.append(survivor)

# start
title_screen()
survivor_select()  # Add survivor selection
create_survivors()  # Create survivors after selection
# instantiate killer after selection
if selected_killer == "CoolKid":
    coolkid = Player(300, HEIGHT - 150, is_noob=False)
    coolkid.variant = "CoolKid"
else:
    coolkid = Player(300, HEIGHT - 150, is_noob=False)
    coolkid.variant = "1x1x1x1"
    coolkid.base_speed = int(coolkid.base_speed * 0.85) if isinstance(coolkid.base_speed, int) else coolkid.base_speed * 0.85
    coolkid.speed = coolkid.base_speed

# Add missing attributes to coolkid
coolkid.helpless_until = 0.0
coolkid.subspace_until = 0.0
coolkid.speed_boost_until = 0.0

# Survivors already spawned with random positions!
# Display survivor team composition
print(f"\nSURVIVOR TEAM ASSEMBLED!")
for i, survivor in enumerate(survivors):
    print(f"  {i+1}. {survivor.survivor_type} - HP: {survivor.hp}, Speed: {survivor.base_speed}")
print(f"\nFacing: {selected_killer}\n")

# Round intro (3s) showing killer face and text
intro_until = time.time() + 3.0
while time.time() < intro_until:
    win.fill(SKY)
    # killer face preview center
    face_rect = pygame.Rect(WIDTH//2 - 60, HEIGHT//2 - 100, 120, 160)
    if selected_killer == '1x1x1x1':
        # Black body
        pygame.draw.rect(win, (30,30,30), face_rect)
        pygame.draw.rect(win, (0,0,0), face_rect, 3)

        # Green hat
        hat_rect = pygame.Rect(face_rect.left - 10, face_rect.top - 20, face_rect.width + 20, 25)
        pygame.draw.rect(win, (0,180,0), hat_rect)
        pygame.draw.rect(win, (0,120,0), hat_rect, 2)

        # BIGGER Dominos on TOP of hat (left-middle-right)
        domino_positions = [face_rect.left + 25, face_rect.centerx - 8, face_rect.right - 41]  # left, middle, right
        for i, domino_x in enumerate(domino_positions):
            domino_y = face_rect.top - 25  # ON TOP of hat
            pygame.draw.rect(win, (20,20,20), (domino_x, domino_y, 16, 20))  # MUCH BIGGER
            pygame.draw.rect(win, (255,255,255), (domino_x, domino_y, 16, 20), 1)
            # domino dots (bigger)
            pygame.draw.circle(win, (255,255,255), (domino_x + 8, domino_y + 5), 2)
            pygame.draw.circle(win, (255,255,255), (domino_x + 8, domino_y + 15), 2)

        # BIGGER Asymmetric red cross (left side only)
        eye_x = face_rect.left + 35  # left side of face
        eye_y = face_rect.top + 55
        pygame.draw.line(win, (220,0,0), (eye_x-12, eye_y), (eye_x+12, eye_y), 6)  # much bigger horizontal
        pygame.draw.line(win, (220,0,0), (eye_x, eye_y-12), (eye_x, eye_y+12), 6)  # much bigger vertical

        title = PRESS_FONT.render("This round's killer is 1x1x1x", True, (0,220,100))
    else:
        pygame.draw.rect(win, RED, face_rect)
        pygame.draw.rect(win, (120,0,0), face_rect, 3)
        pygame.draw.circle(win, BLACK, (face_rect.left+38, face_rect.top+55), 10)
        pygame.draw.circle(win, BLACK, (face_rect.right-38, face_rect.top+55), 10)
        title = PRESS_FONT.render("This round's killer is CoolKid", True, (255,180,180))
    win.blit(title, (WIDTH//2 - title.get_width()//2, face_rect.bottom + 16))
    pygame.display.update()
    clock.tick(60)

# === Audio: CoolKid sounds & music ===
coolkid_snd_dir = os.path.join("cabbage", "assets", "sounds", "coolkid")
def load_snd(name):
    try:
        path = os.path.join(coolkid_snd_dir, name)
        if os.path.exists(path):
            return pygame.mixer.Sound(path)
    except Exception:
        return None
    return None

snd_slash = load_snd("slash.ogg")
snd_dash = load_snd("dash_start.ogg")
snd_explosion = load_snd("dash_hit_explosion.ogg")
snd_clone = load_snd("clone_spawn.ogg")
snd_punch = load_snd("punch.ogg")

def play(snd, vol=1.0):
    try:
        if snd:
            snd.set_volume(vol)
            snd.play()
    except Exception:
        pass

# Start BGM if CoolKid
if selected_killer == "CoolKid":
    try:
        bgm_path = os.path.join(coolkid_snd_dir, "theme_ready_or_not.mp3")
        if os.path.exists(bgm_path) and pygame.mixer.get_init():
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.set_volume(0.6)
            pygame.mixer.music.play(-1)
    except Exception:
        pass

start_time = time.time()
# time bonus (seconds) gained from generators
bonus_time = 0

# main loop
running = True
camera_x = 0

# for ability durations we use timers via 'active_until' values:
noob_speed_until = 0.0
noob_invis_until = 0.0
coolkid_dash_until = 0.0
noob_reduce_until = 0.0
# NEW: Special effect timers
time_slow_until = 0.0

# fx timers/flags
noob_explosion_until = 0.0
confetti = []  # list of particles: {x,y,vx,vy,color,life}
# Projectiles for 1x1x1x1
projectiles = []  # each: {x,y,vx,vy,ttl,kind}
# Portals between floors (pairs). Each is a dict: rect and target (x,y)
# All portals now aligned vertically - CORRECTED for equal 400px gaps between all floors
portals = [
    # Floor 1 to Floor 2 portals (Floor1=650, Floor2=250, gap=400px)
    {"rect": pygame.Rect(40, HEIGHT-110, 40, 60),  "to": (2920, 250)},  # Floor1 left -> Floor2 right
    {"rect": pygame.Rect(2920, HEIGHT-110, 40, 60), "to": (40, 250)},   # Floor1 right -> Floor2 left
    {"rect": pygame.Rect(1480, HEIGHT-110, 40, 60), "to": (1480, 250)}, # Floor1 center -> Floor2 center

    # Floor 2 to Floor 3 portals (Floor2=250, Floor3=-150, gap=400px) - NOW PROPER GAP
    {"rect": pygame.Rect(40, 190, 40, 60),          "to": (2920, -150)},  # Floor2 left -> Floor3 right
    {"rect": pygame.Rect(2920, 190, 40, 60),        "to": (40, -150)},    # Floor2 right -> Floor3 left
    {"rect": pygame.Rect(1480, 190, 40, 60),        "to": (1480, -150)},  # Floor2 center -> Floor3 center

    # Floor 3 to Floor 1 portals (quick descent)
    {"rect": pygame.Rect(40, -210, 40, 60),          "to": (40, HEIGHT-50)},   # Floor3 left -> Floor1 left
    {"rect": pygame.Rect(2920, -210, 40, 60),        "to": (2920, HEIGHT-50)}, # Floor3 right -> Floor1 right
    {"rect": pygame.Rect(1480, -210, 40, 60),        "to": (1480, HEIGHT-50)}, # Floor3 center -> Floor1 center
]
# Cute houses placed on floors: (x,y,w,h) - CORRECTED for equal 400px gaps
houses = [
    # Floor 1 (ground) - houses sit on y=650 floor
    (500, HEIGHT-120, 120, 70), (1300, HEIGHT-120, 120, 70), (2200, HEIGHT-120, 120, 70),
    # Floor 2 (middle) - houses sit on y=250 floor - CORRECTED
    (800, 180, 120, 70), (1900, 180, 120, 70),
    # Floor 3 (top) - houses sit on y=-150 floor
    (600, -220, 120, 70), (1700, -220, 120, 70)
]
# 1x1x1x1 arrow ping state
arrow_hint_until = 0.0
# portal cooldowns to prevent instant re-trigger
noob_portal_cd_until = 0.0
coolkid_portal_cd_until = 0.0

# Generators: 5 brown boxes with green slider
class Generator:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 50, 40)
        self.progress = 0.0
        self.done = False
        self.active = False
        self.sequence = []  # list of pygame key constants
        self.index = 0
    def start_puzzle(self):
        if self.done:
            return
        import random as _r
        keys_pool = [pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_w, pygame.K_q, pygame.K_e]
        self.sequence = [_r.choice(keys_pool) for _ in range(3)]
        self.index = 0
        self.active = True
    def input_key(self, key):
        if not self.active or self.done:
            return False
        expected = self.sequence[self.index]
        if key == expected:
            self.index += 1
            if self.index >= len(self.sequence):
                self.done = True
                self.active = False
            return True
        else:
            # reset on wrong input
            self.index = 0
            return False
    def draw(self, cam_x, cam_y=0):
        # base box
        pygame.draw.rect(win, (150,75,0), (self.rect.x - cam_x, self.rect.y - cam_y, self.rect.w, self.rect.h))
        pygame.draw.rect(win, (80,40,0), (self.rect.x - cam_x, self.rect.y - cam_y, self.rect.w, self.rect.h), 2)
        # slider/progress bar (kept as visual aid for completion status)
        bar_x, bar_y, bar_w, bar_h = self.rect.x - cam_x + 6, self.rect.y - cam_y + 12, self.rect.w - 12, 12
        pygame.draw.rect(win, (40,40,40), (bar_x, bar_y, bar_w, bar_h))
        fill = 1.0 if self.done else (self.index / max(1,len(self.sequence)) if self.active else 0.0)
        fill_w = int(bar_w * fill)
        pygame.draw.rect(win, (0,200,60), (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(win, WHITE, (bar_x, bar_y, bar_w, bar_h), 2)
        # sequence text
        if self.active and not self.done:
            labels = {pygame.K_a:'A', pygame.K_s:'S', pygame.K_d:'D', pygame.K_w:'W', pygame.K_q:'Q', pygame.K_e:'E'}
            txt = ' '.join(labels[k] for k in self.sequence)
            col = WHITE
            surf = FONT.render(txt, True, col)
            win.blit(surf, (self.rect.x - cam_x - 10, self.rect.y - cam_y - 24))
        elif self.done:
            surf = FONT.render('OK', True, (0,220,80))
            win.blit(surf, (self.rect.x - cam_x + 10, self.rect.y - cam_y - 24))

# Create generators randomly distributed across all floors
def create_random_generators():
    generators = []
    # Define floor positions and their generator y positions - CORRECTED
    floor_data = [
        (HEIGHT-90, "Floor 1"),  # Floor 1: ground level generators
        (210, "Floor 2"),        # Floor 2: middle level generators - CORRECTED for y=250 floor
        (-190, "Floor 3")        # Floor 3: top level generators
    ]

    # Generate exactly 5 generators spread across all floors
    import random as gen_random
    gen_random.seed()  # Use current time for randomness

    for i in range(5):
        # Random x position (avoid portal areas and edges)
        x = gen_random.randint(200, 2800)
        # Ensure generators don't overlap with portal x positions
        while abs(x - 40) < 100 or abs(x - 1480) < 100 or abs(x - 2920) < 100:
            x = gen_random.randint(200, 2800)

        # Random floor selection
        floor_y, floor_name = gen_random.choice(floor_data)
        generators.append(Generator(x, floor_y))

    return generators

# instantiate generators with random distribution
generators = create_random_generators()
# Snap generators to nearest platform top under their x-span
for gen in generators:
    gx_center = gen.rect.centerx
    # find candidate platforms aligned horizontally
    candidates = [p for p in platforms if p.left <= gx_center <= p.right]
    if candidates:
        # choose the highest platform (smallest top) that is below current y
        under = [p for p in candidates if p.top >= 0]
        if under:
            target = min(under, key=lambda p: p.top)
            gen.rect.y = target.top - gen.rect.height

# active generator reference
active_generator = None

while running:
    dt = clock.tick(60) / 1000.0
    now = time.time()
    keys = pygame.key.get_pressed()

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if ev.type == pygame.KEYDOWN:
            # generator puzzle input
            if active_generator and not active_generator.done:
                before = active_generator.index
                progressed = active_generator.input_key(ev.key)
                if active_generator.done and progressed:
                    bonus_time += 10
                    active_generator = None
            # begin puzzle when pressing G near a generator
            if ev.key == pygame.K_g:
                for gen in generators:
                    if gen.done:
                        continue
                    if noob.rect().inflate(30,20).colliderect(gen.rect):
                        gen.start_puzzle()
                        active_generator = gen
                        break
            # CoolKid clones on keydown to improve reliability
            if selected_killer == "CoolKid" and ev.key == pygame.K_m and now > cooldowns["coolkid_clone"]:
                if len(clones) < 3:
                    # spawn one clone per press; alternate sides
                    off = 50 if (len(clones) % 2 == 0) else -50
                    c = Player(coolkid.x + off, coolkid.y, is_noob=False)
                    c.is_clone = True
                    c.base_speed = coolkid.base_speed / 3.0
                    c.speed = c.base_speed
                    clones.append({"p": c, "spawn": now})
                    play(snd_clone, 0.9)
                cooldowns["coolkid_clone"] = now + 10.0
            # CoolKid slash on keydown (comma)
            if selected_killer == "CoolKid" and ev.key == pygame.K_COMMA and now > cooldowns["coolkid_slash"]:
                sx = coolkid.x + coolkid.w // 2
                sy = coolkid.y + coolkid.h // 2
                length = 160
                if getattr(coolkid, 'facing_dir', 1) >= 0:
                    coolkid.slash_line = ((sx, sy), (sx + length, sy))
                else:
                    coolkid.slash_line = ((sx, sy), (sx - length, sy))
                coolkid.slash_spawn_time = now
                coolkid.slash_end_time = now + 0.6
                coolkid.has_hit = False
                cooldowns["coolkid_slash"] = now + 1.0
                play(snd_slash, 0.8)
            # 1x1x1x1 M: arrow ping towards Noob
            if selected_killer == "1x1x1x1" and ev.key == pygame.K_m and now > cooldowns["one_arrow"]:
                arrow_hint_until = now + 15.0
                cooldowns["one_arrow"] = now + 40.0

    # ------- input & abilities -------
    # Only main character is player controlled
    if main_character and main_character.hp > 0:
        main_character.move_input(keys, pygame.K_a, pygame.K_d, pygame.K_w, barriers)

    # NPC AI behavior - make NPCs avoid the killer and move around smoothly
    MAP_WIDTH = 3000
    for npc in npcs:
        if npc.hp > 0 and time.time() >= npc.stun_until:  # Only move if not stunned
            # Initialize AI state if not set
            if not hasattr(npc, 'ai_decision_until'):
                npc.ai_decision_until = 0.0
                npc.ai_move_direction = 0
                npc.ai_last_jump_time = 0.0
            
            now_time = time.time()
            
            # Make new decision every 0.5-1.5 seconds (smooth, not jittery)
            if now_time >= npc.ai_decision_until:
                killer_distance = abs(npc.x - coolkid.x)
                main_char_distance = abs(npc.x - main_character.x) if main_character else 9999
                
                # Priority 1: Run away from killer if too close
                if killer_distance < 200:
                    if coolkid.x < npc.x:
                        npc.ai_move_direction = 1  # Move right
                        npc.facing_dir = 1
                    else:
                        npc.ai_move_direction = -1  # Move left
                        npc.facing_dir = -1
                    # Commit to this direction for 0.4-0.8 seconds
                    npc.ai_decision_until = now_time + random.uniform(0.4, 0.8)
                # Priority 2: Follow main character if far away
                elif main_char_distance > 300 and main_character:
                    if main_character.x < npc.x:
                        npc.ai_move_direction = -1  # Move left
                        npc.facing_dir = -1
                    else:
                        npc.ai_move_direction = 1  # Move right
                        npc.facing_dir = 1
                    # Commit to this direction for 0.5-1.0 seconds
                    npc.ai_decision_until = now_time + random.uniform(0.5, 1.0)
                # Priority 3: Wander slowly
                else:
                    # Random direction change
                    if random.random() < 0.3:  # 30% chance to change direction
                        npc.ai_move_direction = random.choice([-1, 0, 1])
                    # Commit to this direction for 1.0-2.0 seconds (longer for wandering)
                    npc.ai_decision_until = now_time + random.uniform(1.0, 2.0)
            
            # Apply movement based on current AI decision
            if npc.ai_move_direction != 0:
                old_x = npc.x
                move_speed = npc.speed
                # Use full speed when fleeing, slower when following/wandering
                if abs(npc.x - coolkid.x) < 200:
                    move_speed = npc.speed  # Full speed when fleeing
                else:
                    move_speed = npc.speed * 0.6  # Slower when wandering/following
                
                move_delta = npc.ai_move_direction * move_speed
                
                # Check map boundaries
                new_x = old_x + move_delta
                if new_x < 0:
                    new_x = 0
                    npc.ai_move_direction = 0  # Stop if hit boundary
                    npc.ai_decision_until = now_time + 0.3  # Quick decision to change direction
                elif new_x + npc.w > MAP_WIDTH:
                    new_x = MAP_WIDTH - npc.w
                    npc.ai_move_direction = 0  # Stop if hit boundary
                    npc.ai_decision_until = now_time + 0.3  # Quick decision to change direction
                
                # Check for collision with barriers
                can_move = True
                for barrier in barriers:
                    if move_delta < 0 and (new_x) <= (barrier.x + barrier.w) and (new_x + npc.w) > barrier.x and (npc.y + npc.h) > barrier.y and npc.y < (barrier.y + barrier.h):
                        can_move = False
                        break
                    elif move_delta > 0 and (new_x + npc.w) >= barrier.x and new_x < (barrier.x + barrier.w) and (npc.y + npc.h) > barrier.y and npc.y < (barrier.y + barrier.h):
                        can_move = False
                        break
                
                if can_move:
                    npc.x = new_x
                    npc.last_move_time = time.time()
                else:
                    # Hit a barrier, change direction quickly
                    npc.ai_move_direction = 0
                    npc.ai_decision_until = now_time + 0.2
            
            # Very rare jumping - only when truly needed (avoid obstacles or jump over gaps)
            # Jump much less frequently (only every 5-10 seconds, and only if on ground for a while)
            if (npc.on_ground and 
                now_time - npc.ai_last_jump_time > 5.0 and  # At least 5 seconds between jumps
                random.random() < 0.001):  # Very low chance (0.1% per frame, ~0.06 per second)
                npc.vel_y = -15
                npc.on_ground = False
                npc.ai_last_jump_time = now_time

    # CoolKid controls: arrows ; / is K_SLASH, comma is K_COMMA, m spawn clone
    coolkid.move_input(keys, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, barriers)

    # Determine move directions for camera logic (-1 left, 1 right, 0 idle)
    noob_move_dir = (-1 if keys[pygame.K_a] else 0) + (1 if keys[pygame.K_d] else 0)
    coolkid_move_dir = (-1 if keys[pygame.K_LEFT] else 0) + (1 if keys[pygame.K_RIGHT] else 0)

    # Main character abilities - Z, X, C, V keys based on survivor type
    if main_character and main_character.hp > 0:
        survivor = main_character
        survivor_type = getattr(survivor, 'survivor_type', 'Noob')
        survivor_id = id(survivor)

        # 007n7 abilities: Clone (Z), c00lgui (X), Inject (C)
        if survivor_type == "007n7":
            if keys[pygame.K_z] and now > cooldowns.get(f"clone_{survivor_id}", 0):
                # Clone: Create a clone that lives for 10 seconds
                clone = Player(survivor.x + 50, survivor.y, is_noob=True)
                clone.survivor_type = "007n7"
                clone.type_data = SURVIVOR_TYPES["007n7"]
                clone.base_speed = clone.type_data["speed"]
                clone.speed = clone.base_speed
                clone.hp = 50  # Clone has less HP
                clone.max_hp = 50
                clone.invisible = True
                clone.special_effect_until = now + 4.0  # Invisible for 4 seconds
                clone.clone_until = now + 10.0  # Clone lives for 10 seconds
                survivors.append(clone)
                cooldowns[f"clone_{survivor_id}"] = now + 15.0

            if keys[pygame.K_x] and now > cooldowns.get(f"c00lgui_{survivor_id}", 0):
                # c00lgui: After being idle for 6 seconds, teleport to the furthest survivor spawn
                if now - survivor.last_move_time > 6.0:  # Check if idle for 6 seconds
                    # Find furthest survivor spawn
                    furthest_spawn = max(SURVIVOR_SPAWNS, key=lambda spawn: abs(spawn[0] - survivor.x))
                    survivor.x, survivor.y = furthest_spawn
                    cooldowns[f"c00lgui_{survivor_id}"] = now + 20.0

            if keys[pygame.K_c] and now > cooldowns.get(f"inject_{survivor_id}", 0):
                # Inject: Changes the clone's movement type
                for clone_info in clones:
                    if clone_info["p"].survivor_type == "007n7":
                        # Random movement type: 0=aimless, 1=pathfinding, 2=cursor
                        clone_info["p"].movement_type = random.randint(0, 2)
                cooldowns[f"inject_{survivor_id}"] = now + 10.0

        # Shedletsky abilities: Slash (Z), Fried Chicken (X)
        elif survivor_type == "Shedletsky":
            if keys[pygame.K_z] and now > cooldowns.get(f"slash_{survivor_id}", 0):
                # Slash: Deal 30 damage and stun the killer for 3 seconds while gaining resistance for 0.575
                if coolkid.rect().colliderect(survivor.rect()):
                    coolkid.hp -= 30
                    coolkid.stun_until = now + 3.0
                    survivor.shield_active = True
                    survivor.special_effect_until = now + 0.575
                cooldowns[f"slash_{survivor_id}"] = now + 8.0

            if keys[pygame.K_x] and now > cooldowns.get(f"fried_chicken_{survivor_id}", 0):
                # Fried Chicken: Restores 35 HP in 10 seconds (2 charges)
                if survivor.fried_chicken_charges > 0:
                    survivor.hp = min(survivor.max_hp, survivor.hp + 35)
                    survivor.fried_chicken_charges -= 1
                    cooldowns[f"fried_chicken_{survivor_id}"] = now + 15.0

        # Guest 1337 abilities: Block (Z), Charge (X), Punch (C)
        elif survivor_type == "Guest 1337":
            if keys[pygame.K_z] and now > cooldowns.get(f"block_{survivor_id}", 0):
                # Block: Gain resistance for 1 second, then speed boost for 3 seconds
                survivor.shield_active = True
                survivor.special_effect_until = now + 1.0
                survivor.speed_boost_until = now + 4.0  # Speed boost after shield
                cooldowns[f"block_{survivor_id}"] = now + 12.0

            if keys[pygame.K_x] and now > cooldowns.get(f"charge_{survivor_id}", 0):
                # Charge: Dash forward for 1.5 seconds, and if the killer is hit, their abilities are locked for 1.25 seconds
                survivor.dash_active = True
                survivor.dash_end = now + 1.5
                survivor.dash_direction = survivor.facing_dir
                cooldowns[f"charge_{survivor_id}"] = now + 10.0

            if keys[pygame.K_c] and now > cooldowns.get(f"punch_{survivor_id}", 0):
                # Punch: Channel a fist for 0.8 seconds and stun a killer for 2 seconds
                survivor.punch_channeling = True
                survivor.punch_channel_end = now + 0.8
                cooldowns[f"punch_{survivor_id}"] = now + 15.0

        # Two Time abilities: Sacrificial Dagger (Z), Crouch (X), Ritual (C)
        elif survivor_type == "Two Time":
            if keys[pygame.K_z] and now > cooldowns.get(f"dagger_{survivor_id}", 0):
                # Sacrificial Dagger: Gain resistance for 0.7 seconds, and if the dagger hits the killer, it deals 25 damage
                survivor.shield_active = True
                survivor.special_effect_until = now + 0.7
                survivor.dagger_active = True
                survivor.dagger_end = now + 0.7
                cooldowns[f"dagger_{survivor_id}"] = now + 8.0

            if keys[pygame.K_x] and now > cooldowns.get(f"crouch_{survivor_id}", 0):
                # Crouch: Perform crouch, but slower movement speed
                survivor.crouching = True
                survivor.speed = survivor.base_speed * 0.5
                cooldowns[f"crouch_{survivor_id}"] = now + 5.0

            if keys[pygame.K_c] and now > cooldowns.get(f"ritual_{survivor_id}", 0):
                # Ritual: Carve a mark on the ground that acts as the respawn beacon
                survivor.respawn_beacon = (survivor.x, survivor.y)
                cooldowns[f"ritual_{survivor_id}"] = now + 30.0

        # Chance Forsaken abilities: Coil Flip (Z), One Shot (X), Reroll (C), Hat Fix (V)
        elif survivor_type == "Chance Forsaken":
            if keys[pygame.K_z] and now > cooldowns.get(f"coin_flip_{survivor_id}", 0):
                # Coil Flip: Flip the coin. If it lands on heads, gain one charge for all abilities, and if it lands on tails, gain a stack of weakness
                if random.random() < 0.5:  # Heads
                    # Gain one charge for all abilities (reduce cooldowns)
                    for key in cooldowns:
                        if key.startswith(f"{survivor_id}"):
                            cooldowns[key] = max(0, cooldowns[key] - 5.0)
                else:  # Tails
                    # Gain a stack of weakness
                    survivor.weakness_stacks = getattr(survivor, 'weakness_stacks', 0) + 1
                    survivor.weakness_until = now + 10.0
                cooldowns[f"coin_flip_{survivor_id}"] = now + 8.0

            if keys[pygame.K_x] and now > cooldowns.get(f"one_shot_{survivor_id}", 0):
                # One Shot: Unreliable flintlock with 3 outcomes
                outcome = random.randint(1, 3)
                if outcome == 1:  # Explode and deal 45 damage
                    if coolkid.rect().colliderect(survivor.rect()):
                        coolkid.hp -= 45
                    cooldowns[f"one_shot_{survivor_id}"] = now + 60.0  # Disable ability
                elif outcome == 2:  # Fail to fire
                    cooldowns[f"one_shot_{survivor_id}"] = now + 20.0  # Force wait
                else:  # Successfully shoot and stun
                    distance = abs(coolkid.x - survivor.x)
                    stun_duration = max(1, min(4, 4 - distance // 90))
                    coolkid.stun_until = now + stun_duration
                    cooldowns[f"one_shot_{survivor_id}"] = now + 15.0

            if keys[pygame.K_c] and now > cooldowns.get(f"reroll_{survivor_id}", 0):
                # Reroll: Reroll the value of your max health
                new_max_hp = random.randint(70, 90)
                survivor.max_hp = new_max_hp
                survivor.hp = new_max_hp
                cooldowns[f"reroll_{survivor_id}"] = now + 25.0

            if keys[pygame.K_v] and now > cooldowns.get(f"hat_fix_{survivor_id}", 0):
                # Hat Fix: Revert all weakness stacks to a single weakness debuff
                survivor.weakness_stacks = 1
                survivor.weakness_until = now + 10.0
                cooldowns[f"hat_fix_{survivor_id}"] = now + 20.0

        # Elliot abilities: Pizza Throw (Z), Rush Hour (X)
        elif survivor_type == "Elliot":
            if keys[pygame.K_z] and now > cooldowns.get(f"pizza_throw_{survivor_id}", 0):
                # Pizza Throw: Throw a pizza to heal survivors for 35 HP
                for other_survivor in survivors:
                    if other_survivor != survivor and other_survivor.hp > 0:
                        distance = abs(other_survivor.x - survivor.x)
                        if distance < 100:  # Within range
                            other_survivor.hp = min(other_survivor.max_hp, other_survivor.hp + 35)
                cooldowns[f"pizza_throw_{survivor_id}"] = now + 12.0

            if keys[pygame.K_x] and now > cooldowns.get(f"rush_hour_{survivor_id}", 0):
                # Rush Hour: Grants a speed boost for 3 seconds
                survivor.speed_boost_until = now + 3.0
                survivor.speed = survivor.base_speed * 1.5
                cooldowns[f"rush_hour_{survivor_id}"] = now + 15.0

        # Dusekkar abilities: Spawn Protection (Z), Plasma Beam (X)
        elif survivor_type == "Dusekkar":
            if keys[pygame.K_z] and now > cooldowns.get(f"spawn_protection_{survivor_id}", 0):
                # Spawn Protection: Give an ally a shield for 3.5 seconds
                for other_survivor in survivors:
                    if other_survivor != survivor and other_survivor.hp > 0:
                        other_survivor.shield_active = True
                        other_survivor.special_effect_until = now + 3.5
                        break
                cooldowns[f"spawn_protection_{survivor_id}"] = now + 20.0

            if keys[pygame.K_x] and now > cooldowns.get(f"plasma_beam_{survivor_id}", 0):
                # Plasma Beam: Cast a beam that slows killers for 3 seconds or gives a speed boost to survivors for 4 seconds
                if random.random() < 0.5:  # Slow killer
                    coolkid.speed_boost_until = now + 3.0
                    coolkid.speed = coolkid.base_speed * 0.5
                else:  # Speed boost survivors
                    for other_survivor in survivors:
                        other_survivor.speed_boost_until = now + 4.0
                        other_survivor.speed = other_survivor.base_speed * 1.5
                cooldowns[f"plasma_beam_{survivor_id}"] = now + 18.0

        # Builderman abilities: Sentry Construction (Z), Dispenser Construction (X)
        elif survivor_type == "Builderman":
            if keys[pygame.K_z] and now > cooldowns.get(f"sentry_{survivor_id}", 0):
                # Sentry Construction: Receive weakness for 2 seconds before crafting a Sentry
                survivor.weakness_until = now + 2.0
                survivor.weakness_stacks = 1
                # Create sentry after 2 seconds
                survivor.sentry_construction_end = now + 2.0
                cooldowns[f"sentry_{survivor_id}"] = now + 25.0

            if keys[pygame.K_x] and now > cooldowns.get(f"dispenser_{survivor_id}", 0):
                # Dispenser Construction: Receive weakness for 2 seconds before crafting a Dispenser
                survivor.weakness_until = now + 2.0
                survivor.weakness_stacks = 1
                # Create dispenser after 2 seconds
                survivor.dispenser_construction_end = now + 2.0
                cooldowns[f"dispenser_{survivor_id}"] = now + 20.0

        # Taph abilities: Tripwire (Z), Subspace Tripmine (X)
        elif survivor_type == "Taph":
            if keys[pygame.K_z] and now > cooldowns.get(f"tripwire_{survivor_id}", 0):
                # Tripwire: Place a tripwire that weakens the killer and alerts survivors about their location
                survivor.tripwire_active = True
                survivor.tripwire_end = now + 15.0
                survivor.tripwire_location = (survivor.x, survivor.y)
                cooldowns[f"tripwire_{survivor_id}"] = now + 12.0

            if keys[pygame.K_x] and now > cooldowns.get(f"subspace_{survivor_id}", 0):
                # Subspace Tripmine: Killer gets helpless and subspaced buffs for 5 seconds
                coolkid.helpless_until = now + 5.0
                coolkid.subspace_until = now + 5.0
                cooldowns[f"subspace_{survivor_id}"] = now + 30.0

    # NEW: Survivor Special Abilities (T key) - Only for main character
    if keys[pygame.K_t] and main_character and main_character.hp > 0:
        survivor = main_character
        survivor_type = getattr(survivor, 'survivor_type', 'Noob')
        survivor_id = id(survivor)

        if survivor_type == "Noob":
            # Noob abilities: Q, E, R (handled separately)
            pass
        elif survivor_type == "007n7" and now > cooldowns.get(f"clone_{survivor_id}", 0):
            # Clone: Create a clone that lives for 10 seconds
            clone = Player(survivor.x + 50, survivor.y, is_noob=True)
            clone.survivor_type = "007n7"
            clone.type_data = SURVIVOR_TYPES["007n7"]
            clone.base_speed = clone.type_data["speed"]
            clone.speed = clone.base_speed
            clone.hp = 50  # Clone has less HP
            clone.max_hp = 50
            clone.invisible = True
            clone.special_effect_until = now + 4.0  # Invisible for 4 seconds
            clone.clone_until = now + 10.0  # Clone lives for 10 seconds
            survivors.append(clone)
            cooldowns[f"clone_{survivor_id}"] = now + 15.0
        elif survivor_type == "Shedletsky" and now > cooldowns.get(f"slash_{survivor_id}", 0):
            # Slash: Deal 30 damage and stun the killer for 3 seconds
            if coolkid.rect().colliderect(survivor.rect()):
                coolkid.hp -= 30
                coolkid.stun_until = now + 3.0
            cooldowns[f"slash_{survivor_id}"] = now + 8.0
        elif survivor_type == "Guest 1337" and now > cooldowns.get(f"block_{survivor_id}", 0):
            # Block: Gain resistance for 1 second, then speed boost for 3 seconds
            survivor.shield_active = True
            survivor.special_effect_until = now + 1.0
            survivor.speed_boost_until = now + 4.0  # Speed boost after shield
            cooldowns[f"block_{survivor_id}"] = now + 12.0
        elif survivor_type == "Two Time" and now > cooldowns.get(f"sacrificial_dagger_{survivor_id}", 0):
            # Sacrificial Dagger: Gain resistance for 0.7 seconds, deal 25 damage if hit
            survivor.shield_active = True
            survivor.special_effect_until = now + 0.7
            survivor.dagger_active = True
            cooldowns[f"sacrificial_dagger_{survivor_id}"] = now + 10.0
        elif survivor_type == "Chance Forsaken" and now > cooldowns.get(f"coil_flip_{survivor_id}", 0):
            # Coil Flip: 50% chance to gain ability charges or weakness
            if random.random() < 0.5:
                # Heads: gain ability charges (heal)
                survivor.hp = min(survivor.max_hp, survivor.hp + 20)
            else:
                # Tails: weakness (slower speed)
                survivor.speed = survivor.base_speed * 0.7
                survivor.weakness_until = now + 5.0
            cooldowns[f"coil_flip_{survivor_id}"] = now + 8.0
        elif survivor_type == "Elliot" and now > cooldowns.get(f"pizza_throw_{survivor_id}", 0):
            # Pizza Throw: Heal all survivors for 35 HP
            for s in survivors:
                s.hp = min(s.max_hp, s.hp + 35)
            cooldowns[f"pizza_throw_{survivor_id}"] = now + 15.0
        elif survivor_type == "Dusekkar" and now > cooldowns.get(f"spawn_protection_{survivor_id}", 0):
            # Spawn Protection: Give an ally a shield for 3.5 seconds
            for s in survivors:
                if s != survivor and s.hp > 0:
                    s.shield_active = True
                    s.special_effect_until = now + 3.5
                    break
            cooldowns[f"spawn_protection_{survivor_id}"] = now + 20.0
        elif survivor_type == "Builderman" and now > cooldowns.get(f"sentry_construction_{survivor_id}", 0):
            # Sentry Construction: Create a sentry that deals damage
            # Simplified: just deal damage to killer if nearby
            if coolkid.rect().colliderect(pygame.Rect(survivor.x - 100, survivor.y - 100, 200, 200)):
                coolkid.hp -= 10
            cooldowns[f"sentry_construction_{survivor_id}"] = now + 25.0
        elif survivor_type == "Taph" and now > cooldowns.get(f"tripwire_{survivor_id}", 0):
            # Tripwire: Place a tripwire that weakens the killer
            # Simplified: weaken killer if they're nearby
            if coolkid.rect().colliderect(pygame.Rect(survivor.x - 50, survivor.y - 50, 100, 100)):
                coolkid.speed = coolkid.base_speed * 0.5
                coolkid.weakness_until = now + 3.0
            cooldowns[f"tripwire_{survivor_id}"] = now + 12.0

    # CoolKid dash (duration 4s, cd 40s) bound to slash key (/)
    if keys[pygame.K_SLASH] and now > cooldowns["coolkid_dash"] and selected_killer == "CoolKid":
        coolkid_dash_until = now + 4.0
        cooldowns["coolkid_dash"] = now + 40.0
        coolkid.dash_active = True
        coolkid.dash_end = coolkid_dash_until
        coolkid.speed = coolkid.base_speed * 5
        coolkid.dash_has_hit = False
        play(snd_dash, 0.9)

    # 1x1x1x1 abilities
    if selected_killer == "1x1x1x1":
        # comma: little flying sword that stuns Noob (no damage)
        if keys[pygame.K_COMMA] and now > cooldowns["one_stun"]:
            sx = coolkid.x + coolkid.w//2
            sy = coolkid.y + coolkid.h//3
            dirx = 1 if getattr(coolkid,'facing_dir',1) >= 0 else -1
            projectiles.append({
                "kind":"stun_blade",
                "x": sx,
                "y": sy,
                "vx": 12*dirx,
                "vy": 0,
                "ttl": now + 1.0,
                "len": 60,
                "wid": 12,
                "angle": 0.0,
                "spin": 12.0 * dirx,
                "trail": []
            })
            cooldowns["one_stun"] = now + 0.8
        # slash: period '.' melee slash like CoolKid
        if keys[pygame.K_PERIOD] and now > cooldowns["one_slash"]:
            sx = coolkid.x + coolkid.w // 2
            sy = coolkid.y + coolkid.h // 2
            length = 160
            if getattr(coolkid, 'facing_dir', 1) >= 0:
                coolkid.slash_line = ((sx, sy), (sx + length, sy))
            else:
                coolkid.slash_line = ((sx, sy), (sx - length, sy))
            coolkid.slash_spawn_time = now
            coolkid.slash_end_time = now + 0.6
            coolkid.has_hit = False
            cooldowns["one_slash"] = now + 1.0
        # mass infection: anime blade projectile on '/' key, uses coolkid_dash cooldown slot
        if keys[pygame.K_SLASH] and now > cooldowns["coolkid_dash"]:
            sx = coolkid.x + coolkid.w//2
            sy = coolkid.y + coolkid.h//2
            dirx = 1 if getattr(coolkid,'facing_dir',1) >= 0 else -1
            projectiles.append({
                "kind":"blade",
                "x": sx,
                "y": sy,
                "vx": 14*dirx,
                "vy": 0,
                "ttl": now + 1.2,
                "len": 90,
                "wid": 18,
                "angle": 0.0,
                "spin": 9.0 * dirx,
                "trail": []
            })
            cooldowns["coolkid_dash"] = now + 3.0
        # black sword slash (N key) short range
        if keys[pygame.K_n] and now > cooldowns["clone_slash"]:
            sx = coolkid.x + coolkid.w // 2
            sy = coolkid.y + coolkid.h // 2
            length = 140
            if getattr(coolkid, 'facing_dir', 1) >= 0:
                coolkid.slash_line = ((sx, sy), (sx + length, sy))
            else:
                coolkid.slash_line = ((sx, sy), (sx - length, sy))
            coolkid.slash_spawn_time = now
            coolkid.slash_end_time = now + 0.5
            coolkid.has_hit = False
            cooldowns["clone_slash"] = now + 1.0

    # Spawn clones (M) cd 10s, create up to 3 clones
    if selected_killer == "CoolKid" and keys[pygame.K_m] and now > cooldowns["coolkid_clone"]:
        # clear old clones if too many
        if len(clones) < 3:
            spawn_offsets = [50, -50, 100, -100]
            for off in spawn_offsets:
                if len(clones) >= 3:
                    break
                c = Player(coolkid.x + off, coolkid.y, is_noob=False)
                c.is_clone = True
                c.base_speed = coolkid.base_speed / 3.0
                c.speed = c.base_speed
                clones.append({"p": c, "spawn": now})
        cooldowns["coolkid_clone"] = now + 10.0

    # ------- durations expiry for ALL survivors -------
    if noob_speed_until and now >= noob_speed_until:
        for survivor in survivors:
            survivor.speed = survivor.base_speed
        noob_speed_until = 0.0
    if noob_invis_until and now >= noob_invis_until:
        for survivor in survivors:
            survivor.invisible = False
        noob_invis_until = 0.0
    # reset speed after R ends (but don't override active speed boost)
    if noob_reduce_until and now >= noob_reduce_until:
        noob_reduce_until = 0.0
        if not noob_speed_until or now >= noob_speed_until:
            for survivor in survivors:
                survivor.speed = survivor.base_speed
    if coolkid.dash_active and now >= coolkid.dash_end:
        coolkid.dash_active = False
        coolkid.speed = coolkid.base_speed
        coolkid.dash_has_hit = False

    # ------- physics -------
    # apply gravity and collisions to ALL survivors
    moving_entities = survivors + [coolkid] + [c["p"] for c in clones]
    for p in moving_entities:
        if p:
            # Apply time slow effect if active
            gravity_mult = 0.3 if now < time_slow_until else 1.0
            if hasattr(p, 'survivor_type') and getattr(p, 'survivor_type', '') == 'Speedster':
                gravity_mult = 1.0  # Speedster immune to time slow

            # Temporarily modify gravity
            old_gravity = GRAVITY
            globals()['GRAVITY'] = GRAVITY * gravity_mult
            p.apply_gravity()
            globals()['GRAVITY'] = old_gravity

            p.check_platforms(platforms)

            # Handle special effect expiry
            if hasattr(p, 'special_effect_until') and now >= p.special_effect_until:
                if hasattr(p, 'survivor_type'):
                    # Reset shield effects
                    if hasattr(p, 'shield_active'):
                        p.shield_active = False
                    # Reset invisibility for clones
                    if hasattr(p, 'clone_until') and p.clone_until and now >= p.clone_until:
                        # Remove clone from survivors list
                        if p in survivors:
                            survivors.remove(p)
                    elif hasattr(p, 'invisible') and getattr(p, 'survivor_type', '') == '007n7':
                        p.invisible = False
                    # Reset speed effects
                    if hasattr(p, 'speed_boost_until') and p.speed_boost_until and now >= p.speed_boost_until:
                        p.speed = p.base_speed
                    if hasattr(p, 'weakness_until') and p.weakness_until and now >= p.weakness_until:
                        p.speed = p.base_speed
    # Portal teleport (only way between floors) - Updated for multiple survivors
    def try_teleport(player, who):
        global noob_portal_cd_until, coolkid_portal_cd_until
        prect = player.rect()
        # respect per-player cooldown
        if who.startswith('survivor') and hasattr(player, 'portal_cd_until') and now < player.portal_cd_until:
            return
        if who == 'noob' and now < noob_portal_cd_until:
            return
        if who == 'coolkid' and now < coolkid_portal_cd_until:
            return
        for prt in portals:
            if prect.colliderect(prt["rect"]):
                tx, ty = prt["to"]
                # spawn BESIDE destination portal to avoid immediate re-trigger
                # decide offset direction based on destination x (left or right edge portals)
                if tx <= 200:
                    spawn_x = tx + 80  # to the right of the portal
                elif tx >= 2800:
                    spawn_x = tx - 80 - player.w  # to the left of the portal
                else:
                    spawn_x = tx + 80
                player.x = spawn_x
                player.y = ty - player.h  # stand on floor top
                player.vel_y = 0
                # set cooldown
                if who.startswith('survivor'):
                    player.portal_cd_until = now + 0.6
                elif who == 'noob':
                    noob_portal_cd_until = now + 0.6
                elif who == 'coolkid':
                    coolkid_portal_cd_until = now + 0.6
                break

    # Teleport all survivors
    for i, survivor in enumerate(survivors):
        try_teleport(survivor, f'survivor_{i}')
    try_teleport(coolkid, 'coolkid')
    for cinfo in clones:
        try_teleport(cinfo["p"], 'clone')

    # Update projectiles (1x1x1x1)
    if projectiles:
        kept_proj = []
        for pr in projectiles:
            # motion
            pr["x"] += pr.get("vx",0) * (1)
            pr["y"] += pr.get("vy",0) * (1)
            if pr["kind"] in ("blade","stun_blade"):
                pr["angle"] += pr.get("spin", 8.0) * (dt*60/60)
                pr["trail"].append((pr["x"], pr["y"]))
                if len(pr["trail"]) > 6:
                    pr["trail"].pop(0)
                # collision AABB approx
                half_l = pr.get("len", 80) * 0.5
                half_w = pr.get("wid", 16) * 0.5
                aabb = pygame.Rect(int(pr["x"] - half_l) - camera_x, int(pr["y"] - half_w), int(half_l*2), int(half_w*2))
                nr = noob.rect(); nr.x -= camera_x
                if aabb.colliderect(nr) and not noob.invisible:
                    if pr["kind"] == "stun_blade":
                        noob.stun_until = max(noob.stun_until, now + 5.0)
                    else:
                        dmg = 30
                        if noob_reduce_until and now < noob_reduce_until:
                            dmg = max(1, int(dmg * 0.1))
                        noob.hp -= dmg
                        noob.stun_until = max(noob.stun_until, now + 0.4)
                    continue
            elif pr["kind"] == "stun":
                pass
            # ttl bounds
            if now < pr["ttl"] and -200 <= pr["x"] <= 5000 and -200 <= pr["y"] <= HEIGHT+200:
                kept_proj.append(pr)
        projectiles = kept_proj

    # Generator puzzle visuals are handled in draw; logic handled on keydown

    # CoolKid falls out of map -> Noob wins
    if coolkid.y > HEIGHT + 200:
        winner = "Noob"
        game_over = True

    # ------- clone AI -------
    kept = []
    for cinfo in clones:
        c = cinfo["p"]
        # despawn after 15s
        if now - cinfo["spawn"] > 15.0:
            continue
        # horizontal chase (simple)
        if noob.x + noob.w/2 < c.x + c.w/2:
            c.x -= c.speed
        elif noob.x + noob.w/2 > c.x + c.w/2:
            c.x += c.speed
        # small vertical hop if target higher and on ground
        if noob.y + 10 < c.y and c.on_ground:
            c.vel_y = -18
            c.on_ground = False
        # auto-slash when in range and clone's own cooldown ready
        if abs((noob.x + noob.w/2) - (c.x + c.w/2)) < 80 and now > cooldowns["clone_slash"]:
            sx = c.x + c.w // 2
            sy = c.y + c.h // 2
            if noob.x + noob.w/2 >= c.x + c.w/2:
                c.slash_line = ((sx, sy), (sx + 80, sy))
            else:
                c.slash_line = ((sx, sy), (sx - 80, sy))
            c.slash_end_time = now + 0.3
            c.has_hit = False
            cooldowns["clone_slash"] = now + 1.0
        kept.append(cinfo)
    clones = kept

    # ------- slash lifecycle & hit detection -------
    attackers = [coolkid] + [c["p"] for c in clones]
    for attacker in attackers:
        if attacker.slash_line and now > getattr(attacker, "slash_end_time", 0):
            attacker.slash_line = None
            attacker.has_hit = False

        if attacker.slash_line and not noob.invisible:
            a0, a1 = attacker.slash_line
            minx = min(a0[0], a1[0])
            maxx = max(a0[0], a1[0])
            midy = a0[1]
            # simple collision: check noob center in horizontal range and vertical closeness
            noob_cx = noob.x + noob.w/2
            noob_cy = noob.y + noob.h/2
            if (minx <= noob_cx <= maxx) and abs(noob_cy - midy) < 40:
                if not attacker.has_hit:
                    dmg = 10
                    if noob_reduce_until and now < noob_reduce_until:
                        dmg = max(1, int(dmg * 0.1))
                    noob.hp -= dmg
                    noob.stun_until = now + 0.3
                    attacker.has_hit = True
                    # keep slash until timeout for visibility

    # ------- dash contact damage -------
    # if coolkid dashing and touches noob, deal damage once per dash activation
    if coolkid.dash_active:
        # Check collision with all survivors
        for survivor in survivors:
            if survivor.hp > 0 and coolkid.rect().colliderect(survivor.rect()) and not getattr(survivor, 'invisible', False):
                # stop dash immediately
                coolkid.dash_active = False
                coolkid.speed = coolkid.base_speed
                if not coolkid.dash_has_hit:
                    dmg = 40
                    # Tank shield reduces damage
                    if getattr(survivor, 'shield_active', False):
                        dmg = max(1, int(dmg * 0.2))  # 80% damage reduction
                    elif noob_reduce_until and now < noob_reduce_until:
                        dmg = max(1, int(dmg * 0.1))
                    survivor.hp -= dmg
                    survivor.stun_until = now + 0.3
                    coolkid.dash_has_hit = True
                    # explosion FX at survivor for 0.45s
                    noob_explosion_until = now + 0.45
                    play(snd_explosion, 1.0)
                    break

    # ------- camera follow with VERTICAL and horizontal movement -------
    # Split-screen: compute two camera positions with vertical following
    # Track main character for left camera
    if main_character and main_character.hp > 0:
        noob_center_x = main_character.x + main_character.w/2
        noob_center_y = main_character.y + main_character.h/2
    else:
        noob_center_x = WIDTH//4
        noob_center_y = HEIGHT//2
    cool_center_x = coolkid.x + coolkid.w/2
    cool_center_y = coolkid.y + coolkid.h/2

    render_w = WIDTH//2
    render_h = HEIGHT

    # Horizontal camera (same as before)
    MAP_WIDTH = 3000
    camera_left_x = int(noob_center_x - render_w//2)
    camera_right_x = int(cool_center_x - render_w//2)
    # Clamp horizontal camera to map bounds
    max_camera_x = MAP_WIDTH - render_w
    if camera_left_x < 0: camera_left_x = 0
    if camera_left_x > max_camera_x: camera_left_x = max_camera_x
    if camera_right_x < 0: camera_right_x = 0
    if camera_right_x > max_camera_x: camera_right_x = max_camera_x

    # NEW: Vertical camera following
    camera_left_y = int(noob_center_y - render_h//2)
    camera_right_y = int(cool_center_y - render_h//2)

    # Clamp vertical camera to reasonable bounds
    min_camera_y = -200  # can see above top floor
    max_camera_y = HEIGHT - 100  # don't go too far below ground
    camera_left_y = max(min_camera_y, min(max_camera_y, camera_left_y))
    camera_right_y = max(min_camera_y, min(max_camera_y, camera_right_y))

    # ------- draw (split screen) -------
    def draw_world(camera_x, camera_y=0):
        # background
        win.fill(SKY)
        pygame.draw.circle(win, (230,230,255), (int(140 - camera_x//6), int(90 - camera_y//8)), 28)
        pygame.draw.circle(win, SKY, (int(150 - camera_x//6), int(86 - camera_y//8)), 10)
        for sx, sy, sr in stars:
            pygame.draw.circle(win, (240, 240, 200), (int(sx - camera_x*0.2), int(sy - camera_y*0.1)), sr)
        # ground
        pygame.draw.rect(win, DARK_RED, (0 - camera_x, HEIGHT-60 - camera_y, 5000, 60))
        pygame.draw.rect(win, GOLD, (0 - camera_x, HEIGHT-60 - camera_y, 5000, 6))
        # background tents and market
        def draw_tent(base_x, scale):
            tent_base_y = HEIGHT - 80 - camera_y
            tent_w = int(240 * scale)
            tent_h = int(140 * scale)
            tx = int(base_x - camera_x*0.8)
            # tent body
            pygame.draw.polygon(win, RED, [(tx, tent_base_y), (tx+tent_w, tent_base_y), (tx+tent_w-24, tent_base_y - tent_h//2), (tx+24, tent_base_y - tent_h//2)])
            # roof
            pygame.draw.polygon(win, (220,0,0), [(tx+24, tent_base_y - tent_h//2), (tx+tent_w-24, tent_base_y - tent_h//2), (tx+tent_w//2, tent_base_y - tent_h)])
            # rainbow stripes
            rainbow = [(255,0,0),(255,127,0),(255,255,0),(0,200,0),(0,120,255),(75,0,130),(148,0,211)]
            tip = (tx+tent_w//2, tent_base_y - tent_h)
            step = max(6, tent_w // (len(rainbow)*6))
            for i, x in enumerate(range(0, tent_w, step)):
                col = rainbow[i % len(rainbow)]
                pygame.draw.line(win, col, (tx+x, tent_base_y), tip, 2)
            # flag
            pygame.draw.line(win, WHITE, (tx+tent_w//2, tent_base_y - tent_h), (tx+tent_w//2, tent_base_y - tent_h - int(20*scale)), 2)
            pygame.draw.polygon(win, GOLD, [(tx+tent_w//2, tent_base_y - tent_h - int(20*scale)), (tx+tent_w//2 + int(12*scale), tent_base_y - tent_h - int(14*scale)), (tx+tent_w//2, tent_base_y - tent_h - int(8*scale))])
        # Place several tents across background
        all_tents = [(250,0.9),(700,0.8),(1150,0.7),(1600,0.85),(2100,0.75),(2550,0.8)]
        for base_x, sc in all_tents:
            if sc >= 0.85:
                continue  # skip largest tents that may block
            draw_tent(base_x, sc)
        # Market stalls (behind platforms)
        def draw_stall(x):
            sx = int(x - camera_x*0.9)
            sy = HEIGHT - 90 - camera_y
            pygame.draw.rect(win, (180,80,40), (sx, sy, 80, 40))
            pygame.draw.polygon(win, (220,0,0), [(sx-6, sy), (sx+86, sy), (sx+40, sy-24)])
            for i in range(6):
                col = (255,220,0) if i%2==0 else (255,255,255)
                pygame.draw.circle(win, col, (sx+10+i*12, sy+6), 3)
        for bx in [400, 900, 1350, 1750, 2200, 2650]:
            draw_stall(bx)
        # platforms (draw beams with stripes)
        for p in platforms:
            base = pygame.Rect(p.x - camera_x, p.y - camera_y, p.w, p.h)
            pygame.draw.rect(win, MID_BLUE, base)
            for i in range(0, p.w, 20):
                col = GOLD if (i//20)%2==0 else PURPLE
                pygame.draw.rect(win, col, (p.x - camera_x + i, p.y - camera_y, 10, p.h))
        # portals
        for prt in portals:
            r = prt["rect"]
            pygame.draw.rect(win, (80,20,100), (r.x - camera_x, r.y - camera_y, r.w, r.h))
            pygame.draw.rect(win, (200,160,255), (r.x - camera_x+4, r.y - camera_y+4, r.w-8, r.h-8))
        # barriers
        for barrier in barriers:
            pygame.draw.rect(win, GOLD, (barrier.x - camera_x, barrier.y - camera_y, barrier.w, barrier.h))
            pygame.draw.rect(win, (255,255,255), (barrier.x - camera_x+2, barrier.y - camera_y+2, barrier.w-4, barrier.h-4), 2)
        # Draw ALL survivors
        for survivor in survivors:
            if not getattr(survivor, 'invisible', False):
                survivor.draw(camera_x, camera_y)

            # Special effects overlays
            if getattr(survivor, 'shield_active', False):
                # Tank shield effect
                shield_overlay = pygame.Surface((survivor.w + 10, survivor.h + 10), pygame.SRCALPHA)
                shield_overlay.fill((0,100,255,80))
                win.blit(shield_overlay, (survivor.x - camera_x - 5, survivor.y - camera_y - 5))

            if noob_reduce_until and now < noob_reduce_until:
                overlay = pygame.Surface((survivor.w, survivor.h), pygame.SRCALPHA)
                overlay.fill((100,100,100,120))
                win.blit(overlay, (survivor.x - camera_x, survivor.y - camera_y))
        coolkid.draw(camera_x, camera_y)
        for cinfo in clones:
            c = cinfo["p"]
            c.draw(camera_x, camera_y)
        # cooldown bars moved to bottom of each screen - REMOVED from above heads
        for gen in generators:
            gen.draw(camera_x, camera_y)
        # draw houses last so they occlude characters
        for hx, hy, hw, hh in houses:
            pygame.draw.rect(win, (180,80,40), (hx - camera_x, hy - camera_y, hw, hh))
            pygame.draw.polygon(win, (150,50,30), [(hx - camera_x, hy - camera_y), (hx - camera_x + hw, hy - camera_y), (hx - camera_x + hw//2, hy - camera_y - 30)])
            # window - lights up if ANY survivor is inside
            wx, wy, ww, wh = hx - camera_x + 20, hy - camera_y + 20, 24, 18
            in_window = any(survivor.rect().colliderect(pygame.Rect(hx, hy, hw, hh)) for survivor in survivors)
            pygame.draw.rect(win, (255,255,120) if in_window else (80,80,80), (wx, wy, ww, wh))
            pygame.draw.rect(win, BLACK, (wx, wy, ww, wh), 2)
        # 1x1x1x1 arrow render - points to nearest survivor
        if selected_killer == '1x1x1x1' and now < arrow_hint_until and survivors:
            # Find nearest survivor
            nearest_survivor = min(survivors, key=lambda s: abs(s.x - coolkid.x) + abs(s.y - coolkid.y))
            # vector from killer to nearest survivor
            vx = (nearest_survivor.x + nearest_survivor.w/2) - (coolkid.x + coolkid.w/2)
            vy = (nearest_survivor.y + nearest_survivor.h/2) - (coolkid.y + coolkid.h/2)
            ang = math.atan2(vy, vx)
            # arrow at killer head
            base_x = int(coolkid.x + coolkid.w/2 - camera_x)
            base_y = int(coolkid.y + 10 - camera_y)
            L = 60
            tip_x = base_x + int(math.cos(ang) * L)
            tip_y = base_y + int(math.sin(ang) * L)
            # simple triangle arrow
            left = (tip_x + int(math.cos(ang + 2.5) * 14), tip_y + int(math.sin(ang + 2.5) * 14))
            right = (tip_x + int(math.cos(ang - 2.5) * 14), tip_y + int(math.sin(ang - 2.5) * 14))
            pygame.draw.line(win, (0,255,0), (base_x, base_y), (tip_x, tip_y), 4)
            pygame.draw.polygon(win, (0,255,0), [(tip_x, tip_y), left, right])
        # draw projectiles
        for pr in projectiles:
            if pr["kind"] == "stun":
                pygame.draw.circle(win, (0,255,0), (int(pr["x"]) - camera_x, int(pr["y"])) , 6)
                pygame.draw.circle(win, (255,255,255), (int(pr["x"]) - camera_x, int(pr["y"])) , 9, 2)
            elif pr["kind"] == "blade":
                for i in range(len(pr["trail"]) - 1):
                    x1,y1 = pr["trail"][i]
                    x2,y2 = pr["trail"][i+1]
                    pygame.draw.line(win, (80,80,80), (int(x1) - camera_x, int(y1) - camera_y), (int(x2) - camera_x, int(y2) - camera_y), 3)
                cx = pr["x"] - camera_x
                cy = pr["y"] - camera_y
                L = pr.get("len",90)
                W = pr.get("wid",18)
                ang = math.radians(pr.get("angle",0))
                cosA = math.cos(ang); sinA = math.sin(ang)
                pts = []
                for px, py in [( -L/2, -W/2 ), ( L/2, -W/2 ), ( L/2, W/2 ), ( -L/2, W/2 )]:
                    rx = px*cosA - py*sinA + cx
                    ry = px*sinA + py*cosA + cy
                    pts.append((int(rx), int(ry)))
                pygame.draw.polygon(win, (0,0,0), pts)
                pygame.draw.polygon(win, (255,0,0), pts, 2)
            elif pr["kind"] == "stun_blade":
                for i in range(len(pr["trail"]) - 1):
                    x1,y1 = pr["trail"][i]
                    x2,y2 = pr["trail"][i+1]
                    pygame.draw.line(win, (80,80,80), (int(x1) - camera_x, int(y1) - camera_y), (int(x2) - camera_x, int(y2) - camera_y), 3)
                cx = pr["x"] - camera_x
                cy = pr["y"] - camera_y
                L = pr.get("len",60)
                W = pr.get("wid",12)
                ang = math.radians(pr.get("angle",0))
                cosA = math.cos(ang); sinA = math.sin(ang)
                pts = []
                for px, py in [( -L/2, -W/2 ), ( L/2, -W/2 ), ( L/2, W/2 ), ( -L/2, W/2 )]:
                    rx = px*cosA - py*sinA + cx
                    ry = px*sinA + py*cosA + cy
                    pts.append((int(rx), int(ry)))
                pygame.draw.polygon(win, (0,0,0), pts)
                pygame.draw.polygon(win, (0,200,0), pts, 2)
        # dash explosion FX (render inside each view)
        if noob_explosion_until and now < noob_explosion_until:
            t = 1.0 - ((noob_explosion_until - now) / 0.45)
            cxp = int(noob.x + noob.w/2 - camera_x)
            cyp = int(noob.y + noob.h/2 - camera_y)
            r1 = int(20 + 40 * t)
            r2 = int(10 + 30 * t)
            pygame.draw.circle(win, (255,120,0), (cxp, cyp), r1)
            pygame.draw.circle(win, (255,220,0), (cxp, cyp), r2)
            pygame.draw.circle(win, (255,255,255), (cxp, cyp), max(2, int(6 * (1-t))), 2)
        # slashes
        attackers = [coolkid] + [c["p"] for c in clones]
        for attacker in attackers:
            if attacker.slash_line:
                a0, a1 = attacker.slash_line
                if getattr(attacker,'variant','CoolKid') == '1x1x1x1':
                    pygame.draw.line(win, (0,0,0), (a0[0] - camera_x, a0[1] - camera_y), (a1[0] - camera_x, a1[1] - camera_y), 12)
                else:
                    pygame.draw.line(win, (0,0,0), (a0[0] - camera_x, a0[1] - camera_y), (a1[0] - camera_x, a1[1] - camera_y), 12)
                    pygame.draw.line(win, (255,255,255), (a0[0] - camera_x, a0[1] - camera_y), (a1[0] - camera_x, a1[1] - camera_y), 8)
                    pygame.draw.line(win, (255,215,0), (a0[0] - camera_x, a0[1] - camera_y), (a1[0] - camera_x, a1[1] - camera_y), 4)
                if now - getattr(attacker, 'slash_spawn_time', 0) < 0.2:
                    cxp = (a0[0] + a1[0]) // 2 - camera_x
                    cyp = (a0[1] + a1[1]) // 2 - camera_y
                    pygame.draw.circle(win, (255,255,0), (cxp, cyp), 10)
                    pygame.draw.circle(win, (255,255,255), (cxp, cyp), 16, 3)
        # foreground platform edges
        for p in platforms:
            pygame.draw.line(win, WHITE, (p.x - camera_x, p.y - camera_y), (p.x - camera_x + p.w, p.y - camera_y), 3)
            pygame.draw.line(win, (0,0,0), (p.x - camera_x, p.y - camera_y + p.h - 1), (p.x - camera_x + p.w, p.y - camera_y + p.h - 1), 2)

    # render both views
    display_surface = win
    # left view (Noob)
    scene_left = pygame.Surface((render_w, render_h))
    win = scene_left
    draw_world(camera_left_x, camera_left_y)
    # right view (Killer)
    scene_right = pygame.Surface((render_w, render_h))
    win = scene_right
    draw_world(camera_right_x, camera_right_y)
    # back to display and blit halves without scaling
    win = display_surface
    win.blit(scene_left, (0, 0))
    win.blit(scene_right, (WIDTH//2, 0))
    # divider
    pygame.draw.rect(win, (20,20,20), (WIDTH//2 - 2, 0, 4, HEIGHT))

    # Draw cooldown bars at bottom of each screen
    # Left screen (Main character) cooldowns
    if main_character and main_character.hp > 0:
        survivor_type = getattr(main_character, 'survivor_type', 'Noob')
        if survivor_type == "Noob":
            draw_cooldowns_bottom(["noob_speed","noob_invis","noob_reduce"], 0, HEIGHT, WIDTH//2, True)
        else:
            # Show first 3 abilities for the main character
            abilities = SURVIVOR_TYPES[survivor_type]["abilities"][:3]
            draw_cooldowns_bottom(abilities, 0, HEIGHT, WIDTH//2, True)

    # Right screen (Killer) cooldowns
    if selected_killer == "CoolKid":
        draw_cooldowns_bottom(["coolkid_dash","coolkid_clone","coolkid_slash"], WIDTH//2, HEIGHT, WIDTH//2, False)
    else:
        draw_cooldowns_bottom(["one_stun","one_slash","coolkid_dash","one_arrow"], WIDTH//2, HEIGHT, WIDTH//2, False)

    # UI overlay (fixed to screen): timer at top center
    elapsed = now - start_time
    time_left = max(0, int(GAME_DURATION - elapsed - bonus_time))
    timer_text = FONT.render(f"Survive: {time_left}s", True, WHITE)
    win.blit(timer_text, (WIDTH//2 - timer_text.get_width()//2, 20))
    # UI overlay: ALL Survivors health bars (individual bars)
    for i, survivor in enumerate(survivors):
        ui_bar_x, ui_bar_y = 20, 50 + i * 35
        ui_bar_w, ui_bar_h = 200, 20

        # Background
        pygame.draw.rect(win, (60,0,0), (ui_bar_x, ui_bar_y, ui_bar_w, ui_bar_h))

        # Health bar with survivor type-specific color
        survivor_type = getattr(survivor, 'survivor_type', 'Noob')
        type_data = getattr(survivor, 'type_data', SURVIVOR_TYPES['Noob'])
        hp_ratio = survivor.hp / survivor.max_hp
        hp_w = max(0, int(ui_bar_w * hp_ratio))

        # Color based on health and type
        if hp_ratio > 0.6:
            bar_color = type_data['color']
        elif hp_ratio > 0.3:
            bar_color = (255,165,0)  # Orange for medium health
        else:
            bar_color = (255,0,0)    # Red for low health

        pygame.draw.rect(win, bar_color, (ui_bar_x, ui_bar_y, hp_w, ui_bar_h))
        pygame.draw.rect(win, WHITE, (ui_bar_x, ui_bar_y, ui_bar_w, ui_bar_h), 2)

        # Survivor name and HP text
        hp_text = FONT.render(f"{survivor_type}: {survivor.hp}/{survivor.max_hp}", True, WHITE)
        win.blit(hp_text, (ui_bar_x, ui_bar_y - 20))

    # check win/lose 
    game_over = False
    winner = None
    alive_survivors = [s for s in survivors if s.hp > 0]
    if not alive_survivors:  # All survivors dead
        game_over = True
        winner = selected_killer
    elif time_left <= 0:
        game_over = True
        winner = "Survivors"

    if game_over:
        # spawn confetti once
        if not confetti:
            import random as _r
            if winner == "Noob":
                colors = [(0,200,0),(0,120,255),(255,215,0)]
            else:
                # killer wins: green if 1x1x1x1, red if CoolKid
                colors = [(0,200,0)] if selected_killer == "1x1x1x1" else [(255,0,0)]
            for _ in range(120):
                cx = WIDTH//2 + _r.randint(-80,80)
                cy = HEIGHT//3
                vx = _r.uniform(-2.5, 2.5)
                vy = _r.uniform(-5.0, -1.0)
                col = colors[_r.randrange(len(colors))]
                confetti.append({"x":cx, "y":cy, "vx":vx, "vy":vy, "color":col, "life":_r.uniform(1.0, 2.0)})
        # animate confetti for 2 seconds (or until rematch)
        end_until = now + 2.0
        rematch = False
        button_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 20, 200, 48)
        while True:
            # fade overlay
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,60))
            win.blit(overlay, (0,0))
            # update and draw confetti
            for p in confetti:
                p["vy"] += 0.15
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                pygame.draw.rect(win, p["color"], (int(p["x"]), int(p["y"]), 4, 6))
            # custom win text for 1x1x1x1
            if winner == "Noob":
                end_col = WHITE
                win_text = f"{winner} Wins!"
            else:
                if selected_killer == "1x1x1x1":
                    end_col = (0,200,0)
                    win_text = "1x1x1x wins!!!"
                else:
                    end_col = RED
                    win_text = "CoolKid Wins!"
            end_txt = BIG.render(win_text, True, end_col)
            win.blit(end_txt, (WIDTH//2 - end_txt.get_width()//2, HEIGHT//2 - 60))
            # Rematch button
            pygame.draw.rect(win, (30,30,30), button_rect)
            pygame.draw.rect(win, WHITE, button_rect, 2)
            btn_txt = PRESS_FONT.render("Rematch (R)", True, WHITE)
            win.blit(btn_txt, (button_rect.centerx - btn_txt.get_width()//2, button_rect.centery - btn_txt.get_height()//2))
            pygame.display.update()
            clock.tick(60)
            # events
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                    rematch = True
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if button_rect.collidepoint(ev.pos):
                        rematch = True
            if rematch or time.time() >= end_until:
                break
        if rematch:
            # reset round state without quitting
            confetti.clear()
            # reset survivors
            for i, survivor in enumerate(survivors):
                survivor.hp = survivor.max_hp
                if i < len(SURVIVOR_SPAWNS):
                    survivor.x, survivor.y = SURVIVOR_SPAWNS[i]
                else:
                    survivor.x, survivor.y = SURVIVOR_SPAWNS[i % len(SURVIVOR_SPAWNS)]
                survivor.vel_y = 0; survivor.on_ground = False; survivor.invisible = False; survivor.stun_until = 0.0
            coolkid.x, coolkid.y = 300, HEIGHT - 150
            coolkid.vel_y = 0; coolkid.on_ground = False; coolkid.stun_until = 0.0
            # clear effects
            clones.clear()
            projectiles.clear()
            noob_explosion_until = 0.0
            arrow_hint_until = 0.0
            # reset generators
            for gen in generators:
                gen.done = False
                gen.active = False
                gen.index = 0
                gen.sequence = []
            bonus_time = 0
            # reset cooldowns
            for k in cooldowns.keys():
                cooldowns[k] = 0.0
            # timer
            start_time = time.time()
            game_over = False
            winner = None
            continue
        # otherwise end the program (fade out music first)
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.fadeout(1500)
        except Exception:
            pass
        pygame.quit()
        sys.exit()

    pygame.display.update()



