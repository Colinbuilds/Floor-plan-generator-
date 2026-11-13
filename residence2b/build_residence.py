"""
Build a furnished Blender model of Residence 2B (The Residences, Levels 2-6)
plus a 45-second eye-level walkthrough camera.

Plan coordinates are in FEET measured on the PDF plan (x to the right, y down,
origin at the plan's top-left), scaled from the labelled room dimensions
(e.g. Balcony 30'-4", Bedroom 12'-10", Primary Bedroom 13'-0").
World coordinates: X = x_ft * 0.3048, Y = -y_ft * 0.3048, Z up (metres).

Run:  python3 build_residence.py  [out.blend]
"""
import bpy, bmesh, json, math, os, random, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[-1] if sys.argv[-1].endswith('.blend') else os.path.join(HERE, 'Residence_2B.blend')
F = 0.3048
CEIL = 2.74          # 9'-0" ceilings
DOOR_H = 2.13        # 7'-0" doors
FPS = 24
DURATION = 45
random.seed(7)

# ----------------------------------------------------------------------------
# scene reset
# ----------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

COLL = {}
def coll(name):
    if name not in COLL:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
        COLL[name] = c
    return COLL[name]

OBST = []   # footprints for camera clearance checks: (cx, cy, hx, hy, rot) in ft
def add_obst(cx, cy, hx, hy, rot=0.0, tag=''):
    OBST.append((cx, cy, hx, hy, rot, tag))

