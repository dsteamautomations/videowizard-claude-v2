# design/120 — The image model chosen once per run: OpenAI GPT Image or Gemini Nano Banana (plan, 28 Oct 2026)

SK, 28 Oct: one codebase, one server; one group of operators runs a script with GPT Image, another the same script with Gemini's image model; the choice is made when the run starts and **cannot change midway**; the operator is made to answer when the command does not say. "Do excellent planning, one round of self-review, present the plan, then go ahead: implementation and deployment." The exact Gemini model id comes from SK; until then the server setting carries Google's documented id `gemini-3-pro-image`, one line to change.

## 1. The requirement

A run is created with `image_provider` = `openai` or `gemini`, recorded on the run, immutable, shown everywhere a picture is listed, and every picture of the run is made by that provider through one seam in the server. Everything else in the flow (the plan, the references, the checks, the takes, the drawn route, the delivery) is unchanged and blind to the choice.

## 2. What the two providers differ in (from Google's docs, read 28 Oct; GPT Image from design/71's fact sheet)

| | GPT Image 2.5 (today) | Gemini image (Nano Banana Pro) |
|---|---|---|
| Endpoint | `/v1/images/generations` and `/edits`, form upload | `models/<id>:generateContent` with `responseModalities: ["IMAGE"]` and `imageConfig {aspectRatio, imageSize}`; pictures as `inlineData` parts (Google's samples; the Interactions endpoint is the newer alternative with the same content blocks) |
| Size | pixels, 1536x864 / 1088x1936 | aspect ratio 16:9 or 9:16 and a tier, 1K / 2K / 4K; the output's pixels are read from the file |
| Input pictures | 16, untyped | 14, counted by kind: up to 6 object pictures, 5 character pictures, 3 style references |
| Mask for a region edit | yes (a mask file) | no; words only |
| Transparent output | yes (`background: transparent`) | no; chroma key on the server |
| Price | tokens at OpenAI's rates, about ₹3 to ₹5 | $0.134 a picture at 1K or 2K, $0.24 at 4K, plus $0.0011 an input picture: about ₹12 at 2K |
| Watermark | none | SynthID, invisible |
| Keys | the OpenAI pool (design/114) | the Gemini pool, already there |

## 3. The change

### Server
- **Migration 009:** `vw2_runs.image_provider text not null default 'openai' check (image_provider in ('openai','gemini'))`. Old runs read as `openai`; nothing re-made.
- **Run creation** (`core.create_run`, `POST /api/runs`): `image_provider` required (`Literal['openai', 'gemini']`, no default); a request without it is refused: "say which image model this run uses: image_provider openai or gemini; it cannot change later". No route changes it afterwards. The run's row, `/api/runs/{id}`, the status, the page header and the start line show it.
- **Config:** `GEMINI_IMAGE_MODEL` (default `gemini-3-pro-image`), `GEMINI_IMAGE_SIZE` (default `2K`), `GEMINI_IMAGE_USD` (0.134) and `GEMINI_IMAGE_USD_4K` (0.24), `GEMINI_IMAGE_MAX_INPUTS` 14 with the three kind counts.
- **The request** (`_queue_image`): carries `provider`; the job row's `provider` is `openai` or `gemini-image` (the worker claims both); `model` is the provider's; `size` stays pixels for OpenAI and becomes `{'aspect': '16:9', 'tier': '2K'}` for Gemini (from the brief's frame, as today); `background: transparent` only for OpenAI.
- **The parents, for Gemini:** the ceiling 14 and the kind counts (object: golden, isolated, component, frame, supplied, web pictures of things; character: a person element's pictures; style: the style picture), refused by name above a count; the order rule of design/111 F21 stays; every job line stays.
- **A region edit on Gemini:** no mask; the prompt gets "Change only what is inside the region left x %, top y %, width w %, height h % of Image 1; everything outside it exactly as Image 1"; the server's composite-back (design/111 F11) still restores the outside pixel for pixel, as it does today.
- **A component on Gemini:** the prompt asks for a flat chroma green `#00FF00` background instead of transparency; the worker keys the green out (an HSV match, Pillow and numpy) into alpha before storing; the alpha line of design/117 stays as the check.
- **The worker:** `process_image` branches on `req['provider']`: `_gemini_image(payload)` posts through the Gemini key pool with the same cooling as `_openai` (429 and revoked keys cool the key and the call moves to the next); parses the first image part, converts to PNG, reads width and height, reads `usageMetadata` for the token counts; an answer with no image part is a failure with the model's text as the reason. Retries on 5xx and 429 as the OpenAI path (design/82 U3).
- **Cost and ledger:** `image_cost_inr` by provider: OpenAI as today; Gemini flat $0.134 (or $0.24 at 4K) plus $0.0011 an input picture, at the configured dollar rate. `visuals_spend` counts both providers' jobs. The reference's `generation` record carries `provider`.
- **Checks:** unchanged; Gemini reads both providers' pictures.

### Plugin
- `vw start --images openai|gemini` required: without it the plugin refuses with "Ask the operator which image model this run uses, GPT Image (openai) or Gemini (gemini); it cannot change later; then `vw start --client … --images …`." The start line and `vw status` show it.
- No other command changes; the operator's flow is identical for both groups.

### Procedure
One sentence at the start: the question to the operator before `vw start`, the answer recorded on the run, never changed; and a line on the Pictures step that Gemini pictures carry up to 14 inputs by kind and no transparent output (the server keys components).

## 4. Unstated but expected
- Existing runs (VW-7 included) are `openai` and behave exactly as before.
- Both groups share the server, the key pools, the pages and the logs; the comparison is run against run.
- The drawn route, takes (video providers), voices and delivery do not read the choice.
- The procedure's picture rules and prompt form are the same for both; a provider-specific form, if ever wanted, goes behind the same value.
- Gemini's SynthID is noted in the run's delivery README line for the editor (one sentence), since the client may ask.

## 5. Edge cases
| Case | Handling |
|---|---|
| `vw start` without `--images` | refused with the question; no run created |
| `image_provider` other than the two | refused by the API model |
| a run created before this release | `openai` by the migration default |
| any attempt to change it later | no route exists; the page shows it read-only |
| Gemini keys missing or all cooling | the job requeues as the OpenAI path does; `/api/meta` shows the pool |
| the answer has no image part (a refusal, a safety block) | the job fails with the model's text as the reason, never retried blindly |
| the answer is JPEG | converted to PNG on the server, as the OpenAI path already converts |
| more than 14 pictures, or more than the kind count | refused by name at `generate_image`, before anything is paid |
| a region edit on Gemini | the sentence in the prompt; composite-back restores the outside; the edit record keeps how much the model changed outside, as today |
| a component on Gemini whose background is not clean green | the key-out leaves green fringes; the alpha line and the "clean edge" line catch it; the planner retries |
| a 4K tier set by config | priced at the 4K rate |
| a model id SK gives that differs from the default | one config line in `server/.env` (`VW2_GEMINI_IMAGE_MODEL`); the sample run confirms the request shape |
| the request shape differs on SK's model (Interactions instead of generateContent) | the client is one function; the sample tells; the fix is in that function alone |

## 6. Failure modes
- The request shape in Google's docs is in motion (generateContent with `imageConfig` versus the Interactions endpoint). The first paid picture on the VM is the test; nothing else in the system depends on which it is.
- The kind counts (6 / 5 / 3) are Google's for Pro; a different model id has different counts; they are config.
- Chroma keying can leave fringes on soft edges; the lines catch it; a better matte is a later step if components matter on Gemini.

## 7. Tests, written first
- `test_design120_a_pure.py` (server contract): run creation requires and stores the provider; the API refuses a missing or foreign value; the run's view and status carry it; old rows default to openai (the migration text).
- `test_design120_b_pure.py` (the request): `_queue_image` on a gemini run: provider, model, size as aspect and tier, no `background`; the kind counts refuse by name; the region sentence; the component green sentence; the OpenAI run unchanged.
- `test_design120_c_pure.py` (the worker): `_gemini_image` through a fake httpx: the generateContent URL and header, the payload (responseModalities, imageConfig, inlineData parents), the parse of the image part, JPEG to PNG, usage to cost, a 429 cooling the key and moving on, an answer with no image failing with its text; the chroma key-out; the ledger per provider.
- Plugin: `start` refuses without `--images`, posts it with; the start line shows it; 3.9 parse; procedure text loads.

## 8. Order
One commit per set (a, b, c, plugin + procedure), the suites after each, server 0.71.0, plugin 0.58.0, then deploy on SK's standing word in this message, the migration applying at start, then one paid sample picture on a gemini run to confirm the request shape (announced, about ₹12).

## 9. Self-review (before building)
- Dropped a per-shot override and any "change the provider" route: SK restricted it; immutability is a property, not a rule to enforce later.
- Put the provider on the run row, not in the visuals session: the session begins at the visuals stage, and the choice belongs to the run from its first second; one column, one migration.
- Kept `size` as the request field for both and let its shape differ by provider rather than adding a second field: the worker is the only reader.
- Did not add a second prompt form: SK's complaint about prompt length is a decision for both models; one form keeps the comparison honest.
- Priced Gemini flat per picture rather than by tokens: Google bills per image; the token figure would be a guess.
- Kept the drawn route, takes and checks out of the seam entirely; a grep for the provider name outside the image path is part of the build's last step.
- The one real uncertainty is the request shape; isolated in one function, tested with a fake, confirmed with one paid picture.

## 10. As built (28 Oct 2026, server 0.71.0, plugin 0.58.0)

- **Migration 009** adds `vw2_runs.image_provider` (default `openai`, check `openai|gemini`). `core.create_run` writes it; `NewRun.image_provider` is required (`Literal`); the run row carries it to the plugin and the page; `status` reports `image_provider`; `provider_of(run)` is the one reader.
- **The request** (`_queue_image`): `provider`; on gemini `model = GEMINI_IMAGE_MODEL`, `size = {aspect, tier}`, `chroma_key` for a component instead of `background: transparent`; the job's provider is `openai` or `gemini-image`; the generation record carries `provider`, `size` and `chroma_key`.
- **The parents on gemini:** 14 at most, counted by kind (object 6, character 5, style 3; `GEMINI_MAX_INPUTS`, `GEMINI_KIND_CAPS`), refused by name. A region edit gets the region in words; the composite-back is unchanged. A component's prompt asks for flat chroma green (`COMPONENT_BLOCK_GREEN`).
- **The worker:** `_gemini_image` posts `generateContent` with `responseModalities: ["IMAGE"]` and `imageConfig {aspectRatio, imageSize}`, the pictures as `inlineData` parts each announced by "Image k.", through the Gemini key pool with the OpenAI path's cooling; the first image part comes back in OpenAI's shape so the rest of `process_image` is shared; no image part fails the job with the model's words (`failure: no_image`); `key_out_green` makes the alpha for a component; `tick` claims both families. Cost `{provider: gemini, model, tier, inputs, tokens}`; `image_cost_inr` prices gemini flat ($0.134, $0.24 at 4K, $0.0011 an input) at the configured dollar rate; `visuals_spend` counts both families.
- **Config:** `GEMINI_IMAGE_MODEL` (`gemini-3-pro-image` until SK's id goes in `server/.env` as `VW2_GEMINI_IMAGE_MODEL`), `GEMINI_IMAGE_SIZE` (2K), the three prices.
- **Plugin:** `vw start --images openai|gemini`; without it the run is not created and the operator is asked; the start line says `images: …`.
- **Procedure:** the question before `vw start` and the gemini rules (14 by kind, the region in words, chroma green) in the intake step.
- **Tests:** `test_design120_a/b/c_pure.py` (4, 5, 5), `plugin/tests/test_design120.py` (2).

**Not covered until the sample.** The request shape on SK's exact model id (Google's docs show both `generateContent` with `imageConfig` and the Interactions endpoint); one paid picture from the VM through `_gemini_image` confirms it, about ₹12. The kind caps are Google's for the Pro model; another id has other caps (config). Chroma keying's edge quality on real components. The page shows the provider only through status, not as a header badge (a later line).
