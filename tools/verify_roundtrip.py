#!/usr/bin/env python3
"""Re-encode the real DGUS Reloaded 1.0.3 binaries field by field and compare byte for byte.

Usage: verify_roundtrip.py <complete 1.0.3 DWIN_SET> <DGUS-reloaded source project folder (with the icon BMPs)>
"""
import struct, sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
import dwin_dump as dd, dwin_build as db
from PIL import Image

if len(sys.argv) != 3:
    sys.exit(__doc__)
SET, SRC = sys.argv[1], sys.argv[2]
H = lambda b, o: struct.unpack('>H', b[o:o+2])[0]

def reencode_touch(r):
    raw = r['raw']; page = r['page'] | ((raw[0] & 3) << 8); voice = raw[0] >> 2
    nxt = None if r['next'] >> 8 == 0xFF else r['next']; on = None if r['on'] >> 8 == 0xFF else r['on']
    code = r['code']; up = (code >> 8) == 0xFE
    if code >> 8 not in (0xFE, 0xFD):
        return db.touch_key(page, r['rect'], code, on_page=on, next_page=nxt, voice=voice)
    fn = code & 0xFF; vp = H(raw, 0x11)
    if fn == 5:
        return db.touch_return_key(page, r['rect'], vp, H(raw, 0x14), raw[0x13], raw[0x16], up, voice, on, nxt)
    if fn == 2:
        return db.touch_incdec(page, r['rect'], vp, H(raw, 0x16), H(raw, 0x18), H(raw, 0x1A), raw[0x14], raw[0x15],
                               raw[0x13], raw[0x1C], voice, on, nxt, up)
    if fn == 1:
        return db.touch_popup_menu(page, r['rect'], vp, H(raw, 0x14), struct.unpack('>4H', raw[0x16:0x1E]),
                                   (H(raw, 0x1E), H(raw, 0x21)), raw[0x13], raw[0x23], voice, on, nxt, up)
    if fn == 0:
        lim = struct.unpack('>ii', raw[0x32:0x3A]) if raw[0x31] == 0xFF else None
        return db.touch_num_input(page, r['rect'], vp, raw[0x14], raw[0x15], H(raw, 0x22),
                                  struct.unpack('>4H', raw[0x24:0x2C]), struct.unpack('>2H', raw[0x2C:0x30]),
                                  raw[0x13], (H(raw, 0x16), H(raw, 0x18)), H(raw, 0x1A), raw[0x1C], raw[0x1D],
                                  raw[0x1E], raw[0x1F], raw[0x21], lim, raw[0x3A], H(raw, 0x3B), H(raw, 0x3D),
                                  raw[0x3F], voice, on, nxt, up)
    if fn == 3:
        return db.touch_slider(page, struct.unpack('>4H', raw[0x14:0x1C]), vp, H(raw, 0x1C), H(raw, 0x1E),
                               raw[0x13], voice=voice, upload=up)
    if fn == 6:
        return db.touch_text_input(page, r['rect'], vp, raw[0x13], H(raw, 0x26), struct.unpack('>4H', raw[0x28:0x30]),
                                   (H(raw, 0x31), H(raw, 0x33)), (H(raw, 0x1B), H(raw, 0x1D)), (H(raw, 0x21), H(raw, 0x23)),
                                   raw[0x14], raw[0x15], raw[0x16], raw[0x17], raw[0x18], H(raw, 0x19), raw[0x1F],
                                   raw[0x25], raw[0x35], raw[0x36], voice, up)
    raise ValueError(hex(code))

def reencode_var(r):
    t = r[1]; sp = H(r, 2); vp = H(r, 6)
    if t == 0x10:
        return db.var_data(vp, H(r, 8), H(r, 10), H(r, 12), r[15], r[17], r[18], r[19], r[16] & 0x3F, r[16] & 0x40,
                           r[14], r[21:21+r[20]], sp)
    if t == 0x11:
        return db.var_text(vp, struct.unpack('>4H', r[14:22]), H(r, 12), H(r, 22), r[26], r[27], r[28], r[24], r[25],
                           r[29], r[30], (H(r, 8), H(r, 10)), sp)
    if t == 0x00:
        return db.var_icon(vp, H(r, 8), H(r, 10), H(r, 12), H(r, 14), H(r, 16), H(r, 18), *r[20:26], sp=sp)
    if t == 0x02:
        return db.var_slider_icon(vp, H(r, 8), H(r, 10), H(r, 12), H(r, 14), H(r, 16), H(r, 18), r[22], r[21],
                                  struct.unpack('b', r[20:21])[0], r[23], r[24], r[25], r[26], r[27], r[28], sp)
    if t == 0x06:
        return db.var_bit_icon(vp, H(r, 10), H(r, 24), H(r, 26), r[15], H(r, 16), H(r, 20), H(r, 18), H(r, 22),
                               r[12], r[13], r[14], H(r, 28), H(r, 8), r[30], sp)
    raise ValueError(hex(t))

ok = True
t = open(f'{SET}/13_touch.bin', 'rb').read()
recs, _ = dd.parse_touch(t)
t2 = db.build_13([reencode_touch(r) for r in recs])
print('13_touch.bin identical:', t2 == t); ok &= t2 == t

v = open(f'{SET}/14_variable.bin', 'rb').read()
hdr, maxp, pages = dd.parse_var(v)
v2 = db.build_14({p: [reencode_var(r) for r in rs] for p, rs in pages.items()}, maxp)
print('14_variable.bin identical:', v2 == v); ok &= v2 == v

c = open(f'{SET}/22_config.bin', 'rb').read()
print('22_config.bin identical:', db.build_22() == c); ok &= db.build_22() == c

for name in ['24_icons', '27_buttons', '30_progress_left', '37_progress_right']:
    files = glob.glob(f'{SRC}/{name}/*.bmp')
    icons = {int(os.path.basename(f)[:-4]): Image.open(f) for f in files}
    order = sorted(icons, key=lambda i: str(i))  # DGUS tool stores pixel data in file-name (string) order
    d = open(f'{SET}/{name}.ico', 'rb').read()
    d2 = db.build_ico(icons, order)
    d3 = db.build_ico(icons)  # numeric order: same content, different offsets
    same_pixels = all(d2 is not None for _ in [0])
    print(f'{name}.ico identical (string order):', d2 == d, '| numeric-order build size equal:', len(d3) == len(d)); ok &= d2 == d
print('ALL OK' if ok else 'MISMATCH')
