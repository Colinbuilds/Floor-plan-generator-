"""Omaha surroundings, four seasons and a solar day cycle for Residence 2B.

The balcony faces south (world +Y = south, +X = west, -X = east).
Sun positions use Omaha's latitude (41.26 N) and a representative date per season.
Times of day are a continuous parameter t:
    0 = morning (9:00 solar), 1 = midday (12:30), 2 = golden hour (sun 7 deg), 3 = night (sun -10 deg)
"""
import bpy, math, random
import mathutils
from geo import F, coll, link, boxm, cylm, sphere, ico, mesh_obj, principled, noisy, emissive, glass, tex_coord, MATS

LAT = 41.26
GROUND_Z = -11.0          # Level 4 floor is ~11 m above the street

SEASONS = {
    'spring': dict(label='Spring', date='Apr 20', decl=11.5,
                   canopy=((0.17, 0.33, 0.06), (0.30, 0.48, 0.10)),
                   canopy_b=((0.80, 0.50, 0.60), (0.95, 0.84, 0.88)),
                   ground=((0.14, 0.26, 0.05), (0.22, 0.32, 0.08)),
                   roof=((0.18, 0.17, 0.17), (0.24, 0.22, 0.21)), snow=False, leaves=True, haze=1.0),
    'summer': dict(label='Summer', date='Jul 10', decl=22.3,
                   canopy=((0.04, 0.12, 0.025), (0.09, 0.20, 0.04)),
                   canopy_b=((0.06, 0.15, 0.03), (0.11, 0.23, 0.05)),
                   ground=((0.07, 0.15, 0.035), (0.12, 0.20, 0.05)),
                   roof=((0.18, 0.17, 0.17), (0.24, 0.22, 0.21)), snow=False, leaves=True, haze=1.2),
    'fall':   dict(label='Fall', date='Oct 18', decl=-9.6,
                   canopy=((0.50, 0.15, 0.02), (0.78, 0.46, 0.05)),
                   canopy_b=((0.42, 0.05, 0.02), (0.62, 0.17, 0.03)),
                   ground=((0.22, 0.17, 0.07), (0.32, 0.22, 0.08)),
                   roof=((0.18, 0.17, 0.17), (0.24, 0.22, 0.21)), snow=False, leaves=True, haze=1.0),
    'winter': dict(label='Winter', date='Jan 12', decl=-21.7,
                   canopy=((0.3, 0.3, 0.3), (0.3, 0.3, 0.3)), canopy_b=((0.3, 0.3, 0.3), (0.3, 0.3, 0.3)),
                   ground=((0.78, 0.80, 0.85), (0.90, 0.92, 0.96)),
                   roof=((0.80, 0.82, 0.86), (0.92, 0.93, 0.96)), snow=True, leaves=False, haze=0.8),
}
TIMES = ['morning', 'midday', 'golden', 'night']
TIME_LABELS = {'morning': 'Morning', 'midday': 'Midday', 'golden': 'Golden hour', 'night': 'Evening'}

# ----------------------------------------------------------------------------- solar geometry

def sun_position(decl, hour):
    """elevation, azimuth (deg, azimuth clockwise from north) for solar time 'hour'."""
    phi, d = math.radians(LAT), math.radians(decl)
    H = math.radians(15 * (hour - 12))
    el = math.asin(math.sin(phi) * math.sin(d) + math.cos(phi) * math.cos(d) * math.cos(H))
    az = math.atan2(math.sin(H), math.cos(H) * math.sin(phi) - math.tan(d) * math.cos(phi))
    return math.degrees(el), (math.degrees(az) + 180) % 360


def hour_for_elevation(decl, target, afternoon=True):
    lo, hi = (12.0, 21.0) if afternoon else (3.0, 12.0)
    for _ in range(60):
        mid = (lo + hi) / 2
        e = sun_position(decl, mid)[0]
        if (e > target) == afternoon:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def key_hours(decl):
    return [9.0, 12.5, hour_for_elevation(decl, 7.0), hour_for_elevation(decl, -10.0)]


def solar_hour(season, t):
    hs = key_hours(SEASONS[season]['decl'])
    t = max(0.0, min(3.0, t))
    i = min(int(t), 2); f = t - i
    return hs[i] + (hs[i + 1] - hs[i]) * f


