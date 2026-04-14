# Function types

Explains the differences between the function and class patterns in Modal.

Modal Functions can be written either as simple Python functions and wrapped with `@app.function()` or as classes that are wrapped with `@app.cls()`.

The class pattern is useful in the following contexts:

1. Container lifecycle logic

Classes can have methods decorated with `@modal.enter()` and `@modal.exit()`. These methods will run just once during the container lifecycle. This allows you to avoid performing expensive setup operations (e.g., loading model weights) while handling every input:

```python
@app.cls()
class MyClass:
    @modal.enter()
    def setup(self):
        ...  # Runs once per container

    @modal.method()
    def call(self, ...):
        ...  # Runs for every input
```

More information: https://modal.com/docs/guide/lifecycle-functions

2. Function parameterization

Parametrized Functions allow you to write templated logic with behavior that can be modified at call time by passing container-level parameters.

Unlike Function inputs, each unique parameterization defined a _distinct pool of containers_ with its own autoscaling. Parameterization is most useful when the parameters modify _container lifecycle_ logic or when you want to segregate inputs in different containers.

```python
@app.cls()
class MyClass:

    name: str = modal.parameter()

    @modal.enter()
    def setup(self, ...):
        ...  # Can reference self.name

    @modal.method()
    def call(self, ...):
        ...  # Can also reference self.name

# At call time, you pass a specific name to use
MyClass(name="...").call.remote(...)
```

More information: https://modal.com/docs/guide/parametrized-functions

3. Runtime configuration

Classes can also be invoked at runtime using the `.with_options()` method to override aspects of the Function configuration.

```python
@app.cls(gpu="A100")
class MyClass:
    @modal.method()
    def cal(self, ...):
        ...

# At call time, override the GPU configuration
MyClass.with_options(gpu="H100")().call.remote(...)
```

As with Parameterized Functions, each unique configuration will define a separate independently-autoscaling container pool.
