# App structure

Contains guidance on structuring the source code for a Modal App.

A Modal App does not need to involve anything more than a single Python file: the remote environment, resource configuration, and function logic can be specified in one place.

More complicated Apps _can_ be organized into multiple files. It's best to structure a multi-file App as a Python _package_ and to invoke the Modal CLI in "module mode" (`modal deploy -m ...`) so that the entire package gets included in the remote container.

Additional local dependencies can be included in the `modal.Image` definition, e.g. using `modal.Image.add_local_file` or `modal.Image.add_local_directory`.

Any code that is in _global scope_ of the App source will execute both locally during deployment and in all remote containers during container startup. This means that global scope code has to behave the same way in both environments or else it will crash. Avoid referencing files, reading environment variables, or importing packages in global scope if you don't take care to make sure they are available in both contexts.

Additionally, avoid putting any slow operations in global scope, as they will impact container startup time. Note that the `.from_name()` constructors on Modal objects are _lazy_ for this reason.
