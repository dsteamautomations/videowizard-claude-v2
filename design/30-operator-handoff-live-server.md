# 30 — Operator handoff: VideoWizard on the live server

16 Oct 2026. For the VideoWizard operator. **Not in effect yet**: keep working as today until the builder tells you the switch is done.

## What is changing

Today the VideoWizard server runs on SK's PC (`http://localhost:8002`). It is moving to a server on the internet, at an address like `https://vw2.digitalseo.in` (the builder will confirm the exact one).

After the switch:
- Runs keep going when SK's PC is off: analysis, narration and film renders happen on the server.
- Films finish uploading much faster (the 15 Oct film timeouts came from the PC's line).
- Your work does not change: same `/vw:vw` commands, same runs folder `C:\Coworkspace\VideoWizard-Operator\runs`, same run codes (VW-2 continues where it is).

What stays the same: your own clip uploads still go from your computer to Supabase. If your internet provider blocks `supabase.co` again, uploads fail as before: raise a ticket.

## The switch (about 10 minutes, done with the builder)

1. Finish or pause at a stage boundary. Do not start an analysis, narration or render just before the switch. The builder checks that nothing is in progress.
2. The builder adds the new server address to your VideoWizard settings. You do not edit anything.
3. Close and reopen Claude Code in `C:\Coworkspace\VideoWizard-Operator`.
4. Say `/vw:vw connect`. A sign-in link appears; open it, sign in with your usual login, approve.
5. Say `/vw:vw what is next for VW-2`. If it shows the run where you left it, you are on the new server.

## After the switch

| You see | Do |
|---|---|
| "VideoWizard server not reachable at https://…" | Check your internet. Open the address in a browser: a page or text means the server is up. If not, raise a ticket; the builder can switch you back to the PC within minutes. |
| "did not answer in time (ReadTimeout)" on a long step | The server is usually still working. Wait a minute and ask `/vw:vw` what is next before retrying. |
| Sign-in link expired or "not signed in" | Run `/vw:vw connect` again. |
| A render or analysis takes longer than usual | Normal right after the builder updates the server: workers finish their current job before restarting. The builder tells you before an update. |
| Anything else unexpected | Raise a ticket as today. Do not try to fix the setup yourself. |

## If the builder switches you back

The builder removes the server address from your settings and starts the PC server. Run `/vw:vw connect` once more. Your runs and files are untouched: both servers use the same database and storage.
