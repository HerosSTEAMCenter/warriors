#!/usr/bin/env python3
"""
Pixel-art generator for "Warriors: Fireheart's Quest" (MakeCode Arcade).

Every cat in the game is drawn from ONE template so the whole cast shares the
same art style: same body shape, same 1px black outline, same animation poses.
The template is drawn in Fireheart's own colours; at runtime main.ts recolours
it into each Clan cat's coat.

Template colour roles (MakeCode palette index):
    f outline   4 base fur   e stripes   b spots   d light fur
    7 eyes      3 nose/ears  1 claws/teeth

Run:  python3 tools/make_art.py
It rewrites the GENERATED ART block inside main.ts and writes art_preview.png.
"""
import math
import pathlib
import random
import re
import struct
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

OUT, BASE, STRIPE, SPOT, LIGHT, EYE, PINK, CLAW = "f", "4", "e", "b", "d", "7", "3", "1"


# --------------------------------------------------------------------------- helpers
def blank(w, h):
    return [["."] * w for _ in range(h)]


def put(g, x, y, c):
    if 0 <= y < len(g) and 0 <= x < len(g[0]):
        g[y][x] = c


def get(g, x, y):
    if 0 <= y < len(g) and 0 <= x < len(g[0]):
        return g[y][x]
    return "."


def outline(g, col=OUT):
    """Give every filled shape a 1px outline (the shared art-style rule)."""
    h, w = len(g), len(g[0])
    res = [row[:] for row in g]
    for y in range(h):
        for x in range(w):
            if g[y][x] != ".":
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if get(g, x + dx, y + dy) != ".":
                    res[y][x] = col
                    break
    return res


def flip(g):
    return [row[::-1] for row in g]


# --------------------------------------------------------------------------- cats
CW, CH = 24, 16

TAIL_IDLE_A = [(3, 8), (2, 7), (2, 6), (1, 5), (1, 4), (2, 3)]
TAIL_IDLE_B = [(3, 8), (2, 7), (2, 6), (2, 5), (1, 4), (1, 3)]
TAIL_WALK_A = [(3, 8), (2, 7), (1, 6), (1, 5), (2, 4)]
TAIL_WALK_B = [(3, 8), (2, 8), (1, 7), (1, 6), (1, 5)]
TAIL_JUMP = [(3, 8), (2, 8), (1, 8), (1, 9)]
TAIL_ATTACK = [(3, 7), (3, 6), (2, 5), (2, 4), (1, 3), (1, 2)]

LEGS_STAND = [(5, 0, 0), (8, 0, 0), (14, 0, 0), (17, 0, 0)]


def cat(bob=0, head_dy=0, legs=LEGS_STAND, tail=TAIL_IDLE_A, eye_open=True,
        ears_flat=False, mouth=False, paw=None, claws=None):
    g = blank(CW, CH)

    # tail (behind the body), ringed with stripes
    for i, (x, y) in enumerate(tail):
        put(g, x, y + bob, STRIPE if i in (2, 4) else BASE)

    # legs: (x, dx, lifted) — 2px wide, bottom row offset by dx
    top = 12 + bob
    for (x, dx, lift) in legs:
        bottom = 13 if lift else 14
        n = bottom - top + 1
        for k, y in enumerate(range(top, bottom + 1)):
            off = math.floor(dx * (k + 1) / n + 0.5)
            put(g, x + off, y, BASE)
            put(g, x + off + 1, y, BASE)

    # body
    for y in range(7, 12):
        for x in range(4, 18):
            if (x, y) in ((4, 7), (4, 11)):
                continue
            put(g, x, y + bob, BASE)
    for x in range(7, 16):
        put(g, x, 11 + bob, LIGHT)                       # belly
    for (x, y) in ((16, 9), (17, 9), (16, 10), (17, 10), (15, 10)):
        put(g, x, y + bob, LIGHT)                        # chest
    for x, ys in ((6, (7, 8, 9)), (9, (7, 8, 9)), (12, (7, 8, 9)), (14, (7, 8))):
        for y in ys:
            put(g, x, y + bob, STRIPE)                   # tabby stripes
    for (x, y) in ((7, 10), (10, 9), (13, 10), (11, 7), (8, 8), (15, 8)):
        if get(g, x, y + bob) == BASE:
            put(g, x, y + bob, SPOT)                     # spots/rosettes

    # head
    hy = bob + head_dy
    for y in range(3, 9):
        for x in range(15, 23):
            if (x, y) in ((15, 3), (22, 3), (22, 8)):
                continue
            put(g, x, y + hy, BASE)
    if ears_flat:
        for (x, y) in ((14, 3), (15, 3), (16, 2), (19, 2), (20, 2)):
            put(g, x, y + hy, BASE)
    else:
        for (x, y) in ((16, 1), (16, 2), (17, 2), (21, 1), (20, 2), (21, 2)):
            put(g, x, y + hy, BASE)
        put(g, 16, 2 + hy, PINK)
        put(g, 21, 2 + hy, PINK)
    put(g, 17, 3 + hy, STRIPE)
    put(g, 19, 3 + hy, STRIPE)
    put(g, 16, 5 + hy, STRIPE)
    if eye_open:
        put(g, 20, 4 + hy, EYE)
        put(g, 20, 5 + hy, EYE)
    else:
        put(g, 19, 5 + hy, OUT)
        put(g, 20, 5 + hy, OUT)
    for (x, y) in ((21, 6), (20, 7), (21, 7), (22, 7), (19, 7)):
        put(g, x, y + hy, LIGHT)                         # muzzle
    put(g, 22, 5 + hy, PINK)                             # nose
    if mouth:
        put(g, 21, 7 + hy, OUT)
        put(g, 22, 7 + hy, CLAW)                         # fang

    g = outline(g)
    if paw:  # the swiping paw is its own outlined layer, drawn in front of the body
        pg = blank(CW, CH)
        for (x, y) in paw:
            put(pg, x, y, BASE)
        put(pg, paw[-1][0], paw[-1][1], LIGHT)
        pg = outline(pg)
        for y in range(CH):
            for x in range(CW):
                if pg[y][x] != ".":
                    g[y][x] = pg[y][x]
    if claws:
        for (x, y) in claws:
            put(g, x, y, CLAW)
    return g


