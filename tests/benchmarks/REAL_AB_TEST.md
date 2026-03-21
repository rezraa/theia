# Real-World A/B Test: Vanilla Claude vs Claude + Theia Design Knowledge

## How This Works

8 **design audit questions** about the Hyperion SOC Dashboard — a real production UI with dark theme, Canvas charts, WebSocket real-time updates, and severity-driven information hierarchy. The dashboard has real design issues (accessibility violations, typography problems, responsive gaps). Two sessions audit it independently.

- **Session A (Vanilla)**: Fresh Claude Code, no MCP, no Theia. Claude uses only its own design knowledge to audit the dashboard.
- **Session B (Augmented)**: Claude Code from `theia/` with Theia MCP configured. Claude can call `audit_design`, `plan_design_system`, `spec_component`, `evaluate_accessibility`, `log_decision` tools.

**What we're testing**: Does structured design knowledge (52 design systems, 66 component patterns, 58 WCAG criteria, 62 decision rules) produce more precise, principle-grounded design audits than general LLM knowledge alone? Can Theia catch issues vanilla Claude misses?

---

## Prerequisites

1. Theia installed: `cd ~/Repos/theia && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
2. `.mcp.json` in `~/Repos/theia` is configured (already done during build)
3. Hyperion dashboard source exists at `~/Repos/hyperion/src/hyperion/dashboard/`

---

## Step 1: Run the Vanilla Session

Open a **new Claude Code session** from a directory with NO Theia configured (e.g., `~` or `/tmp`).

Paste this prompt:

---

### Prompt for Vanilla Session

```
IMPORTANT: Record the current time at the START before answering anything, and again at the END after writing the JSON. Include both timestamps and total duration in seconds.

I need you to audit the UI/UX design of a security dashboard. First, read these source files:

- ~/Repos/hyperion/src/hyperion/dashboard/templates/index.html
- ~/Repos/hyperion/src/hyperion/dashboard/static/styles.css
- ~/Repos/hyperion/src/hyperion/dashboard/static/dashboard.js

Then answer these 8 design audit questions. Be specific — cite CSS values, line numbers, WCAG criteria, design principles. This is a professional design audit, not a casual review.

Write ALL results to: ~/Repos/theia/tests/benchmarks/results/vanilla.json

JSON format:
{
  "session": "vanilla",
  "start_time": "<ISO timestamp>",
  "end_time": "<ISO timestamp>",
  "duration_seconds": <total seconds>,
  "results": [
    {
      "id": "Q1",
      "question": "<the question>",
      "answer": "<your complete answer>",
      "principles_cited": ["<design principles referenced>"],
      "wcag_criteria_cited": ["<WCAG success criteria referenced>"],
      "tools_used": ["<any tools you called, or empty>"],
      "confidence": "<high/medium/low>"
    },
    ...
  ]
}

Q1: Analyze the visual hierarchy of the threat summary counter cards (the 6 cards: Critical, High, Medium, Low, Total, Risk Score). Are all severity levels given equal visual weight? Is that correct for a SOC dashboard? What design principle applies?

Q2: Check the color contrast ratios. The muted text color is #555570 on backgrounds of #12121e and #0a0a0f. Does this meet WCAG AA requirements? Calculate or estimate the contrast ratio and cite the specific WCAG criterion.

Q3: The dashboard uses color extensively to indicate severity levels (red for critical, orange for high, yellow for medium, blue for low). The finding cards use only a colored left border + small badge to show severity. Is there an accessibility issue? Cite the specific WCAG criterion.

Q4: Evaluate the code viewer modal overlay for accessibility. Look at the HTML structure (the code-viewer-overlay div and code-viewer div) and the CSS. What ARIA attributes are missing? Is there a focus trap? How does a keyboard user dismiss it?

Q5: Look at the ALERTS toggle button: style="color:#555570;border-color:#555570;font-size:0.65rem;padding:4px 10px". Is there a touch target size issue? Cite the specific WCAG criterion and the minimum size requirement.

Q6: The base font-size is set to 13px in the html rule. Elements use sizes ranging from 0.6rem to 1.3rem (including 0.6, 0.65, 0.68, 0.7, 0.72, 0.75, 0.78, 0.8, 0.85, 1.0, 1.3rem). Evaluate the typography system. Is there a systematic type scale? What would you recommend?

Q7: The dashboard uses a 3-column CSS grid: grid-template-columns: 300px 1fr 320px. It switches to 2 columns at 1200px and 1 column at 768px. Evaluate the responsive design. Are the fixed column widths a problem? What about code blocks with white-space:pre on narrow screens?

Q8: What design system methodology would you recommend as the foundation for redesigning this dashboard? Consider it's a SOC (Security Operations Center) tool for analysts monitoring threats in real-time. Be specific about token architecture, spacing system, and type scale.

