# design/92: a busy run never times out a read (L60, with L59)

24 Oct 2026. SK's go, after defects 22 and 23 on VW-7: "fix this immdly". Built at once; one deploy.

## What happened

- **Defect 22.** Finishing pass 1 of the reference round ran 13 image searches inside the request, holding VW-7's run lock for minutes.
- **Defect 23.** Every new picture's check (the Gemini call, the light measured against up to six footage frames, the session read and written) ran inside the run lock in the image worker. A batch of 10 pictures held the lock for minutes.
- **The effect.** `vw visuals status` and the visuals page's data both take the same lock before reading, so they waited, the page was slow, and the tool gave up after 60 s. The assistant read that as a defect.
- **Worse after a defect.** Once a defect was open, both reads stopped at once, because the lock path also refuses on an open defect.
- **Size.** The visuals session had grown to 655 KB, and the page reads it every 15 s.

## What changes

1. **The image check runs before the lock.**
   - The worker records the picture as a candidate under the lock, marked as being checked. Then it runs the check with no lock held, and takes the lock only to save the result, and to queue the one fix round when a must line failed.
   - A picture whose record changed in the meantime (rejected, or replaced by another job) keeps what it has.
   - The page shows "being checked" until the result arrives.
2. **The searches of the reference round run before the lock** (L59). The pass is checked and the searches run first, then the lock is taken only to save the results.
3. **Reads never wait and never stop on a defect.**
   - `vw visuals status` and the visuals page's data take the lock only if it is free at that moment. If it is busy, they answer from the stored session without repairing it, and say `busy`.
   - An open defect blocks writes only. The reads stay readable, so the page still loads and the assistant can still see where the run is.
4. **The session is kept small.** Measured on VW-7 (24 Oct): 654 KB. The pictures' check records are the largest part (182 KB): 42 KB of pass conditions their checklists already hold, and 52 KB of failed must lines that repeat whole lines. Both are now stored without the pass condition a checklist holds; `expand` puts it back for the page and the fix round. A line no checklist holds (the light) keeps its own. About 90 KB less on VW-7.
5. **The page's buttons run off the event loop.** One server process serves every request, and three page handlers (the visuals, review and voices buttons) ran their blocking work on its event loop. While a button worked (the round's searches took minutes), every other page and API call waited. The body is now read on the loop and the work runs on a worker thread.
6. **A timeout is "busy", not a defect.**
   - When a read times out, the tool tries again every 15 s for three minutes, as it already does for a broken connection. Then it says "the server is busy … not a defect: wait a minute and ask again" (`action: wait`).
   - A write that times out says the server may still be doing it: check the status, and repeat only if it didn't happen.

7. **Defect 24 (VW-7), folded in.** A picture for a named image shot (`image --kind keyframe --shot B01_S2`) was refused with the bind-and-packet rule of the first video shot sharing its element (design/77 L35): the gate looked at every video shot of the element and ignored `--shot`. The gate now follows the named shot: an image shot is a still, with no bind or packet; a named video shot still needs its own packet; with no shot named, it works as before.

## Tests first

- The worker's check runs while no lock is held, and only the save is locked. A changed record keeps what it has. A failed must line still queues one fix.
- The worker no longer runs the check inside `finalize_image`, and marks the picture as being checked.
- Status and page data with the lock busy: no session write, and `busy` is said. With a defect open, the reads still answer.
- The round's searches run before the lock.
- The tool: a read that times out is tried again, then reported as `wait`, never as a defect.
- Defect 24: a keyframe for a named image shot passes; for a named video shot without its packet, and with no shot named, it is refused as before.

## As built

- Server 0.40.0, plugin 0.38.0.
- The tool answers `wait` (not `tell_builder`) for a read that keeps timing out, and for a write that times out. The help (`vw.md`) says what `wait` means: tell the operator in one line, wait a minute, check the status, then carry on.

## Not covered

- The rest of the session stays as it is: answer forms 67 KB, feedback records 67 KB, searches 61 KB, gap timing 53 KB, generation records 51 KB, server checklists 48 KB. Moving any of them out of the session is a larger change, left for later if the reads stay slow.
- Requests that are slow for other reasons (a large session read, storage latency) still take that time. The reads are no longer queued behind the work.
- `server/tests` (Docker).
