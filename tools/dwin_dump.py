#!/usr/bin/env python3
"""Decode DGUS II (T5UID1) 13_touch.bin and 14_variable.bin into readable tables."""
import struct, sys, re, collections

import os
# Optional: names VPs after Marlin's DGUS_Addr.h (set MARLIN to a Marlin checkout).
MARLIN_ADDR = os.path.join(os.environ.get('MARLIN', ''), 'Marlin/src/lcd/extui/dgus_reloaded/config/DGUS_Addr.h')
VPNAMES = {}
try:
    for m in re.finditer(r'^\s*(\w+)\s*=\s*0x([0-9A-Fa-f]+)', open(MARLIN_ADDR).read(), re.M):
        VPNAMES[int(m.group(2), 16)] = m.group(1)
except OSError:
    pass

def vpn(vp):
    return f'0x{vp:04X}' + (f' {VPNAMES[vp]}' if vp in VPNAMES else '')

def page_str(w):
    return '-' if (w >> 8) == 0xFF else str(w)

# ---------------------------------------------------------------- 13_touch.bin
TOUCH_LEN = {0x00: 64, 0x01: 48, 0x02: 32, 0x03: 32, 0x04: 48, 0x05: 32, 0x06: 64}

def parse_touch(d):
    recs = []
    i = 0
    while i < len(d):
        if d[i:i+2] == b'\xff\xff':
            return recs, i
        pic, xs, ys, xe, ye, nxt, on, code = struct.unpack('>8H', d[i:i+16])
        if code >> 8 in (0xFE, 0xFD):
            n = TOUCH_LEN.get(code & 0xFF)
            if n is None:
                raise ValueError(f'unknown touch function 0x{code:04X} at 0x{i:X}')
        else:
            n = 16
        raw = d[i:i+n]
        # sanity: every 16-byte continuation block starts with 0xFE
        for k in range(16, n, 16):
            assert raw[k] == 0xFE, (hex(i), k, raw.hex())
        recs.append(dict(off=i, pic_hi=pic >> 8, page=pic & 0xFF, rect=(xs, ys, xe, ye),
                         next=nxt, on=on, code=code, raw=raw))
        i += n
    raise ValueError('no FFFF terminator')

def describe_touch(r):
    raw, code = r['raw'], r['code']
    if code >> 8 not in (0xFE, 0xFD):
        return 'KEY', f"keycode 0x{code:04X}" + (f" '{chr(code)}'" if 0x20 <= code < 0x7F else ''), ''
    fn = code & 0xFF
    vp = struct.unpack('>H', raw[0x11:0x13])[0]
    if fn == 0x05:
        mode = raw[0x13]; key = struct.unpack('>H', raw[0x14:0x16])[0]; hold = raw[0x16]
        return 'RETURN_KEY(05)', vpn(vp), f'mode={mode:#04x} key=0x{key:04X} hold={hold} tail0={raw[0x17:0x20]==bytes(9)}'
    if fn == 0x00:
        vtype, nint, ndot = raw[0x13], raw[0x14], raw[0x15]
        x, y, color = struct.unpack('>HHH', raw[0x16:0x1C])
        lib, fx, cur, hide = raw[0x1C], raw[0x1D], raw[0x1E], raw[0x1F]
        kbsrc = raw[0x21]; kbpic = struct.unpack('>H', raw[0x22:0x24])[0]
        kba = struct.unpack('>4H', raw[0x24:0x2C]); kbp = struct.unpack('>2H', raw[0x2C:0x30])
        lim = raw[0x31]; vmin, vmax = struct.unpack('>ii', raw[0x32:0x3A])
        rset = raw[0x3A]; rvp, rdata = struct.unpack('>HH', raw[0x3B:0x3F]); gama = raw[0x3F]
        return 'NUM_INPUT(00)', vpn(vp), (f'type={vtype} int={nint} dot={ndot} cursor=({x},{y}) color=0x{color:04X} lib={lib} fontx={fx} '
                f'curcol={cur} hide_en={hide} kb_src={kbsrc} kb_pic={kbpic} kb_area={kba} kb_pos={kbp} '
                f'limit_en=0x{lim:02X} min={vmin} max={vmax} ret_set={rset} ret_vp=0x{rvp:04X} ret_data={rdata} gamma={gama}')
    if fn == 0x01:
        mode = raw[0x13]; menu = struct.unpack('>H', raw[0x14:0x16])[0]
        area = struct.unpack('>4H', raw[0x16:0x1E]); px = struct.unpack('>H', raw[0x1E:0x20])[0]
        py = struct.unpack('>H', raw[0x21:0x23])[0]; tr = raw[0x23]
        return 'POPUP_MENU(01)', vpn(vp), f'mode={mode} menu_pic={menu} menu_area={area} pos=({px},{py}) translucent={tr} tail0={raw[0x24:0x30]==bytes(12)}'
    if fn == 0x03:
        mode = raw[0x13]; area = struct.unpack('>4H', raw[0x14:0x1C]); vb, ve = struct.unpack('>HH', raw[0x1C:0x20])
        return 'SLIDER(03)', vpn(vp), f'adj_mode=0x{mode:02X} area={area} v_begin={vb} v_end={ve}'
    if fn == 0x06:
        return 'TEXT_INPUT(06)', vpn(vp), 'raw+10=' + raw[0x10:].hex()
    if fn == 0x02:
        return 'INCDEC(02)', vpn(vp), raw[0x10:].hex()
    return f'FN{fn:02X}', vpn(vp), raw[0x10:].hex()