def lerp(a, b, f):
    return a + (b - a) * f


def curve(t, vals):
    t = max(0.0, min(3.0, t)); i = min(int(t), 2); f = t - i
    f = f * f * (3 - 2 * f)
    return lerp(vals[i], vals[i + 1], f)


def params(season, t):
    S = SEASONS[season]
    hour = solar_hour(season, t)
    el, az = sun_position(S['decl'], hour)
    # direction toward the sun in world space (east = -X, north = -Y)
    tx = -math.sin(math.radians(az)) * math.cos(math.radians(el))
    ty = -math.cos(math.radians(az)) * math.cos(math.radians(el))
    tz = math.sin(math.radians(el))
    warm = max(0.0, min(1.0, el / 30.0))
    sun_color = (1.0, lerp(0.55, 0.95, warm), lerp(0.28, 0.88, warm))
    sun_energy = 4.2 * max(0.0, min(1.0, math.sin(math.radians(max(el, 0))) * 2.6)) * (0.85 if S['snow'] else 1.0)
    return dict(
        hour=hour, elevation=el, azimuth=az, toward=(tx, ty, tz),
        sun_energy=sun_energy, sun_color=sun_color,
        sky_strength=0.11 * S['haze'] ** 0.2,
        night_strength=curve(t, [0.0, 0.0, 0.15, 1.0]),
        interior=curve(t, [0.55, 0.45, 0.85, 1.0]),
        window_glow=curve(t, [0.0, 0.0, 0.25, 1.0]),
        street_glow=curve(t, [0.0, 0.0, 0.15, 1.0]),
        fire_table=curve(t, [0.0, 0.0, 1.0, 1.0]),
        exposure=curve(t, [0.0, -0.25, 0.05, 0.35]) + (-0.2 if S['snow'] else 0.0),
    )

# ----------------------------------------------------------------------------- world

def build_world(scene):
    world = bpy.data.worlds.new('Omaha Sky'); scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    out = nt.nodes['World Output']; bg = nt.nodes['Background']; bg.name = 'Sky BG'
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.name = 'Sky'
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.altitude = 330.0     # Omaha elevation (m)
    nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
    night = nt.nodes.new('ShaderNodeBackground'); night.name = 'Night BG'
    night.inputs['Color'].default_value = (0.010, 0.016, 0.035, 1)
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(bg.outputs['Background'], add.inputs[0]); nt.links.new(night.outputs['Background'], add.inputs[1])
    nt.links.new(add.outputs['Shader'], out.inputs['Surface'])
    sun_d = bpy.data.lights.new('Sun', 'SUN'); sun_d.angle = math.radians(0.8)
    sun = bpy.data.objects.new('Sun', sun_d); link(sun, 'Lighting')
    return world


# ----------------------------------------------------------------------------- exterior

