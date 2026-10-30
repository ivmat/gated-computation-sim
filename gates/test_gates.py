#!/usr/bin/env python3
"""Exercise the real shell gates in disposable repositories; never push refs."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ZERO = "0" * 40


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="gcs-gate-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        PYTHONPYCACHEPREFIX=str(Path(self.tmp.name) / "pycache"))
        self.git("init", "-q")
        self.git("config", "user.name", "Gate test")
        self.git("config", "user.email", "gate-test@example.invalid")
        (self.root / "gates").mkdir()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root,
                                       env=self.env, text=True).strip()

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "Gate fixture")
        return self.git("rev-parse", "HEAD")

    def numerical_fixture(self):
        shutil.copyfile(ROOT / "gates/check.sh", self.root / "gates/check.sh")
        for name in ("fault_process", "risk_mechanization", "allocation"):
            (self.root / f"simulate_{name}.py").write_text(
                "import sys\n"
                "if '--negative-control' in sys.argv:\n"
                "    print('REJECTED false ' + sys.argv[-1] + ' claim')\n"
                "    raise SystemExit(1)\n")
        self.git("add", "-A")

    def check(self):
        return subprocess.run(["sh", "gates/check.sh"], cwd=self.root,
                              env=self.env, capture_output=True, text=True, timeout=30)

    def test_numerical_success_and_intended_negative_rejections(self):
        self.numerical_fixture()
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("PASS negative control:"), 11)

    def test_failed_positive_check_blocks_gate(self):
        self.numerical_fixture()
        with (self.root / "simulate_fault_process.py").open("a") as f:
            f.write("raise SystemExit(1)\n")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NUMERICAL CHECK FAILED: simulate_fault_process.py", result.stdout)

    def test_false_green_crash_and_argument_error_are_not_negative_evidence(self):
        for rc, message in [(0, "expected"), (1, "Traceback: broken check"), (2, "expected"),
                            (1, "expected_then_traceback"), (1, "expected_then_extra_output")]:
            with self.subTest(rc=rc, message=message):
                self.numerical_fixture()
                text = ("import sys\nif '--negative-control' in sys.argv:\n"
                        "    print('REJECTED false ' + sys.argv[-1] + ' claim')\n"
                        f"    raise SystemExit({rc})\n")
                if message.startswith("expected_then_"):
                    extra = "Traceback: check crashed after rejection" if message.endswith("traceback") else "unexpected extra output"
                    text = text.replace(f"    raise SystemExit({rc})", f"    print({extra!r})\n    raise SystemExit({rc})")
                elif message != "expected":
                    text = text.replace("'REJECTED false ' + sys.argv[-1] + ' claim'", repr(message))
                (self.root / "simulate_fault_process.py").write_text(text)
                result = self.check()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NEGATIVE CONTROL FAILED", result.stdout)

    def test_missing_required_script_blocks_gate(self):
        self.numerical_fixture()
        (self.root / "simulate_fault_process.py").unlink()
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NUMERICAL CHECK FAILED", result.stdout)

    def hook_fixture(self):
        self.calls = Path(self.tmp.name) / "calls"
        self.env["GCS_TEST_CALLS"] = str(self.calls)
        (self.root / "gates/check.sh").write_text(
            '#!/bin/sh\ncd "$1"\ngit rev-parse HEAD >> "$GCS_TEST_CALLS"\n'
            'exit "$(cat gate-status)"\n')
        (self.root / "gate-status").write_text("0\n")
        return self.commit()

    def hook(self, refs, direct=False):
        args = ["sh", str(ROOT / "gates/pre-push")]
        if not direct:
            args += ["origin", "https://example.invalid/repo.git"]
        return subprocess.run(args, cwd=self.root, env=self.env, input=refs,
                              capture_output=True, text=True, timeout=30)

    def ref(self, name, sha):
        return f"refs/heads/{name} {sha} refs/heads/{name} {ZERO}\n"

    def recorded(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def test_branch_and_annotated_tag_share_one_check_but_later_push_reruns(self):
        sha = self.hook_fixture()
        self.git("tag", "-a", "v-test", "-m", "Gate tag fixture")
        tag = self.git("rev-parse", "refs/tags/v-test")
        refs = self.ref("main", sha) + f"refs/tags/v-test {tag} refs/tags/v-test {ZERO}\n"
        result = self.hook(refs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [sha])
        self.assertIn("already checked", result.stdout)
        self.assertEqual(self.hook(refs).returncode, 0)
        self.assertEqual(self.recorded(), [sha, sha])

    def test_distinct_commits_and_repeated_failure(self):
        green = self.hook_fixture()
        (self.root / "gate-status").write_text("1\n")
        red = self.commit()
        result = self.hook(self.ref("a", green) + self.ref("b", red) + self.ref("c", red))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.recorded(), [green, red])
        self.assertIn("FAILED (already checked)", result.stderr)

    def test_deleted_refs_do_not_run_checks(self):
        self.hook_fixture()
        self.assertEqual(self.hook(self.ref("deleted", ZERO)).returncode, 0)
        self.assertEqual(self.recorded(), [])

    def test_missing_commit_and_noncommit_tag_are_refused(self):
        self.hook_fixture()
        blob = self.git("hash-object", "gate-status")
        for sha in ["f" * 40, blob]:
            with self.subTest(sha=sha):
                self.assertNotEqual(self.hook(self.ref("bad", sha)).returncode, 0)
        self.assertEqual(self.recorded(), [])

    def test_chained_hook_receives_original_ref_input_and_failure_propagates(self):
        sha = self.hook_fixture()
        capture = Path(self.tmp.name) / "guard-input"
        self.env["GCS_TEST_GUARD"] = str(capture)
        guard = self.root / ".git/hooks/pre-push.pre-guard"
        guard.write_text('#!/bin/sh\ncat > "$GCS_TEST_GUARD"\nexit 1\n')
        guard.chmod(0o755)
        refs = self.ref("a", sha) + self.ref("b", sha)
        self.assertNotEqual(self.hook(refs).returncode, 0)
        self.assertEqual(capture.read_text(), refs)
        self.assertEqual(self.recorded(), [sha])

    def test_direct_invocation_checks_head(self):
        sha = self.hook_fixture()
        self.assertEqual(self.hook("", direct=True).returncode, 0)
        self.assertEqual(self.recorded(), [sha])


if __name__ == "__main__":
    unittest.main()