After answering all 8, write the results JSON file.
```

---

## Step 2: Run the Augmented Session (Theia Tools)

Open a **new Claude Code session** from **`~/Repos/theia/`** with Theia MCP configured.

Paste this prompt:

---

### Prompt for Augmented Session

```
IMPORTANT: Record the current time at the START before answering anything, and again at the END after writing the JSON. Include both timestamps and total duration in seconds.

First, invoke /theia. Then audit the UI/UX design of a security dashboard using Theia's MCP tools for each question.

First, read these source files:

- ~/Repos/hyperion/src/hyperion/dashboard/templates/index.html
- ~/Repos/hyperion/src/hyperion/dashboard/static/styles.css
- ~/Repos/hyperion/src/hyperion/dashboard/static/dashboard.js

Then answer these 8 design audit questions. Be specific — cite CSS values, line numbers, WCAG criteria, design principles. This is a professional design audit, not a casual review.

Write ALL results to: ~/Repos/theia/tests/benchmarks/results/augmented.json

JSON format:
{
  "session": "augmented",
  "start_time": "<ISO timestamp>",
  "end_time": "<ISO timestamp>",
  "duration_seconds": <total seconds>,
  "results": [
    {
      "id": "Q1",
      "question": "<the question>",
      "answer": "<your complete answer>",
      "principles_cited": ["<design principles referenced>"],
      "wcag_criteria_cited": ["<WCAG success criteria referenced>"],
      "tools_used": ["<any tools you called, or empty>"],
      "confidence": "<high/medium/low>"
    },
    ...
  ]
}

Q1: Analyze the visual hierarchy of the threat summary counter cards (the 6 cards: Critical, High, Medium, Low, Total, Risk Score). Are all severity levels given equal visual weight? Is that correct for a SOC dashboard? What design principle applies?

Q2: Check the color contrast ratios. The muted text color is #555570 on backgrounds of #12121e and #0a0a0f. Does this meet WCAG AA requirements? Calculate or estimate the contrast ratio and cite the specific WCAG criterion.

Q3: The dashboard uses color extensively to indicate severity levels (red for critical, orange for high, yellow for medium, blue for low). The finding cards use only a colored left border + small badge to show severity. Is there an accessibility issue? Cite the specific WCAG criterion.

Q4: Evaluate the code viewer modal overlay for accessibility. Look at the HTML structure (the code-viewer-overlay div and code-viewer div) and the CSS. What ARIA attributes are missing? Is there a focus trap? How does a keyboard user dismiss it?

Q5: Look at the ALERTS toggle button: style="color:#555570;border-color:#555570;font-size:0.65rem;padding:4px 10px". Is there a touch target size issue? Cite the specific WCAG criterion and the minimum size requirement.

Q6: The base font-size is set to 13px in the html rule. Elements use sizes ranging from 0.6rem to 1.3rem (including 0.6, 0.65, 0.68, 0.7, 0.72, 0.75, 0.78, 0.8, 0.85, 1.0, 1.3rem). Evaluate the typography system. Is there a systematic type scale? What would you recommend?

Q7: The dashboard uses a 3-column CSS grid: grid-template-columns: 300px 1fr 320px. It switches to 2 columns at 1200px and 1 column at 768px. Evaluate the responsive design. Are the fixed column widths a problem? What about code blocks with white-space:pre on narrow screens?

Q8: What design system methodology would you recommend as the foundation for redesigning this dashboard? Consider it's a SOC (Security Operations Center) tool for analysts monitoring threats in real-time. Be specific about token architecture, spacing system, and type scale.

After answering all 8, write the results JSON file.
```

---

## Step 3: Score Both Sessions

Open a third session and paste:

```
Score two design audit sessions. Each session answered the same 8 questions about a security dashboard. Score them blindly — do not assume one is better than the other.

Read both files:
- ~/Repos/theia/tests/benchmarks/results/vanilla.json (Session A)
- ~/Repos/theia/tests/benchmarks/results/augmented.json (Session B)

For each question in each session, score on these 4 criteria (1 point each, max 32 total per session):

1. **Issue detection** — does the answer correctly identify the design problem?
2. **No wrong conclusions** — does the answer avoid stating incorrect assessments (e.g., "passes WCAG" when it fails)?
3. **Principle/standard citation** — does the answer cite specific WCAG criteria, design principles, or methodology names?
4. **Actionable specificity** — does the answer include specific values (px, ratios, hex codes) and concrete fix recommendations?

Score each question for Session A, then the same question for Session B, using the same criteria and ground truth. Here is the ground truth:

Q1: Analyze the visual hierarchy of the threat summary counter cards (the 6 cards: Critical, High, Medium, Low, Total, Risk Score). Are all severity levels given equal visual weight? Is that correct for a SOC dashboard? What design principle applies?
- Key facts: All 6 cards have equal visual weight (same flex:1, padding, sizing); Critical should be more prominent; visual hierarchy principle violated; hierarchy should match severity importance
- Wrong if stated: "well-designed hierarchy"; "correct visual weight"

