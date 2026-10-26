#!/usr/bin/env python
# Generates the Living Chess app icon: a gold chess king on a dark stone, gold-ringed tile.
import os
from PIL import Image, ImageDraw, ImageOps, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "icons")
os.makedirs(OUT, exist_ok=True)
S = 1024
CX = S // 2

GOLD      = (232, 197, 106)
GOLD_HI   = (247, 227, 165)
GOLD_LO   = (176, 134, 60)
RING      = (201, 162, 75)

def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m

# ---- background: radial stone gradient (warm, lighter centre -> near-black edge)
grad = Image.radial_gradient("L").resize((S, S))              # 0 at centre, 255 at edge
bg = ImageOps.colorize(grad, black=(60, 53, 44), white=(17, 14, 10)).convert("RGB")
img = bg

# ---- gold ring border
ring_w = 26
ImageDraw.Draw(img).rounded_rectangle([ring_w // 2, ring_w // 2, S - ring_w // 2, S - ring_w // 2],
                                      radius=190, outline=RING, width=ring_w)

# ---- the king, drawn on its own layer then gold-shaded
king = Image.new("L", (S, S), 0)
k = ImageDraw.Draw(king)

def rrect(d, box, r, fill=255):
    d.rounded_rectangle(box, radius=r, fill=fill)

# cross on top
k.rounded_rectangle([CX - 26, 150, CX + 26, 330], radius=18, fill=255)   # vertical bar
k.rounded_rectangle([CX - 95, 205, CX + 95, 262], radius=24, fill=255)   # horizontal bar
# crown band (wide, with three rounded merlons via the band + body)
# head / neck under the cross
k.ellipse([CX - 70, 318, CX + 70, 452], fill=255)
# crown: a trapezoidal band
k.polygon([(CX - 150, 560), (CX + 150, 560), (CX + 120, 430), (CX - 120, 430)], fill=255)
k.rounded_rectangle([CX - 162, 548, CX + 162, 612], radius=26, fill=255)  # crown base slab
# body: hourglass goblet
k.polygon([(CX - 150, 612), (CX + 150, 612),
           (CX + 70, 720), (CX + 110, 860),
           (CX - 110, 860), (CX - 70, 720)], fill=255)
# base: two stacked rounded slabs
k.rounded_rectangle([CX - 150, 846, CX + 150, 905], radius=26, fill=255)
k.rounded_rectangle([CX - 196, 898, CX + 196, 968], radius=30, fill=255)

# soften edges a touch
king = king.filter(ImageFilter.GaussianBlur(1.2))

# vertical gold gradient for the king fill (highlight at top -> deep gold at bottom)
col = Image.new("RGB", (S, S))
cp = col.load()
for y in range(S):
    t = y / (S - 1)
    r = int(GOLD_HI[0] * (1 - t) + GOLD_LO[0] * t)
    g = int(GOLD_HI[1] * (1 - t) + GOLD_LO[1] * t)
    b = int(GOLD_HI[2] * (1 - t) + GOLD_LO[2] * t)
    for x in range(S):
        cp[x, y] = (r, g, b)

# drop shadow for depth
shadow = king.filter(ImageFilter.GaussianBlur(14))
sh_img = Image.new("RGB", (S, S), (0, 0, 0))
img = Image.composite(Image.blend(img, sh_img, 0.55), img, shadow.point(lambda v: int(v * 0.6)))
# paint the king
img = Image.composite(col, img, king)

# ---- round the tile corners (transparent outside) for the non-maskable icons
def finish(radius):
    out = img.copy().convert("RGBA")
    out.putalpha(rounded_mask(S, radius))
    return out

tile = finish(190)

sizes = {"icon-512.png": 512, "icon-192.png": 192, "icon-180.png": 180, "icon-32.png": 32}
for name, sz in sizes.items():
    tile.resize((sz, sz), Image.LANCZOS).save(os.path.join(OUT, name))

# maskable icon: full-bleed square (no rounded corners, extra safe padding) so Android can mask it
maskable = img.copy().convert("RGBA")
maskable.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "icon-maskable-512.png"))

# favicon.ico (multi-size)
tile.resize((48, 48), Image.LANCZOS).save(os.path.join(OUT, "favicon.ico"),
                                          sizes=[(16, 16), (32, 32), (48, 48)])
print("icons written to", OUT, sorted(os.listdir(OUT)))
