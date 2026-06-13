"""Inline all slide images into pitch-deck.html -> pitch-deck-standalone.html (one portable file)."""
import base64, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
html = (root / "pitch-deck.html").read_text()

def inline(match):
    rel = match.group(1)
    data = (root / rel).read_bytes()
    b64 = base64.b64encode(data).decode()
    return f'"data:image/png;base64,{b64}"'

html = re.sub(r'"(assets/video/[^"]+\.png)"', inline, html)
out = root / "pitch-deck-standalone.html"
out.write_text(html)
print(f"wrote {out} ({out.stat().st_size/1_000_000:.1f} MB)")
