#!/usr/bin/env python3
"""Tests for the git-facing parts of bin/autocraft: generated-file markers and the install commit. Stdlib only; every test builds its own throw-away git repository. Run: python3 scripts/test_cli.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = str(ROOT / "bin" / "autocraft")
ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t", PYTHONDONTWRITEBYTECODE="1")
ALL_TOOLS = "claude-code,claude-app,cursor,copilot,gemini-cli,windsurf,cline,agents-md,prompts"


def sh(args, cwd, check=True):
    r = subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
    r.out, r.err = r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
    if check and r.returncode != 0:
        raise AssertionError(f"{args} failed ({r.returncode}): {r.out}{r.err}")
    return r


def git(cwd, *args, check=True):
    return sh(["git", *args], cwd, check)


def cli(cwd, *args, check=False):
    return sh([sys.executable, CLI, *args], cwd, check)


def lines(n, prefix="line"):
    return "".join(f"{prefix} {i}\n" for i in range(1, n + 1))


def write(root, rel, text):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")


def new_repo(base):
    Path(base).mkdir(parents=True, exist_ok=True)
    git(base, "init", "-q", "-b", "main")
    return base


class TempCase(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp(prefix="autocraft-test-")
        self.tmp = Path(self._td)
        self.addCleanup(shutil.rmtree, self._td, True)


# ---------------------------------------------------------------------------------------------- generated-file markers
class GitattributesTests(TempCase):
    def check_attr(self, repo, paths):
        r = git(repo, "check-attr", "linguist-generated", "--", *paths)
        out = {}
        for ln in r.out.splitlines():
            path, _, val = ln.rpartition(": linguist-generated: ")
            out[path] = val
        return out

    def test_fresh_init_marks_exactly_the_wholly_generated_files(self):
        repo = new_repo(self.tmp)
        r = cli(repo, "init", ".", "--tool", ALL_TOOLS, "--team", "starter")
        self.assertEqual(r.returncode, 0, r.err)
        manifest = json.loads((repo / ".autocraft" / "manifest.json").read_text())
        marked = self.check_attr(repo, sorted(manifest) + [".autocraft/framework/bin/autocraft", ".autocraft/templates/review/review-guide.md",
                                                           ".autocraft/manifest.json", ".autocraft/protocol.md"])
        self.assertTrue(manifest)
        self.assertEqual({k: v for k, v in marked.items() if v != "true"}, {})
        # files that merely CONTAIN a managed block, and user-owned files, are NOT generated
        unmarked = self.check_attr(repo, ["CLAUDE.md", "AGENTS.md", "GEMINI.md", ".github/copilot-instructions.md", ".autocraft/config.yml",
                                          ".autocraft/custom/README.md", ".autocraft/custom/team-rules.md", ".claude/settings.json",
                                          "docs/architecture/status.md"])
        self.assertEqual({k: v for k, v in unmarked.items() if v != "unspecified"}, {})
        text = (repo / ".gitattributes").read_text()
        self.assertIn("# autocraft:begin generated (managed block - do not edit between the markers)\n", text)
        self.assertTrue(text.rstrip().endswith("# autocraft:end"))
        # a user's own agent file in a shared directory is not swallowed by the markers
        self.assertEqual(self.check_attr(repo, [".github/agents/mine.agent.md", ".cursor/rules/mine.mdc"]),
                         {".github/agents/mine.agent.md": "unspecified", ".cursor/rules/mine.mdc": "unspecified"})

    def test_existing_gitattributes_is_preserved_and_second_run_changes_nothing(self):
        repo = new_repo(self.tmp)
        (repo / ".gitattributes").write_bytes(b"*.png binary\n*.sh text eol=lf")  # no trailing newline on purpose
        cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", check=True)
        first = (repo / ".gitattributes").read_bytes()
        self.assertTrue(first.startswith(b"*.png binary\n*.sh text eol=lf\n\n# autocraft:begin"))
        mtime = (repo / ".gitattributes").stat().st_mtime_ns
        cli(repo, "sync", ".", check=True)
        self.assertEqual((repo / ".gitattributes").read_bytes(), first)
        self.assertEqual((repo / ".gitattributes").stat().st_mtime_ns, mtime, "an unchanged .gitattributes must not be rewritten")
        # lines the user adds AFTER the block survive a sync, and a hand-edited block is repaired
        text = first.decode().replace("# autocraft:end", "# autocraft:end\n*.bin -diff") .replace(".claude/agents/** linguist-generated=true\n", "")
        (repo / ".gitattributes").write_text(text)
        cli(repo, "sync", ".", check=True)
        fixed = (repo / ".gitattributes").read_text()
        self.assertIn(".claude/agents/** linguist-generated=true", fixed)
        self.assertTrue(fixed.startswith("*.png binary\n*.sh text eol=lf\n"))
        self.assertTrue(fixed.rstrip().endswith("*.bin -diff"))

    def test_opt_out(self):
        repo = new_repo(self.tmp)
        r = cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", "--no-gitattributes")
        self.assertEqual(r.returncode, 0, r.err)
        self.assertFalse((repo / ".gitattributes").exists())
        cli(repo, "sync", ".", check=True)
        self.assertFalse((repo / ".gitattributes").exists(), "sync must respect the stored opt-out")
        d = cli(repo, "doctor", ".")
        self.assertEqual(d.returncode, 0)
        self.assertNotIn("gitattributes", d.out)

    def test_tool_removal_drops_stale_entries(self):
        repo = new_repo(self.tmp)
        cli(repo, "init", ".", "--tool", "claude-code,cursor,gemini-cli", "--team", "starter", check=True)
        before = (repo / ".gitattributes").read_text()
        self.assertIn(".cursor/rules/role-*.mdc", before)
        self.assertIn(".gemini/commands/", before)
        cli(repo, "remove-tool", "cursor", ".", check=True)
        cli(repo, "remove-tool", "gemini-cli", ".", check=True)
        after = (repo / ".gitattributes").read_text()
        self.assertNotIn(".cursor", after)
        self.assertNotIn(".gemini", after)
        self.assertNotIn(".autocraft/roles", after)
        self.assertIn(".claude/agents/**", after)
        self.assertEqual(cli(repo, "doctor", ".").returncode, 0)

    def test_doctor_warns_when_block_missing_or_stale(self):
        repo = new_repo(self.tmp)
        cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", check=True)
        ok = cli(repo, "doctor", ".")
        self.assertNotIn("warning", ok.out)
        (repo / ".gitattributes").unlink()
        d = cli(repo, "doctor", ".")
        self.assertIn("warning: no autocraft block in .gitattributes", d.out)
        self.assertEqual(d.returncode, 0, "a warning must not fail doctor")
        cli(repo, "sync", ".", check=True)
        (repo / ".gitattributes").write_text((repo / ".gitattributes").read_text().replace("# autocraft:end", ".old/** linguist-generated=true\n# autocraft:end"))
        d = cli(repo, "doctor", ".")
        self.assertIn("block is stale", d.out)
        cli(repo, "sync", ".", check=True)
        self.assertNotIn("warning", cli(repo, "doctor", ".").out)


# ---------------------------------------------------------------------------------------------- the install commit
class InstallCommitTests(TempCase):
    def owned_only(self, repo, rev="HEAD"):
        names = git(repo, "show", "--name-only", "--format=", rev).out.split("\n")
        return [n for n in names if n]

    def test_init_commit_in_repo_without_commits_leaves_user_changes_alone(self):
        repo = new_repo(self.tmp)
        write(repo, "s.txt", "staged by the user\n")
        git(repo, "add", "s.txt")
        write(repo, "wip.txt", "untracked\n")
        r = cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", "--commit")
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertEqual(git(repo, "rev-list", "--count", "HEAD").out.strip(), "1")
        self.assertEqual(git(repo, "log", "-1", "--format=%s").out.strip(), "chore(autocraft): install agent team (generated files)")
        files = self.owned_only(repo)
        self.assertIn(".autocraft/config.yml", files)
        self.assertIn(".gitattributes", files)
        self.assertIn("CLAUDE.md", files)
        self.assertIn(".autocraft/custom/team-rules.md", files)
        self.assertTrue(any(f.startswith(".claude/agents/") for f in files))
        self.assertNotIn("s.txt", files)
        self.assertNotIn("wip.txt", files)
        self.assertEqual(git(repo, "diff", "--cached", "--name-only").out.split(), ["s.txt"], "the user's staged file must stay staged")
        self.assertIn("?? wip.txt", git(repo, "status", "--short").out)
        self.assertNotIn("autocraft", git(repo, "status", "--short").out.replace("autocraft-test", ""), "everything of autocraft is committed")

    def test_commit_with_history_keeps_unstaged_and_staged_changes_exactly(self):
        repo = new_repo(self.tmp)
        write(repo, "app.py", "print(1)\n")
        write(repo, "notes.md", "n\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "first")
        write(repo, "app.py", "print(2)\n")  # unstaged edit
        write(repo, "notes.md", "n2\n")
        git(repo, "add", "notes.md")  # staged edit
        before = git(repo, "status", "--porcelain").out
        r = cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", "--commit")
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertEqual(git(repo, "rev-list", "--count", "HEAD").out.strip(), "2")
        self.assertEqual(set(self.owned_only(repo)) & {"app.py", "notes.md"}, set())
        after = [ln for ln in git(repo, "status", "--porcelain").out.splitlines()]
        self.assertEqual(after, before.splitlines())  # only the user's two entries remain, byte for byte
        self.assertEqual((repo / "app.py").read_text(), "print(2)\n")
        # a second sync with nothing new refuses with a clear message and exit code != 0
        r = cli(repo, "sync", ".", "--commit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nothing to commit", r.out + r.err)
        self.assertEqual(git(repo, "rev-list", "--count", "HEAD").out.strip(), "2")

    def test_sync_commit_message_and_scope(self):
        repo = new_repo(self.tmp)
        cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", "--commit", check=True)
        cli(repo, "add-role", "qa-engineer", ".", check=True)  # changes the generated files
        write(repo, ".autocraft/custom/team-rules.md", "my own rule\n")  # user-owned: must NOT be swept into the commit
        write(repo, "src.py", "x = 1\n")
        r = cli(repo, "sync", ".", "--commit")
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertEqual(git(repo, "log", "-1", "--format=%s").out.strip(), "chore(autocraft): sync agent team (generated files)")
        files = self.owned_only(repo)
        self.assertIn(".claude/agents/qa-engineer.md", files)
        self.assertNotIn("src.py", files)
        self.assertNotIn(".autocraft/custom/team-rules.md", files)

    def test_refuses_outside_a_git_work_tree_and_writes_nothing(self):
        r = cli(self.tmp, "init", "proj", "--tool", "claude-code", "--team", "starter", "--commit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("git work tree", r.out + r.err)
        self.assertFalse((self.tmp / "proj").exists(), "nothing may be created when --commit cannot work")

    def test_failing_hook_is_honoured_and_nothing_is_left_staged(self):
        repo = new_repo(self.tmp)
        write(repo, "keep.txt", "k\n")
        git(repo, "add", "keep.txt")
        hook = repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho HOOK-SAYS-NO >&2\nexit 1\n")
        hook.chmod(0o755)
        r = cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", "--commit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("HOOK-SAYS-NO", r.err + r.out, "git's own message must be shown")
        self.assertEqual(git(repo, "diff", "--cached", "--name-only").out.split(), ["keep.txt"], "autocraft must unstage what it staged")
        self.assertNotEqual(git(repo, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode, 0, "no commit may exist")
        self.assertTrue((repo / ".autocraft" / "config.yml").exists(), "the files stay on disk")

    def test_user_edited_gitattributes_is_not_committed_for_them(self):
        repo = new_repo(self.tmp)
        write(repo, ".gitattributes", "*.png binary\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "base")
        write(repo, ".gitattributes", "*.png binary\n*.jpg binary\n")  # uncommitted user edit outside the block
        r = cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", "--commit")
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertNotIn(".gitattributes", self.owned_only(repo))
        self.assertIn("left .gitattributes out of the commit", r.out)
        self.assertIn(" M .gitattributes", git(repo, "status", "--short").out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
