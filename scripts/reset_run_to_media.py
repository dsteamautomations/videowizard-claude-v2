"""Reset a run to its media stage (SK, 2 Nov 2026, VW-16: "reset VW-16 to media and remove any unnecessary files and decisions from the server").
Run on the VM as the service user, from /opt/vw2/app/server:  python ../scripts/reset_run_to_media.py VW-16 "<SK's words>"
- Marks the analysis and every later stage output stale (core.revise, recorded in vw2_revises with SK's words); the media and earlier stages stay.
- Moves the first cut's working files (<run>/stage2/: the session with its scenes, options, decisions and review renders) to <run>/archive-<date>/stage2/,
  so the next options step starts fresh; nothing is deleted outright (ask the builder to purge the archive).
- Writes one entry in the run's decision log. The analysis then runs afresh: the new analysis instruction changes every clip's analysis key."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))

from app import core, runlog   # noqa: E402
from app.db import connect   # noqa: E402
from app.storage import storage   # noqa: E402


def main(code, words):
    store = storage()
    with connect() as conn:
        run = conn.execute('select * from vw2_runs where code=%s', (code,)).fetchone()
        user = {'id': 'SK (builder, on request)', 'name': 'SK', 'role': 'Admin'}
        out = core.revise(conn, user, run, 'analysis', None, words)
        prefix = f"{run['id']}/stage2"   # storage lists a prefix without its trailing slash and returns '<prefix>/<name>'
        keys = store.list(prefix)
        archive = f"{run['id']}/archive-{date.today().isoformat()}/stage2"
        for k in keys:
            store.put(archive + k[len(prefix):], store.get(k))
        if keys:
            store.delete(keys)
        runlog.write(conn, {'run_id': run['id'], 'stage': 'media', 'kind': 'override', 'about': code, 'rule': 'builder reset on SK\'s request',
                            'entry': f"reset to media: {out['stale']} outputs marked stale (analysis onward, stages {', '.join(out['reopened'])}); "
                                     f"{len(keys)} first-cut files moved to {archive}", 'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})
    print({'stale': out['stale'], 'reopened': out['reopened'], 'moved': len(keys), 'archive': archive})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
