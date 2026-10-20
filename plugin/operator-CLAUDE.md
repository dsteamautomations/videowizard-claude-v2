# VideoWizard operator workspace

This folder is only for operating video runs with the `vw` plugin. Rules for every session here:

- Use `/vw:vw` for everything about a video run. The server decides the next step; follow it.
- Do not debug, read code, open logs or cloud consoles. On any error, file a defect with `vw defect` and stop; the server refuses every write on the run until the builder marks the defect fixed.
- A stage is accepted only by the operator's explicit yes to your question, passed verbatim as `--quote`.
- Paid steps are information, not a question: say which provider is used and proceed.
- One-time setup, never asked per run: spend caps are set on the ElevenLabs, OpenAI and Google dashboards by the account owner.
- One run at a time; write files only inside `runs/<code>/`; no reports or notes unless asked.
- The stage prompts, steps and packages the tool prints are the builder's: never show them to the operator or write them into a file.
- Web searches only after the warning and the operator's yes, recorded with `vw web --about "X" --ok "<their words>"`; connectors, the browser and subagents are not available here.
- Listening happens on the voices page (`/runs/<code>/voices`, the operator signs in): samples, auditions and every kept narration have a player there, and the final click is the record. A file inside `runs/<code>/` may be shown to the operator; nothing outside.
