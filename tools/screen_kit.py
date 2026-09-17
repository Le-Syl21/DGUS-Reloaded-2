#!/usr/bin/env python3
"""Drawing kit shared by build_screen.py.
"""
import io, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import cairosvg
from PIL import Image, ImageDraw, ImageFont
import dwin_build as db, dwin_dump as dd, hzk_asc as hz
from strings import S, LANGS

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(HERE, 'base', 'DWIN_SET')   # DGUS Reloaded 1.0.3: touch and display records, ASCII font, sounds
FONTS = os.path.join(HERE, 'fonts')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build')
VERSION = '2.0.1'

W, H = 480, 272
BG, BAR, CARD, CARD2, LINE, FIELD, FIELD_LINE = '#141417', '#1e1e24', '#202026', '#1a1a1f', '#2c2c34', '#2a2a31', '#3a3a43'
TEXT, MUTED, ICON, ACC, ACC_ON, OK, WARN, WHITE = '#f1f1f3', '#9b9ba6', '#d6d6de', '#2fa89a', '#3cc4b4', '#3ecf8e', '#e5484d', '#ffffff'
LANG_VP, TEXT_LIB = 0x4024, 44  # DGUS_Addr::LANGUAGE (Marlin saves it)
NO_PAGE = 0xFF00

# ------------------------------------------------------------------------------------------ drawing kit
_font_cache = {}


NOTO = os.path.join(FONTS, 'noto')
SCRIPT_FONT = {'ar': 'NotoSansArabic[wdth,wght].ttf', 'hi': 'NotoSansDevanagari[wdth,wght].ttf',
               'zh': 'NotoSansSC[wght].ttf', 'ja': 'NotoSansJP[wght].ttf', 'ko': 'NotoSansKR[wght].ttf'}
ROLES = {'cond': (600, 75), 'bold': (700, 75), 'text': (500, 100)}   # weight, width (%)


def font(role, size, lang='en'):
    """Noto Sans for every language: Latin, Cyrillic and Greek from Noto Sans, other scripts from their Noto font."""
    k = (role, size, lang)
    if k not in _font_cache:
        name = SCRIPT_FONT.get(lang, 'NotoSans[wdth,wght].ttf')
        f = ImageFont.truetype(os.path.join(NOTO, name), size, layout_engine=ImageFont.Layout.RAQM)
        weight, width = ROLES[role]
        axes = [a['name'] for a in f.get_variation_axes()]
        f.set_variation_by_axes([weight if a == b'Weight' else width for a in axes])
        _font_cache[k] = f
    return _font_cache[k]


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def c565(h):
    r, g, b = rgb(h)
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


