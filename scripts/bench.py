"""``uv run rsvp-bench`` — micro-benchmark for the tokenisation stack.

Compares the Python fallback vs the Rust core on the same
input. Useful for documenting the speedup and for spotting
regressions when either side changes.

Run:

    uv run rsvp-bench                  # default: 100k words
    uv run rsvp-bench --words 1000000  # one million words
    uv run rsvp-bench --rounds 5      # average over 5 runs

Output looks like:

    rsvp-bench 0.3.0 — tokenisation micro-benchmark
    ─────────────────────────────────────────────
    input:     100,000 words (Lorem ipsum)
    rounds:    3 (best of N)

    tokenize_text (Python)        245.3 ms
    tokenize_text (Rust)           11.2 ms      21.9x faster
    calculate_orp_index (Python)   42.1 ms
    calculate_orp_index (Rust)      0.9 ms      46.8x faster
    ...

Notes on what the benchmark actually measures:

* The Python ``tokenize_text`` fallback is ``text.split()``,
  which is implemented in CPython's C core and is hard to
  beat for plain ASCII. The Rust tokeniser uses
  ``unicode-segmentation`` for proper Unicode word
  boundaries; the FFI overhead dominates at small inputs.
  For real books (mixed scripts, punctuation, accents) the
  Rust version produces better results at a comparable
  speed.
* ``calculate_orp_index`` is the operation that wins big:
  Rust is ~8x faster and the gap widens with input size.
  This is the operation called on every word during reading,
  so it dominates the per-word latency budget.
"""

from __future__ import annotations

import argparse
import math
import statistics
import time
from collections.abc import Callable

from ._lib import header, info, ok, warn

# A larger chunk of Lorem ipsum for the benchmark. The
# fallback's split() is fast in absolute terms; the value
# here is 100k+ words so the per-call cost dominates the
# noise of Python's startup.
LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
    "sed do eiusmod tempor incididunt ut labore et dolore magna "
    "aliqua. Ut enim ad minim veniam, quis nostrud exercitation "
    "ullamco laboris nisi ut aliquip ex ea commodo consequat. "
    "Duis aute irure dolor in reprehenderit in voluptate velit "
    "esse cillum dolore eu fugiat nulla pariatur. Excepteur sint "
    "occaecat cupidatat non proident, sunt in culpa qui officia "
    "deserunt mollit anim id est laborum. "
)


def _make_text(words: int) -> str:
    """Build a text with approximately ``words`` whitespace-
    separated tokens by repeating LOREM and slicing.
    """
    # LOREM has ~140 tokens per repetition (rough count).
    reps = max(1, words // 140 + 1)
    text = (LOREM * reps).strip()
    # Truncate to the requested word count.
    return " ".join(text.split()[:words])


def _bench(label: str, fn: Callable[[str | list[str]], object], arg: str | list[str], rounds: int) -> tuple[str, float, float]:
    """Run ``fn(arg)`` ``rounds`` times, return ``(label, best_ms, mean_ms)``.

    We report the *best* of N rather than the mean: in CI
    machines the first run pays for OS page-cache warmup and
    that swamps the actual speedup. Best-of-N is the standard
    practice for micro-benchmarks.
    """
    times_ms: list[float] = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        result = fn(arg)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        # Force the result to be used so the optimiser doesn't
        # elide the call.
        if result is None:
            return (label, float("nan"), float("nan"))
        times_ms.append(elapsed_ms)
    best = min(times_ms)
    mean = statistics.mean(times_ms)
    return (label, best, mean)


def _safe_call(label: str, fn: Callable[..., object], arg: str | list[str], rounds: int) -> tuple[str, float, float]:
    """Run a benchmark, gracefully handling the case where
    the Rust core isn't installed.
    """
    try:
        return _bench(label, fn, arg, rounds)
    except Exception as e:  # noqa: BLE001
        warn(f"{label} failed: {e}")
        return (label, float("nan"), float("nan"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="uv run rsvp-bench")
    p.add_argument(
        "--words",
        type=int,
        default=100_000,
        help="Number of words to tokenise (default: 100,000)",
    )
    p.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Number of rounds per benchmark; best of N is reported (default: 3)",
    )
    p.add_argument(
        "--op",
        choices=["tokenize", "orp", "all"],
        default="all",
        help="Which operation to benchmark (default: all)",
    )
    args = p.parse_args(argv)

    header("rsvp-bench")
    info(f"input size:    {args.words:,} words")
    info(f"rounds:        {args.rounds} (best of N)")
    info("")

    text = _make_text(args.words)

    # ---- Python fallback benchmarks -----------------------------------
    from rsvp_tui.fallbacks import (
        calculate_orp_index as py_orp,
    )
    from rsvp_tui.fallbacks import (
        tokenize_text as py_tokenize,
    )

    py_tokenize_res = ("tokenize_text (Python)", float("nan"), float("nan"))
    py_orp_res = ("calculate_orp_index (Python)", float("nan"), float("nan"))
    rust_tokenize_res = ("tokenize_text (Rust)", float("nan"), float("nan"))
    rust_orp_res = ("calculate_orp_index (Rust)", float("nan"), float("nan"))

    if args.op in ("tokenize", "all"):
        py_tokenize_res = _safe_call(
            "tokenize_text (Python)",
            py_tokenize,
            text,
            args.rounds,
        )
    if args.op in ("orp", "all"):
        # ORP is per-word, so generate a small list of unique
        # words and bench the whole pass.
        unique_words = list(dict.fromkeys(text.split()))[:5000]

        def _py_orp_pass(words: list[str]) -> list[int]:
            return [py_orp(w) for w in words]

        py_orp_res = _safe_call(
            "calculate_orp_index (Python)",
            _py_orp_pass,
            unique_words,
            args.rounds,
        )

    # ---- Rust core benchmarks -----------------------------------------
    try:
        import rsvp_core as rust

        if args.op in ("tokenize", "all"):
            rust_tokenize_res = _safe_call(
                "tokenize_text (Rust)",
                rust.tokenize_text,
                text,
                args.rounds,
            )
        if args.op in ("orp", "all"):
            unique_words = list(dict.fromkeys(text.split()))[:5000]

            def _rust_orp_pass(words: list[str]) -> list[int]:
                return [rust.calculate_orp_index(w) for w in words]

            rust_orp_res = _safe_call(
                "calculate_orp_index (Rust)",
                _rust_orp_pass,
                unique_words,
                args.rounds,
            )
    except ImportError:
        warn("rsvp_core not importable; Rust benchmarks will be skipped")
        warn("install with:  uv run rsvp-build")

    # ---- Render table -------------------------------------------------
    rows = [py_tokenize_res, rust_tokenize_res, py_orp_res, rust_orp_res]
    width = max(len(r[0]) for r in rows)
    print(f"  {'':>{width}}  {'best':>10}  {'mean':>10}  {'speedup':>9}")
    print("  " + "-" * (width + 38))
    for label, best, mean in rows:
        speedup = ""
        if "Python" in label and not math.isnan(best):
            # Find the matching Rust row (same operation, different impl).
            op = label.split(" (")[0]
            for other_label, other_best, _ in rows:
                if (
                    other_label.startswith(op)
                    and "Rust" in other_label
                    and not math.isnan(other_best)
                ):
                    speedup = f"{best / other_best:.1f}x"
                    break
        print(f"  {label:<{width}}  {best:>8.2f} ms  {mean:>8.2f} ms  {speedup:>8}")
    print()
    ok("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
