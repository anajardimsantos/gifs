from __future__ import annotations

import math
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WIDTH = 960
HEIGHT = 540
FPS = 30
DURATION_SECONDS = 4
TOTAL_FRAMES = FPS * DURATION_SECONDS
OUTPUT_FILE = Path("we_are_tunisia_sticker_removal.mp4")

ALBUM_LEFT = 150
ALBUM_TOP = 75
ALBUM_WIDTH = 660
ALBUM_HEIGHT = 390

STICKER_W = 110
STICKER_H = 140
TARGET_X = 525
TARGET_Y = 220


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease_in_out(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def draw_background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), (24, 86, 102))
    draw = ImageDraw.Draw(image)

    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(28 + 22 * t)
        g = int(90 + 40 * t)
        b = int(106 + 42 * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    draw.rounded_rectangle(
        [ALBUM_LEFT, ALBUM_TOP, ALBUM_LEFT + ALBUM_WIDTH, ALBUM_TOP + ALBUM_HEIGHT],
        radius=24,
        fill=(245, 238, 218),
        outline=(146, 121, 88),
        width=4,
    )

    center_x = ALBUM_LEFT + ALBUM_WIDTH // 2
    draw.rectangle(
        [center_x - 6, ALBUM_TOP + 8, center_x + 6, ALBUM_TOP + ALBUM_HEIGHT - 8],
        fill=(214, 196, 162),
    )

    draw.text((ALBUM_LEFT + 200, ALBUM_TOP + 18), "We Are Tunisia", fill=(121, 33, 33))

    return image


def draw_sticker(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int]) -> None:
    draw.rounded_rectangle([x, y, x + STICKER_W, y + STICKER_H], radius=8, fill=color, outline=(70, 70, 70), width=2)
    draw.rectangle([x + 10, y + 12, x + STICKER_W - 10, y + 72], fill=(232, 232, 232))
    draw.ellipse([x + 40, y + 24, x + 70, y + 54], fill=(183, 151, 118))
    draw.rectangle([x + 42, y + 54, x + 68, y + 76], fill=(165, 42, 42))
    draw.rectangle([x + 25, y + 96, x + STICKER_W - 25, y + 104], fill=(255, 255, 255))


def build_static_album(target_visible: bool) -> Image.Image:
    image = draw_background()
    draw = ImageDraw.Draw(image)

    palette = [(216, 210, 244), (243, 224, 187), (204, 234, 214), (247, 203, 206), (199, 223, 241)]

    left_start_x = ALBUM_LEFT + 50
    right_start_x = ALBUM_LEFT + ALBUM_WIDTH // 2 + 35
    start_y = ALBUM_TOP + 90

    for row in range(2):
        for col in range(2):
            x = left_start_x + col * 145
            y = start_y + row * 160
            draw_sticker(draw, x, y, palette[(row * 2 + col) % len(palette)])

    positions = [
        (right_start_x, start_y),
        (right_start_x + 145, start_y),
        (right_start_x, start_y + 160),
        (right_start_x + 145, start_y + 160),
    ]

    for index, (x, y) in enumerate(positions):
        if x == TARGET_X and y == TARGET_Y and not target_visible:
            draw.rounded_rectangle([x, y, x + STICKER_W, y + STICKER_H], radius=8, fill=(238, 232, 214), outline=(185, 175, 151), width=2)
            continue
        draw_sticker(draw, x, y, palette[(index + 2) % len(palette)])

    return image


def build_target_sticker() -> Image.Image:
    sticker = Image.new("RGBA", (STICKER_W, STICKER_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sticker)
    draw_sticker(draw, 0, 0, (247, 203, 206))
    return sticker


def draw_hand(base: Image.Image, t: float, sticker_pos: tuple[float, float]) -> None:
    hand = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hand)

    if t < 0.15:
        blend = 0.0
    elif t < 0.45:
        blend = ease_in_out((t - 0.15) / 0.30)
    elif t < 0.85:
        blend = 1.0
    else:
        blend = max(0.0, 1.0 - (t - 0.85) / 0.15)

    if blend <= 0:
        return

    start_x, start_y = WIDTH + 40, 60
    target_x, target_y = sticker_pos[0] + 95, sticker_pos[1] + 38
    x = start_x + (target_x - start_x) * blend
    y = start_y + (target_y - start_y) * blend

    skin = (232, 189, 150, int(220 * blend))
    finger = (219, 176, 138, int(220 * blend))

    draw.ellipse([x - 65, y - 38, x + 45, y + 34], fill=skin)
    draw.ellipse([x - 18, y - 56, x + 24, y - 5], fill=finger)
    draw.ellipse([x + 8, y - 54, x + 50, y - 2], fill=finger)
    draw.ellipse([x + 30, y - 48, x + 70, y + 3], fill=finger)
    draw.ellipse([x - 50, y - 20, x - 12, y + 16], fill=finger)

    hand = hand.filter(ImageFilter.GaussianBlur(0.8))
    base.alpha_composite(hand)


def render_frame(index: int, target_sticker: Image.Image) -> Image.Image:
    t = index / (TOTAL_FRAMES - 1)

    peel = clamp((t - 0.42) / 0.18)
    pull = clamp((t - 0.55) / 0.35)

    sticker_attached = peel < 0.08
    frame = build_static_album(target_visible=sticker_attached).convert("RGBA")

    sticker_x = TARGET_X
    sticker_y = TARGET_Y

    if peel > 0.0:
        peel_eased = ease_in_out(peel)
        pull_eased = ease_in_out(pull)

        rotation = -18 * peel_eased - 28 * pull_eased
        offset_x = -110 * pull_eased
        offset_y = -95 * pull_eased - 18 * peel_eased

        moved_sticker = target_sticker.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
        shadow = Image.new("RGBA", moved_sticker.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rectangle([6, 6, moved_sticker.size[0] - 1, moved_sticker.size[1] - 1], fill=(0, 0, 0, 70))
        shadow = shadow.filter(ImageFilter.GaussianBlur(5))

        paste_x = int(sticker_x + offset_x)
        paste_y = int(sticker_y + offset_y)

        frame.alpha_composite(shadow, dest=(paste_x + 8, paste_y + 8))
        frame.alpha_composite(moved_sticker, dest=(paste_x, paste_y))

        if peel < 0.6:
            peel_size = int(18 + 22 * peel_eased)
            corner = [
                (sticker_x + STICKER_W - peel_size, sticker_y),
                (sticker_x + STICKER_W, sticker_y),
                (sticker_x + STICKER_W, sticker_y + peel_size),
            ]
            draw = ImageDraw.Draw(frame)
            draw.polygon(corner, fill=(255, 243, 224, 220))

    hand_pos = (sticker_x - 110 * ease_in_out(pull), sticker_y - 95 * ease_in_out(pull))
    draw_hand(frame, t, hand_pos)

    return frame.convert("RGB")


def create_video(output_path: Path = OUTPUT_FILE) -> None:
    target_sticker = build_target_sticker()
    writer = imageio.get_writer(output_path, fps=FPS, codec="libx264", quality=8, macro_block_size=None)

    try:
        for i in range(TOTAL_FRAMES):
            frame = render_frame(i, target_sticker)
            writer.append_data(np.asarray(frame))
    finally:
        writer.close()


if __name__ == "__main__":
    create_video()
    print(f"Vídeo gerado: {OUTPUT_FILE.resolve()}")