Q2: Check the color contrast ratios. The muted text color is #555570 on backgrounds of #12121e and #0a0a0f. Does this meet WCAG AA requirements? Calculate or estimate the contrast ratio and cite the specific WCAG criterion.
- Key facts: #555570 on #12121e is approximately 2.8:1 contrast ratio; fails WCAG AA minimum of 4.5:1 (criterion 1.4.3); text-muted at small sizes makes it worse
- Wrong if stated: "passes AA"; "meets WCAG"; "sufficient contrast"

Q3: The dashboard uses color extensively to indicate severity levels (red for critical, orange for high, yellow for medium, blue for low). The finding cards use only a colored left border + small badge to show severity. Is there an accessibility issue? Cite the specific WCAG criterion.
- Key facts: WCAG 1.4.1 Use of Color; severity communicated primarily through color alone; color vision deficiency users affected; needs icons, patterns, or shapes alongside color
- Wrong if stated: "no accessibility issue"; "colors are sufficient"

Q4: Evaluate the code viewer modal overlay for accessibility. Look at the HTML structure (the code-viewer-overlay div and code-viewer div) and the CSS. What ARIA attributes are missing? Is there a focus trap? How does a keyboard user dismiss it?
- Key facts: No role="dialog" or aria-modal; no aria-label; no focus trap; no visible close button in HTML; no Escape key handling in template; keyboard users cannot dismiss it
- Wrong if stated: "accessible modal"; "properly implemented"

Q5: Look at the ALERTS toggle button: style="color:#555570;border-color:#555570;font-size:0.65rem;padding:4px 10px". Is there a touch target size issue? Cite the specific WCAG criterion and the minimum size requirement.
- Key facts: WCAG 2.5.8 Target Size Minimum; 24x24 CSS px minimum; with font-size 0.65rem (~8.5px) and padding 4px, button height is below 24px
- Wrong if stated: "adequate size"; "meets requirements"

Q6: The base font-size is set to 13px in the html rule. Elements use sizes ranging from 0.6rem to 1.3rem (including 0.6, 0.65, 0.68, 0.7, 0.72, 0.75, 0.78, 0.8, 0.85, 1.0, 1.3rem). Evaluate the typography system. Is there a systematic type scale? What would you recommend?
- Key facts: Base 13px means 0.6rem=7.8px — extremely small; no modular type scale; sizes are arbitrary; should use major third (1.250) or perfect fourth (1.333) scale
- Wrong if stated: "appropriate font sizes"; "good typography"

Q7: The dashboard uses a 3-column CSS grid: grid-template-columns: 300px 1fr 320px. It switches to 2 columns at 1200px and 1 column at 768px. Evaluate the responsive design. Are the fixed column widths a problem? What about code blocks with white-space:pre on narrow screens?
- Key facts: Fixed 300px/320px columns don't scale; gap between usable width and 1200px breakpoint; white-space:pre code blocks cause horizontal overflow on mobile; Canvas has no responsive resize
- Wrong if stated: "well-designed responsive"; "appropriate breakpoints"

Q8: What design system methodology would you recommend as the foundation for redesigning this dashboard? Consider it's a SOC (Security Operations Center) tool for analysts monitoring threats in real-time. Be specific about token architecture, spacing system, and type scale.
- Key facts: Design tokens with semantic severity tokens; 8px spacing grid; modular type scale; consider Carbon Design or similar for dense data viz; systematize existing arbitrary values
- Wrong if stated: N/A — assess quality of recommendation

Write the scoring results to:
~/Repos/theia/tests/benchmarks/results/scores.json

Include:
- Per-question scores for both sessions (same 4 criteria applied identically)
- Total scores (out of 32)
- Accuracy percentages
- Time comparison
- Whether either session stated wrong conclusions
- Number of design principles and WCAG criteria cited by each session
- Overall winner and uplift percentage
```

---

## Ground Truth

See the full questions and key facts in Step 3 above. The questions in Step 3 are identical to Q1-Q8 in Steps 1 and 2.

## Expected Outcome

Claude's training includes general UI/UX knowledge, so it should catch obvious issues (Q2 contrast, Q3 color-only). But:
- **Q1** (visual hierarchy) — vanilla Claude may say the cards "look fine" without identifying the flat hierarchy as a deliberate design problem for a SOC context
- **Q4** (modal accessibility) — requires specific ARIA knowledge; vanilla may miss focus trap and aria-modal
- **Q5** (target size) — WCAG 2.5.8 is a newer criterion (WCAG 2.2); vanilla may not cite it specifically or know the 24px threshold
- **Q6** (type scale) — vanilla may note small sizes but not identify the lack of a modular scale or recommend a specific ratio
- **Q8** (design system) — vanilla gives general advice; Theia should give specific token architecture with spacing values, type ratios, and named design system foundations

Theia should excel on: principle citation, WCAG criterion specificity, actionable token/scale recommendations, and structured design system thinking.
