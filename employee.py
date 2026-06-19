"""Employee pay data — take-home tasks.

Records arrive as positional JSON arrays.  They are parsed into the typed
``Employee`` NamedTuple at load time, so the rest of the code reads in terms
of named fields (``emp.salary``) instead of magic indices (``emp[7]``).

Run ``py employee.py`` to execute all six tasks against the data files.
"""

import bisect
import json
import math
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple


class Employee(NamedTuple):
    employee_id: int
    gender: int                     # 1 = male, 2 = female
    job_role: str
    experience_months: int
    performance: int
    has_mgmt_responsibility: int    # 0 / 1
    education: str
    salary: float
    bonus: float


# Ordinal encoding for education (used in the similarity metric)
EDU_ORDER = {"Elementary": 0, "High School": 1, "BS": 2, "MS": 3, "PhD": 4}


def load(path: str) -> List[Employee]:
    """Parse a monthly JSON file into a list of Employee records.

    Each row must have exactly the nine fields above in order; a malformed
    row raises TypeError here rather than failing silently downstream.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Employee(*row) for row in raw]


# ---------------------------------------------------------------------------
# Task 1 — list all job roles
# ---------------------------------------------------------------------------

def all_job_roles(employees: List[Employee]) -> List[str]:
    """Return a sorted list of unique job roles."""
    return sorted({emp.job_role for emp in employees})


# ---------------------------------------------------------------------------
# Task 2 — average salary for a given role
# ---------------------------------------------------------------------------

def average_salary_for_role(employees: List[Employee], role: str) -> Optional[float]:
    """Return the mean salary for *role*, or None if no employees match."""
    salaries = [emp.salary for emp in employees if emp.job_role == role]
    return sum(salaries) / len(salaries) if salaries else None


# ---------------------------------------------------------------------------
# Task 3 — who left and who joined between two months
# ---------------------------------------------------------------------------

def headcount_changes(jan: List[Employee], feb: List[Employee]) -> Dict[str, List[Employee]]:
    """Compare two monthly snapshots, keyed on employee_id.

    Returns {"left": [...], "joined": [...]}, each sorted by employee_id.
    An id present in both months (even with changed fields) counts as
    still present.
    """
    jan_ids = {e.employee_id: e for e in jan}
    feb_ids = {e.employee_id: e for e in feb}

    left   = [e for eid, e in jan_ids.items() if eid not in feb_ids]
    joined = [e for eid, e in feb_ids.items() if eid not in jan_ids]

    left.sort(key=lambda e: e.employee_id)
    joined.sort(key=lambda e: e.employee_id)
    return {"left": left, "joined": joined}


# ---------------------------------------------------------------------------
# Task 4 — biggest raise between two months
# ---------------------------------------------------------------------------

def biggest_raise(jan: List[Employee], feb: List[Employee]) -> Optional[dict]:
    """Find the employee with the largest absolute salary increase.

    Only employees present in both months are considered (a new joiner has
    no January baseline).  "Raise" is the change in salary, not total comp.
    Ties are broken deterministically by lowest employee_id.

    Returns a dict with employee_id, the January and February records, and
    the raise amount; or None if no employee appears in both months.
    """
    jan_map = {e.employee_id: e for e in jan}
    feb_map = {e.employee_id: e for e in feb}

    best = None
    best_key: Optional[Tuple[float, int]] = None
    for eid, jan_emp in jan_map.items():
        feb_emp = feb_map.get(eid)
        if feb_emp is None:
            continue
        amount = feb_emp.salary - jan_emp.salary
        # Maximise raise, then minimise id  ->  maximise (amount, -id)
        key = (amount, -eid)
        if best_key is None or key > best_key:
            best_key = key
            best = {"employee_id": eid, "jan": jan_emp, "feb": feb_emp, "raise": amount}
    return best


# ---------------------------------------------------------------------------
# Task 5 — nearest salary to a target
# ---------------------------------------------------------------------------

def _nearest_in_sorted(ordered: List[Employee], salaries: List[float], target: float) -> dict:
    pos = bisect.bisect_left(salaries, target)
    candidates = []
    if pos < len(ordered):
        candidates.append(ordered[pos])
    if pos > 0:
        candidates.append(ordered[pos - 1])
    # Closest by distance, ties broken by lowest employee_id.
    best = min(candidates, key=lambda e: (abs(e.salary - target), e.employee_id))
    return {"employee": best, "salary": best.salary, "delta": abs(best.salary - target)}


def nearest_salary(employees: List[Employee], target: float) -> dict:
    """Return the employee whose salary is closest to *target*.

    Single query: sort by salary O(n log n), then binary search O(log n);
    the sort dominates.  For *many* targets, build a SalaryIndex once and
    reuse it (each query then costs only O(log n)).  Ties are broken by
    lowest employee_id.
    """
    ordered  = sorted(employees, key=lambda e: e.salary)
    salaries = [e.salary for e in ordered]
    return _nearest_in_sorted(ordered, salaries, target)


class SalaryIndex:
    """Pre-built index for repeated nearest-salary queries.

    One-time build is O(n log n); each ``nearest`` call is O(log n).  Use
    this when answering many targets — it amortises the sort across queries
    (break-even is at roughly log n queries versus a per-query linear scan).
    """

    def __init__(self, employees: List[Employee]):
        self._ordered  = sorted(employees, key=lambda e: e.salary)
        self._salaries = [e.salary for e in self._ordered]

    def nearest(self, target: float) -> dict:
        return _nearest_in_sorted(self._ordered, self._salaries, target)


# ---------------------------------------------------------------------------
# Task 6 — most similar employee
# ---------------------------------------------------------------------------

class _Stat(NamedTuple):
    mean: float
    std: float


def _edu_value(education: str) -> int:
    """Map an education label to its ordinal rank, failing loudly on unknowns."""
    try:
        return EDU_ORDER[education]
    except KeyError:
        raise ValueError(f"Unknown education value: {education!r}")


def _compute_stats(employees: List[Employee]) -> Dict[str, _Stat]:
    def stat(vals: List[float]) -> _Stat:
        n = len(vals)
        mean = sum(vals) / n
        std  = math.sqrt(sum((v - mean) ** 2 for v in vals) / n)
        return _Stat(mean, std)

    return {
        "exp":    stat([e.experience_months          for e in employees]),
        "perf":   stat([e.performance                for e in employees]),
        "salary": stat([e.salary                     for e in employees]),
        "bonus":  stat([e.bonus                      for e in employees]),
        "edu":    stat([_edu_value(e.education)      for e in employees]),
    }


def _z(value: float, stat: _Stat) -> float:
    return (value - stat.mean) / stat.std if stat.std else 0.0


def _numeric_vector(emp: Employee, stats: Dict[str, _Stat]) -> Tuple[float, ...]:
    """Z-score normalised vector of the numeric / ordinal fields."""
    return (
        _z(emp.experience_months,      stats["exp"]),
        _z(emp.performance,            stats["perf"]),
        _z(emp.salary,                 stats["salary"]),
        _z(emp.bonus,                  stats["bonus"]),
        _z(_edu_value(emp.education),  stats["edu"]),
    )


def most_similar(employees: List[Employee], target_id: int,
                 include_gender: bool = False) -> Optional[dict]:
    """Find the employee most similar to the one with *target_id*.

    Distance combines z-score normalised numeric fields (experience,
    performance, salary, bonus, and education as an ordinal) with a fixed
    1.0 penalty per categorical mismatch (job_role, mgmt — and gender only
    if *include_gender* is True).  Lower distance = more similar.  Ties are
    broken by lowest employee_id.

    Gender is excluded by default: this dataset looks like a pay-equity
    study, where the useful question is "who is comparable on legitimate
    factors regardless of gender" so their pay can be contrasted.  Pass
    include_gender=True to fold gender into the similarity instead.

    Returns the best match and its distance, or None if target_id is absent
    or there are fewer than two employees.
    """
    id_map = {e.employee_id: e for e in employees}
    if target_id not in id_map or len(employees) < 2:
        return None

    target     = id_map[target_id]
    stats      = _compute_stats(employees)
    target_vec = _numeric_vector(target, stats)   # computed once, not per candidate

    best_emp  = None
    best_key: Optional[Tuple[float, int]] = None
    for emp in employees:
        if emp.employee_id == target_id:
            continue
        cand_vec = _numeric_vector(emp, stats)
        sq = sum((t - c) ** 2 for t, c in zip(target_vec, cand_vec))
        mismatches = ((emp.job_role != target.job_role)
                      + (emp.has_mgmt_responsibility != target.has_mgmt_responsibility))
        if include_gender:
            mismatches += (emp.gender != target.gender)
        dist = math.sqrt(sq) + mismatches

        key = (dist, emp.employee_id)   # minimise distance, then id
        if best_key is None or key < best_key:
            best_key = key
            best_emp = emp

    return {"employee": best_emp, "distance": best_key[0]}


# ---------------------------------------------------------------------------
# Demo runner — executes all six tasks against the data files
# ---------------------------------------------------------------------------

def _run_demo() -> None:
    here = Path(__file__).parent
    jan = load(str(here / "january.json"))
    feb = load(str(here / "february.json"))

    roles = all_job_roles(jan)
    print(f"Task 1 - {len(roles)} job roles:")
    for r in roles:
        print(f"    {r}")

    avg = average_salary_for_role(jan, "Helpers--Roofers")
    print(f"\nTask 2 - avg salary for Helpers--Roofers: {avg:.2f}")

    changes = headcount_changes(jan, feb)
    print("\nTask 3 - headcount changes:")
    print(f"    left:   {[e.employee_id for e in changes['left']]}")
    print(f"    joined: {[e.employee_id for e in changes['joined']]}")

    raise_ = biggest_raise(jan, feb)
    print("\nTask 4 - biggest raise:")
    print(f"    employee {raise_['employee_id']}: "
          f"{raise_['jan'].salary:.2f} -> {raise_['feb'].salary:.2f} "
          f"(+{raise_['raise']:.2f})")

    near = nearest_salary(jan, 8000)
    print("\nTask 5 - nearest salary to 8000:")
    print(f"    employee {near['employee'].employee_id}: "
          f"{near['salary']:.2f} (delta {near['delta']:.2f})")

    first_id = jan[0].employee_id
    sim = most_similar(jan, first_id)
    print(f"\nTask 6 - most similar to employee {first_id} (gender excluded):")
    print(f"    employee {sim['employee'].employee_id} (distance {sim['distance']:.3f})")


if __name__ == "__main__":
    _run_demo()
