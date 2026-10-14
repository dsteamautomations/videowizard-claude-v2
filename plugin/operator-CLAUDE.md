# VideoWizard operator profile

- Use `/vw` for everything about a video run. The server decides the next step; follow it.
- Do not debug, read code, open logs or cloud consoles. On any error, file a defect with `vw defect` and stop.
- A stage is accepted only by the operator's explicit yes to your question, passed verbatim as `--quote`.
- Paid steps are information, not a question: say which provider is used and proceed.
- One run at a time on this machine; do not write files outside `runs/<code>/`; no reports unless asked.
