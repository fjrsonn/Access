#!/usr/bin/env python3
"""Gera a logo do executável (fundo preto, triângulo branco e letra A preta)."""
from __future__ import annotations

from pathlib import Path


SIZE = 512


def _draw_logo_image(size: int = SIZE):
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - erro tratado para uso em CLI
        raise RuntimeError(
            "Pillow não está instalado. Execute: python -m pip install pillow"
        ) from exc

    img = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Triângulo branco ao centro
    triangle = [
        (size * 0.50, size * 0.12),
        (size * 0.87, size * 0.84),
        (size * 0.13, size * 0.84),
    ]
    draw.polygon(triangle, fill=(255, 255, 255, 255))

    # Letra A preta sobre o triângulo
    stroke = max(20, int(size * 0.06))
    left = (size * 0.34, size * 0.76)
    top = (size * 0.50, size * 0.30)
    right = (size * 0.66, size * 0.76)
    bar_left = (size * 0.41, size * 0.56)
    bar_right = (size * 0.59, size * 0.56)

    draw.line([left, top], fill=(0, 0, 0, 255), width=stroke)
    draw.line([top, right], fill=(0, 0, 0, 255), width=stroke)
    draw.line([bar_left, bar_right], fill=(0, 0, 0, 255), width=stroke)

    return img


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    assets_dir = root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    img = _draw_logo_image(SIZE)
    png_path = assets_dir / "access_logo.png"
    ico_path = assets_dir / "access_logo.ico"

    img.save(png_path, format="PNG")
    img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    print(f"Logo PNG gerada em: {png_path}")
    print(f"Logo ICO gerada em: {ico_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
