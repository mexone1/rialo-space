# RIALO Space — Flappy-like (PC + Web/pygbag)
# Controls: SPACE/Click = flap, R = restart, ESC = quit

import math, random, asyncio
from pathlib import Path
import pygame

# ---------------- CONFIG ----------------
W, H = 480, 720
FPS = 60

# physics
GRAVITY = 1400.0
FLAP_VY  = -460.0
MAX_VY   = 900.0

# gates
GATE_W = 92
GATE_GAP = 200
GATE_MIN = 70
GATE_MAX = H - 230
GATE_SPACING = 250
SCROLL_SPEED = 260.0

HUD = (230, 250, 255)

# fallback neon styles (если нет column.png)
COL_CORE    = (120, 205, 255)
COL_EDGE    = ( 80, 170, 255)
COL_GLOW    = (160, 220, 255)
COL_STRIPE  = (140, 210, 255)
COL_SCAN    = (220, 245, 255)
SCAN_SPEED   = 0.28
PULSE_SPEED  = 0.35
PULSE_AMT    = 0.035
GLOW_ALPHA   = 36
EDGE_ALPHA   = 140
SCAN_ALPHA   = 42
SCAN_WIDTH_F = 0.16
LABEL_TEXT           = "RIALO"
LABEL_CORE_COLOR     = (240, 250, 255)
LABEL_GLOW_COLOR     = (170, 230, 255)
LABEL_GLOW_ALPHA     = 90
LABEL_BREATH_AMT     = 0.04
LABEL_MARGIN_PX      = 6
LABEL_EXTRA_W_STRETCH= 1.06

# ship + flame
SHIP_SIZE    = (72, 72)
THRUST_TIME  = 0.18
FLAME_COLOR_OUTER = (70, 180, 255)
FLAME_COLOR_CORE  = (200, 240, 255)
FLAME_ATTACH   = 0.48
FLAME_WIDTH    = 10
FLAME_Y_OFFSET = 5
NOZZLE_INSET   = 2

# pillars render tuning (новые колоны)
PILLAR_RADIUS      = 16
PILLAR_TRIM_TOP    = 8     # подрез верх исходной текстуры (убирает «крышку»)
PILLAR_TRIM_BOTTOM = 8     # подрез низа
PILLAR_INNER_GLOW  = True # мягкое свечение по внутреннему гориз. краю; по умолчанию выключено
PILLAR_GLOW_BAND   = 8
PILLAR_GLOW_COLOR  = (120, 200, 255, 85)

# assets
ASSET_DIRS = [Path("."), Path("./assets")]
BG_NAME    = "space_bg.png"
SHIP_NAME  = "ship.png"
PILLAR_IMG_NAME = "column_v2.png"  # твой арт колонн

# -------------- UTILS --------------
def load_image(name: str):
    for d in ASSET_DIRS:
        p = d / name
        if p.exists():
            return pygame.image.load(str(p)).convert_alpha()
    return None

def mask_rect_overlap(mask: pygame.mask.Mask, rect: pygame.Rect, offset):
    if rect.width <= 0 or rect.height <= 0: return False
    rs = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    rs.fill((255, 255, 255, 255))
    rmask = pygame.mask.from_surface(rs, 1)
    return mask.overlap(rmask, offset) is not None

def lerp(a, b, t): return a + (b - a) * t
def clamp8(x): return max(0, min(255, int(x)))

