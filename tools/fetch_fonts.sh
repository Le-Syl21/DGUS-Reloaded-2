#!/bin/sh
# Download the Noto Sans fonts the generator draws with (SIL Open Font License 1.1) into fonts/noto,
# pinned to a google/fonts commit and checked against their SHA-256.
set -eu
cd "$(dirname "$0")/.."
mkdir -p fonts/noto
REV=ea9bc40cb0323afec81e7f1005453eea36f51708
while read -r sum dir file; do
  out="fonts/noto/$file"
  if [ ! -f "$out" ] || ! echo "$sum  $out" | sha256sum -c --status; then
    url="https://raw.githubusercontent.com/google/fonts/$REV/ofl/$dir/$(echo "$file" | sed 's/\[/%5B/; s/\]/%5D/')"
    echo "downloading $file"
    curl -fsSL -o "$out" "$url"
    echo "$sum  $out" | sha256sum -c
  fi
done <<'LIST'
bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d notosans NotoSans[wdth,wght].ttf
63111b5b2e074dd48cc67692e0a2726d86ee94c1c37fe8598257b7b4e87e869e notosansarabic NotoSansArabic[wdth,wght].ttf
14ec4af41f27482216d1c2229f417ff9b1425e1babb014e57d1d40d03229853e notosansdevanagari NotoSansDevanagari[wdth,wght].ttf
a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da notosanssc NotoSansSC[wght].ttf
c2f3b4d463500a2ddcd3849cded1fceeb9fd6d1c32e6cbecd568453ba50fc68f notosansjp NotoSansJP[wght].ttf
194018e6b2b293a7964f037b25c0249ce1418bc9ab3c971060a03aa57861e252 notosanskr NotoSansKR[wght].ttf
LIST
