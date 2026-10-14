"""Stage 2 (blueprint v3.2 §3–6, design/15 + 17): options (2A) and master (2B) replace planning on procedure version 2.
package.py builds what the chat model reads; validator.py is the mechanical judge; render.py makes the review and master films;
stage.py holds the stage logic (session JSON in storage, stage outputs as the record)."""
CONTRACT_OPTIONS = 'vw2-options-v1'
CONTRACT_MASTER = 'vw2-master-v1'
SLATE_FRAMES = 75
