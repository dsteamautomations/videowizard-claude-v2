"""Defect 30 (VW-7): a rejected take stayed 'ready' on the page and in status; the operator rejected it again and again. Its latest review now shows."""
from pathlib import Path

from app import visuals_stage as VS
from test_design94_r1_pure import cheap, film   # noqa: F401  (cheap: the autouse price fixture)
from test_design97_r3_pure import take
from test_visuals_stage_pure import FakeConn, RUN, store_with

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def review(decision, notes='the wall bends'):
    return {'id': 'r-' + decision, 'decision': decision, 'notes': notes, 'timing_notes': '', 'quote': '', 'by': 'u1', 'sha256': 's'}


def test_status_gives_each_take_its_latest_verdict():
    doc, sess = film(reviews={'j1': [review('rejected')], 'j2': [review('rejected'), review('accepted', '')]})
    st = VS.status(FakeConn([take('j1', 'VS1'), take('j2', 'VS1'), take('j3', 'VS1')]), store_with(sess, doc), RUN, [], repair=False)
    verdicts = {j['id']: j.get('verdict') for j in st['jobs']}
    assert verdicts == {'j1': 'rejected', 'j2': 'accepted', 'j3': None}


def test_the_page_shows_a_rejected_take_as_rejected_and_asks_nothing_of_it():
    assert 'function takeRejected(k)' in PAGE
    panel = PAGE[PAGE.index('if(selPic.take){'):]
    panel = panel[:panel.index('\n  }\n')]
    assert "k.status==='ready'&&!k.selected&&!takeRejected(k)" in panel and 'Rejected' in panel
    assert "(takeRejected(k)?'rejected':esc(k.status))" in panel   # the panel's head line too
    turn = PAGE[PAGE.index('function shotState(s)'):]
    turn = turn[:turn.index('\n}\n')]
    assert "ready=s.takes.find(k=>k.status==='ready'&&!k.selected&&!takeRejected(k))" in turn
    assert 'the assistant prepares a new take' in turn
    row = PAGE[PAGE.index("s.takes.map(k=>'<tr data-take="):]
    row = row[:row.index('</tbody></table>')]
    assert "takeRejected(k)?'<span class=\"badge err\">rejected</span>'" in row and "k.status==='ready'&&can&&!k.selected&&!takeRejected(k)" in row
