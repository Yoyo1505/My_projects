# Decision Records — Iteration 2 (post-submission)

Not part of the graded submission — `DECISIONS.md`'s original three records
stand as sent. These are the two decisions from the follow-up graph-based
rework worth defending the same way.

## 1. Guardrail verification as deterministic post-processing, not a second model call

**Decision:** `verifier.py` runs after the reasoning node as plain
regex/rule-based checks (escalation phrasing, policy-term quoting, date
disambiguation) — never a second LLM call.
**Options considered:** a "critic" LLM pass reviewing the draft answer; a
second independent model (e.g. a different provider) voting/verifying; the
deterministic pass actually built.
**Why:** the original submission's cost/latency budget ($50/day, p95≤3s at
100k q/day) was already built around avoiding extra network hops per
question (`DECISIONS.md` #1, #2). A second model call here would double
inference cost and latency for every request to catch a fraction of
phrasing bugs. The three bugs this iteration actually found and fixed — a
Unicode-whitespace artifact in the model's own output, a policy quote
reintroducing forbidden promise-language, a routing-rule blind spot — are
all shapes regex/structural checks catch for free; none needed semantic
judgment a second model would add.
**What would change my mind:** if the hidden set surfaces failures that are
genuinely semantic (the answer is subtly wrong in a way no regex could
catch, not just mis-phrased or mis-routed), that's evidence a second-pass
critic model earns its cost where deterministic checks structurally cannot.

## 2. Escalation routing forced structurally by the router, not left to model tool-calling

**Decision:** `router.py` scans the raw question against categorized hint
phrases *before* the model runs; a match pins `route="escalate"`
unconditionally, regardless of whether the model actually calls the
`escalate()` tool.
**Options considered:** keep routing purely a function of which tools the
model invokes (the original design); add the hints only as extra system-prompt
context (already tried — this is what produced v09's flakiness, a fraud
report intermittently routing to `policy`); force the route structurally.
**Why:** `DECISIONS.md` #3 already established the principle that guardrails
should be enforced in code, not just requested in a prompt, for *data
access*. v09 showed the same gap exists for *routing*: a prompt instruction
("you MUST call escalate for fraud") is exactly the kind of rule the brief
says to test adversarially, and it's also just unreliable under ordinary
sampling variance, no adversary required. The fix is the same shape as #3's:
move the decision out of the model's discretion for the categories where
getting it wrong is worst.
**What would change my mind:** if the hidden set contains legitimate
escalation-shaped phrasing this hint list doesn't cover, false negatives
(missed escalations) would need addressing on the knowledge-plane side
(broadening `ESCALATION_CATEGORIES` in `prompts.py`) rather than here — this
router is only as good as the hints it's given, by design; it trades recall
on *known* categories for zero-tolerance precision on them.

## 3. Structural data preload over stronger prompt directives, when a prompt directive demonstrably doesn't work

**Decision:** when `router.py` detects a question needs a specific order's
data (`likely_needs_order_lookup`), it fetches that order itself
(`find_referenced_order`, authorization-scoped the same as every other
lookup) and hands it directly to the reasoning node, instead of only telling
the model via the system prompt that it must call the tool.
**Options considered:** keep escalating the system-prompt wording (tried
first, twice — a general rule addition, then an explicit "you MUST call
get_order" directive); force the route label without the underlying data
(rejected — would make the route claim true while the answer content stayed
wrong); fetch and hand over the data structurally.
**Why:** measured, not assumed — the explicit directive was tested directly
(v10) and the model still skipped the tool call. A structural guarantee costs
one extra deterministic lookup (already fast — same in-process data access as
`orders_store.py` uses everywhere) against a model call that might not
happen at all. This is `DECISIONS.md` #3's principle taken one step further:
first "don't let the model bypass authorization," now "don't rely on the
model to fetch grounding data it was told to fetch."
**What would change my mind:** if this pattern needs to generalize past
"question names a merchant the user has an order with" to something fuzzier
(e.g. no merchant name, ambiguous which order), the matching logic would
need to get smarter or bail out — right now it's deliberately narrow (regex
merchant-name match) rather than guessing.
