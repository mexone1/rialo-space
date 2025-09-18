

import sys, random, math
from pathlib import Path
import pygame

# ---------------- Config ----------------
W, H = 480, 720
FPS = 60

GRAVITY = 1400.0
FLAP_VY  = -460.0
MAX_VY   = 900.0

GATE_W = 92
GATE_GAP = 200
GATE_MIN = 70
GATE_MAX = H - 230
GATE_SPACING = 250
SCROLL_SPEED = 260.0

HUD = (230, 250, 255)

# --- Soft Space Blue theme (columns) ---
COL_CORE    = (120, 205, 255)   #
COL_EDGE    = ( 80, 170, 255)   
COL_GLOW    = (160, 220, 255)   
COL_STRIPE  = (140, 210, 255)   
COL_SCAN    = (220, 245, 255)   

#анимация
SCAN_SPEED   = 0.28
PULSE_SPEED  = 0.35
PULSE_AMT    = 0.035
GLOW_ALPHA   = 36
EDGE_ALPHA   = 140
SCAN_ALPHA   = 42
SCAN_WIDTH_F = 0.16

# --- Вертикальная широкая надпись внутри колоны ---
LABEL_TEXT          = "RIALO"
LABEL_CORE_COLOR    = (240, 250, 255)   
LABEL_GLOW_COLOR    = (170, 230, 255)   
LABEL_GLOW_ALPHA    = 90
LABEL_BREATH_AMT    = 0.04             
LABEL_MARGIN_PX     = 8              
LABEL_EXTRA_W_STRETCH= 4             

# --- Разряды (не используем тут, можно включить позже) ---
ENABLE_ARCS     = False
ARC_COLOR_CORE  = (230, 255, 255)
ARC_COLOR_GLOW  = (120, 220, 255)
ARC_WIDTH       = 2
ARC_GLOW_ALPHA  = 90
ARC_MIN_GAP_S   = 2.5
ARC_MAX_GAP_S   = 6.0
ARC_DURATION_S  = 0.25
ARC_SEGMENTS    = 7

ASSETS = [Path("."), Path("./assets")]
BG_NAME   = "space_bg.png"
SHIP_NAME = "ship.png"

# --- Ship / flame ---
SHIP_SIZE    = (72, 72)
THRUST_TIME  = 0.18
FLAME_COLOR_OUTER = (70, 180, 255)
FLAME_COLOR_CORE  = (200, 240, 255)
FLAME_ATTACH   = 0.48
FLAME_WIDTH    = 10
FLAME_Y_OFFSET = 5
NOZZLE_INSET   = 2

# ---------- Utils ----------
def load_image(name: str):
    for d in ASSETS:
        p = d / name
        if p.exists():
            return pygame.image.load(str(p)).convert_alpha()
    return None

def mask_rect_overlap(mask: pygame.mask.Mask, rect: pygame.Rect, offset):
    if rect.width <= 0 or rect.height <= 0:
        return False
    rs = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    rs.fill((255, 255, 255, 255))
    rmask = pygame.mask.from_surface(rs, 1)
    return mask.overlap(rmask, offset) is not None

def lerp(a, b, t): return a + (b - a) * t
def clamp8(x): return max(0, min(255, int(x)))

# ---------- Panels (columns) ----------
def draw_soft_fill(panel: pygame.Surface, radius: int):
    """Нежный вертикальный градиент + тонкие диагональные дорожки."""
    w, h = panel.get_width(), panel.get_height()

    # вертикальный градиент
    for y in range(h):
        ky = y / max(1, h - 1)
        mul = (0.86 + 0.14 * (1 - ky))
        r = clamp8(COL_CORE[0] * mul)
        g = clamp8(COL_CORE[1] * mul)
        b = clamp8(COL_CORE[2] * mul)
        pygame.draw.line(panel, (r, g, b), (0, y), (w - 1, y))

    # диагональные дорожки (очень мягкие)
    stripes = pygame.Surface((w, h), pygame.SRCALPHA)
    step = 14
    for x in range(-h, w, step):
        pygame.draw.line(stripes, (*COL_STRIPE, 24), (x, 0), (x + h, h), width=2)
    panel.blit(stripes, (0, 0), special_flags=pygame.BLEND_ADD)

    # маска скругления
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
    panel.blit(mask, (0, 0), special_flags=pygame.BLEND_MULT)

