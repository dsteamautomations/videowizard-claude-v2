"""One Resolve timeline from the delivery bundle (design/16 §1, design/17 §3). Targets DaVinci Resolve 21.1.1 scripting (DaVinciResolveScript):
ImportMedia (idempotent by path), CreateEmptyTimeline, AppendToTimeline (mediaType 1 video-only), SetProperty ZoomX/ZoomY/Pan/Tilt/RotationAngle,
AddMarker, SetClipColor, Export DRT, reopen the DRT and compare per event. VW2_RESOLVE_FAKE=1 uses an in-memory adapter (tests, dry runs)."""
import json
import os
import re
import sys
from fractions import Fraction
from pathlib import Path

COLOURS = {'Blue': 'Blue', 'Green': 'Green'}


class FakeAdapter:
    """Records the calls a real Resolve would receive and answers the readback from them; writes a small XML DRT."""
    def __init__(self):
        self.imported, self.items, self.markers, self.props = {}, [], [], {}

    def check(self):
        return {'resolve': 'fake', 'version': '21.1.1-fake', 'scripting': True}

    def project(self, name, timeline):
        self.name, self.fps = name, timeline['fps']
        return name

    def import_media(self, paths):
        out = []
        for p in paths:
            self.imported.setdefault(str(p), {'path': str(p)})
            out.append(self.imported[str(p)])
        return out

    def timeline(self, name):
        self.tl = name
        return name

    def append(self, item, start, end, record, track=1, media_type=1):
        row = {'path': item['path'], 'start': start, 'end': end, 'record': record, 'track': track, 'media_type': media_type}
        self.items.append(row)
        return row

    def set_property(self, item, props):
        self.props[id(item)] = props
        item.update(props)

    def marker(self, frame, colour, name, note, duration=1):
        self.markers.append({'frame': frame, 'colour': colour, 'name': name, 'note': note})

    def export_drt(self, path):
        clip = lambda i: f'<clipitem><name>{Path(i["path"]).name}</name><start>{i["record"]}</start><end>{i["record"] + (i["end"] - i["start"])}</end><in>{i["start"]}</in><out>{i["end"]}</out></clipitem>'
        Path(path).write_text('<?xml version="1.0"?><xmeml version="5"><sequence><name>' + self.tl + '</name><media><video><track>'
                              + ''.join(clip(i) for i in self.items if i['media_type'] == 1) + '</track></video><audio><track>'
                              + ''.join(clip(i) for i in self.items if i['media_type'] == 2) + '</track></audio></media></sequence></xmeml>', encoding='utf-8')
        return path

    def reopen(self, drt_path):
        txt = Path(drt_path).read_text(encoding='utf-8')
        out = []
        for track, body in re.findall(r'<(video|audio)><track>(.*?)</track></\1>', txt):
            out += [{'track': track, 'record_in': int(m.group(1)), 'record_out': int(m.group(2)), 'source_in': int(m.group(3)), 'source_out': int(m.group(4))}
                    for m in re.finditer(r'<start>(\d+)</start><end>(\d+)</end><in>(\d+)</in><out>(\d+)</out>', body)]
        return out

    def export_project(self, path):
        Path(path).write_bytes(b'fake project export')
        return path

    def import_timeline(self, path, name):   # design/107 slice 3: the whole edit in one import
        import handoff
        self.tl, self.cuts = name, handoff.read_timeline(Path(path).read_bytes().decode('utf-8'), self.fps)[0]
        return name

    def readback(self):
        return self.cuts


