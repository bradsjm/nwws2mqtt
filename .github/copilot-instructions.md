# Python Code Generation Instructions (Python 3.12+)

## Libraries
- **Standard Libraries:** Prefer built-in libraries over 3rd party when possible.
- **3rd Party Library Use:** Use only well-maintained libraries with active communities. Avoid libraries with known security vulnerabilities or poor documentation.
- **Documentation**: Always lookup the latest SDK details for 3rd party libraries using available tools.

## Type System (Pyright Strict)
- **Target Version:** Use Python 3.12+ features (e.g. pattern matching, Self type).
- **Complete Typing:** Type ALL function parameters, return values, class attributes, and critical variables.
- **Modern Typing Only:**
  - **Type Aliases:** `type Name = Definition` (PEP 695); never `typing.TypeAlias`/`NewType`.
  - **Unions:** Use `X | Y` (not `Union[X, Y]`).
  - **Generics:** Use `list[int]`, `dict[str, int]` (not `List[:]`, `Dict[:]`).
- **Optional Types:** Use `X | None`; always explicitly `return None` when applicable.
- **No `Any`:** NEVER use `Any`. Use explicit types, `TypeVar`, `Protocol`, or `object`.
- **Data Structures:**
  - Limit tuples to 3 elements for small, immutable groups.
  - Use dataclasses/pydantic for any structured or complex data.
  - AVOID nested types like `dict[str, tuple[...]]`; prefer named types.
- **Dynamic and Factory Typing:**
  - When implementing factory functions (`Callable[..., SomeType]`), explicitly type parameters like `**kwargs` as `**kwargs: object` or a more specific `typing.Dict` if the structure is known.
  - Ensure factory functions return the most specific type possible.
  - Use `isinstance()` for runtime type checking of arguments passed via `**kwargs`.
  - Use `typing.cast()` judiciously and with string literal type expressions (`cast("list[dict[str, str]]", ...)`) when necessary to guide the type checker, especially when dealing with data structures from configurations.

## Style & Formatting (Ruff Enforcement)
- **PEP 8 Compliance:** Follow naming conventions (`snake_case` for functions/variables; `PascalCase` for classes).
- **String Interpolation:** Use f-strings exclusively.
- **Unused Variables:** Remove or prefix with underscore (`_`) if they must be kept (e.g., in function signatures for compatibility).
- **Import Formatting**: Ensure import statements are automatically sorted and formatted according to project standards (as enforced by Ruff).
- **Line Length:** Limit lines to 88 characters.
- **Ruff Format**: Use the shell tool to run the `ruff format` command to resolve simple formatting issues and `ruff check --fix` to automatically fix linting issues where possible.

## Structure & Complexity
- **Imports:** Always use absolute imports.
- **Function Parameters:** Limit to 5 arguments; group related parameters using dataclasses.
- **Complexity Limits:**
  - Cyclomatic complexity < 10.
  - ≤ 12 branch statements per function.
  - ≤ 50 logical statements per function.
- **Testability:** Write pure functions and employ dependency injection. Avoid hidden state.

## Implementation Details
- **Data Representation:** Use dataclasses or pydantic models for structured data.
- **Properties:** Use `@property` for managed attribute access.
- **Efficiency:** Use comprehensions and generators for data transformation and large datasets.
- **Output & Logging:** Use the existing logging library (or `logging` if none) for output; never use `print()`.
- **Design Patterns:** Apply idiomatic patterns (e.g., context managers, factories) where it will reduce complexity or improve understandability.
- **Inline Simple Functions:** Avoid creating functions that have only a single line of code; prefer to inline such logic directly.

## Error Handling
- **Granular Exceptions:** Always catch specific exceptions (e.g., `except ValueError:`, `except requests.HTTPError:`) for external or I/O operations.
- **Specific Exception Types**: Use appropriate built-in exception types (e.g., `ValueError`, `TypeError`, `FileNotFoundError`, `ConnectionError`) for specific error conditions. Use `TypeError` when an argument or object is of an inappropriate type. Create exception messages by assigning the message string to a variable first, rather than directly in the exception constructor, for clarity and adherence to style guidelines.
- **AVOID** bare except blocks except as a fallback for unexpected errors with # noqa: BLE001 comment.

## Documentation
- **Docstrings:** Add PEP 257 docstrings for all public modules, classes, functions, and methods. Include examples in public facing docstrings.
- **Style:** Use active, imperative voice in docstrings (e.g., "Return...", "Calculate...").
- **Supporting Files**: Only generate examples or documentation files after confirming with the user.

## Testing
- **Pytest:** Use pytest for unit tests.
- **Linting**: Generated code MUST pass `ruff check --fix` without reporting any errors or warnings.
- **Type Checking**: Generated code MUST pass `basedpyright` in strict mode without reporting any errors or warnings.
- **Diagnostic Resolution**: Prioritize addressing and resolving ALL diagnostics reported by the environment (linting and type checking) as a critical step before considering code complete.
