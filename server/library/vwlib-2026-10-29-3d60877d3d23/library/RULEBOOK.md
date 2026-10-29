# Rulebook: read on every job

Status: first draft, 2026-10-19. Short on purpose. These are the rules that apply to every image and every clip, whatever the playbook and whatever the model. Model habits are in the fact sheets. Job-type rules are in the playbooks. The long method files this was distilled from are named at the end.

## 1. Before writing anything

1. Read the whole job form. If a required field is missing, answer `needs_input`. Do not guess.
2. Open only what `INDEX.md` says for this job. Five to nine files. Not the shelf.
3. Look at every picture sent. Write two lines on each: what is in it, any text read letter by letter, colours, anything odd. Check the tag against what you see.
4. Decide the model from the job form or the "when to pick" rules in the fact sheets. Open that fact sheet. Write in its dialect.

## 2. Every instruction must be checkable by looking at the output

"Premium" is not checkable. "Brushed metal, one object, generous margins" is. Rewrite every vague word from the brief into visible facts before it reaches the prompt, and list the rewrites in the answer form. The replacement table is in `agency/deterministic-checks.md` section 1. The six presence checks there are the floor: composition, lighting, typography, materials and reference handling are each named, and no banned phrase survives.

## 3. Canvas before subject

State the deliverable, the aspect and the layout first: where the subject sits, where the text goes, what margin and what empty area are reserved. Then describe the subject. A model that gets the subject first spends its detail on the object and improvises the layout.

## 4. Exact words

1. Every string that must appear goes in quotes, exactly as approved. Never change a letter. Never paraphrase.
2. Say where it sits, how big, in what type feel. Say how many times: once.
3. Close with the standing line: "Render only explicitly requested image text. Do not add unrelated logos, signatures or captions." Every prompt. Even prompts with no text; that is when stray captions and fake watermarks appear.
4. Keep rendered copy short: one to five words renders best; long copy goes to a reserved area and is typeset later.
5. Regional-script copy is reserved, not rendered, until a test on that model says otherwise.
6. After generation, read every character in the whole frame, not only the headline.

## 5. Never generated as final

The client's logo: reserve an empty area, composite the real file afterwards. Legal text, long copy, real data charts, shippable app screens: generate as reference, rebuild in the proper tool. Cutouts needing true transparency: only on a model that returns a real alpha channel, and inspect it; a drawn checkerboard is not transparency.

## 6. Never invent

No price, date, phone number, address, award, badge, seal, star rating, certification, sponsor strip, product feature, ingredient claim, or efficacy claim that is not in the job form. If copy is missing, reserve a clean area and say so. This applies to background text too: no readable text that looks like a real brand, a number or an address.

## 7. Reference pictures

1. Number them in the order they are sent and give each one a job in words, using that model's own convention: "Image 1 is the product", `@Image 1`, `<FIRST_FRAME>`. The fact sheet says which.
2. Say what to take from each and what not to take: "take only the colours and light from Image 2; do not copy any object from it".
3. Do not restate what a reference already shows. Describe only what must change or what must hold.
4. Build the keep-list from the picture itself, as nouns a checker can tick: "lamp silhouette; brass colour; label text NET WT 200 G".
5. Stay within the model's count and kind limits. Never send a first frame together with references on a model where the first frame wins.
6. A reference from the shelf is for structure only. Its brands, people, text, prices and distinctive details are never copied.

## 8. Edits

1. One change per turn. Name the region, the change and the keep-list. Repeat the keep-list every turn.
2. Order when several changes are wanted: ratio first, then copy, then props or colour. A ratio change moves everything.
3. If a result drifts, retry from the last approved file, not from the drifted one. Never stack repairs.
4. When pixels outside the change must be exactly the source, composite the model's output back onto the source in an editor. Prompting cannot promise untouched pixels.
5. A mask is guidance, not a boundary.

## 9. Words

Words that hurt: "stunning", "epic", "masterpiece", "best quality", "8K", "ultra-detailed", "hyper-realistic", "flawless", "perfect". They add nothing and on some models they make the result worse. Words that help: concrete nouns and physical facts. Five to twelve named objects and surfaces for a scene, two to four light and material facts. Materials, lighting and palette are three separate controls; name each. Camera words as a look, not as physics: "50mm feel", "eye level", "low three-quarter angle".

