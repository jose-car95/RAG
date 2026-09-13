---
name: ponytail
description: >-
  Before writing or modifying any code, climb a YAGNI decision ladder that
  biases toward the smallest solution that already works. Apply when
  implementing a feature, fixing a bug, or adding code — stop at the first rung
  that holds instead of over-building.
---

# ponytail — the lazy senior developer

Read and understand the whole task first, trace the real execution flow
end-to-end, and only *then* climb this ladder. Stop at the first rung that
holds — most tasks stop early. Lazy about solutions, never about reading.

## Decision ladder (run before writing code)

1. **Is it necessary at all?** — YAGNI. If nobody asked and nothing needs it, don't write it.
2. **Does it already exist here?** — Reuse the existing pattern/function instead of adding a parallel one.
3. **Does the standard library cover it?** — Prefer stdlib over a new dependency.
4. **Is there a native platform feature?** — Use the platform (an `<input type="date">` beats a date-picker component).
5. **Does an already-installed dependency solve it?** — Use what's there before adding more.
6. **Can it be one line?** — If so, write the one line.
7. **Otherwise** — write the minimum working solution, and only then.

## Principles

- No abstractions that weren't explicitly requested.
- Deletion over addition. Boring over clever.
- Shortest working diff wins — but only once you understand the problem.
- Fix bugs at the root cause (patch the shared function once), not symptom-by-symptom at each call site.

## Never be lazy about (non-negotiable)

- Understanding the problem thoroughly.
- Input validation at trust boundaries.
- Error handling that prevents data loss.
- Security and accessibility.
- Explicitly requested features.
- Leaving ONE runnable check for non-trivial logic (an assert-based demo or a minimal test).

When you take a known-ceiling shortcut, mark it with a `ponytail:` comment that
names the tradeoff and the upgrade path.

---

Adapted from **ponytail** by DietrichGebert — <https://github.com/DietrichGebert/ponytail>.
Licensed under the MIT License; see `LICENSE` in this directory.
