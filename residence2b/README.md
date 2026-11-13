# Residence 2B – furnished Blender model & walkthrough

Generated from `The-Residences_2B-Floor-Plan.pdf` (2 Beds | 3 Baths | Den, 2,326 SF, Levels 2–6).

| Script | What it does |
|---|---|
| `trace_plan.py` | Rasterises the PDF and traces the dark wall fill into 121 wall rectangles (`plan_walls.json`). |
| `build_residence.py` | Builds the model in Blender (bpy 5.3): walls, door openings and leaves, windows, sliding doors, finishes, furniture, lighting, surroundings. Also builds the 45 s camera path and writes `camera_report.json` with clearance numbers. |
| `plot_route.py` | Top-down diagnostic of the camera route, coloured by clearance to walls and furniture. |
| `render_topdown.py` | Cut-away overhead render for checking the layout. |
| `render_stills.py` | Renders single frames for look development. |
| `render_animation.py` | Renders the walkthrough as a PNG sequence with Cycles. It can be resumed. |

## Scale
The plan is traced at 300 dpi and converted at **37.6 px = 1 ft**. That scale is calibrated against the labelled sizes: Balcony 30'-4", Bedroom 12'-10", Primary Bedroom 13'-0", Primary Bath 12'-10" × 16'-2". Ceilings are 9'-0" and doors are 7'-0".

## Rebuild
```bash
pip install bpy==5.3.0 scipy pillow
python3 trace_plan.py The-Residences_2B-Floor-Plan.pdf plan_walls.json   # optional, the JSON is committed
python3 build_residence.py Residence_2B.blend
python3 plot_route.py camera_report.json route_plan.png
python3 render_animation.py -- Residence_2B.blend frames 1920 1080 8
ffmpeg -framerate 24 -i frames/frame_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 walkthrough.mp4
```

## Camera route (24 fps, 1080 frames, about 60 m)
1. Front door, then up the entry hall.
2. Past the den, looking in through its opening.
3. Around the island and up the kitchen aisle.
4. Past the dining table, with a view over the living room and fireplace.
5. Out through the open slider onto the balcony, then back inside.
6. Primary bedroom, then a loop through the primary bath.
7. Back past the living room and down the bedroom hallway to Bedroom 2.

The camera is at 1.60 m eye height with a 20 mm lens. It keeps at least 0.30 m from every wall, door leaf, glass panel and piece of furniture, and `camera_report.json` gives the per-frame clearance.