def _deciduous_proto(name, rnd, mat_bark, mat_canopy, height):
    trunk = bpy.data.meshes.new(name + ' Trunk')
    vs, fs = [], []
    def add_cyl(x0, y0, z0, x1, y1, z1, r0, r1, n=6):
        base = len(vs)
        ax = (x1 - x0, y1 - y0, z1 - z0)
        L = math.sqrt(sum(a * a for a in ax))
        ux = (ax[0] / L, ax[1] / L, ax[2] / L)
        # perpendicular basis
        p = (1, 0, 0) if abs(ux[2]) > 0.5 else (0, 0, 1)
        e1 = (ux[1] * p[2] - ux[2] * p[1], ux[2] * p[0] - ux[0] * p[2], ux[0] * p[1] - ux[1] * p[0])
        l1 = math.sqrt(sum(a * a for a in e1)); e1 = tuple(a / l1 for a in e1)
        e2 = (ux[1] * e1[2] - ux[2] * e1[1], ux[2] * e1[0] - ux[0] * e1[2], ux[0] * e1[1] - ux[1] * e1[0])
        for (cx, cy, cz, r) in ((x0, y0, z0, r0), (x1, y1, z1, r1)):
            for i in range(n):
                a = 2 * math.pi * i / n
                vs.append((cx + r * (math.cos(a) * e1[0] + math.sin(a) * e2[0]),
                           cy + r * (math.cos(a) * e1[1] + math.sin(a) * e2[1]),
                           cz + r * (math.cos(a) * e1[2] + math.sin(a) * e2[2])))
        for i in range(n):
            fs.append((base + i, base + (i + 1) % n, base + n + (i + 1) % n, base + n + i))
    h = height
    add_cyl(0, 0, 0, 0, 0, h * 0.45, h * 0.035, h * 0.025)
    for k in range(5):                       # main limbs
        a = k * 2 * math.pi / 5 + rnd.uniform(-0.3, 0.3)
        ex, ey = math.cos(a) * h * 0.28, math.sin(a) * h * 0.28
        ez = h * rnd.uniform(0.75, 0.95)
        add_cyl(0, 0, h * 0.40, ex, ey, ez, h * 0.02, h * 0.007)
        for j in range(3):                   # twigs (visible when bare)
            b = a + rnd.uniform(-0.9, 0.9)
            add_cyl(ex * 0.7, ey * 0.7, ez * 0.88, ex * 0.7 + math.cos(b) * h * 0.16,
                    ey * 0.7 + math.sin(b) * h * 0.16, ez + h * rnd.uniform(0.0, 0.12), h * 0.006, h * 0.002, 4)
    trunk.from_pydata(vs, [], fs); trunk.update(); trunk.materials.append(mat_bark)
    canopies = []
    for k in range(4):
        me = leafy(h * rnd.uniform(0.17, 0.24), mat_canopy, f'{name} Canopy {k}', rnd.randint(0, 999))
        a = k * math.pi / 2 + rnd.uniform(-0.4, 0.4)
        off = (math.cos(a) * h * 0.14, math.sin(a) * h * 0.14, h * rnd.uniform(0.68, 0.85))
        canopies.append((me, off))
    canopies.append((leafy(h * 0.25, mat_canopy, f'{name} Canopy top', rnd.randint(0, 999)), (0, 0, h * 0.9)))
    return trunk, canopies


def leafy(r, mat, name, seed, subdiv=3, amp=0.35):
    """icosphere pushed around by fractal noise -> clumpy foliage silhouette"""
    me = ico(r, subdiv, mat, name)
    off = mathutils.Vector((seed * 1.37, seed * 0.71, seed * 2.13))
    for v in me.vertices:
        n = mathutils.noise.fractal(v.co * (2.2 / r) + off, 0.6, 2.2, 4)
        v.co *= 1 + amp * n
    me.update()
    return me


def place_tree(proto, x, y, z, rot, s, cname_trunk='Exterior Trees', cname_canopy='Exterior Canopies'):
    trunk, canopies = proto
    o = bpy.data.objects.new('Tree', trunk); o.location = (x, y, z); o.rotation_euler = (0, 0, rot); o.scale = (s, s, s)
    link(o, cname_trunk)
    for me, off in canopies:
        c = bpy.data.objects.new('Tree Canopy', me)
        ca, sa = math.cos(rot), math.sin(rot)
        c.location = (x + (off[0] * ca - off[1] * sa) * s, y + (off[0] * sa + off[1] * ca) * s, z + off[2] * s)
        c.scale = (s, s, s * 0.85)
        link(c, cname_canopy)


def window_material(name, facade, lit=(1.0, 0.72, 0.42), cell=(1.6, 1.4)):
    """dark glass by day; random warm lit windows at night via brick cells (strength input 'Glow')."""
    m = principled(name, (0.02, 0.025, 0.03), 0.08)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0.0
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Brick Width'].default_value = cell[0]; br.inputs['Row Height'].default_value = cell[1]
    br.inputs['Mortar Size'].default_value = 0.0
    br.inputs['Bias'].default_value = 0.55
    br.inputs['Color1'].default_value = (*lit, 1); br.inputs['Color2'].default_value = (0, 0, 0, 1)
    nt.links.new(tex_coord(nt), br.inputs['Vector'])
    nt.links.new(br.outputs['Color'], b.inputs['Emission Color'])
    v = nt.nodes.new('ShaderNodeValue'); v.name = 'Glow'; v.outputs[0].default_value = 0.0
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.9
    nt.links.new(v.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], b.inputs['Emission Strength'])
    return m


def glow_material(name, color, strength):
    m = emissive(name, color, strength)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    v = nt.nodes.new('ShaderNodeValue'); v.name = 'Glow'; v.outputs[0].default_value = 0.0
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = strength
    nt.links.new(v.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], b.inputs['Emission Strength'])
    return m