def cat_frames():
    idle = [
        cat(tail=TAIL_IDLE_A),
        cat(tail=TAIL_IDLE_B),
        cat(tail=TAIL_IDLE_A),
        cat(tail=TAIL_IDLE_B, eye_open=False),
    ]
    walk = [
        cat(legs=[(5, -1, 0), (8, 1, 0), (14, -1, 0), (17, 1, 0)], tail=TAIL_WALK_A),
        cat(bob=-1, legs=[(5, 0, 1), (8, 0, 0), (14, 0, 0), (17, 0, 1)], tail=TAIL_WALK_B),
        cat(legs=[(5, 1, 0), (8, -1, 0), (14, 1, 0), (17, -1, 0)], tail=TAIL_WALK_A),
        cat(bob=-1, legs=[(5, 0, 0), (8, 0, 1), (14, 0, 1), (17, 0, 0)], tail=TAIL_WALK_B),
    ]
    jump = [
        cat(bob=-1, legs=[(5, -1, 0), (7, -1, 0), (15, 2, 1), (17, 2, 1)], tail=TAIL_JUMP,
            ears_flat=True),
    ]
    attack = [
        cat(bob=1, head_dy=1, tail=TAIL_ATTACK, ears_flat=True),
        cat(legs=[(5, -1, 0), (8, -1, 0), (14, 0, 0)], tail=TAIL_ATTACK, ears_flat=True,
            mouth=True,
            paw=[(17, 10), (18, 10), (19, 10), (19, 9), (20, 9), (21, 9), (20, 10), (21, 10), (22, 9)],
            claws=[(23, 8), (23, 9), (23, 10)]),
        cat(legs=[(5, -1, 0), (8, -1, 0), (14, 0, 0), (17, 2, 0)], tail=TAIL_ATTACK,
            mouth=True, claws=[(21, 15), (22, 14)]),
    ]
    hurt = [
        cat(legs=[(5, -1, 0), (8, -1, 0), (14, -1, 0), (17, -1, 0)], tail=TAIL_JUMP,
            eye_open=False, ears_flat=True, mouth=True),
    ]
    return {"IDLE": idle, "WALK": walk, "JUMP": jump, "ATTACK": attack, "HURT": hurt}


# --------------------------------------------------------------------------- prey
def mouse(step):
    g = blank(12, 8)
    for y in range(3, 7):
        for x in range(3, 10):
            if (x, y) in ((3, 3), (9, 6), (3, 6)):
                continue
            put(g, x, y, "e")
    for (x, y) in ((9, 3), (10, 4), (9, 4), (10, 5), (9, 5)):
        put(g, x, y, "e")
    put(g, 8, 2, "3")                                    # ear
    for x in range(4, 9):
        put(g, x, 6, "d")                                # belly
    legs = [(4, 7), (8, 7)] if step == 0 else [(5, 7), (7, 7)]
    for (x, y) in legs:
        put(g, x, y, "e")
    g = outline(g)
    put(g, 9, 3, "f")                                    # eye
    put(g, 11, 5, "3")                                   # nose
    tail = [(2, 5), (1, 4), (0, 3)] if step == 0 else [(2, 5), (1, 5), (0, 4)]
    for (x, y) in tail:
        put(g, x, y, "3")
    return g


