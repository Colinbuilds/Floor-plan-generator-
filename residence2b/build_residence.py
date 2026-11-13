"""
Residence 2B (The Residences, Omaha - Levels 2-6): staged luxury Blender model,
Omaha surroundings with four seasons + solar day cycle, and a 45 s walkthrough camera.

Plan coordinates are FEET measured on the PDF plan (x right, y down, origin top-left),
calibrated on the labelled room sizes (Balcony 30'-4", Bedroom 12'-10", Primary Bedroom 13'-0").
World: X = x_ft * 0.3048, Y = -y_ft * 0.3048, Z up (m).  Balcony faces south (+Y).

Run:  python3 build_residence.py [out.blend] [--season fall]
The saved file contains the walkthrough with an animated day cycle (morning -> golden hour on
the balcony -> evening).  environment.apply_time()/set_season() re-light it for any season/time.
"""
import bpy, json, math, os, random, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geo
from geo import (F, CEIL, DOOR_H, coll, add_obst, OBST, W, link, mesh_obj, boxm, box, cylm, cyl, sphere, ico, torus,
                 curtain, Group, principled, noisy, plank_floor, tile, marble, fluted, emissive, glass, art)
import environment as env

OUT = next((a for a in sys.argv if a.endswith('.blend')), os.path.join(HERE, 'Residence_2B.blend'))
VIDEO_SEASON = sys.argv[sys.argv.index('--season') + 1] if '--season' in sys.argv else 'fall'
FPS = 24
DURATION = 45
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
geo.reset()
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

# ----------------------------------------------------------------------------
# materials - dark contemporary
# ----------------------------------------------------------------------------
M = dict(
    floor=plank_floor('Smoked Oak Wide Plank', (0.150, 0.105, 0.072), (0.120, 0.083, 0.058), (0.03, 0.02, 0.015)),
    wall=noisy('Limewash Plaster Greige', (0.40, 0.37, 0.33), (0.45, 0.42, 0.38), 1.6, (1, 1, 1), 0.92, bump=0.05),
    ceiling=principled('Ceiling Warm White', (0.62, 0.60, 0.56), 0.92),
    trim=principled('Charcoal Trim', (0.045, 0.043, 0.042), 0.5),
    tile=marble('Honed Marble Floor', (0.66, 0.65, 0.63), (0.18, 0.18, 0.19), 0.5, 0.35, 0.05),
    marble=marble('Black-Veined Marble', (0.82, 0.81, 0.79), (0.16, 0.16, 0.17), 0.9, 0.10, 0.035),
    nero=marble('Nero Marble', (0.020, 0.020, 0.022), (0.55, 0.54, 0.52), 0.7, 0.08, 0.04),
    balcony=tile('Porcelain Pavers', (0.25, 0.24, 0.23), (0.22, 0.21, 0.20), 0.61, 0.7, (0.12, 0.12, 0.12)),
    navy=noisy('Charcoal Oak Millwork', (0.032, 0.030, 0.029), (0.050, 0.046, 0.043), 5, (1, 1, 22), 0.45),
    fluted=fluted('Fluted Smoked Oak', (0.10, 0.07, 0.05), (0.14, 0.10, 0.07), 45),
    walnut=noisy('Smoked Oak', (0.09, 0.062, 0.042), (0.15, 0.105, 0.07), 6, (1, 18, 1), 0.4),
    oak=noisy('Smoked Oak Light', (0.16, 0.115, 0.08), (0.22, 0.16, 0.11), 6, (1, 18, 1), 0.45),
    steel=principled('Brushed Steel', (0.6, 0.6, 0.6), 0.3, 1.0),
    black=principled('Matte Black Metal', (0.018, 0.018, 0.018), 0.45, 0.7),
    bronze=principled('Satin Bronze', (0.30, 0.19, 0.11), 0.30, 1.0),
    glass_black=principled('Black Glass', (0.008, 0.008, 0.009), 0.04),
    boucle=noisy('Cream Boucle', (0.62, 0.57, 0.50), (0.70, 0.66, 0.59), 140, (1, 1, 1), 1.0, bump=0.35),
    linen=noisy('Ivory Linen', (0.74, 0.71, 0.66), (0.68, 0.65, 0.60), 70, (1, 1, 1), 0.95, bump=0.1),
    mushroom=noisy('Mushroom Velvet', (0.26, 0.22, 0.19), (0.32, 0.28, 0.24), 90, (1, 1, 1), 0.7, bump=0.15),
    charcoal=noisy('Charcoal Wool', (0.045, 0.045, 0.048), (0.07, 0.07, 0.072), 80, (1, 1, 1), 0.95, bump=0.2),
    rust=principled('Rust Velvet', (0.30, 0.085, 0.035), 0.6),
    olive=principled('Olive Velvet', (0.12, 0.13, 0.06), 0.6),
    cognac=noisy('Cognac Leather', (0.20, 0.075, 0.03), (0.26, 0.10, 0.04), 30, (1, 1, 1), 0.38, bump=0.1),
    black_leather=principled('Black Leather', (0.02, 0.018, 0.017), 0.35),
    rug=noisy('Charcoal Wool Rug', (0.07, 0.065, 0.06), (0.12, 0.11, 0.10), 40, (1, 1, 1), 1.0, bump=0.4),
    rug2=art('Ivory Abstract Rug', [(0.55, 0.51, 0.45), (0.30, 0.27, 0.24), (0.08, 0.07, 0.07)], 0.9, 4),
    porcelain=principled('Stone Resin White', (0.80, 0.79, 0.77), 0.15),
    mirror=principled('Mirror', (0.9, 0.9, 0.9), 0.02, 1.0),
    glass=glass('Clear Glass'),
    shower_glass=glass('Shower Glass', (0.90, 0.92, 0.92)),
    frame=principled('Window Frame Black', (0.018, 0.018, 0.02), 0.45, 0.3),
    plant=noisy('Leaf Green', (0.04, 0.10, 0.03), (0.09, 0.17, 0.05), 8, (1, 1, 1), 0.6),
    olive_leaf=noisy('Olive Leaf', (0.16, 0.19, 0.12), (0.26, 0.29, 0.20), 12, (1, 1, 1), 0.7),
    pot=noisy('Stone Planter', (0.20, 0.19, 0.17), (0.28, 0.27, 0.25), 10, (1, 1, 1), 0.85, bump=0.3),
    ceramic=principled('Matte Ceramic Black', (0.03, 0.03, 0.03), 0.6),
    ceramic2=principled('Matte Ceramic Sand', (0.50, 0.44, 0.36), 0.7),
    soil=principled('Soil', (0.04, 0.03, 0.02), 1.0),
    log=noisy('Firewood', (0.10, 0.06, 0.03), (0.26, 0.17, 0.09), 14, (1, 1, 1), 0.9, bump=0.4),
    flame=geo.flame_material('Fire', (1.0, 0.40, 0.08), 5.0),
    lampshade=emissive('Lamp Shade Glow', (1.0, 0.82, 0.62), 3.0, base=(0.8, 0.75, 0.68)),
    led=emissive('LED Strip 2700K', (1.0, 0.78, 0.52), 3.0),
    bulb=emissive('Warm Bulb', (1.0, 0.78, 0.52), 25.0),
    alabaster=emissive('Alabaster Glow', (1.0, 0.86, 0.70), 4.0, base=(0.85, 0.80, 0.72)),
    screen=principled('TV Screen', (0.004, 0.004, 0.005), 0.06),
    concrete=principled('Architectural Concrete', (0.30, 0.29, 0.28), 0.9),
    sheer=principled('Sheer Linen', (0.70, 0.67, 0.61), 0.95),
    towel=noisy('Towel Ivory', (0.72, 0.69, 0.64), (0.78, 0.75, 0.70), 200, (1, 1, 1), 1.0, bump=0.3),
    teak=noisy('Teak', (0.22, 0.12, 0.06), (0.30, 0.17, 0.09), 6, (1, 18, 1), 0.6),
    outdoor=noisy('Outdoor Cushion Sand', (0.42, 0.38, 0.32), (0.48, 0.44, 0.37), 90, (1, 1, 1), 1.0),
    fire_glass=principled('Fire Glass', (0.04, 0.05, 0.06), 0.05),
    planting=noisy('Season Planting', (0.45, 0.30, 0.10), (0.6, 0.4, 0.13), 25, (1, 1, 1), 0.8),
    art1=art('Art Charcoal Gesture', [(0.78, 0.75, 0.70), (0.06, 0.06, 0.06), (0.55, 0.45, 0.35)], 1.2, 8),
    art2=art('Art Rust Field', [(0.30, 0.10, 0.05), (0.55, 0.30, 0.16), (0.12, 0.10, 0.09), (0.70, 0.62, 0.52)], 0.7, 3),
    art3=art('Art Ink Wash', [(0.80, 0.78, 0.74), (0.35, 0.36, 0.38), (0.05, 0.05, 0.06)], 2.0, 12),
    art4=art('Art Gold Leaf', [(0.04, 0.04, 0.045), (0.45, 0.32, 0.12), (0.06, 0.06, 0.06)], 3.0, kind='VORONOI'),
)
# the sheer curtains: let light through
_sh = M['sheer'].node_tree; _b = _sh.nodes['Principled BSDF']
_b.inputs['Transmission Weight'].default_value = 0.55; _b.inputs['Alpha'].default_value = 0.8
M['fire_table'] = geo.flame_material('Fire Table Flame', (1.0, 0.42, 0.10), 5.0)
BOOK_MATS = [principled(f'Book {i}', c, 0.8) for i, c in enumerate(
    [(0.30, 0.08, 0.04), (0.05, 0.06, 0.08), (0.62, 0.58, 0.50), (0.12, 0.13, 0.08), (0.40, 0.30, 0.15),
     (0.02, 0.02, 0.02), (0.55, 0.52, 0.48)])]

# ----------------------------------------------------------------------------
# architecture: walls traced from the PDF plan
# ----------------------------------------------------------------------------
S_PX = 37.6  # px per foot on the 300-dpi raster used for tracing
RECTS = [[v / S_PX for v in r] for r in json.load(open(os.path.join(HERE, 'plan_walls.json')))]
AR = 'Architecture'
WALLS = []
for i, (x0, y0, x1, y1) in enumerate(RECTS):
    box(x0, y0, x1, y1, 0, CEIL, M['wall'], AR, f'Wall.{i:03d}')
    WALLS.append((x0, y0, x1, y1))
    # skirting board (sits 1 cm proud of every wall face)
    e = 0.04
    box(x0 - e, y0 - e, x1 + e, y1 + e, 0, 0.10, M['trim'], AR, f'Skirting.{i:03d}')