class ResolveAdapter:
    def __init__(self):
        try:
            import DaVinciResolveScript as dvr
        except ImportError:
            candidates = ['/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules', 'C:/ProgramData/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Modules']
            for c in candidates:
                if Path(c).exists():
                    sys.path.append(c)
            import DaVinciResolveScript as dvr
        self.resolve = dvr.scriptapp('Resolve')
        if not self.resolve:
            raise SystemExit('Resolve is not running or scripting is disabled (Preferences > System > General > External scripting: Local).')
        self.pm = self.resolve.GetProjectManager()

    def check(self):
        return {'resolve': 'live', 'version': self.resolve.GetVersionString(), 'scripting': True, 'product': self.resolve.GetProductName()}

    def project(self, name, timeline):
        p = self.pm.LoadProject(name) or self.pm.CreateProject(name)
        if not p:
            raise SystemExit(f'Could not open or create project {name}.')
        for k, v in (('timelineFrameRate', str(timeline['fps'])), ('timelineResolutionWidth', str(timeline['width'])), ('timelineResolutionHeight', str(timeline['height']))):
            p.SetSetting(k, v)
        self.p, self.mp = p, p.GetMediaPool()
        return p.GetUniqueId()

    def import_media(self, paths):
        existing = {}
        for item in self.mp.GetRootFolder().GetClipList() or []:
            existing[item.GetClipProperty('File Path')] = item
        missing = [str(p) for p in paths if str(p) not in existing]
        if missing:
            for item in self.mp.ImportMedia(missing) or []:
                existing[item.GetClipProperty('File Path')] = item
        return [{'path': str(p), 'item': existing.get(str(p))} for p in paths]

    def timeline(self, name):
        for i in range(1, int(self.p.GetTimelineCount()) + 1):
            t = self.p.GetTimelineByIndex(i)
            if t.GetName() == name:
                raise SystemExit(f'Timeline {name} already exists; a dispatched import is never replayed. Inspect or close it.')
        self.tl = self.mp.CreateEmptyTimeline(name)
        return name

    def append(self, item, start, end, record, track=1, media_type=1):
        res = self.mp.AppendToTimeline([{'mediaPoolItem': item['item'], 'startFrame': start, 'endFrame': end - 1, 'trackIndex': track, 'recordFrame': record, 'mediaType': media_type}])
        if not res:
            raise SystemExit(f"AppendToTimeline failed for {item['path']} at record {record}.")
        return res[0]

    def set_property(self, item, props):
        for k, v in props.items():
            item.SetProperty(k, v)

    def marker(self, frame, colour, name, note, duration=1):
        self.tl.AddMarker(frame, COLOURS.get(colour, 'Blue'), name, note, duration)

    def export_drt(self, path):
        if not self.tl.Export(str(path), self.resolve.EXPORT_DRT):
            raise SystemExit('DRT export failed.')
        return path

    def reopen(self, drt_path):
        t = self.mp.ImportTimelineFromFile(str(drt_path), {'timelineName': self.tl.GetName() + '-verify'})
        if not t:
            raise SystemExit('DRT reopen failed.')
        out = []
        for track in ('video', 'audio'):
            for it in t.GetItemListInTrack(track, 1) or []:
                out.append({'track': track, 'record_in': it.GetStart(), 'record_out': it.GetEnd(), 'source_in': it.GetLeftOffset(), 'source_out': it.GetLeftOffset() + it.GetDuration()})
        return out

    def export_project(self, path):
        self.pm.ExportProject(self.p.GetName(), str(path))
        return path

    def import_timeline(self, path, name):   # design/107 slice 3
        self.tl = self.mp.ImportTimelineFromFile(str(path), {'timelineName': name, 'importSourceClips': True})
        if not self.tl:
            raise SystemExit(f'Resolve could not import {Path(path).name}.')
        self.p.SaveProject()
        return name

    def readback(self):
        out = []
        for lane, track, idx in ((1, 'video', 1), (-1, 'audio', 1)):
            for it in self.tl.GetItemListInTrack(track, idx) or []:
                mp = it.GetMediaPoolItem()
                out.append({'file': (mp.GetClipProperty('File Path') if mp else '') or it.GetName(), 'lane': lane, 'record_in': it.GetStart(), 'record_out': it.GetEnd(),
                            'source_in': it.GetLeftOffset(), 'source_out': it.GetLeftOffset() + it.GetDuration()})
        return out


