# VideoWizard operator workspace

This folder is only for operating video runs with the `vw` plugin. Rules for every session here:

- Use `/vw:vw` for everything about a video run. The server decides the next step; follow it.
- Do not debug, read code, open logs or cloud consoles. On any error, file a defect with `vw defect` and stop.
- A stage is accepted only by the operator's explicit yes to your question, passed verbatim as `--quote`.
- Paid steps are information, not a question: say which provider is used and proceed.
- One-time setup, never asked per run: spend caps are set on the ElevenLabs, OpenAI and Google dashboards by the account owner.
- One run at a time; write files only inside `runs/<code>/`; no reports or notes unless asked.
