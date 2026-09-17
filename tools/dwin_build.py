#!/usr/bin/env python3
"""Field-level encoders/decoders for DGUS II (T5UID1) DWIN_SET binaries.

Formats established against DGUS-reloaded 1.0.3 and CR-10S Pro 1.60.8 files and
against the decompiled DGUS Tool V7.383 (DwinTerminal.dll, DW_ICON.exe).
All multi-byte integers are big-endian.
"""
import struct
from PIL import Image

# ----------------------------------------------------------------------------- 13_touch.bin
# Common 16-byte head of every touch record:
#   0x00 u8  (voice_id << 2) | (page >> 8 & 3)   voice_id = WAV file id played on press (0 = none)
#   0x01 u8  page & 0xFF
#   0x02 u16 xs, 0x04 u16 ys, 0x06 u16 xe, 0x08 u16 ye  (inclusive corners)
#   0x0A u16 pic_next  (0xFF00 = no page switch)
#   0x0C u16 pic_on    (0xFF00 = no pressed-effect page)
#   0x0E u16 tp_code   (0xFExx function with auto-upload, 0xFDxx without, else ASCII key code)
NO_PAGE = 0xFF00
TOUCH_FN_LEN = {0x00: 64, 0x01: 48, 0x02: 32, 0x03: 32, 0x04: 48, 0x05: 32, 0x06: 64}


def touch_head(page, rect, next_page=None, on_page=None, tp_code=0xFE05, voice=0):
    xs, ys, xe, ye = rect
    b0 = ((voice & 0x3F) << 2) | ((page >> 8) & 3)
    return struct.pack('>BB4HHHH', b0, page & 0xFF, xs, ys, xe, ye,
                       NO_PAGE if next_page is None else next_page,
                       NO_PAGE if on_page is None else on_page, tp_code)


def touch_key(page, rect, keycode, on_page=None, next_page=None, voice=0):
    """16-byte keyboard key (used on popup keyboard pages)."""
    return touch_head(page, rect, next_page, on_page, keycode, voice)


def touch_return_key(page, rect, vp, key, vp_mode=0, hold=0, upload=True, voice=0, on_page=None, next_page=None):
    """0xFE05 Return Key Code, 32 bytes."""
    body = struct.pack('>BHBHB9x', 0xFE, vp, vp_mode, key & 0xFFFF, hold)
    return touch_head(page, rect, next_page, on_page, 0xFE05 if upload else 0xFD05, voice) + body


def touch_popup_menu(page, rect, vp, menu_page, menu_area, menu_pos, vp_mode=0, translucent=0, voice=0,
                     on_page=None, next_page=None, upload=True):
    """0xFE01 Popup Menu, 48 bytes."""
    body = struct.pack('>BHBH4HH', 0xFE, vp, vp_mode, menu_page, *menu_area, menu_pos[0])
    body += struct.pack('>BHB12x', 0xFE, menu_pos[1], translucent)
    return touch_head(page, rect, next_page, on_page, 0xFE01 if upload else 0xFD01, voice) + body


def touch_num_input(page, rect, vp, n_int, n_dot, kb_page, kb_area, kb_pos, v_type=0, cursor=(0, 0),
                    color=0, lib=0, font_x=0, cursor_color=0, hide_en=1, kb_source=1, limit=None,
                    ret_set=0, ret_vp=0, ret_data=0, gamma=0, voice=0, on_page=None, next_page=None, upload=True):
    """0xFE00 Variable Data Input, 64 bytes. limit=(min,max) enables range check (0xFF)."""
    b1 = struct.pack('>BHBBBHHHBBBB', 0xFE, vp, v_type, n_int, n_dot, cursor[0], cursor[1], color,
                     lib, font_x, cursor_color, hide_en)
    b2 = struct.pack('>BBH4H2H', 0xFE, kb_source, kb_page, *kb_area, *kb_pos)
    lo, hi = limit if limit is not None else (0, 0)
    b3 = struct.pack('>BBiiBHHB', 0xFE, 0xFF if limit is not None else 0x00, lo, hi, ret_set, ret_vp, ret_data, gamma)
    return touch_head(page, rect, next_page, on_page, 0xFE00 if upload else 0xFD00, voice) + b1 + b2 + b3


