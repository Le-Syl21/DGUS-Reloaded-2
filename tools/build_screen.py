#!/usr/bin/env python3
"""DGUS Reloaded 2.0 for DWIN T5UID1 480x272 touchscreens: generate a complete DWIN_SET from Python.

Works with Marlin's DGUS_LCD_UI RELOADED: every page keeps its VPs, its display formats and its touch controls
in the same order (Marlin enables and disables controls by their index within a page).

  - dark theme, teal accent, every label drawn with Noto Sans into the pictures and icons;
  - 16 languages: each translated label is a row of icons in 44_text.ico, and VP 0x4024 (DGUS_Addr::LANGUAGE,
    saved by Marlin) holds the language, so a label shows icon base + language;
  - popups use pictograms (check, cross, pause, play), so they need no translation;
  - new page 23, filament sensor: runout on/off, jam detection on/off and jam length.

Usage: build_screen.py [out_dir]     (default: build/)
"""
import os, shutil, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
import dwin_build as db, dwin_dump as dd, hzk_asc as hz
from strings import S, LANGS
from screen_kit import (HERE, REF, W, H, BG, BAR, CARD, CARD2, LINE, FIELD, FIELD_LINE, TEXT, MUTED, ICON, ACC, ACC_ON,
                        OK, WARN, WHITE, LANG_VP, TEXT_LIB, STYLES, NLANG, font, rgb, c565, glyph, text, TL, Page)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build')
VERSION = '2.0.0'
BACK = (0, 0, 39, 39)
# Copied unchanged from DGUS Reloaded 1.0.3: ASCII font, sounds, screen config and T5 OS files.
BASE_FILES = ['0_DWIN_ASC.HZK', '01_boot.wav', '02_click.wav', '03_notification.wav', 'T5UID1.CFG', 'T5UID1_V30.BIN',
              'T5OS_V21_NOACK.BIN']
Hh = lambda b, o: struct.unpack('>H', b[o:o + 2])[0]


# ------------------------------------------------------------------------------------------ record re-encoding
def decode_var(r):
    t = r[1]
    base = dict(vp=Hh(r, 6), sp=Hh(r, 2))
    if t == 0x10:
        return dict(base, kind='data', x=Hh(r, 8), y=Hh(r, 10), color=Hh(r, 12), lib=r[14], font_x=r[15], align=r[16] & 0x3F,
                    zero_flag=r[16] & 0x40, n_int=r[17], n_dot=r[18], v_type=r[19], unit=r[21:21 + r[20]])
    if t == 0x11:
        return dict(base, kind='text', pos=(Hh(r, 8), Hh(r, 10)), color=Hh(r, 12), box=struct.unpack('>4H', r[14:22]),
                    length=Hh(r, 22), font0=r[24], font1=r[25], font_x=r[26], font_y=r[27], encode=r[28], hdis=r[29], vdis=r[30])
    if t == 0x00:
        return dict(base, kind='icon', x=Hh(r, 8), y=Hh(r, 10), v_min=Hh(r, 12), v_max=Hh(r, 14), icon_min=Hh(r, 16), icon_max=Hh(r, 18),
                    lib=r[20], mode=r[21], layer=r[22], icon_gamma=r[23], pic_gamma=r[24], filt=r[25])
    if t == 0x02:
        return dict(base, kind='slider', v_begin=Hh(r, 8), v_end=Hh(r, 10), pos_begin=Hh(r, 12), pos_end=Hh(r, 14), icon=Hh(r, 16),
                    cross=Hh(r, 18), x_adj=struct.unpack('b', r[20:21])[0], vertical=r[21], lib=r[22], icon_mode=r[23], vp_mode=r[24],
                    layer=r[25], icon_gamma=r[26], pic_gamma=r[27], filt=r[28])
    if t == 0x06:
        return dict(base, kind='bit', vp_aux=Hh(r, 8), act_bits=Hh(r, 10), disp_mode=r[12], move_mode=r[13], icon_mode=r[14], lib=r[15],
                    icon0s=Hh(r, 16), icon0e=Hh(r, 18), icon1s=Hh(r, 20), icon1e=Hh(r, 22), x=Hh(r, 24), y=Hh(r, 26), dis_mov=Hh(r, 28), filt=r[30])
    raise ValueError(hex(t))


def encode_var(f):
    k = f['kind']
    if k == 'data':
        return db.var_data(f['vp'], f['x'], f['y'], f['color'], f['font_x'], f['n_int'], f['n_dot'], f['v_type'], f['align'],
                           f['zero_flag'], f['lib'], f['unit'], f['sp'])
    if k == 'text':
        return db.var_text(f['vp'], f['box'], f['color'], f['length'], f['font_x'], f['font_y'], f['encode'], f['font0'], f['font1'],
                           f['hdis'], f['vdis'], f['pos'], f['sp'])
    if k == 'icon':
        return db.var_icon(f['vp'], f['x'], f['y'], f['v_min'], f['v_max'], f['icon_min'], f['icon_max'], f['lib'], f['mode'],
                           f['layer'], f['icon_gamma'], f['pic_gamma'], f['filt'], f['sp'])
    if k == 'slider':
        return db.var_slider_icon(f['vp'], f['v_begin'], f['v_end'], f['pos_begin'], f['pos_end'], f['icon'], f['cross'], f['lib'],
                                  f['vertical'], f['x_adj'], f['icon_mode'], f['vp_mode'], f['layer'], f['icon_gamma'], f['pic_gamma'],
                                  f['filt'], f['sp'])
    if k == 'bit':
        return db.var_bit_icon(f['vp'], f['act_bits'], f['x'], f['y'], f['lib'], f['icon0s'], f['icon1s'], f['icon0e'], f['icon1e'],
                               f['disp_mode'], f['move_mode'], f['icon_mode'], f['dis_mov'], f['vp_aux'], f['filt'], f['sp'])


def chars(f):
    return f['n_int'] + (1 + f['n_dot'] if f['n_dot'] else 0) + (1 if f['v_type'] in (1, 2, 3) else 0)


class P2(Page):
    """A page that re-uses the original page's records."""

    def __init__(self, pid, name, orig_vars, orig_touch, *a, **kw):
        self.ov = orig_vars.get(pid, [])
        self.ot = orig_touch.get(pid, [])
        super().__init__(pid, name, *a, **kw)
        if self.vars and self.ov and decode_var(self.ov[0])['vp'] == 0x3000:
            pass  # the title bar already re-created the status text

    def var(self, i, **over):
        f = decode_var(self.ov[i])
        f.update(over)
        if f['kind'] == 'text' and 'box' in over and 'pos' not in over:
            f['pos'] = over['box'][:2]
        self.vars.append(encode_var(f))
        return f

    def value(self, i, cx, cy, fx=None, color=TEXT, **over):
        """Numeric display i centred on (cx, cy)."""
        f = decode_var(self.ov[i])
        f.update(over)
        if fx:
            f['font_x'] = fx
        n = chars(f) * f['font_x']
        f.update(x=int(cx - n / 2), y=int(cy - f['font_x']), align=2, color=c565(color))
        self.vars.append(encode_var(f))
        return f

    def value_at(self, i, x, y, fx=None, color=TEXT, align=0, **over):
        f = decode_var(self.ov[i])
        f.update(over)
        if fx:
            f['font_x'] = fx
        f.update(x=int(x), y=int(y), align=align, color=c565(color))
        self.vars.append(encode_var(f))
        return f

    def value_unit(self, i, r, fx, unit, typical=None, color=TEXT, rec=None):
        """Number followed by its unit in the screen font (no gap), centred in r for a typical number width."""
        f = decode_var(rec) if rec else decode_var(self.ov[i])
        f['font_x'] = fx
        f['unit'] = unit.encode()
        n = (typical if typical is not None else chars(f)) + len(unit)
        f.update(x=int((r[0] + r[2]) / 2 - n * fx / 2), y=int((r[1] + r[3]) / 2 - fx), align=0, color=c565(color))
        self.vars.append(encode_var(f))
        return f

    def value_in(self, i, r, fx=None, color=TEXT):
        return self.value(i, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, fx, color)

    def t(self, i, rect=None):
        raw = self.ot[i]
        if rect is None:
            return raw
        code = Hh(raw, 14)
        fn, up = code & 0xFF, code >> 8
        if fn == 0x03 and up in (0xFE, 0xFD):
            vp, mode = Hh(raw, 0x11), raw[0x13]
            return db.touch_slider(self.pid, rect, vp, Hh(raw, 0x1C), Hh(raw, 0x1E), mode, voice=raw[0] >> 2, upload=up == 0xFE)
        b = bytearray(raw)
        b[2:10] = struct.pack('>4H', *rect)
        if fn == 0x00 and up in (0xFE, 0xFD):
            b[0x1A:0x1C] = struct.pack('>H', c565(TEXT))
        if fn == 0x06 and up in (0xFE, 0xFD):
            b[0x19:0x1B] = struct.pack('>H', c565(TEXT))
        return bytes(b)

    def temp_block(self, x, y, label_key, icon, cur_i, tgt_i, bg, big=14, small=8):
        self.glyph(icon, 15, MUTED, x - 1, y + 1)
        self.label(label_key, x + 18, y - 1, 'label', bg, maxw=None if bg != CARD2 else 188)
        vy = y + 20
        self.value_at(cur_i, x, vy, big, TEXT, 1, zero_flag=0)
        ux = x + chars(decode_var(self.ov[cur_i])) * big + 4
        self.text('°C', ux, vy + 5, 'num')
        self.text('/', ux + 23, vy + 8, 'numsmall')
        self.value_at(tgt_i, ux + 33, vy + 6, small, MUTED, 1)
        self.text('°C', ux + 33 + 3 * small + 3, vy + 8, 'numsmall')


