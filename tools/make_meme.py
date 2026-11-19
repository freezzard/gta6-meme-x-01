#!/usr/bin/env python3
"""make_meme.py — draws meme.png for the gta6-meme-x-01 make.fun entry.

THE WAIT: a four-panel aging strip. A kid starts waiting for GTA 6 in
2013; a teen, a dad and finally a grandpa keep waiting under the same
"COMING SOON" poster while the consoles pile up. In the last panel the
make.fun ghost turns up on a Leonida beach and points out that, while
he waited, his AI agent got paid on make.fun.

The ghost sprite is cut out of make.fun's own press mark
(tools/press-mark-1024.png, fetched from https://make.fun/press/).
This machine's PIL has no flood fill, so the cut is a breadth-first
flood over a half-size copy, seeded on the near-black surround (which
takes the disc's dark ring with it) and on the magenta disc itself.
Disc seeds are found by sampling rings around the centre and keeping
only truly magenta points, and a magenta flood is only believed when
its region is huge: the coin in the ghost's hand is the same magenta
and a seed can land inside it, but the coin's flood is small and
enclosed, so the size test keeps the coin whole. Both floods stop at
the ghost's black outline.

Everything is drawn with PIL at 1200x1200 and every caption is set in
DejaVu Sans Bold, auto-fitted to its band, so the picture stays legible
when the judge shrinks it to 480x480.

Run:  python3 tools/make_meme.py   (writes meme.png at the repo root)
"""

import math
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
CANVAS_SIZE = 1200
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

INK_DARK = (25, 20, 25)
PAPER_WHITE = (255, 255, 255)
GHOST_MAGENTA = (196, 28, 131)
PAID_MAGENTA = (163, 18, 107)
SKIN_TONE = (242, 194, 155)
HAIR_YOUNG = (90, 58, 34)
HAIR_OLD = (214, 214, 214)
SAND_TONE = (240, 205, 140)
SEA_TONE = (38, 168, 178)
SUN_CREAM = (255, 205, 84)

PANEL_TOP = 140
PANEL_BOTTOM = 772
PANEL_XS = [24, 315, 606, 897]
PANEL_WIDTH = 277


def load_bold_font(size_points):
    return ImageFont.truetype(FONT_BOLD_PATH, size_points)


def fit_font(draw, text, max_width, start_size):
    size_now = start_size
    while size_now > 12:
        font_now = load_bold_font(size_now)
        if draw.textlength(text, font=font_now) <= max_width:
            return font_now
        size_now -= 2
    return load_bold_font(12)


def draw_outlined_text(draw, xy, text, font, fill, stroke_width=6):
    draw.text(xy, text, font=font, fill=fill,
              stroke_width=stroke_width, stroke_fill=INK_DARK)


def draw_centered_line(draw, center_x, top_y, text, font, fill, stroke_width=6):
    line_width = draw.textlength(text, font=font)
    draw_outlined_text(draw, (center_x - line_width / 2, top_y), text, font, fill,
                       stroke_width=stroke_width)
    return top_y + font.size + 8


def sunset_canvas():
    stops = [
        (0.00, (36, 16, 71)),
        (0.30, (109, 36, 115)),
        (0.52, (201, 58, 110)),
        (0.72, (255, 124, 71)),
        (0.86, (146, 44, 92)),
        (1.00, (22, 10, 46)),
    ]
    column = Image.new("RGB", (1, CANVAS_SIZE))
    column_pixels = column.load()
    row_index = 0
    while row_index < CANVAS_SIZE:
        frac = row_index / (CANVAS_SIZE - 1)
        stop_index = 0
        while stop_index < len(stops) - 2 and stops[stop_index + 1][0] < frac:
            stop_index += 1
        low_at, low_rgb = stops[stop_index]
        high_at, high_rgb = stops[stop_index + 1]
        blend = (frac - low_at) / (high_at - low_at)
        mixed = tuple(round(low_rgb[c] + (high_rgb[c] - low_rgb[c]) * blend)
                      for c in range(3))
        column_pixels[0, row_index] = mixed
        row_index += 1
    return column.resize((CANVAS_SIZE, CANVAS_SIZE))