# door openings found on the plan: (orient, a, b, band0, band1, hinge, swing, angle, kind)
#   orient 'H' -> wall runs along x (a,b are x extents, band is y); 'V' -> wall along y
#   hinge 'a'|'b', swing +1/-1 (direction perpendicular to wall), angle deg open (0 = closed)
DOORS = [
    ('H', 36.01, 39.23, 44.81, 45.21, 'a', -1, 92, 'Front Door'),
    ('H', 22.21, 26.25, 35.11, 35.43, None, 0, 0, 'Den Opening'),
    ('V', 39.47, 42.77, 35.24, 35.64, 'a', -1, 75, 'Hall Bath Door'),
    ('V', 39.47, 42.69, 27.53, 27.87, 'a', 1, 0, 'Den-Bath Door'),
    ('V', 40.61, 43.91, 42.66, 43.06, 'a', -1, 0, 'Entry Closet Door'),
    ('H', 45.98, 49.12, 38.19, 38.75, 'a', 1, 85, 'Laundry Door'),
    ('V', 39.07, 42.37, 54.73, 55.11, 'a', 1, 0, 'Mech Door'),
    ('H', 46.76, 49.97, 27.90, 28.24, 'a', -1, 92, 'Bedroom Hall Door'),
    ('H', 46.89, 50.05, 16.20, 16.54, None, 0, 0, 'Bedroom 2 Opening'),
    ('V', 20.69, 23.96, 50.48, 50.88, 'a', 1, 80, 'Bath 2 Door'),
    ('H', 51.17, 53.88, 27.90, 28.24, 'a', 1, 85, 'Closet 2 Door'),
    ('V', 14.68, 17.82, 14.15, 14.57, 'b', -1, 95, 'Primary Bedroom Door'),
    ('H', 8.01, 11.14, 18.19, 18.54, 'b', 1, 88, 'Primary Bath Door'),
    ('V', 30.98, 33.75, 7.23, 7.63, 'a', 1, 75, 'WC Door'),
    ('H', 8.01, 11.14, 34.71, 35.00, 'a', 1, 90, 'Primary Closet Door'),
]
DOOR_LEAVES = []
for (o, a, b, c0, c1, hinge, swing, ang, nm) in DOORS:
    # header above the opening
    if o == 'H':
        box(a, c0, b, c1, DOOR_H, CEIL, M['wall'], AR, nm + ' Header')
    else:
        box(c0, a, c1, b, DOOR_H, CEIL, M['wall'], AR, nm + ' Header')
    # casing (trim) around the opening, both faces
    t = 0.06 / F; d = 0.02 / F
    for side in (c0 - d, c1):
        if o == 'H':
            box(a - t, side, a, side + d, 0, DOOR_H + 0.06, M['trim'], AR, nm + ' Casing')
            box(b, side, b + t, side + d, 0, DOOR_H + 0.06, M['trim'], AR, nm + ' Casing')
            box(a - t, side, b + t, side + d, DOOR_H, DOOR_H + 0.07, M['trim'], AR, nm + ' Casing')
        else:
            box(side, a - t, side + d, a, 0, DOOR_H + 0.06, M['trim'], AR, nm + ' Casing')
            box(side, b, side + d, b + t, 0, DOOR_H + 0.06, M['trim'], AR, nm + ' Casing')
            box(side, a - t, side + d, b + t, DOOR_H, DOOR_H + 0.07, M['trim'], AR, nm + ' Casing')
    if hinge is None:
        continue
    # door leaf: built in local coords along +X from the hinge, then rotated open
    width = (b - a) * F - 0.01
    thick = 0.045
    mid = (c0 + c1) / 2
    if o == 'H':
        hx, hy = (a, mid) if hinge == 'a' else (b, mid)
        base = 0 if hinge == 'a' else math.pi                  # closed direction (+x or -x)
        perp = -math.pi / 2 if swing > 0 else math.pi / 2       # +y plan == -Y world
    else:
        hx, hy = (mid, a) if hinge == 'a' else (mid, b)
        base = -math.pi / 2 if hinge == 'a' else math.pi / 2    # along +y plan (= -Y world)
        perp = 0 if swing > 0 else math.pi
    # rotate from 'base' toward 'perp' by the open angle
    dlt = (perp - base + math.pi) % (2 * math.pi) - math.pi
    yaw = base + math.copysign(math.radians(ang), dlt) if ang else base
    piv = bpy.data.objects.new(nm, None)
    X, Y = W(hx, hy)
    piv.location = (X, Y, 0); piv.rotation_euler = (0, 0, yaw)
    link(piv, AR)
    leaf = boxm(0.005, -thick / 2, 0.005, width, thick / 2, DOOR_H - 0.01,
                M['walnut'] if 'Front' not in nm else M['navy'], AR, nm + ' Leaf', 0.004)
    leaf.parent = piv
    # handle
    hd = boxm(width - 0.20, -thick / 2 - 0.06, 0.99, width - 0.07, thick / 2 + 0.06, 1.01, M['black'], AR, nm + ' Handle')
    hd.parent = piv
    # footprint for clearance checks
    ex, ey = math.cos(yaw) * width, math.sin(yaw) * width
    cxw, cyw = X + ex / 2, Y + ey / 2
    add_obst(cxw / F, -cyw / F, width / 2 / F, thick / 2 / F, yaw, nm + ' Leaf')
    DOOR_LEAVES.append((nm, X, Y, yaw, width))

# den barn door parked open beside the opening (plan shows the slider track)
box(17.85, 35.45, 22.25, 35.55, 2.18, 2.22, M['black'], AR, 'Den Barn Rail')
box(17.95, 35.56, 22.15, 35.70, 0.02, 2.15, M['walnut'], AR, 'Den Barn Door', 0.004)
box(16.60, 36.62, 16.75, 44.76, DOOR_H, CEIL, M['wall'], AR, 'Den Closet Header')
for k in range(4):   # bi-fold closet doors (closed)
    y0 = 36.62 + k * (44.76 - 36.62) / 4
    box(16.62, y0 + 0.02, 16.74, y0 + (44.76 - 36.62) / 4 - 0.02, 0.01, DOOR_H - 0.01, M['trim'], AR, 'Den Closet Door', 0.004)

# ----------------------------------------------------------------------------
# windows / sliding doors on the exterior
# ----------------------------------------------------------------------------
def glazing(x0, x1, y0, y1, name, sill=0.0, head=2.44, panels=3, open_panel=None):
    """window wall along x between x0..x1 with wall band y0..y1 (plan ft)."""
    mid = (y0 + y1) / 2
    box(x0, y0, x1, y1, head, CEIL, M['wall'], AR, name + ' Header')
    if sill > 0:
        box(x0, y0, x1, y1, 0, sill, M['wall'], AR, name + ' Sill')
    fw = 0.05 / F
    box(x0, mid - 0.12, x1, mid + 0.12, head - 0.05, head, M['frame'], AR, name + ' Frame')
    box(x0, mid - 0.12, x1, mid + 0.12, sill, sill + 0.05, M['frame'], AR, name + ' Frame')
    pw = (x1 - x0) / panels
    for p in range(panels):
        a = x0 + p * pw; b = a + pw
        off = 0
        if open_panel is not None and p == open_panel:
            continue
        box(a, mid - 0.12, a + fw, mid + 0.12, sill, head, M['frame'], AR, name + ' Mullion')
        box(b - fw, mid - 0.12, b, mid + 0.12, sill, head, M['frame'], AR, name + ' Mullion')
        box(a + fw, mid - 0.02, b - fw, mid + 0.02, sill + 0.05, head - 0.05, M['glass'], AR, name + ' Glass')
        add_obst((a + b) / 2, mid, pw / 2, 0.15, 0, name + ' Glass')
    if open_panel is not None:
        # the open panel is slid behind its western neighbour, on the outer track
        a = x0 + (open_panel - 1) * pw; b = a + pw
        box(a, y0 - 0.05, a + fw, y0 + 0.12, sill, head, M['frame'], AR, name + ' Slider')
        box(b - fw, y0 - 0.05, b, y0 + 0.12, sill, head, M['frame'], AR, name + ' Slider')
        box(a + fw, y0 + 0.02, b - fw, y0 + 0.06, sill + 0.05, head - 0.05, M['glass'], AR, name + ' Slider Glass')

glazing(4.68, 13.64, 0.98, 1.60, 'Primary Bedroom Window', sill=0.45, panels=3)
glazing(47.05, 55.82, 0.98, 1.60, 'Bedroom 2 Window', sill=0.45, panels=3)
glazing(18.80, 41.78, 11.10, 11.86, 'Living Slider', sill=0.0, panels=4, open_panel=1)

# floors & ceilings
box(0.3, 0.6, 60.2, 46.3, -0.06, 0.0, M['floor'], AR, 'Floor Oak')
box(15.1, -0.4, 45.5, 11.1, -0.12, -0.035, M['balcony'], AR, 'Balcony Floor')
box(0.3, -0.4, 60.2, 46.3, CEIL, CEIL + 0.15, M['ceiling'], AR, 'Ceiling')
for (x0, y0, x1, y1, nm) in [(0.6, 18.55, 14.0, 34.7, 'Primary Bath'), (27.9, 35.6, 35.2, 45.4, 'Hall Bath'),
                             (50.9, 16.6, 59.3, 27.9, 'Bath 2'), (45.6, 38.75, 59.3, 45.7, 'Laundry')]:
    box(x0, y0, x1, y1, 0.0, 0.006, M['tile'], AR, nm + ' Tile Floor')
# balcony glass guard + top rail
box(15.13, 0.35, 45.48, 0.45, -0.03, 1.07, M['glass'], AR, 'Balcony Glass Guard')
box(15.13, 0.25, 45.48, 0.55, 1.07, 1.11, M['black'], AR, 'Balcony Rail')
add_obst(30.3, 0.4, 15.2, 0.2, 0, 'Balcony Guard')
for x in range(16, 46, 5):
    box(x, 0.3, x + 0.15, 0.5, -0.03, 1.07, M['black'], AR, 'Balcony Post')
# slab edge / soffit beyond the guard
box(14.0, -1.4, 46.9, 0.6, -0.40, -0.035, M['concrete'], AR, 'Slab Edge')
box(14.0, -1.4, 46.9, 0.6, CEIL, CEIL + 0.30, M['concrete'], AR, 'Soffit')

# ----------------------------------------------------------------------------
# lights (every light stores a base energy + group so the day cycle can scale it)
# ----------------------------------------------------------------------------
LI = 'Lighting'
WARM = (1.0, 0.78, 0.55)

def _light(kind, name, loc, power, color, group, **kw):
    d = bpy.data.lights.new(name, kind)
    d.energy = power; d.color = color
    d['base'] = power; d['group'] = group
    for k, v in kw.items():
        setattr(d, k, v)
    o = bpy.data.objects.new(name, d); o.location = loc
    link(o, LI)
    return o

def add_point(name, X, Y, Z, power, color=WARM, radius=0.08, group='accent'):
    return _light('POINT', name, (X, Y, Z), power, color, group, shadow_soft_size=radius)

def area(name, x0, y0, x1, y1, power, color=(1.0, 0.84, 0.66), z=CEIL - 0.02, group='interior'):
    X, Y = W((x0 + x1) / 2, (y0 + y1) / 2)
    o = _light('AREA', name, (X, Y, z), power, color, group, shape='RECTANGLE',
               size=abs(x1 - x0) * F * 0.8, size_y=abs(y1 - y0) * F * 0.8)
    return o

def downlight(x, y, power=28, cn=LI):
    """recessed 2700K spot - pools of light rather than flat fill"""
    X, Y = W(x, y)
    cylm(X, Y, 0.045, CEIL - 0.004, CEIL - 0.001, M['bulb'], cn, 'Recessed Downlight', 16)
    cylm(X, Y, 0.06, CEIL - 0.003, CEIL, M['black'], cn, 'Downlight Trim', 16)
    _light('SPOT', 'Downlight', (X, Y, CEIL - 0.03), power, WARM, 'interior',
           spot_size=math.radians(80), spot_blend=0.7, shadow_soft_size=0.04)

def picture_light(x, y, facing, width, z):
    """small area light above artwork aimed at the wall"""
    X, Y = W(x, y)
    ang = {'E': -90, 'W': 90, 'N': 0, 'S': 180}[facing]
    a = math.radians(ang)
    fx, fy = -math.sin(a), math.cos(a)                      # direction the art faces
    o = _light('AREA', 'Picture Light', (X + fx * 0.25, Y + fy * 0.25, z), 18, WARM, 'accent',
               shape='RECTANGLE', size=width, size_y=0.08)
    o.rotation_euler = (Vector((-fx, -fy, -1.4))).to_track_quat('-Z', 'Y').to_euler()

# ----------------------------------------------------------------------------
# furniture library
# ----------------------------------------------------------------------------
FU = 'Furniture'

def chair(x, y, facing, mat_seat=None, name='Dining Chair', cn=FU, frame=None):
    g = Group(name, x, y, facing, cn, 0.26, 0.28)
    ms = mat_seat or M['mushroom']; fm = frame or M['walnut']
    for sx in (-0.21, 0.21):
        for sy in (-0.21, 0.21):
            g.box(sx - 0.018, sy - 0.018, 0, sx + 0.018, sy + 0.018, 0.44, fm, 0.004)
    g.box(-0.25, -0.25, 0.42, 0.25, 0.25, 0.50, ms, 0.03)
    g.box(-0.25, -0.28, 0.48, 0.25, -0.20, 0.90, ms, 0.035)
    g.box(-0.27, -0.26, 0.48, -0.22, 0.10, 0.70, ms, 0.02)
    g.box(0.22, -0.26, 0.48, 0.27, 0.10, 0.70, ms, 0.02)
    return g

def lounge_chair(x, y, facing, mat=None, name='Lounge Chair', cn=FU, base=None):
    """sculptural barrel-back lounge chair"""
    m = mat or M['cognac']
    g = Group(name, x, y, facing, cn, 0.44, 0.44)
    g.cyl(0, 0, 0.26, 0.0, 0.06, base or M['bronze'], 28)
    g.cyl(0, 0, 0.05, 0.06, 0.20, base or M['bronze'], 12)
    g.cyl(0, 0.02, 0.40, 0.20, 0.44, m, 36, ry=0.38)
    g.cyl(0, 0.04, 0.36, 0.44, 0.52, m, 36, ry=0.33)
    back = g.cyl(0, -0.02, 0.43, 0.20, 0.78, m, 40, ry=0.41, cap=False)
    # carve the front of the barrel back away by squashing a cylinder shell
    back.scale = (1, 1, 1)
    md = back.modifiers.new('Shell', 'SOLIDIFY'); md.thickness = 0.09
    # remove front half faces
    me = back.data
    import bmesh as _bm
    bm = _bm.new(); bm.from_mesh(me)
    kill = [f for f in bm.faces if f.calc_center_median().y > 0.06 + 0 * f.index]
    _bm.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(me); bm.free()
    g.box(-0.18, -0.28, 0.50, 0.18, -0.16, 0.74, M['linen'], 0.06)
    return g