import math


def _star(d, cx, cy, r, color, rot=-90):
    pts = []
    for i in range(10):
        a = math.radians(rot + i * 36)
        rr = r if i % 2 == 0 else r * 0.4
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=color)


def _country(code):
    """Country flag at 96 x 64 (drawn large, then scaled down)."""
    W_, H_ = 96, 64
    im = Image.new('RGB', (W_, H_), (255, 255, 255))
    d = ImageDraw.Draw(im)
    def h_stripes(*cols):
        n = len(cols)
        for i, c in enumerate(cols):
            d.rectangle((0, i * H_ // n, W_, (i + 1) * H_ // n), fill=c)
    def v_stripes(*cols):
        n = len(cols)
        for i, c in enumerate(cols):
            d.rectangle((i * W_ // n, 0, (i + 1) * W_ // n, H_), fill=c)
    if code == 'fr': v_stripes((0, 85, 164), (255, 255, 255), (239, 65, 53))
    elif code == 'it': v_stripes((0, 146, 70), (255, 255, 255), (206, 43, 55))
    elif code == 'de': h_stripes((0, 0, 0), (221, 0, 0), (255, 206, 0))
    elif code == 'nl': h_stripes((174, 28, 40), (255, 255, 255), (33, 70, 139))
    elif code == 'pl': h_stripes((255, 255, 255), (220, 20, 60))
    elif code == 'ru': h_stripes((255, 255, 255), (0, 57, 166), (213, 43, 30))
    elif code == 'id': h_stripes((206, 17, 38), (255, 255, 255))
    elif code == 'es':
        h_stripes((170, 21, 27), (241, 191, 0), (241, 191, 0), (170, 21, 27))
    elif code == 'mx':
        v_stripes((0, 104, 71), (255, 255, 255), (206, 17, 38))
        d.ellipse((40, 24, 56, 40), fill=(120, 80, 40))
    elif code == 'pt':
        d.rectangle((0, 0, W_, H_), fill=(255, 0, 0)); d.rectangle((0, 0, 38, H_), fill=(0, 102, 0))
        d.ellipse((26, 20, 50, 44), fill=(255, 255, 0)); d.ellipse((32, 26, 44, 38), fill=(255, 0, 0))
    elif code == 'br':
        d.rectangle((0, 0, W_, H_), fill=(0, 156, 59))
        d.polygon([(8, 32), (48, 6), (88, 32), (48, 58)], fill=(255, 223, 0))
        d.ellipse((32, 16, 64, 48), fill=(0, 39, 118))
    elif code == 'gb':
        d.rectangle((0, 0, W_, H_), fill=(1, 33, 105))
        d.line((0, 0, W_, H_), fill=(255, 255, 255), width=12); d.line((0, H_, W_, 0), fill=(255, 255, 255), width=12)
        d.line((0, 0, W_, H_), fill=(200, 16, 46), width=4); d.line((0, H_, W_, 0), fill=(200, 16, 46), width=4)
        d.rectangle((38, 0, 58, H_), fill=(255, 255, 255)); d.rectangle((0, 22, W_, 42), fill=(255, 255, 255))
        d.rectangle((42, 0, 54, H_), fill=(200, 16, 46)); d.rectangle((0, 26, W_, 38), fill=(200, 16, 46))
    elif code == 'us':
        for i in range(13):
            d.rectangle((0, i * H_ / 13, W_, (i + 1) * H_ / 13), fill=(178, 34, 52) if i % 2 == 0 else (255, 255, 255))
        d.rectangle((0, 0, 40, 34), fill=(60, 59, 110))
        for r in range(4):
            for c in range(5):
                d.ellipse((4 + c * 8 - 1.5, 5 + r * 8 - 1.5, 4 + c * 8 + 1.5, 5 + r * 8 + 1.5), fill=(255, 255, 255))
    elif code == 'tr':
        d.rectangle((0, 0, W_, H_), fill=(227, 10, 23))
        d.ellipse((18, 14, 54, 50), fill=(255, 255, 255)); d.ellipse((26, 18, 56, 46), fill=(227, 10, 23))
        _star(d, 60, 32, 9, (255, 255, 255), rot=180)
    elif code == 'ar':   # Arabic language flag (public domain): black, green, white stripes, red hoist triangle
        h_stripes((0, 0, 0), (0, 122, 61), (255, 255, 255))
        d.polygon([(0, 0), (32, 32), (0, 64)], fill=(206, 17, 38))
    elif code == 'hi':
        h_stripes((255, 153, 51), (255, 255, 255), (19, 136, 8))
        d.ellipse((38, 22, 58, 42), outline=(0, 0, 128), width=3)
        d.ellipse((46, 30, 50, 34), fill=(0, 0, 128))
    elif code == 'zh':
        d.rectangle((0, 0, W_, H_), fill=(238, 28, 37))
        _star(d, 16, 16, 10, (255, 255, 0))
        for (x, y) in ((32, 6), (38, 13), (38, 23), (32, 29)):
            _star(d, x, y, 3.5, (255, 255, 0))
    elif code == 'ja':
        d.ellipse((29, 13, 67, 51), fill=(188, 0, 45))
    elif code == 'ko':
        d.pieslice((32, 16, 64, 48), 180, 360, fill=(205, 46, 58)); d.pieslice((32, 16, 64, 48), 0, 180, fill=(0, 71, 160))
        d.ellipse((32, 24, 48, 40), fill=(205, 46, 58)); d.ellipse((48, 24, 64, 40), fill=(0, 71, 160))
        for (x, y) in ((14, 12), (82, 12), (14, 52), (82, 52)):
            for k in range(3):
                d.line((x - 7, y - 4 + k * 4, x + 7, y - 4 + k * 4), fill=(0, 0, 0), width=2)
    return im


FLAG_OF = {'en': ('gb', 'us'), 'es': ('es', 'mx'), 'pt': ('pt', 'br')}


def flag(lang, bg):
    """24 x 16 flag for a language, on its background colour (rounded corners are the transparent key).
    Languages spoken in several big countries get a flag split on the diagonal."""
    codes = FLAG_OF.get(lang, (lang,))
    big = _country(codes[0])
    if len(codes) == 2:
        other = _country(codes[1])
        mask = Image.new('L', big.size, 0)
        ImageDraw.Draw(mask).polygon([(96, 0), (96, 64), (0, 64)], fill=255)
        big.paste(other, (0, 0), mask)
    small = big.resize((24, 16), Image.LANCZOS)
    im = Image.new('RGB', (24, 16), rgb(bg))
    mask = Image.new('L', (24, 16), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 23, 15), radius=3, fill=255)
    im.paste(small, (0, 0), mask)
    return im


def gauge(p, x0, y, x1):
    """Temperature track: cool teal to hot red, 6 px high."""
    stops = [(0.0, (47, 168, 154)), (0.5, (240, 180, 41)), (1.0, (229, 72, 77))]
    w = x1 - x0
    for i in range(w + 1):
        t = i / w
        for (a, ca), (b_, cb) in zip(stops, stops[1:]):
            if a <= t <= b_:
                u = (t - a) / (b_ - a)
                col = tuple(int(ca[k] + (cb[k] - ca[k]) * u) for k in range(3))
                break
        p.d.line((x0 + i, y, x0 + i, y + 5), fill=col)
    # rounded ends
    for (cx, side) in ((x0, 1), (x1, -1)):
        for dy in (0, 5):
            p.d.point((cx, y + dy), fill=rgb(CARD2))


# ------------------------------------------------------------------------------------------ pages
def build_pages(OV, OT):
    P = {}
    N = lambda pid, name, *a, **kw: P2(pid, name, OV, OT, *a, **kw)

    # 0 boot
    p = N(0, 'boot')
    p.d.ellipse((190, 50, 290, 150), outline=rgb(ACC), width=3)
    p.glyph('print', 54, WHITE, 213, 73)
    p.text('WANHAO D9', 240, 176, 'brand', 'mm')
    p.text('DGUS Reloaded ' + VERSION, 240, 204, 'numsmall', 'mm')
    P[0] = p

    # 1 home (direction C)
    p = N(1, 'home')
    LW = 222
    p.d.rectangle((0, 0, LW - 1, H), fill=rgb(CARD2))
    p.d.line((LW - 1, 0, LW - 1, H), fill=rgb(LINE))
    # Language flag (touch it, or the name, to change language), then the machine name sent by Marlin
    base, _ = TL.custom('flags', [flag(c, CARD2) for c in LANGS])
    p.vars.append(db.var_icon(LANG_VP, 12, 13, 0, NLANG - 1, base, base + NLANG - 1, TEXT_LIB))
    p.vars.append(db.var_text(0x3133, (44, 14, 280, 30), c565(TEXT), 24, 16, 16))  # INFOS_Machine
    for (y, key, icon, cur, tgt, vmax) in ((44, 't_ext', 'nozzle', 1, 2, 305), (122, 't_bed', 'bed', 3, 4, 125)):
        p.temp_block(13, y, key, icon, cur, tgt, CARD2)
        ty = y + 62
        gauge(p, 14, ty, 208)
        p.vars.append(db.var_slider_icon(decode_var(p.ov[cur])['vp'], 0, vmax * 10, 14 - 7, 208 - 7, 13, ty - 4, 24))
        p.vars.append(db.var_slider_icon(decode_var(p.ov[tgt])['vp'], 0, vmax, 14 - 6, 208 - 6, 14, ty - 11, 24))
    p.d.line((14, 204, LW - 15, 204), fill=rgb(LINE))
    p.d.ellipse((13, 214, 20, 221), fill=rgb(OK))
    p.label('status', 26, 210, 'label', CARD2, maxw=180)
    p.var(0, box=(14, 236, 282, 254), color=c565(TEXT), font_x=18, font_y=18)  # one line: wraps (hidden) past 19 chars
    rows = [(234, 12, 468, 88), (234, 98, 468, 174), (234, 184, 468, 260)]
    for i, (r, icon, key) in enumerate(zip(rows, ['print', 'temp', 'settings'], ['print', 'temperature', 'settings'])):
        acc = i == 0
        p.rect(r, ACC if acc else CARD, ACC if acc else LINE, 9)
        cy = (r[1] + r[3]) // 2
        p.glyph(icon, 28, WHITE if acc else ICON, 248, cy - 14)
        p.glyph('chev', 16, '#d8f0ed' if acc else MUTED, r[2] - 26, cy - 8)
        p.label(key, 286, cy, 'row_acc' if acc else 'row', ACC if acc else CARD, valign='center', maxw=150)
    p.touch = [p.t(0, rows[0]), p.t(1, rows[1]), p.t(2, rows[2]),
               db.touch_incdec(1, (0, 0, LW - 2, 40), LANG_VP, 1, 0, NLANG - 1, True, True, voice=p.ot[0][0] >> 2, upload=True)]
    P[1] = p

    # 2 print: file list
    p = N(2, 'files', 'files')
    p.rect((12, 48, 404, 216), CARD, LINE, 10)
    files = []
    for i in range(5):
        y = 48 + i * 33
        files.append((12, y, 404, y + 32))
        if i:
            p.d.line((22, y, 394, y), fill=rgb(LINE))
        p.var(1 + i, x=22, y=y + 6)
        p.var(6 + i, box=(56, y + 9, 396, y + 25), color=c565(TEXT), font_x=16, font_y=16)
    btns = [(412, 48, 468, 100), (412, 106, 468, 158), (412, 164, 468, 216)]
    for j, r in enumerate(btns):
        p.rect(r, CARD, LINE, 9)
        p.var(12 + j, x=r[0] + 12, y=(r[1] + r[3]) // 2 - 16)
    p.rect((12, 226, 330, 262), CARD2, LINE, 9)
    p.var(11, box=(24, 237, 322, 253), color=c565(TEXT), font_x=16, font_y=16)
    pb = (340, 226, 468, 262)
    p.button(pb, 'print', 'print', accent=True)
    p.touch = [p.t(0, BACK)] + [p.t(1 + i, files[i]) for i in range(5)] + [p.t(6 + j, btns[j]) for j in range(3)] + [p.t(9, pb)]
    P[2] = p

    # 3 print status / 5 finished
    def status_page(pid, name, title, buttons):
        p = N(pid, name, title, back=False)
        p.rect((12, 48, 236, 110), CARD, LINE, 10)
        p.temp_block(24, 56, 'extruder', 'nozzle', 1, 2, CARD)
        p.rect((244, 48, 468, 110), CARD, LINE, 10)
        p.temp_block(256, 56, 'bed', 'bed', 3, 4, CARD)
        p.rect((12, 118, 236, 174), CARD, LINE, 10)
        p.glyph('height', 15, MUTED, 23, 127)
        p.label('z_height', 42, 125, 'label', CARD, maxw=186)
        p.value_at(5, 24, 146, 10, TEXT, 0, unit=b' mm')
        p.rect((244, 118, 468, 174), CARD, LINE, 10)
        p.glyph('timer', 15, MUTED, 255, 127)
        p.label('elapsed', 274, 125, 'label', CARD, maxw=186)
        p.var(6, box=(256, 147, 462, 165), color=c565(TEXT), font_x=18, font_y=18)
        p.label('progress', 14, 182, 'label', BG, maxw=300)
        p.value_at(7, 468 - 5 * 9, 180, 9, TEXT, 1, unit=b' %')
        p.var(8, x=12, y=202)
        p.var(9, x=239, y=202)
        for kind, r in buttons:
            if kind == 'abort':
                p.button(r, 'stop', 'abort')
            elif kind == 'adjust':
                p.button(r, 'adjust', 'adjust_btn')
            elif kind == 'home':
                p.button(r, 'home', 'home', accent=True)
            elif kind == 'pause':
                p.var(10, x=r[0], y=r[1])
            elif kind == 'resume':
                p.var(11, x=r[0], y=r[1])
        return p

    b3 = [('abort', (12, 224, 120, 262)), ('pause', (128, 224, 236, 262)), ('resume', (244, 224, 352, 262)), ('adjust', (360, 224, 468, 262))]
    p = status_page(3, 'print_status', 'printing', b3)
    p.touch = [p.t(i, b3[i][1]) for i in range(4)]
    P[3] = p
    b5 = [('home', (170, 224, 310, 262))]
    p = status_page(5, 'print_finished', 'finished', b5)
    p.touch = [p.t(0, b5[0][1])]
    P[5] = p

    # 4 adjust during a print
    p = N(4, 'print_adjust', 'adjust')
    cards = [((12, 48, 236, 116), 'extruder', 'nozzle', '°C'), ((12, 122, 236, 190), 'bed', 'bed', '°C'),
             ((12, 196, 236, 264), 'fan_speed', 'fan', '%'), ((244, 48, 468, 116), 'feedrate', 'right', '%'),
             ((244, 122, 468, 190), 'flowrate', 'extrude', '%'), ((244, 196, 468, 264), 'z_offset', 'z', 'mm')]
    fields = []
    for k, (r, key, icon, unit) in enumerate(cards):
        p.rect(r, CARD, LINE, 10)
        p.glyph(icon, 15, MUTED, r[0] + 11, r[1] + 9)
        p.label(key, r[0] + 30, r[1] + 7, 'label', CARD, maxw=188)
        f = (r[0] + 12, r[1] + 28, r[0] + (122 if unit == 'mm' else 104), r[1] + 60)
        fields.append(f)
        p.field(f)
        if unit == '°C':
            p.text(unit, f[2] + 6, f[1] + 7, 'num')
            p.value_in(1 + k, f, 10)
        else:
            p.value_unit(1 + k, f, 10, ' ' + unit, 5 if unit == 'mm' else 3)
    zr = cards[5][0]
    up, dn = (zr[0] + 130, zr[1] + 26, zr[0] + 168, zr[1] + 62), (zr[0] + 176, zr[1] + 26, zr[0] + 214, zr[1] + 62)
    p.button(up, 'up', gsize=20)
    p.button(dn, 'down', gsize=20)
    p.touch = [p.t(0, BACK)] + [p.t(1 + i, fields[i]) for i in range(6)] + [p.t(7, up), p.t(8, dn)]
    P[4] = p

    # 6 temperature menu
    p = N(6, 'temp_menu', 'temperature')
    p.rect((12, 48, 236, 262), CARD2, LINE, 10)
    p.temp_block(24, 62, 't_ext', 'nozzle', 1, 2, CARD2)
    p.temp_block(24, 150, 't_bed', 'bed', 3, 4, CARD2)
    r6 = {'presets': (244, 48, 468, 99), 'manual': (244, 104, 468, 155), 'cool': (244, 160, 468, 211), 'fan': (244, 216, 468, 262)}
    for key, icon in (('presets', 'preset'), ('manual', 'manual'), ('cool', 'snow'), ('fan', 'fan')):
        r = r6[key]
        p.rect(r, CARD, LINE, 9)
        cy = (r[1] + r[3]) // 2
        p.glyph(icon, 24, ICON, r[0] + 14, cy - 12)
        p.glyph('chev', 14, MUTED, r[2] - 22, cy - 7)
        p.label(key, r[0] + 48, cy, 'btn', CARD, valign='center', maxw=146)
    p.touch = [p.t(0, BACK), p.t(1, r6['manual']), p.t(2, r6['cool']), p.t(3, r6['fan']), p.t(4, r6['presets'])]
    P[6] = p

    # 7 temperature manual
    p = N(7, 'temp_manual', 'temperature')
    tf, cb = [], []
    for k, (y, key, icon, cur, tgt, mx) in enumerate(((48, 'extruder', 'nozzle', 1, 2, 5), (158, 'bed', 'bed', 3, 4, 6))):
        r = (12, y, 468, y + 104)
        p.rect(r, CARD, LINE, 10)
        p.glyph(icon, 16, MUTED, 24, y + 11)
        p.label(key, 44, y + 9, 'label', CARD, maxw=120)
        cf = p.value_at(cur, 24, y + 38, 16, TEXT, 1)
        p.text('°C', 24 + chars(cf) * 16 + 4, y + 46, 'num')
        p.label('target', 176, y + 9, 'label', CARD, maxw=130)
        f = (176, y + 32, 262, y + 68)
        tf.append(f)
        p.field(f)
        p.value_in(tgt, f, 10)
        p.text('°C', 268, y + 41, 'num')
        p.text('max', 176, y + 78, 'numsmall')
        p.value_at(mx, 206, y + 79, 7, MUTED, 1)
        p.text('°C', 206 + 21 + 4, y + 78, 'numsmall')
        c = (312, y + 32, 456, y + 68)
        cb.append(c)
        p.button(c, 'snow', 'cool')
    p.touch = [p.t(0, BACK), p.t(1, tf[0]), p.t(2, tf[1]), p.t(3, cb[0]), p.t(4, cb[1])]
    P[7] = p

    # 8 fan, 20 volume, 21 brightness
    def level_page(pid, name, title, key, icon):
        p = N(pid, name, title)
        p.rect((12, 48, 468, 262), CARD, LINE, 10)
        p.glyph(icon, 22, MUTED, 28, 62)
        p.label(key, 58, 73, 'text', CARD, valign='center', maxw=380)
        f = (180, 96, 300, 140)
        p.field(f)
        p.value_unit(2, f, 12, ' %', 3)
        off, full = (28, 182, 112, 226), (368, 182, 452, 226)
        p.rect(off, FIELD, FIELD_LINE, 9)
        p.text('0 %', 70, 204, 'btn', 'mm')
        p.rect(full, FIELD, FIELD_LINE, 9)
        p.text('100 %', 410, 204, 'btn', 'mm')
        p.d.rounded_rectangle((136, 201, 344, 207), radius=3, fill=rgb(LINE))
        p.var(1, pos_begin=126, pos_end=326, cross=192)
        p.touch = [p.t(0, BACK), p.t(1, off), p.t(2, full), p.t(3, (130, 180, 350, 228)), p.t(4, f)]
        return p

    P[8] = level_page(8, 'fan', 'fan', 'fan_speed', 'fan')
    P[20] = level_page(20, 'volume', 'volume', 'volume', 'volume')
    P[21] = level_page(21, 'brightness', 'brightness', 'brightness', 'brightness')

    grid = [(12, 48, 157, 152), (167, 48, 312, 152), (322, 48, 467, 152),
            (12, 158, 157, 262), (167, 158, 312, 262), (322, 158, 467, 262)]
    # 9 settings
    p = N(9, 'settings_menu', 'settings')
    for r, icon, key in zip(grid, ['leveling', 'filament', 'move', 'steppers', 'gcode', 'more'],
                            ['leveling', 'filament', 'move', 'steppers', 'gcode', 'more']):
        p.tile(r, icon, key)
    p.var(1, x=grid[3][0] + 111, y=grid[3][1] + 8)
    p.touch = [p.t(0, BACK), p.t(1, grid[0]), p.t(2, grid[3]), p.t(3, grid[1]), p.t(4, grid[2]), p.t(5, grid[4]), p.t(6, grid[5])]
    P[9] = p

    # 18 settings 2
    p = N(18, 'settings_menu2', 'more')
    for r, icon, key in zip(grid[:4], ['pid', 'volume', 'brightness', 'eeprom'], ['pid', 'volume', 'brightness', 'reset_eeprom']):
        p.tile(r, icon, key)
    p.rect(grid[4], BG, LINE, 10)
    p.rect(grid[5], BG, LINE, 10)
    p.var(1, x=grid[4][0], y=grid[4][1])
    p.var(2, x=grid[5][0], y=grid[5][1])
    p.touch = [p.t(0, BACK), p.t(1, grid[0]), p.t(2, grid[1]), p.t(3, grid[2]), p.t(4, grid[3]), p.t(5, grid[4]), p.t(6, grid[5])]
    P[18] = p

    # 10 leveling menu
    p = N(10, 'leveling_menu', 'leveling')
    lt = [(12, 58, 157, 250), (167, 58, 312, 250), (322, 58, 467, 250)]
    for r, icon, key in zip(lt, ['manual', 'probe', 'z'], ['manual', 'automatic', 'z_offset']):
        p.tile(r, icon, key, gsize=44)
    p.touch = [p.t(0, BACK), p.t(1, lt[0]), p.t(2, lt[1]), p.t(3, lt[2])]
    P[10] = p

    # 11 Z offset
    p = N(11, 'leveling_offset', 'z_offset')
    p.rect((12, 48, 468, 150), CARD, LINE, 10)
    p.label('z_offset', 26, 58, 'label', CARD, maxw=280)
    dn, f, up = (26, 84, 86, 136), (96, 84, 236, 136), (246, 84, 306, 136)
    p.button(dn, 'down', gsize=26)
    p.field(f)
    p.value_unit(1, f, 10, ' mm', 5)
    p.button(up, 'up', gsize=26)
    hb = (322, 84, 454, 136)
    p.button(hb, 'home', 'home_axes')
    p.rect((12, 158, 468, 262), CARD, LINE, 10)
    p.label('step', 26, 170, 'label', CARD, maxw=280)
    s1, s2 = (26, 198, 86, 228), (96, 198, 156, 228)
    p.var(2, x=s1[0], y=s1[1])
    p.var(3, x=s2[0], y=s2[1])
    p.touch = [p.t(0, BACK), p.t(1, f), p.t(2, up), p.t(3, dn), p.t(4, hb), p.t(5, s1), p.t(6, s2)]
    P[11] = p

    # 12 manual leveling
    p = N(12, 'leveling_manual', 'manual')
    p.rect((12, 48, 236, 262), CARD2, LINE, 10)
    p.d.rectangle((56, 80, 192, 214), outline=rgb(LINE))
    pts = {5: (28, 56, 84, 112), 4: (164, 56, 220, 112), 1: (96, 122, 152, 178), 2: (28, 188, 84, 244), 3: (164, 188, 220, 244)}
    for n, r in pts.items():
        p.rect(r, CARD, LINE, 9)
        p.text(str(n), (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, 'big', 'mm')
    tf, cb = [], []
    for k, (y, key, icon, cur, tgt) in enumerate(((48, 'extruder', 'nozzle', 1, 2), (158, 'bed', 'bed', 3, 4))):
        r = (244, y, 468, y + 104)
        p.rect(r, CARD, LINE, 10)
        p.glyph(icon, 15, MUTED, 255, y + 10)
        p.label(key, 274, y + 8, 'label', CARD, maxw=180)
        cf = p.value_at(cur, 256, y + 30, 10, TEXT, 1)
        p.text('°C', 256 + chars(cf) * 10 + 3, y + 32, 'num')
        f = (344, y + 26, 408, y + 58)
        tf.append(f)
        p.field(f)
        p.value_in(tgt, f, 9)
        p.text('°C', 412, y + 33, 'numsmall')
        c = (256, y + 64, 456, y + 96)
        cb.append(c)
        p.button(c, 'snow', 'cool', gsize=18)
    p.touch = [p.t(0, BACK), p.t(1, tf[0]), p.t(2, tf[1]), p.t(3, cb[0]), p.t(4, cb[1])] + [p.t(5 + i, pts[n]) for i, n in enumerate([1, 2, 3, 4, 5])]
    P[12] = p

    # 13 automatic leveling
    p = N(13, 'leveling_automatic', 'automatic')
    probe_b, dis_b = (12, 48, 130, 98), (12, 106, 130, 156)
    p.button(probe_b, 'probe', 'probe', accent=True)
    p.rect(dis_b, BG, LINE, 9)
    p.var(5, x=dis_b[0], y=dis_b[1])
    p.rect((138, 48, 468, 156), CARD, LINE, 10)
    for k in range(25):
        col, row = k % 5, k // 5
        p.value_at(6 + k, 150 + col * 62, 56 + (4 - row) * 19, 8, TEXT, 1)
    tf, cb = [], []
    for k, (x, key, icon, cur, tgt) in enumerate(((12, 'extruder', 'nozzle', 1, 2), (244, 'bed', 'bed', 3, 4))):
        r = (x, 164, x + 224, 262)
        p.rect(r, CARD, LINE, 10)
        p.glyph(icon, 15, MUTED, x + 11, 173)
        p.label(key, x + 30, 171, 'label', CARD, maxw=186)
        cf = p.value_at(cur, x + 12, 192, 10, TEXT, 1)
        p.text('°C', x + 12 + chars(cf) * 10 + 3, 194, 'num')
        f = (x + 108, 188, x + 172, 220)
        tf.append(f)
        p.field(f)
        p.value_in(tgt, f, 9)
        p.text('°C', x + 176, 195, 'numsmall')
        c = (x + 12, 226, x + 212, 256)
        cb.append(c)
        p.button(c, 'snow', 'cool', gsize=18)
    p.touch = [p.t(0, BACK), p.t(1, tf[0]), p.t(2, cb[0]), p.t(3, tf[1]), p.t(4, cb[1]), p.t(5, dis_b), p.t(6, probe_b)]
    P[13] = p

    # 14 probing
    p = N(14, 'leveling_probing', 'probing', back=False)
    p.rect((12, 48, 236, 262), CARD, LINE, 10)
    for k in range(25):
        f = decode_var(p.ov[1 + k])
        x, y = f['x'], f['y']
        p.d.rounded_rectangle((x - 4, y - 6, x + 30, y + 28), radius=6, fill=rgb(FIELD), outline=rgb(FIELD_LINE))
        p.var(1 + k)
    p.glyph('probe', 44, ACC, 330, 70)
    p.vars.append(db.var_text(0x3000, (252, 150, 468, 186), c565(TEXT), 32, 16, 16))
    P[14] = p

    # 15 filament
    p = N(15, 'filament', 'filament')
    p.rect((12, 48, 468, 136), CARD, LINE, 10)
    p.label('length', 26, 56, 'label', CARD, maxw=124)
    lf = (26, 78, 150, 126)
    p.field(lf)
    p.value_unit(1, (26, 78, 150, 126), 12, ' mm', 2)
    rb, eb = (166, 78, 308, 126), (316, 78, 456, 126)
    p.button(rb, 'retract', 'retract')
    p.button(eb, 'extrude', 'extrude')
    p.rect((12, 144, 468, 214), CARD, LINE, 10)
    p.glyph('nozzle', 16, MUTED, 24, 153)
    p.label('extruder', 44, 151, 'label', CARD, maxw=120)
    cf = p.value_at(2, 24, 176, 12, TEXT, 1)
    p.text('°C', 24 + chars(cf) * 12 + 4, 181, 'num')
    p.label('target', 176, 151, 'label', CARD, maxw=130)
    tfld = (176, 170, 262, 204)
    p.field(tfld)
    p.value_in(3, tfld, 10)
    p.text('°C', 268, 178, 'num')
    cbt = (312, 170, 456, 204)
    p.button(cbt, 'snow', 'cool')
    sensor_b = (12, 222, 468, 262)
    p.rect(sensor_b, CARD, LINE, 9)
    p.glyph('sensor', 24, ICON, 26, 230)
    p.glyph('chev', 16, MUTED, 440, 234)
    p.label('sensor', 60, 242, 'btn', CARD, valign='center', maxw=370)
    goto_sensor = db.touch_return_key(15, sensor_b, 0x2000, 23, voice=p.ot[0][0] >> 2)
    p.touch = [p.t(0, BACK), p.t(1, lf), p.t(2, rb), p.t(3, eb), p.t(4, tfld), p.t(5, cbt), goto_sensor]
    P[15] = p

    # 23 filament sensor (as on the mockup): runout switch, jam detection, jam length -/+, filament dot, Save
    p = N(23, 'filament_sensor', 'sensor')
    voice = P[15].ot[0][0] >> 2
    rows23 = [(12, 48, 468, 104), (12, 110, 468, 166), (12, 172, 468, 226)]
    for r, key, sub in ((rows23[0], 'runout', 'runout_sub'), (rows23[1], 'jam', 'jam_sub')):
        p.rect(r, CARD, LINE, 10)
        p.label(key, r[0] + 14, r[1] + 9, 'btn', CARD, maxw=360)
        p.label(sub, r[0] + 14, r[1] + 33, 'label', CARD, maxw=360)
    sw1, sw2 = (392, 60, 454, 92), (392, 122, 454, 154)
    p.vars.append(db.var_bit_icon(0x31BF, 0x0001, sw1[0], sw1[1], 27, 19, 20))
    p.vars.append(db.var_bit_icon(0x31BF, 0x0002, sw2[0], sw2[1], 27, 19, 20))
    p.rect(rows23[2], CARD, LINE, 10)
    p.label('jam_len', 26, 199, 'btn', CARD, valign='center', maxw=262)
    dec, jf, inc = (296, 182, 336, 216), (342, 182, 414, 216), (420, 182, 460, 216)
    p.rect(dec, FIELD, FIELD_LINE, 8)
    p.glyph('minus', 18, TEXT, 307, 190, 2)
    p.field(jf)
    p.value_unit(None, jf, 10, ' mm', 2, rec=db.var_data(0x4025, 0, 0, c565(TEXT), 10, 3, 0))
    p.rect(inc, FIELD, FIELD_LINE, 8)
    p.glyph('plus', 18, TEXT, 431, 190, 2)
    pill = (12, 234, 150, 266)
    p.rect(pill, CARD, LINE, 16)
    p.vars.append(db.var_bit_icon(0x31BF, 0x0004, 26, 244, 27, 21, 22))
    p.label('loaded', 44, 250, 'btn', CARD, valign='center', maxw=96)
    save23 = (308, 234, 468, 266)
    p.button(save23, 'save', 'save', accent=True, gsize=20)
    ref = P[15].ot[1]   # filament length numeric input: same keypad, other VP
    jam_in = bytearray(ref)
    jam_in[0:2] = bytes([ref[0] & 0xFC, 23])
    jam_in[2:10] = struct.pack('>4H', *jf)
    jam_in[0x11:0x13] = struct.pack('>H', 0x4025)
    jam_in[0x14], jam_in[0x15] = 3, 0
    jam_in[0x1A:0x1C] = struct.pack('>H', c565(TEXT))
    p.touch = [db.touch_return_key(23, BACK, 0x2000, 15, voice=voice),
               db.touch_return_key(23, rows23[0], 0x2030, 0, voice=voice),
               db.touch_return_key(23, rows23[1], 0x2030, 1, voice=voice),
               bytes(jam_in),
               db.touch_incdec(23, dec, 0x4025, 1, 0, 999, increment=False, voice=voice),
               db.touch_incdec(23, inc, 0x4025, 1, 0, 999, increment=True, voice=voice),
               db.touch_return_key(23, save23, 0x2032, 0, voice=voice)]
    P[23] = p

    # 16 move
    p = N(16, 'move', 'move')
    p.rect((12, 48, 186, 262), CARD, LINE, 10)
    axis_f = []
    for k, axis in enumerate('XYZ'):
        y = 58 + k * 56
        p.d.rounded_rectangle((22, y + 5, 50, y + 39), radius=7, outline=rgb(FIELD_LINE))
        p.text(axis, 36, y + 22, 'big', 'mm')
        f = (58, y, 176, y + 44)
        axis_f.append(f)
        p.field(f)
        p.value_unit(1 + k, f, 10, ' mm', 5)
    p.label('step', 196, 239, 'label', BG, maxw=66)
    jog = {'yp': (262, 48, 318, 104), 'xm': (202, 110, 258, 166), 'home': (262, 110, 318, 166), 'xp': (322, 110, 378, 166),
           'ym': (262, 172, 318, 228), 'zp': (402, 48, 458, 104), 'zm': (402, 172, 458, 228)}
    for key, icon in (('yp', 'up'), ('xm', 'left'), ('home', 'home'), ('xp', 'right'), ('ym', 'down'), ('zp', 'up'), ('zm', 'down')):
        p.button(jog[key], icon, gsize=24)
    p.text('Z', 430, 138, 'big', 'mm')
    steps = [(270, 234, 330, 264), (338, 234, 398, 264), (406, 234, 466, 264)]
    for j, r in enumerate(steps):
        p.var(4 + j, x=r[0], y=r[1])
    p.touch = [p.t(0, BACK), p.t(1, axis_f[0]), p.t(2, axis_f[1]), p.t(3, axis_f[2]), p.t(4, steps[0]), p.t(5, steps[1]), p.t(6, steps[2]),
               p.t(7, jog['home']), p.t(8, jog['xm']), p.t(9, jog['xp']), p.t(10, jog['ym']), p.t(11, jog['yp']), p.t(12, jog['zm']), p.t(13, jog['zp'])]
    P[16] = p

    # 17 G-code
    p = N(17, 'gcode', 'gcode')
    p.rect((12, 48, 468, 262), CARD, LINE, 10)
    p.label('gcode_hint', 26, 62, 'label', CARD, maxw=420)
    gf = (26, 90, 454, 132)
    p.field(gf)
    p.var(1, box=(38, 102, 446, 120), color=c565(TEXT), font_x=18, font_y=18)
    cl, ex = (104, 168, 236, 212), (244, 168, 376, 212)
    p.button(cl, 'clear', 'clear')
    p.button(ex, 'send', 'send', accent=True)
    p.touch = [p.t(0, BACK), p.t(1, gf), p.t(2, cl), p.t(3, ex)]
    P[17] = p

    # 19 PID
    p = N(19, 'pid', 'pid')
    p.rect((12, 48, 296, 262), CARD, LINE, 10)
    sel = [(24, 58, 154, 96), (160, 58, 290, 96)]
    p.var(6, x=sel[0][0], y=sel[0][1])
    p.var(7, x=sel[1][0], y=sel[1][1])
    p.label('pid_temp', 24, 106, 'label', CARD, maxw=136)
    tfp = (24, 124, 112, 160)
    p.field(tfp)
    p.value_in(1, tfp, 10)
    p.text('°C', 118, 133, 'num')
    p.label('cycles', 170, 106, 'label', CARD, maxw=116)
    cfp = (170, 124, 240, 160)
    p.field(cfp)
    p.value_in(2, cfp, 10)
    run = (24, 180, 284, 222)
    p.button(run, 'play', 'run', accent=True)
    p.rect((304, 48, 468, 262), CARD2, LINE, 10)
    for k, name in enumerate(('Kp', 'Ki', 'Kd')):
        y = 56 + k * 68
        p.text(name, 318, y, 'num')
        p.value_at(3 + k, 318, y + 24, 10, TEXT, 0)
    p.touch = [p.t(0, BACK), p.t(1, tfp), p.t(2, cfp), p.t(3, run), p.t(4, sel[0]), p.t(5, sel[1])]
    P[19] = p

    # 22 information
    p = N(22, 'information', 'information')
    p.rect((12, 48, 468, 124), CARD, LINE, 10)
    for k, key in enumerate(('machine', 'build_volume', 'version')):
        y = 56 + k * 22
        p.label(key, 24, y, 'label', CARD, maxw=136)
        p.var(1 + k, box=(168, y + 1, 460, y + 17), color=c565(TEXT), font_x=16, font_y=16)
    p.rect((12, 132, 468, 262), CARD, LINE, 10)
    p.label('prints', 24, 142, 'label', CARD, maxw=136)
    p.value_at(7, 168, 143, 8, TEXT, 0)
    p.label('completed', 300, 142, 'label', CARD, maxw=96)
    p.value_at(8, 400, 143, 8, TEXT, 0)
    for k, key in enumerate(('print_time', 'longest', 'filament_used')):
        y = 172 + k * 28
        p.label(key, 24, y, 'label', CARD, maxw=136)
        p.var(4 + k, box=(168, y + 1, 460, y + 17), color=c565(TEXT), font_x=16, font_y=16)
    p.touch = [p.t(0, BACK), p.t(1, (12, 48, 468, 124))]
    P[22] = p

    # 240 / 241 debug (kept simple)
    p = N(240, 'debug1', '', status=False)
    p.text('Debug', 50, 20, 'title', 'lm')
    for k in range(2):
        p.var(k, color=c565(TEXT))
    p.var(2, color=c565(TEXT))
    nav = (220, 229, 258, 267)
    p.button(nav, 'down', gsize=20)
    p.touch = [p.t(0, nav), p.t(1, BACK)]
    P[240] = p
    p = N(241, 'debug2', '', status=False)
    p.text('Debug', 50, 20, 'title', 'lm')
    for k in range(4):
        p.var(k)
    nav2 = (220, 44, 258, 82)
    p.button(nav2, 'up', gsize=20)
    p.touch = [p.t(0, BACK), p.t(1, nav2)]
    P[241] = p

    # 248 power loss
    p = N(248, 'power_loss', 'power_loss', back=False)
    p.glyph('power', 26, ACC, 24, 54)
    p.label('resume_q', 60, 67, 'big', BG, valign='center', maxw=400)
    ab, rs = (40, 100, 228, 250), (252, 100, 440, 250)
    p.rect(ab, CARD, LINE, 12)
    p.glyph('x', 44, WARN, 112, 136)
    p.label('cancel', 134, 204, 'tile', CARD, halign='center', maxw=176)
    p.rect(rs, ACC, ACC, 12)
    p.glyph('play', 44, WHITE, 324, 136)
    p.label('resume', 346, 204, 'tile', ACC, halign='center', maxw=176)
    p.touch = [p.t(0, ab), p.t(1, rs)]
    P[248] = p

    # 249 wait
    p = N(249, 'wait', 'wait', back=False)
    p.rect((12, 48, 468, 212), CARD, LINE, 10)
    for i in range(4):
        p.var(1 + i, box=(28, 62 + i * 36, 452, 80 + i * 36), color=c565(TEXT), font_x=18, font_y=18)
    wa, wc = (128, 222, 236, 262), (244, 222, 352, 262)
    p.var(5, x=wa[0], y=wa[1])
    p.var(6, x=wc[0], y=wc[1])
    p.touch = [p.t(0), p.t(1, wa), p.t(2, wc)]
    P[249] = p

    # 250 kill
    p = N(250, 'kill', 'error', back=False, status=False)
    p.glyph('warning', 64, WARN, 34, 108)
    for i in range(4):
        p.var(i, box=(128, 70 + i * 36, 470, 88 + i * 36), color=c565(TEXT), font_x=18, font_y=18)
    P[250] = p
    return P


# ------------------------------------------------------------------------------------------ popups and keyboards
def popups():
    """Picture pages shown as popups: normal and pressed (_sel) versions. Geometry = DGUS Reloaded 1.0.3."""
    pics = {}

    def base():
        im = Image.new('RGB', (W, H), rgb(BG))
        return im, ImageDraw.Draw(im)

    def dialog(area, pressed, draw_title, keys):
        im, d = base()
        d.rounded_rectangle(area, radius=12, fill=rgb(CARD2), outline=rgb(ACC))
        draw_title(im, d)
        for r, kind in keys:
            if kind == 'yes':
                d.rounded_rectangle(r, radius=9, fill=rgb(ACC_ON if pressed else ACC))
                glyph(im, 'check', 26, WHITE, (r[0] + r[2]) // 2 - 13, (r[1] + r[3]) // 2 - 13, 2.4)
            elif kind == 'no':
                d.rounded_rectangle(r, radius=9, fill=rgb(FIELD_LINE if pressed else FIELD), outline=rgb(FIELD_LINE))
                glyph(im, 'x', 24, TEXT, (r[0] + r[2]) // 2 - 12, (r[1] + r[3]) // 2 - 12, 2.2)
            elif kind == 'close':
                glyph(im, 'x', 20, TEXT if pressed else MUTED, (r[0] + r[2]) // 2 - 10, (r[1] + r[3]) // 2 - 10, 2)
            else:
                d.rounded_rectangle(r, radius=9, fill=rgb(ACC if pressed else FIELD), outline=rgb(FIELD_LINE))
                if kind.startswith('g:'):
                    glyph(im, kind[2:], 24, WHITE if pressed else TEXT, (r[0] + r[2]) // 2 - 12, (r[1] + r[3]) // 2 - 12, 2)
                else:
                    text(d, kind, (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, 'btn', 'mm')
        return im

    A = (118, 99, 360, 202)
    yes, no = (129, 155, 230, 191), (249, 155, 350, 191)

    def question(icon):
        def draw(im, d):
            glyph(im, icon, 34, TEXT, 196, 110, 2)
            text(d, '?', 262, 127, 'big', 'mm')
        return draw

    for pid, icon in ((204, 'stop'), (206, 'pause'), (208, 'play'), (214, 'eeprom')):
        pics[pid] = dialog(A, False, question(icon), [(yes, 'yes'), (no, 'no')])
        pics[pid + 1] = dialog(A, True, question(icon), [(yes, 'yes'), (no, 'no')])

    def titled(icon):
        def draw(im, d):
            glyph(im, icon, 30, TEXT, 139, 108, 2)
        return draw

    st = [((129, 155, 230, 191), 'g:lock'), ((249, 155, 350, 191), 'g:unlock'), ((323, 98, 361, 136), 'close')]
    pics[212] = dialog(A, False, titled('steppers'), st)
    pics[213] = dialog(A, True, titled('steppers'), st)
    pr = [((313, 98, 351, 136), 'close'), ((141, 155, 202, 191), 'PLA'), ((209, 155, 270, 191), 'ABS'), ((277, 155, 338, 191), 'PETG')]
    pics[210] = dialog((129, 99, 350, 202), False, titled('preset'), pr)
    pics[211] = dialog((129, 99, 350, 202), True, titled('preset'), pr)

    # numeric keypad (area 144,50 - 335,252)
    def numpad(pressed):
        im, d = base()
        d.rounded_rectangle((144, 50, 335, 252), radius=10, fill=rgb(CARD2), outline=rgb(ACC))
        d.rounded_rectangle((148, 55, 331, 87), radius=7, fill=rgb(FIELD), outline=rgb(FIELD_LINE))
        keys = [((148, 93, 191, 128), '1'), ((195, 93, 238, 128), '2'), ((242, 93, 285, 128), '3'), ((289, 93, 332, 128), 'g:clear'),
                ((148, 133, 191, 168), '4'), ((195, 133, 238, 168), '5'), ((242, 133, 285, 168), '6'), ((289, 133, 332, 168), 'g:x'),
                ((148, 173, 191, 208), '7'), ((195, 173, 238, 208), '8'), ((242, 173, 285, 208), '9'), ((242, 213, 285, 248), '.'),
                ((289, 173, 332, 248), 'g:check'), ((195, 213, 238, 248), '0'), ((148, 213, 191, 248), '-')]
        for r, k in keys:
            ok = k == 'g:check'
            fill = (ACC_ON if pressed else ACC) if ok else (ACC if pressed else FIELD)
            d.rounded_rectangle(r, radius=7, fill=rgb(fill), outline=None if ok else rgb(FIELD_LINE))
            if k.startswith('g:'):
                glyph(im, k[2:], 22, WHITE if ok or pressed else TEXT, (r[0] + r[2]) // 2 - 11, (r[1] + r[3]) // 2 - 11, 2)
            else:
                text(d, k, (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, 'key', 'mm')
        return im

    pics[202], pics[203] = numpad(False), numpad(True)

    # G-code keyboard (area 34,60 - 446,242)
    def keyboard(pressed):
        im, d = base()
        d.rounded_rectangle((34, 60, 446, 242), radius=10, fill=rgb(CARD2), outline=rgb(ACC))
        d.rounded_rectangle((40, 64, 440, 92), radius=7, fill=rgb(FIELD), outline=rgb(FIELD_LINE))
        rows = ['1234567890', 'QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM.-']
        for ri, row in enumerate(rows):
            y0 = 97 + ri * 36
            for ci, ch in enumerate(row):
                x0 = 37 + ci * 36
                r = (x0, y0, x0 + 34, y0 + 34)
                d.rounded_rectangle(r, radius=6, fill=rgb(ACC if pressed else FIELD), outline=rgb(FIELD_LINE))
                text(d, ch, x0 + 17, y0 + 17, 'key', 'mm')
        special = [((397, 97, 443, 131), 'g:clear', False), ((397, 133, 443, 167), 'g:x', False), ((361, 169, 443, 203), 'g:check', True),
                   ((361, 205, 401, 239), 'g:left', False), ((403, 205, 443, 239), 'g:right', False)]
        for r, k, ok in special:
            fill = (ACC_ON if pressed else ACC) if ok else (ACC if pressed else FIELD)
            d.rounded_rectangle(r, radius=6, fill=rgb(fill), outline=None if ok else rgb(FIELD_LINE))
            glyph(im, k[2:], 20, WHITE if ok or pressed else TEXT, (r[0] + r[2]) // 2 - 10, (r[1] + r[3]) // 2 - 10, 2)
        return im

    pics[200], pics[201] = keyboard(False), keyboard(True)
    return pics


# ------------------------------------------------------------------------------------------ icon libraries
def icon_libs():
    def canvas(w, h, bg):
        im = Image.new('RGB', (w, h), rgb(bg))
        return im, ImageDraw.Draw(im)

    lib24 = {}
    for i, g in ((0, 'file'), (1, 'folder')):
        im, d = canvas(22, 22, CARD)
        glyph(im, g, 22, ICON, 0, 0)
        lib24[i] = im
    for i, (g, on) in enumerate((('parent', 0), ('parent', 1), ('up', 0), ('up', 1), ('down', 0), ('down', 1))):
        im, d = canvas(32, 32, CARD)
        glyph(im, g, 30, TEXT if on else LINE, 1, 1, 2)
        lib24[2 + i] = im
    im, d = canvas(28, 28, CARD)
    d.ellipse((1, 1, 26, 26), fill=rgb(ACC), outline=rgb(WHITE), width=2)
    lib24[8] = im
    im, d = canvas(28, 28, CARD)
    d.ellipse((1, 1, 26, 26), fill=rgb(WARN))
    glyph(im, 'x', 16, WHITE, 6, 6, 2.4)
    lib24[9] = im
    im, d = canvas(26, 26, FIELD)
    glyph(im, 'check', 26, ACC, 0, 0, 2.6)
    lib24[10] = im
    for i, g in ((11, 'x'), (12, 'check')):
        im, d = canvas(21, 21, BG)
        glyph(im, g, 21, TEXT, 0, 0, 2)
        lib24[i] = im
    im, d = canvas(14, 14, CARD2)            # current temperature marker on the gauge
    d.ellipse((0, 0, 13, 13), fill=rgb(WHITE))
    d.ellipse((3, 3, 10, 10), fill=rgb(CARD2))
    lib24[13] = im
    im, d = canvas(12, 8, CARD2)             # target temperature marker, above the gauge (pixel 0,0 stays the key colour)
    d.polygon([(1, 1), (10, 1), (5, 7)], fill=rgb(ICON))
    lib24[14] = im

    lib27 = {}

    def btn(w, h, fill, g, label=None, fg=TEXT, outline=None, gsize=20):
        im, d = canvas(w, h, BG)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=9, fill=rgb(fill), outline=rgb(outline) if outline else None)
        if label:
            f = font('cond', 17)
            tw = f.getbbox(label)[2]
            total = (gsize + 6 if g else 0) + tw
            x = (w - total) // 2
            if g:
                glyph(im, g, gsize, fg, x, h // 2 - gsize // 2, 2)
                x += gsize + 6
            d.text((x, h // 2), label, font=f, fill=rgb(fg), anchor='lm')
        elif g:
            glyph(im, g, gsize, fg, w // 2 - gsize // 2, h // 2 - gsize // 2, 2)
        return im

    lib27[0] = btn(108, 38, CARD, 'pause', outline=LINE, gsize=22)
    lib27[1] = btn(108, 38, ACC, 'play', fg=WHITE, gsize=22)
    lib27[2] = btn(118, 50, CARD, 'x', 'ABL', outline=LINE)
    for i, lbl in enumerate(('10', '1', '0.1', '0.01')):
        lib27[3 + 2 * i] = btn(60, 30, FIELD, None, lbl, outline=FIELD_LINE)
        lib27[4 + 2 * i] = btn(60, 30, ACC, None, lbl, fg=WHITE)

    def tile(g, label):
        im, d = canvas(145, 104, BG)
        d.rounded_rectangle((0, 0, 144, 103), radius=10, fill=rgb(CARD), outline=rgb(LINE))
        glyph(im, g, 34, ICON, 72 - 17, 52 - 17 - 12)
        f = font('cond', 17)
        d.text((72, 52 + 17 + 4), label, font=f, fill=rgb(TEXT), anchor='mt')
        return im

    lib27[11] = tile('info', 'Info')
    lib27[12] = tile('probe', 'BLTouch')
    lib27[13] = btn(130, 38, FIELD, 'nozzle', None, outline=FIELD_LINE, gsize=24)
    lib27[14] = btn(130, 38, ACC, 'nozzle', None, fg=WHITE, gsize=24)
    lib27[15] = btn(130, 38, FIELD, 'bed', None, outline=FIELD_LINE, gsize=24)
    lib27[16] = btn(130, 38, ACC, 'bed', None, fg=WHITE, gsize=24)
    lib27[17] = btn(108, 38, CARD, 'stop', outline=LINE, gsize=22)
    def switch(on):
        im, d = canvas(62, 32, CARD)
        d.rounded_rectangle((0, 0, 61, 31), radius=16, fill=rgb(ACC if on else FIELD_LINE))
        x = 34 if on else 4
        d.ellipse((x, 4, x + 23, 27), fill=rgb(WHITE if on else ICON))
        return im

    lib27[19], lib27[20] = switch(False), switch(True)

    def presence(ok):
        im, d = canvas(38, 28, BG)
        d.rounded_rectangle((0, 0, 37, 27), radius=14, fill=rgb(CARD), outline=rgb(OK if ok else WARN))
        glyph(im, 'check' if ok else 'x', 16, OK if ok else WARN, 11, 6, 2.4)
        return im

    def dot(ok):
        im, d = canvas(12, 12, CARD)
        d.ellipse((1, 1, 10, 10), fill=rgb(OK if ok else WARN))
        return im

    lib27[21], lib27[22] = dot(False), dot(True)
    lib27[18] = btn(108, 38, ACC, 'play', fg=WHITE, gsize=22)

    def bar(p, side):
        im, d = canvas(228, 14, BG)
        lo, hi = (0, 50) if side == 'left' else (50, 100)
        frac = min(max((p - lo) / 50, 0), 1)
        if side == 'left':
            d.rounded_rectangle((0, 0, 237, 13), radius=7, fill=rgb(LINE))
            if frac > 0:
                d.rounded_rectangle((0, 0, max(14, int(228 * frac) + (10 if frac < 1 else 10)), 13), radius=7, fill=rgb(ACC))
        else:
            # Placed one pixel to the left of the seam: column 0 is the transparent key colour, so the
            # left half's last column shows through and the bar stays continuous.
            im, d = canvas(229, 14, BG)
            d.rounded_rectangle((-10, 0, 228, 13), radius=7, fill=rgb(LINE))
            if frac > 0:
                d.rounded_rectangle((-10, 0, 1 + int(227 * frac), 13), radius=7, fill=rgb(ACC))
            d.line((0, 0, 0, 13), fill=rgb(BG))
        return im

    lib30 = {p: bar(p, 'left') for p in range(101)}
    lib37 = {p: bar(p, 'right') for p in range(101)}
    return {24: lib24, 27: lib27, 30: lib30, 37: lib37}


# ------------------------------------------------------------------------------------------ preview
SAMPLE_DATA = {0x30FF: 205.3, 0x3100: 210, 0x30FC: 60.0, 0x30FD: 60, 0x30E6: 12.34, 0x30F7: 42, 0x3101: 290, 0x30FE: 120,
               0x4000: 100, 0x30F8: 100, 0x30F9: 100, 0x3106: -1.11, 0x3125: 50, 0x3126: 150.0, 0x3127: 150.0, 0x3128: 10.0,
               0x312C: 210, 0x4021: 8, 0x312D: 33.41, 0x312F: 1.47, 0x3131: 189.27, 0x3173: 128, 0x3174: 117, 0x4022: 80, 0x4023: 90, 0x4025: 10}
SAMPLE_TEXT = {0x3000: 'E1 Heating...', 0x3025: 'BENCHY.GCO', 0x3045: 'VASE.GCO', 0x3065: 'CLIPS', 0x3085: 'CALIB.GCO', 0x30A5: '',
               0x30C6: 'BENCHY.GCO', 0x30E8: '1h 23m 45s', 0x4001: 'G28', 0x3133: 'Wanhao D9 MK2 300', 0x314B: '300x300x400',
               0x3163: '2.1.x (v2.0.9)', 0x3175: '12d 4h 10m', 0x318D: '14h 2m', 0x31A5: '1.23 km', 0x1100: 'Printer halted.',
               0x1120: 'Please reset', 0x1140: '', 0x1160: ''}


def preview(pages, pics, libs, lang=0):
    hzk = open(os.path.join(REF, '0_DWIN_ASC.HZK'), 'rb').read()

    def ascii_draw(im, s, x, y, n, color):
        for i, ch in enumerate(s[:64]):
            if not (32 <= ord(ch) < 127):
                continue
            for gy, row in enumerate(hz.glyph(hzk, n, ord(ch))):
                for gx, bit in enumerate(row):
                    if bit and 0 <= x + i * n + gx < W and 0 <= y + gy < H:
                        im.putpixel((x + i * n + gx, y + gy), color)

    def paste_icon(im, icon, x, y):
        key = icon.getpixel((0, 0))
        mask = Image.new('L', icon.size, 0)
        mask.putdata([0 if px == key else 255 for px in icon.getdata()])
        im.paste(icon, (x, y), mask)

    def c_from565(v):
        return ((v >> 11) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31)

    out = {}
    for pid, p in pages.items():
        im = p.im.copy()
        for r in p.vars:
            f = decode_var(r)
            if f['kind'] == 'icon':
                lib = TL.icons if f['lib'] == TEXT_LIB else libs[f['lib']]
                if f['vp'] == LANG_VP:
                    idx = f['icon_min'] + lang
                elif f['lib'] in (30, 37):
                    idx = SAMPLE_DATA.get(f['vp'], 0)
                else:
                    idx = f['icon_max']
                if idx in lib:
                    paste_icon(im, lib[idx], f['x'], f['y'])
            elif f['kind'] == 'bit':
                idx = f['icon1s']
                if idx in libs[f['lib']]:
                    paste_icon(im, libs[f['lib']][idx], f['x'], f['y'])
            elif f['kind'] == 'slider':
                icon = libs[f['lib']][f['icon']]
                paste_icon(im, icon, (f['pos_begin'] + f['pos_end']) // 2, f['cross'])
            elif f['kind'] == 'data':
                v = SAMPLE_DATA.get(f['vp'], 123)
                s = f"{v:.{f['n_dot']}f}" if f['n_dot'] else str(int(v))
                w = chars(f)
                s = s.rjust(w) if f['align'] == 1 else s.center(w) if f['align'] == 2 else s
                s = s + f['unit'].decode()
                ascii_draw(im, s, f['x'], f['y'], f['font_x'], c_from565(f['color']))
            elif f['kind'] == 'text':
                s = SAMPLE_TEXT.get(f['vp'], 'text')
                ascii_draw(im, s, f['box'][0], f['box'][1], f['font_x'] // 2, c_from565(f['color']))
        out[pid] = im
    return out


# ------------------------------------------------------------------------------------------ main
def main():
    ds = os.path.join(OUT, 'DWIN_SET')
    os.makedirs(ds, exist_ok=True)
    t = open(os.path.join(REF, '13_touch.bin'), 'rb').read()
    recs, _ = dd.parse_touch(t)
    OT, order = {}, []
    for r in recs:
        pg = r['page'] | ((r['raw'][0] & 3) << 8)
        if pg not in OT:
            order.append(pg)
        OT.setdefault(pg, []).append(r['raw'])
    v = open(os.path.join(REF, '14_variable.bin'), 'rb').read()
    _, maxp, OV = dd.parse_var(v)

    pages = build_pages(OV, OT)
    pics = popups()
    libs = icon_libs()

    # Touch file: pages without a new definition (keyboards, popups) keep their records.
    touch = []
    for pg in sorted(set(OT) | {pid for pid, p in pages.items() if p.touch}):
        new = pages[pg].touch if pg in pages else None
        if pg in OT and new is not None and len(new) < len(OT[pg]):
            raise SystemExit(f'page {pg}: {len(new)} touch controls, original has {len(OT[pg])}')
        touch += new if new else OT[pg]
    open(os.path.join(ds, '13_touch.bin'), 'wb').write(db.build_13(touch))

    var_pages = {pid: p.vars for pid, p in pages.items() if p.vars}
    for pg in OV:
        if pg not in var_pages:
            raise SystemExit(f'page {pg} has display controls but no new definition')
    open(os.path.join(ds, '14_variable.bin'), 'wb').write(db.build_14(var_pages, maxp))
    open(os.path.join(ds, '22_config.bin'), 'wb').write(db.build_22({LANG_VP: b'\x00\x00'}))

    names = {0: 'boot', 1: 'home', 2: 'print', 3: 'print_status', 4: 'print_adjust', 5: 'print_finished', 6: 'temp_menu',
             7: 'temp_manual', 8: 'fan', 9: 'settings_menu', 10: 'leveling_menu', 11: 'leveling_offset', 12: 'leveling_manual',
             13: 'leveling_automatic', 14: 'leveling_probing', 15: 'filament', 16: 'move', 17: 'gcode', 18: 'settings_menu2',
             19: 'pid', 20: 'volume', 21: 'brightness', 22: 'information', 23: 'filament_sensor', 240: 'debug1', 241: 'debug2', 248: 'power_loss',
             249: 'wait', 250: 'kill', 200: 'popup_gcode', 201: 'popup_gcode_sel', 202: 'popup_numpad', 203: 'popup_numpad_sel',
             204: 'popup_abort', 205: 'popup_abort_sel', 206: 'popup_pause', 207: 'popup_pause_sel', 208: 'popup_resume',
             209: 'popup_resume_sel', 210: 'popup_presets', 211: 'popup_presets_sel', 212: 'popup_steppers',
             213: 'popup_steppers_sel', 214: 'popup_eeprom', 215: 'popup_eeprom_sel'}
    for f in os.listdir(ds):
        if f.endswith('.bmp'):
            os.remove(os.path.join(ds, f))
    for pid, p in pages.items():
        p.im.save(os.path.join(ds, f'{pid:03d}_{names[pid]}.bmp'))
    for pid, im in pics.items():
        im.save(os.path.join(ds, f'{pid:03d}_{names[pid]}.bmp'))
    for lib, icons in libs.items():
        name = {24: '24_icons', 27: '27_buttons', 30: '30_progress_left', 37: '37_progress_right'}[lib]
        open(os.path.join(ds, name + '.ico'), 'wb').write(db.build_ico(icons))
    for f in BASE_FILES:
        shutil.copyfile(os.path.join(REF, f), os.path.join(ds, f))
    ico = db.build_ico(TL.icons)
    open(os.path.join(ds, f'{TEXT_LIB}_text.ico'), 'wb').write(ico)
    # Fonts and icon libraries share 256 KB flash slots: a file with id N takes ceil(size / 256 KB) slots from N.
    used = {}
    for f in sorted(os.listdir(ds)):
        m = f.split('_')[0]
        if not (f.endswith('.ico') or f.endswith('.HZK')) or not m.isdigit():
            continue
        n = -(-os.path.getsize(os.path.join(ds, f)) // (256 * 1024))
        for slot in range(int(m), int(m) + n):
            if slot in used:
                raise SystemExit(f'flash slot {slot}: {f} overlaps {used[slot]}')
            used[slot] = f
    print('flash slots:', {f: [s for s, g in used.items() if g == f] for f in sorted(set(used.values()))})

    # Previews
    pv = os.path.join(OUT, 'preview')
    os.makedirs(pv, exist_ok=True)
    for lang in range(NLANG):
        imgs = preview(pages, pics, libs, lang)
        for pid, im in imgs.items():
            im.save(os.path.join(pv, f'{LANGS[lang]}_{pid:03d}.png'))
    for pid, im in pics.items():
        im.save(os.path.join(pv, f'popup_{pid:03d}.png'))
    total = sum(os.path.getsize(os.path.join(ds, f)) for f in os.listdir(ds))
    print(f'pages {len(pages)} popups {len(pics)} text icons {len(TL.icons)} ({len(ico)} B), DWIN_SET {total / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
