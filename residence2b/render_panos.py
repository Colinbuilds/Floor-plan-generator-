"""Render equirectangular 360 panoramas for the tour (resumable).
usage: python3 render_panos.py -- file.blend outdir width samples [spot,spot...]"""
import bpy, sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
argv = sys.argv[sys.argv.index('--') + 1:]
blend, outdir, width, spp = argv[0], argv[1], int(argv[2]), int(argv[3])
bpy.ops.wm.open_mainfile(filepath=blend)
import environment as env
from tour_spots import SPOTS, variants, pano_name, T_VALUE, F, EYE
only = argv[4].split(',') if len(argv) > 4 else list(SPOTS)

sc = bpy.context.scene
env.clear_time_animation(sc)
cd = bpy.data.cameras.new('Pano'); cd.type = 'PANO'; cd.panorama_type = 'EQUIRECTANGULAR'
cd.clip_start = 0.05; cd.clip_end = 3000
cam = bpy.data.objects.new('Pano Camera', cd); sc.collection.objects.link(cam)
cam.rotation_euler = (math.pi / 2, 0, 0)      # image centre looks toward +Y (south, out the balcony)
sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = width, width // 2, 100
c = sc.cycles
c.samples = spp; c.adaptive_threshold = 0.05; c.use_denoising = True
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
os.makedirs(outdir, exist_ok=True)
cur_season = None
for spot in only:
    label, x, y, _ = SPOTS[spot]
    cam.location = (x * F, -y * F, EYE)
    for season, tod in variants(spot):
        path = os.path.join(outdir, pano_name(spot, season, tod))
        if os.path.exists(path):
            continue
        if season != cur_season:
            env.set_season(season); cur_season = season
        env.apply_time(sc, season, T_VALUE[tod])
        sc.render.filepath = path
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f'PANO {spot} {season} {tod} {time.time() - t:.1f}s', flush=True)