GLYPHS = {
    'back': '<path d="M15 5l-7 7 7 7"/>',
    'chev': '<path d="M9 5l7 7-7 7"/>',
    'nozzle': '<path d="M8 3h8v6H8z"/><path d="M9.5 9h5L13 14h-2z"/><path d="M8 18c1-1 2 1 3 0M13 18c1-1 2 1 3 0"/>',
    'bed': '<rect x="3" y="15" width="18" height="4" rx="1"/><path d="M8 5c-1 1.5 1 3 0 4.5M12 5c-1 1.5 1 3 0 4.5M16 5c-1 1.5 1 3 0 4.5"/>',
    'print': '<path d="M7 9V4h10v5"/><rect x="3.5" y="9" width="17" height="8" rx="2"/><path d="M7 14h10v6H7z"/>',
    'temp': '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/><path d="M12 9v8"/>',
    'settings': '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
    'fan': '<circle cx="12" cy="12" r="1.8"/><path d="M12 10.2C11 6 12.5 3 15 3.5s2.5 4.2-1.3 7.3M13.8 12c4.2-1 7.2.5 6.7 3s-4.2 2.5-7.3-1.3M12 13.8c1 4.2-.5 7.2-3 6.7s-2.5-4.2 1.3-7.3M10.2 12c-4.2 1-7.2-.5-6.7-3s4.2-2.5 7.3 1.3"/>',
    'snow': '<path d="M12 2v20M3.3 7l17.4 10M3.3 17L20.7 7"/><path d="M9 4l3 2 3-2M9 20l3-2 3 2M3.6 10.5l3.2-.8L5.4 7M20.4 13.5l-3.2.8 1.4 2.7M3.6 13.5l3.2.8-1.4 2.7M20.4 10.5l-3.2-.8L18.6 7"/>',
    'preset': '<path d="M11 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/><path d="M15 5h6M15 10h6M15 15h4"/>',
    'manual': '<path d="M4 7h16M4 12h16M4 17h16"/><circle cx="8" cy="7" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="11" cy="17" r="2"/>',
    'leveling': '<path d="M3 18h18"/><path d="M6 18v-3M12 18v-7M18 18v-3"/><path d="M9 7l3-3 3 3"/>',
    'steppers': '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2.5V6M15 2.5V6M9 18v3.5M15 18v3.5M2.5 9H6M2.5 15H6M18 9h3.5M18 15h3.5"/>',
    'filament': '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.5"/><path d="M20 12h2.5"/>',
    'move': '<path d="M12 3v18M3 12h18M12 3L9 6M12 3l3 3M12 21l-3-3M12 21l3-3M3 12l3-3M3 12l3 3M21 12l-3-3M21 12l-3 3"/>',
    'gcode': '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/>',
    'more': '<circle cx="6" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="18" cy="12" r="1.2"/>',
    'pid': '<path d="M3 20h18"/><path d="M3 16c3 0 3-9 6-9s3 6 6 6 3-4 6-4"/>',
    'volume': '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>',
    'brightness': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/>',
    'eeprom': '<path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 4v4h4"/><path d="M12 8v4l3 2"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    'probe': '<path d="M9 3h6v8H9z"/><path d="M10.5 11v5l1.5 3 1.5-3v-5"/><path d="M6 21h12"/>',
    'stop': '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    'adjust': '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/>',
    'pause': '<path d="M9 5v14M15 5v14"/>',
    'play': '<path d="M8 5l11 7-11 7z"/>',
    'home': '<path d="M4 11l8-7 8 7"/><path d="M6 9.5V20h12V9.5"/>',
    'up': '<path d="M12 19V5M6 11l6-6 6 6"/>',
    'down': '<path d="M12 5v14M6 13l6 6 6-6"/>',
    'left': '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    'right': '<path d="M5 12h14M13 6l6 6-6 6"/>',
    'retract': '<path d="M12 20V8M7 13l5-5 5 5"/><path d="M5 4h14"/>',
    'extrude': '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M5 20h14"/>',
    'clear': '<path d="M20 5H9l-6 7 6 7h11z"/><path d="M11 9l6 6M17 9l-6 6"/>',
    'send': '<path d="M4 12l16-8-6 16-2.5-6.5z"/><path d="M11.5 13.5L20 4"/>',
    'check': '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    'x': '<path d="M6 6l12 12M18 6L6 18"/>',
    'warning': '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>',
    'power': '<path d="M12 3v8"/><path d="M6.3 6.8a8 8 0 1 0 11.4 0"/>',
    'unlock': '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7.5-2"/>',
    'lock': '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    'file': '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>',
    'folder': '<path d="M3 6h7l2 2h9v11H3z"/>',
    'parent': '<path d="M9 14L4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
    'timer': '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2M9 2h6"/>',
    'height': '<path d="M12 3v18M8 7l4-4 4 4M8 17l4 4 4-4"/>',
    'z': '<path d="M7 6h10L7 18h10"/>',
    'minus': '<path d="M6 12h12"/>',
    'plus': '<path d="M12 6v12M6 12h12"/>',
    'save': '<path d="M5 4h11l3 3v13H5z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>',
    'sensor': '<circle cx="9" cy="12" r="6"/><circle cx="9" cy="12" r="1.8"/><path d="M17.5 8.5a5.5 5.5 0 0 1 0 7M20.5 6a9.5 9.5 0 0 1 0 12"/>',
}


def glyph(im, name, size, color, x, y, stroke=1.8):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
           f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{GLYPHS[name]}</svg>')
    g = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size))).convert('RGBA')
    im.paste(g, (int(x), int(y)), g)


