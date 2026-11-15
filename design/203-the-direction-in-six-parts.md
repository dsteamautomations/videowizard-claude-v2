# design/203: the Direction in six labelled parts (requirement handoff)

**Status:** requirements for hand-over. Asked for by SK on 15 Nov 2026 ("create the document… it should be a requirement handoff"). **Not yet approved for building as a list; no code written.** The thread that builds confirms the list with SK before code (working rule: requirements before code).

**Written by:** a side thread of the VW monitoring session. It read the code at `main` 40eb67b (server 0.100.0, design/202 in). It changed nothing in the application.

**Research behind it:** `videobuilder-v4/research/direction-rules-15-nov.md` (eight directors' videos on writing a treatment, six web searches). Related: design/202 (the treatment's lines and their two reasons), design/190 (the card), design/191 (what changed).

## Built on 15 Nov 2026 (not deployed)

SK approved the list on 15 Nov, with the six limits as proposed and a missing part as a warning ("Agreed for B first and then A. Yes for tests. Go ahead").

| Built | Where |
|---|---|
| `direction_parts`, the six limits, the idea in one sentence, the Direction's text built from the parts; an older paragraph taken with its flag; `direction_missing` | `server/app/visuals_stage.py` (`DIRECTION_PARTS`, `direction_from`, `direction_fields`, `treatment`) |
| What changed, named by part | `visuals_stage.direction_changes`, `_carry_lines` |
| A second Direction beside the first (`direction_alternative`, each with how it answers the brief and what it risks); an identical one refused; using the second sends every gap line back to be written again | `visuals_stage._treatment_lines`, `_line_digests` |
| Six headed rows, the "From the brief" rows, "not given", and the buttons Accept, Change this, Show me a different direction (Use the first, Use the second when two are shown) | `server/app/chat_flow.py` (`_direction_rows`, `_treatment_items`) |
| The instructions | `scripts/d203_wording_v3.py`, `server/procedures/v3.json` |
| Old way 75 | `design/35-decision-log.md` |

Tests: `server/unit/test_design203_pure.py` (23 tests); the whole `server/unit` suite passes.

**Where the build differs from the text below:**
- When the operator takes the second Direction, a gap line the assistant sends again unchanged returns as "to accept"; it is not held as sent back.
- The first Direction's two lines are sent as `direction_answers_brief` and `direction_risk`; the second's sit inside `direction_alternative`.
- Not seen on a real run: how well the assistant writes the six parts, and a second Direction.

## 1. Why

SK, 15 Nov: "The direction is what would be putting things in place and we should definitely have some rules that would control the direction."

The Direction is the first thing the treatment step produces. Every gap line is written from it, and a changed Direction sends every line back. Yet almost nothing controls what it says.

## 2. What the tool does today

| Where | What |
|---|---|
| `server/app/visuals_stage.py:725-727` (`treatment`) | A Direction must be present and at most 2,000 characters. Nothing else is checked. |
| `visuals_stage.py:321-323` (`propose`) | The plan's `foundation.treatment` must begin with the Direction, word for word. |
| `visuals_stage.py:801` (`_line_digests`), `:825` (`_carry_lines`) | The Direction is one line with its own state; a change shows `Before: "…"`. |
| `server/app/chat_flow.py` (`_treatment_items`) | The Direction is asked first and alone; no gap line is offered until it is accepted; sent back, every gap line is written again. Since design/202 its question names it. |
| `server/procedures/v3.json`, visuals stage, part `treatment` | The assistant is told to cover four things in one paragraph: what the audience should understand or feel, the storytelling viewpoint, the principal visual approach and why, and the roles of footage, stills, generated scenes and graphics. A palette alone is not a Direction. No quota of any kind of picture. |

## 3. Requirement

The Direction is written and shown as **six short labelled parts**, not one paragraph. The server checks that each part is there and within its length. The film's goal and audience are shown from the brief beside it. The operator approves it first, as today, and can ask for a second Direction that differs in kind.