def draw_scan_band(panel: pygame.Surface, t: float):
    """Тихая скан-лента."""
    w, h = panel.get_width(), panel.get_height()
    phase = (math.sin(t * SCAN_SPEED * 2.0 * math.pi) * 0.5 + 0.5)
    band_h = max(8, int(h * SCAN_WIDTH_F))
    band_y = int(lerp(-h//2, h, phase))
    band = pygame.Surface((w, band_h), pygame.SRCALPHA)
    for i in range(band_h):
        k = i / max(1, band_h - 1)
        alpha = int(SCAN_ALPHA * (1 - abs(0.5 - k) * 2))
        pygame.draw.line(band, (*COL_SCAN, alpha), (0, i), (w - 1, i))
    panel.blit(band, (0, band_y - band_h // 2), special_flags=pygame.BLEND_ADD)

def draw_label_vertical(panel: pygame.Surface, t: float, text: str = LABEL_TEXT):
  
    w, h = panel.get_width(), panel.get_height()
    if w <= 6 or h <= 6: return

    
    breath = 1.0 + LABEL_BREATH_AMT * math.sin(t * 2.0 * math.pi * 0.25)


    target_w = max(4, int((w - LABEL_MARGIN_PX * 2) * LABEL_EXTRA_W_STRETCH * breath))

    
    base_size = max(14, int(h * 0.24))
    font = pygame.font.SysFont(None, base_size, bold=True)

   
    text_core = font.render(text, True, LABEL_CORE_COLOR)

    
    ratio = target_w / max(1, text_core.get_width())
    new_w = max(1, int(text_core.get_width() * ratio))
    new_h = max(1, int(text_core.get_height() * ratio * 0.95))  
    text_core = pygame.transform.smoothscale(text_core, (new_w, new_h))

   
    glow = pygame.Surface((text_core.get_width()+12, text_core.get_height()+12), pygame.SRCALPHA)
    offsets = [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,1),(-1,1),(1,-1)]
    for dx, dy in offsets:
        tmp = font.render(text, True, LABEL_GLOW_COLOR)
        tmp = pygame.transform.smoothscale(tmp, (new_w, new_h))
        glow.blit(tmp, (dx+6, dy+6))
    glow.set_alpha(LABEL_GLOW_ALPHA)

    
    combo = pygame.Surface((max(glow.get_width(), text_core.get_width()),
                            max(glow.get_height(), text_core.get_height())), pygame.SRCALPHA)
    combo.blit(glow, ((combo.get_width()-glow.get_width())//2, (combo.get_height()-glow.get_height())//2))
    combo.blit(text_core, ((combo.get_width()-text_core.get_width())//2, (combo.get_height()-text_core.get_height())//2))

    
    combo = pygame.transform.rotozoom(combo, -90, 1.0)

 
    px = (w - combo.get_width()) // 2
    py = (h - combo.get_height()) // 2
    panel.blit(combo, (px, py), special_flags=pygame.BLEND_PREMULTIPLIED)

def draw_panel(surf: pygame.Surface, rect: pygame.Rect, t: float, radius: int = 16):
    """Панель полностью: свечение, наполнение, вертикальная надпись, окантовка, скан-лента."""
    if rect.width <= 0 or rect.height <= 0: return

  
    pad = 14
    glow = pygame.Surface((rect.width + pad*2, rect.height + pad*2), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*COL_GLOW, GLOW_ALPHA),
                     (0, 0, glow.get_width(), glow.get_height()),
                     border_radius=radius + pad//2)
    surf.blit(glow, (rect.x - pad, rect.y - pad), special_flags=pygame.BLEND_PREMULTIPLIED)

   
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

   
    pulse = 1.0 + PULSE_AMT * (1 - math.cos(t * PULSE_SPEED * 2.0 * math.pi)) * 0.5
    draw_soft_fill(panel, radius)
    if pulse != 1.0:
        tint = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        mul = clamp8(255 * (pulse - 1.0))
        if mul > 0:
            tint.fill((COL_GLOW[0], COL_GLOW[1], COL_GLOW[2], min(60, mul)))
            panel.blit(tint, (0, 0), special_flags=pygame.BLEND_ADD)

   
    draw_label_vertical(panel, t, LABEL_TEXT)

   
    draw_scan_band(panel, t)

    
    pygame.draw.rect(panel, (*COL_EDGE, EDGE_ALPHA),
                     (0, 0, rect.width, rect.height), width=3, border_radius=radius)

    surf.blit(panel, rect.topleft)

# ---------------- Entities ----------------
class Ship:
    def __init__(self, img):
        self.x = W * 0.25
        self.y = H * 0.5
        self.vy = 0.0

        self.base_img = pygame.transform.smoothscale(img, SHIP_SIZE)

        base_mask = pygame.mask.from_surface(self.base_img, 10)
        rects = base_mask.get_bounding_rects()
        if rects: bbox = rects[0]
        else:     bbox = pygame.Rect(0, 0, self.base_img.get_width(), self.base_img.get_height())

        self.anchor_base = (bbox.left + NOZZLE_INSET, bbox.top + bbox.height // 2)
        self.base_center = (self.base_img.get_width() / 2.0, self.base_img.get_height() / 2.0)

        self.current_img = self.base_img
        self.current_rect = self.current_img.get_rect(center=(int(self.x), int(self.y)))
        self.current_mask = pygame.mask.from_surface(self.current_img, 10)
        self.angle_deg = 0.0

        self.thrust_timer = 0.0

    @property
    def rect(self): return self.current_rect

    def flap(self):
        self.vy = FLAP_VY
        self.thrust_timer = THRUST_TIME

    def nozzle_pos(self):
        ax, ay = self.anchor_base
        cx, cy = self.base_center
        dx, dy = (ax - cx), (ay - cy)
        a = math.radians(self.angle_deg)
        rx = dx * math.cos(a) - dy * math.sin(a)
        ry = dx * math.sin(a) + dy * math.cos(a)
        return (self.current_rect.centerx + rx, self.current_rect.centery + ry)

    def update(self, dt):
        self.vy = min(self.vy + GRAVITY * dt, MAX_VY)
        self.y += self.vy * dt
        if self.thrust_timer > 0: self.thrust_timer -= dt

        vy_clamp = max(-420, min(420, self.vy))
        self.angle_deg = -vy_clamp / 420 * 12

        self.current_img = pygame.transform.rotozoom(self.base_img, self.angle_deg, 1.0)
        self.current_rect = self.current_img.get_rect(center=(int(self.x), int(self.y)))
        self.current_mask = pygame.mask.from_surface(self.current_img, 10)

    def draw(self, screen):
        if self.thrust_timer > 0:
            nx, ny = self.nozzle_pos()
            ny_adj = ny + FLAME_Y_OFFSET
            base_len = 26
            vel_add  = max(0, min(14, -self.vy * 0.04))
            length   = int(max(14, min(50, base_len + vel_add)))
            width    = FLAME_WIDTH
            tail_x   = nx - int(length * FLAME_ATTACH)
            pygame.draw.polygon(screen, FLAME_COLOR_OUTER,
                                [(tail_x, ny_adj), (nx, ny_adj - width // 2), (nx, ny_adj + width // 2)])
            core_len = int(length * 0.6)
            core_w   = int(width * 0.5)
            core_tail= nx - int(core_len * FLAME_ATTACH)
            pygame.draw.polygon(screen, FLAME_COLOR_CORE,
                                [(core_tail, ny_adj), (nx, ny_adj - core_w // 2), (nx, ny_adj + core_w // 2)])
        screen.blit(self.current_img, self.current_rect.topleft)

class Gate:
    def __init__(self, x, gap_y):
        self.x = float(x); self.gap_y = gap_y; self.passed = False

    @property
    def top_rect(self): return pygame.Rect(int(self.x), 0, GATE_W, self.gap_y - GATE_GAP // 2)
    @property
    def bot_rect(self):
        by = self.gap_y + GATE_GAP // 2
        return pygame.Rect(int(self.x), by, GATE_W, H - by)

    def update(self, dt):
        self.x -= SCROLL_SPEED * dt

    def draw(self, surf, t):
        if self.top_rect.height > 0: draw_panel(surf, self.top_rect, t, radius=16)
        if self.bot_rect.height > 0: draw_panel(surf, self.bot_rect, t, radius=16)

# ---------------- Game ----------------
def add_gate(gates, x):
    gap_y = random.randint(GATE_MIN + GATE_GAP // 2, GATE_MAX - GATE_GAP // 2)
    gates.append(Gate(x, gap_y))

def reset_game(ship_img):
    ship = Ship(ship_img)
    gates = []; spawn = W + 120
    for i in range(4): add_gate(gates, spawn + i * GATE_SPACING)
    return ship, gates, 0, False, True

def draw_background(screen, bg_img):
    if bg_img:
        iw, ih = bg_img.get_width(), bg_img.get_height()
        scale = max(W / iw, H / ih)
        bg = pygame.transform.smoothscale(bg_img, (int(iw * scale), int(ih * scale)))
        screen.blit(bg, ((W - bg.get_width()) // 2, (H - bg.get_height()) // 2))
    else:
        screen.fill((0, 0, 0))

def draw_hud(screen, score, best, started, running, fonts):
    big, small = fonts
    txt = big.render(f"Score: {score}", True, HUD); screen.blit(txt, (W//2 - txt.get_width()//2, 16))
    best_txt = small.render(f"Best: {best}", True, HUD); screen.blit(best_txt, (16, 14))
    if not started:
        tip = small.render("Click or SPACE to start", True, HUD); screen.blit(tip, (W//2 - tip.get_width()//2, H//2))
    if not running:
        over = big.render("GAME OVER", True, HUD); screen.blit(over, (W//2 - over.get_width()//2, int(H*0.45)))
        tip2 = small.render("Press R to restart", True, HUD); screen.blit(tip2, (W//2 - tip2.get_width()//2, int(H*0.5)))

def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Space Edition — columns with vertical RIALO")
    clock = pygame.time.Clock()
    font_big = pygame.font.SysFont(None, 36, bold=True)
    font_small = pygame.font.SysFont(None, 24)

    bg_img = load_image(BG_NAME)
    ship_img = load_image(SHIP_NAME)
    if not ship_img: sys.exit("ship.png not found!")
    ship_img = pygame.transform.smoothscale(ship_img, SHIP_SIZE)

    ship, gates, score, started, running = reset_game(ship_img)
    best = 0
    time_acc = 0.0

    while True:
        dt = clock.tick(FPS) / 1000.0
        time_acc += dt
        flap = False

        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if e.key == pygame.K_r: ship, gates, score, started, running = reset_game(ship_img)
                if e.key in (pygame.K_SPACE, pygame.K_UP): flap = True
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1: flap = True

        if flap:
            if running: started = True; ship.flap()
            else: ship, gates, score, started, running = reset_game(ship_img)

        if started and running:
            ship.update(dt)
            for g in gates: g.update(dt)
            if gates and gates[0].x + GATE_W < -20:
                gates.pop(0); add_gate(gates, gates[-1].x + GATE_SPACING)
            for g in gates:
                if not g.passed and g.x + GATE_W < ship.x:
                    g.passed = True; score += 1; best = max(best, score)
            if ship.rect.top < 0 or ship.rect.bottom > H:
                running = False
            for g in gates:
                if ship.rect.colliderect(g.top_rect):
                    dx = g.top_rect.x - ship.rect.x; dy = g.top_rect.y - ship.rect.y
                    if mask_rect_overlap(ship.current_mask, g.top_rect, (dx, dy)):
                        running = False; break
                if ship.rect.colliderect(g.bot_rect):
                    dx = g.bot_rect.x - ship.rect.x; dy = g.bot_rect.y - ship.rect.y
                    if mask_rect_overlap(ship.current_mask, g.bot_rect, (dx, dy)):
                        running = False; break

        draw_background(screen, bg_img)
        for g in gates: g.draw(screen, time_acc)
        ship.draw(screen)
        draw_hud(screen, score, best, started, running, (font_big, font_small))
        pygame.display.flip()

if __name__ == "__main__":
    main()