# design/190: one card for the treatment step and one for the plan step

SK, 13 Nov 2026. Status: requirements, waiting for SK's approval. Nothing built.

## The requirement, restated

In the treatment step and the plan step the operator answers every entry on one card in the chat and submits once. The server is called once to hand out the card and once to record all answers. Pictures, reference sets, takes, shoot and record stay as they are: plain chat, one at a time.

On the card:
- The number buttons at the top are the only way to move. No Back or Next, no progress dots.
- A short message at the top says what to do.
- Each entry has Accept and Change this. Change this opens a box for the operator's words.
- Accept moves to the next unanswered entry by itself. This can be switched per step.
- Column widths are set per step.
- An answered entry shows its answer on the button itself: Accept becomes "Accepted" in green with a tick, Change this becomes "Change saved" in amber. Clicking an answered button again does nothing.
- No "gap 2 of 20" line. The entry's own name (Gap G2) is a coloured label at the top of the entry, so the eye sees it change.

## How the answers are kept (the part that must not fail)

1. The server hands out a card with a card number and, for each entry, the entry's own mark (a short code of its content).
2. Submit all puts the answers into the chat as one message. From that moment they are in the conversation and cannot be lost.
3. The `vw` tool first writes them to a file in the run folder (`card-<number>.json`), then sends that file to the server.
4. The server records each entry in order. An entry already recorded is skipped, so sending the same file twice changes nothing.
5. When the server confirms, the tool renames the file to `card-<number>.sent.json`. A sent card is never picked up again; the server also refuses a second submit of the same card number with "already recorded".
6. If the call fails (network), the file stays. `vw visuals card --resend` sends it again. No answer is asked twice.

## Expected but not stated

- The Direction is the first entry of the treatment card. If the operator changes the Direction, the gap answers on that card are not recorded, because every gap line is rewritten from the new Direction. The card comes again after the rewrite.
- A plan gap that offers a choice (two ways to film it) is asked in the plain chat first, as today. The card then shows the chosen way. Otherwise the card would carry every table twice.
- After a submit, only the changed entries come back, on a smaller card.
- The one-at-a-time way stays for treatment and plan when the card tool is not there on the operator's machine (old-ways rule: kept until every operator machine shows the card; listed in design/35).
- The record of each answer says it came from a card, with the card number.

## Edge cases and how each is handled

| Case | Handling |
|---|---|
| Not every entry answered | Submit all is refused on the card and names the missing entries |
| Change this with no words | Refused on the card |
| Same card submitted twice | Second one answered "already recorded"; nothing changes |
| Card submitted after the plan changed | Entries whose mark no longer matches are refused and asked again; the others are recorded |
| Server fails halfway (entry 12 of 20) | Entries 1 to 11 stay recorded; the answer names where it stopped; resend records the rest |
| Network drops at submit | The file is in the run folder; resend |
| Chat closed before Submit all | The card tries to keep the answers in the browser's own store. If that store is not allowed, the card is shown again and answered again; nothing was recorded, so nothing is wrong |
| An old card still on screen higher in the chat | Its submit is refused by card number |
| Operator types the answers instead of using the card | Recorded the same way, by entry number |
| Operator's words contain `|`, quotes or new lines | Answers travel as a file, not as a command argument |
| More than 12 entries | See "Size" below |
| Two people on the same run | The server takes the first submit; the second gets "already recorded" |

## Size: 9 entries, and 15 to 20 gaps

Tested on 13 Nov with a 20-entry sample card in this chat: the number row, the table and the answers hold for 20; nothing breaks in the display.

What grows is the time to write the card. The operator's assistant types every word of every entry. Estimate from the plan table we use today (about 450 characters a shot, 4 shots a gap):

| Entries | Card text | Time to appear | Today, one at a time |
|---|---|---|---|
| 9 (treatment) | about 6,000 characters | about half a minute | about 4.5 minutes |
| 12 | about 22,000 | about 1.5 minutes | about 6 minutes |
| 20 | about 36,000 | about 2.5 to 3 minutes | about 10 minutes |

These are estimates; they are not measured on a real plan.

Proposal: one card up to 12 entries. A longer plan is split into cards of at most 10 (a plan of 20 gaps = 2 cards, 2 submits). Reason: a 3-minute wait with nothing on screen reads as a hang, and a longer card raises the risk below.

## Review from a consultant's point of view

Points that matter, most serious first:

1. **What the operator reads is typed by the assistant, not sent by the server.** A mistyped line means the operator accepts words the server does not hold. The entry mark proves which entry was answered, not that the words on screen were exact. Reduced by: the assistant is told to copy the server's data as it is into a fixed card; cards are kept to 10 to 12 entries; the recorded text is always the server's. Not removed.
2. **Twenty Accept buttons invite accepting without reading.** One at a time had the same risk, but the card makes it faster. Not solved here; say if you want a guard (for example, Accept only after the table was scrolled into view).
3. **Direction and gaps on one card** (handled above).
4. **Offered choices in the plan** (handled above).
5. **The card tool on each operator machine.** It exists in the desktop app on this PC. Not checked on the Mac. The fallback is the one-at-a-time way.
6. **Guard.** The card tool must be let through.
7. **Nothing in this change is run yet.** The chat flow's later paths (sets, pictures, takes, shoot, record) have been read, not run. The card adds a new path on top. One real pass on a fresh run is the only proof.

## The guard

My reading of "get rid of the plugin guard": the guard stops blocking the card tool; the guard stays for everything else (it is what keeps builder tools out of the operator folder). If you meant remove the guard altogether, say so.

## Tests

By SK's word for the chat flow: no unit suites. One check stays with the code: a small self-check that a card submitted twice records once, and that a changed entry is refused.

## Built (13 Nov, local, not committed, not deployed)

- Server: `chat_flow.next_item` hands out a card when two or more treatment lines or plan gaps wait (`_card`, `_card_code`, `chat_card.html`); `chat_flow.card_answer` records it; route `POST /visuals/chat/card`. Cards: up to 12 entries on one, a longer step in cards of 10.
- Tool: `vw visuals next` saves the card as `work/chat/<card>.html`; `vw visuals card --file <answers file>` sends the answers and renames the file to `<card>.sent.json`; `--one` on `next`, `decide` and `card` asks one at a time.
- The same answers sent twice are one request (the request number is made from the answers), and the server keeps a list of spent cards.
- Guard: the card tool is let through.
- Instructions: section E, the treatment part, the plan part (`scripts/d190_wording_v3.py`), `plugin/commands/vw.md`.
- A direction sent back now holds every gap line until it is revised, in both ways of asking.
- Older way: row 49 of design/35.

Checked: `server/tests/check_chat_card.py` (stand-ins for the decision functions; passes), the guard tests (15 pass), and the card page clicked through in a browser on a local copy (accept, change, the button states, the kept answers after a reload, the lock after submit, the copy-line fallback).

## Not covered

- The card inside the operator's real chat, with the real card tool, on a real run: first seen on the next user run.
- `vw visuals card` against the live server (the file checks and the rename were read, not run).

- Pictures, sets and takes on a card (decided: plain chat).
- A guard against accepting without reading.
- Measuring the real time on a real 20-gap plan; first seen on the next user run.
- Keeping half-filled answers when the browser store is not allowed.
