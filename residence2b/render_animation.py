"""Render the walkthrough as a PNG sequence with Cycles (resumable: existing frames are skipped).
usage: python3 render_animation.py -- file.blend outdir width height samples [start end]"""
import bpy, sys, os, time
argv = sys.argv[sys.argv.index('--') + 1:]
blend, outdir, w, h, spp = argv[0], argv[1], int(argv[2]), int(argv[3]), int(argv[4])
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
start = int(argv[5]) if len(argv) > 5 else sc.frame_start
end = int(argv[6]) if len(argv) > 6 else sc.frame_end
sc.render.engine = 'CYCLES'
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
c = sc.cycles
c.device = 'CPU'; c.samples = spp; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.06
c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; c.denoising_prefilter = 'ACCURATE'
c.max_bounces = 3; c.diffuse_bounces = 2; c.glossy_bounces = 1; c.transmission_bounces = 2
c.transparent_max_bounces = 6; c.sample_clamp_indirect = 3.0
c.caustics_reflective = False; c.caustics_refractive = False
c.seed = 0; c.use_animated_seed = False   # fixed seed keeps residual noise from crawling
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'
os.makedirs(outdir, exist_ok=True)
for f in range(start, end + 1):
    path = os.path.join(outdir, f'frame_{f:04d}.png')
    if os.path.exists(path):
        continue
    sc.frame_set(f)
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f'FRAME {f} {time.time() - t:.1f}s', flush=True)