def armchair(x, y, facing, mat=None, name='Armchair', cn=FU):
    m = mat or M['boucle']
    g = Group(name, x, y, facing, cn, 0.42, 0.44)
    g.box(-0.40, -0.42, 0.06, 0.40, 0.42, 0.40, m, 0.06)
    g.box(-0.40, -0.42, 0.40, 0.40, -0.22, 0.78, m, 0.07)
    g.box(-0.40, -0.40, 0.40, -0.26, 0.40, 0.60, m, 0.06)
    g.box(0.26, -0.40, 0.40, 0.40, 0.40, 0.60, m, 0.06)
    g.box(-0.26, -0.22, 0.40, 0.26, 0.40, 0.50, m, 0.06)
    g.box(-0.36, -0.38, 0.0, 0.36, 0.38, 0.06, M['black'], 0.005)
    return g

def lamp(x, y, z_base, cn=FU, h=0.45, r=0.17, name='Table Lamp', power=18, base_mat=None):
    X, Y = W(x, y)
    cylm(X, Y, 0.09, z_base, z_base + 0.22, base_mat or M['ceramic'], cn, name + ' Base', 24, r_top=0.05)
    cylm(X, Y, 0.012, z_base + 0.2, z_base + h, M['bronze'], cn, name, 8)
    cylm(X, Y, r, z_base + h - 0.05, z_base + h + 0.20, M['lampshade'], cn, name + ' Shade', 28, cap=False, r_top=r * 0.8)
    add_point(name + ' Light', X, Y, z_base + h + 0.04, power, radius=0.1)

def arc_lamp(x, y, tx, ty, cn=FU, name='Arc Floor Lamp'):
    """bronze arc lamp from (x,y) reaching toward (tx,ty) (plan ft)"""
    X, Y = W(x, y); TX, TY = W(tx, ty)
    cylm(X, Y, 0.18, 0, 0.05, M['nero'], cn, name + ' Base', 28)
    pts = []
    for i in range(13):
        t = i / 12
        px = X + (TX - X) * (1 - math.cos(t * math.pi / 2))
        py = Y + (TY - Y) * (1 - math.cos(t * math.pi / 2))
        pz = 0.05 + 2.05 * math.sin(t * math.pi * 0.62) / math.sin(math.pi * 0.62) if t < 0.81 else None
        pts.append((px, py, pz))
    zs = [0.05 + 2.1 * math.sin(min(1, i / 9) * math.pi / 2) - (0.25 * max(0, i - 9) / 3) for i in range(13)]
    prev = None
    for (px, py, _), pz in zip(pts, zs):
        if prev:
            mid = ((prev[0] + px) / 2, (prev[1] + py) / 2, (prev[2] + pz) / 2)
            d = Vector((px - prev[0], py - prev[1], pz - prev[2]))
            o = cylm(0, 0, 0.012, -d.length / 2, d.length / 2, M['bronze'], cn, name + ' Arc', 8)
            o.location = mid; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        prev = (px, py, pz)
    sphere(TX, TY, zs[-1] - 0.12, 0.2, M['bronze'], cn, name + ' Shade', sz=0.55, seg=20)
    cylm(TX, TY, 0.15, zs[-1] - 0.20, zs[-1] - 0.19, M['bulb'], cn, name + ' Glow', 20)
    add_point(name + ' Light', TX, TY, zs[-1] - 0.3, 30, radius=0.1)
    add_obst(x, y, 0.65, 0.65, 0, name)

def plant(x, y, cn=FU, h=1.4, r=0.22, name='Plant', leaf=None):
    X, Y = W(x, y)
    cylm(X, Y, r, 0, 0.5, M['pot'], cn, name + ' Planter', 28, r_top=r * 1.08)
    cylm(X, Y, r * 1.02, 0.46, 0.48, M['soil'], cn, name + ' Soil', 24)
    cylm(X, Y, 0.02, 0.45, h * 0.7, M['walnut'], cn, name + ' Stem', 8)
    lm = leaf or M['plant']
    me = ico(0.11, 1, lm, name + ' Leaf mesh', noise=0.2)
    for i in range(22):
        a = random.uniform(0, 2 * math.pi); rr = random.uniform(0.05, r * 1.8)
        z = random.uniform(0.75, h)
        o = bpy.data.objects.new(name + ' Leaf', me)
        o.location = (X + rr * math.cos(a), Y + rr * math.sin(a), z)
        o.scale = (1.1, 0.35, 1.5); o.rotation_euler = (random.uniform(-0.7, 0.7), random.uniform(-0.7, 0.7), a)
        link(o, cn)
    add_obst(x, y, (r * 1.8) / F, (r * 1.8) / F, 0, name)

def olive_tree(x, y, cn=FU, h=2.1, name='Olive Tree'):
    X, Y = W(x, y)
    cylm(X, Y, 0.30, 0, 0.55, M['pot'], cn, name + ' Planter', 32, r_top=0.33)
    cylm(X, Y, 0.31, 0.52, 0.54, M['soil'], cn, name + ' Soil', 24)
    for k in range(3):
        a = k * 2.1
        d = Vector((math.cos(a) * 0.25, math.sin(a) * 0.25, h * 0.55))
        o = cylm(0, 0, 0.035, 0, d.length, M['walnut'], cn, name + ' Trunk', 8, r_top=0.018)
        o.location = (X, Y, 0.5); o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    me = ico(0.09, 1, M['olive_leaf'], name + ' Leaf', noise=0.3)
    for i in range(60):
        a = random.uniform(0, 2 * math.pi); rr = random.uniform(0.0, 0.62)
        o = bpy.data.objects.new(name + ' Leaves', me)
        o.location = (X + rr * math.cos(a), Y + rr * math.sin(a), random.uniform(h * 0.62, h))
        o.scale = (1.4, 0.5, 0.6); o.rotation_euler = (0, random.uniform(-0.5, 0.5), a)
        link(o, cn)
    add_obst(x, y, 2.2, 2.2, 0, name)

def rug(x0, y0, x1, y1, mat, cn=FU, name='Rug'):
    box(x0, y0, x1, y1, 0.0, 0.014, mat, cn, name, 0.006)

def frame_art(x, y, facing, w, h, zc, mat, cn=FU, name='Art', light=True):
    g = Group(name, x, y, facing, cn, obst=False)
    g.box(-w / 2, -0.02, zc - h / 2, w / 2, 0.025, zc + h / 2, M['black'], 0.003)
    g.box(-w / 2 + 0.02, 0.025, zc - h / 2 + 0.02, w / 2 - 0.02, 0.03, zc + h / 2 - 0.02, M['linen'], 0)
    g.box(-w / 2 + 0.07, 0.03, zc - h / 2 + 0.07, w / 2 - 0.07, 0.034, zc + h / 2 - 0.07, mat, 0)
    if light:
        picture_light(x, y, facing, w * 0.7, zc + h / 2 + 0.15)

def books(x0, y, z, n, cn, axis='x', name='Books'):
    """row of books starting at plan (x0, y) ft"""
    pos = x0
    for i in range(n):
        wft = random.uniform(0.09, 0.14); h = random.uniform(0.21, 0.29)
        if axis == 'x':
            box(pos, y - 0.5, pos + wft, y, z, z + h, random.choice(BOOK_MATS), cn, name)
        else:
            box(y - 0.5, pos, y, pos + wft, z, z + h, random.choice(BOOK_MATS), cn, name)
        pos += wft + 0.005
    return pos

def vessel(x, y, z, r, h, mat, cn, name='Vessel'):
    X, Y = W(x, y)
    o = cylm(X, Y, r, z, z + h, mat, cn, name, 28, r_top=r * 0.55)
    o.modifiers.new('Sub', 'SUBSURF').levels = 1
    return o

def stack(x, y, z, cn, n=3, name='Coffee Table Books'):
    for i in range(n):
        w, d = random.uniform(0.9, 1.1), random.uniform(0.7, 0.85)
        box(x - w / 2, y - d / 2, x + w / 2, y + d / 2, z + i * 0.035, z + (i + 1) * 0.035 - 0.003,
            random.choice(BOOK_MATS), cn, name, 0.002)
    return z + n * 0.035

def bed(x, y, facing, w, l, cn=FU, name='Bed', throw=None, panel=None):
    g = Group(name, x, y, facing, cn, w / 2 + 0.05, l / 2 + 0.05)
    g.box(-w / 2 - 0.03, -l / 2, 0.06, w / 2 + 0.03, l / 2 + 0.03, 0.34, panel or M['mushroom'], 0.03)    # upholstered base
    g.box(-w / 2 + 0.03, -l / 2 + 0.05, 0.34, w / 2 - 0.03, l / 2 - 0.02, 0.58, M['linen'], 0.06)          # mattress
    g.box(-w / 2 - 0.03, -l / 2 + 0.55, 0.42, w / 2 + 0.03, l / 2 + 0.03, 0.62, M['linen'], 0.08)          # duvet
    g.box(-w / 2 - 0.05, l / 2 - 0.85, 0.43, w / 2 + 0.05, l / 2 + 0.05, 0.645, M['charcoal'], 0.05)       # coverlet
    g.box(-w / 2 + 0.25, l / 2 - 0.75, 0.46, w / 2 - 0.25, l / 2 - 0.35, 0.665, throw or M['rust'], 0.04)  # throw
    n = 2
    pw = (w - 0.1) / n
    for i in range(n):
        x0 = -w / 2 + 0.05 + i * pw
        g.box(x0 + 0.02, -l / 2 + 0.03, 0.55, x0 + pw - 0.02, -l / 2 + 0.20, 0.98, M['charcoal'], 0.09)   # euro sham
        g.box(x0 + 0.06, -l / 2 + 0.17, 0.56, x0 + pw - 0.06, -l / 2 + 0.33, 0.86, M['linen'], 0.08)
        g.box(x0 + 0.20, -l / 2 + 0.31, 0.56, x0 + pw - 0.20, -l / 2 + 0.43, 0.76, throw or M['rust'], 0.05)
    return g

def channel_headboard(x0, y0, x1, y1, z0, z1, mat, cn, wall_side='W', name='Upholstered Wall Panel'):
    """vertical channel-tufted wall panel (plan ft)"""
    horiz = abs(x1 - x0) > abs(y1 - y0)
    n = int((abs(x1 - x0) if horiz else abs(y1 - y0)) / 0.55)
    for i in range(n):
        if horiz:
            a = x0 + (x1 - x0) * i / n; b = x0 + (x1 - x0) * (i + 1) / n
            box(a + 0.01, y0, b - 0.01, y1, z0, z1, mat, cn, name, 0.04)
        else:
            a = y0 + (y1 - y0) * i / n; b = y0 + (y1 - y0) * (i + 1) / n
            box(x0, a + 0.01, x1, b - 0.01, z0, z1, mat, cn, name, 0.04)

def floating_nightstand(x, y, facing, cn, name='Nightstand', pendant=True):
    g = Group(name, x, y, facing, cn, 0.28, 0.22)
    g.box(-0.28, -0.21, 0.30, 0.28, 0.21, 0.56, M['walnut'], 0.01)
    g.box(-0.26, 0.205, 0.33, 0.26, 0.215, 0.53, M['walnut'], 0.003)
    g.box(-0.10, 0.215, 0.42, 0.10, 0.225, 0.44, M['bronze'], 0)
    X, Y = W(x, y)
    vessel(x + 0.25, y + 0.1, 0.56, 0.05, 0.16, M['ceramic2'], cn, name + ' Vase')
    stack(x - 0.2, y, 0.56, cn, 2, name + ' Books')
    if pendant:
        cylm(X, Y, 0.004, 1.15, CEIL, M['bronze'], cn, name + ' Pendant Cord', 6)
        sphere(X, Y, 1.05, 0.12, M['alabaster'], cn, name + ' Pendant')
        add_point(name + ' Pendant Light', X, Y, 1.05, 14, radius=0.12)

def dresser(x, y, facing, w, cn=FU, name='Dresser'):
    g = Group(name, x, y, facing, cn, w / 2, 0.26)
    g.box(-w / 2, -0.25, 0.12, w / 2, 0.25, 0.80, M['navy'], 0.008)
    g.box(-w / 2 + 0.05, -0.2, 0, w / 2 - 0.05, 0.2, 0.12, M['bronze'], 0.002)
    cols = 2
    cw = (w - 0.04) / cols
    for c in range(cols):
        for r in range(3):
            x0 = -w / 2 + 0.02 + c * cw; z0 = 0.15 + r * 0.215
            g.box(x0 + 0.006, 0.245, z0, x0 + cw - 0.006, 0.258, z0 + 0.20, M['navy'], 0.002)
            g.box(x0 + cw / 2 - 0.12, 0.258, z0 + 0.17, x0 + cw / 2 + 0.12, 0.268, z0 + 0.185, M['bronze'], 0)
    g.box(-w / 2, -0.25, 0.80, w / 2, 0.25, 0.83, M['marble'], 0.003)
    return g

