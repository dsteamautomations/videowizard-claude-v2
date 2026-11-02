# design/140 part 1: brand-generic library, the requirement as understood

Status: restated by Claude, corrected by SK, 2 Nov 2026. Not approved for code. Part 2 (`140-brand-library-2-hidden-requirements.md`) reads the code and lists the hidden requirements, edge cases and failure modes.

## In one line

After Gemini Flash 3.8 has studied a film's uploads, Claude asks the user which files are brand-generic. Every file is stored with its description, tied to its film and brand. When a later film of the same brand is processed, Claude first places that film's own files, then *proposes* library files for the gaps and for better swaps, and the user accepts or rejects each proposal.

## 1. A new question between the study and the analysis

1. The team uploads the film's videos and images. Gemini Flash 3.8 studies them, as today.
2. Before the analysis stage starts, Claude reads Gemini's description of every file. It works from the text. It opens an image or a frame only when the text leaves it unsure.
3. From the descriptions, Claude shortlists the files that are not tied to this one film: clips that could serve any film of the same brand (montage / B-roll).
4. Claude shows the shortlist and asks the user which files to mark brand-generic.
   - The user can accept or drop any file on the shortlist.
   - The user can also mark files Claude did not suggest.
   - If the user marks nothing, the analysis carries on normally.
5. The analysis stage starts only after the user has answered.

## 2. The library

1. Every file of the batch is stored in the database with:
   - its Gemini description,
   - the film it was uploaded for,
   - the brand that film belongs to,
   - whether the user marked it brand-generic.
2. **Brand only.** A brand-generic file is reused only in films of the same brand. It is never offered to another client.
3. **Near duplicates.** The stored descriptions are used to catch a near duplicate when a later upload repeats a file the brand already has. The duplicate is stopped at the processing stage.
4. Montage videos and B-roll are the same pool: the files marked brand-generic. Images are handled the same way as videos.

## 3. Using the library when a film is processed

### Pass 1: the film's own files (Claude decides on its own)
1. Claude places the current batch's own files in the film.
2. Claude rechecks its own placements and corrects any that do not fit.

### Pass 2: the brand library (proposals only)
1. Claude proposes brand-generic files from earlier films for the places Pass 1 left empty.
2. Where a library file would serve a place better than the current file placed there, Claude proposes the swap. It does not swap.
3. The user accepts or rejects each proposal. Nothing from the library enters the film without the user's yes, because the user may not want these files in this film.
4. If the user rejects everything, the film keeps what Pass 1 produced.

## 4. Interface

No new UI. Both questions (which files are brand-generic; which library proposals to accept) use the screens and controls the tool has today.

## Corrections SK made to the first restatement

| First restatement | SK's correction |
|---|---|
| One placement pass, then gap-filling | Pass 1 has two steps: place, then recheck its own decisions |
| Claude may swap a current file for a library file | Claude proposes the swap; the user decides |
| Library files fill the gaps | Library files are proposed for the gaps; never forced on the user |
| Reuse scope unstated | Brand only, never another client |