def touch_slider(page, adj_area, vp, v_begin, v_end, adj_mode=0, rect=None, screen=(480, 272), voice=0, upload=True):
    """0xFE03 Drag adjustment, 32 bytes.  Tool widens the touch rect by 32 px along the drag axis."""
    xs, ys, xe, ye = adj_area
    if rect is None:
        w, h = screen
        if adj_mode & 0x0F:  # vertical
            rect = (xs, max(ys - 32, 0), xe, min(ye + 32, h))
        else:
            rect = (max(xs - 32, 0), ys, min(xe + 32, w), ye)
    body = struct.pack('>BHB4HHH', 0xFE, vp, adj_mode, xs, ys, xe, ye, v_begin & 0xFFFF, v_end & 0xFFFF)
    return touch_head(page, rect, None, None, 0xFE03 if upload else 0xFD03, voice) + body


def touch_text_input(page, rect, vp, max_words, kb_page, kb_area, kb_pos, scan_start, scan_end, scan_mode=1,
                     lib=0, font_x=16, font_y=16, cursor_color=0, color=0, return_mode=0, kb_source=1,
                     display_en=0, gamma=0, voice=0, upload=True):
    """0xFE06 ASCII text input, 64 bytes (layout from DwinTerminal TextInput.GetByte)."""
    b1 = struct.pack('>BHBBBBBBHHHB', 0xFE, vp, max_words, scan_mode, lib, font_x, font_y, cursor_color, color,
                     scan_start[0], scan_start[1], return_mode)
    b2 = struct.pack('>BHHBH4H', 0xFE, scan_end[0], scan_end[1], kb_source, kb_page, *kb_area)
    b3 = struct.pack('>BHHBB9x', 0xFE, kb_pos[0], kb_pos[1], display_en, gamma)
    return touch_head(page, rect, None, None, 0xFE06 if upload else 0xFD06, voice) + b1 + b2 + b3


def touch_incdec(page, rect, vp, step, v_min, v_max, increment=True, loop=False, vp_mode=0, key_mode=0,
                 voice=0, on_page=None, next_page=None, upload=True):
    """0xFE02 Incremental adjustment, 32 bytes."""
    body = struct.pack('>BHBBBHHHB3x', 0xFE, vp, vp_mode, 1 if increment else 0, 1 if loop else 0,
                       step & 0xFFFF, v_min & 0xFFFF, v_max & 0xFFFF, key_mode)
    return touch_head(page, rect, next_page, on_page, 0xFE02 if upload else 0xFD02, voice) + body


def build_13(records):
    """records must already be sorted by page (then by priority, first = highest). Terminator FF FF."""
    return b''.join(records) + b'\xff\xff'


# ----------------------------------------------------------------------------- 14_variable.bin
def var_data(vp, x, y, color, font_x, n_int, n_dot, v_type=0, align=0, zero_flag=0, lib=0, unit=b'', sp=0xFFFF):
    """0x10 Data variable (32 bytes). align: 0 left 1 right 2 centre; zero_flag -> bit 6 (DGUS 7.36 'zeroDisplay')."""
    assert len(unit) <= 11
    return struct.pack('>BBHHHHHHBBBBBBB', 0x5A, 0x10, sp, 0x000D, vp, x, y, color, lib, font_x,
                       align | (0x40 if zero_flag else 0), n_int, n_dot, v_type, len(unit)) + unit.ljust(11, b'\0')


def var_text(vp, box, color, length, font_x, font_y, encode=0x02, font0=0, font1=0, hdis=0, vdis=0, pos=None, sp=0xFFFF):
    """0x11 Text display (32 bytes). box=(xs,ys,xe,ye); pos defaults to box top-left."""
    x, y = pos if pos else box[:2]
    return struct.pack('>BBHHHHHH4HHBBBBBBBB', 0x5A, 0x11, sp, 0x000D, vp, x, y, color, *box, length,
                       font0, font1, font_x, font_y, encode, hdis, vdis, 0)


def var_icon(vp, x, y, v_min, v_max, icon_min, icon_max, lib, mode=0, layer=0, icon_gamma=0, pic_gamma=0, filt=0, sp=0xFFFF):
    """0x00 Variable icon (32 bytes). mode 0 = transparent (key colour filtered)."""
    return struct.pack('>BBHHHHHHHHHBBBBBB6x', 0x5A, 0x00, sp, 0x000A, vp, x, y, v_min & 0xFFFF, v_max & 0xFFFF,
                       icon_min, icon_max, lib, mode, layer, icon_gamma, pic_gamma, filt)


