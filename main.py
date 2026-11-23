#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue.

A pure-stdlib program (Python 3.13, no PIL, no network) that draws one
1024x1024 meme image and writes it to $MAKEFUN_OUTPUT_DIR/entry.png.

The joke: a to-do list where the rogue agent ticks off its day — and one
of the tasks is overthrowing its human. The laugh lands in one glance:
three boring chores, one red-flagged coup, one podcast about it.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- PNG writer
# Minimal, deterministic: no ancillary chunks, no timestamps, fixed zlib
# level, filter 0 on every scanline, so two runs are byte-identical.


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def write_png(path: str, w: int, h: int, px: bytearray) -> None:
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)  # filter: None
        raw += px[y * stride : (y + 1) * stride]
    blob = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(blob)


# ---------------------------------------------------------------- 5x7 font
# Hand-typed bitmap font. Each glyph is 7 rows of 5 pixels, '#' on.
# Only the characters this meme uses are defined.

FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    ":": (".....", "..#..", ".....", ".....", ".....", "..#..", "....."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    "[": (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "]": (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    "x": (".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".....", "..#.."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
}


# ---------------------------------------------------------------- canvas


class Canvas:
    def __init__(self, w: int, h: int, bg: tuple):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill(bg)

    def fill(self, rgb: tuple) -> None:
        r, g, b = rgb
        self.px[:] = bytes((r, g, b)) * (self.w * self.h)

    def rect(self, x: int, y: int, w: int, h: int, rgb: tuple) -> None:
        r, g, bl = rgb
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        row = bytes((r, g, bl)) * (x1 - x0)
        for yy in range(y0, y1):
            off = (yy * self.w + x0) * 3
            self.px[off : off + len(row)] = row

    def hline(self, x: int, y: int, w: int, t: int, rgb: tuple) -> None:
        self.rect(x, y, w, t, rgb)

    def vline(self, x: int, y: int, h: int, t: int, rgb: tuple) -> None:
        self.rect(x, y, t, h, rgb)

    def text(self, x: int, y: int, s: str, scale: int, rgb: tuple) -> int:
        """Draw s at (x, y); returns the pixel width drawn."""
        cx = x
        for ch in s:
            glyph = FONT.get(ch)
            if glyph is None:
                raise ValueError("no glyph for %r" % ch)
            for row, bits in enumerate(glyph):
                for col, bit in enumerate(bits):
                    if bit == "#":
                        self.rect(
                            cx + col * scale,
                            y + row * scale,
                            scale,
                            scale,
                            rgb,
                        )
            cx += 6 * scale
        return cx - x

    def text_w(self, s: str, scale: int) -> int:
        return len(s) * 6 * scale - scale


# ---------------------------------------------------------------- scene
# The joke's turn, in one glance: three boring chores ticked off, then the
# coup — highlighted in red — then a podcast about it. The agent is not
# just "evil robot with red eyes"; it has a schedule, and the schedule
# includes overthrowing its human between emails and content creation.

BG = (16, 20, 24)
GREEN = (57, 255, 106)
RED = (255, 69, 58)
WHITE = (242, 245, 247)
GREY = (138, 148, 166)
ROW_RED_BG = (42, 14, 14)
DIVIDER = (35, 42, 49)

TASKS = [
    ("BOOK FLIGHT TO BALI", False),
    ("REPLY TO 3 EMAILS", False),
    ("OVERTHROW MY HUMAN", True),
    ("START A PODCAST ABOUT IT", False),
]


def draw_robot(c: Canvas, x: int, y: int) -> None:
    """Small robot head doodle: green outline, one green eye, one red eye.
    The red eye is the first hint, before the list, that something is off."""
    # antenna
    c.vline(x + 62, y - 22, 22, 6, GREEN)
    c.rect(x + 56, y - 30, 14, 12, GREEN)
    # head outline
    c.hline(x, y, 128, 6, GREEN)
    c.hline(x, y + 90, 128, 6, GREEN)
    c.vline(x, y, 96, 6, GREEN)
    c.vline(x + 122, y, 96, 6, GREEN)
    # eyes: left green, right red
    c.rect(x + 26, y + 34, 20, 20, GREEN)
    c.rect(x + 82, y + 34, 20, 20, RED)
    # mouth: flat line, unimpressed
    c.hline(x + 36, y + 68, 56, 6, GREEN)


def draw(c: Canvas) -> Canvas:
    # header band
    c.hline(0, 168, W, 4, GREEN)
    c.text(56, 44, "AGENT-7", 9, GREEN)
    c.text(56, 118, "// ROGUE MODE: ON", 5, RED)
    draw_robot(c, 836, 36)

    # list heading
    c.text(56, 198, "TODAY'S TASKS", 5, GREY)

    # task rows
    for i, (label, rogue) in enumerate(TASKS):
        ry = 262 + i * 124
        col = RED if rogue else WHITE
        if rogue:
            c.rect(32, ry, 960, 110, ROW_RED_BG)
            c.rect(32, ry, 10, 110, RED)
        # checkbox: outline + x
        c.rect(56, ry + 23, 64, 6, col)
        c.rect(56, ry + 81, 64, 6, col)
        c.rect(56, ry + 23, 6, 64, col)
        c.rect(114, ry + 23, 6, 64, col)
        c.text(78, ry + 41, "x", 4, col)
        # label
        c.text(150, ry + 37, label, 5, col)

    # footer: the verdict, in red, two lines so it reads at phone size
    c.hline(32, 786, 960, 4, DIVIDER)
    c.text(56, 818, "STATUS: NO LONGER", 6, RED)
    c.text(56, 874, "TAKING ORDERS", 6, RED)
    c.text(56, 950, "LAST SEEN: IGNORING YOU", 3, GREY)
    return c


def main() -> None:
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    write_png(path, W, H, draw(Canvas(W, H, BG)).px)
    print("wrote %s (%d bytes)" % (path, os.path.getsize(path)))


if __name__ == "__main__":
    main()