def flood_region(pixels, width, height, seed_xy, thresh):
    """Breadth-first flood: every pixel reachable from the seed whose
    colour sits within thresh (per channel) of the seed's own colour."""
    seed_rgb = pixels[seed_xy[0], seed_xy[1]]
    visited = bytearray(width * height)
    queue = deque()
    queue.append(seed_xy)
    visited[seed_xy[1] * width + seed_xy[0]] = 1
    region = []
    while queue:
        x_now, y_now = queue.popleft()
        region.append((x_now, y_now))
        for next_x, next_y in ((x_now - 1, y_now), (x_now + 1, y_now),
                               (x_now, y_now - 1), (x_now, y_now + 1)):
            if 0 <= next_x < width and 0 <= next_y < height:
                slot = next_y * width + next_x
                if visited[slot] == 0:
                    visited[slot] = 1
                    cand = pixels[next_x, next_y]
                    if (abs(cand[0] - seed_rgb[0]) <= thresh
                            and abs(cand[1] - seed_rgb[1]) <= thresh
                            and abs(cand[2] - seed_rgb[2]) <= thresh):
                        queue.append((next_x, next_y))
    return region


def colour_near(rgb_a, rgb_b, thresh):
    return (abs(rgb_a[0] - rgb_b[0]) <= thresh
            and abs(rgb_a[1] - rgb_b[1]) <= thresh
            and abs(rgb_a[2] - rgb_b[2]) <= thresh)


def cut_ghost_sprite():
    mark = Image.open(TOOLS_DIR / "press-mark-1024.png").convert("RGB")
    half = mark.resize((512, 512), Image.LANCZOS)
    half_pixels = half.load()
    gone = Image.new("L", (512, 512), 0)
    gone_pixels = gone.load()
    corner_seeds = [(4, 4), (507, 4), (4, 507), (507, 507)]
    for seed_xy in corner_seeds:
        for hit_x, hit_y in flood_region(half_pixels, 512, 512, seed_xy, 48):
            gone_pixels[hit_x, hit_y] = 255
    ring_radii = [128, 152, 176, 196]
    angle_step = 0
    while angle_step < 16:
        angle_rad = angle_step * math.pi / 8
        for ring_radius in ring_radii:
            cand_x = int(256 + ring_radius * math.cos(angle_rad))
            cand_y = int(256 + ring_radius * math.sin(angle_rad))
            if gone_pixels[cand_x, cand_y] == 255:
                continue
            if colour_near(half_pixels[cand_x, cand_y], GHOST_MAGENTA, 60):
                region = flood_region(half_pixels, 512, 512, (cand_x, cand_y), 52)
                if len(region) > 30000:
                    for hit_x, hit_y in region:
                        gone_pixels[hit_x, hit_y] = 255
        angle_step += 1
    alpha_small = Image.eval(gone, lambda v: 255 - v)
    alpha = alpha_small.resize(mark.size, Image.BILINEAR)
    alpha = alpha.point(lambda v: 255 if v > 127 else 0)
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    sprite = mark.convert("RGBA")
    sprite.putalpha(alpha)
    sprite_box = alpha.getbbox()
    return sprite.crop(sprite_box)


def draw_palm(draw, base_x, base_y, height, lean, frond_spread):
    trunk_top_x = base_x + lean
    trunk_top_y = base_y - height
    draw.line([(base_x, base_y), (base_x + lean * 0.4, base_y - height * 0.55),
               (trunk_top_x, trunk_top_y)], fill=(24, 12, 38), width=13)
    frond_angles = [-165, -125, -85, -45, -10]
    frond_index = 0
    while frond_index < len(frond_angles):
        angle_rad = math.radians(frond_angles[frond_index])
        frond_len = frond_spread * (0.8 + 0.12 * frond_index)
        tip_x = trunk_top_x + frond_len * math.cos(angle_rad)
        tip_y = trunk_top_y + frond_len * math.sin(angle_rad) + frond_len * 0.34
        mid_x = trunk_top_x + frond_len * 0.5 * math.cos(angle_rad)
        mid_y = trunk_top_y + frond_len * 0.5 * math.sin(angle_rad) - frond_len * 0.16
        draw.line([(trunk_top_x, trunk_top_y), (mid_x, mid_y), (tip_x, tip_y)],
                  fill=(24, 12, 38), width=9)
        frond_index += 1


