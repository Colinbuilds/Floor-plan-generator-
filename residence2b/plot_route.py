"""Top-down diagnostic: walls, furniture footprints, camera route coloured by clearance."""
import json, math, sys
from PIL import Image, ImageDraw
R = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'camera_report.json'))
out = sys.argv[2] if len(sys.argv) > 2 else 'route_plan.png'
S = 22; P = 30
img = Image.new('RGB', (int(61 * S + 2 * P), int(47 * S + 2 * P)), 'white'); d = ImageDraw.Draw(img)
T = lambda x, y: (P + x * S, P + y * S)
for (cx, cy, hx, hy, rot, tag) in R['obstacles']:
    col = (40, 50, 60) if tag == 'wall' else (200, 160, 120)
    c, s = math.cos(rot), math.sin(rot)
    pts = []
    for (lx, ly) in [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]:
        wx, wy = c * lx - s * ly, s * lx + c * ly
        pts.append(T(cx + wx, cy - wy))
    if tag == 'wall': d.polygon(pts, fill=col)
    else: d.polygon(pts, outline=col)
fr = R['frames']; cl = R['clearance']
for i in range(len(fr) - 1):
    c = cl[i][0]
    col = (220, 30, 30) if c < 0.25 else (240, 160, 0) if c < 0.35 else (30, 150, 60)
    d.line([T(fr[i][0], fr[i][1]), T(fr[i + 1][0], fr[i + 1][1])], fill=col, width=3)
for i in range(0, len(fr), 48):
    x, y, a = fr[i]
    d.line([T(x, y), T(x + 1.6 * math.cos(a), y - 1.6 * math.sin(a))], fill=(30, 60, 220), width=2)
    d.text(T(x + 0.3, y + 0.3), f'{i // 24}s', fill=(30, 60, 220))
img.save(out)
bad = [(i + 1, c) for i, c in enumerate(cl) if c[0] < 0.3]
print('frames under 0.30 m:', len(bad), bad[:: max(1, len(bad) // 25)] if bad else '')
