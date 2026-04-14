# Development workflow

Contains advice about an effective development workflow on Modal.

Modal is cloud-first and encourages a development loop that runs through the exact same cloud environment as will be used in production. Modal's fast container startup supports iterative testing during development, even though the code executes remotely.

The `modal run` command allows you to execute specific entrypoints or functions during development. Pass flags directly after the filename (e.g., `modal run app.py --flag value`) — the old `modal run app.py -- --flag` separator syntax no longer works. This creates an "ephemeral App" that stops automatically when the run completes. **Note:** ephemeral apps conflict when run concurrently with the same app name — use `modal deploy` for concurrent/multi-agent workloads. Similarly, `modal serve` creates an ephemeral App and runs it until the serve process is stopped (without calling any specific Function). This can be useful for developing web endpoint Functions: you serve the App and then make HTTP requests to the endpoints using `curl`, etc.

After you run `modal deploy`, the App will be live until it is explicitly stopped (`modal app stop`). However, it won't incur any costs until it is actually used. Stopping an App is a destructive action and cannot be reverted.

Modal's "Environment" segregation concept can also be useful for development. For example, you may have separate `dev` and `prod` environments. Most CLI commands accept an `--env` option that selects the environment to use (e.g. `modal deploy --env=dev`).

Environment segregation during development can be useful when:

- Your App uses resources like `modal.Dict`, `modal.Queue`, etc. and you do not want your development Apps to interfere with resources used in production
- You are developing a system that uses Function lookups (`modal.Function.from_name`), which can only be performed against a _deployed_ App
- You would like to direct some actual traffic to the development App before promoting it to production