def toilet(x, y, facing, cn, name='Toilet'):
    g = Group(name, x, y, facing, cn, 0.22, 0.34)
    g.box(-0.19, -0.34, 0.35, 0.19, -0.20, 0.80, M['porcelain'], 0.03)
    g.cyl(0, 0.02, 0.17, 0.0, 0.40, M['porcelain'], 28, rx=0.18, ry=0.24)
    g.cyl(0, 0.03, 0.18, 0.40, 0.43, M['porcelain'], 28, rx=0.19, ry=0.25)

def vanity(x0, y0, x1, y1, cn, sinks, wall_side, name='Vanity', mirror=True):
    """floating charcoal oak vanity, marble top, bronze faucets, backlit mirrors (plan ft)"""
    box(x0, y0, x1, y1, 0.30, 0.82, M['navy'], cn, name, 0.006, obst=True, tag=name)
    box(x0, y0, x1, y1, 0.28, 0.30, M['led'], cn, name + ' Toe LED')
    box(x0 - 0.04, y0 - 0.04, x1 + 0.04, y1 + 0.04, 0.82, 0.86, M['marble'], cn, name + ' Top', 0.003)
    off = {'E': (0.30, 0), 'W': (-0.30, 0), 'N': (0, 0.30), 'S': (0, -0.30)}[wall_side]
    for (sx, sy) in sinks:
        X, Y = W(sx, sy)
        cylm(X, Y, 0.20, 0.861, 0.862, M['glass_black'], cn, name + ' Basin', 28, rx=0.22, ry=0.16)
        fx, fy = X + off[0], Y + off[1]
        cylm(fx, fy, 0.016, 0.86, 1.13, M['bronze'], cn, name + ' Faucet', 10)
        boxm(min(fx, fx - off[0] * 0.4) - 0.012, min(fy, fy - off[1] * 0.4) - 0.012, 1.10,
             max(fx, fx - off[0] * 0.4) + 0.012, max(fy, fy - off[1] * 0.4) + 0.012, 1.13, M['bronze'], cn, name + ' Spout')
    return

def backlit_mirror(x, y0, y1, z0, z1, cn, side='E', name='Backlit Mirror'):
    """mirror on a wall running along plan y at plan x"""
    d = 0.05 if side == 'E' else -0.05
    box(x - d, y0, x, y1, z0, z1, M['mirror'], cn, name, 0.004)
    box(x - d * 0.5, y0 - 0.06, x - d * 0.2, y1 + 0.06, z0 - 0.06, z1 + 0.06, M['led'], cn, name + ' Halo')

def shower(x0, y0, x1, y1, glass_edges, cn, name='Shower', head=(None, None)):
    box(x0, y0, x1, y1, 0.0, 0.012, M['tile'], cn, name + ' Floor')
    for (ax, ay, bx, by) in glass_edges:
        box(ax, ay, bx, by, 0.02, 2.05, M['shower_glass'], cn, name + ' Glass')
        box(ax, ay, bx, by, 2.05, 2.07, M['bronze'], cn, name + ' Glass Rail')
        add_obst((ax + bx) / 2, (ay + by) / 2, abs(bx - ax) / 2 + 0.05, abs(by - ay) / 2 + 0.05, 0, name + ' Glass')
    if head[0] is not None:
        X, Y = W(*head)
        cylm(X, Y, 0.15, 2.30, 2.32, M['bronze'], cn, name + ' Rain Head', 28)
        cylm(X, Y, 0.012, 2.32, CEIL, M['bronze'], cn, name + ' Arm', 8)

def marble_walls(segments, cn, z1=CEIL, name='Marble Slab Wall'):
    for (x0, y0, x1, y1) in segments:
        box(x0, y0, x1, y1, 0.0, z1, M['marble'], cn, name)

def closet_system(x0, y0, x1, y1, cn, name='Closet', open_sides='LRB'):
    """charcoal oak closet with glass doors, LED rods, shelves and garments (plan ft)"""
    d = 0.62 / F
    runs = []
    if 'L' in open_sides: runs.append((x0, y0, x0 + d, y1, 'v'))
    if 'R' in open_sides: runs.append((x1 - d, y0, x1, y1, 'v'))
    if 'B' in open_sides: runs.append((x0 + d, y1 - d, x1 - d, y1, 'h'))
    for (a0, b0, a1, b1, o) in runs:
        box(a0, b0, a1, b1, 0.0, 0.08, M['black'], cn, name + ' Plinth')
        box(a0, b0, a1, b1, 2.35, 2.42, M['navy'], cn, name + ' Top')
        box(a0, b0, a1, b1, 1.93, 1.95, M['led'], cn, name + ' LED Shelf')
        mx, my = (a0 + a1) / 2, (b0 + b1) / 2
        L = (b1 - b0) if o == 'v' else (a1 - a0)
        n = int(L / 0.42)
        for i in range(n):
            t = (b0 if o == 'v' else a0) + 0.25 + i * 0.42
            h1 = random.uniform(0.95, 1.3)
            col = random.choice([M['linen'], M['charcoal'], M['mushroom'], M['rust'], M['black_leather'], M['boucle']])
            if o == 'v':
                box(mx - 0.75, t, mx + 0.75, t + 0.10, 1.80 - h1, 1.78, col, cn, name + ' Garment', 0.02)
            else:
                box(t, my - 0.75, t + 0.10, my + 0.75, 1.80 - h1, 1.78, col, cn, name + ' Garment', 0.02)
        if o == 'v':
            box(mx - 0.03, b0, mx + 0.03, b1, 1.80, 1.82, M['bronze'], cn, name + ' Rod')
        else:
            box(a0, my - 0.03, a1, my + 0.03, 1.80, 1.82, M['bronze'], cn, name + ' Rod')
    add_obst((x0 + x1) / 2, (y0 + y1) / 2, 0.1, 0.1, 0, name)

def wine_wall(x0, y0, x1, y1, cn, name='Wine Wall'):
    """glass-front, backlit wine display (plan ft, along the east wall)"""
    box(x0, y0, x1, y1, 0.0, 2.40, M['navy'], cn, name + ' Case', 0.004, obst=True, tag=name)
    box(x1 - 0.12, y0 + 0.15, x1 - 0.08, y1 - 0.15, 0.10, 2.30, M['led'], cn, name + ' Backlight')
    bottle = bpy.data.meshes.new('Wine Bottle')
    v, f = geo.cyl_data(0.037, 0, 0.24, 12)
    v2, f2 = geo.cyl_data(0.013, 0.24, 0.31, 8)
    off = len(v)
    bottle.from_pydata(v + v2, [], f + [tuple(i + off for i in ff) for ff in f2]); bottle.update()
    bottle.materials.append(principled('Wine Bottle Glass', (0.02, 0.05, 0.02), 0.08))
    for ry in range(9):
        z = 0.15 + ry * 0.24
        box(x0 + 0.1, y0 + 0.1, x1 - 0.1, y1 - 0.1, z - 0.012, z, M['bronze'], cn, name + ' Rail')
        yy = y0 + 0.35
        while yy < y1 - 0.3:
            o = bpy.data.objects.new('Wine Bottle', bottle)
            X, Y = W((x0 + x1) / 2 + 0.3, yy)
            o.location = (X, Y, z + 0.045); o.rotation_euler = (0, -math.pi / 2, 0)
            link(o, cn)
            yy += 0.30
    box(x0 - 0.04, y0 + 0.05, x0, y1 - 0.05, 0.05, 2.35, M['glass'], cn, name + ' Glass Doors')
    for yy in (y0 + 0.08, (y0 + y1) / 2, y1 - 0.08):
        box(x0 - 0.05, yy - 0.03, x0, yy + 0.03, 0.03, 2.37, M['bronze'], cn, name + ' Door Frame')
    area(name + ' Glow', x0 + 0.3, y0 + 0.4, x1 - 0.3, y1 - 0.4, 12, z=1.2, group='accent').rotation_euler = (0, math.radians(-90), 0)

# ============================================================================
# ROOMS
# ============================================================================
# ---------------- Kitchen ----------------------------------------------------
K = 'Kitchen'
wine_wall(43.9, 12.0, 45.88, 16.6, K)
box(43.6, 16.6, 45.88, 19.6, 0.0, 2.40, M['navy'], K, 'Panel-Ready Refrigerator', 0.004, obst=True)
for (z0, z1) in ((0.05, 1.55), (1.58, 2.38)):
    box(43.585, 16.65, 43.6, 19.55, z0, z1, M['navy'], K, 'Fridge Panel', 0.002)
box(43.53, 17.95, 43.585, 18.02, 0.75, 1.45, M['bronze'], K, 'Fridge Pull')
box(43.53, 18.18, 43.585, 18.25, 0.75, 1.45, M['bronze'], K, 'Fridge Pull')
box(43.6, 19.6, 45.88, 31.4, 0.10, 0.86, M['navy'], K, 'Base Cabinets', 0.003, obst=True)
box(43.7, 19.6, 45.88, 31.4, 0.0, 0.10, M['led'], K, 'Toe Kick LED')
for i in range(12):
    yy = 19.6 + i * (31.4 - 19.6) / 12
    box(43.585, yy + 0.01, 43.6, yy + (31.4 - 19.6) / 12 - 0.01, 0.12, 0.84, M['navy'], K, 'Cabinet Front', 0.002)
    box(43.57, yy + 0.25, 43.585, yy + (31.4 - 19.6) / 12 - 0.25, 0.80, 0.815, M['bronze'], K, 'Edge Pull')
box(43.4, 19.6, 45.88, 31.4, 0.86, 0.92, M['marble'], K, 'Marble Counter', 0.003)
box(45.80, 19.6, 45.88, 31.4, 0.92, 2.40, M['marble'], K, 'Marble Slab Backsplash')
box(43.75, 23.3, 45.55, 26.0, 0.92, 0.925, M['glass_black'], K, 'Induction Cooktop')
box(44.25, 23.2, 45.80, 26.1, 1.62, CEIL, M['wall'], K, 'Plaster Range Hood', 0.02)
box(44.20, 23.15, 45.80, 26.15, 1.58, 1.62, M['bronze'], K, 'Hood Band', 0.003)
for (a, b) in [(19.8, 23.0), (26.3, 31.2)]:                    # floating oak shelves with LED
    for z in (1.45, 1.90):
        box(44.85, a, 45.80, b, z, z + 0.045, M['walnut'], K, 'Floating Shelf', 0.003)
        box(44.90, a + 0.05, 45.75, b - 0.05, z - 0.003, z, M['led'], K, 'Shelf LED')
    for z in (1.495, 1.945):
        yy = a + 0.4
        while yy < b - 0.4:
            r = random.choice([0.05, 0.07, 0.09])
            vessel(45.35, yy, z, r, random.choice([0.12, 0.2, 0.28]), random.choice([M['ceramic'], M['ceramic2'], M['porcelain']]), K, 'Ceramic')
            yy += random.uniform(0.7, 1.1)
area('Under-Shelf Wash', 44.0, 19.8, 45.7, 31.0, 30, z=1.44, group='accent')
box(43.2, 31.4, 45.88, 33.75, 0.10, 0.86, M['navy'], K, 'Base Cabinets L', 0.003, obst=True)
box(43.1, 31.4, 45.88, 33.75, 0.86, 0.92, M['marble'], K, 'Marble Counter L', 0.003)
box(40.53, 31.65, 43.2, 33.75, 0.0, 2.40, M['navy'], K, 'Oven Tower', 0.004, obst=True)
box(40.9, 31.6, 42.8, 31.65, 0.75, 1.32, M['glass_black'], K, 'Wall Oven')
box(40.9, 31.6, 42.8, 31.65, 1.37, 1.82, M['glass_black'], K, 'Speed Oven')
box(40.9, 31.57, 42.8, 31.60, 1.27, 1.29, M['bronze'], K, 'Oven Handle')
box(40.9, 31.57, 42.8, 31.60, 1.77, 1.79, M['bronze'], K, 'Oven Handle')
# island: marble waterfall, charcoal base, bronze foot rail
box(36.5, 21.4, 39.6, 28.0, 0.10, 0.88, M['navy'], K, 'Island Base', 0.003)
box(35.8, 21.2, 39.8, 28.2, 0.88, 0.95, M['marble'], K, 'Island Top', 0.003)
box(35.8, 21.2, 39.8, 21.4, 0.0, 0.88, M['marble'], K, 'Waterfall', 0.003)
box(35.8, 28.0, 39.8, 28.2, 0.0, 0.88, M['marble'], K, 'Waterfall', 0.003)
box(36.3, 21.5, 36.4, 27.9, 0.20, 0.23, M['bronze'], K, 'Foot Rail')
add_obst(37.8, 24.7, 2.0, 3.5, 0, 'Island')
box(38.3, 23.9, 39.35, 25.6, 0.94, 0.951, M['steel'], K, 'Undermount Sink')
cyl(39.5, 24.75, 0.018, 0.95, 1.36, M['bronze'], K, 'Faucet', 10)
box(39.05, 24.70, 39.52, 24.80, 1.33, 1.36, M['bronze'], K, 'Faucet Spout')
X, Y = W(37.0, 26.6)
cylm(X, Y, 0.22, 0.95, 0.99, M['walnut'], K, 'Board', 24)
for (dx, c) in ((-0.06, M['olive_leaf']), (0.07, M['rust']), (0.0, M['ceramic2'])):
    sphere(X + dx, Y + dx * 0.5, 1.03, 0.045, c, K, 'Fruit')
