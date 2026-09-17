# DWIN T5UID1 (DGUS II) DWIN_SET: binary formats for scripted generation

Target: DMT48270T043_07W, a 480x272 T5UID1 screen with 128 MB NAND, driven by Marlin `DGUS_LCD_UI RELOADED`.
Goal: build a complete `DWIN_SET` from Python, without the Windows DGUS tool.

Report date: 2026-09-17.

## 0. How much of this is proven

| Tag | Meaning |
|---|---|
| **[DATA]** | Checked on real files with Python. Each field was decoded, re-encoded and compared byte for byte. |
| **[TOOL]** | Read from the decompiled DGUS Tool V7.383 (`DwinTerminal.dll`, `DW_ICON.exe`, `DW_0Font.exe`). This is the program that writes these files, so it is authoritative for the file layout, but it does not tell us how the screen firmware reads them. |
| **[DOC]** | Taken from DWIN documentation only. |
| **[INFERRED]** | My reading of the evidence. It is not proven. |

**Main result [DATA]:** `tools/verify_roundtrip.py` rebuilds these files from decoded fields and gets **byte-identical** output:
- `13_touch.bin`
- `14_variable.bin`
- `22_config.bin`
- the four `.ico` libraries (24, 27, 30, 37), built from the project's source BMP icons

The same encoders also rebuild the 350 touch records of a second project, the Creality CR-10S Pro 1.60.8 set, byte for byte. That set was made with an older DGUS tool.

**None of these files has a checksum, CRC or signature.** A byte-identical rebuild is only possible because there is none.

### Reference material used