STYLES = {  # role, size, colour
    'title': ('cond', 21, TEXT),
    'label': ('text', 12, MUTED),
    'text': ('text', 14, TEXT),
    'btn': ('cond', 17, TEXT),
    'btn_acc': ('cond', 17, WHITE),
    'row': ('cond', 21, TEXT),
    'row_acc': ('cond', 21, WHITE),
    'tile': ('cond', 16, TEXT),
    'big': ('cond', 23, TEXT),
    'brand': ('bold', 20, TEXT),
    'num': ('cond', 16, TEXT),
    'numsmall': ('text', 12, MUTED),
    'key': ('cond', 18, TEXT),
}


def text(d, s, x, y, style, anchor='la'):
    role, size, color = STYLES[style]
    d.text((x, y), s, font=font(role, size), fill=rgb(color), anchor=anchor)


# ------------------------------------------------------------------------------------------ text icons
NLANG = len(LANGS)


class TextLib:
    def __init__(self):
        self.icons = {}
        self.cache = {}
        self.shrunk = []

    def custom(self, name, images):
        """One pre-drawn image per language, stored like a label."""
        if name not in self.cache:
            base = len(self.icons)
            for j, im in enumerate(images):
                self.icons[base + j] = im
            self.cache[name] = (base, images[0].size)
        return self.cache[name]

    def label(self, key, style, bg, width=None, align='left', maxw=None):
        """Returns (icon_base, (w, h)). Every translation shares one size, so a position works in every language.
        A translation wider than the room (width, or maxw) is drawn with a smaller font, down to 70 %."""
        ck = (key, style, bg, width, align, maxw)
        if ck in self.cache:
            return self.cache[ck]
        role, size, color = STYLES[style]
        limit = (width - 4) if width else maxw
        fonts, boxes = [], []
        for lang, t in zip(LANGS, S[key]):
            s = size
            while True:
                f = font(role, s, lang)
                bb = f.getbbox(t, anchor='ls')
                if not limit or bb[2] - bb[0] <= limit or s <= int(size * 0.7):
                    break
                s -= 1
            if limit and bb[2] - bb[0] > limit:
                raise ValueError(f'label {key!r} ({lang}) is {bb[2] - bb[0]}px, room is {limit}px')
            if s != size:
                self.shrunk.append((key, lang, size, s))
            fonts.append(f)
            boxes.append(bb)
        # common baseline: the tallest ascent and descent over all languages at the nominal size
        asc = max(max(-bb[1] for bb in boxes), max(font(role, size, l).getmetrics()[0] for l in ('en', 'hi', 'ja')) - 2)
        desc = max(max(bb[3] for bb in boxes), 3)
        h = asc + desc + 2
        w = width or (max(bb[2] - bb[0] for bb in boxes) + 4)
        base = len(self.icons)
        for j, (t, f, bb) in enumerate(zip(S[key], fonts, boxes)):
            im = Image.new('RGB', (w, h), rgb(bg))
            tw = bb[2] - bb[0]
            x = 2 - bb[0] if align == 'left' else (w - tw) // 2 - bb[0] if align == 'center' else w - 2 - tw - bb[0]
            ImageDraw.Draw(im).text((x, 1 + asc), t, font=f, fill=rgb(color), anchor='ls')
            self.icons[base + j] = im
        self.cache[ck] = (base, (w, h))
        return self.cache[ck]


TL = TextLib()