vessel(37.0, 23.0, 0.95, 0.10, 0.32, M['ceramic'], K, 'Island Vase')
for i in range(5):
    sphere(*W(37.0 + random.uniform(-0.2, 0.2), 23.0 + random.uniform(-0.2, 0.2)), 1.45 + random.uniform(0, 0.2), 0.05,
           M['olive_leaf'], K, 'Branch Leaves', sx=1.5, sy=0.4, sz=0.4, seg=8)
for yy in (22.9, 24.7, 26.5):
    g = Group('Counter Stool', 34.9, yy, 'W', K, 0.25, 0.25)
    g.cyl(0, 0, 0.20, 0.0, 0.02, M['bronze'], 28)
    g.cyl(0, 0, 0.03, 0.02, 0.62, M['bronze'], 10)
    g.cyl(0, 0, 0.17, 0.30, 0.31, M['bronze'], 24, cap=False)
    g.box(-0.22, -0.21, 0.62, 0.22, 0.21, 0.70, M['cognac'], 0.04)
    g.box(-0.22, -0.24, 0.66, 0.22, -0.17, 0.95, M['cognac'], 0.04)
for yy in (22.3, 24.7, 27.1):
    X, Y = W(37.8, yy)
    cylm(X, Y, 0.004, 1.95, CEIL, M['bronze'], K, 'Pendant Cord', 6)
    sphere(X, Y, 1.85, 0.22, M['bronze'], K, 'Dome Pendant', sz=0.55)
    cylm(X, Y, 0.17, 1.735, 1.74, M['bulb'], K, 'Pendant Diffuser', 24)
    add_point('Island Pendant', X, Y, 1.70, 30, radius=0.1, group='accent')

# ---------------- Dining ------------------------------------------------------
D = 'Dining'
box(31.0, 13.2, 39.0, 16.0, 0.72, 0.77, M['walnut'], D, 'Dining Table', 0.01)
for lx in (32.4, 37.6):
    box(lx - 0.35, 13.9, lx + 0.35, 15.3, 0.0, 0.72, M['walnut'], D, 'Plinth Base', 0.01)
add_obst(35.0, 14.6, 4.0, 1.4, 0, 'Dining Table')
for xx in (32.4, 35.0, 37.6):
    chair(xx, 12.85, 'S', M['mushroom'], cn=D)
    chair(xx, 16.35, 'N', M['mushroom'], cn=D)
chair(30.35, 14.6, 'E', M['black_leather'], cn=D)
chair(39.65, 14.6, 'W', M['black_leather'], cn=D)
X, Y = W(35.0, 14.6)
for (R, z) in ((0.75, 1.92), (0.55, 1.80), (0.35, 1.70)):     # tiered ring chandelier
    torus(X, Y, z, R, 0.022, M['bronze'], D, 'Ring Chandelier')
    torus(X, Y, z - 0.024, R, 0.008, M['led'], D, 'Ring Chandelier LED')
    for k in range(3):
        a = k * 2 * math.pi / 3 + R
        cylm(X + R * math.cos(a), Y + R * math.sin(a), 0.003, z, CEIL, M['bronze'], D, 'Chandelier Cable', 5)
add_point('Chandelier', X, Y, 1.65, 70, radius=0.5, group='accent')
for (dx, h, m) in ((-0.9, 0.34, M['ceramic']), (-0.55, 0.22, M['ceramic2']), (0.7, 0.28, M['ceramic'])):
    vessel(35.0 + dx * 1.5, 14.6, 0.77, 0.09, h, m, D, 'Centerpiece Vessel')

# ---------------- Living --------------------------------------------------------
L = 'Living'
rug(18.9, 19.0, 27.4, 30.9, M['rug2'], L, 'Living Rug')
g = Group('Sectional Sofa', 26.55, 22.75, 'W', L, obst=False)
add_obst(26.55, 22.75, 1.55, 4.7, 0, 'Sectional (leg B)')
add_obst(23.0, 19.55, 2.05, 1.45, 0, 'Sectional (leg A)')
LB = 1.42
g.box(-LB, -0.47, 0.10, LB, 0.47, 0.40, M['boucle'], 0.06)
g.box(-LB, -0.47, 0.40, LB, -0.22, 0.76, M['boucle'], 0.08)
g.box(-LB + 0.05, -0.42, 0.0, LB - 0.05, 0.42, 0.10, M['black'], 0.005)
for k in range(3):
    a = -LB + 0.22 + k * 0.87
    g.box(a + 0.01, -0.22, 0.40, a + 0.86, 0.46, 0.51, M['boucle'], 0.07)
g.box(-LB, -0.47, 0.40, -LB + 0.22, 0.47, 0.58, M['boucle'], 0.07)
for (px, m) in [(-0.95, M['rust']), (-0.55, M['charcoal']), (0.9, M['olive'])]:
    g.box(px - 0.22, -0.22, 0.48, px + 0.22, -0.08, 0.88, m, 0.08)
g.box(0.2, -0.3, 0.51, 0.75, 0.40, 0.55, M['charcoal'], 0.03)                  # folded throw
g2 = Group('Sectional Sofa A', 23.05, 19.55, 'S', L, obst=False)
g2.box(-0.62, -0.44, 0.10, 0.62, 0.44, 0.40, M['boucle'], 0.06)
g2.box(-0.62, -0.44, 0.40, 0.62, -0.20, 0.76, M['boucle'], 0.08)
g2.box(0.40, -0.44, 0.40, 0.62, 0.44, 0.58, M['boucle'], 0.07)
g2.box(-0.62, -0.20, 0.40, 0.39, 0.42, 0.51, M['boucle'], 0.07)
g2.box(-0.57, -0.40, 0.0, 0.57, 0.40, 0.10, M['black'], 0.005)
for (px, m) in [(0.12, M['rust']), (-0.3, M['charcoal'])]:
    g2.box(px - 0.22, -0.2, 0.48, px + 0.22, -0.06, 0.88, m, 0.08)
# round two-tier marble coffee table
X, Y = W(22.2, 25.3)
cylm(X, Y, 0.55, 0.0, 0.34, M['nero'], L, 'Drum Coffee Table', 48)
cylm(X + 0.35, Y - 0.35, 0.38, 0.0, 0.42, M['marble'], L, 'Drum Coffee Table Upper', 48)
add_obst(22.4, 25.6, 2.6, 2.6, 0, 'Coffee Tables')
stack(22.3, 24.6, 0.34, L, 3)
vessel(23.2, 26.5, 0.42, 0.11, 0.18, M['ceramic2'], L, 'Bowl')
sphere(X + 0.38, Y - 0.40, 0.47, 0.05, M['bronze'], L, 'Sculpture Orb')
lounge_chair(21.4, 30.0, 'N', M['cognac'], 'Living Lounge Chair L', L)
lounge_chair(24.6, 30.0, 'N', M['cognac'], 'Living Lounge Chair R', L)
X, Y = W(23.0, 30.4)
cylm(X, Y, 0.22, 0.0, 0.5, M['bronze'], L, 'Drum Side Table', 32)
lamp(23.0, 30.4, 0.5, L, h=0.32, r=0.13, name='Side Table Lamp', power=14)
add_obst(23.0, 30.4, 0.75, 0.75, 0, 'Drum Side Table')
olive_tree(17.7, 32.4, L, 2.2)
arc_lamp(19.0, 18.7, 21.7, 21.9, L)
# fireplace feature wall: book-matched Nero marble, linear fire, art above
box(15.53, 24.15, 16.49, 29.34, 0.95, CEIL, M['nero'], L, 'Fireplace Surround')
box(15.53, 24.15, 16.49, 29.34, 0.0, 0.30, M['nero'], L, 'Fireplace Hearth')
box(15.53, 24.15, 15.60, 29.34, 0.30, 0.95, M['glass_black'], L, 'Firebox Back')
box(15.6, 24.3, 16.3, 29.2, 0.30, 0.32, M['fire_glass'], L, 'Fire Glass Bed')
for i in range(7):
    X, Y = W(15.9 + random.uniform(-0.15, 0.15), 24.9 + i * 0.62)
    geo.flame_sheet(X, Y, 0.31, 0.32, random.uniform(0.28, 0.42), False, M['flame'], L, 'Flame')
add_point('Fireplace Glow', *W(16.3, 26.7), 0.55, 45, (1.0, 0.5, 0.2), 0.3, group='accent')
box(16.49, 24.15, 16.53, 29.34, 0.30, 0.95, M['glass'], L, 'Firebox Glass')
for (a, b) in ((22.95, 24.12), (29.34, 30.56)):
    box(14.57, a, 16.49, b, 0.0, CEIL, M['nero'], L, 'Marble Pier')
frame_art(16.52, 26.75, 'E', 1.45, 1.05, 1.75, M['art2'], L, 'Fireplace Art')
# display niche (firewood below, styled shelves with LED above)
box(14.57, 18.54, 14.62, 22.95, 0, CEIL, M['fluted'], L, 'Niche Back')
for z in (0.0, 0.85, 1.45, 2.05):
    box(14.6, 18.54, 16.49, 22.95, z, z + 0.04, M['walnut'], L, 'Niche Shelf')
    if z > 0:
        box(14.65, 18.6, 16.4, 22.9, z - 0.004, z, M['led'], L, 'Niche LED')
for r in range(5):
    for c in range(9):
        yy = 18.85 + c * 0.47 + (0.23 if r % 2 else 0)
        if yy > 22.75: continue
        o = cylm(0, 0, random.uniform(0.045, 0.06), 0, 0.56, M['log'], L, 'Log', 9, smooth=False)
        o.rotation_euler = (0, math.pi / 2, 0)
        X, Y = W(14.65, yy); o.location = (X, Y, 0.11 + r * 0.14)
vessel(15.5, 19.6, 0.89, 0.09, 0.30, M['ceramic'], L, 'Niche Vase')
books(21.1, 15.6, 0.89, 8, L, 'y')
vessel(15.5, 20.2, 1.49, 0.12, 0.18, M['ceramic2'], L, 'Niche Bowl')
sphere(*W(15.5, 22.2), 1.58, 0.08, M['bronze'], L, 'Niche Orb')
books(18.8, 15.6, 2.09, 10, L, 'y')
add_obst(15.5, 20.7, 1.0, 2.3, 0, 'Display niche')
area('Niche Wash', 14.7, 18.7, 16.4, 22.8, 12, z=2.0, group='accent')
curtain(18.9, 20.6, 11.0, 0.0, CEIL - 0.03, M['sheer'], L, 'Sheer Drapery')
curtain(40.0, 41.7, 11.0, 0.0, CEIL - 0.03, M['sheer'], L, 'Sheer Drapery')
box(18.8, 10.95, 41.8, 11.05, CEIL - 0.06, CEIL - 0.02, M['black'], L, 'Drapery Track')
frame_art(14.6, 33.0, 'E', 1.0, 1.3, 1.55, M['art2'], L, 'Living Art')

# ---------------- Den / library ---------------------------------------------------------
DN = 'Den'
rug(17.6, 37.0, 25.6, 44.4, M['rug'], DN, 'Den Rug')
g = Group('Den Leather Sofa', 22.2, 44.6, 'N', DN, 1.25, 0.48)
g.box(-1.20, -0.47, 0.12, 1.20, 0.47, 0.42, M['cognac'], 0.05)
g.box(-1.20, -0.47, 0.42, 1.20, -0.25, 0.80, M['cognac'], 0.06)
g.box(-1.20, -0.47, 0.42, -1.04, 0.47, 0.64, M['cognac'], 0.05)
g.box(1.04, -0.47, 0.42, 1.20, 0.47, 0.64, M['cognac'], 0.05)
g.box(-1.0, -0.25, 0.42, 1.0, 0.45, 0.52, M['cognac'], 0.05)
for (px, m) in [(-0.7, M['linen']), (0.65, M['olive'])]:
    g.box(px - 0.2, -0.24, 0.5, px + 0.2, -0.1, 0.86, m, 0.07)
