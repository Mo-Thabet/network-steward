import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReproducibleDemoSmokeTests(unittest.TestCase):
    def test_documented_demo_command_runs_and_emits_verifiable_result(self):
        completed = subprocess.run(
            [sys.executable, "-B", "examples/reproducible_demo.py"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Synthetic Cisco-style fixture data; not captured from IOS or a simulator.", completed.stdout)
        self.assertIn("Input fixture: fixtures/NS-01/ns_01_pos_01.json", completed.stdout)
        self.assertIn("Result: NS-01 supported", completed.stdout)
        self.assertIn("Abstain: no", completed.stdout)
        self.assertIn("Evidence citation: capture 0 line 2:", completed.stdout)
        self.assertIn("Why this supports the candidate:", completed.stdout)
        self.assertIn("Suggested read-only next check (not executed): show interfaces GigabitEthernet1/0/12", completed.stdout)
        self.assertIn("does not establish the current state", completed.stdout)
        self.assertIn("all report citations point to exact lines in the input fixture", completed.stdout)


if __name__ == "__main__":
    unittest.main()

