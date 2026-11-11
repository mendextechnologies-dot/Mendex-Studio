# MENDEX ENGINEERING STUDIO v1.9 — PARAMETRIC DESIGN ENGINE

## 1. Safe AST Evaluation Architecture

The `ParametricDesignEngine` evaluates algebraic equations without arbitrary Python `eval()`. It utilizes Python's `ast` (Abstract Syntax Tree) module to restrict operations to approved mathematical functions and operators:

- **Approved Binary Operators**: Add, Subtract, Multiply, Divide, Power, Modulo.
- **Approved Unary Operators**: Positive, Negate.
- **Approved Functions**: `sqrt`, `abs`, `sin`, `cos`, `tan`, `exp`, `log`, `log10`, `min`, `max`.
- **Approved Constants**: `pi`, `e`.

---

## 2. Dependency Graph & Change Impact Analysis

When an engineer modifies a named parameter ($f_{sw}$, $L$, $C$, $V_{in}$):

1. **Dependency Traversal**: Identifies all expressions referencing the changed identifier.
2. **Topological Recalculation**: Recursively updates downstream parameters.
3. **Component Binding Update**: Updates any component value bound to the variable name.
4. **Change Impact Preview**:
   - Lists old value vs new value.
   - Lists recalculated parameters.
   - Identifies affected component designators.
   - Marks affected native files and simulation runs for re-verification.