def seasonal_material(name, rough=0.8):
    m = noisy(name, (0.1, 0.2, 0.05), (0.15, 0.25, 0.07), 2.5, (1, 1, 1), rough)
    return m


def set_ramp(mat, c1, c2):
    for n in mat.node_tree.nodes:
        if n.type == 'VALTORGB':
            n.color_ramp.elements[0].color = (*c1, 1); n.color_ramp.elements[1].color = (*c2, 1)
            break
    mat.diffuse_color = (*c1, 1)


def build_exterior(rnd_seed=11):
    rnd = random.Random(rnd_seed)
    EX = 'Exterior'
    G = GROUND_Z
    ground = seasonal_material('Season Ground', 1.0)
    ground.node_tree.nodes['Noise Texture'].inputs['Scale'].default_value = 0.08
    canopy = seasonal_material('Season Canopy', 0.75)
    canopy_b = seasonal_material('Season Canopy B', 0.75)
    for mat in (canopy, canopy_b):
        mat.node_tree.nodes['Noise Texture'].inputs['Scale'].default_value = 3.0
        mat.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.0
    roof = seasonal_material('Season Roof', 0.85)
    bark = noisy('Bark', (0.07, 0.055, 0.045), (0.13, 0.10, 0.08), 20, (1, 1, 6), 0.9)
    asphalt = noisy('Asphalt', (0.045, 0.045, 0.048), (0.07, 0.07, 0.072), 30, (1, 1, 1), 0.85)
    concrete = noisy('Sidewalk Concrete', (0.42, 0.41, 0.39), (0.50, 0.49, 0.46), 12, (1, 1, 1), 0.9)
    brick = noisy('Omaha Red Brick', (0.30, 0.11, 0.06), (0.40, 0.17, 0.09), 1.5, (1, 1, 1), 0.9)
    brick2 = noisy('Buff Brick', (0.50, 0.40, 0.28), (0.58, 0.48, 0.34), 1.5, (1, 1, 1), 0.9)
    stone = noisy('Limestone', (0.58, 0.55, 0.50), (0.66, 0.63, 0.57), 1.0, (1, 1, 1), 0.85)
    tower_glass = principled('Tower Glass', (0.10, 0.14, 0.18), 0.08, 0.6)
    win = window_material('Neighbour Windows', None)
    tower_win = window_material('Tower Windows', None, (1.0, 0.85, 0.65), (1.5, 1.0))
    street_glow = glow_material('Street Lamp Glow', (1.0, 0.75, 0.45), 20.0)
    car_mats = [principled(f'Car Paint {i}', c, 0.25, 0.5, **{'Coat Weight': 1.0}) for i, c in enumerate(
        [(0.02, 0.02, 0.022), (0.6, 0.6, 0.62), (0.25, 0.03, 0.03), (0.05, 0.08, 0.15), (0.75, 0.75, 0.73)])]
    car_glass = principled('Car Glass', (0.01, 0.012, 0.015), 0.05)
    snow = noisy('Snow', (0.86, 0.88, 0.93), (0.95, 0.96, 0.99), 6, (1, 1, 1), 0.6, bump=0.2)
    conifer = noisy('Conifer', (0.02, 0.07, 0.03), (0.04, 0.10, 0.04), 6, (1, 1, 1), 0.8)
    bare_mass = noisy('Bare Canopy Mass', (0.16, 0.13, 0.11), (0.24, 0.20, 0.17), 3, (1, 1, 1), 0.95)

    # ground plane, street, sidewalks (street runs east-west below the balcony)
    boxm(-900, -300, G - 0.2, 900, 1500, G, ground, EX, 'Ground')
    boxm(-900, 1.5, G, 900, 6.0, G + 0.12, concrete, EX, 'Sidewalk North')
    boxm(-900, 6.0, G, 900, 17.0, G + 0.02, asphalt, EX, 'Street')
    boxm(-900, 17.0, G, 900, 21.5, G + 0.12, concrete, EX, 'Sidewalk South')
    for x in range(-200, 200, 6):
        boxm(x, 11.45, G + 0.021, x + 3, 11.55, G + 0.022, MATS.get('Lane Paint') or principled('Lane Paint', (0.7, 0.6, 0.2), 0.6), EX, 'Lane Dash')
    boxm(-900, -40, G, 900, 1.5, G + 0.05, concrete, EX, 'Ground Floor Patio')
    # this building's lower facade (below the balcony slab) so the view down reads correctly
    boxm(-12, -30, G, 26, 0.0, -0.40, MATS.get('Facade Stone') or stone, EX, 'Building Base')
    for z in range(0, 3):
        boxm(-10, 0.0, G + 1.0 + z * 3.6, 24, 0.05, G + 3.2 + z * 3.6, win, EX, 'Lower Floor Glazing')

    # street trees + street lights both sides
    protos = [_deciduous_proto(f'Tree Proto {i}', rnd, bark, canopy if i < 3 else canopy_b, 9.0) for i in range(4)]
    for side_y in (3.8, 19.5):
        for x in range(-90, 110, 9):
            p = protos[rnd.randrange(4)]
            place_tree(p, x + rnd.uniform(-1, 1), side_y + rnd.uniform(-0.3, 0.3), G + 0.12, rnd.uniform(0, 6.28), rnd.uniform(0.85, 1.15))
        for x in range(-85, 110, 18):
            boxm(x - 0.08, side_y + 1.0 - 0.08, G, x + 0.08, side_y + 1.0 + 0.08, G + 6.0, MATS['Matte Black Metal'] if 'Matte Black Metal' in MATS else bark, EX, 'Lamp Post')
            cylm(x, side_y + 1.0, 0.25, G + 5.9, G + 6.1, street_glow, EX, 'Street Lamp Head', 12)
            d = bpy.data.lights.new('Street Light', 'POINT'); d.energy = 0; d.color = (1.0, 0.75, 0.45)
            d['base'] = 600.0; d['group'] = 'street'
            o = bpy.data.objects.new('Street Light', d); o.location = (x, side_y + 1.0, G + 5.6); link(o, 'Exterior Lights')
    # parked & driving cars
    for i in range(16):
        x = -60 + i * 8 + rnd.uniform(-2, 2)
        y = rnd.choice([7.2, 15.8]) if i % 3 else rnd.choice([9.8, 13.2])
        m = rnd.choice(car_mats)
        boxm(x - 2.2, y - 0.9, G + 0.3, x + 2.2, y + 0.9, G + 0.95, m, EX, 'Car Body', 0.12)
        boxm(x - 1.2, y - 0.8, G + 0.95, x + 1.0, y + 0.8, G + 1.45, car_glass, EX, 'Car Cabin', 0.1)
        boxm(x - 1.9, y - 0.82, G, x + 1.9, y + 0.82, G + 0.3, car_glass, EX, 'Tyres')

    # across-the-street: Old-Market-style brick warehouse lofts (3-6 storeys)
    x = -110
    while x < 120:
        w = rnd.uniform(14, 26); h = rnd.choice([11, 14.5, 18, 21.5])
        d = rnd.uniform(18, 28); y0 = 23.0
        mat = rnd.choice([brick, brick, brick2, stone])
        boxm(x, y0, G, x + w, y0 + d, G + h, mat, EX, 'Loft Building')
        boxm(x - 0.3, y0 - 0.3, G + h, x + w + 0.3, y0 + 0.6, G + h + 0.8, stone, EX, 'Cornice')
        boxm(x + 0.3, y0 + 0.6, G + h - 0.05, x + w - 0.3, y0 + d - 0.3, G + h + 0.02, roof, EX, 'Flat Roof')
        for k in range(int(h / 3.6)):
            z = G + 1.2 + k * 3.6
            boxm(x + 1.0, y0 - 0.06, z, x + w - 1.0, y0, z + 2.0, win, EX, 'Loft Windows')
            for pier in range(int((w - 2) / 2.2) + 1):          # brick piers between windows
                px = x + 1.0 + pier * 2.2
                boxm(px, y0 - 0.12, z - 0.1, px + 0.45, y0 - 0.05, z + 2.1, mat, EX, 'Pier')
        if rnd.random() < 0.4:                                  # rooftop water tank / mechanical
            boxm(x + w * 0.3, y0 + 4, G + h, x + w * 0.3 + 3, y0 + 7, G + h + 2.2, concrete, EX, 'Rooftop Mech')
        x += w + rnd.uniform(0.0, 4.0)

    # mid-distance: mixed houses with pitched roofs and mature tree canopy (Dundee / Midtown feel)
    def house(cx, cy, s):
        w, d, h = 9 * s, 11 * s, 6.5 * s
        mat = rnd.choice([brick, brick2, stone, concrete])
        boxm(cx - w / 2, cy - d / 2, G, cx + w / 2, cy + d / 2, G + h, mat, EX, 'House')
        v = [(cx - w / 2 - 0.4, cy - d / 2 - 0.4, G + h), (cx + w / 2 + 0.4, cy - d / 2 - 0.4, G + h),
             (cx + w / 2 + 0.4, cy + d / 2 + 0.4, G + h), (cx - w / 2 - 0.4, cy + d / 2 + 0.4, G + h),
             (cx, cy - d / 2 - 0.4, G + h + 3.2 * s), (cx, cy + d / 2 + 0.4, G + h + 3.2 * s)]
        f = [(0, 1, 4), (3, 5, 2), (0, 4, 5, 3), (1, 2, 5, 4)]
        mesh_obj('Pitched Roof', v, f, roof, EX)
        boxm(cx - w / 2 + 1, cy - d / 2 - 0.05, G + 1.5, cx + w / 2 - 1, cy - d / 2, G + 2.7, win, EX, 'House Windows')
    for i in range(70):
        cx = rnd.uniform(-220, 260); cy = rnd.uniform(70, 260)
        house(cx, cy, rnd.uniform(0.9, 1.3))
    for i in range(140):
        cx = rnd.uniform(-260, 300); cy = rnd.uniform(55, 300)
        place_tree(protos[rnd.randrange(4)], cx, cy, G, rnd.uniform(0, 6.28), rnd.uniform(1.2, 1.9))
    # far canopy belt (Omaha's tree-covered horizon); bare-branch masses replace it in winter
    for i in range(170):
        cx = rnd.uniform(-700, 800); cy = rnd.uniform(300, 900)
        r = rnd.uniform(8, 16)
        me = leafy(r, canopy if rnd.random() < 0.7 else canopy_b, 'Far Canopy', i, subdiv=2, amp=0.3)
        o = bpy.data.objects.new('Far Canopy', me); o.location = (cx, cy, G + r * 0.6); o.scale = (1, 1, 0.6)
        link(o, 'Exterior Canopies')
        me2 = ico(r * 0.95, 1, bare_mass, 'Far Bare Mass', noise=0.25, seed=i)
        o2 = bpy.data.objects.new('Far Bare Mass', me2); o2.location = (cx, cy, G + r * 0.55); o2.scale = (1, 1, 0.55)
        link(o2, 'Exterior Winter')
    for i in range(40):                                     # evergreens stay green all year
        cx = rnd.uniform(-250, 300); cy = rnd.uniform(60, 280); h = rnd.uniform(8, 15)
        for k in range(3):
            cylm(cx, cy, h * (0.28 - k * 0.07), G + h * (0.15 + k * 0.25), G + h * (0.55 + k * 0.22), conifer, EX,
                 'Evergreen', 10, r_top=0.02)
    # distant downtown skyline to the south-east (generic towers)
    for i in range(16):
        cx = rnd.uniform(-1400, -500); cy = rnd.uniform(1300, 1700)
        w = rnd.uniform(25, 45); h = rnd.choice([45, 60, 75, 95, 120, 140])
        boxm(cx, cy, G, cx + w, cy + w, G + h, rnd.choice([tower_glass, stone, tower_win]), EX, 'Skyline Tower')
        boxm(cx + 1, cy - 0.3, G + 3, cx + w - 1, cy, G + h - 3, tower_win, EX, 'Skyline Windows')
    # winter: snow on balcony, rail and the slab edge
    WI = 'Exterior Winter'
    boxm(15.1 * F, 0.05, -0.035, 45.5 * F, -11.1 * F, 0.005, snow, WI, 'Balcony Snow')
    boxm(15.1 * F, -0.25 * F, 1.11, 45.5 * F, -0.55 * F, 1.14, snow, WI, 'Rail Snow')
    for side_y in (3.8, 19.5):
        boxm(-900, side_y - 2.0, G + 0.12, 900, side_y + 1.6, G + 0.2, snow, WI, 'Snow Bank')
    return dict(ground=ground, canopy=canopy, canopy_b=canopy_b, roof=roof)

