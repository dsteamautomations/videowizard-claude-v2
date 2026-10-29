# Feedback on every image

Status: section opened 2026-10-19. No records yet. How automatic feedback will work is not decided; the place for it is ready.

## Why

Every image or video clip made through this folder gets one record. Without records we cannot tell which prompts work, which model suits which job, or whether a playbook is getting better. With records, a fix that repeats three times becomes a line in the playbook.

## What one record holds

One file per output, at `feedback/records/{job id}-{version}.yaml`. Template in `record-template.yaml`.

- Job id, client code, date.
- Which playbook was used, and its version.
- Which model, and which settings.
- The pictures sent in, with their tags.
- The prompt text, exactly as sent.
- Attempt number. First try, second try, and so on.
- Where the output file is.
- The checklist Claude wrote for this image, with a tick or cross on each line.
- The verdict: pass, fix needed, reject.
- Who gave the verdict: a person, an automatic check, or both.
- What went wrong, in one line.
- What fixed it, in one line, if a later attempt passed.
- Minutes from job received to final.

## Three ways a verdict can be given

1. **The checklist Claude writes with every prompt.** Each line is something you can see in the image: "the text reads exactly FESTIVE 20% OFF", "the lower-right corner is empty", "the product has one handle". This checklist travels with the image. Whoever checks, person or machine, ticks it.
2. **A person looks.** A reviewer opens the image and the checklist side by side and ticks each line. This is the only method we trust today.
3. **A vision model looks.** A model that can see images is given the output and the checklist and asked to tick each line and say why. Not built, not decided. When tried, its verdicts are written next to the person's verdict for the same image, so we learn how often it agrees before we let it decide alone.

## Letting some prompts run without a person first

SK's plan: a share of jobs runs straight through, and we see how it goes.

- A switch per playbook: off, sample, or on. "Sample" means a set share of jobs, say one in ten, runs without a person checking before the result is stored. SK sets the share.
- Every such output is marked `trial` in its record.
- Trial outputs are still checked afterwards, by a person, within a set time. The gap between the automatic verdict and the person's verdict is what we measure.
- A playbook moves from sample to on only when the gap stays small over an agreed number of records.

## How feedback flows back into a playbook

Only three kinds of change are allowed from one record. This stops a prompt being rewritten on the strength of one bad run.

1. A new line in the preserve list. Something drifted that we had not named.
2. A new constraint sentence. Something appeared that we had not forbidden.
3. A split. One prompt could not serve two cases, so it becomes two.

A prompt is rewritten wholesale only after a pattern shows across several records.

## When a prompt is trusted

- **Draft**: written, not run on a real job.
- **Tested**: passed on real jobs for two different clients.
- **Trusted**: passed on three or more, first or second attempt in most, no compliance miss.
- **Retired**: fails twice in a row after a model change and one added constraint does not fix it.

## Monthly summary

Once a month, one short file at `feedback/summary-{year}-{month}.md`: how many jobs, first-try pass rate, average attempts, which playbook lines were added, which model handled which job best, and the agreement rate between automatic and human verdicts where both exist.
