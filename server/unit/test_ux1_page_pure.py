"""design/129 G, UX1 (SK, 1 Nov 2026): the visuals page as slides, a rail of cards on the left and the chosen card on the stage, versions in tabs,
the message bar in colour at the top; desktop only. Everything that works today keeps working: every action, element id and data attribute of
the page before UX1 (frozen below on 1 Nov 2026, server 0.78.0) is still on it, and each action still sends the same request."""
import re
from pathlib import Path

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
SCRIPT = PAGE[PAGE.index('<script>'):]

# the page before UX1, read from server 0.78.0's visuals.html
OLD_ACTIONS = ['accept-selected', 'answer', 'approve', 'approve-reuse', 'approve-spec', 'approve-specs', 'clear-ticks', 'clip', 'correct-spec', 'fix', 'footage',
               'ignore', 'measure', 'nothing-fits', 'pick', 'reason-skip', 'record', 'reject', 'reject-take', 'reject-take-why', 'reject-why', 'revise-selected',
               'round-done', 'round-picks', 'round-picks-back', 'round-search', 'round-undo', 'save-note', 'search', 'select', 'select-take', 'sequence', 'still',
               'supply', 'supply-open', 't-accept', 't-back', 'treatment', 'unplace']
OLD_IDS = ['action', 'app', 'card-specs', 'fmsg', 'ft-form', 'ft-open', 'ftwords', 'line', 'msg', 'p-close', 'p-next', 'p-note', 'p-prev', 'p-save', 'p-tick', 'panel',
           'pl', 'pl-name', 'player', 'pwords', 'ref-note', 'rwhy', 's-pictures', 's-plan', 's-record', 's-references', 's-takes', 's-treatment', 'steps', 'tray',
           'viewer', 'vw-close', 'vw-img', 'vw-in', 'vw-next', 'vw-out', 'vw-panel', 'vw-prev', 'vw-stage', 'wcount', 'wlist', 'wnext', 'words']
OLD_DATA = ['data-a', 'data-answer', 'data-choice', 'data-code', 'data-el', 'data-g', 'data-gap', 'data-gnote', 'data-go', 'data-id', 'data-item', 'data-job',
            'data-lb', 'data-line', 'data-name', 'data-pchip', 'data-play', 'data-rchip', 'data-ref', 'data-s', 'data-search', 'data-sel', 'data-sha', 'data-shot',
            'data-sview', 'data-take', 'data-tick', 'data-untick', 'data-view']

# every request body the page sends, as it was before UX1: the action and its fields (test 5's static half; the browser check clicks them)
OLD_SENDS = ["send({action:'select',gap_id:b.dataset.gap,choice_id:b.dataset.choice}", "send({action:'treatment',accept:[b.dataset.line],quote:q}",
             "send({action:'treatment',send_back:[id],notes:w,quote:q}", "send({action:'treatment',quote:q}", "send({action:'accept',gap_ids:ids,quote:q}",
             "send({action:'revise',gap_id:gid,notes:q,quote:q}", "{action:'approve',reference_id:b.dataset.ref,sha256:b.dataset.sha}:{action:'reject',reference_id:b.dataset.ref}",
             "send({action:'still',shot_id:b.dataset.shot,reference_id:b.dataset.ref,...reuseOf(b.dataset.shot)}",
             "{action:'reject',reference_id:id,notes:w}:{action:'reject-take',job_id:id,notes:w}",
             "send({action:'clip',shot_id:sh,clip_id:$('cf-c-'+sh).value,in_s:Number(at),quote:w,...reuseOf(sh)}", "send({action:'sequence',shot_id:b.dataset.shot}",
             "send({action:'fix',reference_id:b.dataset.ref}", "send({action:'unplace',shot_id:b.dataset.shot}", "send({action:'select-take',job_id:b.dataset.job}",
             "send({action:'reject-take',job_id:b.dataset.job}", "send({action:'pick',search_id:sid,picks:list}", "send({action:'answer',item:b.dataset.item,answer:b.dataset.answer}",
             "send({action:'round-undo',quote:q}", "send({action:'supply',element_id:el,url:u}", "send({action:'nothing-fits',search_id:b.dataset.search,reason:q}",
             "send({action:'approve-spec',shot_id:b.dataset.shot,quote:''}", "send({action:'note',reference_id:b.dataset.ref,note:", "send({action:'approve-specs',quote:''}",
             "send({action:'correct-spec',shot_id:sh,words:w}", "send({action:'measure',reference_ids:refs,question:q}", "send({action:'approve-reuse',shot_id:b.dataset.shot,quote:w}",
             "send({action:'footage',camera:v('camera'),support:v('support'),look:v('look'),quote:w}", "send({action:'record',gap_ids:readyGaps().map(g=>g.gap_id),quote:q}",
             "send({action:'round-done',verdicts:verdicts,quote:q}", "send({action:'round-picks',picks:pk,ignore:ign,quote:q}",
             "send({action:'pick',search_id:sid,picks:[{n:p.n,note:p.note||''}]}", "JSON.stringify({action:'search',element_id:eid,keywords:kw,source:src})"]


def test_1_every_action_id_and_data_attribute_of_the_old_page_is_still_there():
    gone = [a for a in OLD_ACTIONS if f'data-a="{a}"' not in PAGE and f"a==='{a}'" not in PAGE]
    gone += [i for i in OLD_IDS if f'id="{i}"' not in PAGE and f"$('{i}')" not in PAGE]
    gone += [d for d in OLD_DATA if f'{d}=' not in PAGE]
    assert gone == []


def test_5_every_request_body_is_sent_as_before():
    assert [s for s in OLD_SENDS if s not in SCRIPT] == []
    assert SCRIPT.count("fetch(base+'/act'") == 3 and "fetch(base+'/data',{cache:'no-store'})" in SCRIPT   # the page talks to the same two routes, nothing new; UI change, 11 Nov 2026 (R13): a third call on the same route stores one answer of step 2 (set_answer), outside the in-flight lock


def test_ux1_the_rail_the_stage_and_the_message_bar_are_on_the_page():
    for needle in ('id="rail"', 'id="stage"', 'id="grip"', 'function railCards', 'function renderRail', 'function focusUnit', 'data-unit=',
                   'Waiting for me', 'function versionTabs', 'function takeTabs', 'id="mhist"', "remember('rail'"):
        assert needle in PAGE, needle
    top = PAGE[PAGE.index('<div class="top">'):PAGE.index('id="stage"')]
    assert 'id="fmsg"' in top   # the message bar sits under the steps, always in view, not at the foot


def test_ux1_the_message_bar_has_four_colours():
    for cls in ('.v2 .status.info', '.v2 .status.ok', '.v2 .status.err', '.v2 .status.dec'):
        assert cls in PAGE, cls


def test_ux1_desktop_only_and_no_whole_page_scroll():
    assert 'body:has(.v2.ux1){height:100vh;overflow:hidden' in PAGE
    css = PAGE[:PAGE.index('</style>')]
    new = css[css.index('/* design/129 UX1'):]
    assert not re.search(r'@media \(max-width:(\d+)px\)', new) or all(int(w) >= 1280 for w in re.findall(r'@media \(max-width:(\d+)px\)', new))   # nothing for phones


def test_ux1_the_rail_width_is_200_to_360_and_remembered():
    assert 'Math.min(360,Math.max(200' in PAGE and "recall('rail')" in PAGE


def test_ux1_versions_are_named_new_rejected_and_fixed_into():
    for words in ("' · new'", "' · rejected'", "'fixed into version '", "'fix of version '", "'Take '"):
        assert words in PAGE, words
