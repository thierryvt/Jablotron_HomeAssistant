"""Generate Jablotron integration brand assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "custom_components" / "jablotron" / "brand"

RED = (198, 40, 40, 255)
DARK_RED = (127, 29, 29, 255)
INK = (31, 41, 55, 255)
WHITE = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Return a readable Windows font."""
    candidates = (
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    )

    for candidate in candidates:
        path = Path(candidate)

        if path.exists():
            return ImageFont.truetype(str(path), size)

    return ImageFont.load_default()


def _draw_mark(draw: ImageDraw.ImageDraw, offset_x: int, offset_y: int, scale: float) -> None:
    """Draw a simple alarm shield and home mark."""
    def pt(x: int, y: int) -> tuple[int, int]:
        return (int(offset_x + x * scale), int(offset_y + y * scale))

    shield = [
        pt(128, 24),
        pt(216, 58),
        pt(202, 158),
        pt(128, 232),
        pt(54, 158),
        pt(40, 58),
    ]
    draw.polygon(shield, fill=RED)
    draw.line(shield + [shield[0]], fill=DARK_RED, width=max(2, int(8 * scale)))

    roof = [pt(78, 126), pt(128, 80), pt(178, 126)]
    draw.line(roof, fill=WHITE, width=max(2, int(16 * scale)), joint="curve")

    house = [pt(92, 126), pt(92, 174), pt(164, 174), pt(164, 126)]
    draw.line(house, fill=WHITE, width=max(2, int(14 * scale)))

    keypad = [pt(112, 140), pt(144, 174)]
    draw.rounded_rectangle(
        keypad,
        radius=max(2, int(5 * scale)),
        outline=WHITE,
        width=max(2, int(6 * scale)),
    )

    dot_radius = max(2, int(3 * scale))

    for x in (121, 135):
        for y in (150, 164):
            cx, cy = pt(x, y)
            draw.ellipse(
                (cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius),
                fill=WHITE,
            )


def generate_icon() -> None:
    """Generate icon.png."""
    image = Image.new("RGBA", (256, 256), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    _draw_mark(draw, 0, 0, 1.0)
    image.save(BRAND_DIR / "icon.png")


def generate_logo() -> None:
    """Generate logo.png."""
    image = Image.new("RGBA", (512, 128), TRANSPARENT)
    draw = ImageDraw.Draw(image)

    _draw_mark(draw, 12, 8, 0.44)

    title_font = _font(44, bold=True)
    subtitle_font = _font(19)

    draw.text((148, 30), "Jablotron", fill=INK, font=title_font)
    draw.text((151, 82), "Home Assistant", fill=RED, font=subtitle_font)

    image.save(BRAND_DIR / "logo.png")


def main() -> None:
    """Generate brand assets."""
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    generate_icon()
    generate_logo()


if __name__ == "__main__":
    main()
