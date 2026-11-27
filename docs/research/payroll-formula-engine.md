# Payroll Formula Engine Technical Selection (薪资公式引擎技术选型)

- Ticket: [#56](https://github.com/nasa-du/anysys-hr/issues/56) (research), feeding [#47](https://github.com/nasa-du/anysys-hr/issues/47) (decision)
- Date: 2026-11-27
- Runtime used for experiments: CPython 3.14.4 on Linux (WSL2)
- Status: research input, non-normative. The final decision lives in the payroll specification and ADRs. Merged to `main` on 2026-11-27; experiment artifacts were throwaway and are not committed.
- Requirement source: [`docs/requirement/rx-hr-requirement.html`](../requirement/rx-hr-requirement.html) §3.9, §4.1–§4.4
- Constraint from the map: no production code in this effort; the experiment is a throwaway prototype outside the repository

## 1. Question and constraints

The payroll module must let business users edit Excel-like formulas per field and per calculation scheme, without redeploying code. The requirement says:

- Field references are bare keys (`base_pay`, `overtime_pay`); parameter references use braces (`{avg_pay_days}`, `{ot_mult_weekday}`) (§4.2).
- Operators are `+ - * / ( )`, plus comparisons and `IF(cond, a, b)`; the function whitelist is `ROUND`, `SUM`, `MIN`, `MAX`, `ABS`, `IF` (§4.2).
- Default formulas include `ROUND(..., 2)`, `SUM(...)`, and nested arithmetic (§4.3).
- The engine must parse formulas, build a dependency graph, topologically order fields, detect cycles immediately and name the field, sandbox evaluation (no file/network/system calls), set an expression timeout and recursion depth, and report missing fields/parameters and division by zero clearly (§4.1, §4.4).
- Money is two decimal places; the UI is Chinese; formulas are authored by non-programmers (§3.9, §4).

Two constraints are already decided and are treated as hard requirements here:

1. No arbitrary Python `eval` and no unrestricted expression library. Formula text is untrusted input from business users.
2. The engine must fit FastAPI + SQLModel + PostgreSQL and CPython 3.14, and must be maintainable by this project rather than a large external engine.

## 2. What the requirement actually needs

The syntax surface is small, but the semantics are not. The following is the distilled contract used to compare candidates:

| Need | Concrete expectation from the requirement |
| --- | --- |
| Field references | Bare canonical keys, including inside `SUM` and `IF`; Chinese labels may be shown in the UI |
| Parameter references | `{param}` tokens, resolved from scheme-level workday params first, then global legal params (§4.2) |
| Arithmetic | `+ - * /`, unary sign, parentheses; no power/percent/string operators in V1 |
| Comparison | Excel-like equality and not-equal (`=`, `<>`) plus `< <= > >=`; used inside `IF` |
| Functions | `IF` (must be lazy), `ROUND` (Excel half-away-from-zero), `SUM/MIN/MAX` (varargs), `ABS` |
| Numeric type | Decimal, not binary float; exact `0.1 + 0.2 = 0.3`; explicit `ROUND` |
| Dependency handling | Extract field dependencies, build a graph, topological order, detect self/indirect cycles and name the path |
| Failure handling | Unknown field/parameter, missing value, `NULL`, division by zero, type mismatch: actionable error with location |
| Sandbox | No attribute access, subscripting, imports, system calls, lambda, comprehensions, or Python statements |
| Limits | Expression length, nesting/recursion depth, evaluation budget/timeout |
| Auditability | Formula change history and a stable compiled version/snapshot per calculation |
| Scale | Hundreds of employees × dozens of fields per monthly run |

The requirement's default formulas also expose a modeling issue that #47 must settle: `addon_sum` is written as `ROUND(SUM(带薪假,加班补贴,话费,...), 2)` using Chinese labels, while the same document defines canonical English field keys. The engine must either resolve labels to keys at save time or the default formulas must be rewritten to keys. Mixing both in the stored formula would make dependency analysis and audit trails ambiguous.

## 3. Candidates at a glance

All library versions below are the latest on PyPI as of 2026-11-27; maintenance counts are commits on the default branch since 2025-11-27 (GitHub API). The custom option was prototyped for this ticket. Python 3.14 results are from the experiment in §6.

| Criterion | Custom Pratt/recursive-descent parser + whitelisted AST evaluator | simpleeval 1.0.8 | asteval 1.0.10 | formulas 1.3.4 | pycel 1.0b30 |
| --- | --- | --- | --- | --- | --- |
| Excel-like `=` / `<>`, lazy `IF` | Yes by design | No: Python syntax only; `IF` is an eager function | No: Python subset; `IF` eager; `=` is assignment | Yes (Excel parser), `IF` lazy | Partly; released 1.0b30 is broken on 3.14 for arithmetic |
| `{param}` token | Yes, first-class token | No | No | No: `{...}` is an Excel array constant (returns 2-D `Array`) | No |
| Decimal precision | Yes: `Decimal` throughout | No: literals are float | No: literals are float | No: arithmetic becomes float/numpy | No |
| Dependency graph / cycle detection | Yes, built from AST and owned by the engine | No | No | Schedula workbook graph; default `circular=False` omitted circular cells in the test; `circular=True` inserts cell errors | Cell graph; iterative-cycle mode only |
| Sandbox model | Allowlist by construction; no `eval`/`exec`/Python AST | AST handler blocklist; attributes/subscripts/strings still reachable; history of escapes | Python subset with blocklists; `minimal=True` still exposes read-only `open` by default in the test | Not a sandbox; workbook/formula engine; evaluates via schedula; `eval` for literals | Compiles formulas to Python and `exec`s them; CVE-2024-53924 code injection in the released artifact |
| Error location | Token/AST position, field key, error code | SyntaxError carries `lineno`/`offset`; semantic errors carry the expression text only | `ExceptionHolder` carries line/column and node (best of the libraries), but no field/batch context | Formula/cell errors; no character position | Cell-level; parser errors not positional |
| Performance in this use | 500 employees × 40 fields in 0.175 s (prototype) | 18.4 µs/eval (float, parse each call) | 8.3 µs/eval (float, parse once) | 502 µs/eval standalone; workbook load/calc overhead | Not measurable for the released artifact on 3.14 (arithmetic parse failure) |
| Maintenance | Owned by this repo | Active: 40 commits/12 mo, release 2026-09-12 | Active: 75 commits/12 mo, release 2026-08-21 | Active: 12 commits/12 mo, release 2026-03-11 | Canonical repo active (46 commits/12 mo, latest 2026-11-18) but no release since 1.0b30 (2021-10-13) |
| License | Stdlib only, no third-party license | MIT | MIT | EUPL-1.1+ (copyleft; legal review needed) | GPL-3.0 |
| Python 3.14 | Works (stdlib only) | Works in the experiment (requires >=3.9; CI tests 3.9-3.15) | Works; declares 3.14 | Runs with `SyntaxWarning`s; no 3.14 classifier/`Requires-Python` | Released 1.0b30 fails arithmetic (`ast.Str` removed); master is unreleased/unverified |
| Verdict | Recommend | Reject as the engine | Reject as the engine | Reject for this use | Reject |

## 4. Candidate findings

### 4.1 Custom tokenizer + Pratt/recursive-descent parser + whitelisted Decimal evaluator

This option is not "write an Excel engine"; it is a small language with exactly the requirement's grammar. The throwaway prototype used:

- A tokenizer for decimal numbers, identifiers (ASCII and CJK for label experiments), `{param}` tokens, operators, and parentheses; illegal characters are rejected with a character offset.
- A precedence-climbing/recursive-descent parser producing a small immutable tuple AST. No Python `eval`, `exec`, `compile`, or `ast.parse` is applied to user text.
- A tree-walking evaluator over `Decimal`. `IF` is represented as a lazy node so the unchosen branch is never evaluated. `ROUND(x, n)` uses `Decimal.quantize` with `ROUND_HALF_UP`, which means ties away from zero and matches Excel's documented `ROUND` behavior for positive and negative values.
- A dependency collector that walks the AST and separates field references from parameter references.
- A graph layer with DFS cycle detection (returns the cycle path) and deterministic Kahn topological ordering.
- Hard limits: expression length 2,000 chars, 500 tokens, nesting depth 100, number literal length 30, 20,000 evaluation steps, Decimal context precision 28 with `Emax=100`/`Emin=-100`, and `ROUND` digits in `-10..10`.
- Typed errors: `FormulaSyntaxError` and `FormulaEvaluationError`, each carrying a character position and (for evaluation) the field key; no raw Python traceback reaches the user.

The prototype passed 43 tests covering precedence, comparisons, lazy `IF`, `SUM/MIN/MAX/ABS`, `{param}`, Chinese labels, Decimal exactness, four `ROUND` edge cases, every default formula shape, dependency ordering, self/two/three-node cycles, unknown dependencies, 13 attack strings plus three size/depth/number limit cases, and the default-formula invariants. It is roughly 430 lines of Python excluding tests. It is not production code and is not part of this repository.

Why the custom option wins for this requirement:

- The requirement is a domain-specific language, not Python. Excel equality (`=`), `<>`, `{}` parameters, lazy `IF`, and Excel `ROUND` cannot be expressed without preprocessing in any Python-expression library.
- Decimal is the primary numeric type, not a conversion afterthought. This is the difference between `ROUND(1.005, 2) = 1.01` and `1.0`.
- Dependency extraction is a by-product of the AST; the engine owns the graph and can report a cycle path such as `a -> b -> c -> a`. Library engines can evaluate a workbook graph but do not expose field-level cycle diagnostics for this data model.
- The sandbox is the grammar, not a blocklist. No Python object model is exposed, so there is no `__class__`, no attribute, no subscript, no import, no lambda, and no comprehension to block.
- The parser/evaluator is small enough to fuzz and review. The security review surface is ~400 lines, not a dependency tree with numpy/scipy/schedula.

The trade-offs are real and must be planned for: we own parser security and regression tests; the function set is deliberately narrow; when text/date/lookup functions are requested, the grammar and AST need explicit extension. Those costs are smaller than wrapping a library whose semantics, numeric type, and security model do not match.

### 4.2 simpleeval

- MIT, version 1.0.8 released 2026-09-12, `Requires-Python >=3.9`, 40 commits in the last 12 months ([PyPI](https://pypi.org/project/simpleeval/), [source](https://github.com/danthedeckie/simpleeval)).
- It parses with Python's `ast.parse` and walks a handler table rather than calling `eval`; its default function set is tiny (`int`, `float`, `str`, `rand`, `randint`) and extra functions/names are supplied by the caller ([source](https://github.com/danthedeckie/simpleeval/blob/main/simpleeval.py)).
- It is Python expression syntax, not Excel syntax. In the experiment, `1 = 1` raised a Python assignment `SyntaxError` and `1 <> 2` was invalid syntax. A caller could translate `=` to `==` and `<>` to `!=`, but that is a home-grown preprocessing layer.
- `IF` must be supplied as a function; function arguments are evaluated eagerly, so `IF(1==1, 10, 1/0)` raised `ZeroDivisionError` instead of returning 10. The same happened with the false branch. This is a semantic mismatch with the requirement and with Excel.
- Numeric literals are Python floats: `0.1 + 0.2` produced `0.30000000000000004`. A `Decimal` name plus a float literal raised `TypeError`. There is no supported "use Decimal for all literals" mode; the AST constant handler returns the float value.
- There is no dependency graph, cycle detection, or parameter syntax. `NameNotDefined` says only that a name is missing and carries the expression text, not a semantic position; `SyntaxError` from `ast.parse` does carry `lineno`/`offset` (for a one-line formula, line 1 and the offending column). Build can add semantic positions around the evaluator, but that is another layer.
- Sandbox: the base evaluator blocks dunder attributes and functions such as `__import__`, `open`, `eval`, `getattr`, lambda, and comprehensions; it still allows string subscripts (`'abc'[0]` returned `'a'`) and normal attributes subject to a deny list. Its README explicitly warns that the safety claim applies only to the expression, and quotes the view that "a lot of very clever people think the whole idea of trying to sandbox CPython is impossible" ([README](https://github.com/danthedeckie/simpleeval/blob/main/README.rst)). It has had at least one recent escape: CVE-2026-32640 / GHSA-44vg-5wv2-h2hg, fixed in 1.0.5, where modules exposed through `names` leaked dangerous modules; the current version is patched ([OSV](https://osv.dev/vulnerability/GHSA-44vg-5wv2-h2hg)). In our scope only Decimal numbers would be passed as names, so that specific escape is not directly exploitable, but the blocklist architecture and the preprocessing burden remain.
- Performance was good in float terms: 18.4 µs per evaluation of a 6-operation formula, parsing each time in the experiment. simpleeval does expose a parse-once API (`parse()` plus `eval(..., previously_parsed=...)`), so a caller could improve that number, but the semantic gaps remain.
- Verdict: reject as the payroll engine. It is a safe-ish calculator for Python expressions, not an Excel-compatible, Decimal-native formula engine with dependency validation.

### 4.3 asteval

- MIT, version 1.0.10 released 2026-08-21, `Requires-Python >=3.10`, classifiers include Python 3.14, 75 commits in the last 12 months ([PyPI](https://pypi.org/project/asteval/), [docs](https://lmfit.github.io/asteval/), [source](https://github.com/lmfit/asteval)). Its own README calls it "safe(ish)" and says it cannot guarantee complete safety ([README](https://github.com/lmfit/asteval/blob/master/README.rst)).
- It is a restricted Python interpreter, not an Excel expression language. `minimal=True` disables imports, `if` statements, loops, `try`, `with`, function definitions, lambdas, comprehensions, augmented assignment, and other nodes ([source](https://github.com/lmfit/asteval/blob/master/asteval/asteval.py)), but it still supports expression calls, attributes, and subscripts.
- Critical configuration finding: with `Interpreter(minimal=True)` on asteval 1.0.10, `open('/etc/passwd').read()` succeeded and returned the file contents. asteval's safety docs say `open()` is read-only by default, which limits damage but still lets formula text read arbitrary files, outside the requirement's sandbox. The default symbol table (397 symbols in the experiment) contains `open`; minimal mode does not remove it. Attributes and subscripts also remained usable (`'abc'.upper()`, `d['secret']`, `l.append(1)`). It is possible to lock this down by constructing a custom symbol table, setting `builtins_readonly=True`, and removing the `attribute` and `subscript` node handlers, but that is exactly the kind of blocklist assembly this project should avoid. Even the locked-down variant still evaluated both branches of an `IF` function and failed on the unused `1/0`.
- Excel equality is not supported: `1 = 1` and `1 <> 2` produced `None` with errors, not a boolean. Numeric literals are floats; `Decimal('0.1') + 0.2` raised `TypeError`. `0.1 + 0.2` was the float result. `{param}` is not part of the language.
- No dependency graph or cycle detection. Error reporting is the best of the four libraries: `ExceptionHolder` records the exception, message, `lineno`, `end_lineno`, `col_offset`, and the offending AST node, and errors accumulate in `interpreter.error`. It still has no field key, calculation-row context, or field-level dependency path, and the docs state there is no guaranteed timeout for a single expression.
- Security history is a warning sign for a Python-subset sandbox: CVE-2025-24359 (format-string escape, fixed in 1.0.6), GHSA-vp47-9734-prjw (AST tampering, fixed in 1.0.6), CVE-2026-55244 (BaseException subclass escape, fixed in 1.0.9), and CVE-2026-102734 (numpy ctypes native memory read/write, fixed in 1.0.9) ([OSV query](https://osv.dev/list?ecosystem=PyPI&q=asteval)). The current 1.0.10 includes the fixes, but four escapes in two years show the maintenance burden of exposing a Python subset to untrusted authors.
- Performance was the best of the libraries when parsing once and re-running the AST: 8.3 µs/eval in float terms. That does not compensate for the semantic and sandbox gaps.
- Verdict: reject. It could be locked down into a restricted Python calculator, but it would still not be Excel-like, Decimal-native, or dependency-aware, and the security configuration would be ours to maintain.

### 4.4 formulas

- EUPL-1.1+, version 1.3.4 released 2026-03-11, 12 commits in the last 12 months; dependencies include `schedula`, numpy, scipy, openpyxl, and regex; no `Requires-Python` and no Python 3.14 classifier ([PyPI](https://pypi.org/project/formulas/), [docs](https://formulas.readthedocs.io/), [source](https://github.com/vinci1it2000/formulas)).
- It is an Excel workbook engine: it parses cell formulas, builds a schedula dependency graph, and calculates a workbook. This is a different abstraction from "a map of field key to formula" evaluated per employee. Using it would mean synthesizing a workbook or reaching into its internal parser/graph for every formula.
- Standalone parsing works, but names are normalized to upper case: `base_salary` must be supplied as `BASE_SALARY`; unmatched names raise `TypeError: missing a required argument`. `{avg_pay_days}` is parsed as an Excel array constant, not a parameter token: `=1+{x}` returned `Array([[3.0]])`, and a formula using braces produced a 2-D `Array` rather than a scalar. That is not the `{param}` contract in the requirement.
- Numeric behavior is float/numpy. `0.1+0.2` returned `0.30000000000000004`. Decimal inputs are accepted at the boundary but coerced during arithmetic: `=x*2` with `x=Decimal('10.00')` returned an `Array(20.0)`. `ROUND` implements the half-away-from-zero rule with `Decimal.quantize`, but the scaling is float-based (`x*d`), so `ROUND(1.005,2)` returned `1.0` where Decimal/exact Excel semantics give `1.01` ([formulas math source](https://github.com/vinci1it2000/formulas/blob/master/formulas/functions/math.py)). `ROUND(-2.5,0)` returned `-3`, which is correct Excel behavior.
- Dependency/cycle behavior: `ExcelModel` builds a schedula graph and has an optional `circular=True` mode that inserts `ERR_CIRCULAR` for workbook cycles (the default is `circular=False`). In our test with the default, a workbook with `D1 = D2+1` and `D2 = D1+1` returned a solution with D1/D2 simply absent and did not surface a field-level cycle error. Even with `circular=True`, the diagnostic is a cell error, not the field path required by §4.4; the engine would still need its own cycle validation and diagnostics for the field model.
- Error reporting: `FormulaError`, `ParenthesesError`, and `DispatcherError` are raised, but messages such as `Not a valid formula: =1+*2` do not include a character position. A function implemented by the workbook's function registry can fail with a dispatcher traceback.
- Security: formulas is not documented or designed as a sandbox for untrusted formula authors. It evaluates Excel formulas through schedula and compiles numeric literals with `eval` on a regex-constrained token ([operand source](https://github.com/vinci1it2000/formulas/blob/master/formulas/tokens/operand.py)); the function set is broad and workbook-oriented. No OSV advisories were found for the package in the query, but the absence of advisories is not a sandbox guarantee. The dependency tree (numpy/scipy/schedula) also enlarges the review surface.
- Python 3.14: the package ran, but importing/using it emitted `SyntaxWarning: "is" with a 'float' literal` and `SyntaxWarning: "is not" with a 'str' literal` from its own source. It is usable in a smoke test but not declared compatible with 3.14.
- Performance: a compiled standalone expression took 502.5 µs/eval in the experiment; 20,000 evaluations would be roughly 10 seconds before database work. A 200-row × 4-formula-field workbook took 2.316 s to load/finish and 0.623 s to calculate. Workbook batching can amortize this differently, but the per-field, per-employee path is heavy.
- License: EUPL-1.1+ is a copyleft license; whether the project's distribution/SaaS model triggers obligations needs legal review. It is not an MIT-style drop-in.
- Verdict: reject for this use. It is the closest Excel-compatible engine, but it is workbook-centric, float-based, lacks the `{param}` token, does not give field-level cycle diagnostics, adds a large dependency/license surface, and is slower than the small custom engine.

### 4.5 pycel

- GPL-3.0, PyPI version 1.0b30 released 2021-10-13, `Requires-Python >=3.6`, networkx `<2.7` ([PyPI](https://pypi.org/project/pycel/), [canonical source](https://github.com/dgorissen/pycel)). The PyPI homepage still points at `stephenrauch/pycel`, which is a stale fork; the canonical `dgorissen/pycel` repository is active (46 commits in the last 12 months, latest 2026-11-18) but has no tags and no GitHub releases, and `version.py` still says `1.0b30`. All current fixes are unreleased; the installable PyPI artifact is from 2021.
- It compiles Excel formulas into Python code and executes the compiled code with `exec` ([source](https://github.com/dgorissen/pycel/blob/master/src/pycel/excelformula.py)). It is a cell/workbook engine and is not designed as a sandbox for untrusted formulas.
- Python 3.14 compatibility of the released 1.0b30 fails for ordinary arithmetic: `=ROUND(A1/A2*A3,2)`, `=0.1+0.2`, and `=ROUND(-2.5,0)` all raised `FormulaParserError: ... module 'ast' has no attribute 'Str'`. Python 3.14 removed the deprecated `ast.Str` alias ([What's New in Python 3.14](https://docs.python.org/3/whatsnew/3.14.html#removed)). Trivial formulas that do not rewrite binary operators (`=ROUND(2.345,2)`, `=SUM(A1,A2,A3)`) happened to work, which is worse than a clean failure: the engine would break only on realistic formulas. The unreleased master may fix some of this, but using it would mean pinning an untagged commit.
- Security: CVE-2024-53924 / GHSA-pw67-xjhq-389w, "Pycel allows code injection via a crafted formula", affects all released versions through 1.0b30; the example payload is a cell formula beginning with `=IF(A1=200, eval("__import__('os').system(...` ([OSV](https://osv.dev/vulnerability/GHSA-pw67-xjhq-389w)). The fix landed on master in October 2026 (commit `1981c228b310c4747cf335c103ed6ba928633bfd`) but there is no patched PyPI release. Even the master fix reduces a known injection while still `exec`ing generated Python; it is not a sandbox. This directly violates the sandbox requirement for the installable artifact.
- No Decimal mode; rounding is float-based (and negative-digit `ROUND` falls back to Python's banker's rounding). Cell-cycle support is iterative calculation, not field-level validation. License is GPL-3.0.
- Verdict: reject. The released artifact is broken on the target Python, five years old, GPL-3.0, and has a formula-injection CVE; the active git repo does not change the released-package situation.

### 4.6 Other options considered

- **`xlcalculator` 0.5.0** (MIT, released 2023-02-06) is in the same Excel-to-Python code-generation family as pycel. It was not tested in depth because pycel's Python 3.14 break and CVE already disqualified that family for untrusted, per-field formulas; its 2023 release is also stale. If someone proposes it later, evaluate it against the same security and Decimal criteria, not only Excel syntax.
- **Lark or pyparsing** are parser generators, not evaluators. They could replace the hand-written parser if the grammar grows, but the Decimal evaluator, dependency graph, cycle detection, limits, and error model still have to be built. A hand-written Pratt/recursive-descent parser is small enough that an extra grammar dependency is not justified for V1.
- **`ast.parse` + a strict whitelist visitor** (the approach asteval generalizes) is technically viable, but Excel `=`/`<>`, `{param}`, Decimal literals, and lazy `IF` all require preprocessing, and the visitor must exhaustively reject attributes, subscripts, comprehensions, lambdas, calls outside the whitelist, and every statement node. That is more security-critical code than a small parser, with less control over numeric semantics. The asteval escape history is evidence of the cost of this approach.
- **RestrictedPython** restricts Python code rather than defining a business formula language; it is compile-based and not a fit for Excel-like formulas authored by finance users. It is out of scope.

## 5. Security analysis

Threat model: a logged-in business user can edit formula text. They may make mistakes, paste hostile text, or deliberately try to reach the server. The formula text is untrusted; the engine must not be able to import modules, open files, access the network, spawn processes, inspect Python objects, or loop indefinitely. The existing system currently grants all logged-in users payroll access, so there is no trusted-admin gate on formula editing.

### 5.1 Why arbitrary Python evaluation is not acceptable

Python's own documentation warns that `eval()` "executes arbitrary code" and that calling it with untrusted input "will lead to security vulnerabilities" ([Python docs: eval](https://docs.python.org/3/library/functions.html#eval)). This is CWE-95, Improper Control of Generation of Code ("eval injection") ([CWE-95](https://cwe.mitre.org/data/definitions/95.html)). OWASP's injection guidance makes the same point: do not send untrusted data to an interpreter; prefer an API that does not interpret code ([OWASP Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html)). `ast.literal_eval` is not an escape hatch here: the docs say it is not DoS-safe and is not recommended for untrusted data, and it cannot evaluate arithmetic or calls anyway ([Python docs: ast.literal_eval](https://docs.python.org/3/library/ast.html#ast.literal_eval)). Blocklists are fragile because Python's object model is reachable through attributes, subscripts, exceptions, frame objects, format strings, and library objects. The project has already ruled out arbitrary `eval`; the library findings below show why "restricted Python" libraries are also a poor fit for this specific requirement.

### 5.2 Candidate sandbox findings

| Candidate | What the experiment showed | Consequence |
| --- | --- | --- |
| Custom parser/evaluator | All 13 attack strings plus three limit cases rejected with syntax errors: `().__class__`, `().__class__.__bases__[0].__subclasses__()`, `__import__(...)`, `open(...)`, `eval(...)`, `getattr(...)`, lambda, comprehension, `a.b`, `a[0]`, `[1,2]`, `1;2`, Python conditional expression, overlong expression, deep nesting, long numeric literal | The grammar exposes no Python object model; attacks fail at tokenization/whitelist |
| simpleeval | Dunder/import/open/getattr/lambda/comprehension/format blocked; string subscript `'abc'[0]` allowed; CVE-2026-32640 fixed in 1.0.5 (current 1.0.8) | Better than raw `eval`, but a blocklist with a history of escapes; not enough as the primary boundary |
| asteval | With `minimal=True`, read-only `open('/etc/passwd').read()` returned file contents; attributes and subscripts usable; locking down requires custom symbol table plus removing handlers; even then `IF` evaluates both branches | The default configuration is not a sandbox for this threat model (arbitrary file reads remain possible) |
| formulas | `=__import__("os")` was rejected as an unknown function; formula parsing is Excel-shaped; but the library is not documented as a sandbox and has a broad function registry and large dependency tree | Do not treat it as a security boundary; any use would need an outer validator |
| pycel | CVE-2024-53924: code injection via a crafted formula in the released 1.0b30 (master fix unreleased); compiled formulas are `exec`'d | Disqualified outright |

Historical advisories found via the OSV API on 2026-11-27:

- simpleeval: GHSA-44vg-5wv2-h2hg / CVE-2026-32640, HIGH, fixed in 1.0.5. Dangerous modules could leak through attributes of objects passed as `names`; the current version is patched, but the advisory illustrates that the safety of the evaluator depends on the objects exposed to it.
- asteval: CVE-2025-24359 (format-string escape, fixed 1.0.6), GHSA-vp47-9734-prjw (AST tampering, fixed 1.0.6), CVE-2026-55244 (BaseException subclass escape, fixed 1.0.9), CVE-2026-102734 (numpy ctypes native memory read/write, fixed 1.0.9). The current 1.0.10 is patched for those, but the pattern is clear: a Python-subset sandbox is a moving target.
- pycel: CVE-2024-53924 / GHSA-pw67-xjhq-389w, HIGH, no patched PyPI release through 1.0b30; the fix exists only on master (October 2026) and is unreleased.
- formulas: no OSV advisories returned in the query. This is not evidence of safety; it is a workbook engine, not a sandbox.

### 5.3 Controls the custom engine should implement

1. **Parse, don't execute.** The only code that runs is the engine's own tokenizer, parser, and evaluator. `eval`, `exec`, `compile`, `ast.parse`, and dynamic imports are forbidden in the formula module. This is a code-review/CI rule, not only a convention.
2. **Grammar-level allowlist.** Tokens are numbers, field identifiers, `{param}`, the five functions plus `IF`, arithmetic/comparison operators, parentheses, and commas. String literals, attribute dots, brackets, semicolons, `**`, `%`, `&`, and keyword syntax are rejected. No need to block `__class__` because attribute access cannot be expressed.
3. **Numeric boundary.** Formula scope values must be `Decimal` or `int`; `float` is rejected. Convert Excel/openpyxl values to `Decimal` at the import boundary using their textual representation, and enforce a maximum digit count and exponent. This prevents binary-float artifacts from entering calculations and prevents a stray float from silently changing rounding.
4. **Bounded work.** Enforce expression length, token count, nesting depth, number literal length, `ROUND` digits, evaluation steps, and Decimal precision/exponent limits. These make each formula O(bounded) and avoid the need for a per-formula thread/process in the common case. If a hard wall-clock timeout is required by the security acceptance criteria, add it at the batch/service boundary (e.g., run the calculation in a worker with a deadline) rather than inside every node.
5. **Field/parameter isolation.** Field names are resolved only against the supplied scope; parameter names only against the supplied parameter map. Function names are reserved and cannot be shadowed by a field. Unknown names fail with a field/parameter error and position, never fall back to Python builtins or globals.
6. **Error hygiene.** User-facing errors contain a code, a Chinese message, the field key, and a character position; they do not include Python tracebacks, file paths, SQL, or raw values. Log the full internal context separately, correlated with the calculation batch and row.
7. **Security regression suite.** Keep the 15-attack corpus in the test suite, add fuzz/property tests for the tokenizer/parser (no crash, no unbounded memory/time), and add a test that asserts the formula module does not import/use `eval`, `exec`, `compile`, `ast.parse`, `importlib`, `subprocess`, `os`, or network modules. Run it in CI.
8. **Audit and snapshot.** Store the original formula text, a normalized form, the compiled hash/engine version, the actor and timestamp, and the resolved configuration snapshot used for each payroll month. This is required by the map's traceability boundary and makes it possible to explain historical results after a formula edit.

### 5.4 Residual risks and open security questions

- **Decimal denial of service.** Decimal operations are not free, and a pathological formula with many multiplications of large numbers could be expensive. The step budget and 30-digit literals bound this in the prototype, but the production implementation should also cap the result's adjusted exponent and reject non-finite results. The prototype's final-range check is weaker than the arithmetic context check; the implementation should check both.
- **Boundary conversion.** openpyxl returns Python floats for numeric cells. Converting with `Decimal(str(value))` preserves the usual decimal spelling but is not a lossless xlsx parser for extreme precision. The import pipeline should define a maximum precision/scale and reject values that do not fit, or parse the sheet XML with Decimal if exactness matters. This belongs to #48 (import contract) but the formula engine must not accept raw floats.
- **Timeout semantics.** The prototype has an evaluation-step budget but no wall-clock timeout. The requirement says "设单表达式超时" (§4.4). #47 should decide whether the step budget is the accepted interpretation or whether the batch runner enforces a hard deadline. Do not use `signal.alarm` in FastAPI request handlers without understanding thread/async interactions.
- **Comparison chaining.** The prototype accepts `1 < 2 < 3` as left-associative comparisons. That is not useful for payroll and can confuse authors. #47 should reject chained comparisons (require parentheses or a single comparison per `IF` condition) or explicitly document the semantics.
- **Chinese labels and canonical keys.** The prototype can parse Chinese identifiers, but the production contract should store canonical keys and resolve labels at the UI boundary. This avoids duplicate dependencies, homoglyph confusion, and label renames breaking history.
- **Function evolution.** Every added function is a new AST node and a new security review. Text/date/lookup functions must not be added by exposing a general Python call mechanism.

## 6. Minimal verification experiment

The experiment was run in a throwaway virtual environment at `/tmp/payroll-formula-exp` with CPython 3.14.4, using `uv venv` and `uv pip install simpleeval asteval formulas pycel`. Installed versions: simpleeval 1.0.8, asteval 1.0.10, formulas 1.3.4, pycel 1.0b30. The custom prototype and test harness were also in that directory; **none of these scripts are committed to the repository or merged into production code**, per the planning constraint.

### 6.1 Semantic results

| Test | Custom prototype | simpleeval | asteval (`minimal=True`) | formulas | pycel |
| --- | --- | --- | --- | --- | --- |
| `0.1 + 0.2` | `0.3` (Decimal) | `0.30000000000000004` | `0.30000000000000004` | `0.30000000000000004` | n/a (3.14 parse failure) |
| Decimal field + literal | Works | `TypeError` | `TypeError` | Coerced to float/Array | n/a |
| `ROUND(2.345, 2)` | `2.35` | Works only with a caller-supplied Decimal wrapper | Same | `2.35` | `2.35` (trivial formula) |
| `ROUND(1.005, 2)` | `1.01` | Caller wrapper needed | Caller wrapper needed | `1.0` (float scaling) | n/a |
| `ROUND(-2.5, 0)` | `-3` | Caller wrapper needed | Caller wrapper needed | `-3` | n/a |
| `IF(1=1, 10, 1/0)` | `10` (lazy) | Raises `ZeroDivisionError` | Returns `None` with an error | `10` (lazy) | n/a |
| `1 = 1`, `1 <> 2` | `True`, `True` | Python `SyntaxError` | `None` with errors | Works (Excel parser) | Works (Excel parser) |
| `SUM(1,2,3)` | `6` | Needs a varargs wrapper | Works via symbol table | `6.0` (`np.float64`) | Works for cell refs |
| `{param}` | First-class | Not supported | Not supported | Array constant; 2-D `Array` | Not supported |
| Chinese identifier (`带薪假`) | Parses (with label resolution) | Python identifiers may parse, but no label mapping | Same | Excel name rules; not a label map | Excel name rules |
| Error position | Character offset + field key | `SyntaxError` has line/offset; semantic errors no offset | `ExceptionHolder` has line/column and node; no field/batch context | Formula/cell message; no position | Cell-level |
| Cycle detection | `a -> b -> c -> a` with path | None | None | Circular cells omitted from solution in the test | Iterative mode; no field-level path |
| Python 3.14 | Works | Works | Works | Works with `SyntaxWarning`s | Arithmetic fails (`ast.Str`) |

The custom prototype's default-formula chain produced:

```
base_pay = 9195.402298850574712643678160
performance = 231.76
overtime_pay_actual = 228.5714285714285714285714286
normal_pay = 10305.73
gross = 11899.98
net = 10399.98
```

The raw sum before the explicit `ROUND` in `normal_pay` was `10305.73372742200328407224958949096880132`; the formula's `ROUND(...,2)` is what produces `10305.73`. This is a concrete example for #47: the engine must not add an implicit rounding step at every field, and the consistency check must compare values with the same explicit rounding contract as the formulas. Rounding each component before summing can change results in other cases (for example, `0.005 + 0.005`: per-component half-up gives `0.02`, while sum-then-round gives `0.01`), so the decision must be explicit.

### 6.2 Security results

The custom prototype rejected all of the following at parse time, with a character position: `().__class__`, `().__class__.__bases__[0].__subclasses__()`, `__import__('os').system('id')`, `open('/etc/passwd').read()`, `eval('1+1')`, `getattr((), '__class__')`, `(lambda:1)()`, `[x for x in (1,2)]`, `a.b`, `a[0]`, `[1,2]`, `1;2`, `1 if 1 else 2`, an over-2,000-character expression, 150-level nesting, and a 40-digit numeric literal.

For comparison:

- simpleeval blocked the dunder/import/open/getattr/lambda/comprehension/format attacks but allowed `'abc'[0]`. Current version 1.0.8 is patched for CVE-2026-32640.
- asteval `minimal=True` allowed `open('/etc/passwd').read()` and returned the file contents; it also allowed `'abc'.upper()`, `d['secret']`, and `l.append(1)`. A custom symbol table plus removed `attribute`/`subscript` handlers blocked those, but the `IF` function still evaluated both branches and returned `None` on the unused `1/0`.
- formulas rejected `=__import__("os")` as an unknown function in the experiment; it is not a sandbox and should not be treated as one.
- pycel's released 1.0b30 has the formula-injection CVE noted above (master fix unreleased) and cannot compile ordinary arithmetic on 3.14.

### 6.3 Performance results

Synthetic benchmark, Decimal values for the custom engine, floats for the libraries (their natural numeric type). No database I/O, no HTTP overhead. The numbers are indicative, not a capacity plan.

| Scenario | Result |
| --- | --- |
| Custom: compile 14 default-formula-shaped fields | 0.332 ms total |
| Custom: 500 employees × 14 fields (7,000 field evals) | 0.079 s, 11.3 µs/field |
| Custom: 500 employees × 40 fields (20,000 field evals) | 0.175 s, 8.8 µs/field |
| Custom: 20,000 evals of the 20-node `performance` formula | 0.526 s, 26.3 µs/eval |
| simpleeval: 5,000 evals of a 6-operation formula, parse each time | 18.4 µs/eval |
| asteval: 5,000 evals, parse once and reuse AST | 8.3 µs/eval |
| formulas: 5,000 evals of a compiled standalone formula | 502.5 µs/eval |
| formulas: 200-row × 4-formula-field workbook | 2.316 s load/finish + 0.623 s calculate |
| pycel: arithmetic formula on Python 3.14 | Fails with `FormulaParserError: module 'ast' has no attribute 'Str'` |

The custom engine is fast enough that the monthly run is dominated by database/import work, not formula evaluation. It also has the advantage that compile-once/evaluate-many is explicit: the graph is validated once per scheme, and only the per-employee scope changes.

## 7. Recommendation

**Adopt an in-house, stdlib-only formula engine: tokenizer + Pratt/recursive-descent parser + whitelisted tuple-AST evaluator over `Decimal`, plus an engine-owned dependency graph with cycle detection and deterministic topological ordering.** Use `ROUND_HALF_UP` (ties away from zero) for `ROUND`, make `IF` lazy, and enforce hard structural limits. Do not adopt simpleeval, asteval, formulas, pycel, or `xlcalculator` as the engine.

Rationale, in order of importance:

1. **Security boundary:** the grammar exposes no Python object model. This is stronger and easier to review than a blocklist over a Python AST, and it is the only option that satisfies the stated "no eval / no unrestricted expression library" constraint without a wrapper.
2. **Semantics:** Excel `=`/`<>`, `{param}`, lazy `IF`, and Excel `ROUND` are requirements, not conveniences. Only the custom parser and formulas support the Excel-shaped syntax; only the custom parser supports all four with Decimal.
3. **Decimal correctness:** formulas silently returns floats and even `ROUND(1.005,2)=1.0`; simpleeval/asteval cannot mix Decimal fields with their float literals. For payroll, this is a correctness issue, not a preference.
4. **Dependency correctness:** the engine must report cycles by field path and reject unknown fields before calculation. The library engines' graphs are workbook/cell graphs; even formulas, which has a real graph, silently omitted the circular cells in the test instead of producing a field-level error.
5. **Performance and dependency footprint:** the prototype handles 500×40 in ~0.18 s; formulas is ~500 µs per evaluation plus a numpy/scipy/schedula stack. The custom engine has no third-party runtime dependency.
6. **License and maintenance:** stdlib only; no EUPL/GPL review, no stale beta, no external security advisories on the engine itself. The parser is small enough to fuzz and keep current with Python 3.14.

Implementation shape:

- `formula/tokenizer.py`: token types, positions, limits.
- `formula/parser.py`: Pratt/recursive descent, AST tuples, function arity checks.
- `formula/evaluator.py`: Decimal evaluator, lazy `IF`, function whitelist, error types, step budget.
- `formula/graph.py`: dependency extraction, cycle detection with path, deterministic topological order, unknown-dependency checks.
- `formula/service.py`: compile/cache per scheme/formula hash, evaluate a row, build the calculation snapshot; config-save validation uses the same compiler.
- Tests: unit tests for syntax/rounding/errors, the security corpus, graph tests, golden cases, and a 500×40 performance smoke marker.

Do not commit the prototype; use it as a design reference and rewrite it as production code with the repo's typing/lint standards when the implementation ticket starts.

## 8. Implications for ticket #47

The following are concrete decisions #47 should adopt. Items marked "Decide" need the human decision #47 is designed to elicit; the recommendation is given so the default is clear.

1. **Adopt the custom engine.** Do not add simpleeval, asteval, formulas, pycel, or xlcalculator as a dependency. Record the rejection reasons in the decision record: Python syntax/float/eager `IF` (simpleeval/asteval), workbook abstraction/float/cycle behavior/EUPL (formulas), GPL/no-release-since-2021/Python 3.14 break/CVE (pycel).
2. **Canonical syntax.** Store formulas without a leading `=` but accept and strip one optional leading `=` in the editor/import. Field references are canonical ASCII keys (`base_pay`); parameter references are `{param}`; function names are case-insensitive; field and parameter names are case-sensitive. Reject string literals, cell references, sheet references, `$`, `**`, `%`, `&`, and all Python-only syntax in V1.
3. **Functions and arities.** Whitelist `IF(3, lazy)`, `ROUND(2)`, `SUM(n>=1)`, `MIN(n>=1)`, `MAX(n>=1)`, `ABS(1)`. `IF` uses Excel truthiness for numeric conditions (0 false, nonzero true) and only evaluates the selected branch. No `IFERROR`, lookup, text, or date functions in V1; add them later only as explicit AST nodes with their own tests.
4. **Comparisons.** Support `< <= > >= = <>`, and optionally accept `==`/`!=` as aliases. Decide whether chained comparisons are rejected (recommended) or left-associative; document it in the formula editor help and golden cases. `=` is equality, never assignment.
5. **Decimal context.** All formula values are `Decimal`; no float inside the engine. Use precision 28 (a named constant), an explicit context rounding mode (recommend `ROUND_HALF_UP` for consistency with Excel `ROUND`, or document why another mode is chosen), `Emax=100`/`Emin=-100`, and reject non-finite results and values outside the payroll field's scale. Convert imported numeric cells with `Decimal(str(value))` or a stricter parser at the import boundary; never pass raw openpyxl floats into formulas.
6. **`ROUND` semantics.** `ROUND(x, n)` is Excel half-away-from-zero, implemented with `Decimal.quantize` and `ROUND_HALF_UP`; support negative `n` (tens/hundreds) within a bounded range. Golden cases must include `ROUND(2.345,2)=2.35`, `ROUND(1.005,2)=1.01`, `ROUND(-2.5,0)=-3`, and a negative-`n` case. Confirm the tie rule against the business's Excel version; the Microsoft `ROUND` page describes the function but the tie behavior is easiest to lock with golden cases.
7. **Per-step vs final rounding.** The engine does not implicitly round every field; a formula's value is the value its explicit `ROUND` calls produce. Decide the storage contract: recommended is to normalize every monetary field formula to end with `ROUND(...,2)`, so stored and in-memory values agree, and then make the three consistency checks exact. If instead raw intermediate values must remain unrounded for downstream formulas, store both raw and rounded values and state clearly which one downstream formulas and consistency checks use. The experiment shows the difference is observable (`normal_pay` raw sum `10305.7337...` versus rounded `10305.73`), and per-component rounding can differ from sum-then-round.
8. **Sign convention.** Deduction fields (`social_this`, `tax`, `paid_advance`) are stored negative, as the requirement's `net = gross + deduct_sum` implies. Document that the UI may display the absolute value as "扣款" but the stored/formula value is negative; add validation warnings if a deduction field is positive or an addon field is negative.
9. **Missing and empty values.** Treat a missing field or parameter as a configuration/data error with the field key and position; do not silently coerce `NULL` to zero inside the evaluator. Normalize blank numeric import cells to zero in the import layer (with a visible warning/contract), before formula evaluation. Division by zero is an evaluation error at the operator position; no implicit `IFERROR`. Decide whether the UI should offer a formula-level guard pattern in the default formulas.
10. **Dependency graph.** Build the graph per calculation scheme from the compiled ASTs; treat `plan`/`import`/`fixed` fields as inputs and `formula` fields as nodes. Reject unknown field and parameter references at save time and again when loading a snapshot. Detect self and indirect cycles with a path such as `a -> b -> c -> a`; use a deterministic topological order (sort by display order, then key) so results and error messages are stable. Cache the compiled formula/graph by a hash of the formula text plus engine version; invalidate on save.
11. **Sandbox limits.** Adopt at least: 2,000-character expression, 500 tokens, 100 nesting depth, 30-digit numeric literals, 20,000 evaluation steps, `ROUND` digits `-10..10`, Decimal precision 28, finite/range checks. Decide whether the step budget is the required "single-expression timeout" or add a wall-clock deadline at the batch worker; do not rely on `signal` in async request handlers. Add a CI test that forbids `eval`, `exec`, `compile`, `ast.parse`, `importlib`, `subprocess`, and network imports in the formula module.
12. **Error contract.** Every syntax error carries a character offset (and line/column if multiline input is allowed), expected/found tokens, and a stable code; every evaluation error carries the field key, position, row/employee context at the batch layer, and a Chinese message. Do not return Python exception text or stack traces. The formula editor's "实时试算" uses the same compiler and error types as the monthly run, with a chosen sample employee/scope and clearly labeled sample values.
13. **Chinese labels.** Store canonical English field keys in formulas; resolve Chinese labels to keys in the editor at insert/save time. Rewrite the requirement's default `addon_sum` (`SUM(带薪假,加班补贴,...)`) to keys, or store an explicit alias map; do not allow arbitrary label strings to become dependency nodes. Record label renames in the audit trail if labels are ever user-editable.
14. **Performance target and caching.** Use compile-once/evaluate-many per calculation scheme; reuse the AST/graph across hundreds of employees; batch-load params and field values; measure with a 500×40 smoke test. The prototype's 0.175 s is a reference, not a requirement; set the actual target in the implementation/acceptance ticket. Avoid re-parsing per employee or per row.
15. **Golden cases and acceptance.** Define `docs/specs/payroll-golden-cases/` around the engine contract: syntax, every default formula, all four `ROUND` cases, per-step vs final rounding, lazy `IF`, negative deductions, missing field/param, division by zero, self/indirect cycle paths, unknown function, Chinese alias resolution, security corpus, and the 500×40 performance smoke. Each case records formula text, Decimal inputs (as strings), expected Decimal/error, and engine version. Include at least one case where rounding order changes the result.
16. **Audit and snapshot.** Persist formula text, normalized text, compiled hash/engine version, actor/time, and the resolved configuration snapshot per payroll month. Recalculation and "which months are stale" should use the reverse dependency closure from the graph. This is consistent with the map's traceability boundary and with #47's "配置版本与留痕" requirement.

## 9. Uncertainty and follow-ups

- **Excel `ROUND` tie rule.** The implementation target is half-away-from-zero, and the experiment confirms it for `2.345`, `1.005`, `-2.5`, and negative digits. The Microsoft `ROUND` page describes the function and negative `num_digits` but does not spell out the tie rule in the fetched text; confirm with the business's Excel version and lock it in golden cases. Flagged rather than treated as settled.
- **formulas cycle behavior.** In the test, circular cells D1/D2 were absent from the calculated solution with no surfaced error. The root cause/configuration was not investigated because the library is not recommended; do not cite this as a general claim about schedula.
- **License interpretation.** EUPL-1.1+ and GPL-3.0 obligations depend on distribution/SaaS specifics and are a legal question, not a research conclusion. The recommendation avoids the question by using stdlib only.
- **Python 3.14 compatibility of formulas.** It ran in the experiment with `SyntaxWarning`s but has no 3.14 classifier or `Requires-Python`. "Works today" is not a compatibility guarantee.
- **Performance.** The numbers are synthetic, single-process, Decimal-vs-float comparisons, with no database, HTTP, serialization, or audit overhead. They establish an order of magnitude and a design direction, not a capacity plan.
- **Timeout.** The prototype's step budget bounds work but is not a wall-clock timeout. #47 must decide how to satisfy §4.4's "单表达式超时" in the FastAPI execution model.
- **Import precision.** openpyxl's float conversion and the xlsx decimal representation may lose precision for unusual values; the import contract (#48) should set precision/scale and the formula engine should reject floats. This is a cross-ticket dependency, not fully resolved here.
- **Default formula normalization.** The requirement's `addon_sum` uses Chinese labels and its `base_pay`/`overtime_pay_actual` are unrounded intermediates. #47 must reconcile the formulas with the chosen rounding/storage contract; this report provides the evidence but not the final formula text.

## 10. References

Primary sources and evidence used above:

- Requirement: [`docs/requirement/rx-hr-requirement.html`](../requirement/rx-hr-requirement.html), §3.9 (field formulas), §4.1 (engine flow), §4.2 (syntax), §4.3 (default formulas), §4.4 (security/reliability).
- Python `decimal` documentation: <https://docs.python.org/3/library/decimal.html> — `ROUND_HALF_UP` is "Round to nearest with ties going away from zero"; context precision/rounding/exponent semantics.
- Python `eval` documentation: <https://docs.python.org/3/library/functions.html#eval> — "executes arbitrary code", warning about untrusted input.
- Python 3.14 What's New, removed `ast` classes: <https://docs.python.org/3/whatsnew/3.14.html#removed> — `ast.Str`, `ast.Num`, `ast.Bytes`, `ast.NameConstant`, `ast.Ellipsis` removed.
- CWE-95, Improper Control of Generation of Code: <https://cwe.mitre.org/data/definitions/95.html>.
- OWASP Injection Prevention Cheat Sheet: <https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html>; OWASP Top 10 2021 A03 Injection: <https://owasp.org/Top10/2021/A03_2021-Injection/>.
- Python `ast.literal_eval` docs (not DoS-safe, untrusted input not recommended): <https://docs.python.org/3/library/ast.html#ast.literal_eval>.
- simpleeval: PyPI <https://pypi.org/project/simpleeval/> (1.0.8, 2026-09-12, MIT, Requires-Python >=3.9); source <https://github.com/danthedeckie/simpleeval>; OSV GHSA-44vg-5wv2-h2hg / CVE-2026-32640 <https://osv.dev/vulnerability/GHSA-44vg-5wv2-h2hg>.
- asteval: PyPI <https://pypi.org/project/asteval/> (1.0.10, 2026-08-21, MIT, Requires-Python >=3.10, classifiers through 3.14); docs <https://lmfit.github.io/asteval/>; source <https://github.com/lmfit/asteval>; OSV entries GHSA-3wwr-3g9f-9gc7 (CVE-2025-24359), GHSA-vp47-9734-prjw, GHSA-89v8-rhwq-hf77 (CVE-2026-55244), GHSA-9w56-46f6-3qhx (CVE-2026-102734).
- formulas: PyPI <https://pypi.org/project/formulas/> (1.3.4, 2026-03-11, EUPL-1.1+); docs <https://formulas.readthedocs.io/>; source <https://github.com/vinci1it2000/formulas>; `ROUND` implementation <https://github.com/vinci1it2000/formulas/blob/master/formulas/functions/math.py>; literal token compilation <https://github.com/vinci1it2000/formulas/blob/master/formulas/tokens/operand.py>.
- pycel: PyPI <https://pypi.org/project/pycel/> (1.0b30, 2021-10-13, GPL-3.0); canonical source <https://github.com/dgorissen/pycel> (the PyPI homepage's `stephenrauch/pycel` is a stale fork); unreleased CVE fix commit <https://github.com/dgorissen/pycel/commit/1981c228b310c4747cf335c103ed6ba928633bfd>; OSV GHSA-pw67-xjhq-389w / CVE-2024-53924 <https://osv.dev/vulnerability/GHSA-pw67-xjhq-389w>.
- xlcalculator: PyPI <https://pypi.org/project/xlcalculator/> (0.5.0, 2023-02-06, MIT) — checked for metadata only, not tested.
- Lark: PyPI <https://pypi.org/project/lark/> (1.3.1, 2025-10-27, MIT); RestrictedPython: PyPI <https://pypi.org/project/RestrictedPython/> (9.0, 2026-11-04) — considered only as parser/restriction tooling, not as the engine.
- Microsoft Excel `ROUND` documentation: <https://support.microsoft.com/en-us/office/round-function-c018c5d8-40fb-4053-90b1-b3e7f61a213c> (syntax, negative `num_digits`, relationship to ROUNDUP/ROUNDDOWN; the page does not spell out the tie rule verbatim, so golden cases must lock it).

Experiment artifacts were throwaway files in `/tmp/payroll-formula-exp` (not committed): `custom_engine.py`, `test_custom_engine.py`, `exp_simpleeval.py`, `exp_asteval.py`, `exp_formulas.py`, `exp_formulas2.py`, `exp_excel_workbooks.py`, `exp_pycel.py`, `exp_semantics_perf.py`, and `exp_formulas_scale.py`.
