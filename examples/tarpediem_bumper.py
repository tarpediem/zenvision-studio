"""Bumper TarpeDiem pour le ZenVision — 256x64, gris, ~3,4 s.

Chorégraphie du bumper royisal (fondu de l'emblème, séparateur, révélation du
logo, balayage lumineux, fondu), montée avec les vrais assets d'Olivier :

  - l'emblème  : ~/.local/share/omarchy-branding/skull-albator.jpg
  - le logo    : le lettrage TARPEDIEM de ~/.config/omarchy/branding/screensaver.txt

Le screensaver est écrit en demi-blocs Unicode (█ ▀ ▄), donc chaque cellule vaut
exactement deux pixels verticaux : on le reconstitue en bitmap sans rien
réinterpréter, plutôt que de re-typographier le nom dans une autre police.
"""
import io
import sys

from PIL import Image

W, H, S = 256, 64, 4
SKULL = "/home/tarpediem/.local/share/omarchy-branding/skull-albator.jpg"
BRANDING = "/home/tarpediem/.config/omarchy/branding/screensaver.txt"
LOGO_LINES = (21, 31)          # bornes du lettrage dans screensaver.txt

N_FRAMES = 68
DUR = 50

LVL_LOGO = 165
LVL_SEP = 70


def halfblocks_to_bitmap(lines):
    """Demi-blocs Unicode -> bitmap 1 colonne x 2 pixels par cellule."""
    top = {"█": 1, "▀": 1}      # █ ▀
    bot = {"█": 1, "▄": 1}      # █ ▄
    w = max(len(l) for l in lines)
    im = Image.new("L", (w, len(lines) * 2), 0)
    px = im.load()
    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            if top.get(ch):
                px[c, r * 2] = 255
            if bot.get(ch):
                px[c, r * 2 + 1] = 255
    return im.crop(im.getbbox())


def load_logo():
    lines = io.open(BRANDING, encoding="utf-8").read().split("\n")
    return halfblocks_to_bitmap(lines[LOGO_LINES[0]:LOGO_LINES[1]])


def load_emblem(target):
    im = Image.open(SKULL).convert("L")
    # le JPEG laisse un fond « presque noir » et des bords sales : on reseuille
    im = im.point(lambda v: 255 if v > 110 else 0)
    im = im.crop(im.getbbox())
    r = target / max(im.width, im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


EMBLEM = load_emblem(int(H * 0.94))
LOGO_SRC = load_logo()

EM_X = 3
EM_Y = (H - EMBLEM.height) // 2
SEP_X = EM_X + EMBLEM.width + 7
LOGO_X0 = SEP_X + 8
LOGO_W = W - 8 - LOGO_X0
LOGO = LOGO_SRC.resize((LOGO_W, max(1, int(LOGO_SRC.height * LOGO_W / LOGO_SRC.width))),
                       Image.LANCZOS)
LOGO_Y = (H - LOGO.height) // 2


def frame(i):
    im = Image.new("L", (W, H), 0)

    # 1. l'emblème
    if i >= 4:
        im.paste(EMBLEM, (EM_X, EM_Y))
    # 2. le séparateur se déploie
    if i >= 14:
        g = min(1.0, (i - 14) / 5)
        half = int(H * 0.34 * g)
        for y in range(H // 2 - half, H // 2 + half):
            im.putpixel((SEP_X, y), LVL_SEP)
    # 3. le logo se révèle de gauche à droite — le pendant de la frappe
    if i >= 20:
        g = min(1.0, (i - 20) / 18)
        cut = int(LOGO.width * g)
        if cut:
            part = LOGO.crop((0, 0, cut, LOGO.height))
            dim = part.point(lambda v: int(v * LVL_LOGO / 255))
            im.paste(dim, (LOGO_X0, LOGO_Y), part)

    # 4. balayage lumineux
    if 42 <= i <= 58:
        t = (i - 42) / 16
        xc = -40 + t * (W + 80)
        px = im.load()
        for x in range(W):
            gain = 1 + 1.6 * pow(2.718, -((x - xc) / 20.0) ** 2)
            if gain > 1.01:
                for y in range(H):
                    v = px[x, y]
                    if v:
                        px[x, y] = min(255, int(v * gain))

    # 5. fondus
    fade = 1.0
    if i < 12:
        fade = max(0.0, (i - 3) / 9)
    if i >= 60:
        fade = max(0.0, 1 - (i - 60) / 8)
    if fade < 1.0:
        im = im.point(lambda v: int(v * fade))
    return im


out_dir = sys.argv[1]
frames = [frame(i) for i in range(N_FRAMES)]
frames[0].save(f"{out_dir}/tarpediem-bumper.gif", save_all=True,
               append_images=frames[1:], duration=DUR, loop=0, optimize=False)
frames[59].save(f"{out_dir}/tarpediem-still.png")
print(f"emblème {EMBLEM.size}, logo {LOGO.size} (source {LOGO_SRC.size}), {len(frames)} frames")