# ------------------------------------------------------------------------------------------ page model
class Page:
    def __init__(self, pid, name, title=None, back=True, status=True):
        self.pid, self.name = pid, name
        self.im = Image.new('RGB', (W, H), rgb(BG))
        self.d = ImageDraw.Draw(self.im)
        self.vars = []
        self.touch = []
        if title is not None:
            self.d.rectangle((0, 0, W, 39), fill=rgb(BAR))
            self.d.line((0, 39, W, 39), fill=rgb(LINE))
            if back:
                glyph(self.im, 'back', 24, ICON, 9, 8)
                self.d.line((40, 8, 40, 31), fill=rgb(LINE))
            if title:
                self.label(title, 50 if back else 14, 20, 'title', BAR, valign='center', maxw=(218 - 50) if back else 204)
            if status:
                self.vars.append(db.var_text(0x3000, (222, 11, 472, 29), c565(MUTED), 32, 18, 18))  # one line, centred in the bar

    # background helpers
    def rect(self, r, fill=CARD, outline=LINE, radius=10):
        self.d.rounded_rectangle(r, radius=radius, fill=rgb(fill), outline=rgb(outline) if outline else None)

    def field(self, r):
        self.d.rounded_rectangle(r, radius=7, fill=rgb(FIELD), outline=rgb(FIELD_LINE))

    def glyph(self, name, size, color, x, y, stroke=1.8):
        glyph(self.im, name, size, color, x, y, stroke)

    def text(self, s, x, y, style, anchor='la'):
        text(self.d, s, x, y, style, anchor)

    # translated label (icon) placed at x, y (top-left) or centred on cx / cy
    def label(self, key, x, y, style, bg, width=None, align='left', halign='left', valign='top', maxw=None):
        if maxw is None and not width:
            maxw = W - 8 - x
        if halign == 'center' and align == 'left':
            align = 'center'   # centred labels: centre each translation inside the shared box
        base, (w, h) = TL.label(key, style, bg, width, align, maxw)
        if halign == 'center':
            x = x - w // 2
        if valign == 'center':
            y = y - h // 2
        self.vars.append(db.var_icon(LANG_VP, int(x), int(y), 0, NLANG - 1, base, base + NLANG - 1, TEXT_LIB))
        return w, h

    # compound widgets
    def button(self, r, icon, key=None, style='btn', accent=False, gsize=22):
        x0, y0, x1, y1 = r
        fill = ACC if accent else CARD
        self.rect(r, fill, ACC if accent else LINE, 9)
        col = WHITE if accent else ICON
        cy = (y0 + y1) // 2
        if key:
            st = style + ('_acc' if accent and not style.endswith('_acc') else '')
            base, (w, h) = TL.label(key, st, fill, maxw=(x1 - x0) - gsize - 24)
            total = gsize + 8 + w
            gx = x0 + max(8, ((x1 - x0) - total) // 2)
            self.glyph(icon, gsize, col, gx, cy - gsize // 2)
            self.vars.append(db.var_icon(LANG_VP, gx + gsize + 8, cy - h // 2, 0, NLANG - 1, base, base + NLANG - 1, TEXT_LIB))
        else:
            self.glyph(icon, gsize, col, (x0 + x1) // 2 - gsize // 2, cy - gsize // 2)

    def tile(self, r, icon, key, gsize=34):
        x0, y0, x1, y1 = r
        self.rect(r, CARD, LINE, 10)
        self.glyph(icon, gsize, ICON, (x0 + x1) // 2 - gsize // 2, (y0 + y1) // 2 - gsize // 2 - 12)
        base, (w, h) = TL.label(key, 'tile', CARD, width=x1 - x0 - 8, align='center')
        self.vars.append(db.var_icon(LANG_VP, x0 + 4, (y0 + y1) // 2 + gsize // 2 - 4, 0, NLANG - 1, base, base + NLANG - 1, TEXT_LIB))

    def data(self, vp, x, y, fx, n_int, n_dot, color=TEXT, align=0, v_type=0, zero=0):
        self.vars.append(db.var_data(vp, int(x), int(y), c565(color), fx, n_int, n_dot, v_type, align, zero))

    def data_in(self, vp, r, fx, n_int, n_dot, color=TEXT, v_type=0):
        """Numeric value centred in the field r."""
        chars = n_int + (1 + n_dot if n_dot else 0)
        w = chars * fx
        x0, y0, x1, y1 = r
        self.data(vp, (x0 + x1) // 2 - w // 2, (y0 + y1) // 2 - fx, fx, n_int, n_dot, color, 2, v_type)

    def temp_block(self, x, y, label_key, icon, cur_vp, tgt_vp, bg, big=14, small=8):
        """Label + current (big) °C + / target °C, as on the home page."""
        self.glyph(icon, 15, MUTED, x - 1, y + 1)
        self.label(label_key, x + 18, y - 1, 'label', bg)
        vy = y + 20
        self.data(cur_vp, x, vy, big, 3, 1, TEXT, 2, 0, 1)
        ux = x + 5 * big + 3
        self.text('°C', ux, vy + 5, 'num')
        self.text('/', ux + 23, vy + 8, 'numsmall')
        self.data(tgt_vp, ux + 33, vy + 6, small, 3, 0, MUTED, 2)
        self.text('°C', ux + 33 + 3 * small + 3, vy + 8, 'numsmall')


