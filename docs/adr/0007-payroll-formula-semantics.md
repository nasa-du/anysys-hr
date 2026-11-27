# Payroll formula semantics and rounding

Payroll formulas are authored and edited by business users in an Excel-like syntax. The formula engine must produce exact decimal results, explain dependency errors before a calculation, and keep historical results reproducible. The requirement's default formulas mix unrounded intermediates (`base_pay`, `overtime_pay_actual`) with explicit `ROUND(...,2)` aggregates (`normal_pay`, `gross`, `net`), while the domain model stores monetary result values at two decimal places. The formula-engine research recommended an in-house, stdlib-only tokenizer/parser/evaluator over `Decimal` rather than a third-party expression engine. This ADR records the semantic decisions that follow from that recommendation.

We chose **explicit field-level rounding with no implicit engine rounding**: every monetary field's effective formula must produce a value that is exactly representable at two decimal places, the engine rejects values that are not (`formula_value_scale`), and the default formulas are normalized to end in `ROUND(...,2)`. Downstream formulas read the rounded field values, the result table stores two-decimal money, and the five category-anchored consistency checks compare exactly. `ROUND` uses `Decimal.quantize` with `ROUND_HALF_UP` (ties away from zero), matching Excel. All formula values are `Decimal`; the engine uses precision 28, explicit exponent limits, and rejects non-finite results. Formulas are stored with canonical ASCII field keys and `{param}` references; Chinese labels are editor aliases resolved at insertion, never stored. The engine is the in-house whitelisted tuple-AST evaluator; it does not use `eval`, `exec`, `compile`, or `ast.parse`, and it enforces structural limits (expression length, tokens, nesting depth, literal digits, evaluation steps, and `ROUND` digits). See `docs/research/payroll-formula-engine.md` for the candidate comparison and the security analysis.

We chose this over keeping raw intermediate precision (which would make stored, displayed, and checked values three different contracts and require a tolerance rule), over implicit rounding at every field boundary (which hides semantics and does not cover non-monetary fields with different scales), and over a third-party engine (which cannot provide Excel `=`/`<>`, `{param}`, lazy `IF`, Decimal arithmetic, and field-level cycle diagnostics together). The cost is that `base_pay` and `overtime_pay_actual` are rounded before they feed `performance` and other downstream formulas, so results can differ by cents from a raw-spreadsheet calculation; the golden cases pin the chosen behavior. A formula that wants more precision cannot store it in a monetary field; it must be expressed at the field's declared scale.

The five category-anchored checks are:

- `normal_pay = ROUND(Σ earning, 2)`
- `addon_sum = ROUND(Σ addon, 2)`
- `gross = ROUND(normal_pay + addon_sum, 2)`
- `deduct_sum = ROUND(Σ deduction, 2)`
- `net = ROUND(gross + deduct_sum, 2)`

They are strong: any violation fails the whole calculation run atomically, and no results are written. The categories are semantic, not display-only; a custom field in `earning`, `addon`, or `deduction` must be included in the corresponding subtotal formula. `attendance_deduct` and `admin_deduct` are negative `addon` fields, not `deduction` fields, so `deduct_sum` contains only social insurance, tax, and advances.

Calculation snapshots record an `engine_version`. Semantic engine changes require a version bump and updated golden cases; recalculation uses the current engine, and existing results are never rewritten without an explicit recalculation. The engine version is an audit and compatibility marker, not a mechanism for replaying old code.

## Consequences

- Default formulas are stored with explicit `ROUND(...,2)` on every monetary field; custom monetary formulas must round explicitly or fail with `formula_value_scale`.
- The result table stores two-decimal money and full-precision (up to four decimals) non-monetary values; display and consistency checks use the stored value, so no tolerance is needed.
- Formula changes require a revision snapshot with original and normalized text, a formula hash, the engine version, the actor, and the time; consecutive revisions provide the before/after view.
- Formula validation happens at save time (syntax, references, arity, cycles, limits) and at calculation time (missing values, division by zero, scale, consistency). Trial calculation uses the same compiler and evaluator and never writes results.
- Golden cases under `docs/specs/payroll-golden-cases/` are versioned with the engine version and pin rounding, default formulas, custom fields, cycles, security limits, and the five consistency checks.
