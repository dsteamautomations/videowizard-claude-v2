"""design/142 R5: read-only check of the colour groups on a run's real clips (SK: VW-16's one-yard, one-day footage should come out as one group).
Run on the VM with the server's venv and environment, at deploy, with SK's approval:  python scripts/d142_looks_check.py VW-16
Reads the run's clips from storage, measures each look as the analysis worker now does, prints each clip's look and the groups. Writes nothing."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))

from app import core   # noqa: E402
from app.config import settings   # noqa: E402
from app.db import connect   # noqa: E402
from app.stage2 import looks   # noqa: E402
from app.storage import storage   # noqa: E402


def main(code):
    store = storage()
    with connect() as conn:
        run = conn.execute('select * from vw2_runs where code=%s', (code,)).fetchone()
        media = next(o for o in core.current_outputs(conn, run['id']) if o['stage'] == 'media' and o['unit'] is None)
    found = {}
    for clip in media['summary']['clips']:
        with tempfile.TemporaryDirectory(prefix='vw2-looks-') as folder:
            video = Path(folder) / 'clip.mp4'
            video.write_bytes(store.get(f"{run['id']}/media/{clip['name']}"))
            found[clip['id']] = looks.measure(video, clip.get('duration_s'), folder, settings().FFMPEG_EXECUTABLE, log='log' in str(clip.get('color_transfer') or '').lower())
        print(clip['name'], found[clip['id']])
    grouped = looks.groups(found)
    print('groups:', {g: sum(1 for v in grouped.values() if v == g) for g in set(grouped.values())}, 'distance', looks.LOOK_DISTANCE)


if __name__ == '__main__':
    main(sys.argv[1])
