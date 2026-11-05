# 172 — A scene for Blender: the plinth wetting (VW-18 `BEAT_06-B1-s1`), 5 Nov 2026

SK, 5 Nov evening: the Wan results "have crucial problems like the positioning of the human, what they do"; he wants a Blender-enabled setup and asks for one scene described for the Blender assistant on his system, with sample pictures. This is that scene, in Blender's own terms, taken from the VW-18 plan (scene `B06B1-plinth`, shot `BEAT_06-B1-s1`, 8.2 s, 50 fps in the film; rendered here at 24 fps). The aim: Blender fixes **where everything is, where the person faces, what the hands do and at which second**; the render then goes to the video model as the reference video (Wan: `--videos`, up to 15 s per clip) with the real photographs as the look.

Paste section 1 into the Blender assistant as it is. Section 2 says what to do with the pictures. Section 3 is what to send back.

## 1. The scene, for the Blender assistant

```
Build this scene in Blender (metric units, metres, Z up, 24 fps, frames 1 to 192 = 8 seconds). Keep every object simple: blocks and planes with flat colours are fine; the geometry, the positions, the camera and the timing are what matter. Name every object exactly as given.

GROUND
- A ground plane 20 x 20 m at Z = 0, flat colour red-brown (0.55, 0.25, 0.12). Name: ground.

THE PLINTH (the main landmark)
- A box 6.0 m long (X), 0.45 m wide (Y), 0.50 m high (Z), its base on the ground, its long axis along X, centred at X = 0, with its near face at Y = 0 (so it occupies Y from 0 to 0.45). Flat colour light grey (0.72, 0.72, 0.70) for the top, darker grey-brown (0.45, 0.42, 0.40) for the sides. Name: plinth.
- A second thin box exactly on the plinth top, 6.0 x 0.45 x 0.005 m, colour sandy (0.80, 0.70, 0.52). Name: plinth_dust. This is the dust layer; it disappears as the broom passes (see TIMING).
- A third thin box on top of that, same size, colour dark wet grey (0.30, 0.30, 0.30), hidden at the start. Name: plinth_wet. It appears where the water lands (see TIMING).

THE OTHER LANDMARKS
- A brick stack: a box 1.2 x 1.0 x 1.0 m, base on the ground, centred at X = 3.6, Y = 1.4 (behind the plinth's right end, nobody at it). Flat colour brick red (0.65, 0.28, 0.18). Name: brick_stack.
- A coconut tree: a cylinder trunk 0.3 m diameter, 7 m tall, base at X = -4.5, Y = 3.0; a sphere 2.5 m diameter on top for the crown, dark green. Name: site_tree.
- A bucket: a cylinder 0.30 m diameter, 0.32 m tall, base on the ground at X = 0.6, Y = -0.45 (on the near side of the plinth, at its foot, a little right of the middle). Flat colour blue (0.10, 0.35, 0.80). Name: bucket.
- A mug: a cylinder 0.09 m diameter, 0.10 m tall, resting inside the bucket's top at the start. Colour blue. Name: mug.
- A broom: a thin cylinder 1.2 m long, 0.03 m diameter, brown, with a cone 0.35 m long and 0.25 m wide at one end for the bristles. Name: broom. At the start it is in the worker's right hand with its bristle tip on the plinth top at X = -2.9.

THE WORKER
- One human figure 1.68 m tall. Use Blender's simplest rigged human (a Rigify human meta-rig with a basic mesh, or a mannequin of capsules parented to an armature). Shirt green (0.15, 0.50, 0.25) from shoulders to hips; lungi green with a darker check, from hips to just below the knees; skin medium brown; short black hair. Name: worker.
- Start position: standing on the ground on the NEAR side of the plinth (negative Y), feet at X = -2.9, Y = -0.55, facing +X (along the plinth, to the right), body turned about 30 degrees toward the camera, bent forward from the waist about 45 degrees, head down looking at the plinth top. Right hand holds the broom handle at 0.9 m height; the broom's bristle tip touches the plinth top at X = -2.9, Y = 0.2. Left hand on the left knee.

THE CAMERA
- Camera at X = 0.3, Y = -6.5, Z = 2.1, pointing at the point X = 0.3, Y = 0.2, Z = 0.6 (a little above eye level, looking slightly down at the plinth). Focal length 35 mm, sensor 36 mm, 16:9, 1280 x 720. The camera does not move for the whole shot. Name: shot_camera.
- Check from the camera: the plinth runs across the lower half of the frame from left to right, the worker is full figure, the brick stack is visible behind the plinth's right end, the tree is visible at the left beyond the plinth, the bucket is visible at the plinth's foot right of centre.

LIGHT
- One sun lamp from the camera's left and behind the camera: direction from azimuth 230 degrees (south-west if +Y is north), elevation 40 degrees, strength 4, warm white (1.0, 0.95, 0.85). Shadows on. A world background light grey-blue, strength 0.6. The light does not change.

TIMING (24 fps; the second is given first, the frame in brackets)
0.0-4.7 s [1-113]: SWEEPING. The worker walks slowly along the near side of the plinth from X = -2.9 to X = 0.0 (3 steps, feet always on the ground at Y = -0.55), staying bent and facing +X with the body turned toward the camera. The broom sweeps the plinth top in short strokes: each stroke 0.4 s, the bristle tip moving from the near edge (Y = 0.05) to the far edge (Y = 0.42) and back, at the X of the worker's hands. As the bristle tip passes, the plinth_dust box is cut away behind it: animate the dust box's X-length so that its left end follows the worker (the dust remains only to the right of X = worker position); the swept stretch shows the grey top.
4.7-5.5 s [113-132]: LAYING THE BROOM. The worker stops at X = 0.0, bends lower, and lays the broom on the ground at his feet, along the plinth, at X from -0.6 to 0.6, Y = -0.75. He straightens to half-bent.
5.5-6.3 s [132-151]: THE MUG. He turns a little to the bucket at X = 0.6, Y = -0.45, bends, takes the mug out of the bucket with his right hand and straightens to half-bent; the bucket stays on the ground.
6.3-8.0 s [151-192]: WATERING. Two throws. Throw 1, 6.3-7.1 s: the right arm swings from low right to high left in a flat arc over the plinth top; at 6.6 s the plinth_wet box appears over X from -2.8 to -1.2 (the water lands on the swept stretch at the left). Between throws, 7.1-7.4 s: the mug dips to the bucket and comes up. Throw 2, 7.4-8.0 s: the same arc; at 7.7 s the plinth_wet box extends to X from -2.8 to 0.2. The shot ends at 8.0 s with the worker half-bent near X = 0.0, the mug in his right hand at the end of the arc, the bucket at his feet, the broom on the ground, his head down looking at the wet plinth top.

The worker never crosses to the far side of the plinth, never turns his back to the camera, never faces the camera straight on; his feet never leave the ground; nothing is in his hands except the broom (until 5.5 s) and the mug (from 5.5 s). Only one person in the scene. No text anywhere.

OUTPUT
1. Render the animation from shot_camera: Eevee is fine, 1280 x 720, 24 fps, frames 1-192, H.264 MP4, no sound. Name: plinth_blender.mp4.
2. Render single frames from shot_camera at frames 1, 60, 113, 151 and 192 as PNG.
3. Save the .blend file.
```