# ----------------------------------------------------------------------------- apply / animate

def _glow_nodes():
    out = []
    for m in bpy.data.materials:
        if m.node_tree and 'Glow' in m.node_tree.nodes:
            out.append((m.name, m.node_tree.nodes['Glow']))
    return out


def set_season(season):
    S = SEASONS[season]
    set_ramp(bpy.data.materials['Season Ground'], *S['ground'])
    set_ramp(bpy.data.materials['Season Canopy'], *S['canopy'])
    set_ramp(bpy.data.materials['Season Canopy B'], *S['canopy_b'])
    set_ramp(bpy.data.materials['Season Roof'], *S['roof'])
    for name, vis in (('Exterior Canopies', S['leaves']), ('Exterior Winter', S['snow'])):
        c = bpy.data.collections.get(name)
        if c:
            c.hide_render = not vis; c.hide_viewport = not vis
    # balcony planters follow the season
    for nm, col in (('Season Planting', {'spring': (0.18, 0.35, 0.08), 'summer': (0.08, 0.20, 0.04),
                                         'fall': (0.45, 0.30, 0.10), 'winter': (0.35, 0.30, 0.22)}[season]),):
        m = bpy.data.materials.get(nm)
        if m:
            set_ramp(m, col, tuple(min(1, c * 1.3) for c in col))