# ---------- FALLBACK NEON COLUMN (если нет column.png) ----------
def draw_soft_fill(panel: pygame.Surface, radius: int):
    w, h = panel.get_width(), panel.get_height()
    for y in range(h):
        ky = y / max(1, h - 1)
        mul = (0.86 + 0.14 * (1 - ky))
        r = clamp8(COL_CORE[0] * mul)
        g = clamp8(COL_CORE[1] * mul)
        b = clamp8(COL_CORE[2] * mul)
        pygame.draw.line(panel, (r, g, b), (0, y), (w - 1, y))
    stripes = pygame.Surface((w, h), pygame.SRCALPHA).convert_alpha()
    step = 14
    for x in range(-h, w, step):
        pygame.draw.line(stripes, (*COL_STRIPE, 24), (x, 0), (x + h, h), width=2)
    panel.blit(stripes, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    mask = pygame.Surface((w, h), pygame.SRCALPHA).convert_alpha()
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
    panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

def draw_scan_band(panel: pygame.Surface, t: float):
    w, h = panel.get_width(), panel.get_height()
    phase = (math.sin(t * SCAN_SPEED * 2.0 * math.pi) * 0.5 + 0.5)
    band_h = max(8, int(h * SCAN_WIDTH_F))
    band_y = int(lerp(-h//2, h, phase))
    band = pygame.Surface((w, band_h), pygame.SRCALPHA).convert_alpha()
    for i in range(band_h):
        k = i / max(1, band_h - 1)
        alpha = int(SCAN_ALPHA * (1 - abs(0.5 - k) * 2))
        pygame.draw.line(band, (*COL_SCAN, alpha), (0, i), (w - 1, i))
    panel.blit(band, (0, band_y - band_h // 2), special_flags=pygame.BLEND_RGBA_ADD)

def draw_label_vertical(panel: pygame.Surface, t: float, text: str = LABEL_TEXT):
    w, h = panel.get_width(), panel.get_height()
    if w <= 6 or h <= 6: return
    breath = 1.0 + LABEL_BREATH_AMT * math.sin(t * 2.0 * math.pi * 0.25)
    target_w = max(4, int((w - LABEL_MARGIN_PX * 2) * LABEL_EXTRA_W_STRETCH * breath))
    font = pygame.font.SysFont(None, max(14, int(h * 0.24)), bold=True)
    core = font.render(text, True, LABEL_CORE_COLOR).convert_alpha()
    ratio = target_w / max(1, core.get_width())
    new_w = max(1, int(core.get_width() * ratio))
    new_h = max(1, int(core.get_height() * ratio * 0.95))
    core = pygame.transform.smoothscale(core, (new_w, new_h)).convert_alpha()
    glow = pygame.Surface((core.get_width()+12, core.get_height()+12), pygame.SRCALPHA).convert_alpha()
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,1),(-1,1),(1,-1)]:
        tmp = font.render(text, True, LABEL_GLOW_COLOR).convert_alpha()
        tmp = pygame.transform.smoothscale(tmp, (new_w, new_h)).convert_alpha()
        glow.blit(tmp, (dx+6, dy+6))
    glow.set_alpha(LABEL_GLOW_ALPHA)
    combo = pygame.Surface((max(glow.get_width(), core.get_width()),
                            max(glow.get_height(), core.get_height())), pygame.SRCALPHA).convert_alpha()
    combo.blit(glow, ((combo.get_width()-glow.get_width())//2, (combo.get_height()-glow.get_height())//2))
    combo.blit(core, ((combo.get_width()-core.get_width())//2, (combo.get_height()-core.get_height())//2))
    combo = pygame.transform.rotozoom(combo, -90, 1.0)
    px = (w - combo.get_width()) // 2
    py = (h - combo.get_height()) // 2
    panel.blit(combo, (px, py))

def draw_panel(surf: pygame.Surface, rect: pygame.Rect, t: float, radius: int = 16):
    if rect.width <= 0 or rect.height <= 0: return
    pad = 14
    glow = pygame.Surface((rect.width + pad*2, rect.height + pad*2), pygame.SRCALPHA).convert_alpha()
    pygame.draw.rect(glow, COL_GLOW, (0, 0, glow.get_width(), glow.get_height()),
                     border_radius=radius + pad//2)
    glow.set_alpha(GLOW_ALPHA)
    surf.blit(glow, (rect.x - pad, rect.y - pad))
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA).convert_alpha()
    pulse = 1.0 + PULSE_AMT * (1 - math.cos(t * PULSE_SPEED * 2.0 * math.pi)) * 0.5
    draw_soft_fill(panel, radius)
    if pulse != 1.0:
        tint = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA).convert_alpha()
        mul = max(0, min(70, int(255 * (pulse - 1.0))))
        if mul > 0:
            tint.fill((COL_GLOW[0], COL_GLOW[1], COL_GLOW[2], mul))
            panel.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    draw_label_vertical(panel, t, LABEL_TEXT)
    draw_scan_band(panel, t)
    pygame.draw.rect(panel, (*COL_EDGE, EDGE_ALPHA),
                     (0, 0, rect.width, rect.height), width=3, border_radius=radius)
    surf.blit(panel, rect.topleft)

# ---------- NEW: IMAGE COLUMNS with CACHE (быстро и без полос) ----------
_pillar_cache = {}      # key = (w,h,flip,radius,trimTop,trimBottom,glowFlag) -> Surface
_round_mask_cache = {}  # key = (w,h,radius) -> Surface

def _get_round_mask(w: int, h: int, radius: int) -> pygame.Surface:
    key = (w, h, radius)
    surf = _round_mask_cache.get(key)
    if surf is not None:
        return surf
    surf = pygame.Surface((w, h), pygame.SRCALPHA).convert_alpha()
    pygame.draw.rect(surf, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
    _round_mask_cache[key] = surf
    return surf

def _crop_alpha_bounds(src: pygame.Surface, thresh: int = 5) -> pygame.Surface:
    m = pygame.mask.from_surface(src, thresh)
    rects = m.get_bounding_rects()
    if rects:
        r = rects[0].clip(pygame.Rect(0, 0, src.get_width(), src.get_height()))
        if r.w > 0 and r.h > 0:
            return src.subsurface(r).copy()
    return src.copy()

def get_pillar_surface(img: pygame.Surface, w: int, h: int, flip: bool,
                       radius: int = PILLAR_RADIUS,
                       trim_top: int = PILLAR_TRIM_TOP,
                       trim_bottom: int = PILLAR_TRIM_BOTTOM,
                       inner_glow: bool = PILLAR_INNER_GLOW) -> pygame.Surface:
    """
    Возвращает ГОТОВЫЙ Surface колонны под размер (w,h):
    - вырезает прозрачные поля,
    - дополнительно подрезает верх/низ (убирает «крышки» из исходника),
    - растягивает на весь хитбокс,
    - мягко скругляет углы,
    - не рисует тонких линий/обводок; опционально — мягкое свечение по внутреннему гориз. краю,
    - кэшируется по ключу (w,h,flip,...).
    """
    key = (w, h, flip, radius, trim_top, trim_bottom, inner_glow)
    cached = _pillar_cache.get(key)
    if cached is not None:
        return cached

    src = _crop_alpha_bounds(img)

    # доп. подрезка
    if trim_top or trim_bottom:
        y0 = min(trim_top, src.get_height()-1)
        y1 = max(0, src.get_height() - trim_bottom)
        if y1 - y0 < 2:
            y0, y1 = 0, src.get_height()
        src = src.subsurface((0, y0, src.get_width(), y1 - y0)).copy()

    tex = pygame.transform.smoothscale(src, (w, h)).convert_alpha()
    if flip:
        tex = pygame.transform.flip(tex, False, True)

    mask = _get_round_mask(w, h, radius)
    tex.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    if inner_glow and w > 6 and h > 6:
        glow = pygame.Surface((w, h), pygame.SRCALPHA).convert_alpha()
        band = min(PILLAR_GLOW_BAND, h//3)
        cr, cg, cb, ca = PILLAR_GLOW_COLOR
        if flip:
            # верхняя колонна -> внутренний край "снизу"
            for i in range(band):
                a = int(ca * (1 - i / max(1, band)))
                y = h - 1 - i
                pygame.draw.line(glow, (cr, cg, cb, a), (0, y), (w-1, y))
        else:
            # нижняя колонна -> внутренний край "сверху"
            for i in range(band):
                a = int(ca * (1 - i / max(1, band)))
                pygame.draw.line(glow, (cr, cg, cb, a), (0, i), (w-1, i))
        glow.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        tex.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    _pillar_cache[key] = tex
    return tex

# -------------- ENTITIES --------------
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
        self.base_center = (self.base_img.get_width()/2.0, self.base_img.get_height()/2.0)
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
        self.x = float(x)
        self.gap_y = gap_y
        self.passed = False

    @property
    def top_rect(self): return pygame.Rect(int(self.x), 0, GATE_W, self.gap_y - GATE_GAP // 2)
    @property
    def bot_rect(self):
        by = self.gap_y + GATE_GAP // 2
        return pygame.Rect(int(self.x), by, GATE_W, H - by)

    def update(self, dt):
        self.x -= SCROLL_SPEED * dt

    def draw(self, surf, t, pillar_img):
        if pillar_img:
            # верхняя — перевёрнутая (flip=True)
            if self.top_rect.height > 0:
                tex = get_pillar_surface(pillar_img, self.top_rect.width, self.top_rect.height, flip=True)
                surf.blit(tex, self.top_rect.topleft)
            # нижняя — обычная
            if self.bot_rect.height > 0:
                tex = get_pillar_surface(pillar_img, self.bot_rect.width, self.bot_rect.height, flip=False)
                surf.blit(tex, self.bot_rect.topleft)
        else:
            # fallback (неоновый стиль)
            if self.top_rect.height > 0: draw_panel(surf, self.top_rect, t, radius=PILLAR_RADIUS)
            if self.bot_rect.height > 0: draw_panel(surf, self.bot_rect, t, radius=PILLAR_RADIUS)

# -------------- GAME --------------
def add_gate(gates, x):
    gap_y = random.randint(GATE_MIN + GATE_GAP // 2, GATE_MAX - GATE_GAP // 2)
    gates.append(Gate(x, gap_y))

def reset_game(ship_img):
    ship = Ship(ship_img)
    gates = []
    spawn = W + 120
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

# -------------- MAIN LOOP --------------
async def main():
    pygame.init()
    pygame.transform.set_smoothscale_backend("GENERIC")  # ровнее скейл в web
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("RIALO Space")
    clock = pygame.time.Clock()
    font_big = pygame.font.SysFont(None, 36, bold=True)
    font_small = pygame.font.SysFont(None, 24)

    # assets
    bg_img = load_image(BG_NAME)
    ship_img_raw = load_image(SHIP_NAME)
    if not ship_img_raw:
        raise SystemExit("assets/ship.png not found")
    ship_img = pygame.transform.smoothscale(ship_img_raw, SHIP_SIZE)
    pillar_img = load_image(PILLAR_IMG_NAME)  # опционально

    ship, gates, score, started, running = reset_game(ship_img)
    best = 0
    time_acc = 0.0

    while True:
        dt = clock.tick(FPS) / 1000.0
        time_acc += dt
        flap = False

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit(); return
                if e.key == pygame.K_r:
                    ship, gates, score, started, running = reset_game(ship_img)
                if e.key in (pygame.K_SPACE, pygame.K_UP): flap = True
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                flap = True

        if flap:
            if running:
                started = True
                ship.flap()
            else:
                ship, gates, score, started, running = reset_game(ship_img)

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

        # draw
        draw_background(screen, bg_img)
        for g in gates: g.draw(screen, time_acc, pillar_img)
        ship.draw(screen)
        draw_hud(screen, score, best, started, running, (font_big, font_small))

        pygame.display.flip()
        await asyncio.sleep(0)  # критично для web/pygbag

if __name__ == "__main__":
    asyncio.run(main())