# ----------------------------------------------------------------------------
# materials
# ----------------------------------------------------------------------------
MATS = {}
def principled(name, color, rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    for k, v in kw.items():
        b.inputs[k].default_value = v
    m.diffuse_color = (*color, 1)
    MATS[name] = m
    return m

def tex_coord(nt, scale=(1, 1, 1), space='Object'):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    nt.links.new(tc.outputs[space], mp.inputs['Vector'])
    return mp.outputs['Vector']

def oak_floor():
    m = principled('Oak Floor', (0.55, 0.40, 0.26), 0.38)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    v = tex_coord(nt)
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.offset = 0.37; br.offset_frequency = 1
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Brick Width'].default_value = 1.6
    br.inputs['Row Height'].default_value = 0.19
    br.inputs['Mortar Size'].default_value = 0.0015
    br.inputs['Bias'].default_value = 0.0
    br.inputs['Color1'].default_value = (0.60, 0.44, 0.29, 1)
    br.inputs['Color2'].default_value = (0.50, 0.35, 0.22, 1)
    br.inputs['Mortar'].default_value = (0.20, 0.13, 0.08, 1)
    nt.links.new(v, br.inputs['Vector'])
    # wood grain: noise stretched along the plank (x)
    mp2 = nt.nodes.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (0.6, 25, 1)
    nt.links.new(v, mp2.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 8
    nt.links.new(mp2.outputs['Vector'], nz.inputs['Vector'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 0.35
    nt.links.new(br.outputs['Color'], mix.inputs['A'])
    nt.links.new(nz.outputs['Color'], mix.inputs['B'])
    bc = nt.nodes.new('ShaderNodeBrightContrast'); bc.inputs['Bright'].default_value = 0.08
    nt.links.new(mix.outputs['Result'], bc.inputs['Color'])
    nt.links.new(bc.outputs['Color'], b.inputs['Base Color'])
    return m

def tile(name, c1, c2, size, rough=0.3, grout=(0.55, 0.55, 0.53)):
    m = principled(name, c1, rough)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.offset = 0.5
    br.inputs['Scale'].default_value = 1.0 / size
    br.inputs['Brick Width'].default_value = 1.0
    br.inputs['Row Height'].default_value = 0.5
    br.inputs['Mortar Size'].default_value = 0.004
    br.inputs['Color1'].default_value = (*c1, 1)
    br.inputs['Color2'].default_value = (*c2, 1)
    br.inputs['Mortar'].default_value = (*grout, 1)
    nt.links.new(tex_coord(nt), br.inputs['Vector'])
    nt.links.new(br.outputs['Color'], b.inputs['Base Color'])
    return m

def noisy(name, color, color2, scale=4.0, stretch=(1, 1, 1), rough=0.5, metal=0.0, bump=0.0):
    m = principled(name, color, rough, metal)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 6
    nt.links.new(tex_coord(nt, stretch), nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*color, 1)
    ramp.color_ramp.elements[1].color = (*color2, 1)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    if bump:
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump
        nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

def emissive(name, color, strength):
    m = principled(name, color, 0.5)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (*color, 1)
    b.inputs['Emission Strength'].default_value = strength
    return m

def glass(name, tint=(0.95, 0.97, 0.97)):
    """thin architectural glass: transparent + fresnel reflection (no refraction),
    so both EEVEE and Cycles show the real scene behind it."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = (*tint, 1)
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
    lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.12
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lw.outputs['Fresnel'], mx.inputs['Fac'])
    nt.links.new(tr.outputs['BSDF'], mx.inputs[1]); nt.links.new(gl.outputs['BSDF'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    MATS[name] = m
    m.diffuse_color = (*tint, 0.25)
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    m.use_backface_culling = False
    return m

def art(name, c1, c2, c3, scale=1.5):
    m = principled(name, c1, 0.8)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    w = nt.nodes.new('ShaderNodeTexWave'); w.inputs['Scale'].default_value = scale
    w.inputs['Distortion'].default_value = 6; w.inputs['Detail'].default_value = 2
    nt.links.new(tex_coord(nt, space='Generated'), w.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); cr = ramp.color_ramp
    cr.elements[0].color = (*c1, 1); cr.elements[1].color = (*c3, 1)
    e = cr.elements.new(0.5); e.color = (*c2, 1)
    cr.interpolation = 'CONSTANT'
    nt.links.new(w.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    return m

# palette: warm modern - light oak, warm white, deep navy (brand colour), copper/brass, cognac
M = dict(
    floor=oak_floor(),
    wall=principled('Wall Paint Warm White', (0.80, 0.78, 0.74), 0.85),
    ceiling=principled('Ceiling White', (0.85, 0.85, 0.84), 0.9),
    trim=principled('Trim White', (0.86, 0.86, 0.84), 0.4),
    tile=tile('Porcelain Tile 24x48', (0.70, 0.69, 0.66), (0.66, 0.65, 0.62), 0.61),
    shower_tile=tile('Shower Tile', (0.82, 0.82, 0.80), (0.78, 0.78, 0.76), 0.2, 0.15),
    balcony=tile('Balcony Pavers', (0.50, 0.48, 0.45), (0.46, 0.44, 0.41), 0.61, 0.7, (0.3, 0.3, 0.3)),
    navy=principled('Cabinet Navy', (0.030, 0.045, 0.065), 0.45),
    walnut=noisy('Walnut', (0.16, 0.08, 0.04), (0.28, 0.15, 0.08), 6, (1, 18, 1), 0.45),
    oak=noisy('White Oak', (0.50, 0.37, 0.24), (0.62, 0.48, 0.33), 6, (1, 18, 1), 0.5),
    quartz=noisy('White Quartz', (0.86, 0.86, 0.84), (0.72, 0.72, 0.71), 3, (1, 1, 1), 0.12),
    steel=principled('Stainless', (0.75, 0.75, 0.74), 0.25, 1.0),
    black=principled('Matte Black Metal', (0.02, 0.02, 0.02), 0.45, 0.6),
    brass=principled('Brushed Brass', (0.80, 0.58, 0.32), 0.25, 1.0),
    copper=principled('Copper', (0.75, 0.40, 0.25), 0.3, 1.0),
    glass_black=principled('Black Glass', (0.01, 0.01, 0.01), 0.05),
    boucle=noisy('Boucle Off-White', (0.70, 0.66, 0.60), (0.78, 0.75, 0.69), 120, (1, 1, 1), 1.0, bump=0.3),
    linen=noisy('Linen White', (0.82, 0.80, 0.76), (0.76, 0.74, 0.70), 60, (1, 1, 1), 0.95, bump=0.1),
    rust=principled('Terracotta Textile', (0.45, 0.16, 0.08), 0.9),
    sage=principled('Sage Textile', (0.30, 0.35, 0.26), 0.9),
    cognac=principled('Cognac Leather', (0.36, 0.14, 0.05), 0.45),
    charcoal=principled('Charcoal Fabric', (0.07, 0.07, 0.075), 0.9),
    rug=noisy('Wool Rug Oatmeal', (0.55, 0.50, 0.43), (0.62, 0.57, 0.50), 90, (1, 1, 1), 1.0, bump=0.4),
    rug2=noisy('Wool Rug Rust', (0.32, 0.14, 0.08), (0.42, 0.22, 0.12), 60, (1, 1, 1), 1.0, bump=0.4),
    stone=noisy('Fireplace Stone', (0.12, 0.12, 0.12), (0.22, 0.21, 0.20), 9, (1, 1, 1), 0.8, bump=0.5),
    porcelain=principled('Porcelain White', (0.88, 0.88, 0.87), 0.08),
    mirror=principled('Mirror', (0.9, 0.9, 0.9), 0.02, 1.0),
    glass=glass('Clear Glass'),
    shower_glass=glass('Shower Glass', (0.92, 0.96, 0.96)),
    frame=principled('Window Frame Black', (0.025, 0.025, 0.028), 0.5, 0.3),
    plant=noisy('Leaf Green', (0.05, 0.14, 0.04), (0.10, 0.22, 0.07), 8, (1, 1, 1), 0.6),
    pot=principled('Terracotta Pot', (0.48, 0.22, 0.12), 0.85),
    soil=principled('Soil', (0.05, 0.035, 0.02), 1.0),
    log=noisy('Firewood', (0.13, 0.07, 0.035), (0.30, 0.19, 0.10), 14, (1, 1, 1), 0.9, bump=0.4),
    flame=emissive('Fire', (1.0, 0.38, 0.08), 6.0),
    lampshade=emissive('Lamp Shade Glow', (1.0, 0.86, 0.68), 4.0),
    bulb=emissive('Warm Bulb', (1.0, 0.80, 0.55), 30.0),
    screen=principled('TV Screen', (0.005, 0.005, 0.006), 0.08),
    ground=noisy('Ground Grass', (0.09, 0.14, 0.05), (0.14, 0.18, 0.08), 0.05, (1, 1, 1), 1.0),
    road=principled('Asphalt', (0.06, 0.06, 0.06), 0.9),
    facade=noisy('Neighbour Facade', (0.45, 0.42, 0.38), (0.55, 0.52, 0.47), 0.4, (1, 1, 1), 0.9),
    facade2=noisy('Neighbour Brick', (0.36, 0.18, 0.11), (0.45, 0.25, 0.15), 0.4, (1, 1, 1), 0.9),
    concrete=principled('Concrete Soffit', (0.55, 0.54, 0.52), 0.9),
    art1=art('Art Abstract Copper', (0.80, 0.74, 0.64), (0.62, 0.30, 0.14), (0.10, 0.13, 0.17)),
    art2=art('Art Abstract Sage', (0.86, 0.83, 0.76), (0.40, 0.46, 0.36), (0.75, 0.55, 0.35), 0.8),
    art3=art('Art Abstract Navy', (0.88, 0.86, 0.80), (0.08, 0.12, 0.18), (0.70, 0.45, 0.30), 2.5),
)
BOOK_MATS = [principled(f'Book {i}', c, 0.8) for i, c in enumerate(
    [(0.5, 0.15, 0.08), (0.1, 0.15, 0.25), (0.7, 0.65, 0.55), (0.2, 0.3, 0.2), (0.6, 0.45, 0.2), (0.1, 0.1, 0.1)])]

# ----------------------------------------------------------------------------
# geometry helpers
# ----------------------------------------------------------------------------
def W(x, y):
    """plan feet -> world metres (XY)."""
    return x * F, -y * F

def link(obj, cname):
    coll(cname).objects.link(obj)
    return obj

def mesh_obj(name, verts, faces, mat, cname, bevel=0.0, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    link(ob, cname)
    if bevel > 0:
        md = ob.modifiers.new('Bevel', 'BEVEL')
        md.width = bevel; md.segments = 2; md.limit_method = 'ANGLE'
    return ob

def cube_data(x0, y0, z0, x1, y1, z1):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f

def boxm(x0, y0, z0, x1, y1, z1, mat, cname, name='Box', bevel=0.0):
    """box in world metres"""
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    v, f = cube_data(x0, y0, z0, x1, y1, z1)
    return mesh_obj(name, v, f, mat, cname, bevel)

def box(x0, y0, x1, y1, z0, z1, mat, cname, name='Box', bevel=0.0, obst=False, tag=''):
    """box in plan feet (xy) and metres (z)"""
    X0, Y0 = W(x0, y0); X1, Y1 = W(x1, y1)
    if obst:
        add_obst((x0 + x1) / 2, (y0 + y1) / 2, abs(x1 - x0) / 2, abs(y1 - y0) / 2, 0, tag or name)
    return boxm(X0, Y0, z0, X1, Y1, z1, mat, cname, name, bevel)

def cyl_data(r, z0, z1, n=24, rx=None, ry=None, cap=True):
    rx = rx or r; ry = ry or r
    v = []
    for z in (z0, z1):
        for i in range(n):
            a = 2 * math.pi * i / n
            v.append((rx * math.cos(a), ry * math.sin(a), z))
    f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    if cap:
        f.append(tuple(reversed(range(n))))
        f.append(tuple(range(n, 2 * n)))
    return v, f

def cylm(cx, cy, r, z0, z1, mat, cname, name='Cyl', n=24, rx=None, ry=None, smooth=True, cap=True):
    v, f = cyl_data(r, z0, z1, n, rx, ry, cap)
    v = [(cx + a, cy + b, c) for a, b, c in v]
    ob = mesh_obj(name, v, f, mat, cname, smooth=smooth)
    return ob

def cyl(x, y, r, z0, z1, mat, cname, name='Cyl', n=24, obst=False, tag='', **kw):
    X, Y = W(x, y)
    if obst:
        add_obst(x, y, r / F, r / F, 0, tag or name)
    return cylm(X, Y, r, z0, z1, mat, cname, name, n, **kw)

def sphere(cx, cy, cz, r, mat, cname, name='Sphere', sx=1, sy=1, sz=1, seg=16):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    me.materials.append(mat)
    ob.location = (cx, cy, cz)
    link(ob, cname)
    return ob

class Group:
    """Furniture built in local metres (+Y = front) placed at plan (x, y) ft, facing a world direction."""
    def __init__(self, name, x, y, facing, cname, hx=None, hy=None, obst=True):
        self.cname = cname
        self.empty = bpy.data.objects.new(name, None)
        self.empty.empty_display_size = 0.3
        X, Y = W(x, y)
        self.empty.location = (X, Y, 0)
        # facing: 'N','S','E','W' or degrees (world yaw of +Y; N=0, W=90, S=180, E=-90)
        ang = {'N': 0, 'W': 90, 'S': 180, 'E': -90}.get(facing, facing)
        self.rot = math.radians(ang)
        self.empty.rotation_euler = (0, 0, self.rot)
        link(self.empty, cname)
        self.name = name
        if obst and hx is not None:
            add_obst(x, y, hx / F, hy / F, self.rot, name)

    def _par(self, ob):
        ob.parent = self.empty
        return ob

    def box(self, x0, y0, z0, x1, y1, z1, mat, bevel=0.01, name=None):
        return self._par(boxm(x0, y0, z0, x1, y1, z1, mat, self.cname, name or self.name, bevel))

    def cyl(self, x, y, r, z0, z1, mat, n=20, name=None, **kw):
        return self._par(cylm(x, y, r, z0, z1, mat, self.cname, name or self.name, n, **kw))

    def sphere(self, x, y, z, r, mat, **kw):
        return self._par(sphere(x, y, z, r, mat, self.cname, self.name, **kw))

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
                M['trim'] if 'Front' not in nm else M['navy'], AR, nm + ' Leaf', 0.004)
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
# furniture helpers
# ----------------------------------------------------------------------------
FU = 'Furniture'

def chair(x, y, facing, mat_seat=None, name='Dining Chair', cn=FU):
    g = Group(name, x, y, facing, cn, 0.25, 0.27)
    ms = mat_seat or M['walnut']
    for sx in (-0.2, 0.2):
        for sy in (-0.2, 0.2):
            g.cyl(sx, sy, 0.015, 0, 0.45, M['black'], 8)
    g.box(-0.24, -0.24, 0.43, 0.24, 0.24, 0.48, ms, 0.015)
    g.box(-0.23, -0.27, 0.48, 0.23, -0.23, 0.86, ms, 0.015)
    return g

def armchair(x, y, facing, mat=None, name='Lounge Chair', cn=FU):
    m = mat or M['cognac']
    g = Group(name, x, y, facing, cn, 0.42, 0.44)
    g.box(-0.40, -0.42, 0.08, 0.40, 0.42, 0.40, m, 0.04)
    g.box(-0.40, -0.42, 0.40, 0.40, -0.24, 0.82, m, 0.05)
    g.box(-0.40, -0.40, 0.40, -0.29, 0.40, 0.62, m, 0.04)
    g.box(0.29, -0.40, 0.40, 0.40, 0.40, 0.62, m, 0.04)
    g.box(-0.29, -0.24, 0.40, 0.29, 0.40, 0.50, m, 0.05)
    for sx in (-0.34, 0.34):
        for sy in (-0.36, 0.36):
            g.cyl(sx, sy, 0.02, 0, 0.09, M['walnut'], 8)
    return g

def lamp(x, y, z_base, cn=FU, h=0.45, r=0.17, name='Table Lamp', light=True):
    X, Y = W(x, y)
    cylm(X, Y, 0.07, z_base, z_base + 0.03, M['brass'], cn, name)
    cylm(X, Y, 0.012, z_base, z_base + h, M['brass'], cn, name, 8)
    cylm(X, Y, r, z_base + h - 0.05, z_base + h + 0.22, M['lampshade'], cn, name + ' Shade', 28, cap=False)
    if light:
        add_point(name + ' Light', X, Y, z_base + h + 0.05, 25, (1.0, 0.78, 0.55), 0.12)

def floor_lamp(x, y, cn=FU, name='Floor Lamp'):
    lamp(x, y, 0, cn, h=1.45, r=0.22, name=name)
    add_obst(x, y, 0.8, 0.8, 0, name)

def plant(x, y, cn=FU, h=1.4, r=0.22, name='Plant'):
    X, Y = W(x, y)
    cylm(X, Y, r, 0, 0.42, M['pot'], cn, name + ' Pot', 24)
    cylm(X, Y, r - 0.02, 0.38, 0.41, M['soil'], cn, name + ' Soil', 24)
    cylm(X, Y, 0.018, 0.4, h * 0.8, M['walnut'], cn, name + ' Stem', 8)
    for i in range(14):
        a = random.uniform(0, 2 * math.pi); rr = random.uniform(0.05, r * 1.7)
        z = random.uniform(0.6, h)
        s = sphere(X + rr * math.cos(a), Y + rr * math.sin(a), z, random.uniform(0.09, 0.15), M['plant'], cn, name + ' Leaf',
                   sx=1.0, sy=0.45, sz=1.4, seg=10)
        s.rotation_euler = (random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), a)
    add_obst(x, y, (r * 1.7) / F, (r * 1.7) / F, 0, name)

def rug(x0, y0, x1, y1, mat, cn=FU, name='Rug'):
    box(x0, y0, x1, y1, 0.0, 0.012, mat, cn, name, 0.004)

def frame_art(x, y, facing, w, h, zc, mat, cn=FU, name='Art'):
    g = Group(name, x, y, facing, cn, obst=False)
    g.box(-w / 2, -0.015, zc - h / 2, w / 2, 0.015, zc + h / 2, M['walnut'], 0.003)
    g.box(-w / 2 + 0.04, 0.012, zc - h / 2 + 0.04, w / 2 - 0.04, 0.02, zc + h / 2 - 0.04, mat, 0)

def bed(x, y, facing, w, l, cn=FU, name='Bed', throw=None):
    g = Group(name, x, y, facing, cn, w / 2 + 0.05, l / 2 + 0.05)
    g.box(-w / 2, -l / 2, 0.08, w / 2, l / 2, 0.35, M['oak'], 0.02)               # frame
    g.box(-w / 2 - 0.05, -l / 2 - 0.06, 0.0, w / 2 + 0.05, -l / 2 + 0.04, 1.25, M['charcoal'], 0.04)  # headboard
    g.box(-w / 2 + 0.03, -l / 2 + 0.06, 0.35, w / 2 - 0.03, l / 2 - 0.03, 0.60, M['linen'], 0.06)   # mattress
    g.box(-w / 2 - 0.02, -l / 2 + 0.6, 0.45, w / 2 + 0.02, l / 2 + 0.01, 0.64, M['linen'], 0.07)    # duvet
    g.box(-w / 2 - 0.03, l / 2 - 0.62, 0.46, w / 2 + 0.03, l / 2 - 0.12, 0.66, throw or M['rust'], 0.05)  # throw
    n = 2 if w < 1.7 else 2
    pw = (w - 0.12) / n
    for i in range(n):
        x0 = -w / 2 + 0.06 + i * pw
        g.box(x0 + 0.02, -l / 2 + 0.08, 0.60, x0 + pw - 0.02, -l / 2 + 0.28, 0.86, M['linen'], 0.08)
        g.box(x0 + 0.12, -l / 2 + 0.30, 0.58, x0 + pw - 0.12, -l / 2 + 0.44, 0.78, M['sage'], 0.06)
    return g

def nightstand(x, y, facing, cn=FU, name='Nightstand', with_lamp=True):
    g = Group(name, x, y, facing, cn, 0.27, 0.22)
    g.box(-0.26, -0.21, 0.0, 0.26, 0.21, 0.58, M['walnut'], 0.01)
    g.box(-0.24, 0.205, 0.30, 0.24, 0.215, 0.55, M['walnut'], 0.004)
    g.box(-0.05, 0.215, 0.42, 0.05, 0.23, 0.43, M['brass'], 0)
    if with_lamp:
        lamp(x, y, 0.58, cn, h=0.40, r=0.14, name=name + ' Lamp')

def dresser(x, y, facing, w, cn=FU, name='Dresser'):
    g = Group(name, x, y, facing, cn, w / 2, 0.26)
    g.box(-w / 2, -0.25, 0.10, w / 2, 0.25, 0.80, M['walnut'], 0.01)
    for sx in (-w / 2 + 0.06, w / 2 - 0.06):
        g.box(sx - 0.02, -0.2, 0, sx + 0.02, 0.2, 0.1, M['black'], 0)
    cols = 3
    cw = (w - 0.06) / cols
    for c in range(cols):
        for r in range(3):
            x0 = -w / 2 + 0.03 + c * cw
            z0 = 0.13 + r * 0.22
            g.box(x0 + 0.005, 0.245, z0, x0 + cw - 0.005, 0.258, z0 + 0.205, M['walnut'], 0.003)
            g.box(x0 + cw / 2 - 0.05, 0.258, z0 + 0.17, x0 + cw / 2 + 0.05, 0.27, z0 + 0.18, M['brass'], 0)
    return g

def sofa_straight(g, x0, x1, y_back, depth, mat):
    """add a straight sofa run inside group g, back at y_back, seat toward +y"""
    g.box(x0, y_back, 0.08, x1, y_back + depth, 0.42, mat, 0.04)
    g.box(x0, y_back, 0.42, x1, y_back + 0.22, 0.80, mat, 0.06)

def toilet(x, y, facing, cn, name='Toilet'):
    g = Group(name, x, y, facing, cn, 0.22, 0.36)
    g.box(-0.20, -0.36, 0.40, 0.20, -0.18, 0.78, M['porcelain'], 0.03)
    g.cyl(0, 0.02, 0.17, 0.0, 0.38, M['porcelain'], 24, ry=0.22, rx=0.17)
    g.cyl(0, 0.04, 0.19, 0.38, 0.42, M['porcelain'], 24, ry=0.25, rx=0.19)

def vanity(x0, y0, x1, y1, cn, sinks, wall_side, name='Vanity'):
    """vanity footprint in plan ft; wall_side: 'E','W','N','S' side touching the wall"""
    box(x0, y0, x1, y1, 0.12, 0.82, M['walnut'], cn, name, 0.008, obst=True, tag=name)
    box(x0 - 0.05, y0 - 0.05, x1 + 0.05, y1 + 0.05, 0.82, 0.86, M['quartz'], cn, name + ' Top', 0.004)
    for (sx, sy) in sinks:
        X, Y = W(sx, sy)
        cylm(X, Y, 0.20, 0.86, 0.98, M['porcelain'], cn, name + ' Basin', 28, rx=0.22, ry=0.17)
        cylm(X, Y, 0.18, 0.95, 0.981, M['steel'], cn, name + ' Basin Water', 28, rx=0.20, ry=0.15)
        off = {'E': (0.28, 0), 'W': (-0.28, 0), 'N': (0, 0.28), 'S': (0, -0.28)}[wall_side]
        cylm(X + off[0], Y + off[1], 0.015, 0.86, 1.15, M['brass'], cn, name + ' Faucet', 10)
        dx = -off[0] * 0.35; dy = -off[1] * 0.35
        boxm(X + off[0] - 0.015 + min(0, dx), Y + off[1] - 0.015 + min(0, dy), 1.12,
             X + off[0] + 0.015 + max(0, dx), Y + off[1] + 0.015 + max(0, dy), 1.15, M['brass'], cn, name + ' Spout')

def shower(x0, y0, x1, y1, glass_edges, cn, name='Shower', head=(None, None)):
    box(x0, y0, x1, y1, 0.0, 0.012, M['shower_tile'], cn, name + ' Floor')
    for (ax, ay, bx, by) in glass_edges:
        box(ax, ay, bx, by, 0.02, 2.0, M['shower_glass'], cn, name + ' Glass')
        add_obst((ax + bx) / 2, (ay + by) / 2, abs(bx - ax) / 2 + 0.05, abs(by - ay) / 2 + 0.05, 0, name + ' Glass')
    if head[0] is not None:
        X, Y = W(*head)
        cylm(X, Y, 0.11, 2.05, 2.07, M['black'], cn, name + ' Head', 24)
        cylm(X, Y, 0.012, 2.07, CEIL, M['black'], cn, name + ' Arm', 8)

def shelves_u(x0, y0, x1, y1, cn, name='Closet Shelving'):
    """U shaped closet hang rails + shelves just inside the rectangle (plan ft)"""
    d = 0.6 / F
    for (a0, b0, a1, b1) in [(x0, y0, x0 + d, y1), (x1 - d, y0, x1, y1), (x0 + d, y1 - d, x1 - d, y1)]:
        box(a0, b0, a1, b1, 1.78, 1.80, M['oak'], cn, name + ' Shelf')
        box(a0, b0, a1, b1, 0.0, 0.10, M['oak'], cn, name + ' Base')
        mx, my = (a0 + a1) / 2, (b0 + b1) / 2
        if (a1 - a0) < (b1 - b0):
            box(mx - 0.03, b0, mx + 0.03, b1, 1.65, 1.67, M['brass'], cn, name + ' Rod')
            n = int((b1 - b0) / 0.5)
            for i in range(n):
                yy = b0 + 0.25 + i * 0.5
                box(mx - 0.8, yy, mx + 0.8, yy + 0.08, 0.95 + random.uniform(0, 0.2), 1.62,
                    random.choice([M['linen'], M['charcoal'], M['sage'], M['rust'], M['navy']]), cn, name + ' Garment')
        else:
            box(a0, my - 0.03, a1, my + 0.03, 1.65, 1.67, M['brass'], cn, name + ' Rod')

def bookshelf(x0, y0, x1, y1, cn, name='Bookshelf'):
    box(x0, y0, x1, y1, 0, 1.9, M['oak'], cn, name + ' Body', 0.005, obst=True, tag=name)
    horiz = (x1 - x0) > (y1 - y0)
    for k in range(5):
        z = 0.12 + k * 0.36
        n = random.randint(6, 12)
        if horiz:
            xs = x0 + 0.15
            for i in range(n):
                wft = random.uniform(0.08, 0.15)
                if xs + wft > x1 - 0.15: break
                h = random.uniform(0.2, 0.3)
                box(xs, y1, xs + wft, y1 + 0.02, z, z + h, random.choice(BOOK_MATS), cn, name + ' Book')
                xs += wft + 0.01

# ----------------------------------------------------------------------------
# lights
# ----------------------------------------------------------------------------
LI = 'Lighting'
def add_point(name, X, Y, Z, power, color=(1, 0.85, 0.7), radius=0.1):
    d = bpy.data.lights.new(name, 'POINT')
    d.energy = power; d.color = color; d.shadow_soft_size = radius
    o = bpy.data.objects.new(name, d); o.location = (X, Y, Z)
    link(o, LI)
    return o

AREA_SCALE = 0.45
def area(name, x0, y0, x1, y1, power, color=(1.0, 0.86, 0.70), z=CEIL - 0.02):
    d = bpy.data.lights.new(name, 'AREA')
    d.shape = 'RECTANGLE'
    d.size = abs(x1 - x0) * F * 0.8; d.size_y = abs(y1 - y0) * F * 0.8
    d.energy = power * AREA_SCALE; d.color = color
    o = bpy.data.objects.new(name, d)
    X, Y = W((x0 + x1) / 2, (y0 + y1) / 2)
    o.location = (X, Y, z)
    link(o, LI)
    return o

def downlight(x, y, cn=LI):
    X, Y = W(x, y)
    cylm(X, Y, 0.06, CEIL - 0.004, CEIL - 0.001, M['bulb'], cn, 'Recessed Downlight', 16)
    cylm(X, Y, 0.075, CEIL - 0.003, CEIL, M['trim'], cn, 'Downlight Trim', 16)

# ============================================================================
# ROOMS
# ============================================================================
# ---------------- Kitchen ----------------------------------------------------
K = 'Kitchen'
box(43.9, 12.0, 45.88, 16.6, 0.0, 2.40, M['navy'], K, 'Pantry Cabinet', 0.006, obst=True)
box(43.85, 12.0, 43.9, 16.6, 0.06, 2.34, M['navy'], K, 'Pantry Doors', 0.003)
box(43.80, 14.25, 43.85, 14.35, 0.9, 1.4, M['brass'], K, 'Pantry Pull')
box(43.6, 16.6, 45.88, 19.6, 0.0, 2.05, M['steel'], K, 'Refrigerator', 0.01, obst=True)
box(43.55, 18.05, 43.6, 18.12, 0.9, 1.7, M['black'], K, 'Fridge Handle')
box(43.55, 18.14, 43.6, 18.21, 0.9, 1.7, M['black'], K, 'Fridge Handle')
box(43.9, 16.6, 45.88, 19.6, 2.05, 2.40, M['navy'], K, 'Fridge Upper')
box(43.6, 19.6, 45.88, 31.4, 0.1, 0.86, M['navy'], K, 'Base Cabinets', 0.004, obst=True)
box(43.7, 19.6, 45.88, 31.4, 0.0, 0.1, M['black'], K, 'Toe Kick')
for yy in [x * 0.5 + 19.6 for x in range(0, 24)]:   # door/drawer reveal lines
    box(43.585, yy - 0.01, 43.6, yy + 0.01, 0.12, 0.84, M['black'], K, 'Reveal')
box(43.4, 19.6, 45.88, 31.4, 0.86, 0.91, M['quartz'], K, 'Counter', 0.003)
box(45.80, 19.6, 45.88, 31.4, 0.91, 1.45, M['shower_tile'], K, 'Backsplash')
box(43.7, 23.3, 45.6, 26.0, 0.91, 0.915, M['glass_black'], K, 'Cooktop')
for (cy_, cx_) in [(23.9, 44.2), (25.4, 44.2), (23.9, 45.1), (25.4, 45.1)]:
    cyl(cx_, cy_, 0.09, 0.915, 0.918, M['charcoal'], K, 'Burner', 20)
box(44.2, 23.2, 45.88, 26.1, 1.62, CEIL, M['wall'], K, 'Range Hood', 0.01)
box(44.15, 23.15, 45.88, 26.15, 1.58, 1.64, M['brass'], K, 'Hood Band', 0.004)
for (a, b) in [(19.8, 23.0), (26.3, 31.2)]:   # open walnut shelves
    for z in (1.40, 1.85):
        box(44.9, a, 45.88, b, z, z + 0.04, M['walnut'], K, 'Open Shelf', 0.004)
    for i in range(int((b - a) / 0.55)):
        yy = a + 0.3 + i * 0.55
        cyl(45.4, yy, 0.05, 1.44, 1.44 + random.choice([0.1, 0.16, 0.22]), random.choice([M['porcelain'], M['pot'], M['navy']]), K, 'Ceramic', 16)
# L-return and wall ovens
box(43.2, 31.4, 45.88, 33.75, 0.1, 0.86, M['navy'], K, 'Base Cabinets L', 0.004, obst=True)
box(43.1, 31.4, 45.88, 33.75, 0.86, 0.91, M['quartz'], K, 'Counter L', 0.003)
box(40.53, 31.65, 43.2, 33.75, 0.0, 2.40, M['navy'], K, 'Oven Tower', 0.006, obst=True)
box(40.9, 31.6, 42.8, 31.65, 0.75, 1.30, M['glass_black'], K, 'Wall Oven')
box(40.9, 31.6, 42.8, 31.65, 1.35, 1.80, M['glass_black'], K, 'Microwave')
box(40.9, 31.58, 42.8, 31.6, 1.25, 1.27, M['steel'], K, 'Oven Handle')
# island with waterfall quartz
box(36.5, 21.4, 39.6, 28.0, 0.1, 0.88, M['navy'], K, 'Island Base', 0.004)
box(35.8, 21.2, 39.8, 28.2, 0.88, 0.94, M['quartz'], K, 'Island Top', 0.004)
box(35.8, 21.2, 39.8, 21.4, 0.0, 0.88, M['quartz'], K, 'Waterfall', 0.004)
box(35.8, 28.0, 39.8, 28.2, 0.0, 0.88, M['quartz'], K, 'Waterfall', 0.004)
add_obst(37.8, 24.7, 2.0, 3.5, 0, 'Island')
box(38.2, 23.9, 39.3, 25.6, 0.90, 0.941, M['steel'], K, 'Sink')
cyl(39.45, 24.75, 0.018, 0.94, 1.32, M['brass'], K, 'Faucet', 10)
box(39.0, 24.70, 39.47, 24.80, 1.30, 1.33, M['brass'], K, 'Faucet Spout')
for yy in (22.9, 24.7, 26.5):
    g = Group('Counter Stool', 34.9, yy, 'W', K, 0.24, 0.24)
    g.cyl(0, 0, 0.21, 0.62, 0.67, M['walnut'], 24)
    g.cyl(0, 0, 0.2, 0.25, 0.27, M['black'], 24, cap=False)
    for a in range(4):
        aa = a * math.pi / 2 + math.pi / 4
        leg = g.box(-0.012, -0.012, 0, 0.012, 0.012, 0.63, M['black'], 0)
        leg.location = (0.14 * math.cos(aa), 0.14 * math.sin(aa), 0)
    g.box(-0.16, 0.12, 0.67, 0.16, 0.16, 0.85, M['walnut'], 0.01)
for yy in (22.4, 24.7, 27.0):
    X, Y = W(37.8, yy)
    cylm(X, Y, 0.005, 1.95, CEIL, M['black'], K, 'Pendant Cord', 6)
    sphere(X, Y, 1.86, 0.17, M['copper'], K, 'Pendant', sz=0.6)
    cylm(X, Y, 0.13, 1.79, 1.80, M['bulb'], K, 'Pendant Glow', 20)
    add_point('Pendant Light', X, Y, 1.76, 35, (1.0, 0.78, 0.5), 0.08)

# ---------------- Dining ------------------------------------------------------
D = 'Dining'
box(31.0, 13.2, 39.0, 16.0, 0.72, 0.76, M['walnut'], D, 'Dining Table', 0.006)
for (lx, ly) in [(31.6, 13.6), (38.4, 13.6), (31.6, 15.6), (38.4, 15.6)]:
    box(lx - 0.12, ly - 0.12, lx + 0.12, ly + 0.12, 0, 0.72, M['walnut'], D, 'Table Leg')
add_obst(35.0, 14.6, 4.0, 1.4, 0, 'Dining Table')
for xx in (32.4, 35.0, 37.6):
    chair(xx, 12.85, 'S', M['boucle'], cn=D)
    chair(xx, 16.35, 'N', M['boucle'], cn=D)
chair(30.35, 14.6, 'E', M['boucle'], cn=D)
chair(39.65, 14.6, 'W', M['boucle'], cn=D)
X, Y = W(35.0, 14.6)
boxm(X - 0.75, Y - 0.04, 1.86, X + 0.75, Y + 0.04, 1.90, M['brass'], D, 'Linear Chandelier')
boxm(X - 0.72, Y - 0.025, 1.855, X + 0.72, Y + 0.025, 1.86, M['bulb'], D, 'Linear Chandelier Glow')
for dx in (-0.6, 0.6):
    cylm(X + dx, Y, 0.004, 1.90, CEIL, M['black'], D, 'Chandelier Cable', 6)
add_point('Dining Light', X, Y, 1.80, 45, (1.0, 0.8, 0.55), 0.3)
cyl(35.0, 14.6, 0.08, 0.76, 0.98, M['porcelain'], D, 'Vase', 20)
for i in range(5):
    sphere(X + random.uniform(-0.08, 0.08), Y + random.uniform(-0.08, 0.08), 1.02 + random.uniform(0, 0.12), 0.06, M['plant'], D, 'Stems', sx=0.6, sy=0.6, sz=1.6, seg=8)

# ---------------- Living --------------------------------------------------------
L = 'Living'
rug(18.9, 19.0, 27.2, 30.8, M['rug'], L, 'Living Rug')
g = Group('Sectional Sofa', 26.55, 22.75, 'W', L, obst=False)     # leg facing the fireplace
add_obst(26.55, 22.75, 1.55, 4.7, 0, 'Sectional (leg B)')
add_obst(23.0, 19.55, 2.05, 1.45, 0, 'Sectional (leg A)')
# local coords: +Y = west (toward fireplace).  Leg B: back along east side
LB = 1.42  # half length in metres of leg B along world Y (plan y 18.1 .. 27.4); local -X = south
g.box(-LB, -0.47, 0.08, LB, 0.47, 0.42, M['boucle'], 0.05)
g.box(-LB, -0.47, 0.42, LB, -0.25, 0.80, M['boucle'], 0.06)
g.box(-LB, -0.47, 0.0, -LB + 0.06, 0.47, 0.08, M['black'], 0)
for k in range(3):   # seat cushions
    a = -LB + 0.2 + k * 0.88
    g.box(a + 0.01, -0.25, 0.42, a + 0.87, 0.45, 0.52, M['boucle'], 0.05)
g.box(-LB, -0.47, 0.42, -LB + 0.20, 0.47, 0.62, M['boucle'], 0.05)       # arm (south end)
# Leg A along north side (plan y 18.1-21.0), x 21.0-25.1, facing south
g2 = Group('Sectional Sofa A', 23.05, 19.55, 'S', L, obst=False)
# local +X = west here; the east end butts into leg B
g2.box(-0.62, -0.44, 0.08, 0.62, 0.44, 0.42, M['boucle'], 0.05)
g2.box(-0.62, -0.44, 0.42, 0.62, -0.22, 0.80, M['boucle'], 0.06)
g2.box(0.42, -0.44, 0.42, 0.62, 0.44, 0.62, M['boucle'], 0.05)
g2.box(-0.62, -0.22, 0.42, 0.41, 0.42, 0.52, M['boucle'], 0.05)
for (px, m) in [(0.15, M['rust']), (-0.25, M['sage'])]:
    g2.box(px - 0.2, -0.2, 0.5, px + 0.2, -0.08, 0.86, m, 0.06)
for (px, m) in [(-0.9, M['rust']), (0.6, M['linen'])]:
    g.box(px - 0.2, -0.24, 0.5, px + 0.2, -0.12, 0.86, m, 0.06)
# coffee table (travertine look) + decor
box(21.2, 23.0, 23.2, 28.0, 0.30, 0.38, M['quartz'], L, 'Coffee Table', 0.01, obst=True)
box(21.5, 23.3, 22.9, 27.7, 0.0, 0.30, M['walnut'], L, 'Coffee Table Base', 0.01)
for (yy, m) in [(24.2, BOOK_MATS[1]), (24.2, BOOK_MATS[2])]:
    box(21.6, yy, 22.6, yy + 0.8, 0.38 + (0.03 if m == BOOK_MATS[2] else 0), 0.41 + (0.03 if m == BOOK_MATS[2] else 0), m, L, 'Coffee Book')
cyl(22.2, 26.5, 0.12, 0.38, 0.45, M['brass'], L, 'Bowl', 24)
armchair(23.05, 30.25, 'N', name='Living Lounge Chair', cn=L)
box(25.4, 29.4, 27.2, 31.2, 0.0, 0.55, M['walnut'], L, 'Side Table', 0.02, obst=True)
lamp(26.3, 30.3, 0.55, L, h=0.38, r=0.15, name='Side Table Lamp')
plant(17.6, 32.6, L, 1.6, 0.24, 'Fiddle Leaf Plant')
floor_lamp(19.9, 30.6, L, 'Reading Floor Lamp')
# fireplace feature wall
box(15.53, 24.15, 16.49, 29.34, 0.95, CEIL, M['stone'], L, 'Fireplace Surround')
box(15.53, 24.15, 16.49, 29.34, 0.0, 0.25, M['stone'], L, 'Fireplace Hearth')
box(15.53, 24.15, 15.60, 29.34, 0.25, 0.95, M['glass_black'], L, 'Firebox Back')
box(15.6, 24.3, 16.3, 29.2, 0.25, 0.27, M['charcoal'], L, 'Firebox Bed')
for i in range(9):
    yy = 24.6 + i * 0.52
    sphere(*W(15.95, yy), 0.31, 0.045, M['flame'], L, 'Flame', sx=0.45, sy=1.3, sz=random.uniform(2.2, 3.4), seg=10)
    box(15.75, yy - 0.2, 16.15, yy + 0.2, 0.25, 0.29, M['log'], L, 'Ember Log', 0.01)
add_point('Fireplace Glow', *W(16.2, 26.7), 0.5, 40, (1.0, 0.5, 0.2), 0.3)
box(16.49, 24.15, 16.53, 29.34, 0.25, 0.95, M['glass'], L, 'Firebox Glass')
box(16.49, 24.0, 16.62, 29.5, 0.95, 1.0, M['walnut'], L, 'Mantel', 0.004)
box(16.49, 24.6, 16.55, 28.9, 1.35, 2.05, M['screen'], L, 'TV', 0.004)
box(14.57, 22.95, 16.49, 24.12, 0.0, CEIL, M['stone'], L, 'Stone Pier')
box(14.57, 29.34, 16.49, 30.56, 0.0, CEIL, M['stone'], L, 'Stone Pier')
# firewood niche
box(14.57, 18.54, 14.62, 22.95, 0, CEIL, M['walnut'], L, 'Niche Back')
for z in (0.0, 0.9, 1.8):
    box(14.6, 18.54, 16.49, 22.95, z, z + 0.04, M['walnut'], L, 'Niche Shelf')
for z0 in (0.04, 0.94):
    for r in range(4):
        for c in range(9):
            xx = 15.5; yy = 18.85 + c * 0.47 + (0.23 if r % 2 else 0)
            if yy > 22.75: continue
            o = cylm(0, 0, random.uniform(0.045, 0.06), 0, 0.56, M['log'], L, 'Log', 9, smooth=False)
            o.rotation_euler = (0, math.pi / 2, 0)
            X, Y = W(14.65, yy)
            o.location = (X, Y, z0 + 0.07 + r * 0.13)
box(14.6, 18.54, 16.49, 22.95, 1.84, 1.86, M['oak'], L, 'Niche Shelf Top')
for i, m in enumerate([M['pot'], M['porcelain'], M['brass']]):
    cyl(15.4, 19.5 + i * 1.2, 0.07 + 0.02 * i, 1.86, 2.05 + 0.08 * i, m, L, 'Decor Vessel', 18)
add_obst(15.5, 20.7, 1.0, 2.3, 0, 'Wood niche')
frame_art(14.6, 32.8, 'E', 0.9, 1.2, 1.55, M['art2'], L, 'Living Art')

# ---------------- Den --------------------------------------------------------------
DN = 'Den'
rug(17.6, 37.0, 25.6, 44.4, M['rug2'], DN, 'Den Rug')
g = Group('Den Sleeper Sofa', 22.2, 44.6, 'N', DN, 1.25, 0.48)
sofa_straight(g, -1.20, 1.20, -0.47, 0.94, M['sage'])
g.box(-1.20, -0.47, 0.42, -1.02, 0.47, 0.64, M['sage'], 0.05)
g.box(1.02, -0.47, 0.42, 1.20, 0.47, 0.64, M['sage'], 0.05)
g.box(-0.98, -0.25, 0.42, 0.98, 0.45, 0.52, M['sage'], 0.05)
g.box(-0.9, -0.24, 0.5, -0.5, -0.12, 0.86, M['linen'], 0.06)
g.box(0.5, -0.24, 0.5, 0.9, -0.12, 0.86, M['rust'], 0.06)
box(20.6, 39.6, 23.8, 41.6, 0.36, 0.40, M['walnut'], DN, 'Den Coffee Table', 0.008, obst=True)
for (lx, ly) in [(20.8, 39.8), (23.6, 39.8), (20.8, 41.4), (23.6, 41.4)]:
    cyl(lx, ly, 0.02, 0, 0.36, M['black'], DN, 'Leg', 8)
box(25.5, 37.0, 27.5, 41.6, 0.72, 0.76, M['oak'], DN, 'Desk', 0.006, obst=True)
for ly in (37.2, 41.4):
    box(25.6, ly - 0.1, 27.4, ly + 0.1, 0.0, 0.72, M['black'], DN, 'Desk Leg')
chair(24.7, 39.3, 'E', M['cognac'], 'Desk Chair', DN)
lamp(27.0, 37.6, 0.76, DN, h=0.35, r=0.12, name='Desk Lamp')
box(27.0, 39.0, 27.05, 40.6, 0.76, 1.12, M['screen'], DN, 'Monitor')
bookshelf(17.2, 35.65, 21.6, 36.9, DN, 'Den Bookshelf')
frame_art(27.45, 39.3, 'W', 1.2, 0.8, 1.55, M['art1'], DN, 'Den Art')
plant(26.6, 44.8, DN, 1.2, 0.2, 'Den Plant')

# ---------------- Primary bedroom ------------------------------------------------
PB = 'Primary Bedroom'
rug(3.0, 6.0, 10.4, 15.2, M['rug'], PB, 'Primary Rug')
bed(4.7, 10.6, 'E', 1.93, 2.13, PB, 'Primary King Bed')
nightstand(1.65, 6.25, 'E', PB, 'Primary Nightstand L')
nightstand(1.65, 14.95, 'E', PB, 'Primary Nightstand R')
dresser(13.15, 10.5, 'W', 1.75, PB, 'Primary Dresser')
box(13.6, 9.0, 13.65, 12.0, 1.0, 1.85, M['screen'], PB, 'Bedroom TV')
armchair(11.9, 3.7, -135, M['boucle'], 'Primary Reading Chair', PB)
floor_lamp(13.3, 2.4, PB, 'Primary Floor Lamp')
frame_art(0.62, 10.6, 'E', 1.5, 0.75, 1.75, M['art1'], PB, 'Primary Bed Art')
plant(2.0, 2.4, PB, 1.3, 0.2, 'Primary Plant')

# ---------------- Primary bathroom -----------------------------------------------
PBA = 'Primary Bath'
shower(0.6, 18.55, 7.3, 22.0, [(1.6, 21.9, 7.3, 22.0), (7.25, 19.6, 7.35, 22.0)], PBA, 'Primary Shower', head=(3.5, 19.0))
box(0.6, 18.55, 1.6, 22.0, 0.0, 0.46, M['quartz'], PBA, 'Shower Bench', 0.004)
box(0.6, 18.55, 7.3, 18.65, 0.0, CEIL, M['shower_tile'], PBA, 'Shower Wall Tile')
box(0.62, 18.55, 0.7, 22.0, 0.0, CEIL, M['shower_tile'], PBA, 'Shower Wall Tile')
vanity(12.3, 21.9, 14.0, 30.4, PBA, [(13.2, 23.6), (13.2, 28.4)], 'E', 'Primary Vanity')
for yy in (23.6, 28.4):
    box(13.97, yy - 1.2, 14.0, yy + 1.2, 1.05, 2.0, M['mirror'], PBA, 'Mirror', 0.002)
    box(13.95, yy - 1.25, 13.97, yy + 1.25, 1.02, 2.03, M['brass'], PBA, 'Mirror Frame')
    for dy in (-1.45, 1.45):
        X, Y = W(13.85, yy + dy)
        cylm(X, Y, 0.04, 1.45, 1.75, M['lampshade'], PBA, 'Sconce', 16)
# freestanding tub (hollow ellipse)
X, Y = W(4.2, 28.6)
tub = cylm(X, Y, 1, 0.0, 0.58, M['porcelain'], PBA, 'Freestanding Tub', 40, rx=0.82, ry=0.38, cap=False)
md = tub.modifiers.new('Solid', 'SOLIDIFY'); md.thickness = 0.06
bpy.context.view_layer.objects.active = tub
cylm(X, Y, 1, 0.0, 0.06, M['porcelain'], PBA, 'Tub Floor', 40, rx=0.80, ry=0.36)
cylm(X, Y, 1, 0.38, 0.39, M['steel'], PBA, 'Tub Water', 40, rx=0.76, ry=0.33)
add_obst(4.2, 28.6, 0.85 / F, 0.42 / F, 0, 'Tub')
cyl(7.2, 29.3, 0.02, 0, 0.95, M['brass'], PBA, 'Tub Filler', 10)
box(6.75, 29.25, 7.2, 29.35, 0.92, 0.95, M['brass'], PBA, 'Tub Filler Spout')
plant(1.4, 26.2, PBA, 1.0, 0.16, 'Bath Plant')
frame_art(0.62, 28.6, 'E', 1.0, 0.7, 1.55, M['art3'], PBA, 'Bath Art')
toilet(1.6, 32.3, 'E', PBA, 'Primary Toilet')
box(12.3, 30.6, 14.0, 34.6, 0.0, 2.2, M['walnut'], PBA, 'Linen Cabinet', 0.006, obst=True)

# ---------------- Primary closet ------------------------------------------------------
shelves_u(5.1, 35.1, 13.9, 45.7, 'Primary Closet', 'Primary Closet')
box(7.8, 39.0, 11.2, 42.0, 0, 0.92, M['oak'], 'Primary Closet', 'Closet Island', 0.006)

# ---------------- Bedroom 2 ----------------------------------------------------------
B2 = 'Bedroom 2'
rug(51.0, 6.0, 57.8, 13.4, M['rug2'], B2, 'Bedroom 2 Rug')
bed(56.0, 9.6, 'W', 1.6, 2.05, B2, 'Bedroom 2 Queen Bed')
nightstand(58.4, 5.6, 'W', B2, 'Bedroom 2 Nightstand L')
nightstand(58.4, 13.6, 'W', B2, 'Bedroom 2 Nightstand R')
dresser(47.35, 9.6, 'E', 1.7, B2, 'Bedroom 2 Dresser')
frame_art(46.48, 9.6, 'E', 1.0, 0.7, 1.45, M['art3'], B2, 'Bedroom 2 Dresser Art')
frame_art(59.28, 9.6, 'W', 1.2, 0.6, 1.70, M['art2'], B2, 'Bedroom 2 Bed Art')
armchair(48.4, 3.6, 135, M['sage'], 'Bedroom 2 Chair', B2)
plant(54.5, 2.4, B2, 1.2, 0.2, 'Bedroom 2 Plant')

# ---------------- Bath 2, hall bath, closets, laundry, mech ---------------------------
B2A = 'Bath 2'
shower(53.0, 16.62, 59.28, 20.0, [(53.0, 19.9, 58.0, 20.0)], B2A, 'Bath 2 Shower', head=(56.0, 17.1))
box(50.88, 16.62, 52.7, 18.24, 0.0, 2.3, M['oak'], B2A, 'Linen Tower', 0.005)
vanity(57.6, 20.5, 59.28, 23.7, B2A, [(58.4, 22.1)], 'E', 'Bath 2 Vanity')
box(59.25, 20.9, 59.28, 23.3, 1.05, 1.95, M['mirror'], B2A, 'Mirror')
toilet(58.5, 26.3, 'W', B2A, 'Bath 2 Toilet')
shelves_u(51.3, 28.5, 59.0, 37.8, 'Closet 2', 'Closet 2')
HB = 'Hall Bath'
shower(29.4, 35.6, 35.2, 38.6, [(29.4, 38.5, 34.0, 38.6)], HB, 'Hall Shower', head=(32.0, 36.0))
vanity(28.0, 43.6, 31.3, 45.2, HB, [(29.6, 44.5)], 'S', 'Hall Vanity')
box(28.4, 45.17, 30.8, 45.2, 1.05, 1.9, M['mirror'], HB, 'Mirror')
toilet(33.3, 44.4, 'N', HB, 'Hall Toilet')
LA = 'Laundry'
for xx in (46.0, 48.4):
    box(xx, 43.5, xx + 2.25, 45.6, 0.0, 0.95, M['porcelain'], LA, 'Washer/Dryer', 0.02)
    box(xx + 0.6, 43.45, xx + 1.65, 43.5, 0.25, 0.75, M['glass_black'], LA, 'Washer Door')
box(50.9, 43.6, 54.6, 45.6, 0.1, 0.86, M['navy'], LA, 'Laundry Cabinet', 0.004)
box(46.0, 43.4, 54.6, 45.6, 0.95, 0.99, M['quartz'], LA, 'Laundry Counter', 0.003)
box(46.0, 44.6, 54.6, 45.6, 1.45, 2.2, M['navy'], LA, 'Laundry Uppers', 0.004)
cyl(57.4, 41.0, 0.28, 0.0, 1.5, M['porcelain'], 'Mech', 'Water Heater', 24)
box(43.2, 38.9, 44.9, 45.5, 1.7, 1.72, M['oak'], 'Entry', 'Coat Closet Shelf')
frame_art(42.62, 38.8, 'W', 0.6, 0.8, 1.55, M['art2'], 'Entry', 'Entry Art')

# ---------------- Balcony furniture ---------------------------------------------------
BA = 'Balcony'
armchair(16.4, 3.2, 'E', M['charcoal'], 'Balcony Lounge Chair', BA)
armchair(16.4, 7.4, 'E', M['charcoal'], 'Balcony Lounge Chair', BA)
box(19.2, 3.9, 21.1, 6.8, 0.0, 0.40, M['oak'], BA, 'Balcony Coffee Table', 0.01, obst=True)
g = Group('Balcony Sofa', 23.0, 6.0, 'W', BA, 1.07, 0.47)
sofa_straight(g, -1.05, 1.05, -0.45, 0.9, M['charcoal'])
g.box(-1.05, -0.45, 0.42, -0.9, 0.45, 0.6, M['charcoal'], 0.04)
g.box(0.9, -0.45, 0.42, 1.05, 0.45, 0.6, M['charcoal'], 0.04)
g.box(-0.6, -0.25, 0.48, -0.2, -0.12, 0.8, M['rust'], 0.05)
box(32.6, 4.2, 38.0, 7.2, 0.72, 0.76, M['oak'], BA, 'Balcony Dining Table', 0.006)
for (lx, ly) in [(32.9, 4.5), (37.7, 4.5), (32.9, 6.9), (37.7, 6.9)]:
    cyl(lx, ly, 0.03, 0, 0.72, M['black'], BA, 'Leg', 8)
add_obst(35.3, 5.7, 2.7, 1.5, 0, 'Balcony Table')
for xx in (34.0, 36.6):
    chair(xx, 3.35, 'S', M['charcoal'], 'Balcony Chair', BA)
    chair(xx, 8.05, 'N', M['charcoal'], 'Balcony Chair', BA)
chair(31.8, 5.7, 'E', M['charcoal'], 'Balcony Chair', BA)
chair(38.8, 5.7, 'W', M['charcoal'], 'Balcony Chair', BA)
box(42.6, 2.2, 44.9, 9.4, 0.0, 0.92, M['steel'], BA, 'Outdoor Kitchen', 0.01, obst=True)
box(42.6, 2.2, 44.9, 9.4, 0.92, 0.95, M['stone'], BA, 'Outdoor Counter', 0.004)
plant(44.5, 10.3, BA, 1.4, 0.25, 'Balcony Plant')
plant(15.9, 10.2, BA, 1.0, 0.2, 'Balcony Plant')

# ---------------- ceiling lighting -------------------------------------------------
for (x, y) in [(20, 14), (25, 14), (20, 22), (20, 28), (24, 25), (30, 22), (30, 28), (33, 32.5),
               (41.6, 21), (41.6, 25), (41.6, 29), (37.6, 37), (37.6, 42), (44, 36), (48.5, 20), (48.5, 25),
               (48.5, 31), (6, 5), (10, 5), (6, 15), (11, 14.5), (21, 38), (24, 42), (9.6, 21), (9.6, 26),
               (4, 24.5), (52, 6), (52, 12), (55, 22), (31.5, 41)]:
    downlight(x, y)
area('Living Fill', 17.5, 13, 29, 32, 260)
area('Kitchen Fill', 33, 19, 45, 32, 220)
area('Dining Fill', 30, 12.5, 40, 18, 110)
area('Entry Fill', 35.8, 34.5, 45.5, 44.5, 140)
area('Hall Fill', 46.5, 16.6, 50.4, 38, 90)
area('Den Fill', 16.8, 35.6, 27.4, 45.6, 140)
area('Primary Bedroom Fill', 0.8, 1.6, 13.8, 17.8, 220)
area('Primary Bath Fill', 0.8, 18.6, 13.8, 34.4, 200)
area('Bedroom 2 Fill', 46.6, 1.6, 59.2, 16.0, 200)
area('Bath 2 Fill', 51, 16.7, 59.2, 27.8, 110)
area('Laundry Fill', 45.7, 38.8, 59.2, 45.6, 80)
area('Closet Fill', 5.1, 35.1, 13.9, 45.7, 80)
area('Closet 2 Fill', 51.2, 28.4, 59.1, 37.9, 60)
area('Hall Bath Fill', 27.9, 35.6, 35.2, 45.4, 70)
area('Balcony Soffit', 16, 1, 45, 10.5, 150)

# sun + sky
sun_d = bpy.data.lights.new('Sun', 'SUN'); sun_d.energy = 4.0; sun_d.angle = math.radians(1.5)
sun_d.color = (1.0, 0.93, 0.83)
sun = bpy.data.objects.new('Sun', sun_d); sun.rotation_euler = (math.radians(55), 0, math.radians(200))
link(sun, LI)
world = bpy.data.worlds.new('World'); scene.world = world
world.use_nodes = True
wn = world.node_tree
bg = wn.nodes['Background']
try:
    sky = wn.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'NISHITA' if 'NISHITA' in [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items] else sky.sky_type
    sky.sun_elevation = math.radians(35); sky.sun_rotation = math.radians(200)
    wn.links.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.12
except Exception as e:
    print('sky fallback', e)
    bg.inputs['Color'].default_value = (0.55, 0.70, 0.95, 1)
    bg.inputs['Strength'].default_value = 1.0

# ---------------- surroundings (seen through the glass) -------------------------------------
EX = 'Exterior'
boxm(-140, -60, -7.5, 160, 200, -7.4, M['ground'], EX, 'Ground')
boxm(-140, 28, -7.399, 160, 40, -7.39, M['road'], EX, 'Street')
for i in range(14):
    x = -70 + i * 13 + random.uniform(-3, 3)
    w = random.uniform(8, 12); d = random.uniform(10, 16); h = random.uniform(6, 26)
    boxm(x, 60, -7.4, x + w, 60 + d, -7.4 + h, random.choice([M['facade'], M['facade2']]), EX, 'Neighbour Building')
    # window bands
    for k in range(int(h / 3.2)):
        boxm(x + 0.5, 59.95, -6 + k * 3.2, x + w - 0.5, 60.01, -4.8 + k * 3.2, M['glass_black'], EX, 'Neighbour Windows')
for i in range(26):
    x = -60 + i * 6 + random.uniform(-2, 2); y = random.uniform(14, 26)
    cylm(x, y, 0.18, -7.4, -4.2, M['walnut'], EX, 'Tree Trunk', 8)
    sphere(x, y, -2.8, random.uniform(1.8, 2.6), M['plant'], EX, 'Tree Canopy', seg=12)
for i in range(8):
    x = -40 + i * 15
    sphere(x, 48, -2.0, 3.5, M['plant'], EX, 'Tree Canopy', seg=12)

# ============================================================================
# CAMERA PATH
# ============================================================================
# waypoint: (x_ft, y_ft, speed factor, look target (x_ft, y_ft) or None)
WAYPOINTS = [
    (37.6, 44.3, 0.55, (37.6, 30.0)),   # front door, looking up the entry hall
    (37.6, 40.0, 0.95, None),
    (37.5, 35.4, 0.90, (30.0, 36.0)),
    (34.4, 33.6, 0.80, (25.0, 38.0)),   # passing the den - looking in through its opening
    (30.5, 33.3, 0.60, (24.0, 39.5)),
    (27.2, 33.0, 0.45, (23.5, 41.0)),
    (28.0, 31.9, 0.45, (21.0, 40.0)),
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
    (8.9, 21.3, 0.80, (4.2, 26.5)),
    (8.8, 24.8, 0.70, (4.2, 28.6)),     # tub & shower
    (10.0, 27.4, 0.45, (13.5, 26.5)),
    (11.0, 25.2, 0.50, (13.5, 23.0)),   # double vanity
    (9.9, 22.3, 0.80, (9.6, 16.0)),
    (9.7, 18.4, 0.95, None),
    (11.2, 16.6, 1.00, (15.0, 16.2)),
    (14.36, 16.25, 1.05, None),
    (18.5, 16.7, 1.10, None),
    (25.0, 16.8, 1.10, None),
    (29.1, 17.4, 1.05, None),
    (31.4, 20.4, 1.05, None),
    (32.0, 29.5, 1.10, None),
    (36.0, 32.6, 1.10, None),
    (40.5, 35.9, 1.10, None),
    (45.0, 36.2, 1.05, None),
    (48.5, 34.0, 1.00, (48.5, 20.0)),   # bedroom hallway
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
# render defaults (EEVEE) + save
# ----------------------------------------------------------------------------
scene.render.engine = 'BLENDER_EEVEE'
ee = scene.eevee
for attr, val in [('taa_render_samples', 32), ('use_shadows', True), ('use_raytracing', True),
                  ('shadow_ray_count', 1), ('shadow_step_count', 4), ('use_fast_gi', True)]:
    try:
        setattr(ee, attr, val)
    except Exception as e:
        print('eevee attr', attr, e)
try:
    ee.ray_tracing_options.resolution_scale = '2'
except Exception:
    pass
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast' if 'AgX - Medium High Contrast' in [
    i.identifier for i in scene.view_settings.bl_rna.properties['look'].enum_items_static] else 'None'
scene.view_settings.exposure = 0.0
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print('saved', OUT)