## 2. The sample pictures (sent with this note)

Four pictures, the real references of this scene from VW-18, the ones the video model will use for the look. (Wan's own take of this shot from design/171 is not part of the Blender input; it is only compared with the Blender render afterwards.) Blender does not need them to build the scene; they are for the assistant (and you) to check that the blockout matches, and they can be loaded as **reference images** (Add > Image > Reference, or as the camera's background image) so the layout can be lined up against the photograph:

| File | What it is | Use in Blender |
|---|---|---|
| `env-plinth.jpg` | the scene with nobody in it, made from the plan's layout (design/171) | the camera's background image: line up the plinth, the stack and the tree with it |
| `worker_plinth__sheet__1.png` | the worker full length, neutral | the figure's height and colours |
| `technique_plinth_wetting__sheet__3.png` | the coconut broom on the plinth with the bucket | the broom's and bucket's shape and size against the plinth |
| `water_pot__sheet__1.png` | the bucket with the mug | the bucket and the mug |

Blender will not texture the figure from a photograph by itself; that is not needed. The photographs give the look later, in the video model's call.

## 3. What to send back

The MP4, the five PNG frames, and the .blend file. Then the next test is the one that matters: the Blender MP4 as Wan's `@Video1` (the first 15 s; this shot is 8 s), the photographs as `@Image1…`, and the same take text as design/171's W1a, with the sentence "follow the positions, the facing, the hands and the timing of @Video1 exactly; take the look from the photographs". That run tells us whether a 3D blockout gives the model what the cartoon could not.

## Not covered

- Only one scene described; the kiln (two people, a hand-over) and the pointing (hands only, close) follow once this one proves itself.
- Rigging and walking are the assistant's work in Blender; the figure may be a mannequin, the walk may be simple, as long as the feet stay down and the bend and facing are as written.