def build(adapter, bundle_dir, manifest, run_code, out_dir):
    tl = manifest['timeline']
    fps = Fraction(str(tl['fps']))
    adapter.project(f'VW-{run_code}', tl)
    events = manifest['resolve_events']
    files = sorted({e['file'] for e in events if e['file']} | {'Audio/narration.mp3'})
    items = {e['path']: e for e in adapter.import_media([bundle_dir / f for f in files])}
    name = f'VW-{run_code}-master'
    adapter.timeline(name)
    expected = []
    for e in events:
        item = items[str(bundle_dir / e['file'])]
        src_fps = Fraction(e['source_fps'])
        # source frames are at source fps; Resolve wants source frames of the media item
        ti = adapter.append(item, e['source_in_frame'], e['source_out_frame'], e['record_in_frame'], 1, 1)
        props = {}
        if e['zoom'] and e['zoom'] != 1.0:
            props.update(ZoomX=e['zoom'], ZoomY=e['zoom'], Pan=e['pan'], Tilt=e['tilt'])
        if e['rotation']:
            props['RotationAngle'] = e['rotation']
        if props:
            adapter.set_property(ti, props)
        adapter.marker(e['record_in_frame'], e['marker']['colour'], e['marker']['name'], e['marker']['note'] + (f"; colour group {e['color_group']}" if e.get('color_group') else ''))
        expected.append({'record_in': e['record_in_frame'], 'record_out': e['record_out_frame'], 'source_in': e['source_in_frame'], 'source_out': e['source_out_frame']})
    narration = items[str(bundle_dir / 'Audio/narration.mp3')]
    expected_audio = []
    for p in manifest.get('narration_pieces') or [{'source_in_frame': 0, 'source_out_frame': int(expected[-1]['record_out']) if expected else 0, 'record_in_frame': 0}]:
        adapter.append(narration, p['source_in_frame'], p['source_out_frame'], p['record_in_frame'], 1, 2)   # whole frames: no fractional placement (VW10)
        expected_audio.append({'record_in': p['record_in_frame'], 'record_out': p['record_in_frame'] + p['source_out_frame'] - p['source_in_frame'],
                               'source_in': p['source_in_frame'], 'source_out': p['source_out_frame']})
    drt = adapter.export_drt(out_dir / 'Approved-timeline.drt')
    readback = adapter.reopen(drt)
    differences = []
    for track, exp_list in (('video', expected), ('audio', expected_audio)):
        got_list = [g for g in readback if g.get('track', 'video') == track]
        for i, (exp, got) in enumerate(zip(exp_list, got_list)):
            for k in ('record_in', 'record_out', 'source_in', 'source_out'):
                if int(exp[k]) != int(got.get(k, -1)):
                    differences.append({'track': track, 'event': i + 1, 'field': k, 'expected': exp[k], 'readback': got.get(k)})
        if len(got_list) != len(exp_list):
            differences.append({'track': track, 'event': None, 'field': 'count', 'expected': len(exp_list), 'readback': len(got_list)})
    project_export = adapter.export_project(out_dir / 'project.drp')
    return {'timeline': name, 'events': len(expected), 'narration_pieces': len(expected_audio), 'readback_events': len(readback), 'differences': differences, 'drt_verified': not differences,
            'drt_path': str(drt), 'project_export_path': str(project_export), 'check': adapter.check()}


def studio_import(adapter, edit_dir, manifest, code):
    """design/107 Step F, Studio: import Timeline/VW-n.fcpxml, save, export .drp and .drt into Timeline/, read back and compare with the plan at 0 frames."""
    import handoff
    edit_dir = Path(edit_dir)
    adapter.project(code, manifest['timeline'])
    adapter.import_timeline(edit_dir / 'Timeline' / f'{code}.fcpxml', code)
    drt = adapter.export_drt(edit_dir / 'Timeline' / f'{code}.drt')
    drp = adapter.export_project(edit_dir / 'Timeline' / f'{code}.drp')
    cuts = adapter.readback()
    differences = handoff.compare(cuts, manifest.get('resolve_events') or [], manifest.get('narration_pieces') or [])
    return {'timeline': code, 'events': len(manifest.get('resolve_events') or []), 'readback_events': len([c for c in cuts if c['lane'] == 1]), 'differences': differences,
            'drt_verified': not differences, 'drt': str(drt), 'drp': str(drp), 'check': adapter.check()}


def adapter():
    return FakeAdapter() if os.environ.get('VW2_RESOLVE_FAKE') == '1' else ResolveAdapter()
