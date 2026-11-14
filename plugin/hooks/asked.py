"""The question tool and the run's log (design/192, intake 8 and brief 7): each question the assistant puts to the operator with the question
tool, and each answer, becomes one entry of the run's log, so the person's time can be told from the assistant's. Before the tool the guard calls
log() (no second process on every tool call); after the tool this file runs as its own hook, for the question tool only. The entry is written by
`vw log` in a process of its own that is never waited for; it never blocks or delays the question, and any failure is silent. `vw log` keeps the
entry only in the text stages (intake, brief, script). Silent outside the operator folder and without an active run."""
import json
import os
import subprocess
import sys
from pathlib import Path

CUT = 300


def entry(data):
    """(kind, text) for the hook's payload; text is empty when there is nothing to log."""
    inp = data.get('tool_input') or {}
    if data.get('hook_event_name') == 'PostToolUse':
        resp = data.get('tool_response')
        answers = (resp.get('answers') if isinstance(resp, dict) else None) or inp.get('answers') or {}
        if isinstance(answers, dict) and answers:
            return 'answer', ' | '.join(f'{str(q)[:CUT]} -> {str(a)[:CUT]}' for q, a in answers.items())
        return 'answer', str(resp)[:CUT] if resp else ''
    asked = [str(q.get('question') or '')[:CUT] for q in inp.get('questions') or [] if isinstance(q, dict)]
    return 'question', ' | '.join(q for q in asked if q)


def log(data, cwd, root):
    """Start `vw log` for this question or answer and return at once. The caller has already checked the folder."""
    from guard import active_run
    if not active_run(Path(cwd)):
        return False
    kind, text = entry(data)
    if not text:
        return False
    detach = {'creationflags': 0x00000008 | 0x00000200} if os.name == 'nt' else {'start_new_session': True}   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([sys.executable, str(Path(root) / 'scripts' / 'vw.py'), 'log', '--kind', kind, text], cwd=str(cwd),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **detach)
    return True


def main():
    try:
        data = json.load(sys.stdin)
        if data.get('tool_name') != 'AskUserQuestion':
            sys.exit(0)
        cwd = Path(data.get('cwd') or os.getcwd())
        root = Path(os.environ.get('CLAUDE_PLUGIN_ROOT') or Path(__file__).resolve().parents[1]).resolve()
        from guard import builder_checkout, operator_folder
        if not builder_checkout(cwd, root) and operator_folder(cwd):
            log(data, cwd, root)
    except Exception:   # noqa: BLE001  the log is a record; it never stands in the way of a question
        pass
    sys.exit(0)


if __name__ == '__main__':
    main()
