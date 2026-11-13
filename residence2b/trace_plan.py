"""Trace wall rectangles from The-Residences_2B-Floor-Plan.pdf -> plan_walls.json.

Rasterises the PDF at 300 dpi, keeps the dark wall fill colour (#303C46), removes thin
line-work (furniture, door swings, text) with a 10 px morphological opening, then merges
row runs into axis-aligned rectangles.  Output units are 300-dpi pixels of the crop;
build_residence.py converts with 37.6 px/ft (calibrated on the labelled room sizes:
Balcony 30'-4", Bedroom 12'-10", Primary Bedroom 13'-0").
usage: python3 trace_plan.py path/to/plan.pdf [plan_walls.json]
"""
import json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
from scipy import ndimage as nd

pdf = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else 'plan_walls.json'
with tempfile.TemporaryDirectory() as td:
    subprocess.run(['pdftoppm', '-r', '300', '-png', pdf, os.path.join(td, 'p')], check=True)
    im = np.array(Image.open(os.path.join(td, 'p-1.png')).convert('RGB')).astype(int)
wall_rgb = np.array([48, 60, 70])
mask = np.abs(im - wall_rgb).sum(2) < 60
mask = mask[720:2475, 1725:4005]                      # crop to the unit
walls = nd.binary_opening(mask, structure=np.ones((10, 10)))
H, W = walls.shape
open_runs, rects = {}, []
for y in range(H + 1):
    row = walls[y] if y < H else np.zeros(W, bool)
    d = np.diff(np.concatenate([[0], row.astype(int), [0]]))
    runs = set(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))
    for k in list(open_runs):
        if k not in runs:
            rects.append((k[0], open_runs.pop(k), k[1], y))
    for r in runs:
        if r not in open_runs:
            open_runs[r] = y
rects = [list(map(int, r)) for r in rects if (r[2] - r[0]) >= 6 and (r[3] - r[1]) >= 6]
json.dump(rects, open(out, 'w'))
print(len(rects), 'wall rectangles ->', out)
