#!/usr/bin/env python3
"""DGUS II 0#-style ASCII HZK: sizes N=4..64, glyph N x 2N, chars 0x00-0x7F, rows padded to bytes, MSB first."""
import math, sys
from PIL import Image

def offsets():
    off = 0; table = {}
    for n in range(4, 65):
        table[n] = off
        off += 128 * math.ceil(n / 8) * 2 * n
    return table, off

def glyph(d, n, ch):
    table, _ = offsets(); bpr = math.ceil(n / 8)
    base = table[n] + ch * bpr * 2 * n
    rows = []
    for y in range(2 * n):
        row = d[base + y * bpr: base + (y + 1) * bpr]
        v = int.from_bytes(row, 'big')
        rows.append([(v >> (bpr * 8 - 1 - x)) & 1 for x in range(n)])
    return rows

def sheet(d, n, path):
    im = Image.new('L', (16 * (n + 1), 8 * (2 * n + 1)), 128)
    for ch in range(128):
        g = glyph(d, n, ch)
        ox, oy = (ch % 16) * (n + 1), (ch // 16) * (2 * n + 1)
        for y, row in enumerate(g):
            for x, b in enumerate(row):
                im.putpixel((ox + x, oy + y), 0 if b else 255)
    im.save(path)

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    _, total = offsets(); assert len(d) == total, (len(d), total)
    for n in map(int, sys.argv[3:]):
        sheet(d, n, f'{sys.argv[2]}/asc_{n}x{2*n}.png')