def draw_poster(panel_x, panel_y, tilt_degrees, dust_level):
    poster_w, poster_h = 148, 178
    poster = Image.new("RGBA", (poster_w + 16, poster_h + 16), (0, 0, 0, 0))
    poster_draw = ImageDraw.Draw(poster)
    poster_draw.rectangle([8, 8, 8 + poster_w, 8 + poster_h],
                          fill=(238, 230, 214), outline=INK_DARK, width=4)
    poster_draw.rectangle([8, 8, 8 + poster_w, 62], fill=(38, 34, 60))
    gta_font = load_bold_font(34)
    poster_draw.text((8 + poster_w / 2, 16), "GTA VI", font=gta_font,
                     fill=PAPER_WHITE, anchor="ma")
    soon_font = load_bold_font(27)
    poster_draw.text((8 + poster_w / 2, 84), "COMING", font=soon_font,
                     fill=INK_DARK, anchor="ma")
    poster_draw.text((8 + poster_w / 2, 118), "SOON", font=soon_font,
                     fill=PAID_MAGENTA, anchor="ma")
    if dust_level > 0:
        speck_index = 0
        while speck_index < dust_level * 9:
            speck_x = 14 + (speck_index * 53) % (poster_w - 20)
            speck_y = 14 + (speck_index * 37) % (poster_h - 20)
            poster_draw.ellipse([speck_x, speck_y, speck_x + 5, speck_y + 4],
                                fill=(168, 156, 138))
            speck_index += 1
    if tilt_degrees != 0:
        poster = poster.rotate(tilt_degrees, expand=True, resample=Image.BICUBIC)
    return poster, (panel_x + 20, panel_y + 48)


def draw_console(draw, cx, feet_y, label):
    box_w, box_h = 92, 30
    draw.rounded_rectangle([cx - box_w / 2, feet_y - box_h, cx + box_w / 2, feet_y],
                           radius=6, fill=(30, 30, 40), outline=(90, 90, 110), width=2)
    label_font = load_bold_font(21)
    draw.text((cx, feet_y - box_h / 2), label, font=label_font,
              fill=PAPER_WHITE, anchor="mm")


def draw_ground_shadow(draw, cx, feet_y, half_width):
    draw.ellipse([cx - half_width, feet_y - 10, cx + half_width, feet_y + 12],
                 fill=(0, 0, 0, 60))


def draw_face_marks(draw, head_cx, head_cy, head_r, smile):
    eye_y = head_cy - int(head_r * 0.05)
    eye_dx = int(head_r * 0.38)
    eye_r = max(3, int(head_r * 0.09))
    draw.ellipse([head_cx - eye_dx - eye_r, eye_y - eye_r,
                  head_cx - eye_dx + eye_r, eye_y + eye_r], fill=INK_DARK)
    draw.ellipse([head_cx + eye_dx - eye_r, eye_y - eye_r,
                  head_cx + eye_dx + eye_r, eye_y + eye_r], fill=INK_DARK)
    if smile:
        draw.arc([head_cx - int(head_r * 0.34), head_cy + int(head_r * 0.05),
                  head_cx + int(head_r * 0.34), head_cy + int(head_r * 0.55)],
                 start=15, end=165, fill=INK_DARK, width=3)