| Source | Where |
|---|---|
| DGUS Reloaded 1.0.3 set (the reference) | [Neo2003/DGUS-reloaded 1.0.3](https://github.com/Neo2003/DGUS-reloaded/releases/tag/1.0.3); the files this generator reuses are in `base/DWIN_SET` |
| DGUS project sources | the same repository: `project/TFT/*.tft` (.NET BinaryFormatter) and `project/*/N.bmp` (icon sources) |
| Second real T5UID1 set | Creality CR-10S Pro screen firmware 1.60.8 (`juliandroid/DWIN_CR_10s_Pro`) |
| DGUS Tool V7.383 | DWIN's Windows tool that writes these files, read for the file layout |
| DWIN docs | T5UID1 Development Guide V2.1, T5L DGUS II guide, DGUS Development Guide V4.3 |
| Marlin | `Marlin/src/lcd/extui/dgus_reloaded/` |
| DgusDude, dwin-ico-tools | dwin-ico-tools covers the **T5UIC1** JPEG ICO, which is a different format and does not apply here. |

### Tools (in `tools/`)

| Script | Purpose |
|---|---|
| `dwin_dump.py` | Decodes 13/14 into markdown tables, with Marlin VP names when `MARLIN` points to a Marlin checkout |
| `dwin_build.py` | **Field-level encoders**: touch records, display records, `build_13`, `build_14`, `build_22`, `build_ico`, `parse_ico` |
| `verify_roundtrip.py` | Byte-identical proof against the real set |
| `hzk_asc.py` | Reads and renders `0_DWIN_ASC.HZK` |
| `build_screen.py`, `screen_kit.py`, `strings.py` | The DGUS Reloaded 2.0 generator, its drawing kit and its translations |

Conventions: **all multi-byte fields are big-endian**. Coordinates are in pixels in 0° panel orientation. Colours are RGB565.

---

## 1. `13_touch.bin`: touch controls

### 1.1 File layout [DATA][TOOL]
- There is **no header**. The file is a plain run of records followed by **`FF FF`**. Nothing else follows: no padding, no CRC. Real file: 208 records, terminator at 0x1900, size 6402.
- **Record size depends on the type: 16, 32, 48 or 64 bytes.** Each 16-byte continuation block starts with `0xFE`.
- **Order** (from `TDocumentSpace.BuildInputBinFile`):
  - pages come in ascending picture ID;
  - within a page, the controls are the tool's object list **reversed** (the object drawn last comes first);
  - display controls are skipped.
- The DGUS docs say the earlier a record appears, the higher its touch priority. [DOC]
- **The order inside a page is part of the Marlin interface [DATA + Marlin code].** Marlin enables and disables touch controls through the `0x00B0` interface with bytes `5A A5 00 <page> <ctrl_id> <type> 00 <0|1>`. Here `ctrl_id` is the **0-based index of the record among all records of that page** (all types counted) in `13_touch.bin`. Checked against `DGUS_Control.h`:

  | Page | Marlin constant | Record index |
  |---|---|---|
  | PRINT (2) | FILE0..4 | 1..5 |
  | PRINT (2) | GO_BACK / SCROLL_UP / SCROLL_DOWN | 6 / 7 / 8 |
  | PRINT_STATUS (3) | PAUSE / RESUME | 1 / 2 |
  | LEVELING_AUTOMATIC (13) | DISABLE | 5 (counting only return-key records would give 3, which does not match) |
  | SETTINGS_MENU2 (18) | EXTRA2 | 6 |
  | WAIT (249) | ABORT / CONTINUE | 1 / 2 |

  On page 249, index 0 is a dummy record (`FD05`, VP 0, 10x10 px at 0,0) that shifts the others. **A generator must keep these indices.**
- Size limit: "13*.BIN ≤ 32 KB" (T5UID1 guide) [DOC]. The T5L guide says 256 KB. Stay under 32 KB.

### 1.2 Common 16-byte head [DATA][TOOL]

| Off | Size | Field | Notes |
|---|---|---|---|
| 0x00 | 1 | `(voice_id << 2) \| (page >> 8 & 3)` | See the voice note below the table. |
| 0x01 | 1 | page & 0xFF | |
| 0x02 | 2 | Xs | Touch rectangle, top-left |
| 0x04 | 2 | Ys | |
| 0x06 | 2 | Xe | Bottom-right. The tool writes `left+width`, `top+height`. |
| 0x08 | 2 | Ye | |
| 0x0A | 2 | Pic_Next | Page to switch to. `0xFF00` = no switch. DGUS-reloaded never uses it: Marlin switches pages with `0x84`. |
| 0x0C | 2 | Pic_On | Pressed-effect picture. The firmware copies the same rectangle from that full-screen picture while the key is pressed. `0xFF00` = none. |
| 0x0E | 2 | TP_Code | `0xFExx` = function `xx` with auto-upload. `0xFDxx` = same without upload. Any other value = 16-byte keyboard key with that key code (ASCII, `0x00F0` cancel, `0x00F1` OK, `0x00F2` backspace, `0x00F7/F8` cursor left/right, `0x00FF` popup-menu cancel; `0x2131`-style high/low pairs for shifted text keys). |

**Voice ID (byte 0x00).**
- The DGUS tool writes `b0 = (b0 & 3) + IVRCode*4` when the button's "voice" option is on [TOOL]. It reads it back as `page = ((b0&3)<<8)|b1` and `voice = b0>>2`.
- DGUS-reloaded uses `0x08`, meaning WAV **#2** (`02_click.wav`), on every button. It uses `0x00` (silent) on the hidden Debug button and on the dummy record, which matches `IVRing=false` in the `.tft` files [DATA].
- The CR-10S Pro set uses 4/8/12/16/20, which match its files `1 yes`/`2 no`/`3 sure`/`4 return`/`5 key.WAV` [DATA].
- The physical-keypad variant (`Keying`) sets Xs = `0xFFFF` and puts the key code in byte 0x04. This is not used here [TOOL].

### 1.3 Function bodies (bytes 0x10 onward)

**`FE05` Return Key Code: 32 bytes [DATA][TOOL][DOC]**

| Off | Size | Field |
|---|---|---|
| 0x10 | 1 | 0xFE |
| 0x11 | 2 | VP |
| 0x13 | 1 | VP_Mode (0 = whole word, 1 = high byte, 2 = low byte, 0x10–0x1F = bit n) |
| 0x14 | 2 | Key_Code (value written to VP and uploaded) |
| 0x16 | 1 | Hold_Time (0.1 s) |
| 0x17 | 9 | 0 |

**`FE01` Popup Menu: 48 bytes [DATA][TOOL]**

| Off | Size | Field |
|---|---|---|
| 0x10 | 1 | 0xFE |
| 0x11 | 2 | VP |
| 0x13 | 1 | VP_Mode |
| 0x14 | 2 | Pic_Menu (picture holding the menu) |
| 0x16 | 8 | Area_Menu Xs,Ys,Xe,Ye (cut from Pic_Menu) |
| 0x1E | 2 | Menu_Pos_X (paste position) |
| 0x20 | 1 | 0xFE |
| 0x21 | 2 | Menu_Pos_Y |
| 0x23 | 1 | Translucent (tool writes 255*Layer_Gama/100; 0 = opaque) |
| 0x24 | 12 | 0 |

Inside the menu picture, the buttons are **16-byte key records on the menu page itself** (for example page 204: keys `0x0001` and `0x00FF`, Pic_On 205). The chosen key code is written to VP and uploaded. `0xFF` is cancel.

**`FE00` Variable Data Input (numeric keypad): 64 bytes [DATA][TOOL][DOC]**

| Off | Size | Field |
|---|---|---|
| 0x10 | 1 | 0xFE |
| 0x11 | 2 | VP |
| 0x13 | 1 | V_Type (0 int16, 1 int32, 2 VP high byte, 3 VP low byte, 4 int64, 5 float) |
| 0x14 | 1 | N_Int |
| 0x15 | 1 | N_Dot (decimal places; the value is scaled by 10^N_Dot) |
| 0x16 | 4 | Cursor X,Y (right-aligned echo of the typed number) |
| 0x1A | 2 | Colour |
| 0x1C | 1 | Lib_ID (font) |
| 0x1D | 1 | Font_Hor (x dots) |
| 0x1E | 1 | Cursor colour (0 = black) |
| 0x1F | 1 | Hide_En (0 = show `*`) |
| 0x20 | 1 | 0xFE |
| 0x21 | 1 | KB_Source (0 = keypad drawn on the current page, 1 = keypad taken from another page) |
| 0x22 | 2 | PIC_KB |
| 0x24 | 8 | AREA_KB (cut) |
| 0x2C | 4 | Paste position X,Y |
| 0x30 | 1 | 0xFE |
| 0x31 | 1 | Limits_En (0xFF = on) |
| 0x32 | 4 | V_min (signed int32) |
| 0x36 | 4 | V_max (signed int32) |
| 0x3A | 1 | Return_Set |
| 0x3B | 2 | Return_VP |
| 0x3D | 2 | Return_Data |
| 0x3F | 1 | Layer_Gama |

Keypad keys are 16-byte key records on the keypad page (202) with Pic_On 203.

**`FE03` Slider (drag adjust): 32 bytes [DATA][TOOL]**

| Off | Size | Field |
|---|---|---|
| 0x10 | 1 | 0xFE |
| 0x11 | 2 | VP |
| 0x13 | 1 | Adj_Mode (high nibble: 0 word / 1 VP_H / 2 VP_L; low nibble: 0 horizontal / 1 vertical) |
| 0x14 | 8 | Adjust area Xs,Ys,Xe,Ye |
| 0x1C | 2 | V_begin |
| 0x1E | 2 | V_end |

**The touch rectangle in the head is not the object rectangle.** The tool widens the adjust area by **32 px on both sides along the drag axis**, clamped to the screen [TOOL]. Real example: area 129..349 becomes touch area 97..381 [DATA].

**`FE06` ASCII text input: 64 bytes [DATA][TOOL]**

| Off | Size | Field |
|---|---|---|
| 0x10 | 1 | 0xFE |
| 0x11 | 2 | VP |
| 0x13 | 1 | VP_Len_Max (words) |
| 0x14 | 1 | Scan_Mode (0 = re-input, 1 = edit existing) |
| 0x15 | 1 | Lib_ID |
| 0x16 | 1 | Font_Hor |
| 0x17 | 1 | Font_Ver |
| 0x18 | 1 | Cursor colour |
| 0x19 | 2 | Colour |
| 0x1B | 4 | Echo area start X,Y |
| 0x1F | 1 | Return mode |
| 0x20 | 1 | 0xFE |
| 0x21 | 4 | Echo area end X,Y |
| 0x25 | 1 | KB_Source |
| 0x26 | 2 | PIC_KB |
| 0x28 | 8 | KB area |
| 0x30 | 1 | 0xFE |
| 0x31 | 4 | KB paste position X,Y |
| 0x35 | 1 | Display_En |
| 0x36 | 1 | Gamma |
| 0x37 | 9 | 0 |

The DGUS docs note that `VP-1` is reserved for input status.

**`FE02` Incremental adjust: 32 bytes.** Not used by DGUS-reloaded. Checked on the CR-10S Pro set [DATA][DOC].

| Off | Size | Field |
|---|---|---|
| 0x10 | 1 | 0xFE |
| 0x11 | 2 | VP |
| 0x13 | 1 | VP_Mode |
| 0x14 | 1 | Adj_Mode (0 = −, else +) |
| 0x15 | 1 | Loop |
| 0x16 | 2 | Step |
| 0x18 | 2 | V_Min |
| 0x1A | 2 | V_Max |
| 0x1C | 1 | Key_Mode (0 = repeat while held, 1 = once) |
| 0x1D | 3 | 0 |

`FE04` RTC input (48 bytes) is documented but not used here.

### 1.4 Types used by DGUS-reloaded 1.0.3 [DATA]

| Record | Count | Size |
|---|---|---|
| `FE05` | 98 | 32 |
| `FD05` (dummy) | 1 | 32 |
| `FE00` | 23 | 64 |
| `FE01` | 9 | 48 |
| `FE03` | 3 | 32 |
| `FE06` | 1 | 64 |
| 16-byte keys (pages 200, 202, 204–214) | 73 | 16 |

Full per-page table: **Appendix A.1**.

---

## 2. `14_variable.bin`: display controls

### 2.1 File layout ("DGUS_2" indexed format) [DATA on 2 projects][TOOL]

| Offset | Size | Content |
|---|---|---|
| 0x0000 | 16 | Header: `14` `44 47 55 53 5F 32` ("DGUS_2") `10` `<max_page u16>` `00×6` |
| 0x0010 | 4092×4 | Page index, one entry per page ID 0..4091: `count u8`, `00`, `offset u16` |
| 0x4000 | 32 × N | Records, page by page, contiguous |
| end | 32 | `FF × 32` terminator |

**Header.**
- `max_page` is the highest picture ID of the project, not the last page that has controls: 250 in DGUS-reloaded; 87 in CR-10S Pro, whose last page with controls is 85.
- Byte 7 is `0x10` in both samples. Its meaning is unknown: in the tool's other code path it would be VarCount/64, which gives 1 here. **Write `0x10`.** [DATA] The header and index are written by native `DWINDLL.dll` (`Func02`/`Func03`), which could not be decompiled.

**Page index.**
- `offset` is an absolute file offset. The first page's offset is `0x4000`.
- Every entry holds the running offset. Pages with no controls point to where the next page starts.
- Checked contiguous for all 4092 entries in both files [DATA].
- The index byte after `count` is 0 in both samples. It is probably the high byte of a 24-bit offset **[INFERRED]**. It never matters under 64 KB.

**Terminator.** 32 × `0xFF` [TOOL: `array3 = list + 32×0xFF`; DATA].

**Records.**
- Within a page, records are in the tool's object-list order (not reversed). For the same control type, the later record is drawn on top [DOC].
- Up to 255 per page (u8 count). The CFG "64/128 controls per page" bit is discussed in §7.
- DGUS-reloaded has at most 31 per page.

**Limits.** The file is stored in NAND font slots 14–17, so it must stay ≤ 1 MB [DOC T5UID1].

**Encryption.** The tool can also write an XOR-scrambled variant (`nJiami` path, fixed key table). The reference set is plain and works, so **write it plain** [DATA/TOOL].

### 2.2 Common 8-byte record head [DATA][DOC]

| Off | Size | Field | Notes |
|---|---|---|---|
| 0x00 | 1 | 0x5A | |
| 0x01 | 1 | Type | |
| 0x02 | 2 | SP | Description pointer; `0xFFFF` = none, used everywhere here. With an SP, the 32-byte record is also copied to RAM at SP so the host can move, recolour or hide the control at run time. |
| 0x04 | 2 | Len_Dsc | Description length in words: `000D` data/text/bit icon, `000A` var icon, `000C` slider. The older tool writes `0008` for var icon, and the firmware accepts both [DATA CR-10S]. |
| 0x06 | 2 | VP | A high byte of `0xFF` disables the control. |

### 2.3 Type bodies (offsets within the 32-byte record)

**`0x10` Data variable [DATA][TOOL][DOC]**

| Off | Size | Field |
|---|---|---|
| 0x08 | 4 | X,Y (top-left) |
| 0x0C | 2 | Colour |
| 0x0E | 1 | Lib_ID (font slot; 0 = `0_DWIN_ASC.HZK`) |
| 0x0F | 1 | Font x-dots (glyph is x × 2x from the 0# font) |
| 0x10 | 1 | Alignment (0 left, 1 right, 2 centre) plus bit 6 flag (see below) |
| 0x11 | 1 | Integer digits |
| 0x12 | 1 | Decimal digits (sum ≤ 20) |
| 0x13 | 1 | VarType (0 int16, 1 int32, 2 VP_H u8, 3 VP_L u8, 4 int64, 5 uint16, 6 uint32) |
| 0x14 | 1 | Unit length (0..11) |
| 0x15 | 11 | Unit ASCII, zero-padded |

On bit 6 (0x40): DGUS 7.36's `zeroDisplay=1` sets it. All 13 `zeroDisplay=1` controls have it, for example `0x42` on current temperatures [DATA, correlated with the .tft]. The firmware meaning is not confirmed: the DWIN docs only say "integer bit invalid zero display / non-display". **Copy what DGUS-reloaded does.**

**`0x11` Text [DATA][TOOL]**

| Off | Size | Field |
|---|---|---|
| 0x08 | 4 | X,Y (= box start) |
| 0x0C | 2 | Colour |
| 0x0E | 8 | Text box Xs,Ys,Xe,Ye |
| 0x16 | 2 | Text_Length (bytes) |
| 0x18 | 1 | Font0_ID |
| 0x19 | 1 | Font1_ID |
| 0x1A | 1 | Font X dots |
| 0x1B | 1 | Font Y dots |
| 0x1C | 1 | Encode_Mode (bit 7 = fixed pitch; low 7 bits: 0 8-bit, 1 GB2312, 2 GBK, 3 BIG5, 4 SJIS, 5 UNICODE) |
| 0x1D | 1 | HOR_Dis |
| 0x1E | 1 | VER_Dis |
| 0x1F | 1 | 0 |

- DGUS-reloaded uses `Encode=2` (GBK), `Font0=Font1=0`, X=Y ∈ {14, 18, 20, 22}.
- In modes 1–4, ASCII bytes are drawn from Font0 at **X/2 × Y**, which is the 0# font's N × 2N. That is why X = Y.
- The string ends at `0xFFFF`, `0x0000` or the box edge. Marlin space-pads [DOC].
- The tool ignores the `.tft` text-alignment field (`duiqi`). This record has no alignment field.

**`0x00` Variable icon [DATA][DOC]**

| Off | Size | Field |
|---|---|---|
| 0x08 | 4 | X,Y |
| 0x0C | 2 | V_Min |
| 0x0E | 2 | V_Max |
| 0x10 | 2 | Icon_Min |
| 0x12 | 2 | Icon_Max (linear map; values out of range show nothing) |
| 0x14 | 1 | Icon_Lib (ICO file ID) |
| 0x15 | 1 | Mode (0 = transparent, else opaque) |
| 0x16 | 1 | Layer_Mode |
| 0x17 | 1 | ICON_Gamma |
| 0x18 | 1 | PIC_Gamma |
| 0x19 | 1 | Filter_Set (0x01–0x3F) |
| 0x1A | 6 | 0 |

**`0x02` Slider icon [DATA][DOC]**

| Off | Size | Field |
|---|---|---|
| 0x08 | 2 | V_Begin |
| 0x0A | 2 | V_End |
| 0x0C | 2 | Pos_Begin |
| 0x0E | 2 | Pos_End (x for horizontal) |
| 0x10 | 2 | ICON_ID |
| 0x12 | 2 | Cross coordinate (y for horizontal) |
| 0x14 | 1 | X_Adj (signed) |
| 0x15 | 1 | Mode (0 horizontal / 1 vertical) |
| 0x16 | 1 | ICON_Lib |
| 0x17 | 1 | ICON_Mode |
| 0x18 | 1 | VP_Data_Mode |
| 0x19 | 1 | Layer_Mode |
| 0x1A | 1 | ICON_Gamma |
| 0x1B | 1 | PIC_Gamma |
| 0x1C | 1 | Filter_Set |
| 0x1D | 3 | 0 |

**`0x06` Bit icon [DATA][DOC]**

| Off | Size | Field |
|---|---|---|
| 0x08 | 2 | VP_AUX (0) |
| 0x0A | 2 | Act_Bit_Set (mask of bits handled by this record) |
| 0x0C | 1 | Display_Mode (0: bit0 → ICON0S, bit1 → ICON1S; 3: 0 → nothing, 1 → ICON1S; 1, 2, 4–7 use animation) |
| 0x0D | 1 | Move_Mode |
| 0x0E | 1 | Icon_Mode (0 = transparent) |
| 0x0F | 1 | Icon_Lib |
| 0x10 | 2 | ICON0S |
| 0x12 | 2 | ICON0E |
| 0x14 | 2 | ICON1S |
| 0x16 | 2 | ICON1E |
| 0x18 | 4 | X,Y |
| 0x1C | 2 | DIS_MOV |
| 0x1E | 1 | Filter_Set |
| 0x1F | 1 | 0 |

DGUS-reloaded uses one record per bit, each with its own position.

**Types used by DGUS-reloaded [DATA]:**

| Type | Count |
|---|---|
| `0x10` | 84 |
| `0x11` | 48 |
| `0x06` | 43 |
| `0x00` | 13 |
| `0x02` | 3 |

The progress bar is `0x00` icons 0..100 from libraries 30 and 37. Full per-page table: **Appendix A.2**.

---

## 3. `22_config.bin`: initial VP memory

[DATA][TOOL][DOC]
- The file is **0x20004 bytes**. Byte offset = **2 × VP**, big-endian words, so it covers VP 0x0000–0xFFFF. The trailing 4 bytes are unused (the tool allocates `new byte[131076]`).
- The tool fills it from each control's "initial value" (`InitData[VP*2…]`).
- On boot, the firmware copies 0x2000–0x1FFFF, which is VP 0x1000–0xFFFF, into user RAM. It does this only if CFG 0x08 bit 5 is set [DOC].
- DGUS-reloaded's file is **all zeros**, which is the power-on default anyway. Two equivalent choices: ship a zero file, or clear CFG bit 5 and omit the file.
- CR-10S Pro example: GBK text "迪文科技" at VP 0x1060, stored at byte 0x20C0.

---

## 4. `.ico` icon libraries (T5, 16 bpp)

### 4.1 Format [DATA on 13 files / 500 icons][TOOL: `DW_ICON.exe` `frmprogress.Buildconfigbin`/`buildPic`]

- **Directory:** the first **0x40000 bytes** (256 KB). It holds 8-byte entries, and **the entry index is the icon ID** (0..32767). Absent IDs are 8 × `00`.

  | Byte | Content |
  |---|---|
  | 0 | W & 0xFF |
  | 1 | H & 0xFF |
  | 2 | `(W>>8)<<6 \| (H>>8)<<4 \| (offset>>24 & 0x0F)` |
  | 3..5 | offset (24 low bits), **in words** from file start; the first icon is at word 0x20000 = byte 0x40000 |
  | 6..7 | **Key colour: RGB565 of the icon's pixel (0,0)**, big-endian. In DGUS-reloaded these are `0000` because every icon has a black corner. In CR-10S Pro they look like "garbage" (`FF1F`, `153C`…), but they equal pixel (0,0) in 500/500 icons. |

- **Pixels:** raw **RGB565 big-endian**, row by row from the top, **no compression, no alpha**.
  - Conversion is truncation: `R&0xF8, G&0xFC, B&0xF8`, no dithering.
  - Size = W × H × 2 bytes, starting at `2*offset`.
- **Data order is free.** The DGUS tool writes icons in file-name *string* order (0, 1, 10, 100, 11, …), and the directory points to them. Numeric order gives an equally valid file (same size, different offsets).
- File size = 0x40000 + Σ W×H×2. There is no padding and no trailer.
- **Checks:**
  - All 4 DGUS-reloaded ICOs rebuilt byte-identical from `project/<lib>/<id>.bmp`.
  - All 234 icons, pixel for pixel, match the BMP truncated to RGB565.
- **Limits.** The entry format allows 10-bit W/H [TOOL]. The tool treats W or H = 0 as 255.
  - The tool caps icons at 1024 px [DOC].
  - The T5UID1 guide (V1.4) says icons above 255×255 are supported.
  - The screen is 480×272.
- **Transparency.** Display controls with Mode/Icon_Mode = 0 (transparent) do not draw background-coloured pixels. Filter_Set (0x01–0x3F, 0 in DGUS-reloaded) sets the filter strength [DOC].
  - The key colour is stored per icon from pixel (0,0) [TOOL/DATA]. It is **[INFERRED]** that the firmware uses this stored colour and not a hard-coded black. The DGUS-reloaded icons all use a pure black background, so they cannot tell the two apart.
  - **Practical rule:** paint the background with one colour, make sure pixel (0,0) has it, and do not use that exact RGB565 value inside the icon.
  - Antialiasing toward black is what DGUS-reloaded does, and it looks correct on its dark theme.
- **Flash footprint.** An ICO occupies `ceil(size / 256 KB)` consecutive font slots starting at its ID [DOC, consistent with DATA]:
  - `24_icons` (282 KB) → 24–25
  - `27_buttons` (381 KB) → 27–28
  - `30_progress_left` (1.46 MB) → 30–35
  - `37_progress_right` → 37–42

**Not applicable:** `b-pub/dwin-ico-tools` and the creality customizer handle the **T5UIC1** ICO: 16-byte entries, 4 KB directory, JPEG payloads. That is a different screen family and a different format.

---

## 5. Background pictures (`NNN_*.bmp`)

- **Input format** [DATA]:
  - Windows BMP, `BITMAPINFOHEADER` (40 bytes), 24 bpp, BI_RGB, bottom-up (positive height), exactly **480×272**.
  - 35 of the 44 reference files are 391736 bytes, with 2 extra zero bytes after the pixels (`biSizeImage` = 391682). The other 9 are 391734 bytes (`biSizeImage` = 391680). Both work.
  - Pillow's `Image.save(..., 'BMP')` with RGB gives the 391734 variant.
- The T5 converts to RGB565 while loading from SD. The DGUS docs require 24-bit true colour at native resolution [DOC].
- **ID = leading decimal digits of the file name.** `001_home.bmp`, `1.bmp` and `20_x.bmp` all work; `x20.bmp` does not [DOC].
- DGUS-reloaded uses 0–22, 200–215, 240, 241 and 248–250.
- **Capacity** [DOC T5UID1 guide]: 128 MB NAND, of which **64 MB is picture memory, "250 pictures of 480×272"** (one picture is about 255 KB of RGB565).
  - DGUS-reloaded uses ID 250 (KILL screen), so IDs up to 250 are proven to work in the field.
  - Treat 0–250 as safe. 251–255 is **unverified**.
  - The UART JPEG command (`0xA6`, not used for SD) accepts picture IDs 0x00–0xF0 only.
- Orientation: design pictures at 0°; CFG 0x08 bits 1–0 rotate everything (see `extras/rotated/*.CFG`).
- **Other NAND regions** [DOC T5UID1 guide §1, §4]:
  - **Font space:** 64 MB = 256 slots × 256 KB, IDs 0–255.
  - **Audio:** 32 MB. It overlays the **back half of font space** (slots 128–255). There are 256 WAV IDs of 128 KB each; WAV ID *k* sits at font slot 128 + ⌊k/2⌋.
  - **WAV format:** 32 kHz, 16-bit, mono PCM; a file longer than 128 KB spans several IDs [DATA: 01/02/03 WAVs are 32 kHz mono 16-bit].
  - **NOR:** 320 KB for `.LIB` files.
  - **RAM:** 128 KB of VP space; user VPs are 0x1000–0xFFFF.

---

## 6. `0_DWIN_ASC.HZK` and fonts

### 6.1 Layout of the 0# ASCII font [DATA][TOOL]
- There is **no header**. The file holds **61 fixed-width bitmap fonts, sizes N = 4..64**, each **N wide × 2N high**, with **128 glyphs (codes 0x00–0x7F)**, one after another.
- **Glyph encoding:** 2N rows × `ceil(N/8)` bytes, MSB first, 1 = ink.
- **Offset of size N** = Σ over k < N of 128·ceil(k/8)·2k. It starts 0, 1024, 2304, 3840, 5632, 7680, 12288, …
  - This is identical to `MatFonts.Address[]` in DwinTerminal.
  - Total = **3 082 752 bytes**, which matches the file exactly. The file therefore spans font slots **0–11**.
- **Contents:**
  - 0x20–0x7E: normal ASCII.
  - 0x01–0x1F and 0x7F: CP437-style symbols (arrows, ♂, ♪, ↔, ▲▼…).
  - 0x00, 0x09, 0x0A, 0x0C, 0x0D: empty.
- **Nothing ≥ 0x80.** The DGUS-reloaded HZK differs slightly from the CR-10S Pro and InsanityAutomation copies (same layout, different glyphs).
- `tools/hzk_asc.py <font> <out dir> 8 10 14 20` renders glyph sheets.
- The DGUS tool's own generator (`DW_0Font.exe`) writes exactly this layout: sizes A1..A2, 128 glyphs, `num += i*2*128*ceil(i/8)`.

### 6.2 How controls pick a font
- **Font ID = NAND font slot = numeric prefix of the file name** (256 KB slots) [DOC].
  - `Lib_ID` (data variables, numeric input), `Font0_ID` and `Font1_ID` (text) hold that number.
  - ID 0 = `0_DWIN_ASC.HZK`.
- **Data variable (0x10):** uses Lib_ID with x-dots N and always draws N × 2N glyphs, so it is ASCII only. Lib_ID ≠ 0 must be an 8-bit, half-width font [DOC].
- **Text (0x11):**

  | Encode_Mode | Font0_ID | Font1_ID |
  |---|---|---|
  | 1–4 (GB2312 / GBK / BIG5 / SJIS) | ASCII font, glyph X/2 × Y | double-byte font |
  | 0 (8-bit) or 5 (UNICODE) | 0 | the font file that also contains ASCII |

  Source: DGUS V4.3 guide §8.3.5 and the T5L guide §7.13 [DOC].

### 6.3 Adding accented characters (for example French)
Today DGUS-reloaded uses GBK mode with Font1 = 0. Any byte ≥ 0x80 starts a GBK double-byte sequence that font 0 cannot draw, so Latin-1 or UTF-8 accents will not render.

**A. Recommended, lowest risk: rebuild `0_DWIN_ASC.HZK` with accents in the control-code slots** [format DATA-confirmed].
- Keep 0x20–0x7E. Put é è ê ë à â ç ù û ô î ï œ É È À Ç … into 0x01–0x1F (avoid 0x0A, 0x0D) and 0x7F. That is about 29 slots, which covers French lowercase and common capitals.
- Marlin (or the language layer) then maps UTF-8 to those codes before writing the text VP.
- This changes no control records and works in both GBK text and data variables.
- **Risk:** firmware handling of control bytes. 0x0D 0x0A is documented as a line break, and 0x00/0xFF end the string. Whether 0x01–0x1F glyphs are drawn is **[INFERRED]**: they exist in the stock font, which suggests they are drawable. Test once on the screen.

**B. True 8-bit code page:**
- Set `Encode_Mode = 0x00` and `Font1_ID = <slot>` (use 24–127, clear of icons), with X/Y dots = glyph size.
- File format **[TOOL: DGUS preview renderer `MatFonts`, not firmware-confirmed]**: raw glyph array, **256 glyphs indexed by byte value**, each `Y × ceil(X/8)` bytes, MSB first, no header.
- `DW_0Font.exe` also has a code-page mode (`CreateCharSetFile`: windows-1252, ISO-8859-1/15, …) that writes bare glyphs in code order.
- The firmware's exact expectation for 8-bit fonts (256 glyphs and 0x00-based, versus a range) is **unverified** and needs one hardware test.

**C. UNICODE (mode 5) or GBK fonts:**
- The preview renderer indexes double-byte fonts as `(b0-0xA1)*94 + (b1-0xA1)`, which is the classic GB2312 HZK layout [TOOL].
- The DWIN Unicode font file layout is **not established** here. No sample file was available, and the generator for it is not in DGUS V7.383.
- Not recommended without a reference file.

---

## 7. `T5UID1.CFG`

The file is 128 bytes in DGUS-reloaded (48 in CR-10S Pro). Unlisted bytes are 0. [DOC T5UID1 guide §5 + DATA]

| Off | Len | DGUS-reloaded | Meaning |
|---|---|---|---|
| 0x00 | 4 | `54 35 44 31` | "T5D1" magic |
| 0x04 | 2 | `0000` | `5AA5` = **format NAND** at next SD load (see `extras/flash_reset/T5UID1.CFG`) |
| 0x06 | 2 | `0000` | Clock/RTC calibration triggers (leave 0) |
| 0x08 | 1 | **`B8`** | System_Config1, see the bit list below |
| 0x09 | 2 | **`0044`** | UART2 baud divisor = 7833600 / baud. `0x0044` = 115200. This must match Marlin's `LCD_SERIAL` baud. |
| 0x0B | 5 | 0 | Standby backlight: `0x0B=5A` enables, `0x0C/0D` = bright/dim levels, `0x0E-0F` = timeout ×5 ms |
| 0x10 | 14 | 0 | LCD timing (`0x10=5AA5` enables; "not for user"). Keep 0; the kernel defaults fit the panel. |
| 0x20 | 3 | 0 | Boot picture (`0x20=5A`, `0x21-22` = ID). If unset, page 0 shows at boot. |
| 0x23 | 4 | 0 | Boot music (`0x23=5A`, ID, blocks, volume) |
| 0x27 | 3 | 0 | Touch panel config (`0x27=5A`, `0x28` type/mode: high nibble 0 = resistive, 1 = capacitive GT911…; `0x29` sensitivity 0..0x1F). "Not for user"; leave 0. |
| 0x2C | 1 | 0 | System_Config2, see the bit list below |
| 0x30 | 10 | 0 | SD download count check (`5AA5` + expected counts per type). Optional; leave 0. |
| 0x40 | … | 0 | SD folder rename / encryption. **Never set** in generated sets. |

**Byte 0x08, System_Config1** (value `B8`):
- bit 7 = **auto-upload of touch changes to UART2**. The guide's table says "0 = on", but its revision note and DGUS-reloaded say **1 = on**. Marlin needs it: it receives `5A A5 … 83 VP …` frames on touch.
- bit 6 = controls per page (0 = 64, 1 = 128). DGUS-reloaded uses 0 and has ≤ 31 per page. Its effect on the indexed 14.bin is unclear, so keep 0.
- bit 5 = load `22.bin`.
- bit 4 = SD interface enabled.
- bit 3 = touch tone.
- bit 2 = standby backlight.
- bits 1–0 = rotation (00 = 0°, 01 = 90°, 10 = 180°, 11 = 270°). Confirmed by `extras/rotated`: `B9`/`BA`/`BB`.

**Byte 0x2C, System_Config2:**
- bit 7: 1 = buzzer, 0 = audio player (WAV).
- bit 6: **UART CRC**. Must stay 0, because Marlin sends no CRC.
- bit 5: watchdog.
- bit 4: synchronous refresh.

DgusDude labels 0x08 bit 7 "CheckCRC". That is **wrong** for the CFG file: the CRC flag is at 0x2C bit 6.

The kernel files `T5UID1_V30.BIN` (GUI core) and `T5OS_V21_NOACK.BIN` (OS core) are only needed when upgrading the screen's firmware. Leaving them out of a routine set avoids re-flashing the kernel every time.

---

## 8. What limits scripted generation

1. **No checksums anywhere.** None of 13/14/22/ICO/HZK/BMP/CFG has one; the byte-identical rebuilds prove it. Optional SD count checks (CFG 0x30) and SD encryption (0x40) are off.
2. **File naming:**
   - Must be in a `DWIN_SET` folder at the SD root; FAT32 with 4 KB clusters [DOC].
   - IDs are the leading decimal digits.
   - Fixed names: `13*.bin`, `14*.bin`, `22*.bin`, `T5UID1*.CFG`, `0*.HZK` [DOC]; only the numeric prefix matters, and the upstream `rename.sh` just normalises the names the tool generates.
3. **Font-space map (256 KB slots, IDs 0–255):**

   | Slots | Use |
   |---|---|
   | 0–11 | 0# font (3 MB) |
   | 12 | Input method |
   | 13 | Touch (≤ 32 KB) |
   | 14–17 | Variables (≤ 1 MB) |
   | 22 | Init |
   | 23 | DWIN OS program in older docs |
   | 128–255 | Shared with WAV audio |

   Put ICO and extra fonts in **24–127**, and leave `ceil(size/256 KB)` slots for each file. The current ICOs use 24–25, 27–28, 30–35 and 37–42.
4. **Touch control indices are an API.** The per-page record order in 13.bin must match `DGUS_Control.h` (§1.1), including the dummy record on page 249.
5. **VP map is an API.** Every VP, VarType and decimal count must match `DGUS_Addr.h` and Marlin's `DGUS_VPList.cpp`:
   - text lengths 32/16/24;
   - PID values are int32 with 2 decimals;
   - `STATUS_PositionZ` is int32;
   - bit-icon masks follow `DGUS_Data.h`.
6. **Pages and popups are pictures.**
   - Pressed effects need a second full-screen BMP (the `*_sel` pages).
   - Popups and keypads are cut from their own pictures (keypad 202 → `(144,50)-(335,252)` pasted at `(144,40)`).
   - Each picture costs about 255 KB of 64 MB, with about 250 slots at most.
7. **14.bin native header/index code** (`DWINDLL.dll`) was not decompiled. The layout comes from two real files plus the tool's managed code. Byte 7 (`0x10`) and the second index byte are copied, not understood.
8. **Kernel dependency:** the indexed "DGUS_2" 14.bin is what DGUS ≥ 7.3x generates. Both samples run on T5 OS V2.x / GUI V2–3. A very old GUI kernel might expect the legacy fixed 2 KB-per-page 14.bin **[INFERRED]**. DGUS-reloaded's wiki already asks users to flash the kernel it ships.
9. **Unverified on hardware** (need one flash test each):
   - pictures 251–255;
   - whether the firmware uses the ICO key colour or always black;
   - how control codes 0x01–0x1F are drawn in text;
   - the 8-bit custom font layout.

---

## Appendix A: decoded reference tables (DGUS-reloaded 1.0.3)

The long-form version, with every field, comes from `tools/dwin_dump.py base/DWIN_SET`.
- `snd` = voice ID (WAV number) from byte 0.
- `on` = Pic_On.
- Pic_Next is `FF00` (no switch) in every record, so it is not shown.

### A.1 13_touch.bin (208 records, file order = priority order; `#` = 0-based index inside the page = control id used by 0x00B0)

| page | # | x1,y1,x2,y2 | snd | type | VP | value / parameters | on (pressed pic) |
|---|---|---|---|---|---|---|---|
| 1 | 0 | 50,77,158,185 | 2 | FE05 return key | 0x2001 SCREENCHANGE_SD | key=0x0002 | - |
| 1 | 1 | 185,77,293,185 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0006 | - |
| 1 | 2 | 320,77,428,185 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0009 | - |
| 2 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0001 | - |
| 2 | 1 | 91,59,381,86 | 2 | FE05 return key | 0x2004 SD_SelectFile | key=0x0000 | - |
| 2 | 2 | 91,89,381,116 | 2 | FE05 return key | 0x2004 SD_SelectFile | key=0x0001 | - |
| 2 | 3 | 91,119,381,146 | 2 | FE05 return key | 0x2004 SD_SelectFile | key=0x0002 | - |
| 2 | 4 | 91,149,381,176 | 2 | FE05 return key | 0x2004 SD_SelectFile | key=0x0003 | - |
| 2 | 5 | 91,179,381,206 | 2 | FE05 return key | 0x2004 SD_SelectFile | key=0x0004 | - |
| 2 | 6 | 388,70,426,108 | 2 | FE05 return key | 0x2005 SD_Scroll | key=0x0000 | - |
| 2 | 7 | 388,115,426,153 | 2 | FE05 return key | 0x2005 SD_Scroll | key=0x0001 | - |
| 2 | 8 | 388,160,426,198 | 2 | FE05 return key | 0x2005 SD_Scroll | key=0x0002 | - |
| 2 | 9 | 338,220,432,256 | 2 | FE05 return key | 0x2006 SD_Print | key=0x0000 | - |
| 3 | 0 | 13,222,123,258 | 2 | FE01 popup menu | 0x2007 STATUS_Abort | menu pic 204 area (118, 99, 360, 202) at (119,82) | - |
| 3 | 1 | 128,222,238,258 | 2 | FE01 popup menu | 0x2008 STATUS_Pause | menu pic 206 area (118, 99, 360, 202) at (119,82) | - |
| 3 | 2 | 242,222,352,258 | 2 | FE01 popup menu | 0x2009 STATUS_Resume | menu pic 208 area (118, 99, 360, 202) at (119,82) | - |
| 3 | 3 | 356,222,466,258 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0004 | - |
| 4 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0003 | - |
| 4 | 1 | 160,64,223,95 | 2 | FE00 num input | 0x2012 TEMP_SetTarget_H0 | int=3 dot=0 kb pic 202 [0,999] | - |
| 4 | 2 | 160,115,223,146 | 2 | FE00 num input | 0x2011 TEMP_SetTarget_Bed | int=3 dot=0 kb pic 202 [0,999] | - |
| 4 | 3 | 160,191,223,222 | 2 | FE00 num input | 0x4000 FAN0_Speed | int=3 dot=0 kb pic 202 [0,100] | - |
| 4 | 4 | 378,64,441,95 | 2 | FE00 num input | 0x200A ADJUST_SetFeedrate | int=3 dot=0 kb pic 202 [0,999] | - |
| 4 | 5 | 378,115,441,146 | 2 | FE00 num input | 0x200B ADJUST_SetFlowrate_CUR | int=3 dot=0 kb pic 202 [0,999] | - |
| 4 | 6 | 378,191,441,222 | 2 | FE00 num input | 0x200E ADJUST_SetBabystep | int=1 dot=2 kb pic 202 no limit | - |
| 4 | 7 | 385,158,434,190 | 2 | FE05 return key | 0x200F ADJUST_Babystep | key=0x0000 | - |
| 4 | 8 | 385,223,434,255 | 2 | FE05 return key | 0x200F ADJUST_Babystep | key=0x0001 | - |
| 5 | 0 | 185,222,295,258 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0001 | - |
| 6 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0001 | - |
| 6 | 1 | 131,79,233,181 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0007 | - |
| 6 | 2 | 247,79,349,181 | 2 | FE05 return key | 0x2014 TEMP_Cool | key=0xFFFE | - |
| 6 | 3 | 363,79,465,181 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0008 | - |
| 6 | 4 | 15,79,117,181 | 2 | FE01 popup menu | 0x2010 TEMP_Preset | menu pic 210 area (129, 99, 350, 202) at (129,84) | - |
| 7 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0006 | - |
| 7 | 1 | 253,66,316,97 | 2 | FE00 num input | 0x2012 TEMP_SetTarget_H0 | int=3 dot=0 kb pic 202 [0,999] | - |
| 7 | 2 | 252,163,315,194 | 2 | FE00 num input | 0x2011 TEMP_SetTarget_Bed | int=3 dot=0 kb pic 202 [0,999] | - |
| 7 | 3 | 193,105,286,141 | 2 | FE05 return key | 0x2014 TEMP_Cool | key=0x0000 | - |
| 7 | 4 | 193,202,286,238 | 2 | FE05 return key | 0x2014 TEMP_Cool | key=0xFFFF | - |
| 8 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0006 | - |
| 8 | 1 | 24,167,109,203 | 2 | FE05 return key | 0x4000 FAN0_Speed | key=0x0000 | - |
| 8 | 2 | 370,167,455,203 | 2 | FE05 return key | 0x4000 FAN0_Speed | key=0x0064 | - |
| 8 | 3 | 97,169,381,199 | 2 | FE03 slider | 0x4000 FAN0_Speed | area (129, 169, 349, 199) 0..100 | - |
| 8 | 4 | 259,96,322,127 | 2 | FE00 num input | 0x4000 FAN0_Speed | int=3 dot=0 kb pic 202 [0,100] | - |
| 9 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0001 | - |
| 9 | 1 | 56,45,158,147 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x000A | - |
| 9 | 2 | 56,158,158,260 | 2 | FE01 popup menu | 0x2015 STEPPER_Control | menu pic 212 area (118, 99, 360, 202) at (118,84) | - |
| 9 | 3 | 189,45,291,147 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x000F | - |
| 9 | 4 | 321,45,423,147 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0010 | - |
| 9 | 5 | 189,158,291,260 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0011 | - |
| 9 | 6 | 321,158,423,260 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0012 | - |
| 10 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0009 | - |
| 10 | 1 | 50,93,159,202 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x000C | - |
| 10 | 2 | 184,93,293,202 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x000D | - |
| 10 | 3 | 319,93,428,202 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x000B | - |
| 11 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x000A | - |
| 11 | 1 | 206,98,269,129 | 2 | FE00 num input | 0x2016 LEVEL_OFFSET_Set | int=1 dot=2 kb pic 202 no limit | - |
| 11 | 2 | 213,65,262,97 | 2 | FE05 return key | 0x2017 LEVEL_OFFSET_Step | key=0x0000 | - |
| 11 | 3 | 213,130,262,162 | 2 | FE05 return key | 0x2017 LEVEL_OFFSET_Step | key=0x0001 | - |
| 11 | 4 | 307,96,394,132 | 2 | FE05 return key | 0x201F MOVE_Home | key=0x0002 | - |
| 11 | 5 | 201,179,259,217 | 2 | FE05 return key | 0x2018 LEVEL_OFFSET_SetStep | key=0x0002 | - |
| 11 | 6 | 261,179,319,217 | 2 | FE05 return key | 0x2018 LEVEL_OFFSET_SetStep | key=0x0003 | - |
| 12 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x000A | - |
| 12 | 1 | 362,69,425,100 | 2 | FE00 num input | 0x2012 TEMP_SetTarget_H0 | int=3 dot=0 kb pic 202 [0,999] | - |
| 12 | 2 | 362,166,425,197 | 2 | FE00 num input | 0x2011 TEMP_SetTarget_Bed | int=3 dot=0 kb pic 202 [0,999] | - |
| 12 | 3 | 305,108,398,144 | 2 | FE05 return key | 0x2014 TEMP_Cool | key=0x0000 | - |
| 12 | 4 | 305,205,398,241 | 2 | FE05 return key | 0x2014 TEMP_Cool | key=0xFFFF | - |
| 12 | 5 | 88,122,150,184 | 2 | FE05 return key | 0x2019 LEVEL_MANUAL_Point | key=0x0001 | - |
| 12 | 6 | 24,186,86,248 | 2 | FE05 return key | 0x2019 LEVEL_MANUAL_Point | key=0x0002 | - |
| 12 | 7 | 152,186,214,248 | 2 | FE05 return key | 0x2019 LEVEL_MANUAL_Point | key=0x0003 | - |
| 12 | 8 | 152,58,214,120 | 2 | FE05 return key | 0x2019 LEVEL_MANUAL_Point | key=0x0004 | - |
| 12 | 9 | 24,58,86,120 | 2 | FE05 return key | 0x2019 LEVEL_MANUAL_Point | key=0x0005 | - |
| 13 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x000A | - |
| 13 | 1 | 154,181,217,212 | 2 | FE00 num input | 0x2012 TEMP_SetTarget_H0 | int=3 dot=0 kb pic 202 [0,999] | - |
| 13 | 2 | 86,220,179,256 | 2 | FE05 return key | 0x2014 TEMP_Cool | key=0x0000 | - |
| 13 | 3 | 365,181,428,212 | 2 | FE00 num input | 0x2011 TEMP_SetTarget_Bed | int=3 dot=0 kb pic 202 [0,999] | - |
| 13 | 4 | 296,220,389,256 | 2 | FE05 return key | 0x2014 TEMP_Cool | key=0xFFFF | - |
| 13 | 5 | 38,110,144,148 | 2 | FE05 return key | 0x201B LEVEL_AUTO_Disable | key=0x0000 | - |
| 13 | 6 | 38,65,144,103 | 2 | FE05 return key | 0x201A LEVEL_AUTO_Probe | key=0x0000 | - |
| 15 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0009 | - |
| 15 | 1 | 242,61,305,92 | 2 | FE00 num input | 0x201D FILAMENT_SetLength | int=3 dot=0 kb pic 202 [0,999] | - |
| 15 | 2 | 127,105,231,143 | 2 | FE05 return key | 0x201E FILAMENT_Move | key=0x0000 | - |
| 15 | 3 | 248,105,352,143 | 2 | FE05 return key | 0x201E FILAMENT_Move | key=0x0001 | - |
| 15 | 4 | 250,176,313,207 | 2 | FE00 num input | 0x2012 TEMP_SetTarget_H0 | int=3 dot=0 kb pic 202 [0,999] | - |
| 15 | 5 | 193,215,286,251 | 2 | FE05 return key | 0x2014 TEMP_Cool | key=0x0000 | - |
| 16 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0009 | - |
| 16 | 1 | 56,76,119,107 | 2 | FE00 num input | 0x2020 MOVE_SetX | int=3 dot=1 kb pic 202 [0,9999] | - |
| 16 | 2 | 56,133,119,164 | 2 | FE00 num input | 0x2021 MOVE_SetY | int=3 dot=1 kb pic 202 [0,9999] | - |
| 16 | 3 | 56,190,119,221 | 2 | FE00 num input | 0x2022 MOVE_SetZ | int=3 dot=1 kb pic 202 [0,9999] | - |
| 16 | 4 | 237,218,295,256 | 2 | FE05 return key | 0x2024 MOVE_SetStep | key=0x0000 | - |
| 16 | 5 | 297,218,355,256 | 2 | FE05 return key | 0x2024 MOVE_SetStep | key=0x0001 | - |
| 16 | 6 | 357,218,415,256 | 2 | FE05 return key | 0x2024 MOVE_SetStep | key=0x0002 | - |
| 16 | 7 | 250,100,298,148 | 2 | FE05 return key | 0x201F MOVE_Home | key=0x0000 | - |
| 16 | 8 | 200,100,248,148 | 2 | FE05 return key | 0x2023 MOVE_Step | key=0x0001 | - |
| 16 | 9 | 301,100,349,148 | 2 | FE05 return key | 0x2023 MOVE_Step | key=0x0000 | - |
| 16 | 10 | 250,151,298,199 | 2 | FE05 return key | 0x2023 MOVE_Step | key=0x0003 | - |
| 16 | 11 | 250,50,298,98 | 2 | FE05 return key | 0x2023 MOVE_Step | key=0x0002 | - |
| 16 | 12 | 380,151,428,199 | 2 | FE05 return key | 0x2023 MOVE_Step | key=0x0005 | - |
| 16 | 13 | 380,50,428,98 | 2 | FE05 return key | 0x2023 MOVE_Step | key=0x0004 | - |
| 17 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0009 | - |
| 17 | 1 | 47,98,432,129 | 2 | FE06 text input | 0x4001 GCODE_Data | max 16 words, kb pic 200 | - |
| 17 | 2 | 131,153,234,191 | 2 | FE05 return key | 0x2025 GCODE_Clear | key=0x0000 | - |
| 17 | 3 | 244,153,347,191 | 2 | FE05 return key | 0x2026 GCODE_Execute | key=0x0000 | - |
| 18 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0009 | - |
| 18 | 1 | 56,45,158,147 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0013 | - |
| 18 | 2 | 188,45,290,147 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0014 | - |
| 18 | 3 | 321,45,423,147 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0015 | - |
| 18 | 4 | 56,158,158,260 | 2 | FE01 popup menu | 0x2027 EEPROM_Reset | menu pic 214 area (118, 99, 360, 202) at (118,84) | - |
| 18 | 5 | 188,158,290,260 | 2 | FE05 return key | 0x2028 SETTINGS2_Extra | key=0x0000 | - |
| 18 | 6 | 321,158,423,260 | 2 | FE05 return key | 0x2028 SETTINGS2_Extra | key=0x0001 | - |
| 19 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0012 | - |
| 19 | 1 | 168,104,231,135 | 2 | FE00 num input | 0x202A PID_SetTemp | int=3 dot=0 kb pic 202 [0,999] | - |
| 19 | 2 | 168,154,231,185 | 2 | FE00 num input | 0x4021 PID_Cycles | int=2 dot=0 kb pic 202 [3,10] | - |
| 19 | 3 | 111,202,204,240 | 2 | FE05 return key | 0x202B PID_Run | key=0x0000 | - |
| 19 | 4 | 170,49,236,85 | 2 | FE05 return key | 0x2029 PID_Select | key=0x0000 | - |
| 19 | 5 | 243,49,309,85 | 2 | FE05 return key | 0x2029 PID_Select | key=0xFFFF | - |
| 20 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0012 | - |
| 20 | 1 | 24,167,109,203 | 2 | FE05 return key | 0x4022 VOLUME_Level | key=0x0000 | - |
| 20 | 2 | 370,167,455,203 | 2 | FE05 return key | 0x4022 VOLUME_Level | key=0x0064 | - |
| 20 | 3 | 97,169,381,199 | 2 | FE03 slider | 0x4022 VOLUME_Level | area (129, 169, 349, 199) 0..100 | - |
| 20 | 4 | 251,96,314,127 | 2 | FE00 num input | 0x4022 VOLUME_Level | int=3 dot=0 kb pic 202 [0,100] | - |
| 21 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0012 | - |
| 21 | 1 | 24,167,109,203 | 2 | FE05 return key | 0x4023 BRIGHTNESS_Level | key=0x0000 | - |
| 21 | 2 | 370,167,455,203 | 2 | FE05 return key | 0x4023 BRIGHTNESS_Level | key=0x0064 | - |
| 21 | 3 | 97,169,381,199 | 2 | FE03 slider | 0x4023 BRIGHTNESS_Level | area (129, 169, 349, 199) 0..100 | - |
| 21 | 4 | 262,96,325,127 | 2 | FE00 num input | 0x4023 BRIGHTNESS_Level | int=3 dot=0 kb pic 202 [0,100] | - |
| 22 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0012 | - |
| 22 | 1 | 49,115,240,146 | - | FE05 return key | 0x5001 INFOS_Debug | key=0x0000 | - |
| 200 | 0 | 37,97,71,131 | 2 | key | - | 0x0031 '1' | 201 |
| 200 | 1 | 73,97,107,131 | 2 | key | - | 0x0032 '2' | 201 |
| 200 | 2 | 109,97,143,131 | 2 | key | - | 0x0033 '3' | 201 |
| 200 | 3 | 145,97,179,131 | 2 | key | - | 0x0034 '4' | 201 |
| 200 | 4 | 181,97,215,131 | 2 | key | - | 0x0035 '5' | 201 |
| 200 | 5 | 217,97,251,131 | 2 | key | - | 0x0036 '6' | 201 |
| 200 | 6 | 253,97,287,131 | 2 | key | - | 0x0037 '7' | 201 |
| 200 | 7 | 289,97,323,131 | 2 | key | - | 0x0038 '8' | 201 |
| 200 | 8 | 325,97,359,131 | 2 | key | - | 0x0039 '9' | 201 |
| 200 | 9 | 361,97,395,131 | 2 | key | - | 0x0030 '0' | 201 |
| 200 | 10 | 37,133,71,167 | 2 | key | - | 0x0051 'Q' | 201 |
| 200 | 11 | 73,133,107,167 | 2 | key | - | 0x0057 'W' | 201 |
| 200 | 12 | 109,133,143,167 | 2 | key | - | 0x0045 'E' | 201 |
| 200 | 13 | 145,133,179,167 | 2 | key | - | 0x0052 'R' | 201 |
| 200 | 14 | 181,133,215,167 | 2 | key | - | 0x0054 'T' | 201 |
| 200 | 15 | 217,133,251,167 | 2 | key | - | 0x0059 'Y' | 201 |
| 200 | 16 | 253,133,287,167 | 2 | key | - | 0x0055 'U' | 201 |
| 200 | 17 | 289,133,323,167 | 2 | key | - | 0x0049 'I' | 201 |
| 200 | 18 | 325,133,359,167 | 2 | key | - | 0x004F 'O' | 201 |
| 200 | 19 | 361,133,395,167 | 2 | key | - | 0x0050 'P' | 201 |
| 200 | 20 | 37,169,71,203 | 2 | key | - | 0x0041 'A' | 201 |
| 200 | 21 | 73,169,107,203 | 2 | key | - | 0x0053 'S' | 201 |
| 200 | 22 | 109,169,143,203 | 2 | key | - | 0x0044 'D' | 201 |
| 200 | 23 | 145,169,179,203 | 2 | key | - | 0x0046 'F' | 201 |
| 200 | 24 | 181,169,215,203 | 2 | key | - | 0x0047 'G' | 201 |
| 200 | 25 | 217,169,251,203 | 2 | key | - | 0x0048 'H' | 201 |
| 200 | 26 | 253,169,287,203 | 2 | key | - | 0x004A 'J' | 201 |
| 200 | 27 | 289,169,323,203 | 2 | key | - | 0x004B 'K' | 201 |
| 200 | 28 | 325,169,359,203 | 2 | key | - | 0x004C 'L' | 201 |
| 200 | 29 | 37,205,71,239 | 2 | key | - | 0x005A 'Z' | 201 |
| 200 | 30 | 73,205,107,239 | 2 | key | - | 0x0058 'X' | 201 |
| 200 | 31 | 109,205,143,239 | 2 | key | - | 0x0043 'C' | 201 |
| 200 | 32 | 145,205,179,239 | 2 | key | - | 0x0056 'V' | 201 |
| 200 | 33 | 181,205,215,239 | 2 | key | - | 0x0042 'B' | 201 |
| 200 | 34 | 217,205,251,239 | 2 | key | - | 0x004E 'N' | 201 |
| 200 | 35 | 253,205,287,239 | 2 | key | - | 0x004D 'M' | 201 |
| 200 | 36 | 397,97,443,131 | 2 | key | - | 0x00F2 | 201 |
| 200 | 37 | 397,133,443,167 | 2 | key | - | 0x00F0 | 201 |
| 200 | 38 | 361,169,443,203 | 2 | key | - | 0x00F1 | 201 |
| 200 | 39 | 289,205,323,239 | 2 | key | - | 0x002E '.' | 201 |
| 200 | 40 | 325,205,359,239 | 2 | key | - | 0x002D '-' | 201 |
| 200 | 41 | 361,205,401,239 | 2 | key | - | 0x00F7 | 201 |
| 200 | 42 | 403,205,443,239 | 2 | key | - | 0x00F8 | 201 |
| 202 | 0 | 148,93,191,128 | 2 | key | - | 0x0031 '1' | 203 |
| 202 | 1 | 195,93,238,128 | 2 | key | - | 0x0032 '2' | 203 |
| 202 | 2 | 242,93,285,128 | 2 | key | - | 0x0033 '3' | 203 |
| 202 | 3 | 289,93,332,128 | 2 | key | - | 0x00F2 | 203 |
| 202 | 4 | 148,133,191,168 | 2 | key | - | 0x0034 '4' | 203 |
| 202 | 5 | 195,133,238,168 | 2 | key | - | 0x0035 '5' | 203 |
| 202 | 6 | 242,133,285,168 | 2 | key | - | 0x0036 '6' | 203 |
| 202 | 7 | 289,133,332,168 | 2 | key | - | 0x00F0 | 203 |
| 202 | 8 | 148,173,191,208 | 2 | key | - | 0x0037 '7' | 203 |
| 202 | 9 | 195,173,238,208 | 2 | key | - | 0x0038 '8' | 203 |
| 202 | 10 | 242,173,285,208 | 2 | key | - | 0x0039 '9' | 203 |
| 202 | 11 | 242,213,285,248 | 2 | key | - | 0x002E '.' | 203 |
| 202 | 12 | 289,173,332,248 | 2 | key | - | 0x00F1 | 203 |
| 202 | 13 | 195,213,238,248 | 2 | key | - | 0x0030 '0' | 203 |
| 202 | 14 | 148,213,191,248 | 2 | key | - | 0x002D '-' | 203 |
| 204 | 0 | 129,155,230,191 | 2 | key | - | 0x0001 | 205 |
| 204 | 1 | 249,155,350,191 | 2 | key | - | 0x00FF | 205 |
| 206 | 0 | 129,155,230,191 | 2 | key | - | 0x0001 | 207 |
| 206 | 1 | 249,155,350,191 | 2 | key | - | 0x00FF | 207 |
| 208 | 0 | 129,155,230,191 | 2 | key | - | 0x0001 | 209 |
| 208 | 1 | 249,155,350,191 | 2 | key | - | 0x00FF | 209 |
| 210 | 0 | 313,98,351,136 | 2 | key | - | 0x00FF | - |
| 210 | 1 | 141,155,202,191 | 2 | key | - | 0x0001 | 211 |
| 210 | 2 | 209,155,270,191 | 2 | key | - | 0x0002 | 211 |
| 210 | 3 | 277,155,338,191 | 2 | key | - | 0x0003 | 211 |
| 212 | 0 | 129,155,230,191 | 2 | key | - | 0x0001 | 213 |
| 212 | 1 | 249,155,350,191 | 2 | key | - | 0x0002 | 213 |
| 212 | 2 | 323,98,361,136 | 2 | key | - | 0x00FF | - |
| 214 | 0 | 129,155,230,191 | 2 | key | - | 0x0001 | 215 |
| 214 | 1 | 249,155,350,191 | 2 | key | - | 0x00FF | 215 |
| 240 | 0 | 220,229,258,267 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x00F1 | - |
| 240 | 1 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0016 | - |
| 241 | 0 | 0,0,39,39 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x0016 | - |
| 241 | 1 | 220,38,258,76 | 2 | FE05 return key | 0x2000 SCREENCHANGE | key=0x00F0 | - |
| 248 | 0 | 100,94,208,202 | 2 | FE01 popup menu | 0x202C POWERLOSS_Abort | menu pic 204 area (118, 99, 360, 202) at (119,82) | - |
| 248 | 1 | 271,95,379,203 | 2 | FE01 popup menu | 0x202D POWERLOSS_Resume | menu pic 208 area (118, 99, 360, 202) at (119,82) | - |
| 249 | 0 | 0,0,10,10 | - | FD05 return key | 0x0000 | key=0x0000 | - |
| 249 | 1 | 128,222,238,258 | 2 | FE01 popup menu | 0x202E WAIT_Abort | menu pic 204 area (118, 99, 360, 202) at (119,82) | - |
| 249 | 2 | 242,222,352,258 | 2 | FE05 return key | 0x202F WAIT_Continue | key=0x0000 | - |

### A.2 14_variable.bin (191 records; header `14444755535f321000fa000000000000`)

| page | # | type | VP | x,y | parameters |
|---|---|---|---|---|---|
| 1 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 1 | 1 | 10 data | 0x30FF TEMP_Current_H0 | 78,227 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 1 | 2 | 10 data | 0x3100 TEMP_Target_H0 | 142,227 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=0 |
| 1 | 3 | 10 data | 0x30FC TEMP_Current_Bed | 332,227 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 1 | 4 | 10 data | 0x30FD TEMP_Target_Bed | 394,227 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=0 |
| 2 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 2 | 1 | 00 var icon | 0x3020 SD_Type | 57,57 | v 1..2 -> icon 0..1 lib 24 mode=0 |
| 2 | 2 | 00 var icon | 0x3021 | 57,87 | v 1..2 -> icon 0..1 lib 24 mode=0 |
| 2 | 3 | 00 var icon | 0x3022 | 57,117 | v 1..2 -> icon 0..1 lib 24 mode=0 |
| 2 | 4 | 00 var icon | 0x3023 | 57,147 | v 1..2 -> icon 0..1 lib 24 mode=0 |
| 2 | 5 | 00 var icon | 0x3024 | 57,177 | v 1..2 -> icon 0..1 lib 24 mode=0 |
| 2 | 6 | 11 text | 0x3025 SD_FileName0 | 91,65 | col=0xBDF7 box=(91, 65, 381, 83) len=32 f0=0 f1=0 18x18 enc=2 |
| 2 | 7 | 11 text | 0x3045 SD_FileName1 | 91,95 | col=0xBDF7 box=(91, 95, 381, 113) len=32 f0=0 f1=0 18x18 enc=2 |
| 2 | 8 | 11 text | 0x3065 SD_FileName2 | 91,125 | col=0xBDF7 box=(91, 125, 381, 143) len=32 f0=0 f1=0 18x18 enc=2 |
| 2 | 9 | 11 text | 0x3085 SD_FileName3 | 91,155 | col=0xBDF7 box=(91, 155, 381, 173) len=32 f0=0 f1=0 18x18 enc=2 |
| 2 | 10 | 11 text | 0x30A5 SD_FileName4 | 91,185 | col=0xBDF7 box=(91, 185, 381, 203) len=32 f0=0 f1=0 18x18 enc=2 |
| 2 | 11 | 11 text | 0x30C6 SD_SelectedFileName | 96,231 | col=0xBDF7 box=(96, 231, 324, 246) len=32 f0=0 f1=0 14x14 enc=2 |
| 2 | 12 | 06 bit icon | 0x30C5 SD_ScrollIcons | 392,74 | bits=0x0001 mode=0 icon0=2 icon1=3 lib 24 |
| 2 | 13 | 06 bit icon | 0x30C5 SD_ScrollIcons | 392,119 | bits=0x0002 mode=0 icon0=4 icon1=5 lib 24 |
| 2 | 14 | 06 bit icon | 0x30C5 SD_ScrollIcons | 392,164 | bits=0x0004 mode=0 icon0=6 icon1=7 lib 24 |
| 3 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 3 | 1 | 10 data | 0x30FF TEMP_Current_H0 | 81,54 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 3 | 2 | 10 data | 0x3100 TEMP_Target_H0 | 146,54 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=0 |
| 3 | 3 | 10 data | 0x30FC TEMP_Current_Bed | 81,100 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 3 | 4 | 10 data | 0x30FD TEMP_Target_Bed | 146,100 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=0 |
| 3 | 5 | 10 data | 0x30E6 STATUS_PositionZ | 295,54 | col=0xDEFB font#0 x=10 align=0 int=3 dot=2 vtype=1 |
| 3 | 6 | 11 text | 0x30E8 STATUS_Elapsed | 295,101 | col=0xDEFB box=(295, 101, 447, 121) len=15 f0=0 f1=0 20x20 enc=2 |
| 3 | 7 | 10 data | 0x30F7 STATUS_Percent | 215,154 | col=0xDEFB font#0 x=10 align=1 int=3 dot=0 vtype=5 |
| 3 | 8 | 00 var icon | 0x30F7 STATUS_Percent | 31,177 | v 0..100 -> icon 0..100 lib 30 mode=0 |
| 3 | 9 | 00 var icon | 0x30F7 STATUS_Percent | 241,177 | v 0..100 -> icon 0..100 lib 37 mode=0 |
| 3 | 10 | 06 bit icon | 0x31BE STATUS_Icons | 129,223 | bits=0x0001 mode=3 icon0=0 icon1=0 lib 27 |
| 3 | 11 | 06 bit icon | 0x31BE STATUS_Icons | 243,223 | bits=0x0002 mode=3 icon0=0 icon1=1 lib 27 |
| 4 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 4 | 1 | 10 data | 0x3100 TEMP_Target_H0 | 186,71 | col=0x1082 font#0 x=9 align=1 int=3 dot=0 vtype=0 |
| 4 | 2 | 10 data | 0x30FD TEMP_Target_Bed | 186,122 | col=0x1082 font#0 x=9 align=1 int=3 dot=0 vtype=0 |
| 4 | 3 | 10 data | 0x4000 FAN0_Speed | 186,198 | col=0x1082 font#0 x=9 align=1 int=3 dot=0 vtype=5 |
| 4 | 4 | 10 data | 0x30F8 ADJUST_Feedrate | 397,71 | col=0x1082 font#0 x=9 align=1 int=4 dot=0 vtype=0 |
| 4 | 5 | 10 data | 0x30F9 ADJUST_Flowrate_CUR | 397,122 | col=0x1082 font#0 x=9 align=1 int=4 dot=0 vtype=0 |
| 4 | 6 | 10 data | 0x3106 LEVEL_OFFSET_Current | 387,198 | col=0x1082 font#0 x=9 align=1 int=2 dot=2 vtype=0 |
| 5 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 5 | 1 | 10 data | 0x30FF TEMP_Current_H0 | 81,54 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 5 | 2 | 10 data | 0x3100 TEMP_Target_H0 | 146,54 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=0 |
| 5 | 3 | 10 data | 0x30FC TEMP_Current_Bed | 81,100 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 5 | 4 | 10 data | 0x30FD TEMP_Target_Bed | 146,100 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=0 |
| 5 | 5 | 10 data | 0x30E6 STATUS_PositionZ | 295,54 | col=0xDEFB font#0 x=10 align=0 int=3 dot=2 vtype=1 |
| 5 | 6 | 11 text | 0x30E8 STATUS_Elapsed | 295,101 | col=0xDEFB box=(295, 101, 447, 121) len=15 f0=0 f1=0 20x20 enc=2 |
| 5 | 7 | 10 data | 0x30F7 STATUS_Percent | 215,154 | col=0xDEFB font#0 x=10 align=1 int=3 dot=0 vtype=5 |
| 5 | 8 | 00 var icon | 0x30F7 STATUS_Percent | 31,177 | v 0..100 -> icon 0..100 lib 30 mode=0 |
| 5 | 9 | 00 var icon | 0x30F7 STATUS_Percent | 241,177 | v 0..100 -> icon 0..100 lib 37 mode=0 |
| 6 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 6 | 1 | 10 data | 0x30FF TEMP_Current_H0 | 78,227 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 6 | 2 | 10 data | 0x3100 TEMP_Target_H0 | 142,227 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=0 |
| 6 | 3 | 10 data | 0x30FC TEMP_Current_Bed | 332,227 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 6 | 4 | 10 data | 0x30FD TEMP_Target_Bed | 393,227 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=0 |
| 7 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 7 | 1 | 10 data | 0x30FF TEMP_Current_H0 | 192,73 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 7 | 2 | 10 data | 0x3100 TEMP_Target_H0 | 265,73 | col=0x1082 font#0 x=10 align=1 int=3 dot=0 vtype=0 |
| 7 | 3 | 10 data | 0x30FC TEMP_Current_Bed | 192,170 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 7 | 4 | 10 data | 0x30FD TEMP_Target_Bed | 264,170 | col=0x1082 font#0 x=10 align=1 int=3 dot=0 vtype=0 |
| 7 | 5 | 10 data | 0x3101 TEMP_Max_H0 | 382,73 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=5 |
| 7 | 6 | 10 data | 0x30FE TEMP_Max_Bed | 382,170 | col=0xDEFB font#0 x=10 align=2 int=3 dot=0 vtype=5 |
| 8 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 8 | 1 | 02 slider icon | 0x4000 FAN0_Speed | 126..326,172 | v 0..100 icon 8 lib 24 vertical=0 |
| 8 | 2 | 10 data | 0x4000 FAN0_Speed | 285,103 | col=0x1082 font#0 x=9 align=1 int=3 dot=0 vtype=5 |
| 9 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 9 | 1 | 00 var icon | 0x3105 STEPPER_Status | 76,170 | v 0..0 -> icon 9..9 lib 24 mode=0 |
| 10 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 11 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 11 | 1 | 10 data | 0x3106 LEVEL_OFFSET_Current | 215,105 | col=0x1082 font#0 x=9 align=1 int=2 dot=2 vtype=0 |
| 11 | 2 | 06 bit icon | 0x3107 LEVEL_OFFSET_StepIcons | 203,181 | bits=0x0004 mode=0 icon0=7 icon1=8 lib 27 |
| 11 | 3 | 06 bit icon | 0x3107 LEVEL_OFFSET_StepIcons | 263,181 | bits=0x0008 mode=0 icon0=9 icon1=10 lib 27 |
| 12 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 12 | 1 | 10 data | 0x30FF TEMP_Current_H0 | 302,76 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 12 | 2 | 10 data | 0x3100 TEMP_Target_H0 | 375,76 | col=0x1082 font#0 x=10 align=1 int=3 dot=0 vtype=0 |
| 12 | 3 | 10 data | 0x30FC TEMP_Current_Bed | 302,173 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 12 | 4 | 10 data | 0x30FD TEMP_Target_Bed | 373,173 | col=0x1082 font#0 x=10 align=1 int=3 dot=0 vtype=0 |
| 13 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 13 | 1 | 10 data | 0x30FF TEMP_Current_H0 | 94,188 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 13 | 2 | 10 data | 0x3100 TEMP_Target_H0 | 166,188 | col=0x1082 font#0 x=10 align=1 int=3 dot=0 vtype=0 |
| 13 | 3 | 10 data | 0x30FC TEMP_Current_Bed | 304,188 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 13 | 4 | 10 data | 0x30FD TEMP_Target_Bed | 377,188 | col=0x1082 font#0 x=10 align=1 int=3 dot=0 vtype=0 |
| 13 | 5 | 00 var icon | 0x3108 LEVEL_AUTO_DisableIcon | 40,112 | v 1..1 -> icon 2..2 lib 27 mode=0 |
| 13 | 6 | 10 data | 0x3109 LEVEL_AUTO_Grid | 186,140 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 7 | 10 data | 0x310A | 240,140 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 8 | 10 data | 0x310B | 294,140 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 9 | 10 data | 0x310C | 348,140 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 10 | 10 data | 0x310D | 402,140 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 11 | 10 data | 0x310E | 186,120 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 12 | 10 data | 0x310F | 240,120 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 13 | 10 data | 0x3110 | 294,120 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 14 | 10 data | 0x3111 | 348,120 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 15 | 10 data | 0x3112 | 402,120 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 16 | 10 data | 0x3113 | 186,100 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 17 | 10 data | 0x3114 | 240,100 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 18 | 10 data | 0x3115 | 294,100 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 19 | 10 data | 0x3116 | 348,100 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 20 | 10 data | 0x3117 | 402,100 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 21 | 10 data | 0x3118 | 186,80 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 22 | 10 data | 0x3119 | 240,80 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 23 | 10 data | 0x311A | 294,80 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 24 | 10 data | 0x311B | 348,80 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 25 | 10 data | 0x311C | 402,80 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 26 | 10 data | 0x311D | 186,60 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 27 | 10 data | 0x311E | 240,60 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 28 | 10 data | 0x311F | 294,60 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 29 | 10 data | 0x3120 | 348,60 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 13 | 30 | 10 data | 0x3121 | 402,60 | col=0xB5B6 font#0 x=8 align=1 int=2 dot=3 vtype=0 |
| 14 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 14 | 1 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 30,218 | bits=0x0001 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 2 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 68,218 | bits=0x0002 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 3 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 106,218 | bits=0x0004 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 4 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 144,218 | bits=0x0008 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 5 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 182,218 | bits=0x0010 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 6 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 30,180 | bits=0x0020 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 7 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 68,180 | bits=0x0040 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 8 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 106,180 | bits=0x0080 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 9 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 144,180 | bits=0x0100 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 10 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 182,180 | bits=0x0200 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 11 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 30,142 | bits=0x0400 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 12 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 68,142 | bits=0x0800 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 13 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 106,142 | bits=0x1000 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 14 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 144,142 | bits=0x2000 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 15 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 182,142 | bits=0x4000 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 16 | 06 bit icon | 0x3122 LEVEL_PROBING_Icons1 | 30,104 | bits=0x8000 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 17 | 06 bit icon | 0x3123 LEVEL_PROBING_Icons2 | 68,104 | bits=0x0001 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 18 | 06 bit icon | 0x3123 LEVEL_PROBING_Icons2 | 106,104 | bits=0x0002 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 19 | 06 bit icon | 0x3123 LEVEL_PROBING_Icons2 | 144,104 | bits=0x0004 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 20 | 06 bit icon | 0x3123 LEVEL_PROBING_Icons2 | 182,104 | bits=0x0008 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 21 | 06 bit icon | 0x3123 LEVEL_PROBING_Icons2 | 30,66 | bits=0x0010 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 22 | 06 bit icon | 0x3123 LEVEL_PROBING_Icons2 | 68,66 | bits=0x0020 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 23 | 06 bit icon | 0x3123 LEVEL_PROBING_Icons2 | 106,66 | bits=0x0040 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 24 | 06 bit icon | 0x3123 LEVEL_PROBING_Icons2 | 144,66 | bits=0x0080 mode=3 icon0=0 icon1=10 lib 24 |
| 14 | 25 | 06 bit icon | 0x3123 LEVEL_PROBING_Icons2 | 182,66 | bits=0x0100 mode=3 icon0=0 icon1=10 lib 24 |
| 15 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 15 | 1 | 10 data | 0x3125 FILAMENT_Length | 266,68 | col=0x1082 font#0 x=9 align=1 int=3 dot=0 vtype=5 |
| 15 | 2 | 10 data | 0x30FF TEMP_Current_H0 | 190,183 | col=0xDEFB font#0 x=10 align=2+0x40 int=3 dot=1 vtype=0 |
| 15 | 3 | 10 data | 0x3100 TEMP_Target_H0 | 263,183 | col=0x1082 font#0 x=10 align=1 int=3 dot=0 vtype=0 |
| 16 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 16 | 1 | 10 data | 0x3126 MOVE_CurrentX | 65,83 | col=0x1082 font#0 x=9 align=1 int=3 dot=1 vtype=0 |
| 16 | 2 | 10 data | 0x3127 MOVE_CurrentY | 65,140 | col=0x1082 font#0 x=9 align=1 int=3 dot=1 vtype=0 |
| 16 | 3 | 10 data | 0x3128 MOVE_CurrentZ | 65,197 | col=0x1082 font#0 x=9 align=1 int=3 dot=1 vtype=0 |
| 16 | 4 | 06 bit icon | 0x3129 MOVE_StepIcons | 239,220 | bits=0x0001 mode=0 icon0=3 icon1=4 lib 27 |
| 16 | 5 | 06 bit icon | 0x3129 MOVE_StepIcons | 299,220 | bits=0x0002 mode=0 icon0=5 icon1=6 lib 27 |
| 16 | 6 | 06 bit icon | 0x3129 MOVE_StepIcons | 359,220 | bits=0x0004 mode=0 icon0=7 icon1=8 lib 27 |
| 17 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 17 | 1 | 11 text | 0x4001 GCODE_Data | 64,104 | col=0x1082 box=(64, 104, 424, 128) len=32 f0=0 f1=0 22x22 enc=2 |
| 18 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 18 | 1 | 00 var icon | 0x312A SETTINGS2_BLTouch | 187,156 | v 0..1 -> icon 11..12 lib 27 mode=0 |
| 18 | 2 | 00 var icon | 0x312A SETTINGS2_BLTouch | 319,156 | v 1..1 -> icon 11..11 lib 27 mode=0 |
| 19 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 19 | 1 | 10 data | 0x312C PID_Temp | 194,111 | col=0x1082 font#0 x=9 align=1 int=3 dot=0 vtype=5 |
| 19 | 2 | 10 data | 0x4021 PID_Cycles | 194,161 | col=0x1082 font#0 x=9 align=1 int=3 dot=0 vtype=5 |
| 19 | 3 | 10 data | 0x312D PID_Kp | 348,111 | col=0xDEFB font#0 x=10 align=0 int=5 dot=2 vtype=1 |
| 19 | 4 | 10 data | 0x312F PID_Ki | 348,161 | col=0xDEFB font#0 x=10 align=0 int=5 dot=2 vtype=1 |
| 19 | 5 | 10 data | 0x3131 PID_Kd | 348,211 | col=0xDEFB font#0 x=10 align=0 int=5 dot=2 vtype=1 |
| 19 | 6 | 06 bit icon | 0x312B PID_HeaterIcons | 171,50 | bits=0x0002 mode=0 icon0=13 icon1=14 lib 27 |
| 19 | 7 | 06 bit icon | 0x312B PID_HeaterIcons | 244,50 | bits=0x0001 mode=0 icon0=15 icon1=16 lib 27 |
| 20 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 20 | 1 | 02 slider icon | 0x4022 VOLUME_Level | 126..326,172 | v 0..100 icon 8 lib 24 vertical=0 |
| 20 | 2 | 10 data | 0x4022 VOLUME_Level | 277,103 | col=0x1082 font#0 x=9 align=1 int=3 dot=0 vtype=5 |
| 21 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 21 | 1 | 02 slider icon | 0x4023 BRIGHTNESS_Level | 126..326,172 | v 0..100 icon 8 lib 24 vertical=0 |
| 21 | 2 | 10 data | 0x4023 BRIGHTNESS_Level | 288,103 | col=0x1082 font#0 x=9 align=1 int=3 dot=0 vtype=5 |
| 22 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 22 | 1 | 11 text | 0x3133 INFOS_Machine | 183,57 | col=0xB5B6 box=(183, 57, 438, 76) len=24 f0=0 f1=0 20x20 enc=2 |
| 22 | 2 | 11 text | 0x314B INFOS_BuildVolume | 183,79 | col=0xB5B6 box=(183, 79, 438, 98) len=24 f0=0 f1=0 20x20 enc=2 |
| 22 | 3 | 11 text | 0x3163 INFOS_Version | 183,101 | col=0xB5B6 box=(183, 101, 438, 120) len=16 f0=0 f1=0 20x20 enc=2 |
| 22 | 4 | 11 text | 0x3175 INFOS_PrintTime | 183,185 | col=0xB5B6 box=(183, 185, 438, 204) len=24 f0=0 f1=0 20x20 enc=2 |
| 22 | 5 | 11 text | 0x318D INFOS_LongestPrint | 183,207 | col=0xB5B6 box=(183, 207, 438, 226) len=24 f0=0 f1=0 20x20 enc=2 |
| 22 | 6 | 11 text | 0x31A5 INFOS_FilamentUsed | 183,229 | col=0xB5B6 box=(183, 229, 438, 248) len=24 f0=0 f1=0 20x20 enc=2 |
| 22 | 7 | 10 data | 0x3173 INFOS_TotalPrints | 182,163 | col=0xB5B6 font#0 x=10 align=0 int=5 dot=0 vtype=5 |
| 22 | 8 | 10 data | 0x3174 INFOS_FinishedPrints | 331,163 | col=0xB5B6 font#0 x=10 align=0 int=5 dot=0 vtype=5 |
| 240 | 0 | 10 data | 0x000F | 246,93 | col=0xB5B6 font#0 x=10 align=0 int=4 dot=0 vtype=2 |
| 240 | 1 | 10 data | 0x000F | 246,123 | col=0xB5B6 font#0 x=10 align=0 int=4 dot=0 vtype=3 |
| 240 | 2 | 11 text | 0x007C | 246,153 | col=0xB5B6 box=(246, 153, 431, 172) len=8 f0=0 f1=0 20x20 enc=2 |
| 241 | 0 | 06 bit icon | 0x0081 | 245,93 | bits=0x0040 mode=0 icon0=11 icon1=12 lib 24 |
| 241 | 1 | 06 bit icon | 0x0081 | 245,123 | bits=0x0020 mode=0 icon0=11 icon1=12 lib 24 |
| 241 | 2 | 06 bit icon | 0x0081 | 245,153 | bits=0x0010 mode=0 icon0=11 icon1=12 lib 24 |
| 241 | 3 | 06 bit icon | 0x0081 | 245,183 | bits=0x0004 mode=0 icon0=11 icon1=12 lib 24 |
| 248 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 249 | 0 | 11 text | 0x3000 MESSAGE_Status | 181,7 | col=0xBDAF box=(181, 7, 476, 26) len=32 f0=0 f1=0 18x18 enc=2 |
| 249 | 1 | 11 text | 0x1100 MESSAGE_Line1 | 67,73 | col=0xEF7D box=(67, 73, 429, 97) len=32 f0=0 f1=0 22x22 enc=2 |
| 249 | 2 | 11 text | 0x1120 MESSAGE_Line2 | 67,109 | col=0xDEFB box=(67, 109, 429, 133) len=32 f0=0 f1=0 22x22 enc=2 |
| 249 | 3 | 11 text | 0x1140 MESSAGE_Line3 | 67,145 | col=0xDEFB box=(67, 145, 429, 169) len=32 f0=0 f1=0 22x22 enc=2 |
| 249 | 4 | 11 text | 0x1160 MESSAGE_Line4 | 67,181 | col=0xDEFB box=(67, 181, 429, 205) len=32 f0=0 f1=0 22x22 enc=2 |
| 249 | 5 | 06 bit icon | 0x31BD WAIT_Icons | 129,223 | bits=0x0001 mode=3 icon0=0 icon1=17 lib 27 |
| 249 | 6 | 06 bit icon | 0x31BD WAIT_Icons | 243,223 | bits=0x0002 mode=3 icon0=0 icon1=18 lib 27 |
| 250 | 0 | 11 text | 0x1100 MESSAGE_Line1 | 149,80 | col=0xEF7D box=(149, 80, 475, 104) len=32 f0=0 f1=0 20x20 enc=2 |
| 250 | 1 | 11 text | 0x1120 MESSAGE_Line2 | 149,116 | col=0xEF7D box=(149, 116, 475, 140) len=32 f0=0 f1=0 20x20 enc=2 |
| 250 | 2 | 11 text | 0x1140 MESSAGE_Line3 | 149,152 | col=0xEF7D box=(149, 152, 475, 176) len=32 f0=0 f1=0 20x20 enc=2 |
| 250 | 3 | 11 text | 0x1160 MESSAGE_Line4 | 149,188 | col=0xEF7D box=(149, 188, 475, 212) len=32 f0=0 f1=0 20x20 enc=2 |
