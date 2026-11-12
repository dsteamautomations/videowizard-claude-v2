# The server's one Blender script: builds a guide from a scene description (app/guide_spec.py) and renders frames of it.
# Integration steps B to D (SK, 12 Nov 2026). The helper writes data, never code; this file is the only code Blender runs.
#
# Run:  blender -b --factory-startup --python guide_scene.py -- <scene.json> <outdir> frames=all|1,75,150 [samples=1] [size=1280x720]
# Writes g0001.png ... into <outdir> and prints "GUIDE DONE <n>" as its last line; any fault ends with "GUIDE FAILED: <why>" and exit code 1.
#
# What the building blocks reproduce (the consultant's finished film and our own runs): box people with black face and chest marks
# (front = local -Y), bar arms from the shoulder to the hand point, a prop keyed to the hand that holds it on every frame, a walk bob,
# a camera held still with a tiny handheld drift, a sun and a plain sky. Positions at every moment come from guide_spec, the same module
# the checks before spend use.
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import guide_spec as G   # noqa: E402  (standard library only)

BLACK, STRIPE = (0.03, 0.03, 0.03), (0.95, 0.85, 0.05)


def fail(why):
    print('GUIDE FAILED: ' + str(why))
    sys.exit(1)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    opt = dict(a.split('=', 1) for a in argv[2:] if '=' in a)
    spec = json.load(open(argv[0], encoding='utf-8'))
    wrong = G.problems(spec)
    if wrong:
        fail(wrong[0])   # the server checks before it queues a render; this is the last guard, never an empty scene rendered as if good
    outdir = argv[1]
    os.makedirs(outdir, exist_ok=True)
    n = int(round(spec['seconds'] * G.FPS))
    width, height = (int(x) for x in opt.get('size', '%dx%d' % G.SIZE).split('x'))
    frames = list(range(1, n + 1)) if opt.get('frames', 'all') == 'all' else [int(x) for x in opt['frames'].split(',')]
    if not frames or min(frames) < 1 or max(frames) > n:
        fail('frames run from 1 to %d' % n)

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    sc.render.fps = G.FPS
    sc.frame_start, sc.frame_end = 1, n
    mats = {}

    def mat(rgb):
        key = tuple(round(c, 3) for c in rgb)
        if key not in mats:
            m = bpy.data.materials.new('M%d' % len(mats))
            m.diffuse_color = (*key, 1)
            m.use_nodes = True
            b = m.node_tree.nodes['Principled BSDF']
            b.inputs['Base Color'].default_value = (*key, 1)
            b.inputs['Roughness'].default_value = 0.85
            mats[key] = m
        return mats[key]

    def box(name, lo, hi, rgb, parent=None):
        bpy.ops.mesh.primitive_cube_add(location=[(a + b) / 2 for a, b in zip(lo, hi)])
        o = bpy.context.object
        o.name = name
        o.scale = [(b - a) / 2 for a, b in zip(lo, hi)]
        o.data.materials.append(mat(rgb))
        if parent:
            o.parent = parent
        return o

    def empty(name):
        e = bpy.data.objects.new(name, None)
        sc.collection.objects.link(e)
        return e

    # ---- the set ----
    spun = []
    marks = spec.get('marks') or {}
    for s in spec['set']:
        if s['id'] == marks.get('band_off'):
            continue
        if s.get('shape') == 'cylinder':
            bpy.ops.mesh.primitive_cylinder_add(radius=s['radius'], depth=s['depth'], location=s['centre'])
            o = bpy.context.object
            o.name = s['id']
            if s.get('axis', 'Z') == 'X':
                o.rotation_euler = (0, math.radians(90), 0)
            elif s.get('axis') == 'Y':
                o.rotation_euler = (math.radians(90), 0, 0)
            o.data.materials.append(mat(s['colour']))
        else:
            o = box(s['id'], s['min'], s['max'], s['colour'])
        if s.get('spin'):
            spun.append((o, s['spin'], tuple(o.rotation_euler)))

    # ---- the people: boxes with face and chest marks; arms as bars ----
    people = []
    for p in spec.get('people') or []:
        root, h = empty('ROOT_' + p['id']), p['height']
        top = h - 0.27
        box('BODY_' + p['id'], (-G.BODY_W / 2, -G.BODY_D / 2, 0.0), (G.BODY_W / 2, G.BODY_D / 2, top), p['colour'], root)
        box('HEAD_' + p['id'], (-G.HEAD / 2, -G.HEAD / 2, top + 0.02), (G.HEAD / 2, G.HEAD / 2, h - 0.02), p['colour'], root)
        box('FACE_' + p['id'], (-0.07, -0.135, top + 0.1), (0.07, -0.11, top + 0.2), BLACK, root)
        box('CHEST_' + p['id'], (-0.12, -0.145, max(top - 0.45, 0.05)), (0.12, -0.13, top - 0.1), BLACK, root)
        if marks.get('stripes'):
            for sx in (-0.226, 0.22):
                box('STRIPE_' + p['id'], (sx, -0.05, 0.0), (sx + 0.006, 0.05, h - 0.02), STRIPE, root)
        arms = {}
        for side in ((p.get('hands') or {}).keys()):
            arms[side] = box('ARM_%s_%s' % (p['id'], side[0].upper()), (-0.04, -0.04, -0.5), (0.04, 0.04, 0.5), p.get('arm_colour') or p['colour'])
            arms[side].rotation_mode = 'QUATERNION'
        people.append((p, root, arms))

    props = []
    for pr in spec.get('props') or []:
        s = pr['size']
        props.append((pr, box('PROP_' + pr['id'], (-s[0] / 2, -s[1] / 2, -s[2] / 2), (s[0] / 2, s[1] / 2, s[2] / 2), pr['colour'])))

    # ---- the camera: held still, tiny handheld drift ----
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    sc.camera = cam
    cam.data.sensor_width = G.SENSOR
    cam.data.lens = float(spec['camera']['lens'])
    cam.rotation_mode = 'QUATERNION'
    cpos, caim = Vector(spec['camera']['position']), Vector(spec['camera']['aim'])

    def shake(t, a, s):
        return Vector((a * (math.sin(1.7 * t + s) + 0.5 * math.sin(4.3 * t + 2 * s)), a * 0.6 * math.sin(2.3 * t + 3 * s), a * (math.sin(2.9 * t + s) + 0.4 * math.sin(6.1 * t))))

    # ---- every moving thing keyed on every frame ----
    walked = {p['id']: 0.0 for p, _, _ in people}
    last = {}
    for f in range(1, n + 1):
        t = (f - 1) / G.FPS
        for p, root, arms in people:
            pos, yaw, speed = G.person_at(p, t)
            if p['id'] in last:
                walked[p['id']] += math.hypot(pos[0] - last[p['id']][0], pos[1] - last[p['id']][1])
            last[p['id']] = pos
            step = 0.45 + 0.3 * speed
            bob = 0.025 * abs(math.sin(math.pi * walked[p['id']] / step)) if speed > 0.2 else 0.0
            root.location = (pos[0], pos[1], pos[2] + bob)
            root.rotation_euler = (0, 0, yaw)
            root.keyframe_insert('location', frame=f)
            root.keyframe_insert('rotation_euler', frame=f)
            for side, arm in arms.items():
                a, b = Vector(G.shoulder(p, t, side)), Vector(G.hand(p, t, side))
                arm.location = (a + b) / 2
                arm.scale = (0.04, 0.04, max((b - a).length, 0.02) / 2)   # the cube primitive is 2 m across: scale is the half-size
                arm.rotation_quaternion = (b - a).to_track_quat('Z', 'Y') if (b - a).length > 1e-6 else (1, 0, 0, 0)
                for path in ('location', 'scale', 'rotation_quaternion'):
                    arm.keyframe_insert(path, frame=f)
        for pr, o in props:
            o.location = G.prop_at(spec, pr, t)
            o.keyframe_insert('location', frame=f)
        for o, spin, rest in spun:
            keys = [{'t': k['t'], 'at': (k['deg'], 0, 0)} for k in spin['keys']]
            deg = G._keys(keys, t)[0]
            r = list(rest)
            r['XYZ'.index(spin['axis'])] += math.radians(deg)
            o.rotation_euler = r
            o.keyframe_insert('rotation_euler', frame=f)
        p_ = cpos + shake(t, 0.003, 0.7)
        a_ = caim + shake(t, 0.006, 2.3)
        cam.location = p_
        cam.rotation_quaternion = (a_ - p_).to_track_quat('-Z', 'Y')
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_quaternion', frame=f)

    # ---- the light ----
    bpy.ops.object.light_add(type='SUN')
    sun = bpy.context.object
    sun.rotation_mode = 'QUATERNION'
    sun.rotation_quaternion = Vector(spec['sun']['direction']).normalized().to_track_quat('-Z', 'Y')
    sun.data.energy = float(spec['sun'].get('energy', 3.0))
    sun.data.angle = math.radians(float(spec['sun'].get('soft_deg', 0.5)))
    sc.world = bpy.data.worlds.new('w')
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (*(spec.get('sky') or (0.6, 0.62, 0.66)), 1)
    bg.inputs[1].default_value = float(spec.get('sky_strength', 0.8))

    # ---- render (the view transform is left at Blender's default: changing it washes the picture out) ----
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = width, height
    if hasattr(sc, 'eevee'):
        sc.eevee.taa_render_samples = int(opt.get('samples', 1))
    for f in frames:
        t0 = time.time()
        sc.frame_set(f)
        sc.render.filepath = os.path.join(outdir, 'g%04d.png' % f)
        bpy.ops.render.render(write_still=True)
        print('FRAMETIME', f, round(time.time() - t0, 2))
        sys.stdout.flush()
    missing = [f for f in frames if not os.path.exists(os.path.join(outdir, 'g%04d.png' % f))]
    if missing:
        fail('frames not written: %s' % missing[:5])
    print('GUIDE DONE %d' % len(frames))


try:
    main()
except SystemExit:
    raise
except Exception as exc:   # an unknown fault must never look like a finished guide
    fail('%s: %s' % (type(exc).__name__, exc))