# ---------------------------------------------------------------- 14_variable.bin
def parse_var(d):
    assert d[1:7] == b'DGUS_2', d[:16]
    hdr = d[:16]
    maxpage = struct.unpack('>H', d[8:10])[0]
    pages = collections.OrderedDict()
    for p in range((0x4000 - 0x10) // 4):
        cnt, z, off = struct.unpack('>BBH', d[0x10 + 4*p:0x14 + 4*p])
        if cnt:
            pages[p] = [d[off + 32*k: off + 64*k - 32*k + 32] for k in range(cnt)]
    return hdr, maxpage, pages

def describe_var(r):
    assert r[0] == 0x5A
    t = r[1]; sp, ln, vp = struct.unpack('>HHH', r[2:8])
    if t == 0x10:
        x, y, color = struct.unpack('>HHH', r[8:14])
        lib, fx, align, nint, ndot, vtype, ulen = r[14], r[15], r[16], r[17], r[18], r[19], r[20]
        unit = r[21:21+ulen].decode('latin-1')
        return 'DATA(10)', sp, ln, vpn(vp), (x, y), (f'color=0x{color:04X} lib={lib} fontx={fx} align={align} int={nint} dot={ndot} '
                f'vtype={vtype} unit={unit!r} pad={r[21+ulen:].hex() or "-"}')
    if t == 0x11:
        x, y, color = struct.unpack('>HHH', r[8:14]); box = struct.unpack('>4H', r[14:22])
        tlen = struct.unpack('>H', r[22:24])[0]
        f0, f1, fx, fy, enc, hd, vd, z = r[24:32]
        return 'TEXT(11)', sp, ln, vpn(vp), (x, y), (f'color=0x{color:04X} box={box} len={tlen} font0={f0} font1={f1} '
                f'fx={fx} fy={fy} enc=0x{enc:02X} hdis={hd} vdis={vd} z={z}')
    if t == 0x00:
        x, y, vmin, vmax, imin, imax = struct.unpack('>6H', r[8:20])
        lib, mode, layer, ig, pg, filt = r[20:26]
        return 'VAR_ICON(00)', sp, ln, vpn(vp), (x, y), (f'v=[{vmin},{vmax}] icon=[{imin},{imax}] lib={lib} mode={mode} '
                f'layer={layer} icon_gamma={ig} pic_gamma={pg} filter={filt} tail={r[26:].hex()}')
    if t == 0x02:
        vb, ve, xb, xe, icon, yy = struct.unpack('>6H', r[8:20])
        xadj, mode, lib, imode, vpmode, layer, ig, pg, filt = r[20:29]
        return 'SLIDER_ICON(02)', sp, ln, vpn(vp), (xb, yy), (f'v=[{vb},{ve}] pos=[{xb},{xe}] icon={icon} y={yy} xadj={xadj} mode={mode} '
                f'lib={lib} icon_mode={imode} vp_mode={vpmode} layer={layer} ig={ig} pg={pg} filter={filt} tail={r[29:].hex()}')
    if t == 0x06:
        vpaux, act = struct.unpack('>HH', r[8:12]); dmode, mmode, imode, lib = r[12:16]
        i0s, i0e, i1s, i1e, x, y, dmov = struct.unpack('>7H', r[16:30]); filt = r[30]
        return 'BIT_ICON(06)', sp, ln, vpn(vp), (x, y), (f'vp_aux=0x{vpaux:04X} act_bits=0x{act:04X} disp_mode={dmode} move_mode={mmode} '
                f'icon_mode={imode} lib={lib} icon0=[{i0s},{i0e}] icon1=[{i1s},{i1e}] dis_mov={dmov} filter={filt} last={r[31]:#04x}')
    return f'TYPE{t:02X}', sp, ln, vpn(vp), None, r.hex()

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'base', 'DWIN_SET')
    td = open(f'{base}/13_touch.bin', 'rb').read()
    recs, end = parse_touch(td)
    print(f'## 13_touch.bin: {len(recs)} records, FFFF terminator at 0x{end:X}, file size {len(td)}')
    print('| page | hi | x1,y1,x2,y2 | next | on | type | VP | details |')
    print('|---|---|---|---|---|---|---|---|')
    for r in recs:
        typ, vp, det = describe_touch(r)
        print(f"| {r['page']} | 0x{r['pic_hi']:02X} | {','.join(map(str, r['rect']))} | {page_str(r['next'])} | {page_str(r['on'])} | {typ} | {vp} | {det} |")
    vd = open(f'{base}/14_variable.bin', 'rb').read()
    hdr, maxpage, pages = parse_var(vd)
    print(f'\n## 14_variable.bin: header {hdr.hex()} max page {maxpage}, size {len(vd)}')
    print('| page | # | type | SP | len | VP | x,y | details |')
    print('|---|---|---|---|---|---|---|---|')
    for p, rs in pages.items():
        for k, r in enumerate(rs):
            typ, sp, ln, vp, xy, det = describe_var(r)
            print(f'| {p} | {k} | {typ} | 0x{sp:04X} | {ln} | {vp} | {xy} | {det} |')

if __name__ == '__main__':
    main()
