# Evaluation Concepts for LLM-Generated SQL

Reference notes for the `ca_wi_rag` conversational analytics project — how evaluation
concepts apply to the SQL that Claude generates, and how to implement them in
`validate_sql` in `mcp_server.py`.

---

## The big idea: evaluation = generate → grade → repair

In LLM engineering, "evals" show up in two places, and this project will eventually
want both:

| | Runtime validation (guardrails) | Offline evaluation (benchmarks) |
|---|---|---|
| **When** | Every request, inside the agent loop | Before you ship a prompt/model change |
| **What it does** | Catches a bad SQL *now* and feeds the error back so Claude regenerates | Measures quality across a golden dataset (e.g. 50 known question→SQL pairs) |
| **Your code** | `validate_sql` | A test script you'd run against `agent.py` |

What makes runtime validation powerful in an *agentic* setup: the tool result goes
back into `messages` and Claude reads it. If `validate_sql` returns
`"Validated SQL"` no matter what, the loop learns nothing. If it returns
*"column `prod_name` does not exist in table `products`; available columns are:
prod_cd, prod_nm, …"*, Claude will fix the SQL and call the tool again —
self-correction for free.

> **The quality of your error messages is the quality of your repair loop.**

---

## The evaluation pyramid for text-to-SQL

Order checks from cheap/deterministic to expensive/model-graded. Run the cheap ones
first and short-circuit on failure.

### Layer 1 — Syntactic validity (deterministic, ~1ms)
Does the SQL even parse? Use a SQL parser like `sqlglot`.
Offline-eval metric: **validity rate** (% of generations that parse).

### Layer 2 — Safety / policy (deterministic)
The system prompt says "ONLY SELECT, never UPDATE/DELETE" — but a prompt is a
request, not an enforcement. **Never trust the generator to police itself; enforce
policy in code.** Walk the parsed AST and reject any
INSERT/UPDATE/DELETE/DROP/CREATE/ALTER, multiple statements, etc.

### Layer 3 — Schema grounding (deterministic)
The #1 failure mode of LLM-generated SQL is *hallucinated tables and columns* —
plausible names like `product_name` when the real column is `prod_nm`. Extract every
table/column from the AST and check it against a ground-truth catalog. The ground
truth already exists: `retail_schema_documentation.txt` has a regular structure
(`TABLE: x`, `Column : y`) that can be parsed into a catalog once.

This layer also doubles as an **eval of the RAG step**: if the SQL uses a real table
that wasn't in the retrieved chunks, that's a retrieval miss, not a generation
error — different fix (top_k, chunking), and worth logging separately.

### Layer 4 — Execution validation (ground truth from the database)
Run `EXPLAIN <sql>` or the query with `LIMIT 0` against the real DB. The database
engine is the ultimate validator — it catches type mismatches, ambiguous columns,
bad joins. (Applies once `run_sql` is wired to a real database.)

In offline evals this becomes the gold-standard metric, **execution accuracy**:
run the generated SQL and the reference SQL and compare *result sets*, not SQL
strings — two different queries can both be correct.

### Layer 5 — Semantic intent alignment (LLM-as-judge)
Syntax, safety, and schema can all pass while the SQL still answers the *wrong
question* — e.g. user asks "top 5 categories by revenue" and the SQL sums quantity
instead of revenue, or forgets the `cat_sts_cd = 'I'` filter the schema doc calls
out. No deterministic check can catch that, so use a second model call as a
**judge**: give it the user question + SQL + relevant schema, and a rubric, and ask
for a structured verdict. This is why `validate_sql` takes `user_input` alongside
`sql` — the judge needs the intent to grade against.

Rules of thumb for judges:
- Give an explicit rubric (not "is this good?")
- Ask for structured output (verdict + specific issues)
- Run them *last* — they're the slowest, costliest, and noisiest layer

---

## Drop-in implementation for `validate_sql`

Requires `pip install sqlglot` (add to requirements.txt). Implements layers 1–3
plus an optional layer-5 judge using the existing `claude_init()` helpers.

