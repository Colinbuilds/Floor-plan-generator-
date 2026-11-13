"""Cut-away top-down render of the model (ceiling hidden) for layout review."""
import bpy, sys, math
argv = sys.argv[sys.argv.index('--') + 1:]
blend, out = argv[0], argv[1]
w = int(argv[2]) if len(argv) > 2 else 1800
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
for o in sc.objects:
    if o.name.startswith(('Ceiling', 'Soffit', 'Recessed', 'Downlight', 'Range Hood', 'Hood', 'Pendant Cord', 'Chandelier Cable')) \
            or ' Header' in o.name or o.name.startswith('Shower Arm'):
        o.hide_render = True
    if o.type == 'LIGHT' and o.data.type == 'AREA':
        o.location.z = 6.0; o.data.energy *= 3
FT = 0.3048
cx, cy = 30.25 * FT, -23.3 * FT
cd = bpy.data.cameras.new('Top'); cd.type = 'ORTHO'; cd.ortho_scale = 62 * FT
cam = bpy.data.objects.new('Top', cd); sc.collection.objects.link(cam)
cam.location = (cx, cy, 30); cam.rotation_euler = (0, 0, 0); cd.clip_end = 100
sc.camera = cam
sc.render.resolution_x = w; sc.render.resolution_y = int(w * 48 / 62)
sc.render.engine = 'CYCLES'; c = sc.cycles
c.samples = 12; c.use_denoising = True; c.max_bounces = 3; c.diffuse_bounces = 2
c.sample_clamp_indirect = 3; c.caustics_reflective = False; c.caustics_refractive = False
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