for (lx, ly) in [(-1.1, -0.4), (1.1, -0.4), (-1.1, 0.4), (1.1, 0.4)]:
    g.box(lx - 0.02, ly - 0.02, 0, lx + 0.02, ly + 0.02, 0.12, M['bronze'], 0)
X, Y = W(22.2, 40.6)
cylm(X, Y, 0.42, 0.0, 0.38, M['walnut'], DN, 'Den Coffee Table', 40)
stack(22.2, 40.6, 0.38, DN, 2)
add_obst(22.2, 40.6, 1.45, 1.45, 0, 'Den Coffee Table')
box(25.5, 37.0, 27.5, 41.6, 0.72, 0.77, M['walnut'], DN, 'Desk', 0.006, obst=True)
for ly in (37.2, 41.4):
    box(25.6, ly - 0.08, 27.4, ly + 0.08, 0.0, 0.72, M['bronze'], DN, 'Desk Leg')
chair(24.7, 39.3, 'E', M['black_leather'], 'Desk Chair', DN, M['bronze'])
lamp(27.0, 37.6, 0.77, DN, h=0.38, r=0.12, name='Desk Lamp', power=12)
box(27.38, 38.4, 27.45, 40.4, 1.0, 1.65, M['screen'], DN, 'Wall Display')
# built-in library wall along the north side
box(17.0, 35.43, 21.9, 35.6, 0.0, CEIL, M['navy'], DN, 'Library Back')
add_obst(19.45, 36.17, 2.45, 0.74, 0, 'Library')
for (a, b) in ((17.0, 17.15), (21.75, 21.9)):
    box(a, 35.6, b, 36.9, 0.0, CEIL, M['navy'], DN, 'Library Side')
box(17.15, 35.6, 21.75, 36.9, 0.0, 0.10, M['navy'], DN, 'Library Plinth')
box(17.15, 35.6, 21.75, 36.9, 2.62, CEIL, M['navy'], DN, 'Library Top')
for k in range(6):
    z = 0.10 + k * 0.42
    box(17.15, 35.6, 21.75, 36.9, z, z + 0.03, M['navy'], DN, 'Library Shelf')
    box(17.15, 36.88, 21.75, 36.92, z, z + 0.03, M['bronze'], DN, 'Library Shelf Edge')
    end = books(17.25, 36.6, z + 0.03, random.randint(14, 22), DN)
    if end < 21.0:
        vessel(min(21.4, end + 0.4), 36.5, z + 0.03, 0.06, 0.18, random.choice([M['ceramic'], M['ceramic2']]), DN, 'Shelf Object')
    box(17.15, 35.65, 21.75, 36.85, z + 0.395, z + 0.399, M['led'], DN, 'Library LED')
frame_art(27.45, 43.3, 'W', 0.9, 1.1, 1.5, M['art3'], DN, 'Den Art')
plant(26.6, 44.8, DN, 1.3, 0.2, 'Den Plant')
arc_lamp(19.0, 44.9, 20.8, 42.6, DN, 'Den Arc Lamp')

# ---------------- Primary bedroom ------------------------------------------------
PB = 'Primary Bedroom'
rug(3.0, 6.2, 10.6, 15.0, M['rug2'], PB, 'Primary Rug')
channel_headboard(0.95, 4.5, 1.25, 16.7, 0.0, 1.55, M['mushroom'], PB)
bed(4.75, 10.6, 'E', 1.93, 2.13, PB, 'Primary King Bed', panel=M['mushroom'])
g = Group('Bed Bench', 8.8, 10.6, 'E', PB, 0.25, 0.7)
g.box(-0.65, -0.22, 0.30, 0.65, 0.22, 0.46, M['cognac'], 0.04)
for lx in (-0.6, 0.6):
    g.box(lx - 0.02, -0.18, 0.0, lx + 0.02, 0.18, 0.30, M['bronze'], 0)
floating_nightstand(1.95, 6.0, 'E', PB, 'Primary Nightstand L')
floating_nightstand(1.95, 15.2, 'E', PB, 'Primary Nightstand R')
dresser(13.15, 10.5, 'W', 1.75, PB, 'Primary Dresser')
frame_art(13.75, 10.5, 'W', 1.4, 0.9, 1.65, M['art3'], PB, 'Primary Dresser Art')
vessel(13.2, 9.3, 0.83, 0.09, 0.30, M['ceramic'], PB, 'Dresser Vase')
stack(13.2, 11.4, 0.83, PB, 3)
lounge_chair(11.9, 3.7, -135, M['boucle'], 'Primary Lounge Chair', PB, M['black'])
X, Y = W(10.6, 5.2)
cylm(X, Y, 0.25, 0.0, 0.42, M['cognac'], PB, 'Ottoman', 28)
add_obst(10.6, 5.2, 0.9, 0.9, 0, 'Ottoman')
arc_lamp(13.4, 1.9, 12.3, 3.2, PB, 'Primary Reading Lamp')
plant(2.2, 2.3, PB, 1.5, 0.22, 'Primary Plant')
curtain(4.7, 6.2, 1.85, 0.0, CEIL - 0.03, M['sheer'], PB, 'Primary Sheers')
curtain(12.1, 13.6, 1.85, 0.0, CEIL - 0.03, M['sheer'], PB, 'Primary Sheers')

# ---------------- Primary bathroom -----------------------------------------------
PBA = 'Primary Bath'
marble_walls([(0.6, 18.55, 7.3, 18.65), (0.62, 18.55, 0.72, 22.0), (0.62, 26.0, 0.72, 30.5)], PBA)
shower(0.72, 18.65, 7.3, 22.0, [(1.6, 21.9, 7.3, 22.0), (7.25, 19.6, 7.35, 22.0)], PBA, 'Primary Shower', head=(3.8, 20.2))
box(0.72, 18.65, 1.6, 22.0, 0.0, 0.46, M['marble'], PBA, 'Shower Bench', 0.004)
box(0.73, 19.0, 0.78, 21.5, 1.2, 1.6, M['led'], PBA, 'Shower Niche LED')
vanity(12.3, 21.9, 14.0, 30.4, PBA, [(13.2, 23.6), (13.2, 28.4)], 'E', 'Primary Vanity')
box(13.95, 21.9, 14.0, 30.4, 0.86, 2.4, M['marble'], PBA, 'Vanity Marble Wall')
for yy in (23.6, 28.4):
    backlit_mirror(13.93, yy - 1.1, yy + 1.1, 1.08, 2.05, PBA, 'E')
for (yy, m) in ((26.0, M['towel']),):
    box(12.5, yy - 0.5, 13.3, yy + 0.5, 0.86, 0.96, m, PBA, 'Folded Towels', 0.02)
vessel(13.0, 26.0, 0.96, 0.05, 0.14, M['ceramic'], PBA, 'Vanity Vessel')
X, Y = W(4.2, 28.6)
tub = cylm(X, Y, 1, 0.0, 0.58, M['porcelain'], PBA, 'Freestanding Stone Tub', 48, rx=0.84, ry=0.40, cap=False)
md = tub.modifiers.new('Solid', 'SOLIDIFY'); md.thickness = 0.07
cylm(X, Y, 1, 0.0, 0.06, M['porcelain'], PBA, 'Tub Floor', 48, rx=0.80, ry=0.36)
cylm(X, Y, 1, 0.40, 0.41, M['glass_black'], PBA, 'Tub Water', 48, rx=0.77, ry=0.33)
add_obst(4.2, 28.6, 0.88 / F, 0.44 / F, 0, 'Tub')
cyl(7.25, 29.3, 0.02, 0, 0.98, M['bronze'], PBA, 'Tub Filler', 10)
box(6.8, 29.25, 7.25, 29.35, 0.95, 0.98, M['bronze'], PBA, 'Tub Filler Spout')
X, Y = W(4.2, 28.6)
cylm(X, Y, 0.004, 1.9, CEIL, M['bronze'], PBA, 'Tub Pendant Cord', 6)
sphere(X, Y, 1.85, 0.16, M['alabaster'], PBA, 'Tub Pendant')
add_point('Tub Pendant Light', X, Y, 1.85, 20, radius=0.16)
box(2.3, 28.0, 2.9, 29.2, 0.58, 0.60, M['walnut'], PBA, 'Bath Caddy')
X, Y = W(7.6, 27.2)
cylm(X, Y, 0.17, 0.0, 0.45, M['walnut'], PBA, 'Bath Stool', 24)
box(7.3, 26.95, 7.9, 27.45, 0.45, 0.53, M['towel'], PBA, 'Rolled Towel', 0.03)
add_obst(7.6, 27.2, 0.6, 0.6, 0, 'Bath Stool')
olive_tree(1.6, 25.0, PBA, 1.6, 'Bath Olive')
frame_art(0.75, 28.6, 'E', 0.9, 0.6, 1.6, M['art1'], PBA, 'Bath Art', light=False)
box(0.62, 30.6, 7.3, 34.6, 0, 0.01, M['nero'], PBA, 'WC Floor')
marble_walls([(0.62, 33.9, 7.2, 34.0)], PBA, name='WC Nero Wall')
toilet(1.6, 32.3, 'E', PBA, 'Primary Toilet')
box(12.3, 30.6, 14.0, 34.6, 0.0, 2.3, M['navy'], PBA, 'Linen Cabinet', 0.004, obst=True)
box(12.28, 30.7, 12.3, 34.5, 1.0, 1.02, M['bronze'], PBA, 'Linen Pull')

# ---------------- Primary closet ------------------------------------------------------
closet_system(5.1, 35.1, 13.9, 45.7, 'Primary Closet', 'Primary Closet')
box(7.8, 39.0, 11.2, 42.0, 0, 0.88, M['navy'], 'Primary Closet', 'Closet Island', 0.004)
box(7.75, 38.95, 11.25, 42.05, 0.88, 0.92, M['marble'], 'Primary Closet', 'Closet Island Top', 0.003)
X, Y = W(9.5, 40.5)
torus(X, Y, 2.2, 0.35, 0.02, M['bronze'], 'Primary Closet', 'Closet Ring Light')
torus(X, Y, 2.18, 0.35, 0.008, M['led'], 'Primary Closet', 'Closet Ring LED')
lamp(8.4, 40.0, 0.92, 'Primary Closet', 0.3, 0.1, 'Closet Lamp', 10)

# ---------------- Bedroom 2 ----------------------------------------------------------
B2 = 'Bedroom 2'
rug(51.0, 6.0, 57.8, 13.4, M['rug'], B2, 'Bedroom 2 Rug')
channel_headboard(58.95, 5.0, 59.25, 14.2, 0.0, 1.35, M['charcoal'], B2)
bed(56.15, 9.6, 'W', 1.6, 2.05, B2, 'Bedroom 2 Queen Bed', throw=M['olive'], panel=M['charcoal'])
floating_nightstand(58.45, 5.9, 'W', B2, 'Bedroom 2 Nightstand L')
floating_nightstand(58.45, 13.3, 'W', B2, 'Bedroom 2 Nightstand R')
dresser(47.35, 9.6, 'E', 1.7, B2, 'Bedroom 2 Dresser')
frame_art(46.5, 9.6, 'E', 1.2, 0.9, 1.6, M['art2'], B2, 'Bedroom 2 Art')
vessel(47.3, 8.3, 0.83, 0.08, 0.26, M['ceramic2'], B2, 'Dresser Vase')
lounge_chair(48.4, 3.6, 135, M['olive'], 'Bedroom 2 Lounge Chair', B2, M['black'])
plant(54.6, 2.4, B2, 1.3, 0.2, 'Bedroom 2 Plant')
curtain(47.1, 48.6, 1.85, 0.0, CEIL - 0.03, M['sheer'], B2, 'Bedroom 2 Sheers')
curtain(54.3, 55.8, 1.85, 0.0, CEIL - 0.03, M['sheer'], B2, 'Bedroom 2 Sheers')

# ---------------- Bath 2, hall bath, closets, laundry, mech, entry --------------------------
B2A = 'Bath 2'
marble_walls([(53.0, 16.62, 59.28, 16.72), (59.18, 16.62, 59.28, 20.0)], B2A)
shower(53.0, 16.72, 59.18, 20.0, [(53.0, 19.9, 58.0, 20.0)], B2A, 'Bath 2 Shower', head=(56.0, 17.6))
box(50.88, 16.62, 52.7, 18.24, 0.0, 2.3, M['navy'], B2A, 'Linen Tower', 0.004)
vanity(57.6, 20.5, 59.28, 23.7, B2A, [(58.4, 22.1)], 'E', 'Bath 2 Vanity')
backlit_mirror(59.25, 21.0, 23.2, 1.05, 1.95, B2A, 'E')
box(57.8, 23.0, 58.6, 23.6, 0.86, 0.95, M['towel'], B2A, 'Towels', 0.02)
toilet(58.5, 26.3, 'W', B2A, 'Bath 2 Toilet')
closet_system(51.3, 28.5, 59.0, 37.8, 'Closet 2', 'Closet 2')
HB = 'Hall Bath'
marble_walls([(29.4, 35.6, 35.2, 35.7)], HB)
shower(29.4, 35.7, 35.2, 38.6, [(29.4, 38.5, 34.0, 38.6)], HB, 'Hall Shower', head=(32.0, 36.6))
vanity(28.0, 43.6, 31.3, 45.2, HB, [(29.6, 44.5)], 'S', 'Hall Vanity')
box(28.4, 45.17, 30.8, 45.2, 1.05, 1.9, M['mirror'], HB, 'Mirror')
toilet(33.3, 44.4, 'N', HB, 'Hall Toilet')
LA = 'Laundry'
for xx in (46.0, 48.4):
    box(xx, 43.5, xx + 2.25, 45.6, 0.0, 0.95, M['porcelain'], LA, 'Washer/Dryer', 0.02)
    box(xx + 0.6, 43.45, xx + 1.65, 43.5, 0.25, 0.75, M['glass_black'], LA, 'Washer Door')
