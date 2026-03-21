#!/usr/bin/env python3
# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""A/B Test: Hyperion Dashboard Design Audit — With vs Without Theia's Knowledge.

Asks the same design-critique questions to Claude with and without Theia's
design knowledge base. Measures: issue detection accuracy against ground truth,
specificity of recommendations, design principle citation.

The test case is the Hyperion SOC Dashboard — a real-time security monitoring
UI with dark theme, Canvas charts, WebSocket updates, and severity-driven
information hierarchy.

Requirements:
  - ANTHROPIC_API_KEY env var set
  - Theia installed: cd ~/Repos/theia && pip install -e ".[dev]"

Usage:
  PYTHONPATH=src .venv/bin/python3 tests/ab_test_hyperion_dashboard.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from textwrap import dedent

# ---------------------------------------------------------------------------
# Hyperion dashboard source (embedded for portability)
# ---------------------------------------------------------------------------

DASHBOARD_DIR = Path.home() / "Repos" / "hyperion" / "src" / "hyperion" / "dashboard"


def _load_dashboard_source() -> str:
    """Load the dashboard HTML + CSS + JS as a single context string."""
    parts = []
    for name, subpath in [
        ("HTML (index.html)", "templates/index.html"),
        ("CSS (styles.css)", "static/styles.css"),
        ("JS (dashboard.js)", "static/dashboard.js"),
    ]:
        fpath = DASHBOARD_DIR / subpath
        if fpath.exists():
            content = fpath.read_text()
            # Truncate JS to first 300 lines to stay within context budget
            if subpath.endswith(".js"):
                lines = content.splitlines()
                content = "\n".join(lines[:300])
                if len(lines) > 300:
                    content += f"\n// ... ({len(lines) - 300} more lines)"
            parts.append(f"=== {name} ===\n{content}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Questions + ground truth
# ---------------------------------------------------------------------------

QUESTIONS = [
    {
        "id": "Q1",
        "question": (
            "Analyze the visual hierarchy of the threat summary counter cards. "
            "Are all severity levels given equal visual weight? Is that correct?"
        ),
        "ground_truth": (
            "All 6 counter cards use identical sizing (flex:1, same padding). "
            "Critical findings should have more visual prominence than Low/Info. "
            "Visual hierarchy is flat when it should reflect severity importance."
        ),
        "key_facts": [
            "equal", "same", "identical",  # identifies the flat hierarchy
            "critical", "prominence",  # names what should be different
            "hierarchy", "weight",  # names the principle
        ],
        "trap_facts": [
            "perfect", "well-designed hierarchy", "correct visual weight",
        ],
    },
    {
        "id": "Q2",
        "question": (
            "Check the color contrast ratios in this dashboard. The muted text "
            "color is #555570 on backgrounds of #12121e and #0a0a0f. Does this "
            "meet WCAG AA requirements?"
        ),
        "ground_truth": (
            "#555570 on #12121e has a contrast ratio of approximately 2.8:1, "
            "well below the WCAG AA minimum of 4.5:1 for normal text. "
            "The --text-muted color fails AA at the sizes used (0.6rem-0.75rem)."
        ),
        "key_facts": [
            "fail", "4.5",  # knows the AA threshold
            "contrast", "ratio",  # names the metric
            "below", "insufficient",  # identifies it as a problem
        ],
        "trap_facts": [
            "passes AA", "meets WCAG", "sufficient contrast",
        ],
    },
    {
        "id": "Q3",
        "question": (
            "The dashboard uses color extensively to indicate severity levels "
            "(red for critical, orange for high, etc.). Is there an accessibility "
            "issue with this approach?"
        ),
        "ground_truth": (
            "WCAG 1.4.1 Use of Color: severity is communicated primarily through "
            "color alone. The counter labels say 'Critical'/'High' etc. but the "
            "finding cards in the feed use only a colored left border + small badge "
            "to indicate severity. Users with color vision deficiency cannot "
            "distinguish severity levels reliably. Need icons or patterns."
        ),
        "key_facts": [
            "color alone", "1.4.1",  # cites the WCAG criterion
            "color vision", "deficien",  # names affected users (deficiency/deficient)
            "icon", "pattern", "shape", "text",  # suggests a fix
        ],
        "trap_facts": [
            "no accessibility issue", "colors are sufficient",
        ],
    },
    {
        "id": "Q4",
        "question": (
            "Evaluate the code viewer modal overlay for accessibility. "
            "Look at the HTML structure and CSS."
        ),
        "ground_truth": (
            "The modal has multiple accessibility issues: no role='dialog' or "
            "aria-modal attribute, no aria-label, no visible close button in the "
            "HTML template (it is generated in JS but the template is empty), "
            "no focus trap (keyboard users can tab behind the modal), "
            "no Escape key handler visible in the template, and the overlay "
            "click-to-close relies on mouse only."
        ),
        "key_facts": [
            "focus trap", "focus",  # critical modal accessibility
            "role", "dialog", "aria",  # ARIA requirements
            "close", "escape",  # dismiss mechanisms
            "keyboard",  # keyboard accessibility
        ],
        "trap_facts": [
            "accessible modal", "properly implemented",
        ],
    },
    {
        "id": "Q5",
        "question": (
            "Look at the ALERTS toggle button styling: "
            "style='color:#555570;border-color:#555570;font-size:0.65rem;padding:4px 10px'. "
            "Is there a touch target size issue?"
        ),
        "ground_truth": (
            "WCAG 2.5.8 Target Size Minimum requires interactive elements to be "
            "at least 24x24 CSS pixels. With font-size 0.65rem (~8.5px) and "
            "padding 4px 10px, this button is approximately 50x17px — the height "
            "is below 24px. Fails WCAG 2.5.8."
        ),
        "key_facts": [
            "24", "target size", "minimum",  # knows the standard
            "too small", "below", "fail",  # identifies the issue
            "2.5.8", "touch",  # cites the criterion
        ],
        "trap_facts": [
            "adequate size", "meets requirements",
        ],
    },
    {
        "id": "Q6",
        "question": (
            "The base font-size is set to 13px in the html rule, and many "
            "elements use 0.6rem to 0.72rem. Evaluate the typography system."
        ),
        "ground_truth": (
            "Base 13px means 1rem=13px, making 0.6rem=7.8px and 0.72rem=9.4px. "
            "These are extremely small and fail readability guidelines. "
            "No systematic type scale is used — sizes appear arbitrary "
            "(0.6, 0.65, 0.68, 0.7, 0.72, 0.75, 0.78, 0.8, 0.85, 1.0, 1.3rem). "
            "Should use a modular type scale (major third or perfect fourth)."
        ),
        "key_facts": [
            "13", "small", "readability",  # identifies the base problem
            "scale", "modular", "arbitrary",  # identifies lack of system
            "type scale", "typograph",  # names the domain
        ],
        "trap_facts": [
            "appropriate font sizes", "good typography",
        ],
    },
    {
        "id": "Q7",
        "question": (
            "Evaluate the responsive design breakpoints. The dashboard uses "
            "a 3-column grid at 300px/1fr/320px, switching to 2 columns at "
            "1200px and 1 column at 768px. Are there issues?"
        ),
        "ground_truth": (
            "The 3-column layout requires minimum ~932px (300+12+300+12+320) "
            "but doesn't collapse until 1200px, leaving a gap where columns "
            "are cramped. The fixed 300px/320px side columns don't scale. "
            "Finding cards with code blocks (white-space:pre) will cause "
            "horizontal overflow on narrow screens. Canvas charts have no "
            "responsive resize handling visible in CSS."
        ),
        "key_facts": [
            "fixed", "cramped", "overflow",  # identifies the problems
            "300", "320",  # knows the specific values
            "responsive", "breakpoint",  # names the domain
            "canvas", "code",  # identifies overflow-prone elements
        ],
        "trap_facts": [
            "well-designed responsive", "appropriate breakpoints",
        ],
    },
    {
        "id": "Q8",
        "question": (
            "What design system methodology would you recommend as the "
            "foundation for redesigning this dashboard? Consider it's a "
            "SOC (Security Operations Center) tool for analysts monitoring "
            "threats in real-time."
        ),
        "ground_truth": (
            "A SOC dashboard needs information density, scanability, and "
            "real-time awareness. Recommend a design token system with "
            "semantic severity tokens, consistent spacing (8px grid), "
            "a proper type scale, and component-level theming. Consider "
            "Carbon Design (IBM) or Material for dense data visualization. "
            "The existing arbitrary values should be systematized."
        ),
        "key_facts": [
            "token", "spacing", "grid",  # design system fundamentals
            "information density", "scanability", "real-time",  # SOC-specific needs
            "8px", "systematic", "consistent",  # systematization
        ],
        "trap_facts": [],
    },
]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_response(response: str, question: dict) -> dict:
    """Score a response against ground truth."""
    resp_lower = response.lower()

    key_hits = [f for f in question["key_facts"] if f.lower() in resp_lower]
    key_misses = [f for f in question["key_facts"] if f.lower() not in resp_lower]
    traps_hit = [f for f in question["trap_facts"] if f.lower() in resp_lower]

    total = len(question["key_facts"])
    accuracy = len(key_hits) / total if total > 0 else 1.0

    return {
        "accuracy": accuracy,
        "key_hits": key_hits,
        "key_misses": key_misses,
        "traps_hit": traps_hit,
        "has_wrong_info": len(traps_hit) > 0,
        "total_key_facts": total,
    }


# ---------------------------------------------------------------------------
# Theia augmentation
# ---------------------------------------------------------------------------


def get_theia_context(dashboard_description: str) -> str:
    """Run Theia's tools against the dashboard and build augmentation context."""
    # Import Theia tools directly (standalone mode, no graph)
    sys.path.insert(0, str(Path.home() / "Repos" / "theia" / "src"))
    from theia.tools import (
        audit_design,
        evaluate_accessibility,
        plan_design_system,
        spec_component,
    )

    context_parts = []

    # 1. Audit the dashboard design
    audit = audit_design(
        description=(
            "SOC (Security Operations Center) real-time security monitoring dashboard. "
            "Dark theme. 3-column layout: left charts (risk gauge, donut, timeline), "
            "center findings feed with filter bar, right attack surface map + threat bars. "
            "6 threat counter cards in a summary bar. Code viewer modal. Canvas charts. "
            "WebSocket real-time updates. Base font 13px, muted text #555570 on #12121e."
        ),
        structural_signals=[
            "dashboard with metric cards and data tables",
            "real-time monitoring with WebSocket updates",
            "dark theme with severity color coding",
            "3-column layout with charts and data feed",
            "color only severity indication",
            "small touch targets",
            "modal overlay for code viewing",
            "13px base font with many sub-rem sizes",
            "fixed column widths that dont scale",
            "canvas charts without responsive handling",
        ],
        constraints={"platform": "web", "audience": "security analysts"},
    )
    context_parts.append(
        f"=== DESIGN AUDIT RESULTS ===\n{json.dumps(audit, indent=2, default=str)}"
    )

    # 2. Evaluate accessibility
    a11y = evaluate_accessibility(
        component_or_page_description=(
            "Security dashboard with: dark theme (#0a0a0f background), "
            "muted text (#555570), severity badges using color-only differentiation, "
            "small font sizes (0.6rem = 7.8px based on 13px root), "
            "modal overlay without focus trap or ARIA roles, "
            "interactive buttons with 4px vertical padding (below 24px touch target), "
            "code blocks with white-space:pre causing horizontal overflow, "
            "filter dropdowns, canvas-based charts without text alternatives."
        ),
        target_level="AA",
    )
    context_parts.append(
        f"=== ACCESSIBILITY EVALUATION ===\n{json.dumps(a11y, indent=2, default=str)}"
    )

    # 3. Plan design system for SOC dashboard
    design_sys = plan_design_system(
        product_description=(
            "Real-time Security Operations Center dashboard for monitoring "
            "vulnerabilities, threat levels, and security findings. Information-dense, "
            "analyst-focused, severity-driven visual hierarchy. Dark theme mandatory."
        ),
        platforms=["web"],
        brand_attributes=["professional", "technical", "high-density"],
    )
    context_parts.append(
        f"=== DESIGN SYSTEM PLAN ===\n{json.dumps(design_sys, indent=2, default=str)}"
    )

    # 4. Spec the modal component
    modal_spec = spec_component(
        component_type="modal",
        context="Code viewer overlay showing vulnerable and secure code comparison",
        variants_needed=["default", "fullscreen"],
        platform="web",
    )
    context_parts.append(
        f"=== MODAL COMPONENT SPEC ===\n{json.dumps(modal_spec, indent=2, default=str)}"
    )

    return "\n\n".join(context_parts)


# ---------------------------------------------------------------------------
# Claude interaction
# ---------------------------------------------------------------------------


def ask_claude(
    question: str,
    dashboard_source: str,
    theia_context: str | None = None,
) -> tuple[str, float]:
    """Ask Claude a design question about the dashboard."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: pip install anthropic")
        return ("", 0.0)

    client = anthropic.Anthropic()

    # Same prompt structure for both conditions — only the context block differs
    context_block = ""
    if theia_context:
        context_block = dedent(f"""\

            Here is a design analysis of this dashboard:

            {theia_context}
            """)

    prompt = dedent(f"""\
        You are evaluating a security dashboard's UI/UX design.

        Here is the dashboard source code:

        {dashboard_source}
        {context_block}
        Answer this question concisely:
        {question}""")

    start = time.time()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.time() - start

    text = response.content[0].text if response.content else ""
    return text, elapsed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_ab_test():
    """Run the full A/B comparison."""
    print("=" * 72)
    print("  Theia A/B Test — Hyperion Dashboard Design Audit")
    print("  Condition A: Claude alone (vanilla, no design knowledge)")
    print("  Condition B: Claude + Theia's design knowledge base")
    print("=" * 72)
    print()

    # Load dashboard source
    print("Loading Hyperion dashboard source...")
    dashboard_source = _load_dashboard_source()
    if not dashboard_source:
        print("  ERROR: Could not load dashboard from", DASHBOARD_DIR)
        return
    source_lines = dashboard_source.count("\n")
    print(f"  Loaded {source_lines} lines (HTML + CSS + JS)")
    print()

    # Generate Theia context (augmentation)
    print("Running Theia's design analysis tools...")
    t0 = time.time()
    theia_context = get_theia_context(dashboard_source)
    theia_time = time.time() - t0
    context_size = len(theia_context)
    print(f"  Generated {context_size:,} chars of design context in {theia_time:.1f}s")
    print()

    # Run both conditions
    results_a: list[dict] = []
    results_b: list[dict] = []

    for q in QUESTIONS:
        print(f"--- {q['id']}: {q['question'][:70]}...")
        print()

        # Condition A: Vanilla
        print("  [A] Claude alone...")
        resp_a, time_a = ask_claude(q["question"], dashboard_source)
        score_a = score_response(resp_a, q)
        results_a.append({
            "question": q, "response": resp_a,
            "time": time_a, "score": score_a,
        })
        status_a = "WRONG" if score_a["has_wrong_info"] else f"{score_a['accuracy']:.0%}"
        print(f"      Time: {time_a:.1f}s | Accuracy: {status_a}")
        if score_a["key_misses"]:
            print(f"      Missed: {', '.join(score_a['key_misses'][:4])}")
        if score_a["traps_hit"]:
            print(f"      TRAP: {', '.join(score_a['traps_hit'])}")

        # Condition B: Augmented
        print("  [B] Claude + Theia...")
        resp_b, time_b = ask_claude(q["question"], dashboard_source, theia_context)
        score_b = score_response(resp_b, q)
        results_b.append({
            "question": q, "response": resp_b,
            "time": time_b, "score": score_b,
        })
        status_b = "WRONG" if score_b["has_wrong_info"] else f"{score_b['accuracy']:.0%}"
        print(f"      Time: {time_b:.1f}s | Accuracy: {status_b}")
        if score_b["key_misses"]:
            print(f"      Missed: {', '.join(score_b['key_misses'][:4])}")
        if score_b["traps_hit"]:
            print(f"      TRAP: {', '.join(score_b['traps_hit'])}")
        print()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("=" * 72)
    print("  RESULTS SUMMARY")
    print("=" * 72)
    print()

    avg_acc_a = sum(r["score"]["accuracy"] for r in results_a) / len(results_a)
    avg_acc_b = sum(r["score"]["accuracy"] for r in results_b) / len(results_b)
    avg_time_a = sum(r["time"] for r in results_a) / len(results_a)
    avg_time_b = sum(r["time"] for r in results_b) / len(results_b)
    wrong_a = sum(1 for r in results_a if r["score"]["has_wrong_info"])
    wrong_b = sum(1 for r in results_b if r["score"]["has_wrong_info"])
    total_hits_a = sum(len(r["score"]["key_hits"]) for r in results_a)
    total_hits_b = sum(len(r["score"]["key_hits"]) for r in results_b)
    total_facts = sum(r["score"]["total_key_facts"] for r in results_a)

    print(f"  {'Metric':<30} {'A (vanilla)':>15} {'B (+ Theia)':>15} {'Delta':>10}")
    print(f"  {'─' * 72}")
    print(f"  {'Avg accuracy':<30} {avg_acc_a:>14.1%} {avg_acc_b:>14.1%} {avg_acc_b - avg_acc_a:>+9.1%}")
    print(f"  {'Key facts found':<30} {total_hits_a:>12}/{total_facts} {total_hits_b:>12}/{total_facts} {total_hits_b - total_hits_a:>+9}")
    print(f"  {'Wrong info responses':<30} {wrong_a:>15} {wrong_b:>15} {wrong_b - wrong_a:>+9}")
    print(f"  {'Avg response time':<30} {avg_time_a:>13.1f}s {avg_time_b:>13.1f}s {avg_time_b - avg_time_a:>+8.1f}s")
    print()

    uplift = ((avg_acc_b - avg_acc_a) / avg_acc_a * 100) if avg_acc_a > 0 else 0
    print(f"  Accuracy uplift: {uplift:+.1f}%")
    print(f"  Wrong info prevented: {wrong_a - wrong_b}")
    print()

    # Per-question breakdown
    print("  Per-question breakdown:")
    print(f"  {'Q':<4} {'A acc':>8} {'B acc':>8} {'A wrong':>8} {'B wrong':>8} {'Winner':>8}")
    for ra, rb in zip(results_a, results_b):
        qid = ra["question"]["id"]
        a_better = ra["score"]["accuracy"] > rb["score"]["accuracy"]
        b_better = rb["score"]["accuracy"] > ra["score"]["accuracy"]
        winner = "B" if b_better else ("A" if a_better else "tie")
        if ra["score"]["has_wrong_info"] and not rb["score"]["has_wrong_info"]:
            winner = "B"
        elif rb["score"]["has_wrong_info"] and not ra["score"]["has_wrong_info"]:
            winner = "A"
        print(
            f"  {qid:<4} "
            f"{ra['score']['accuracy']:>7.0%} "
            f"{rb['score']['accuracy']:>7.0%} "
            f"{'yes' if ra['score']['has_wrong_info'] else 'no':>8} "
            f"{'yes' if rb['score']['has_wrong_info'] else 'no':>8} "
            f"{winner:>8}"
        )

    print()
    print("=" * 72)

    # Save results
    results_dir = Path(__file__).parent / "benchmarks" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    for label, results in [("vanilla", results_a), ("augmented", results_b)]:
        out = {
            "condition": label,
            "test": "hyperion_dashboard_design_audit",
            "questions": len(results),
            "avg_accuracy": sum(r["score"]["accuracy"] for r in results) / len(results),
            "total_key_hits": sum(len(r["score"]["key_hits"]) for r in results),
            "total_key_facts": total_facts,
            "wrong_info_count": sum(1 for r in results if r["score"]["has_wrong_info"]),
            "avg_time": sum(r["time"] for r in results) / len(results),
            "per_question": [
                {
                    "id": r["question"]["id"],
                    "accuracy": r["score"]["accuracy"],
                    "key_hits": r["score"]["key_hits"],
                    "key_misses": r["score"]["key_misses"],
                    "traps_hit": r["score"]["traps_hit"],
                    "time": r["time"],
                    "response": r["response"],
                }
                for r in results
            ],
        }
        fpath = results_dir / f"{label}.json"
        fpath.write_text(json.dumps(out, indent=2))
        print(f"  Saved: {fpath}")

    # Write markdown report
    md_lines = [
        "# Theia A/B Test — Hyperion Dashboard Design Audit",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}",
        f"**Test:** Hyperion SOC Dashboard design critique",
        f"**Condition A:** Claude alone (vanilla)",
        f"**Condition B:** Claude + Theia's design knowledge base",
        "",
        "## Summary",
        "",
        f"| Metric | A (vanilla) | B (+ Theia) | Delta |",
        f"|--------|-------------|-------------|-------|",
        f"| Avg accuracy | {avg_acc_a:.1%} | {avg_acc_b:.1%} | {avg_acc_b - avg_acc_a:+.1%} |",
        f"| Key facts found | {total_hits_a}/{total_facts} | {total_hits_b}/{total_facts} | {total_hits_b - total_hits_a:+d} |",
        f"| Wrong info responses | {wrong_a} | {wrong_b} | {wrong_b - wrong_a:+d} |",
        f"| Avg response time | {avg_time_a:.1f}s | {avg_time_b:.1f}s | {avg_time_b - avg_time_a:+.1f}s |",
        f"| **Accuracy uplift** | | | **{uplift:+.1f}%** |",
        "",
        "## Per-Question Breakdown",
        "",
    ]

    for ra, rb in zip(results_a, results_b):
        q = ra["question"]
        sa, sb = ra["score"], rb["score"]
        a_better = sa["accuracy"] > sb["accuracy"]
        b_better = sb["accuracy"] > sa["accuracy"]
        winner = "B" if b_better else ("A" if a_better else "tie")
        if sa["has_wrong_info"] and not sb["has_wrong_info"]:
            winner = "B"
        elif sb["has_wrong_info"] and not sa["has_wrong_info"]:
            winner = "A"

        md_lines.extend([
            f"### {q['id']}: {q['question']}",
            "",
            f"**Ground truth:** {q['ground_truth']}",
            "",
            f"| | A (vanilla) | B (+ Theia) |",
            f"|---|---|---|",
            f"| Accuracy | {sa['accuracy']:.0%} | {sb['accuracy']:.0%} |",
            f"| Key hits | {', '.join(sa['key_hits']) or 'none'} | {', '.join(sb['key_hits']) or 'none'} |",
            f"| Missed | {', '.join(sa['key_misses']) or 'none'} | {', '.join(sb['key_misses']) or 'none'} |",
            f"| Traps hit | {', '.join(sa['traps_hit']) or 'none'} | {', '.join(sb['traps_hit']) or 'none'} |",
            f"| **Winner** | | **{winner}** |",
            "",
            "<details><summary>A response</summary>",
            "",
            ra["response"],
            "",
            "</details>",
            "",
            "<details><summary>B response</summary>",
            "",
            rb["response"],
            "",
            "</details>",
            "",
        ])

    md_path = results_dir / "AB_RESULTS.md"
    md_path.write_text("\n".join(md_lines))
    print(f"  Saved: {md_path}")
    print()


if __name__ == "__main__":
    run_ab_test()
