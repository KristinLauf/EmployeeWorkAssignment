# Employee pay data — take-home

## How to run

Requires Python 3.7+ (standard library only — no third-party packages).

# Run all six tasks against the data files and print results
py employee.py

# Run the test suite
py -m unittest test_employee -v

# To call the methods directly:

```
python
from employee import (
    load, all_job_roles, average_salary_for_role,
    headcount_changes, biggest_raise, nearest_salary,
    most_similar, SalaryIndex,
)

jan = load("january.json")
feb = load("february.json")

all_job_roles(jan)
average_salary_for_role(jan, "Helpers--Roofers")
headcount_changes(jan, feb)
biggest_raise(jan, feb)
nearest_salary(jan, 8000)
most_similar(jan, jan[0].employee_id)
```

## Data format

Each file is a JSON array of **positional arrays** (not objects). On load,
each row is parsed into a typed `Employee` NamedTuple so the rest of the
code reads in named fields (`emp.salary`) rather than magic indices:

| Position | Field                     |
|----------|---------------------------|
| 0        | employee_id               |
| 1        | gender (1=male, 2=female) |
| 2        | job_role                  |
| 3        | experience_months         |
| 4        | performance               |
| 5        | has_mgmt_responsibility   |
| 6        | education                 |
| 7        | salary                    |
| 8        | bonus                     |

A malformed row (wrong number of fields) fails loudly at load time rather
than producing wrong answers downstream.

## Task notes and assumptions

### Task 3 — headcount changes
Employees are identified solely by `employee_id`. An id in January but not
February has **left**; an id in February but not January has **joined**. If
the same id appears in both months with changed fields (e.g. a role change
or raise), that employee is still present. Both lists are returned sorted by
id for stable, reproducible output.

### Task 4 — biggest raise
"Raise" is the change in **salary** only, not total compensation — the brief
lists `salary` and `bonus` as separate fields, and a bonus can swing for
reasons unrelated to a raise. Only employees present in both months are
considered (a new joiner has no January baseline). If every common employee
took a pay cut, the function returns the smallest cut. Ties are broken by
lowest `employee_id`.

### Task 5 — nearest salary
**Single query:** sort employees by salary — O(n log n) — then binary-search
the target — O(log n). The sort dominates.

**Many queries:** build a `SalaryIndex` once (O(n log n)); each subsequent
query is O(log n). A naive per-query scan is O(n) each, so the pre-sort pays
off after roughly log n queries. Ties are broken by lowest `employee_id`.

### Task 6 — most similar employee
Similarity is the inverse of a mixed distance:

- **Numeric fields** (`experience_months`, `performance`, `salary`, `bonus`,
  and `education` as an ordinal Elementary=0 … PhD=4): z-score normalised per
  field, so large-magnitude fields (salary) don't swamp small ones
  (performance). The target's normalised vector is computed once, not per
  comparison.
- **Categorical fields** (`job_role`, `has_mgmt_responsibility`): each
  mismatch adds a fixed penalty of 1.0 (one normalised standard-deviation
  unit).

Lower distance = more similar; ties are broken by lowest `employee_id`.

**Gender is excluded by default.** This dataset — gender, salary, bonus, and
human-capital factors across two months — reads like a pay-equity study. For
that purpose the useful question is "who is comparable on legitimate factors
*regardless* of gender", so their pay can be contrasted. Pass
`include_gender=True` to fold gender into the metric instead.

**Assumption:** all included fields are weighted equally. A real deployment
would want business-specified weights (and possibly labelled "similar" pairs
to tune them); the fixed-penalty structure makes that easy to adjust. An
unrecognised education label raises rather than being silently scored.

## Tests

`test_employee.py` covers each task with unit tests (edge cases: empty input,
no match, full turnover, pay cuts, out-of-range targets, deterministic
tiebreaks, the gender flag, and the unknown-education guard) plus integration
tests that run against the real `january.json` / `february.json` files.