# --------------------------------------------------------------------------- monster (car)
def monster(step):
    """A Twoleg monster driving LEFT. Body colour 'a' is swapped at runtime."""
    W, H = 40, 22
    g = blank(W, H)
    for y in range(9, 17):
        for x in range(1, 39):
            if (x, y) in ((1, 9), (38, 9), (1, 16), (38, 16)):
                continue
            put(g, x, y, "a")
    for y in range(3, 9):                                # cabin
        x0 = 11 - (y - 3)
        x1 = 28 + (y - 3) // 2
        for x in range(x0, x1 + 1):
            put(g, x, y, "a")
    for y in range(4, 9):                                # windows
        x0 = 12 - (y - 4)
        for x in range(x0, 19):
            put(g, x, y, "9")
        for x in range(21, 27):
            put(g, x, y, "9")
    put(g, 12, 4, "1")
    put(g, 11, 5, "1")
    for x in range(2, 38):
        put(g, x, 13, "c")                               # trim line
    put(g, 1, 10, "5"); put(g, 2, 10, "5"); put(g, 1, 11, "5"); put(g, 2, 11, "5")  # headlight
    put(g, 38, 10, "2"); put(g, 38, 11, "2")             # tail light
    g = outline(g)
    for cx in (9, 30):                                   # wheels
        for y in range(H):
            for x in range(W):
                d = (x - cx + 0.5) ** 2 + (y - 16.5) ** 2
                if d <= 20:
                    g[y][x] = "f"
                elif d <= 27 and g[y][x] == ".":
                    g[y][x] = "f"
        for (dx, dy) in ([(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)] if step == 0
                         else [(0, 0), (-1, -1), (1, 1), (1, -1), (-1, 1)]):
            g[16 + dy][cx + dx] = "b"
    return g


def warning_sign(step):
    g = blank(13, 12)
    for y in range(1, 11):
        half = (y - 1) * 6 // 9
        for x in range(6 - half, 7 + half):
            put(g, x, y, "5" if step == 0 else "4")
    for y in (3, 4, 5, 6, 7):
        put(g, 6, y, "f")
    put(g, 6, 9, "f")
    return outline(g, "2")


# --------------------------------------------------------------------------- tiles
def tile(seed):
    random.seed(seed)
    return blank(16, 16)


def speckle(g, rows, base, specks):
    for y in rows:
        for x in range(16):
            r = random.random()
            c = base
            acc = 0.0
            for col, p in specks:
                acc += p
                if r < acc:
                    c = col
                    break
            g[y][x] = c


def t_dirt(seed=1):
    g = tile(seed)
    speckle(g, range(16), "e", [("c", 0.10), ("d", 0.03), ("4", 0.02)])
    return g


def t_grass(seed=2):
    g = t_dirt(seed)
    for x in range(16):
        depth = 3 + random.choice([0, 0, 1, 2])
        for y in range(depth):
            g[y][x] = "7"
        g[depth][x] = "6"
        if random.random() < 0.35:
            g[0][x] = "."
    for x in range(16):
        if random.random() < 0.25:
            g[1][x] = "6"
    return g


def t_heather(seed=3):
    g = t_grass(seed)
    for _ in range(9):
        x, y = random.randrange(16), random.randrange(0, 3)
        if g[y][x] != ".":
            g[y][x] = random.choice("ab")
    return g


def t_rock_fill(seed=4):
    g = tile(seed)
    speckle(g, range(16), "b", [("c", 0.05), ("d", 0.04)])
    x, y = random.randrange(3, 13), 0
    while y < 16:                                        # crack
        g[y][x] = "c"
        y += 1
        x = max(0, min(15, x + random.choice([-1, 0, 1])))
    return g


def t_rock_top(seed=5):
    g = t_rock_fill(seed)
    for x in range(16):
        g[0][x] = "d"
        g[1][x] = "d" if random.random() < 0.6 else "b"
    g[0][0] = "."
    g[0][15] = "."
    return g