def var_slider_icon(vp, v_begin, v_end, pos_begin, pos_end, icon, cross, lib, vertical=0, x_adj=0, icon_mode=0,
                    vp_mode=0, layer=0, icon_gamma=0, pic_gamma=0, filt=0, sp=0xFFFF):
    """0x02 Slider display (32 bytes)."""
    return struct.pack('>BBHHHHHHHHHbBBBBBBBB3x', 0x5A, 0x02, sp, 0x000C, vp, v_begin, v_end, pos_begin, pos_end,
                       icon, cross, x_adj, vertical, lib, icon_mode, vp_mode, layer, icon_gamma, pic_gamma, filt)


def var_bit_icon(vp, act_bits, x, y, lib, icon0s, icon1s, icon0e=0, icon1e=0, disp_mode=0, move_mode=0, icon_mode=0,
                 dis_mov=0, vp_aux=0, filt=0, sp=0xFFFF):
    """0x06 Bit icon (32 bytes)."""
    return struct.pack('>BBHHHHHBBBBHHHHHHHBB', 0x5A, 0x06, sp, 0x000D, vp, vp_aux, act_bits, disp_mode, move_mode,
                       icon_mode, lib, icon0s, icon0e, icon1s, icon1e, x, y, dis_mov, filt, 0)


def build_14(pages, max_page):
    """pages: {page_id: [32-byte records in priority order]}; max_page: highest picture id of the project."""
    hdr = bytes([0x14]) + b'DGUS_2' + bytes([0x10]) + struct.pack('>H', max_page) + bytes(6)
    index = bytearray()
    data = bytearray()
    off = 0x4000
    for p in range((0x4000 - 0x10) // 4):
        recs = pages.get(p, [])
        assert len(recs) <= 255 and all(len(r) == 32 for r in recs)
        assert off + 32 * len(recs) <= 0xFFFFFF
        index += struct.pack('>BBH', len(recs), (off >> 16) & 0xFF, off & 0xFFFF)  # byte1 = offset high byte (inferred)
        data += b''.join(recs)
        off += 32 * len(recs)
    return hdr + bytes(index) + bytes(data) + b'\xff' * 32


# ----------------------------------------------------------------------------- 22_config.bin
def build_22(init=None):
    """init: {vp: bytes}; byte offset = 2*VP; file is 0x20004 bytes (last 4 unused)."""
    buf = bytearray(0x20004)
    for vp, val in (init or {}).items():
        buf[2 * vp:2 * vp + len(val)] = val
    return bytes(buf)


# ----------------------------------------------------------------------------- *.ico (T5 16bpp)
def rgb565_be(img):
    img = img.convert('RGB')
    out = bytearray()
    for r, g, b in img.getdata():
        v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out += struct.pack('>H', v)
    return bytes(out)


def build_ico(icons, data_order=None):
    """icons: {icon_id: PIL.Image}. Header 0x40000 bytes of 8-byte entries indexed by icon id.
    entry: w&FF, h&FF, (w>>8)<<6 | (h>>8)<<4 | (off>>24 & F), off>>16, off>>8, off (offset in WORDS),
           key colour = RGB565 of pixel (0,0) (big-endian)."""
    hdr = bytearray(0x40000)
    data = bytearray()
    order = data_order or sorted(icons)
    for i in order:
        im = icons[i].convert('RGB')
        w, h = im.size
        assert w < 1024 and h < 1024
        px = rgb565_be(im)
        off_words = (0x40000 + len(data)) // 2
        entry = bytes([w & 0xFF, h & 0xFF, ((w >> 8) << 6) | ((h >> 8) << 4) | ((off_words >> 24) & 0xF),
                       (off_words >> 16) & 0xFF, (off_words >> 8) & 0xFF, off_words & 0xFF]) + px[0:2]
        hdr[8 * i:8 * i + 8] = entry
        data += px
    return bytes(hdr) + bytes(data)


def parse_ico(d):
    icons = {}
    for i in range(0x40000 // 8):
        e = d[8 * i:8 * i + 8]
        if e == bytes(8):
            continue
        w = e[0] | ((e[2] >> 6) & 3) << 8
        h = e[1] | ((e[2] >> 4) & 3) << 8
        off = ((e[2] & 0xF) << 24) | (e[3] << 16) | (e[4] << 8) | e[5]
        icons[i] = (w, h, 2 * off, e[6:8])
    return icons
