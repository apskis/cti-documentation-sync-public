# CTI documentation sync: standing context

Carried over from the Claude memory file `/areas/cti-doc-sync-task.md`. Read it
before a sync run. Update it when a standing decision changes.

## What the task is

- The CTI Deliverables folder is the evolving source of truth for the CTI
  portfolio. The plan documents and the strategy deck are maintained
  representations of it.
- Documents under maintenance, all in `CTI Documentation\Strategy_and_Plan`:
  `CTI_Plan.docx`, `Threat Hunting Plan.docx`, `CTI_AI_Strategy_Evolving.pptx`.
- `CTI Strategy.pptx` and `CTI Strategy-Reference for April.pptx` are off limits
  to automation. The evolving deck is a separate copy seeded from the reference
  deck.

## Standing decisions

- Cadence: monthly, first weekday of the month.
- Autonomy: edit documents in place, always taking a timestamped backup first.
- Substantive evolution is what gets tracked, not file timestamps. No edit is
  ever made solely to prove the task ran.
- Every document with a change history table gets a revision entry only when
  something material changed.
- In the strategy deck, observed facts, strategic implications and
  recommendations stay clearly distinguishable. A recommendation is never
  presented as an established capability.
- One consistent branding flow across the whole CTI program: program
  documentation carries the same house identity as the bulletins and hunt
  reports.
- Internal CTI documents carry no TLP marking. TLP is for sharing, not
  classification. It belongs on bulletins and anything leaving GeneLabs, not on
  the plans.

## History

- 2026-08-21: reconciled and rebranded. `CTI_Plan.docx` to version 09,
  `Threat Hunting Plan.docx` to version 1.1. Footer document ids `CTI-PLAN-09`
  and `CTI-THP-1.1`.
- 2026-08-21: `CTI_AI_Strategy_Evolving.pptx` gained a fourteen slide AI Strategy
  and Roadmap section, inserted before the Appendix. Claims carry OBSERVED,
  IMPLICATION or RECOMMENDATION labels.
- 2026-09-01: the Claude scheduled run could not reach the machine and changed
  nothing. That is the reason this repository exists. The first run from Cursor
  therefore has roughly a month of unreconciled drift to absorb, more than a
  normal cycle.

## Strategy direction

April wants the year ahead strategy built around custom MCP servers, not just her
current Claude and MCP usage. Proposed portfolio: `cti-metrics`,
`feed-fidelity`, `genelabs-feeds`, `cve-triage`, `hunt-forge`, `doc-sync`,
phased September 2026 through August 2027. None built yet, so in the deck these
remain RECOMMENDATION, never OBSERVED.
