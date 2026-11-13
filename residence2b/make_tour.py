"""Assemble the 360 tour page: index.html + panos/ + plan.jpg + walkthrough.mp4 in an output folder.
usage: python3 make_tour.py pano_dir topdown.png walkthrough.mp4 out_dir pannellum.css"""
import json, math, os, shutil, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tour_spots import SPOTS, LINKS, SEASONS, TIMES, variants, pano_name, F, EYE

pano_dir, topdown, video, out, css_path = sys.argv[1:6]
os.makedirs(os.path.join(out, 'panos'), exist_ok=True)
for spot in SPOTS:
    for s, t in variants(spot):
        shutil.copy(os.path.join(pano_dir, pano_name(spot, s, t)), os.path.join(out, 'panos', pano_name(spot, s, t)))
Image.open(topdown).convert('RGB').save(os.path.join(out, 'plan.jpg'), quality=86)
if os.path.exists(video):
    shutil.copy(video, os.path.join(out, 'walkthrough.mp4'))

def yaw_pitch(frm, to):
    _, x, y, _ = SPOTS[frm]
    tx, ty = to
    dX, dY = (tx - x) * F, -(ty - y) * F          # world: +Y is the pano's centre (yaw 0), +X is to the right
    yaw = math.degrees(math.atan2(dX, dY))
    pitch = -math.degrees(math.atan2(EYE - 0.05, math.hypot(dX, dY)))
    return round(yaw, 2), round(max(pitch, -55), 2)

data = {'spots': {}, 'seasons': SEASONS, 'times': TIMES}
for k, (label, x, y, win) in SPOTS.items():
    data['spots'][k] = dict(
        label=label, windows=win,
        map=[round((x + 0.75) / 62 * 100, 2), round((y + 0.7) / 48 * 100, 2)],
        variants=[f'{s}_{t}' for s, t in variants(k)],
        links=[dict(to=to, label=SPOTS[to][0], yaw=yaw_pitch(k, pt)[0], pitch=yaw_pitch(k, pt)[1]) for to, pt in LINKS[k]],
    )
# sun position per season/time (Omaha 41.26 N, 95.94 W; clock = solar time + 24 min, +1 h daylight saving)
import environment as env
DST = {'spring': 1, 'summer': 1, 'fall': 1, 'winter': 0}
def clock(season, h):
    m = int(round((h + 0.4 + DST[season]) * 60)); hh, mm = divmod(m, 60)
    return f"{(hh - 1) % 12 + 1}:{mm:02d} {'am' if hh < 12 else 'pm'}"
data['dates'] = {k: v['date'] for k, v in env.SEASONS.items()}
data['sun'] = {}
for season in SEASONS:
    for i, t in enumerate(TIMES):
        P = env.params(season, float(i))
        where = f"sun {P['elevation']:.0f}° up" if P['elevation'] > 0 else 'after sunset'
        data['sun'][f'{season}_{t}'] = f"{where} · about {clock(season, P['hour'])}"
# walkthrough chapters from the camera path
rep = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'camera_report.json')
fr = json.load(open(rep))['frames']
def first(pred, label):
    for i, (x, y, a) in enumerate(fr):
        if pred(x, y):
            return [round(i / 24, 1), label]
data['chapters'] = [c for c in [
    [0.0, 'Front door'],
    first(lambda x, y: y > 34.6 and x < 27, 'Den'),
    first(lambda x, y: x > 40.5 and y < 29, 'Kitchen'),
    first(lambda x, y: y < 20 and x < 35 and x > 29, 'Living & dining'),
    first(lambda x, y: y < 11 and 15 < x < 46, 'Balcony'),
    first(lambda x, y: x < 14.2, 'Primary bedroom'),
    first(lambda x, y: x < 14 and y > 18.7, 'Primary bath'),
    first(lambda x, y: x > 46.5 and y < 16.4, 'Bedroom 2')] if c]
data['film_note'] = os.environ.get('FILM_NOTE', '')
css = open(css_path).read()
html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tour_template.html')).read()
html = html.replace('/*PANNELLUM_CSS*/', css).replace('/*TOUR_DATA*/', json.dumps(data))
open(os.path.join(out, 'index.html'), 'w').write(html)
print('tour written to', out, 'with', sum(len(v['variants']) for v in data['spots'].values()), 'panoramas')