box(50.9, 43.6, 54.6, 45.6, 0.1, 0.86, M['navy'], LA, 'Laundry Cabinet', 0.004)
box(46.0, 43.4, 54.6, 45.6, 0.95, 0.99, M['marble'], LA, 'Laundry Counter', 0.003)
box(46.0, 44.6, 54.6, 45.6, 1.45, 2.2, M['navy'], LA, 'Laundry Uppers', 0.004)
cyl(57.4, 41.0, 0.28, 0.0, 1.5, M['porcelain'], 'Mech', 'Water Heater', 24)
box(43.2, 38.9, 44.9, 45.5, 1.7, 1.72, M['walnut'], 'Entry', 'Coat Closet Shelf')
EN = 'Entry'
box(41.6, 38.6, 42.62, 40.3, 0.78, 0.83, M['nero'], EN, 'Entry Console Top', 0.003)
for yy in (38.75, 40.15):
    box(41.7, yy - 0.06, 42.55, yy + 0.06, 0.0, 0.78, M['bronze'], EN, 'Console Leg')
add_obst(42.1, 39.45, 0.55, 0.9, 0, 'Entry Console')
vessel(42.1, 38.95, 0.83, 0.10, 0.36, M['ceramic'], EN, 'Entry Vase')
for i in range(6):
    sphere(*W(42.1 + random.uniform(-0.25, 0.25), 38.95 + random.uniform(-0.25, 0.25)), 1.35 + random.uniform(0, 0.35),
           0.05, M['olive_leaf'], EN, 'Entry Branches', sx=1.6, sy=0.4, sz=0.4, seg=8)
lamp(42.1, 39.9, 0.83, EN, 0.32, 0.12, 'Entry Lamp', 12)
frame_art(42.62, 39.45, 'W', 1.0, 1.25, 1.6, M['art1'], EN, 'Entry Art')
X, Y = W(37.9, 40.5)
cylm(X, Y, 0.004, 2.4, CEIL, M['bronze'], EN, 'Entry Pendant Cord', 6)
sphere(X, Y, 2.3, 0.15, M['alabaster'], EN, 'Entry Pendant')
add_point('Entry Pendant Light', X, Y, 2.0, 25, radius=0.2)

# ---------------- Balcony -------------------------------------------------------
BA = 'Balcony'
armchair(16.4, 3.2, 'E', M['outdoor'], 'Balcony Lounge Chair', BA)
armchair(16.4, 7.4, 'E', M['outdoor'], 'Balcony Lounge Chair', BA)
# gas fire table (lit from golden hour on)
box(19.0, 3.6, 21.4, 7.1, 0.0, 0.40, M['nero'], BA, 'Fire Table', 0.01, obst=True)
box(19.4, 4.4, 21.0, 6.3, 0.40, 0.41, M['fire_glass'], BA, 'Fire Table Glass')
for i in range(4):
    X, Y = W(20.2 + random.uniform(-0.2, 0.2), 4.8 + i * 0.45)
    geo.flame_sheet(X, Y, 0.41, 0.3, random.uniform(0.25, 0.35), False, M['fire_table'], BA, 'Fire Table Flames')
_ft = add_point('Fire Table Glow', *W(20.2, 5.35), 0.7, 60, (1.0, 0.5, 0.2), 0.3, group='firetable')
g = Group('Balcony Sofa', 23.0, 6.0, 'W', BA, 1.07, 0.47)
g.box(-1.05, -0.45, 0.06, 1.05, 0.45, 0.40, M['outdoor'], 0.05)
g.box(-1.05, -0.45, 0.40, 1.05, -0.24, 0.76, M['outdoor'], 0.06)
g.box(-1.05, -0.45, 0.0, 1.05, 0.45, 0.06, M['black'], 0.003)
g.box(-1.05, -0.45, 0.40, -0.92, 0.45, 0.58, M['outdoor'], 0.04)
g.box(0.92, -0.45, 0.40, 1.05, 0.45, 0.58, M['outdoor'], 0.04)
g.box(-0.6, -0.24, 0.46, -0.2, -0.1, 0.8, M['rust'], 0.06)
g.box(0.3, -0.24, 0.46, 0.7, -0.1, 0.8, M['charcoal'], 0.06)
box(32.6, 4.2, 38.0, 7.2, 0.72, 0.76, M['teak'], BA, 'Balcony Dining Table', 0.006)
for (lx, ly) in [(32.9, 4.5), (37.7, 4.5), (32.9, 6.9), (37.7, 6.9)]:
    cyl(lx, ly, 0.03, 0, 0.72, M['black'], BA, 'Leg', 8)
add_obst(35.3, 5.7, 2.7, 1.5, 0, 'Balcony Table')
for xx in (34.0, 36.6):
    chair(xx, 3.35, 'S', M['outdoor'], 'Balcony Chair', BA, M['black'])
    chair(xx, 8.05, 'N', M['outdoor'], 'Balcony Chair', BA, M['black'])
chair(31.8, 5.7, 'E', M['outdoor'], 'Balcony Chair', BA, M['black'])
chair(38.8, 5.7, 'W', M['outdoor'], 'Balcony Chair', BA, M['black'])
box(42.6, 2.2, 44.9, 9.4, 0.0, 0.92, M['navy'], BA, 'Outdoor Kitchen', 0.006, obst=True)
box(42.5, 2.1, 44.95, 9.5, 0.92, 0.97, M['nero'], BA, 'Outdoor Counter', 0.003)
box(43.4, 4.2, 44.6, 6.6, 0.97, 1.0, M['steel'], BA, 'Built-in Grill')
for (x0, x1) in ((15.4, 18.6), (38.6, 42.0)):                     # long planters of seasonal grasses
    box(x0, 0.7, x1, 2.0, 0.0, 0.55, M['concrete'], BA, 'Planter', 0.01)
    add_obst((x0 + x1) / 2, 1.35, (x1 - x0) / 2, 0.65, 0, 'Planter')
    if 'Grass Clump' not in bpy.data.meshes:
        gv, gf = [], []
        for bl in range(26):                      # one clump = 26 arching blades
            a = random.uniform(0, 2 * math.pi); lean = random.uniform(0.05, 0.25); hh = random.uniform(0.35, 0.6)
            bx, by = math.cos(a) * 0.03, math.sin(a) * 0.03
            tx, ty = bx + math.cos(a) * lean, by + math.sin(a) * lean
            px, py = -math.sin(a) * 0.006, math.cos(a) * 0.006
            k0 = len(gv)
            gv += [(bx - px, by - py, 0), (bx + px, by + py, 0), ((bx + tx) / 2 + px * 0.6, (by + ty) / 2 + py * 0.6, hh * 0.65),
                   ((bx + tx) / 2 - px * 0.6, (by + ty) / 2 - py * 0.6, hh * 0.65), (tx, ty, hh)]
            gf += [(k0, k0 + 1, k0 + 2, k0 + 3), (k0 + 3, k0 + 2, k0 + 4)]
        gme = bpy.data.meshes.new('Grass Clump'); gme.from_pydata(gv, [], gf); gme.update(); gme.materials.append(M['planting'])
    gme = bpy.data.meshes['Grass Clump']
    for i in range(22):
        o = bpy.data.objects.new('Grass Clump', gme)
        X, Y = W(random.uniform(x0 + 0.3, x1 - 0.3), random.uniform(0.95, 1.75))
        o.location = (X, Y, 0.53); o.rotation_euler = (0, 0, random.uniform(0, 6.3)); s = random.uniform(0.8, 1.3)
        o.scale = (s, s, s)
        link(o, BA)
for x in (17.0, 23.0, 29.0, 35.0, 41.0):
    downlight(x, 5.5, 22)

# ---------------- ceiling lighting -------------------------------------------------
for (x, y) in [(20, 14), (25, 14), (19.5, 22), (19.5, 28), (24.5, 25), (30, 22), (30, 28), (33, 32.5),
               (41.6, 21), (41.6, 25), (41.6, 29), (37.6, 37), (37.6, 43), (44, 36), (48.5, 20), (48.5, 25),
               (48.5, 31), (6, 4), (10, 4), (6, 16.5), (11, 14.5), (21, 38), (24, 42), (9.6, 21), (9.6, 26),
               (4, 24.5), (52, 6), (52, 12.5), (55, 22), (31.5, 41), (9.5, 37.5), (9.5, 43.5), (55, 31), (55, 35),
               (50, 41), (3.5, 32.3)]:
    downlight(x, y)
area('Living Fill', 17.5, 13, 29, 32, 70)
area('Kitchen Fill', 33, 19, 45, 32, 60)
area('Dining Fill', 30, 12.5, 40, 18, 30)
area('Entry Fill', 35.8, 34.5, 45.5, 44.5, 45)
area('Hall Fill', 46.5, 16.6, 50.4, 38, 30)
area('Den Fill', 16.8, 35.6, 27.4, 45.6, 45)
area('Primary Bedroom Fill', 0.8, 1.6, 13.8, 17.8, 60)
area('Primary Bath Fill', 0.8, 18.6, 13.8, 34.4, 60)
area('Bedroom 2 Fill', 46.6, 1.6, 59.2, 16.0, 55)
area('Bath 2 Fill', 51, 16.7, 59.2, 27.8, 35)
area('Laundry Fill', 45.7, 38.8, 59.2, 45.6, 30)
area('Closet Fill', 5.1, 35.1, 13.9, 45.7, 35)
area('Closet 2 Fill', 51.2, 28.4, 59.1, 37.9, 25)
area('Hall Bath Fill', 27.9, 35.6, 35.2, 45.4, 25)

# ---------------- sky, sun and the Omaha surroundings -----------------------------------
env.build_world(scene)
env.build_exterior()
env.set_season(VIDEO_SEASON)

# ============================================================================
# CAMERA PATH
# ============================================================================
# waypoint: (x_ft, y_ft, speed factor, look target (x_ft, y_ft) or None)
WAYPOINTS = [
    (37.6, 44.3, 0.55, (37.6, 30.0)),   # front door, looking up the entry hall
    (37.6, 40.0, 0.95, None),
    (37.5, 35.4, 0.90, (28.0, 30.0)),
    (34.4, 33.6, 0.80, (22.0, 31.5)),   # passing the den
    (30.5, 33.4, 0.65, (21.0, 33.5)),
    (26.4, 33.5, 0.50, (23.5, 40.5)),   # step into the den doorway
    (23.6, 35.5, 0.35, (22.5, 42.0)),
    (23.8, 36.6, 0.28, (20.0, 40.0)),
    (24.7, 35.1, 0.35, (28.0, 31.0)),
    (27.0, 32.6, 0.50, (30.0, 28.0)),
    (30.8, 30.6, 0.60, (38.0, 27.0)),
    (34.0, 29.9, 0.95, (41.6, 27.0)),
    (38.4, 30.0, 1.00, None),
    (41.6, 28.2, 0.90, (41.6, 18.0)),   # kitchen aisle
    (41.65, 24.6, 0.75, (44.0, 22.0)),
    (41.6, 21.2, 0.90, None),
    (40.0, 19.5, 0.95, (30.0, 22.0)),   # dining / living
    (34.5, 19.6, 0.80, (21.0, 26.5)),
    (30.8, 19.0, 0.85, (24.0, 22.0)),
    (28.1, 15.6, 0.90, (28.2, 5.0)),
    (28.2, 11.5, 0.95, None),           # through the open slider
    (28.4, 6.6, 0.75, (28.4, -20.0)),   # balcony, looking at the view
    (27.9, 3.4, 0.50, (16.0, 4.0)),
    (26.1, 3.8, 0.50, (16.0, 6.0)),
    (25.9, 7.2, 0.70, (40.0, 8.0)),
    (26.2, 11.5, 1.00, (22.0, 16.0)),   # back inside
    (22.0, 15.6, 1.05, (14.0, 16.2)),
    (16.2, 16.2, 1.00, None),
    (14.36, 16.25, 0.85, None),         # primary bedroom door
    (11.6, 16.2, 0.70, (4.5, 10.0)),    # bedroom, looking at the bed
    (9.9, 17.1, 0.80, (9.6, 26.0)),
    (9.4, 18.4, 0.85, None),            # primary bath door
    (9.0, 21.0, 0.80, (4.2, 27.0)),
    (8.9, 24.0, 0.60, (4.0, 29.0)),     # freestanding tub
    (9.6, 26.2, 0.38, (2.5, 22.0)),     # shower & olive tree
    (10.5, 24.0, 0.45, (13.0, 26.5)),   # vanity, at an angle
    (9.8, 21.6, 0.75, (9.6, 16.0)),
    (9.7, 18.4, 0.95, None),
    (10.6, 17.0, 0.95, (30.0, 16.5)),   # look back out toward the great room
    (12.5, 15.9, 1.00, (30.0, 16.5)),
    (14.36, 16.25, 1.05, None),
    (18.5, 16.7, 1.10, None),
    (25.0, 16.8, 1.10, None),
    (29.1, 17.4, 1.05, None),
    (31.4, 20.4, 1.05, None),
    (32.0, 29.5, 1.10, (40.0, 36.0)),
    (36.0, 32.6, 1.15, (47.0, 36.5)),
    (40.5, 35.9, 1.20, (49.0, 35.0)),
    (45.0, 36.2, 1.15, (49.5, 30.0)),
    (48.5, 34.0, 1.00, (48.5, 16.0)),   # bedroom hallway
    (48.4, 28.1, 1.00, None),
    (48.45, 21.0, 1.00, None),
    (48.5, 16.4, 0.85, None),           # bedroom 2
    (50.2, 13.0, 0.70, (56.0, 9.6)),
    (51.0, 10.6, 0.40, (54.5, 4.0)),
]
EYE = 1.60
NFR = FPS * DURATION

