# actorcompiler_py

A Python port of the Flow actor compiler. It reads `X.actor.cpp` or `X.actor.h` and writes `X.actor.g.cpp` or `X.actor.g.h`, so the build needs no C# toolchain.

- Source: upstream FoundationDB commit 41ffc89f (the last tree that carried it, 2026-08), files unchanged.
- Licence: Apache-2.0, as the rest of this tree.
- Run: `PYTHONPATH=flow python -m actorcompiler_py <input> <output> [--generate-probes] [--disable-diagnostics]`.
- `compare_actor_output.py` compares its output with the C# compiler's, where mono or .NET is available.