## 4. The six parts

The treatment document gains `direction_parts`, an object with these keys. Each is plain text.

| Key | Heading shown | What it holds | Limit |
|---|---|---|---|
| `idea` | The idea | The film's one idea, in **one sentence** | 160 characters, one sentence |
| `purpose` | Who it is for and what it must do | The audience and the result wanted, in line with the brief | 300 |
| `viewpoint` | Whose story | The one side the film is told from | 200 |
| `feel` | How it should feel | What the viewer should feel, and the concrete choices that give it (pace, light, movement) | 300 |
| `shape` | How the film moves | The film from opening to end in three to five beats | 400 |
| `pictures` | What each kind of picture does | The role of real footage, of generated scenes and of graphics, each with its reason; and one or two things the film will not do | 500 |

Example (the rat-trap bond film):

| Part | Text |
|---|---|
| The idea | Fewer bricks, and a better wall. |
| Who it is for and what it must do | Builders and home owners. They should come away believing rat-trap bond is a sound choice. |
| Whose story | Told from beside the mason. |
| How it should feel | Calm and sure: steady pictures, real work, no hype. |
| How the film moves | The housing problem; the method; what it gives; the proof it is strong; what it saves the land. |
| What each kind of picture does | Real footage shows the method and the finished buildings. Short scenes of one person doing one thing show what the footage lacks. One diagram of the wall returns for what a camera cannot see. No still held as wallpaper; no words on the picture. |

## 5. What changes

### 5.1 Server (`visuals_stage.treatment`)

1. A new draft carries `direction_parts` with all six keys. A missing or empty part: named, and **shown to the operator as not given** (design/195: flags warn, they do not block). The draft is still taken.
2. A part over its limit is refused, naming the part and the limit.
3. `idea` holding more than one sentence is refused: "The idea is one sentence."
4. The server builds the `direction` string from the parts, in the order above, each as "Heading: text". Everything that reads `direction` today (the plan's word-for-word check, the line's digest, the 2,000-character limit) keeps working unchanged.
5. A draft that sends only the old `direction` string is still accepted, with one flag: "The Direction is not in its six parts." So an older plugin does not break.
6. The result carries `direction_missing`: the list of parts not given.

### 5.2 What the operator sees (`chat_flow._treatment_items`, and the card or page that shows it)