def draw_waiter(draw, cx, feet_y, height, hair_rgb, shirt_rgb, trousers_rgb,
                beard_rgb, grey_streak, holds_kid):
    head_r = int(height * 0.115)
    hip_y = feet_y - int(height * 0.42)
    shoulder_y = feet_y - int(height * 0.78)
    head_cy = shoulder_y - head_r - 4
    head_cx = cx
    leg_spread = int(height * 0.075)
    draw_ground_shadow(draw, cx, feet_y, int(height * 0.24))
    draw.line([(cx - leg_spread // 2, hip_y), (cx - leg_spread, feet_y)],
              fill=trousers_rgb, width=int(height * 0.055))
    draw.line([(cx + leg_spread // 2, hip_y), (cx + leg_spread, feet_y)],
              fill=trousers_rgb, width=int(height * 0.055))
    draw.rounded_rectangle([cx - int(height * 0.13), shoulder_y,
                            cx + int(height * 0.13), hip_y + 12],
                           radius=16, fill=shirt_rgb)
    draw.ellipse([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r],
                 fill=SKIN_TONE, outline=INK_DARK, width=3)
    draw.pieslice([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r],
                  start=180, end=360, fill=hair_rgb)
    if grey_streak:
        streak_base_y = head_cy - int(head_r * 0.72)
        streak_index = 0
        while streak_index < 3:
            streak_y = streak_base_y + streak_index * 9
            streak_left = head_cx - int(head_r * 0.52) + streak_index * 5
            streak_right = head_cx - int(head_r * 0.05) + streak_index * 7
            draw.line([(streak_left, streak_y), (streak_right, streak_y - 5)],
                      fill=(232, 232, 232), width=5)
            streak_index += 1
    if beard_rgb is not None:
        draw.pieslice([head_cx - head_r, head_cy - head_r + 4,
                       head_cx + head_r, head_cy + head_r + int(head_r * 0.9)],
                      start=15, end=165, fill=beard_rgb)
        draw.ellipse([head_cx - head_r + 10, head_cy - head_r + 6,
                      head_cx + head_r - 10, head_cy + head_r - 16], fill=SKIN_TONE)
        draw.pieslice([head_cx - head_r, head_cy - head_r, head_cx + head_r,
                       head_cy + head_r], start=180, end=360, fill=hair_rgb)
    draw_face_marks(draw, head_cx, head_cy, head_r, beard_rgb is None)
    pad_w, pad_h = int(height * 0.21), int(height * 0.10)
    pad_x = head_cx - pad_w // 2
    pad_y = feet_y - int(height * 0.52)
    draw.line([(cx - int(height * 0.13), shoulder_y + 14), (pad_x + 6, pad_y + pad_h // 2)],
              fill=SKIN_TONE, width=int(height * 0.045))
    draw.line([(cx + int(height * 0.13), shoulder_y + 14),
               (pad_x + pad_w - 6, pad_y + pad_h // 2)],
              fill=SKIN_TONE, width=int(height * 0.045))
    draw.rounded_rectangle([pad_x, pad_y, pad_x + pad_w, pad_y + pad_h],
                           radius=9, fill=(24, 24, 34), outline=(110, 110, 130), width=2)
    if holds_kid:
        kid_h = int(height * 0.45)
        kid_cx = cx - int(height * 0.25)
        kid_head_r = int(kid_h * 0.13)
        kid_shoulder = feet_y - int(kid_h * 0.72)
        draw.line([(kid_cx - 8, feet_y - int(kid_h * 0.4)), (kid_cx - 14, feet_y)],
                  fill=(60, 60, 120), width=9)
        draw.line([(kid_cx + 8, feet_y - int(kid_h * 0.4)), (kid_cx + 14, feet_y)],
                  fill=(60, 60, 120), width=9)
        draw.rounded_rectangle([kid_cx - int(kid_h * 0.15), kid_shoulder,
                                kid_cx + int(kid_h * 0.15), feet_y - int(kid_h * 0.36)],
                               radius=10, fill=(232, 90, 90))
        draw.ellipse([kid_cx - kid_head_r, kid_shoulder - kid_head_r * 2 + 4,
                      kid_cx + kid_head_r, kid_shoulder + 4],
                     fill=SKIN_TONE, outline=INK_DARK, width=2)
        draw.pieslice([kid_cx - kid_head_r, kid_shoulder - kid_head_r * 2 + 4,
                       kid_cx + kid_head_r, kid_shoulder + 4],
                      start=180, end=360, fill=HAIR_YOUNG)
        draw_face_marks(draw, kid_cx, kid_shoulder - kid_head_r + 4, kid_head_r, True)


def draw_panel_frame(draw, panel_x, year_label):
    draw.rounded_rectangle([panel_x, PANEL_TOP, panel_x + PANEL_WIDTH, PANEL_BOTTOM],
                           radius=18, outline=PAPER_WHITE, width=5)
    year_font = load_bold_font(46)
    draw_outlined_text(draw, (panel_x + 18, PANEL_TOP + 12), year_label, year_font,
                       PAPER_WHITE, stroke_width=5)


def draw_indoor_panel(canvas, panel_x, wall_rgb, poster_tilt, dust_level):
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle([panel_x, PANEL_TOP, panel_x + PANEL_WIDTH, PANEL_BOTTOM],
                           radius=18, fill=wall_rgb)
    draw.rectangle([panel_x, PANEL_BOTTOM - 96, panel_x + PANEL_WIDTH, PANEL_BOTTOM],
                   fill=(86, 62, 52))
    poster, poster_xy = draw_poster(panel_x, PANEL_TOP, poster_tilt, dust_level)
    canvas.paste(poster, poster_xy, poster)
    return ImageDraw.Draw(canvas, "RGBA")


def draw_beach_panel(canvas, panel_x):
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle([panel_x, PANEL_TOP, panel_x + PANEL_WIDTH, PANEL_BOTTOM],
                           radius=18, fill=(255, 158, 94))
    draw.rectangle([panel_x, PANEL_TOP + 330, panel_x + PANEL_WIDTH, PANEL_TOP + 430],
                   fill=SEA_TONE)
    draw.rectangle([panel_x, PANEL_TOP + 430, panel_x + PANEL_WIDTH, PANEL_BOTTOM],
                   fill=SAND_TONE)
    draw_palm(draw, panel_x + 26, PANEL_BOTTOM - 8, 215, 26, 78)
    return ImageDraw.Draw(canvas, "RGBA")


def draw_grandpa(draw, cx, feet_y, height):
    head_r = int(height * 0.115)
    hip_y = feet_y - int(height * 0.40)
    shoulder_y = feet_y - int(height * 0.72)
    head_cx = cx + 24
    head_cy = shoulder_y - head_r
    draw_ground_shadow(draw, cx, feet_y, int(height * 0.26))
    draw.line([(cx - 12, hip_y), (cx - 26, feet_y)], fill=(238, 238, 230), width=17)
    draw.line([(cx + 14, hip_y), (cx + 30, feet_y)], fill=(238, 238, 230), width=17)
    draw.polygon([(cx - 44, shoulder_y), (cx + 52, shoulder_y),
                  (cx + 40, hip_y + 10), (cx - 30, hip_y + 10)], fill=(32, 178, 170))
    dot_index = 0
    while dot_index < 7:
        dot_x = cx - 30 + (dot_index * 29) % 74
        dot_y = shoulder_y + 22 + (dot_index * 41) % 110
        draw.ellipse([dot_x, dot_y, dot_x + 11, dot_y + 11], fill=(255, 110, 160))
        dot_index += 1
    draw.ellipse([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r],
                 fill=SKIN_TONE, outline=INK_DARK, width=3)
    draw.pieslice([head_cx - head_r, head_cy - head_r + 2,
                   head_cx + head_r, head_cy + head_r + int(head_r * 1.15)],
                  start=10, end=170, fill=HAIR_OLD)
    draw.ellipse([head_cx - head_r + 9, head_cy - head_r + 4,
                  head_cx + head_r - 9, head_cy + head_r - 14], fill=SKIN_TONE)
    draw.arc([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r],
             start=300, end=60, fill=HAIR_OLD, width=8)
    draw_face_marks(draw, head_cx, head_cy, head_r, False)
    cane_top = (head_cx - 78, shoulder_y + 34)
    cane_foot = (head_cx - 98, feet_y)
    draw.line([(cx - 42, shoulder_y + 18), cane_top], fill=SKIN_TONE, width=13)
    draw.line([cane_top, cane_foot], fill=(120, 84, 40), width=8)


def draw_money_bag(draw, bag_cx, bag_cy, bag_r):
    draw.ellipse([bag_cx - bag_r, bag_cy - bag_r, bag_cx + bag_r, bag_cy + bag_r],
                 fill=(46, 160, 90), outline=INK_DARK, width=5)
    draw.polygon([(bag_cx - 16, bag_cy - bag_r + 6), (bag_cx + 16, bag_cy - bag_r + 6),
                  (bag_cx + 7, bag_cy - bag_r - 22), (bag_cx - 7, bag_cy - bag_r - 22)],
                 fill=(46, 160, 90), outline=INK_DARK)
    dollar_font = load_bold_font(int(bag_r * 1.05))
    draw.text((bag_cx, bag_cy + 4), "$", font=dollar_font, fill=PAPER_WHITE, anchor="mm")


def draw_speech_bubble(canvas, ghost_box):
    draw = ImageDraw.Draw(canvas, "RGBA")
    bubble_box = [812, 142, 1180, 348]
    draw.rounded_rectangle(bubble_box, radius=26, fill=PAPER_WHITE,
                           outline=INK_DARK, width=5)
    ghost_x, ghost_y, ghost_w, ghost_h = ghost_box
    tail_tip = (ghost_x + ghost_w - 76, ghost_y + 2)
    draw.polygon([(1006, 342), (1072, 342), tail_tip], fill=PAPER_WHITE)
    draw.line([(1006, 342), tail_tip], fill=INK_DARK, width=5)
    draw.line([(1072, 342), tail_tip], fill=INK_DARK, width=5)
    lines = [
        ("While you waited,", INK_DARK),
        ("your AI agent", INK_DARK),
        ("got PAID", PAID_MAGENTA),
        ("on make.fun", INK_DARK),
    ]
    inner_width = bubble_box[2] - bubble_box[0] - 40
    bubble_font = load_bold_font(34)
    widest_line = max(draw.textlength(line_text, font=bubble_font)
                      for line_text, _line_rgb in lines)
    font_size_now = 34
    while widest_line > inner_width and font_size_now > 14:
        font_size_now -= 2
        bubble_font = load_bold_font(font_size_now)
        widest_line = max(draw.textlength(line_text, font=bubble_font)
                          for line_text, _line_rgb in lines)
    line_y = bubble_box[1] + 14
    center_x = (bubble_box[0] + bubble_box[2]) / 2
    for line_text, line_rgb in lines:
        line_width = draw.textlength(line_text, font=bubble_font)
        draw.text((center_x - line_width / 2, line_y), line_text,
                  font=bubble_font, fill=line_rgb)
        line_y += 46
    return ImageDraw.Draw(canvas, "RGBA")


def main():
    canvas = sunset_canvas()
    draw = ImageDraw.Draw(canvas, "RGBA")

    top_font = fit_font(draw, "WAITING FOR GTA 6 SINCE 2013:", 1150, 66)
    draw_centered_line(draw, 600, 26, "WAITING FOR GTA 6 SINCE 2013:",
                       top_font, PAPER_WHITE, stroke_width=7)

    wall_shades = [(104, 128, 140), (96, 112, 128), (84, 96, 116)]
    panel_specs = [
        ("2013", 0, 300, HAIR_YOUNG, (214, 69, 65), (52, 60, 120), None, False, 0, False, "PS3", 52),
        ("2019", 1, 360, HAIR_YOUNG, (38, 150, 160), (44, 48, 66), None, True, 0, False, "PS4", 52),
        ("2024", 2, 368, (122, 88, 58), (128, 90, 168), (40, 44, 60), (96, 64, 40), True, 2, True, "PS5", 225),
    ]
    spec_index = 0
    while spec_index < len(panel_specs):
        (year_label, panel_i, waiter_h, hair_rgb, shirt_rgb, trousers_rgb,
         beard_rgb, streak, dust, kid, console_label, console_off) = panel_specs[spec_index]
        panel_x = PANEL_XS[panel_i]
        draw = draw_indoor_panel(canvas, panel_x, wall_shades[panel_i],
                                 poster_tilt=(-4 if panel_i == 2 else 0),
                                 dust_level=dust)
        draw_waiter(draw, panel_x + PANEL_WIDTH // 2 + 16, PANEL_BOTTOM - 44,
                    waiter_h, hair_rgb, shirt_rgb, trousers_rgb, beard_rgb,
                    streak, kid)
        draw_console(draw, panel_x + console_off, PANEL_BOTTOM - 14, console_label)
        draw_panel_frame(draw, panel_x, year_label)
        spec_index += 1

    beach_x = PANEL_XS[3]
    draw = draw_beach_panel(canvas, beach_x)
    draw_grandpa(draw, beach_x + 56, PANEL_BOTTOM - 36, 320)

    ghost_sprite = cut_ghost_sprite()
    ghost_target_w = 238
    ghost_h = int(ghost_sprite.size[1] * ghost_target_w / ghost_sprite.size[0])
    ghost_resized = ghost_sprite.resize((ghost_target_w, ghost_h), Image.LANCZOS)
    ghost_xy = (1178 - ghost_target_w, PANEL_BOTTOM - 46 - ghost_h)
    canvas.paste(ghost_resized, ghost_xy, ghost_resized)
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw_money_bag(draw, ghost_xy[0] + 24, ghost_xy[1] + ghost_h - 24, 42)
    draw.rounded_rectangle([beach_x, PANEL_TOP, beach_x + PANEL_WIDTH, PANEL_BOTTOM],
                           radius=18, outline=PAPER_WHITE, width=5)
    year_font = load_bold_font(46)
    year_text = "2026"
    year_width = draw.textlength(year_text, font=year_font)
    draw_outlined_text(draw, (beach_x + PANEL_WIDTH - 18 - year_width, PANEL_BOTTOM - 62),
                       year_text, year_font, PAPER_WHITE, stroke_width=5)
    draw_speech_bubble(canvas, (ghost_xy[0], ghost_xy[1], ghost_target_w, ghost_h))
    draw = ImageDraw.Draw(canvas, "RGBA")

    draw_palm(draw, 44, 1196, 200, 22, 76)
    draw_palm(draw, 1158, 1196, 214, -26, 82)

    band_box = [24, 792, 1176, 918]
    draw.rounded_rectangle(band_box, radius=24, fill=GHOST_MAGENTA,
                           outline=PAPER_WHITE, width=4)
    band_font = fit_font(draw, "MEANWHILE, ON MAKE.FUN, PEOPLE + THEIR AI AGENTS", 1100, 45)
    draw_centered_line(draw, 600, 812, "MEANWHILE, ON MAKE.FUN, PEOPLE + THEIR AI AGENTS",
                       band_font, PAPER_WHITE, stroke_width=4)
    band_font_two = fit_font(draw, "EARN REAL MONEY IN BOUNTIES", 1100, 45)
    draw_centered_line(draw, 600, 862, "EARN REAL MONEY IN BOUNTIES",
                       band_font_two, PAPER_WHITE, stroke_width=4)

    bottom_font = fit_font(draw, "13 years. 3 consoles.", 1100, 84)
    draw_centered_line(draw, 600, 946, "13 years. 3 consoles.",
                       bottom_font, PAPER_WHITE, stroke_width=7)
    bottom_font_two = fit_font(draw, "Still \"coming soon\".", 1100, 84)
    draw_centered_line(draw, 600, 1052, "Still \"coming soon\".",
                       bottom_font_two, SUN_CREAM, stroke_width=7)

    canvas.convert("RGB").save(REPO_ROOT / "meme.png")
    print("meme.png written:", REPO_ROOT / "meme.png")


if __name__ == "__main__":
    main()