```python
import json
import re
import sqlglot
from sqlglot import exp

SCHEMA_DOC = os.path.join(os.path.dirname(__file__), "retail_schema_documentation.txt")

def load_catalog() -> dict[str, set[str]]:
    """Parse the schema doc into {table_name: {columns}} as ground truth."""
    catalog, current = {}, None
    with open(SCHEMA_DOC) as f:
        for line in f:
            t = re.match(r"TABLE:\s+(\w+)", line)
            c = re.match(r"Column\s+:\s+(\w+)", line)
            if t:
                current = t.group(1)
                catalog[current] = set()
            elif c and current:
                catalog[current].add(c.group(1))
    return catalog

CATALOG = load_catalog()

FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Drop,
             exp.Create, exp.Alter, exp.Merge, exp.TruncateTable)

@mcp.tool()
def validate_sql(sql: str, user_input: str) -> str:
    """Validate generated SQL: syntax, read-only policy, schema grounding,
    and intent alignment. Returns a JSON verdict. If verdict is FAIL, fix
    every listed error and call validate_sql again with the corrected SQL."""
    errors = []

    # Layer 1: syntax
    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError as e:
        return json.dumps({"verdict": "FAIL", "stage": "syntax", "errors": [str(e)]})

    # Layer 2: safety — SELECT-only, enforced in code not in the prompt
    if not isinstance(parsed, exp.Select) or list(parsed.find_all(*FORBIDDEN)):
        return json.dumps({"verdict": "FAIL", "stage": "safety",
                           "errors": ["Only single SELECT statements are allowed."]})

    # Layer 3: schema grounding against the full catalog
    tables = {t.name for t in parsed.find_all(exp.Table)}
    for t in tables - CATALOG.keys():
        errors.append(f"Table '{t}' does not exist. Valid tables: {sorted(CATALOG)}")
    all_cols = set().union(*(CATALOG.get(t, set()) for t in tables)) if tables else set()
    for col in {c.name for c in parsed.find_all(exp.Column)} - all_cols:
        errors.append(f"Column '{col}' not found in {sorted(tables)}. "
                      f"Available columns: {sorted(all_cols)}")
    if errors:
        return json.dumps({"verdict": "FAIL", "stage": "schema", "errors": errors})

    # Layer 5: LLM-as-judge for intent alignment (optional but instructive)
    client, model, max_tokens = claude_init()
    judge_prompt = f"""You are grading a SQL query against the user's question.
User question: {user_input}
SQL: {sql}
Rubric: (1) Does the SQL retrieve what the question asks for — right measures,
filters, grouping, ordering? (2) Are status/soft-delete filters applied where
the schema requires them? Respond with ONLY JSON:
{{"aligned": true|false, "issues": ["..."]}}"""
    resp = claude_call_wo_system_tools(model, max_tokens, client,
                                       [create_user_msg(judge_prompt)])
    verdict = json.loads(resp.content[0].text)
    if not verdict.get("aligned", False):
        return json.dumps({"verdict": "FAIL", "stage": "intent",
                           "errors": verdict.get("issues", [])})

    return json.dumps({"verdict": "PASS",
                       "checks": ["syntax", "safety", "schema_grounding", "intent"]})
```

---

## Three design points (general eval principles, not SQL-specific)

1. **Structured, actionable failures.** Returning JSON with a `stage` and specific
   `errors` (including the *valid alternatives* — "available columns are…") turns
   the tool result into few-shot repair guidance. A bare "validation failed" forces
   Claude to guess.

2. **The tool docstring is part of the loop.** The docstring tells Claude what to
   do on FAIL ("fix every listed error and call validate_sql again"). Claude reads
   tool descriptions; that's where the repair protocol lives. Correspondingly,
   **delete the line "Assume validate_sql tool will pass all your SQLs for now"**
   from the system prompt in `agent.py` — otherwise Claude may shrug off real
   failures. (Also: the active system prompt references `get_schemas_from_txt`, but
   the tool actually registered is `get_schemas_from_rag` — fix while in there.)

3. **Deterministic before model-graded.** The judge call costs money, takes
   seconds, and is itself fallible. Layers 1–3 are free, instant, and never
   wrong — let them filter first so the judge only sees plausible SQL.

---

## Where to go next: offline evals

Once the runtime validator works, build a small **golden dataset** — 20–50
questions about the retail schema, each with a reference SQL verified by hand.
Then a script that runs each question through `agent.py` and reports:

- **Validity rate** — layer 1 pass %
- **Schema-grounding rate** — layer 3 pass %
- **Execution accuracy** — once a real DB is behind `run_sql`: generated query's
  result set matches the reference query's result set

That gives you a **regression suite**: every time you tweak the system prompt, the
chunking strategy, or `top_k` in the RAG, re-run it and see whether the change
helped or hurt, instead of eyeballing one query. The same layers built for runtime
become the offline metrics.