1. The Direction is shown as six headed rows, not a paragraph.
2. Above them, from the brief's own record and marked "From the brief": the film's purpose, audience and tone. The operator can see at once if the Direction departs from them.
3. A part not given shows "not given".
4. When the Direction comes back changed, the list of what changed names the part ("Whose story: … → …"), using the parts, not one long before-text.
5. Three buttons: **Accept**, **Change this** (the operator's words), and **Show me a different direction**.

### 5.3 A different direction

1. "Show me a different direction" is recorded as a change request with fixed words, so it runs through the same path as Change this.
2. The assistant writes a second Direction that differs in **viewpoint or approach**, not in wording, and adds two lines to it: how it answers the brief, and what it risks.
3. The first Direction is kept. The operator sees both, each with those two lines, and accepts one. The other is dropped.
4. At most two are held at a time; asking again replaces the second.

### 5.4 The assistant's instructions (`server/procedures/v3.json`, part `treatment`)

1. Write the Direction as the six parts, in the order given, two or three sentences each.
2. The idea first, in one sentence. If it cannot be said in one, the idea is not clear yet.
3. Every later choice follows from the idea: say in `pictures` how.
4. Take the audience and the result wanted from the brief; where the Direction departs from the brief, say so in `purpose`.
5. One viewpoint, held for the whole film.
6. Tone is what the viewer should feel, tied to concrete choices. Words like "cinematic" or "immersive" alone are not a tone.
7. Be specific and committed: "short scenes of one person doing one thing", not "a mix of techniques".
8. Say what the film will not do.
9. A second Direction, when asked for, differs in kind and states how it answers the brief and what it risks.

The existing sentences on the palette, on no quota, on a film with no footage, and design/202's rules stay.

## 6. Unstated but expected

- The Direction is still asked first and alone; no gap line before it is accepted. Unchanged.
- Sent back, every gap line is written again from it. Unchanged.
- A recorded treatment from before this release is still read; its Direction shows as one paragraph.
- One flow, two front ends: the six rows appear wherever the Direction is shown (the chat, the card, the page), from the same server function.
- The rules are general. Nothing in them is tied to documentaries; the example above is only an example.
- Old way (SK's rule of 30 Oct), to list in design/35: "the Direction as one paragraph" is kept as an input until operators have the new plugin, then retired.

## 7. Edge cases

| Case | Handling |
|---|---|
| A film with no footage | `pictures` also states the film's one look (colours, contrast, light), as today |
| A film with no people (a product, software) | `viewpoint` may be the user's or the maker's side; it is still one |
| The brief has no audience or tone recorded | "From the brief" shows what there is and "not recorded" for the rest; nothing is refused |
| `idea` with a colon or a semicolon | Allowed; one full stop, question mark or exclamation mark at most |
| A part that only repeats its heading | Not checked by the server; the operator is the judge |
| Both `direction` and `direction_parts` sent | The parts win; the string is rebuilt from them |
| The parts together exceed 2,000 characters | Cannot happen: the six limits add up to 1,860 with headings to spare; the old limit stays as a guard |
| A different direction asked twice | The second replaces the earlier second; the first stays |
| The operator accepts neither and writes their own words | Change this, with their words; the assistant rewrites the named part or parts |
| A changed Direction after gap lines were accepted | As today: those lines return to "to accept", each showing what changed |
| A Direction changed in one part only | The what-changed list names that part alone |

## 8. Failure modes

- An older plugin sends the paragraph: accepted with the flag in 5.1 point 5.
- The brief's record cannot be read: the "From the brief" rows are left out; the Direction is still shown.
- The second Direction is identical to the first: the server says so and keeps the request open; it is never shown as different.

## 9. Tests first (`server/unit`)

- Each part missing, empty, at its limit and over it.
- `idea` with one sentence and with two.
- The built `direction` string holds the six headings in order; the plan's word-for-word check passes against it.
- An old paragraph is accepted with its flag; a recorded treatment from before is still read.
- The what-changed list names the changed part only.
- The item for the Direction carries six rows, the "From the brief" rows, "not given" for a missing part, and the three buttons.
- A different direction: kept beside the first, replaced when asked again, refused as different when identical; accepting one drops the other.
- The instruction text holds the new phrases (the suite pins phrases and the stage's word count; raise the visuals count with a note, as design/200 and 202 did).

## 10. Not covered

- **Whether the Direction is good.** The server checks that parts are present and short. The operator judges the content.
- **Tying each gap line back to the idea** (rule D2 of the research). Left to the operator's reading of the line's reason; a check could come later.
- **More than two Directions.** The sources disagree on how many to show; directors pitch one, agencies two or three.
- **Where the operator answers** (the chat card, or a Claude artifact page as tried on 15 Nov). This document says what is shown and asked, not where; it follows whatever design/202 settles.
- **The research's limits:** the eight videos are about films that are shot, mostly commercials; none covers a narrated film built from footage, graphics and AI video.

## 11. For the thread that builds

- Read first: this file, `videobuilder-v4/research/direction-rules-15-nov.md`, design/202, and the memory notes on deployment (no deploy without SK's explicit yes; the unit suite before every server or instruction commit).
- Files touched: `server/app/visuals_stage.py` (`treatment`, `_line_digests`, `_carry_lines`), `server/app/chat_flow.py` (`_treatment_items`, the card code), `server/procedures/v3.json` with a wording script in `scripts/`, `server/unit/` (new test file; the word-count pin in `test_design125_stage7_c_pure.py`), `design/35-decision-log.md`, the version numbers.
- Open for SK before code: the six limits in section 4; whether a missing part warns (as written, after design/195) or refuses.
