"""Tests for employee.py — uses only the standard library."""

import unittest
from pathlib import Path

from employee import (
    Employee,
    SalaryIndex,
    all_job_roles,
    average_salary_for_role,
    biggest_raise,
    headcount_changes,
    load,
    most_similar,
    nearest_salary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_emp(employee_id, gender=1, job_role="A", experience_months=12,
             performance=2, has_mgmt_responsibility=0, education="BS",
             salary=5000.0, bonus=0):
    return Employee(employee_id, gender, job_role, experience_months,
                    performance, has_mgmt_responsibility, education,
                    salary, bonus)


# ---------------------------------------------------------------------------
# Task 1 — all_job_roles
# ---------------------------------------------------------------------------

class TestAllJobRoles(unittest.TestCase):
    def test_unique_and_sorted(self):
        emps = [make_emp(1, job_role="Glaziers"), make_emp(2, job_role="Electricians"),
                make_emp(3, job_role="Glaziers")]
        self.assertEqual(all_job_roles(emps), ["Electricians", "Glaziers"])

    def test_empty(self):
        self.assertEqual(all_job_roles([]), [])

    def test_single(self):
        self.assertEqual(all_job_roles([make_emp(1, job_role="Roofers")]), ["Roofers"])


# ---------------------------------------------------------------------------
# Task 2 — average_salary_for_role
# ---------------------------------------------------------------------------

class TestAverageSalaryForRole(unittest.TestCase):
    def test_basic(self):
        emps = [make_emp(1, job_role="Helpers--Roofers", salary=4000),
                make_emp(2, job_role="Helpers--Roofers", salary=6000),
                make_emp(3, job_role="Other", salary=99000)]
        self.assertAlmostEqual(average_salary_for_role(emps, "Helpers--Roofers"), 5000.0)

    def test_no_match_returns_none(self):
        emps = [make_emp(1, job_role="Other", salary=1000)]
        self.assertIsNone(average_salary_for_role(emps, "Helpers--Roofers"))

    def test_single_employee(self):
        emps = [make_emp(1, job_role="Helpers--Roofers", salary=7777)]
        self.assertAlmostEqual(average_salary_for_role(emps, "Helpers--Roofers"), 7777)


# ---------------------------------------------------------------------------
# Task 3 — headcount_changes
# ---------------------------------------------------------------------------

class TestHeadcountChanges(unittest.TestCase):
    def setUp(self):
        self.alice = make_emp(1)
        self.bob   = make_emp(2)
        self.carol = make_emp(3)

    def test_left(self):
        result = headcount_changes([self.alice, self.bob], [self.bob])
        self.assertEqual([e.employee_id for e in result["left"]], [1])
        self.assertEqual(result["joined"], [])

    def test_joined(self):
        result = headcount_changes([self.alice], [self.alice, self.carol])
        self.assertEqual(result["left"], [])
        self.assertEqual([e.employee_id for e in result["joined"]], [3])

    def test_no_change(self):
        result = headcount_changes([self.alice, self.bob], [self.alice, self.bob])
        self.assertEqual(result["left"], [])
        self.assertEqual(result["joined"], [])

    def test_full_turnover(self):
        result = headcount_changes([self.alice, self.bob], [self.carol])
        self.assertEqual([e.employee_id for e in result["left"]], [1, 2])
        self.assertEqual([e.employee_id for e in result["joined"]], [3])

    def test_changed_fields_still_present(self):
        # Same id, different salary -> not a join or a departure.
        jan = [make_emp(1, salary=5000)]
        feb = [make_emp(1, salary=9000)]
        result = headcount_changes(jan, feb)
        self.assertEqual(result["left"], [])
        self.assertEqual(result["joined"], [])


# ---------------------------------------------------------------------------
# Task 4 — biggest_raise
# ---------------------------------------------------------------------------

class TestBiggestRaise(unittest.TestCase):
    def test_picks_largest(self):
        jan = [make_emp(1, salary=5000), make_emp(2, salary=6000)]
        feb = [make_emp(1, salary=5500), make_emp(2, salary=8000)]
        result = biggest_raise(jan, feb)
        self.assertEqual(result["employee_id"], 2)
        self.assertAlmostEqual(result["raise"], 2000.0)

    def test_ignores_departed(self):
        jan = [make_emp(1, salary=5000), make_emp(2, salary=6000)]
        feb = [make_emp(1, salary=9000)]
        result = biggest_raise(jan, feb)
        self.assertEqual(result["employee_id"], 1)

    def test_no_common_employees(self):
        jan = [make_emp(1, salary=5000)]
        feb = [make_emp(2, salary=6000)]
        self.assertIsNone(biggest_raise(jan, feb))

    def test_negative_raise_allowed(self):
        jan = [make_emp(1, salary=5000), make_emp(2, salary=6000)]
        feb = [make_emp(1, salary=4000), make_emp(2, salary=5500)]
        result = biggest_raise(jan, feb)
        self.assertEqual(result["employee_id"], 2)  # -500 beats -1000
        self.assertAlmostEqual(result["raise"], -500.0)

    def test_tie_broken_by_lowest_id(self):
        jan = [make_emp(7, salary=5000), make_emp(3, salary=5000)]
        feb = [make_emp(7, salary=6000), make_emp(3, salary=6000)]
        result = biggest_raise(jan, feb)
        self.assertEqual(result["employee_id"], 3)  # equal +1000 raises


# ---------------------------------------------------------------------------
# Task 5 — nearest_salary
# ---------------------------------------------------------------------------

class TestNearestSalary(unittest.TestCase):
    def setUp(self):
        self.emps = [make_emp(i, salary=s) for i, s in
                     enumerate([3000, 6000, 9000, 12000], start=1)]

    def test_exact_match(self):
        r = nearest_salary(self.emps, 6000)
        self.assertAlmostEqual(r["salary"], 6000)
        self.assertAlmostEqual(r["delta"], 0)

    def test_between_two(self):
        r = nearest_salary(self.emps, 7000)
        self.assertAlmostEqual(r["salary"], 6000)

    def test_below_minimum(self):
        self.assertAlmostEqual(nearest_salary(self.emps, 1000)["salary"], 3000)

    def test_above_maximum(self):
        self.assertAlmostEqual(nearest_salary(self.emps, 20000)["salary"], 12000)

    def test_single_employee(self):
        self.assertAlmostEqual(nearest_salary([make_emp(1, salary=5000)], 9999)["salary"], 5000)

    def test_equidistant_tie_broken_by_lowest_id(self):
        emps = [make_emp(5, salary=4000), make_emp(3, salary=6000)]
        r = nearest_salary(emps, 5000)  # delta 1000 either way
        self.assertEqual(r["employee"].employee_id, 3)


class TestSalaryIndex(unittest.TestCase):
    def setUp(self):
        self.emps = [make_emp(i, salary=s) for i, s in
                     enumerate([3000, 6000, 9000, 12000], start=1)]
        self.idx = SalaryIndex(self.emps)

    def test_multiple_queries(self):
        self.assertAlmostEqual(self.idx.nearest(3500)["salary"], 3000)
        self.assertAlmostEqual(self.idx.nearest(10000)["salary"], 9000)
        self.assertAlmostEqual(self.idx.nearest(11500)["salary"], 12000)

    def test_matches_standalone_function(self):
        for target in (1000, 4500, 7500, 99999):
            self.assertEqual(self.idx.nearest(target)["salary"],
                             nearest_salary(self.emps, target)["salary"])


# ---------------------------------------------------------------------------
# Task 6 — most_similar
# ---------------------------------------------------------------------------

class TestMostSimilar(unittest.TestCase):
    def test_identical_except_id(self):
        emps = [
            make_emp(1, gender=1, job_role="A", experience_months=24, performance=2,
                     has_mgmt_responsibility=0, education="BS", salary=5000, bonus=0),
            make_emp(2, gender=1, job_role="A", experience_months=24, performance=2,
                     has_mgmt_responsibility=0, education="BS", salary=5000, bonus=0),
            make_emp(3, gender=2, job_role="B", experience_months=120, performance=0,
                     has_mgmt_responsibility=1, education="PhD", salary=15000, bonus=3000),
        ]
        self.assertEqual(most_similar(emps, 1)["employee"].employee_id, 2)

    def test_target_not_found_returns_none(self):
        self.assertIsNone(most_similar([make_emp(1), make_emp(2)], 99))

    def test_only_one_employee_returns_none(self):
        self.assertIsNone(most_similar([make_emp(1)], 1))

    def test_distance_is_nonnegative(self):
        emps = [make_emp(i, salary=1000 * i) for i in range(1, 6)]
        self.assertGreaterEqual(most_similar(emps, 1)["distance"], 0)

    def test_tie_broken_by_lowest_id(self):
        # Two candidates equidistant from the target -> lowest id wins.
        emps = [make_emp(1, salary=5000), make_emp(8, salary=4000), make_emp(4, salary=6000)]
        self.assertEqual(most_similar(emps, 1)["employee"].employee_id, 4)

    def test_gender_flag_changes_result(self):
        # Target male; one candidate female (lower id), one male (higher id),
        # otherwise identical.
        emps = [
            make_emp(1, gender=1),
            make_emp(2, gender=2),  # female, lower id
            make_emp(3, gender=1),  # male, higher id
        ]
        # Excluding gender: candidates tie -> lowest id (2) wins.
        self.assertEqual(most_similar(emps, 1, include_gender=False)["employee"].employee_id, 2)
        # Including gender: same-gender match (3) wins despite higher id.
        self.assertEqual(most_similar(emps, 1, include_gender=True)["employee"].employee_id, 3)

    def test_unknown_education_raises(self):
        emps = [make_emp(1, education="Trade School"), make_emp(2)]
        with self.assertRaises(ValueError):
            most_similar(emps, 1)


# ---------------------------------------------------------------------------
# Integration — smoke test against the real data files
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        jan_path = DATA_DIR / "january.json"
        feb_path = DATA_DIR / "february.json"
        if not jan_path.exists() or not feb_path.exists():
            raise unittest.SkipTest("Data files not found")
        cls.jan = load(str(jan_path))
        cls.feb = load(str(feb_path))

    def test_load_returns_employee_records(self):
        self.assertTrue(all(isinstance(e, Employee) for e in self.jan))

    def test_task1_roles_is_sorted_unique_strings(self):
        roles = all_job_roles(self.jan)
        self.assertTrue(all(isinstance(r, str) for r in roles))
        self.assertEqual(roles, sorted(set(roles)))

    def test_task2_helpers_roofers(self):
        avg = average_salary_for_role(self.jan, "Helpers--Roofers")
        self.assertIsNotNone(avg)
        self.assertGreater(avg, 0)

    def test_task3_changes_are_disjoint(self):
        changes = headcount_changes(self.jan, self.feb)
        left_ids   = {e.employee_id for e in changes["left"]}
        joined_ids = {e.employee_id for e in changes["joined"]}
        self.assertTrue(left_ids.isdisjoint(joined_ids))

    def test_task4_raise_employee_exists_in_both(self):
        result = biggest_raise(self.jan, self.feb)
        self.assertIsNotNone(result)
        self.assertIn(result["employee_id"], {e.employee_id for e in self.jan})
        self.assertIn(result["employee_id"], {e.employee_id for e in self.feb})

    def test_task5_nearest_salary_in_dataset(self):
        r = nearest_salary(self.jan, 8000)
        self.assertIn(r["salary"], [e.salary for e in self.jan])

    def test_task6_similar_is_different_employee(self):
        target_id = self.jan[0].employee_id
        result = most_similar(self.jan, target_id)
        self.assertIsNotNone(result)
        self.assertNotEqual(result["employee"].employee_id, target_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