def t_water(seed, phase):
    g = tile(seed)
    speckle(g, range(16), "8", [("6", 0.04)])
    for y in range(0, 3):
        for x in range(16):
            g[y][x] = "."
    for x in range(16):
        wy = 3 + (1 if (x // 4 + phase) % 2 else 0)
        for y in range(3, wy):
            g[y][x] = "9"
        g[wy][x] = "9"
        if (x + phase * 2) % 8 == 0:
            g[wy + 2][x] = "1"
    for x in range(16):
        if (x + phase * 3) % 6 == 0:
            g[9][x] = "9"
    return g


def t_deep_water(seed=7):
    g = tile(seed)
    speckle(g, range(16), "8", [("6", 0.05), ("9", 0.01)])
    return g


def t_road_top(seed=8):
    g = tile(seed)
    speckle(g, range(16), "c", [("f", 0.08), ("b", 0.05)])
    for x in range(16):
        g[0][x] = "b"
        g[1][x] = "c"
    for x in range(3, 13):                               # yellow dashes
        g[5][x] = "5"
        g[6][x] = "5"
    return g


def t_road_fill(seed=9):
    g = tile(seed)
    speckle(g, range(16), "c", [("f", 0.12), ("b", 0.06), ("e", 0.05)])
    return g


def t_marsh_top(seed=10):
    g = tile(seed)
    speckle(g, range(16), "c", [("e", 0.12), ("f", 0.08), ("6", 0.04)])
    for x in range(16):
        h = random.choice([2, 3, 3, 4, 6])
        for y in range(h):
            g[y][x] = "6" if (x + y) % 3 else "7"
        if random.random() < 0.4:
            for y in range(0, max(0, h - 3)):
                g[y][x] = "."
    return g


def t_mud(seed=11):
    g = tile(seed)
    speckle(g, range(16), "c", [("e", 0.12), ("f", 0.10)])
    return g


def t_bramble(seed=12):
    g = tile(seed)
    for k in range(5):                                   # tangled stems
        x, y = random.randrange(16), 0
        dx = random.choice([-1, 1])
        while y < 16:
            g[y][x % 16] = "e"
            g[y][(x + 1) % 16] = "c"
            y += 1
            x += dx
            if random.random() < 0.25:
                dx = -dx
    for _ in range(14):
        x, y = random.randrange(16), random.randrange(16)
        g[y][x] = random.choice("67")
    for _ in range(6):
        x, y = random.randrange(16), random.randrange(16)
        if g[y][x] in "ec":
            g[y][(x + 1) % 16] = "1"                     # thorns
    for y in range(16):
        for x in range(16):
            if g[y][x] == "." and random.random() < 0.35:
                g[y][x] = "f"
    return g


def t_trunk(seed=13):
    g = tile(seed)
    for y in range(16):
        for x in range(5, 11):
            g[y][x] = "e"
        g[y][4] = "f"
        g[y][11] = "f"
        g[y][10] = "c"
        if random.random() < 0.4:
            g[y][random.randrange(6, 10)] = "c"
    return g


def t_leaves(seed=14):
    g = tile(seed)
    for y in range(16):
        for x in range(16):
            r = random.random()
            edge = min(x, y, 15 - x, 15 - y)
            if edge == 0 and r < 0.45:
                continue
            g[y][x] = "6" if r < 0.35 else ("7" if r < 0.93 else "5")
    return g


def t_fern(seed=15):
    g = tile(seed)
    for (bx, lean) in ((3, -1), (7, 1), (11, -1), (13, 1)):
        x = bx
        for y in range(15, 3 + (bx % 3), -1):
            put(g, x, y, "7")
            if y % 2 == 0:
                put(g, x - 1, y, "6")
                put(g, x + 1, y - 1, "7")
            if y % 4 == 0:
                x += lean
    return g


def t_star(phase):
    g = blank(16, 16)
    cx, cy = 7.5, 8.0
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = 7.5 if i % 2 == 0 else 3.2
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))

    def inside(px, py):
        c = False
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[i - 1]
            if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
                c = not c
        return c

    for y in range(16):
        for x in range(16):
            if inside(x + 0.5, y + 0.5):
                g[y][x] = "5" if phase == 0 else "1"
    for (x, y) in ((7, 7), (8, 7), (7, 8), (8, 8)):
        g[y][x] = "1" if phase == 0 else "5"
    g = outline(g, "9")
    if phase == 1:
        for (x, y) in ((1, 1), (14, 2), (2, 13)):
            put(g, x, y, "1")
    return g


TILES = [
    ("T_GRASS", t_grass()),
    ("T_DIRT", t_dirt()),
    ("T_HEATHER", t_heather()),
    ("T_ROCK_TOP", t_rock_top()),
    ("T_ROCK", t_rock_fill()),
    ("T_WATER_A", t_water(6, 0)),
    ("T_WATER_B", t_water(6, 1)),
    ("T_DEEP_WATER", t_deep_water()),
    ("T_ROAD_TOP", t_road_top()),
    ("T_ROAD", t_road_fill()),
    ("T_MARSH_TOP", t_marsh_top()),
    ("T_MUD", t_mud()),
    ("T_BRAMBLE", t_bramble()),
    ("T_TRUNK", t_trunk()),
    ("T_LEAVES", t_leaves()),
    ("T_FERN", t_fern()),
    ("T_STAR_A", t_star(0)),
    ("T_STAR_B", t_star(1)),
]