def apply_time(scene, season, t, frame=None):
    """set (and optionally keyframe at 'frame') everything that depends on time of day."""
    P = params(season, t)
    sun = bpy.data.objects['Sun']
    from mathutils import Vector
    tw = Vector(P['toward'])
    sun.rotation_euler = (-tw).to_track_quat('-Z', 'Y').to_euler()
    sun.data.energy = P['sun_energy']; sun.data.color = P['sun_color']
    nt = scene.world.node_tree
    sky = nt.nodes['Sky']
    sky.sun_elevation = math.radians(P['elevation'])
    sky.sun_rotation = math.atan2(P['toward'][0], P['toward'][1]) % (2 * math.pi)
    nt.nodes['Sky BG'].inputs['Strength'].default_value = P['sky_strength']
    nt.nodes['Night BG'].inputs['Strength'].default_value = P['night_strength']
    for o in scene.objects:
        if o.type == 'LIGHT' and 'base' in o.data:
            g = o.data.get('group', 'interior')
            mult = {'interior': P['interior'], 'street': P['street_glow'], 'firetable': P['fire_table'],
                    'accent': max(0.6, P['interior'])}.get(g, 1.0)
            o.data.energy = o.data['base'] * mult
            if frame is not None:
                o.data.keyframe_insert('energy', frame=frame)
    for name, node in _glow_nodes():
        key = 'street_glow' if 'Street' in name else 'fire_table' if 'Fire Table' in name else 'window_glow'
        node.outputs[0].default_value = P[key]
        if frame is not None:
            node.outputs[0].keyframe_insert('default_value', frame=frame)
    scene.view_settings.exposure = P['exposure']
    if frame is not None:
        sun.keyframe_insert('rotation_euler', frame=frame)
        sun.data.keyframe_insert('energy', frame=frame); sun.data.keyframe_insert('color', frame=frame)
        sky.keyframe_insert('sun_elevation', frame=frame); sky.keyframe_insert('sun_rotation', frame=frame)
        nt.nodes['Sky BG'].inputs['Strength'].keyframe_insert('default_value', frame=frame)
        nt.nodes['Night BG'].inputs['Strength'].keyframe_insert('default_value', frame=frame)
        scene.view_settings.keyframe_insert('exposure', frame=frame)
    return P


def clear_time_animation(scene):
    for idb in [bpy.data.objects.get('Sun'), scene.world, scene] + list(bpy.data.lights) + list(bpy.data.materials):
        if idb is None:
            continue
        ad = getattr(idb, 'animation_data', None)
        if ad:
            idb.animation_data_clear()
        nt = getattr(idb, 'node_tree', None)
        if nt is not None and nt.animation_data:
            nt.animation_data_clear()
    if bpy.data.objects.get('Sun') and bpy.data.objects['Sun'].data.animation_data:
        bpy.data.objects['Sun'].data.animation_data_clear()