Style anchors: translate a named studio, director, painter, magazine or brand into the visible technique it stands for. Real brands, franchises, interfaces and people never go into a client prompt, even when a shelf template carries them.

## 10. Negatives

Describe what should be present first. Then add a short, targeted list of what the model tends to add wrongly for this job: "no fake sponsor logos, no unreadable microtext, no extra products". Long negative lists dominate the prompt. Where a model has no negative field, the negatives go in the prompt text as plain sentences.

## 11. Real photographs

When the output must pass as an unretouched photo: state the capture as a fact, "a real phone photo", "35mm colour negative, lab scan", never as a style. Name three or more imperfections with their place: "pores across the nose and cheeks", "two flyaways above the crown", "scuffed baseboard behind the subject". Ask for low micro-contrast and no added sharpening. Ban the glow family in the constraints: HDR, bloom, luminous skin, glossy hair, perfectly even background. For people, name every way the subject differs from the model's ideal, and name it twice: once in the description, once in the constraints.

## 12. Series and characters

Make the reference sheet first and approve it. Then send it with every later call and repeat the five fixed traits in words each time. Add "do not redesign the character". For products, the same with silhouette, label, colour and proportions.

## 13. Settings versus words

Aspect ratio, pixel size, quality, clip length and resolution go in the API settings, not in the prompt words, unless that model's fact sheet says the words are where it works. No model name inside a prompt.

## 14. People, consent and compliance

1. No identifiable person without a consent id on the job form. No public figures, no lookalikes. No children's faces without parental consent and client policy.
2. Never change body shape, skin colour, apparent age or gender. Never remove a permanent feature unless the person asked in writing.
3. Sector rules travel with the industry field: registration numbers for real estate, no outcome claims or before-and-after for healthcare, no guarantees for education, licence numbers for food. The full list is DIRECTION section 5d.
4. Festival work: no deities on products, food, footwear or packaging; no religious text; tricolour imagery follows the Flag Code. The festival sheet has the motifs and the avoid-list.

## 15. After generation

Check the most expensive mistake first. People: eye spacing, nose, hairline, skin tone, hands. Products: silhouette, joints, label spelling, proportions. Text: every character, line count, no leftover old text. Storyboards: order of actions, props carried between panels. Infographics: numbers, arrow direction, label pairing. Spaces: window corners, door openings, floor seams, furniture scale. Then the keep-list. Then the untouched remainder for colour shift and crop creep. Then the destination: size, safe zones, reserved areas still empty.

The checklist in the answer form is written for this job in those terms. A must-line failing means fix or reject. The verdict goes into the feedback record with what went wrong and, later, what fixed it.

## 16. Video

1. A frame for video is a brief too. It carries the shot number, the camera move it must leave room for, and the continuity anchors. Approve it before anything moves.
2. The clip prompt is a motion brief, not a retelling of the frame: one camera move, what the subject does, what the environment does, the audio, the continuity line, and the single-scene line where one shot is wanted.
3. One primary camera move per shot. One main action. Longer stories are several clips.
4. Show, do not tell: the body renders, feelings do not. "His jaw locks" works; "he is scared" does not.
5. Timing in windows of three seconds or more, each with one action and a visible end state.
6. Audio is described or switched off. Dialogue is short, attributed to a visible action, and in quotes.
7. After animation, check that the label, the character traits and the palette held through the motion. A shot that broke is regenerated from the approved frame, not patched in the video tool.

## 17. The lint before answering `ready`

The ten rules are in `forms/answer-form.md`. Fail once, repair once. Fail twice, answer `needs_input` naming the rule.

## Where this came from

`00-method/craft.md` sections 1 to 15 and 18; `00-method/prompting-guide.md`; `00-method/workflow.md` sections 2 to 6; `00-method/de-slop.md`; `00-method/craft-additions.md`, `craft-additions-nanobanana.md`, `craft-additions-pixmind.md`; `agency/deterministic-checks.md`; `agency/ad-prompting-universal-rules.md`; `agency/reference-image-policy.md`; `agency/retouching/README.md` universal rule set; `video/universal-rules/` all three; `DIRECTION.md` sections 3, 5d and 5h. Where two sources disagreed, the house position is the one written here: style anchors become technique rather than named brands, and negatives are short and targeted rather than avoided altogether.