def catmull(pts, n_per=60, alpha=0.5):
    """centripetal Catmull-Rom through pts (list of (x,y)); returns dense list."""
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = [Vector((*P[j], 0)) for j in (i - 1, i, i + 1, i + 2)]
        def tj(ti, a, b):
            d = (b - a).length
            return ti + max(d, 1e-4) ** alpha
        t0 = 0; t1 = tj(t0, p0, p1); t2 = tj(t1, p1, p2); t3 = tj(t2, p2, p3)
        for k in range(n_per):
            t = t1 + (t2 - t1) * k / n_per
            A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
            B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
            C = (t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2
            out.append((C.x, C.y, i - 1 + k / n_per))
    out.append((*pts[-1], len(pts) - 1))
    return out

pts = [(w[0], w[1]) for w in WAYPOINTS]
dense = catmull(pts, 80)
# arc length
s = [0.0]
for a, b in zip(dense, dense[1:]):
    s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
total_ft = s[-1]

def interp_wp(u, idx):
    i = min(int(u), len(WAYPOINTS) - 2); f = u - i
    f = f * f * (3 - 2 * f)
    return WAYPOINTS[i][idx] * (1 - f) + WAYPOINTS[i + 1][idx] * f

# speed profile -> time
spd = [interp_wp(d[2], 2) for d in dense]
# smooth speed
k = 40
spd = [sum(spd[max(0, i - k):i + k + 1]) / len(spd[max(0, i - k):i + k + 1]) for i in range(len(spd))]
ramp_ft = 4.0
for i in range(len(spd)):
    r = min(1.0, (s[i] + 0.6) / ramp_ft, (total_ft - s[i] + 0.6) / ramp_ft)
    spd[i] *= max(0.15, math.sin(min(1.0, r) * math.pi / 2))
tt = [0.0]
for i in range(1, len(dense)):
    tt.append(tt[-1] + (s[i] - s[i - 1]) / max(1e-3, (spd[i] + spd[i - 1]) / 2))
scale_t = DURATION / tt[-1]
tt = [t * scale_t for t in tt]

# desired yaw per dense point: tangent look-ahead, blended with look targets
def tangent_yaw(i, ahead_ft=5.0):
    j = i
    while j < len(dense) - 1 and s[j] - s[i] < ahead_ft:
        j += 1
    if j == i:
        j = i; i = max(0, i - 5)
    dx = dense[j][0] - dense[i][0]; dy = dense[j][1] - dense[i][1]
    # plan y down -> world Y = -y
    return math.atan2(-dy, dx)

def target_yaw(px, py, tx, ty):
    return math.atan2(-(ty - py), tx - px)

def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi

yaws = []
for i, (x, y, u) in enumerate(dense):
    ty_tan = tangent_yaw(i)
    ia = min(int(u), len(WAYPOINTS) - 2); f = u - ia
    def wyaw(w):
        if WAYPOINTS[w][3] is None:
            return None
        return target_yaw(x, y, *WAYPOINTS[w][3])
    ya, yb = wyaw(ia), wyaw(ia + 1)
    fa = 1 - f * f * (3 - 2 * f); fb = 1 - fa
    vec = [math.cos(ty_tan) * 0.35, math.sin(ty_tan) * 0.35]
    for (yy, ww) in ((ya, fa), (yb, fb)):
        if yy is None:
            vec[0] += math.cos(ty_tan) * ww; vec[1] += math.sin(ty_tan) * ww
        else:
            vec[0] += math.cos(yy) * ww; vec[1] += math.sin(yy) * ww
    yaws.append(math.atan2(vec[1], vec[0]))

# per frame sampling
def sample_at_time(t):
    lo, hi = 0, len(tt) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if tt[m] <= t: lo = m
        else: hi = m
    f = 0 if tt[hi] == tt[lo] else (t - tt[lo]) / (tt[hi] - tt[lo])
    x = dense[lo][0] + (dense[hi][0] - dense[lo][0]) * f
    y = dense[lo][1] + (dense[hi][1] - dense[lo][1]) * f
    ya = yaws[lo] + wrap(yaws[hi] - yaws[lo]) * f
    return x, y, ya

frames = []
for fr in range(NFR):
    t = fr / FPS * (DURATION / (DURATION - 1.0 / FPS)) if fr else 0.0
    t = min(t, DURATION)
    frames.append(sample_at_time(t))
# unwrap + gaussian smooth yaw (sigma ~0.35 s)
uw = [frames[0][2]]
for fr in frames[1:]:
    uw.append(uw[-1] + wrap(fr[2] - uw[-1]))
sig = 0.8 * FPS
ker = [math.exp(-0.5 * (k / sig) ** 2) for k in range(-int(3 * sig), int(3 * sig) + 1)]
sm = []
for i in range(len(uw)):
    acc = 0; wsum = 0
    for j, kk in enumerate(ker):
        ii = min(max(i + j - len(ker) // 2, 0), len(uw) - 1)
        acc += uw[ii] * kk; wsum += kk
    sm.append(acc / wsum)
frames = [(f[0], f[1], sm[i]) for i, f in enumerate(frames)]

cam_d = bpy.data.cameras.new('Walkthrough Camera')
cam_d.lens = 20; cam_d.sensor_width = 36; cam_d.clip_start = 0.05; cam_d.clip_end = 400
cam = bpy.data.objects.new('Walkthrough Camera', cam_d)
link(cam, 'Camera')
scene.camera = cam
PITCH = math.radians(-3.5)
for i, (x, y, ya) in enumerate(frames):
    X, Y = W(x, y)
    bob = 0.012 * math.sin(i / FPS * 2 * math.pi * 0.9)   # subtle walking bob
    cam.location = (X, Y, EYE + bob)
    # camera looks down -Z; rotate so it looks along yaw (world XY angle)
    cam.rotation_euler = (math.pi / 2 + PITCH, 0, ya - math.pi / 2)
    cam.keyframe_insert('location', frame=i + 1)
    cam.keyframe_insert('rotation_euler', frame=i + 1)

# visible path curve (hidden in render) for editing
cu = bpy.data.curves.new('Camera Route', 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('POLY'); sp.points.add(len(frames) - 1)
for i, (x, y, ya) in enumerate(frames):
    X, Y = W(x, y); sp.points[i].co = (X, Y, 0.05, 1)
route = bpy.data.objects.new('Camera Route', cu); link(route, 'Camera')
route.hide_render = True

scene.frame_start = 1; scene.frame_end = NFR
scene.render.fps = FPS
scene.render.resolution_x = 1920; scene.render.resolution_y = 1080

# ----------------------------------------------------------------------------
# clearance report
# ----------------------------------------------------------------------------
def dist_rect(px, py, cx, cy, hx, hy, rot):
    dx, dy = px - cx, py - cy
    if rot:
        # obstacle local axes are rotated by a world-space yaw; plan y is flipped vs world Y
        wx, wy = dx, -dy
        c, s_ = math.cos(rot), math.sin(rot)
        dx, dy = c * wx + s_ * wy, -s_ * wx + c * wy
    ex = max(abs(dx) - hx, 0); ey = max(abs(dy) - hy, 0)
    return math.hypot(ex, ey)

obstacles = [((a + c) / 2, (b + d) / 2, (c - a) / 2, (d - b) / 2, 0, 'wall') for (a, b, c, d) in WALLS] + OBST
worst = (1e9, None, None)
clear = []
for i, (x, y, _) in enumerate(frames):
    best = (1e9, None)
    for (cx, cy, hx, hy, rot, tag) in obstacles:
        d = dist_rect(x, y, cx, cy, hx, hy, rot)
        if d < best[0]:
            best = (d, tag)
    clear.append(best)
    if best[0] < worst[0]:
        worst = (best[0], best[1], i + 1)
speeds = [math.hypot(frames[i + 1][0] - frames[i][0], frames[i + 1][1] - frames[i][1]) * F * FPS for i in range(NFR - 1)]
yawrate = [abs(frames[i + 1][2] - frames[i][2]) * FPS * 180 / math.pi for i in range(NFR - 1)]
report = dict(route_length_m=round(total_ft * F, 1), frames=NFR, fps=FPS,
              min_clearance_m=round(worst[0] * F, 3), min_clearance_obstacle=worst[1], min_clearance_frame=worst[2],
              max_speed_mps=round(max(speeds), 2), mean_speed_mps=round(sum(speeds) / len(speeds), 2),
              max_yaw_rate_dps=round(max(yawrate), 1), max_yaw_rate_frame=yawrate.index(max(yawrate)) + 1,
              yaw_over_60dps_frames=sum(1 for y in yawrate if y > 60))
print('CAMERA REPORT', json.dumps(report))
json.dump(dict(report=report, frames=[(round(x, 3), round(y, 3), round(a, 4)) for x, y, a in frames],
               clearance=[(round(c[0] * F, 3), c[1]) for c in clear], obstacles=obstacles, walls=WALLS),
          open(os.path.join(HERE, 'camera_report.json'), 'w'))

# ----------------------------------------------------------------------------
# day cycle for the walkthrough: morning at the door -> golden hour on the balcony -> evening
# ----------------------------------------------------------------------------
bal = [i for i, (x, y, _) in enumerate(frames) if y < 11.0 and 15 < x < 46]
t_bal = (bal[0] + bal[-1]) / 2 / FPS if bal else 19.0
DAY_KEYS = [(0.0, 0.0), (t_bal * 0.55, 1.0), (t_bal, 2.0), (t_bal + 8.0, 2.55), (min(DURATION, t_bal + 17.0), 3.0), (DURATION, 3.0)]
def t_at(sec):
    for (s0, t0), (s1, t1) in zip(DAY_KEYS, DAY_KEYS[1:]):
        if sec <= s1:
            f = 0 if s1 == s0 else (sec - s0) / (s1 - s0)
            return t0 + (t1 - t0) * f
    return DAY_KEYS[-1][1]
for fr in list(range(1, NFR + 1, 6)) + [NFR]:
    env.apply_time(scene, VIDEO_SEASON, t_at((fr - 1) / FPS), frame=fr)
print('DAY CYCLE', VIDEO_SEASON, 'balcony at %.1fs' % t_bal, DAY_KEYS)
scene['video_season'] = VIDEO_SEASON

# ----------------------------------------------------------------------------
# render defaults (Cycles) + save
# ----------------------------------------------------------------------------
scene.render.engine = 'CYCLES'
c = scene.cycles
c.device = 'CPU'; c.samples = 8; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.06
c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
c.max_bounces = 3; c.diffuse_bounces = 2; c.glossy_bounces = 1; c.transmission_bounces = 2
c.transparent_max_bounces = 8; c.sample_clamp_indirect = 3.0
c.caustics_reflective = False; c.caustics_refractive = False
scene.render.use_persistent_data = True
scene.view_settings.view_transform = 'AgX'
looks = [i.identifier for i in scene.view_settings.bl_rna.properties['look'].enum_items_static]
scene.view_settings.look = next((l for l in looks if 'Medium High Contrast' in l), 'None')
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print('saved', OUT)
