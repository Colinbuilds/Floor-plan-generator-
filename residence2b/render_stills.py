import bpy, sys, time
argv = sys.argv[sys.argv.index('--') + 1:]
blend, outdir, w, h = argv[0], argv[1], int(argv[2]), int(argv[3])
frames = [int(f) for f in argv[4].split(',')]
engine = argv[5] if len(argv) > 5 else 'BLENDER_EEVEE'
samples = int(argv[6]) if len(argv) > 6 else 16
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = engine
sc.render.resolution_x, sc.render.resolution_y = w, h
sc.render.resolution_percentage = 100
if engine == 'CYCLES':
    c = sc.cycles
    c.samples = samples; c.use_denoising = True; c.device = 'CPU'
    c.denoiser = 'OPENIMAGEDENOISE'; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.05
    c.max_bounces = 4; c.diffuse_bounces = 3; c.glossy_bounces = 2; c.transmission_bounces = 4
    c.transparent_max_bounces = 8; c.sample_clamp_indirect = 4.0; c.use_light_tree = True
    c.caustics_reflective = False; c.caustics_refractive = False
    sc.render.use_persistent_data = True
else:
    sc.eevee.taa_render_samples = samples
    if len(argv) > 7 and argv[7] == 'fast':
        sc.eevee.use_raytracing = False
for f in frames:
    sc.frame_set(f)
    sc.render.filepath = f'{outdir}/still_{engine[:5]}_{f:04d}.png'
    t = time.time(); bpy.ops.render.render(write_still=True); print('FRAME', f, round(time.time() - t, 1), 's')
