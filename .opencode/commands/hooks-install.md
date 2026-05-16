---
description: Install git enforcement hooks (core.hooksPath = .githooks)
---
Install the agentic-engineers SDLC enforcement hooks by running:

```
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
```

Then verify the hooks are active:
```
git config core.hooksPath
ls -la .githooks/
```

Report the result. If hooks are already installed, confirm they are up to date.
The hooks enforce:
- pre-commit: SPEC compliance, secret detection, YAML/JSON validity
- commit-msg: message format and length requirements  
- pre-push: agent YAML validation, test suite (non-blocking warnings)
