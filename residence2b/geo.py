"""Shared geometry + material helpers for the Residence 2B build.

Plan coordinates are FEET measured on the PDF plan (x right, y down, origin top-left).
World: X = x_ft * 0.3048, Y = -y_ft * 0.3048, Z up in metres.
Orientation: the balcony (plan top) faces SOUTH, so world +Y = south, world +X = west.
"""
import bpy, bmesh, math, random

F = 0.3048
CEIL = 2.74
DOOR_H = 2.13

COLL = {}
OBST = []   # (cx_ft, cy_ft, half_x_ft, half_y_ft, world_yaw, tag) footprints for camera clearance
MATS = {}


def reset():
    COLL.clear(); OBST.clear(); MATS.clear()


def coll(name):
    if name not in COLL:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLL[name] = c
    return COLL[name]


def add_obst(cx, cy, hx, hy, rot=0.0, tag=''):
    OBST.append((cx, cy, hx, hy, rot, tag))


def W(x, y):
    return x * F, -y * F

# ----------------------------------------------------------------------------- materials

def principled(name, color, rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    for k, v in kw.items():
        b.inputs[k].default_value = v
    m.diffuse_color = (*color, 1)
    MATS[name] = m
    return m


def tex_coord(nt, scale=(1, 1, 1), space='Object', rot=(0, 0, 0)):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    mp.inputs['Rotation'].default_value = rot
    nt.links.new(tc.outputs[space], mp.inputs['Vector'])
    return mp.outputs['Vector']


def ramp_between(nt, fac, c1, c2, positions=None):
    r = nt.nodes.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].color = (*c1, 1)
    r.color_ramp.elements[1].color = (*c2, 1)
    if positions:
        r.color_ramp.elements[0].position, r.color_ramp.elements[1].position = positions
    nt.links.new(fac, r.inputs['Fac'])
    return r.outputs['Color']