# --------------------------------------------------------------------------- output
def img_literal(g, indent="    "):
    rows = [indent + "    " + " ".join(r) for r in g]
    return "img`\n" + "\n".join(rows) + "\n" + indent + "`"


def ts_array(name, frames):
    body = ",\n".join("    " + img_literal(f) for f in frames)
    return f"const {name}: Image[] = [\n{body}\n]\n"


def build_ts():
    out = ["// Generated by tools/make_art.py — edit that script (or these images) to change the art.",
           "// Cat template colours: f outline, 4 fur, e stripes, b spots, d light fur, 7 eyes, 3 nose/ears, 1 claws",
           ""]
    for k, frames in cat_frames().items():
        out.append(ts_array("CAT_" + k, frames))
    out.append(ts_array("MOUSE_RUN", [mouse(0), mouse(1)]))
    out.append(ts_array("MONSTER_DRIVE", [monster(0), monster(1)]))
    out.append(ts_array("WARNING_SIGN", [warning_sign(0), warning_sign(1)]))
    for name, g in TILES:
        out.append(f"const {name} = {img_literal(g, '')}")
    return "\n".join(out) + "\n"


PALETTE = {
    ".": None, "0": None, "1": (255, 255, 255), "2": (255, 33, 33), "3": (255, 147, 196),
    "4": (255, 129, 53), "5": (255, 246, 9), "6": (36, 156, 163), "7": (120, 220, 82),
    "8": (0, 63, 173), "9": (135, 242, 255), "a": (142, 46, 196), "b": (164, 131, 159),
    "c": (92, 64, 108), "d": (229, 205, 196), "e": (145, 70, 61), "f": (0, 0, 0),
}


def write_png(path, sheets, scale=4):
    """Tiny PNG writer (no Pillow needed). sheets: list of rows of grids."""
    pad = 2
    width = max(sum(len(g[0]) + pad for g in row) for row in sheets)
    height = sum(max(len(g) for g in row) + pad for row in sheets)
    canvas = [[(60, 60, 70)] * width for _ in range(height)]
    y0 = 0
    for row in sheets:
        x0 = 0
        for g in row:
            for y, line in enumerate(g):
                for x, c in enumerate(line):
                    rgb = PALETTE[c]
                    if rgb:
                        canvas[y0 + y][x0 + x] = rgb
            x0 += len(g[0]) + pad
        y0 += max(len(g) for g in row) + pad
    raw = b""
    for y in range(height * scale):
        raw += b"\x00" + b"".join(bytes(canvas[y // scale][x // scale]) for x in range(width * scale))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def recolor(g, m):
    return [[m.get(c, c) for c in row] for row in g]


COATS = {  # mirrors the coats in main.ts (preview only)
    "Fireheart": {"b": "4"},
    "RiverClan": {"4": "b", "e": "c", "b": "b", "d": "1", "7": "5"},
    "Leopardfur": {"4": "5", "e": "5", "b": "e", "d": "1", "7": "7"},
    "WindClan": {"4": "d", "e": "e", "b": "d", "d": "1", "7": "5"},
    "ShadowClan": {"4": "c", "e": "f", "b": "c", "d": "b", "7": "5"},
    "Tigerstar": {"4": "e", "e": "f", "b": "e", "d": "d", "7": "4"},
}


def main():
    ts = build_ts()
    main_ts = ROOT / "main.ts"
    src = main_ts.read_text()
    new = re.sub(r"(// ===== BEGIN GENERATED ART =====\n).*?(// ===== END GENERATED ART =====)",
                 lambda m: m.group(1) + ts + m.group(2), src, flags=re.S)
    main_ts.write_text(new)

    frames = cat_frames()
    sheet = []
    for name, m in COATS.items():
        row = []
        for k in ("IDLE", "WALK", "JUMP", "ATTACK", "HURT"):
            row += [recolor(f, m) for f in frames[k]]
        sheet.append(row)
    sheet.append([mouse(0), mouse(1), monster(0), monster(1), warning_sign(0)])
    sheet.append([g for _, g in TILES])
    write_png(ROOT / "art_preview.png", sheet)
    print("art written to main.ts and art_preview.png")


if __name__ == "__main__":
    main()