def noisy(name, color, color2, scale=4.0, stretch=(1, 1, 1), rough=0.5, metal=0.0, bump=0.0, space='Object'):
    m = principled(name, color, rough, metal)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 6
    nt.links.new(tex_coord(nt, stretch, space), nz.inputs['Vector'])
    nt.links.new(ramp_between(nt, nz.outputs['Fac'], color, color2), b.inputs['Base Color'])
    if bump:
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump
        bp.inputs['Distance'].default_value = 0.002
        nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def plank_floor(name, c1, c2, seam, width=0.24, length=2.2, rough=0.33):
    m = principled(name, c1, rough)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    v = tex_coord(nt)
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.offset = 0.41; br.offset_frequency = 1
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Brick Width'].default_value = length
    br.inputs['Row Height'].default_value = width
    br.inputs['Mortar Size'].default_value = 0.0012
    br.inputs['Color1'].default_value = (*c1, 1)
    br.inputs['Color2'].default_value = (*c2, 1)
    br.inputs['Mortar'].default_value = (*seam, 1)
    nt.links.new(v, br.inputs['Vector'])
    mp2 = nt.nodes.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (0.5, 30, 1)
    nt.links.new(v, mp2.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.5; nz.inputs['Detail'].default_value = 10
    nt.links.new(mp2.outputs['Vector'], nz.inputs['Vector'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 0.45
    nt.links.new(br.outputs['Color'], mix.inputs['A']); nt.links.new(nz.outputs['Color'], mix.inputs['B'])
    bc = nt.nodes.new('ShaderNodeBrightContrast'); bc.inputs['Bright'].default_value = 0.03
    nt.links.new(mix.outputs['Result'], bc.inputs['Color'])
    nt.links.new(bc.outputs['Color'], b.inputs['Base Color'])
    # grain-driven roughness variation + seam bump
    rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough - 0.08
    rr.inputs['To Max'].default_value = rough + 0.12
    nt.links.new(nz.outputs['Fac'], rr.inputs['Value']); nt.links.new(rr.outputs['Result'], b.inputs['Roughness'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.25
    bp.inputs['Distance'].default_value = 0.001
    nt.links.new(br.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def tile(name, c1, c2, size, rough=0.3, grout=(0.3, 0.3, 0.3), ratio=0.5):
    m = principled(name, c1, rough)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.offset = 0.5
    br.inputs['Scale'].default_value = 1.0 / size
    br.inputs['Brick Width'].default_value = 1.0
    br.inputs['Row Height'].default_value = ratio
    br.inputs['Mortar Size'].default_value = 0.003
    br.inputs['Color1'].default_value = (*c1, 1)
    br.inputs['Color2'].default_value = (*c2, 1)
    br.inputs['Mortar'].default_value = (*grout, 1)
    nt.links.new(tex_coord(nt), br.inputs['Vector'])
    nt.links.new(br.outputs['Color'], b.inputs['Base Color'])
    return m


def marble(name, base, vein, scale=1.2, rough=0.12, vein_width=0.06, base2=None):
    """veined stone: distorted wave bands -> thin veins, plus a cloudy base."""
    m = principled(name, base, rough)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    v = tex_coord(nt)
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = scale
    wv.inputs['Distortion'].default_value = 5.5; wv.inputs['Detail'].default_value = 4
    wv.inputs['Detail Scale'].default_value = 1.2
    nt.links.new(v, wv.inputs['Vector'])
    r = nt.nodes.new('ShaderNodeValToRGB'); cr = r.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = (*vein, 1)
    cr.elements[1].position = vein_width; cr.elements[1].color = (*base, 1)
    nt.links.new(wv.outputs['Fac'], r.inputs['Fac'])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; nz.inputs['Detail'].default_value = 8
    nt.links.new(v, nz.inputs['Vector'])
    cl = ramp_between(nt, nz.outputs['Fac'], base, base2 or tuple(c * 0.9 for c in base))
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1.0
    nt.links.new(r.outputs['Color'], mix.inputs['A']); nt.links.new(cl, mix.inputs['B'])
    # restore base brightness after multiply
    bc = nt.nodes.new('ShaderNodeBrightContrast'); bc.inputs['Bright'].default_value = 0.0
    nt.links.new(mix.outputs['Result'], bc.inputs['Color'])
    nt.links.new(bc.outputs['Color'], b.inputs['Base Color'])
    m.diffuse_color = (*base, 1)
    return m


def fluted(name, color, color2, flutes_per_m=40, rough=0.45):
    m = noisy(name, color, color2, 5, (1, 1, 20), rough)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_profile = 'SIN'
    wv.inputs['Scale'].default_value = flutes_per_m / 2
    nt.links.new(tex_coord(nt), wv.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6
    bp.inputs['Distance'].default_value = 0.006
    nt.links.new(wv.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def flame_material(name, color=(1.0, 0.42, 0.08), strength=6.0):
    """wispy flame sheet for vertical planes: emission fading upward, broken up by noise, rest transparent."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4.0; nz.inputs['Detail'].default_value = 4
    nt.links.new(tc.outputs['Generated'], nz.inputs['Vector'])
    # flame mask = (1 - z)^1.5 * noise, tapered at the sides
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs['Z'], inv.inputs[1])
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6
    nt.links.new(inv.outputs[0], pw.inputs[0])
    side = nt.nodes.new('ShaderNodeMath'); side.operation = 'PINGPONG'; side.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs['X'], side.inputs[0])
    sm = nt.nodes.new('ShaderNodeMath'); sm.operation = 'MULTIPLY'; sm.inputs[1].default_value = 2.0
    nt.links.new(side.outputs[0], sm.inputs[0])
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'
    nt.links.new(pw.outputs[0], m1.inputs[0]); nt.links.new(sm.outputs[0], m1.inputs[1])
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'
    nt.links.new(m1.outputs[0], m2.inputs[0]); nt.links.new(nz.outputs['Fac'], m2.inputs[1])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.12; mr.inputs['From Max'].default_value = 0.45
    nt.links.new(m2.outputs[0], mr.inputs['Value'])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1)
    v = nt.nodes.new('ShaderNodeValue'); v.name = 'Glow' if 'Table' in name else 'Strength'; v.outputs[0].default_value = 1.0
    ms = nt.nodes.new('ShaderNodeMath'); ms.operation = 'MULTIPLY'; ms.inputs[1].default_value = strength
    nt.links.new(v.outputs[0], ms.inputs[0]); nt.links.new(ms.outputs[0], em.inputs['Strength'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(mr.outputs['Result'], mx.inputs['Fac'])
    nt.links.new(tr.outputs['BSDF'], mx.inputs[1]); nt.links.new(em.outputs['Emission'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    MATS[name] = m
    return m


def flame_sheet(cx, cy, z0, length, height, along_x, mat, cname, name='Flame'):
    """a vertical quad (world metres) for flame_material; Generated coords run 0..1 across it."""
    if along_x:
        v = [(cx - length / 2, cy, z0), (cx + length / 2, cy, z0), (cx + length / 2, cy, z0 + height), (cx - length / 2, cy, z0 + height)]
    else:
        v = [(cx, cy - length / 2, z0), (cx, cy + length / 2, z0), (cx, cy + length / 2, z0 + height), (cx, cy - length / 2, z0 + height)]
    return mesh_obj(name, v, [(0, 1, 2, 3)], mat, cname)


def emissive(name, color, strength, base=None):
    m = principled(name, base or color, 0.5)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (*color, 1)
    b.inputs['Emission Strength'].default_value = strength
    return m


def glass(name, tint=(0.95, 0.97, 0.97), refl=0.12):
    """thin architectural glass (transparent + fresnel gloss, no refraction)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = (*tint, 1)
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
    lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = refl
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lw.outputs['Fresnel'], mx.inputs['Fac'])
    nt.links.new(tr.outputs['BSDF'], mx.inputs[1]); nt.links.new(gl.outputs['BSDF'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    m.diffuse_color = (*tint, 0.25)
    MATS[name] = m
    return m


def art(name, cols, scale=1.5, distortion=6, kind='WAVE'):
    m = principled(name, cols[0], 0.8)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    if kind == 'WAVE':
        t = nt.nodes.new('ShaderNodeTexWave'); t.inputs['Distortion'].default_value = distortion
        t.inputs['Detail'].default_value = 2
    else:
        t = nt.nodes.new('ShaderNodeTexVoronoi')
    t.inputs['Scale'].default_value = scale
    nt.links.new(tex_coord(nt, space='Generated'), t.inputs['Vector'])
    r = nt.nodes.new('ShaderNodeValToRGB'); cr = r.color_ramp; cr.interpolation = 'CONSTANT'
    cr.elements[0].color = (*cols[0], 1); cr.elements[1].color = (*cols[-1], 1); cr.elements[1].position = 0.85
    for i, c in enumerate(cols[1:-1]):
        e = cr.elements.new((i + 1) / len(cols) * 0.85); e.color = (*c, 1)
    nt.links.new(t.outputs['Fac' if kind == 'WAVE' else 'Distance'], r.inputs['Fac'])
    nt.links.new(r.outputs['Color'], b.inputs['Base Color'])
    return m

# ----------------------------------------------------------------------------- meshes

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
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    v, f = cube_data(x0, y0, z0, x1, y1, z1)
    return mesh_obj(name, v, f, mat, cname, bevel)


def box(x0, y0, x1, y1, z0, z1, mat, cname, name='Box', bevel=0.0, obst=False, tag=''):
    X0, Y0 = W(x0, y0); X1, Y1 = W(x1, y1)
    if obst:
        add_obst((x0 + x1) / 2, (y0 + y1) / 2, abs(x1 - x0) / 2, abs(y1 - y0) / 2, 0, tag or name)
    return boxm(X0, Y0, z0, X1, Y1, z1, mat, cname, name, bevel)


def cyl_data(r, z0, z1, n=24, rx=None, ry=None, cap=True, r_top=None):
    rx = rx or r; ry = ry or r
    k = (r_top / r) if r_top is not None else 1.0
    v = []
    for z, s in ((z0, 1.0), (z1, k)):
        for i in range(n):
            a = 2 * math.pi * i / n
            v.append((rx * s * math.cos(a), ry * s * math.sin(a), z))
    f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    if cap:
        f.append(tuple(reversed(range(n))))
        f.append(tuple(range(n, 2 * n)))
    return v, f


def cylm(cx, cy, r, z0, z1, mat, cname, name='Cyl', n=24, rx=None, ry=None, smooth=True, cap=True, r_top=None):
    v, f = cyl_data(r, z0, z1, n, rx, ry, cap, r_top)
    v = [(cx + a, cy + b, c) for a, b, c in v]
    return mesh_obj(name, v, f, mat, cname, smooth=smooth)


def cyl(x, y, r, z0, z1, mat, cname, name='Cyl', n=24, obst=False, tag='', **kw):
    X, Y = W(x, y)
    if obst:
        add_obst(x, y, r / F, r / F, 0, tag or name)
    return cylm(X, Y, r, z0, z1, mat, cname, name, n, **kw)


def sphere(cx, cy, cz, r, mat, cname, name='Sphere', sx=1, sy=1, sz=1, seg=16, mesh=None):
    if mesh is None:
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(4, seg // 2), radius=r)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        bm.to_mesh(mesh); bm.free()
        for p in mesh.polygons:
            p.use_smooth = True
        mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    ob.location = (cx, cy, cz)
    link(ob, cname)
    return ob


def ico(r, subdiv, mat, name, noise=0.0, seed=0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
    rnd = random.Random(seed)
    if noise:
        for v in bm.verts:
            v.co *= 1 + rnd.uniform(-noise, noise)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    return me


def torus(cx, cy, cz, R, r, mat, cname, name='Torus', n=48, m=12):
    v = []; f = []
    for i in range(n):
        a = 2 * math.pi * i / n
        for j in range(m):
            b = 2 * math.pi * j / m
            v.append(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
    for i in range(n):
        for j in range(m):
            f.append((i * m + j, ((i + 1) % n) * m + j, ((i + 1) % n) * m + (j + 1) % m, i * m + (j + 1) % m))
    ob = mesh_obj(name, v, f, mat, cname, smooth=True)
    ob.location = (cx, cy, cz)
    return ob


def curtain(x0, x1, y, z0, z1, mat, cname, name='Curtain', folds=None, depth=0.05):
    """sheer curtain along plan x (feet) at plan y, wavy folds."""
    X0, Y = W(x0, y); X1, _ = W(x1, y)
    n = max(8, int(abs(X1 - X0) / 0.04))
    folds = folds or max(2, int(abs(X1 - X0) / 0.12))
    v = []; f = []
    for i in range(n + 1):
        t = i / n
        x = X0 + (X1 - X0) * t
        dy = depth * math.sin(t * folds * 2 * math.pi)
        v.append((x, Y + dy, z0)); v.append((x, Y + dy, z1))
    for i in range(n):
        f.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    ob = mesh_obj(name, v, f, mat, cname, smooth=True)
    md = ob.modifiers.new('Solid', 'SOLIDIFY'); md.thickness = 0.004
    return ob


class Group:
    """Furniture built in local metres (+Y = front) placed at plan (x, y) ft facing a direction."""
    def __init__(self, name, x, y, facing, cname, hx=None, hy=None, obst=True):
        self.cname = cname
        self.empty = bpy.data.objects.new(name, None)
        self.empty.empty_display_size = 0.3
        X, Y = W(x, y)
        self.empty.location = (X, Y, 0)
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

    def torus(self, x, y, z, R, r, mat, **kw):
        return self._par(torus(x, y, z, R, r, mat, self.cname, self.name, **kw))
