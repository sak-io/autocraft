#!/usr/bin/env python3
"""Tests for the git-facing parts of bin/autocraft: generated-file markers, the install commit, review-map (+ slices, split script,
verify-guide) and the review-guide config. Stdlib only; every test builds its own throw-away git repository. Run: python3 scripts/test_cli.py"""
import json
import os
import re
import runpy
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

    def test_conflicting_user_rule_is_reported_with_the_winner(self):
        repo = new_repo(self.tmp)
        (repo / ".gitattributes").write_text(".claude/agents/** -linguist-generated\n*.png binary\n")
        r = cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter")
        self.assertEqual(r.returncode, 0, r.err)
        self.assertIn("conflicts with autocraft's entry '.claude/agents/**'", r.out)
        self.assertIn("autocraft's block wins", r.out)
        d = cli(repo, "doctor", ".")
        self.assertIn("warning: .gitattributes line 1", d.out)
        self.assertEqual(d.returncode, 0)
        # the user's rule AFTER the block wins instead, and the warning says so
        text = (repo / ".gitattributes").read_text().replace(".claude/agents/** -linguist-generated\n", "")
        (repo / ".gitattributes").write_text(text + "linguist-generated=false\n".replace("linguist", ".claude/skills/** linguist", 1))
        r = cli(repo, "sync", ".")
        self.assertIn("your rule wins", r.out)
        clean = new_repo(self.tmp / "other")
        r = cli(clean, "init", ".", "--tool", "claude-code", "--team", "starter")
        self.assertNotIn("conflicts", r.out)

    def test_doctor_rejects_bad_review_settings(self):
        repo = new_repo(self.tmp)
        cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", check=True)
        cfg = repo / ".autocraft" / "config.yml"
        for bad, msg in (("review_guide: sometimes", "review_guide"), ("human_review: maybe", "human_review"),
                         ("review_guide_min_files: many", "review_guide_min_files")):
            key = bad.split(":")[0]
            original = cfg.read_text()
            cfg.write_text(re.sub(rf"^{key}:.*$", bad, original, flags=re.M))
            d = cli(repo, "doctor", ".")
            self.assertEqual(d.returncode, 1, bad)
            self.assertIn("PROBLEM", d.out)
            self.assertIn(msg, d.out)
            cfg.write_text(original)
        self.assertIn("human_review: optional", cfg.read_text())
        self.assertIn("review_guide_min_product_lines: 1500", cfg.read_text())


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
        self.assertEqual(r.returncode, 0, "re-running on an up-to-date repository is not an error")
        self.assertIn("nothing to commit", r.out + r.err)
        self.assertEqual(git(repo, "rev-list", "--count", "HEAD").out.strip(), "2")
        r = cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", "--commit")
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertIn("nothing to commit", r.out)

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

    def test_rewriting_pre_commit_hook(self):
        repo = new_repo(self.tmp)
        write(repo, "base.txt", "b\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "base")
        write(repo, "s.txt", "staged by the user\n")
        git(repo, "add", "s.txt")
        write(repo, "wip.txt", "mine\n")
        hook = repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\n# a formatter: rewrites an autocraft file and re-adds it\necho '' >> CLAUDE.md\ngit add CLAUDE.md\n")
        hook.chmod(0o755)
        r = cli(repo, "init", ".", "--tool", "claude-code", "--team", "starter", "--commit")
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertEqual(git(repo, "rev-list", "--count", "HEAD").out.strip(), "2")
        self.assertEqual(git(repo, "diff", "--cached", "--name-only").out.split(), ["s.txt"], "only the user's own staged file may remain staged")
        self.assertNotIn("s.txt", self.owned_only(repo))
        self.assertEqual((repo / "wip.txt").read_text(), "mine\n")
        left = git(repo, "status", "--short", "--", ".autocraft", ".claude", "CLAUDE.md", ".gitattributes").out
        self.assertEqual(left.strip(), "", "the hook's rewrite of an owned file is part of the commit, not left behind")

    def test_linked_worktree_and_detached_head(self):
        repo = new_repo(self.tmp / "main")
        write(repo, "a.txt", "a\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "first")
        wt = self.tmp / "wt"
        git(repo, "worktree", "add", "-q", "-b", "wtb", str(wt))
        r = cli(wt, "init", ".", "--tool", "claude-code", "--team", "starter", "--commit")
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertIn("on branch wtb", r.out)
        self.assertEqual(git(repo, "rev-list", "--count", "main").out.strip(), "1", "the other work tree's branch is untouched")
        self.assertEqual(git(repo, "rev-list", "--count", "wtb").out.strip(), "2")
        self.assertFalse((repo / ".autocraft").exists())
        git(wt, "checkout", "-q", "--detach")
        cli(wt, "add-role", "qa-engineer", ".", check=True)
        r = cli(wt, "sync", ".", "--commit")
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertIn("detached HEAD", r.out)

    def test_submodule_and_subdirectory_projects(self):
        sub = new_repo(self.tmp / "subsrc")
        write(sub, "lib.txt", "x\n")
        git(sub, "add", "-A")
        git(sub, "commit", "-q", "-m", "sub first")
        parent = new_repo(self.tmp / "parent")
        write(parent, "p.txt", "p\n")
        git(parent, "add", "-A")
        git(parent, "commit", "-q", "-m", "parent first")
        git(parent, "-c", "protocol.file.allow=always", "submodule", "add", "-q", "file://" + str(sub), "libs")
        git(parent, "commit", "-q", "-m", "add submodule")
        git(parent / "libs", "config", "user.email", "t@t")
        git(parent / "libs", "config", "user.name", "t")
        r = cli(parent, "init", "libs", "--tool", "claude-code", "--team", "starter", "--commit")  # DIR is the submodule's root
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertEqual(git(parent / "libs", "rev-list", "--count", "HEAD").out.strip(), "2")
        self.assertEqual(git(parent, "rev-list", "--count", "HEAD").out.strip(), "2", "the superproject gets no commit")
        self.assertIn("libs", git(parent, "status", "--short").out)  # it only sees the submodule moved
        # a project in a plain sub-directory: paths are relative to it, nothing outside it is touched
        r = cli(parent, "init", "apps/web", "--tool", "claude-code", "--team", "starter", "--commit")
        self.assertEqual(r.returncode, 0, r.out + r.err)
        files = self.owned_only(parent)
        self.assertTrue(files and all(f.startswith("apps/web/") for f in files), files)

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


# ---------------------------------------------------------------------------------------------- review-map
FEATURE_FILES = {  # path -> added lines in the feature commit (see expected totals in the tests)
    "src/alpha.py": 50, "src/beta.py": 30, "src/gamma.py": 40, "scripts/run": 5, "src/café util.py": 7,
    "tests/test_alpha.py": 20, "tests/test_beta.py": 10, "tests/test_misc.py": 15,
    "docs/guide.md": 8, "pyproject.toml": 6, ".github/workflows/ci.yml": 4, "requirements.txt": 2,
    "package-lock.json": 30, "dist/bundle.min.js": 7, "gen/out.py": 12, "vendor/x.py": 5,
}


def build_review_repo(base):
    """main: core.py, README, old_name.py(20), dead.py(6), two files called dup.py;  feature: see FEATURE_FILES + binary + rename + delete"""
    repo = new_repo(base)
    write(repo, "src/core.py", lines(10))
    write(repo, "README.md", "a\nb\nc\n")
    write(repo, "src/old_name.py", lines(20))
    write(repo, "src/dead.py", lines(6))
    write(repo, "pkg1/dup.py", "x = 1\n")
    write(repo, "pkg2/dup.py", "x = 2\n")
    write(repo, "vendor/lib/deleted.py", lines(8))  # exists only under vendor/: a guide citing lib/deleted.py must NOT resolve to it
    write(repo, "src/test_helpers/h.py", "def helper_h():\n    pass\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "checkout", "-q", "-b", "feature")
    for rel, n in FEATURE_FILES.items():
        write(repo, rel, lines(n, rel))  # distinct contents, or git would pair them with the deleted files as renames
    write(repo, "src/alpha.py", "".join(["x = 1\n", "y = 2\n", "def helper(x):\n", "class Alpha:\n", "LIMIT = 3\n"]) + lines(45))
    write(repo, "src/beta.py", lines(28) + "# TODO frobnicate\nnote = \"def string_sym\"\n")
    write(repo, "tests/test_misc.py", "import gamma\n" + "gamma.run()\n" + lines(13))  # mentions 'gamma' twice: pairs with src/gamma.py
    write(repo, ".gitattributes", "gen/** linguist-generated=true\n")
    write(repo, "assets/logo.png", b"\x89PNG\0\0\0binary\xff\xfe" * 20)
    write(repo, "README.md", "a\nb\nX\nY\n")  # +2 -1
    git(repo, "mv", "src/old_name.py", "src/renamed.py")
    text = lines(20).replace("line 5\n", "line five\n")
    write(repo, "src/renamed.py", text)
    git(repo, "rm", "-q", "src/dead.py")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "feature")
    return repo


class RepoBase(TempCase):
    @classmethod
    def setUpClass(cls):
        cls._shared = tempfile.mkdtemp(prefix="autocraft-rm-")
        cls.repo = build_review_repo(Path(cls._shared) / "repo with spaces ünï")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._shared, True)

    def rm(self, *args, repo=None):
        return cli(repo or self.repo, "review-map", *args)

    def with_config(self, text, *args, as_json=True):
        """run review-map with a (temporary, untracked) .autocraft/config.yml in the shared repo"""
        cfg = self.repo / ".autocraft" / "config.yml"
        write(self.repo, ".autocraft/config.yml", "default_branch: main\n" + text)
        try:
            r = self.rm(*(("--json",) if as_json else ()), *args)
        finally:
            shutil.rmtree(self.repo / ".autocraft")
        return json.loads(r.out) if as_json and r.returncode == 0 else r

    def data(self, *args):
        r = self.rm("--json", *args)
        self.assertEqual(r.returncode, 0, r.err)
        return json.loads(r.out)

    # --- slices and the split script
    # --- verify-guide
    def guide(self, text):
        p = self.tmp / "guide.md"
        p.write_text(text, encoding="utf-8")
        return str(p)

    # --- verify-guide strictness (review round 1)
    def vg(self, text, *args):
        r = self.rm("--verify-guide", self.guide(text), "--json", *args)
        self.assertIn(r.returncode, (0, 1), r.err)
        d = json.loads(r.out)
        return r.returncode, {x["ref"]: x for x in d["references"]}, d["summary"]


class ReviewMapTests(RepoBase):
    def test_exact_counts_per_class_and_json_shape(self):
        d = self.data()
        c = d["classes"]
        self.assertEqual({k: (v["files"], v["added"], v["deleted"]) for k, v in c.items()}, {
            "generated": (4, 54, 0), "tests": (3, 45, 0), "docs": (2, 10, 1), "ci_config": (4, 13, 0),
            "product": (7, 133, 7), "other": (1, 0, 0)})
        self.assertEqual(d["totals"], {"files": 21, "added": 255, "deleted": 8})
        for key in ("base", "head", "merge_base", "classes", "product_top", "files", "summary", "warnings", "guide_recommended",
                    "guide_reason", "split_recommended", "split_reason", "thresholds"):
            self.assertIn(key, d)
        self.assertEqual(d["classes"]["product"]["pct_files"], round(100 * 7 / 21, 1))
        self.assertEqual(d["product_top"][0], {"path": "src/alpha.py", "added": 50, "deleted": 0})
        self.assertTrue(d["summary"].startswith("21 files / 255 added: 7 product files (133 lines)"), d["summary"])
        by_path = {f["path"]: f for f in d["files"]}
        ren = by_path["src/renamed.py"]
        self.assertEqual((ren["old_path"], ren["status"], ren["added"], ren["deleted"], ren["class"]), ("src/old_name.py", "R", 1, 1, "product"))
        self.assertEqual(by_path["assets/logo.png"]["binary"], True)
        self.assertEqual(by_path["assets/logo.png"]["class"], "other")
        self.assertEqual(by_path["src/dead.py"]["status"], "D")
        self.assertEqual(by_path["src/café util.py"]["class"], "product")  # unicode and spaces survive
        self.assertEqual(by_path["gen/out.py"]["class"], "generated")  # via the repository's own linguist-generated entry
        self.assertEqual(by_path["scripts/run"]["class"], "product")  # extension-less script
        self.assertEqual(by_path["requirements.txt"]["class"], "ci_config")
        self.assertEqual(by_path["tests/test_misc.py"]["class"], "tests")

    def test_text_output_has_table_summary_top_list_and_generated_warning(self):
        r = self.rm("--top", "2")
        self.assertEqual(r.returncode, 0, r.err)
        self.assertIn("generated", r.out)
        self.assertRegex(r.out, r"product\s+7\s+133\s+7")
        self.assertIn("top 2 of 7", r.out)
        self.assertIn("21 files / 255 added: 7 product files (133 lines)", r.out)
        self.assertNotIn("% of changed files", r.out)  # 4/21 generated is under the 30% warning threshold
        out = self.rm("--json", "--base", "main").out
        self.assertEqual(json.loads(out)["warnings"], [])

    def test_generated_share_warning_and_extra_globs(self):
        if True:
            d = self.with_config("review_map_extra_generated: [src/**]\nreview_map_extra_tests: [scripts/**]\n")
            self.assertEqual(d["classes"]["generated"]["files"], 4 + 6)  # + alpha, beta, gamma, café util, renamed, dead.py (all under src/)
            self.assertEqual(d["classes"]["tests"]["files"], 4)  # + scripts/run
            self.assertEqual(d["classes"]["product"]["files"], 0)
            self.assertEqual(len(d["warnings"]), 1)  # 10 of 21 files are generated: over the 30% line
            self.assertIn("are generated", d["warnings"][0])
            r = self.with_config("review_map_extra_generated: [src/**]\n", as_json=False)
            self.assertIn("warning: 10 of 21 changed files", r.out)

    def test_empty_diff_and_errors(self):
        r = self.rm("--head", "main")
        self.assertEqual(r.returncode, 0)
        self.assertIn("no changes", r.out)
        d = json.loads(self.rm("--head", "main", "--json").out)
        self.assertEqual(d["totals"], {"files": 0, "added": 0, "deleted": 0})
        self.assertEqual(d["files"], [])
        r = self.rm("--base", "no-such-ref")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no-such-ref", r.err)
        self.assertEqual(self.rm("--head", "nope").returncode, 2)
        with tempfile.TemporaryDirectory() as td:
            r = cli(td, "review-map")
            self.assertEqual(r.returncode, 2)
            self.assertIn("not inside a git work tree", r.err)
            repo = new_repo(Path(td) / "trunk")  # no main / origin/main and no commits
            write(repo, "a.py", "1\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "x")
            git(repo, "branch", "-m", "trunk")
            r = cli(repo, "review-map")
            self.assertEqual(r.returncode, 2)
            self.assertIn("neither origin/main nor main", r.err)
            self.assertEqual(cli(repo, "review-map", "--base", "HEAD").returncode, 0)

    def test_dir_argument_works_from_anywhere(self):
        r = cli(self.repo.parent, "review-map", str(self.repo), "--json")
        self.assertEqual(r.returncode, 0, r.err)
        self.assertEqual(json.loads(r.out)["totals"]["files"], 21)

    def test_shallow_clone_gives_clear_message(self):
        with tempfile.TemporaryDirectory() as td:
            clone = Path(td) / "shallow"
            git(td, "clone", "-q", "--depth", "1", "--no-single-branch", "file://" + str(self.repo), str(clone))
            git(clone, "checkout", "-q", "feature")
            r = cli(clone, "review-map")
            self.assertEqual(r.returncode, 2, r.out + r.err)
            self.assertIn("shallow", r.err)
            self.assertIn("--unshallow", r.err)

    def test_guide_recommendation_follows_config(self):
        with_cfg = self.with_config

        d = with_cfg("")
        self.assertFalse(d["guide_recommended"])
        self.assertIn("below the thresholds", d["guide_reason"])
        self.assertFalse(d["split_recommended"])
        d = with_cfg("review_guide: always\n")
        self.assertEqual((d["guide_recommended"], d["guide_reason"]), (True, "review_guide=always"))
        d = with_cfg("review_guide: never\nreview_guide_min_files: 1\nhuman_review: required\n")
        self.assertEqual((d["guide_recommended"], d["guide_reason"]), (False, "review_guide=never"))
        d = with_cfg("review_guide_min_files: 20\n")
        self.assertTrue(d["guide_recommended"])
        self.assertIn("21 files changed > review_guide_min_files (20)", d["guide_reason"])
        self.assertFalse(d["split_recommended"])
        d = with_cfg("review_guide_min_files: 10\n")
        self.assertTrue(d["split_recommended"])  # 21 > 2 x 10
        d = with_cfg("review_guide_min_product_lines: 100\n")
        self.assertTrue(d["guide_recommended"])
        self.assertIn("133 product lines added > review_guide_min_product_lines (100)", d["guide_reason"])
        d = with_cfg("human_review: required\n")
        self.assertEqual((d["guide_recommended"], d["guide_reason"]), (True, "human_review=required"))
        r = self.with_config("review_guide: sometimes\n", as_json=False)
        self.assertEqual(r.returncode, 2)
        self.assertIn("review_guide", r.err)

    def test_slices_respect_target_and_keep_tests_with_their_module(self):
        d = self.data("--slices", "--target-lines", "100")
        s = d["slices"]
        self.assertEqual(s["bootstrap"]["files"], 4)
        self.assertEqual(s["bootstrap"]["added"], 54)
        seen = []
        for sl in s["slices"]:
            self.assertLessEqual(sl["added"], 100, sl)
            self.assertFalse(sl["oversize"])
            seen += sl["paths"]
        seen += s["bootstrap"]["paths"]
        self.assertEqual(sorted(seen), sorted(f["path"] for f in d["files"]), "every changed file lands in exactly one slice")
        from collections import Counter
        self.assertEqual(set(Counter(seen).values()), {1}, "no file appears in two slices")
        non_generated = [f["path"] for f in d["files"] if f["class"] != "generated"]
        in_slices = [p for sl in s["slices"] for p in sl["paths"]]
        self.assertEqual(sorted(in_slices), sorted(non_generated), "each non-generated file is in exactly one (non-bootstrap) slice")
        where = {p: sl["n"] for sl in s["slices"] for p in sl["paths"]}
        self.assertEqual(where["tests/test_alpha.py"], where["src/alpha.py"])
        self.assertEqual(where["tests/test_beta.py"], where["src/beta.py"])
        self.assertEqual(where["tests/test_misc.py"], where["src/gamma.py"], "a test with no same-stem file goes with the module it mentions")
        self.assertGreaterEqual(len(s["slices"]), 3)
        last = s["slices"][-1]["paths"]
        self.assertIn("docs/guide.md", last)  # docs/config leftovers go last
        self.assertIn("requirements.txt", last)
        text = self.rm("--slices", "--target-lines", "100").out
        self.assertIn("PROPOSED SPLIT", text)
        self.assertIn("NOT dependency-aware", text)
        self.assertIn("bootstrap (generated)", text)
        big = self.data("--slices", "--target-lines", "100000")["slices"]["slices"]
        self.assertEqual(len(big), 1)
        tiny = self.data("--slices", "--target-lines", "10")["slices"]["slices"]
        self.assertTrue(any(sl["oversize"] for sl in tiny), "an indivisible module+tests group bigger than the target is flagged")

    def test_split_script_mentions_every_non_generated_file_once_and_reproduces_head(self):
        d = self.data()
        r = self.rm("--emit-split-script", "--target-lines", "100")
        self.assertEqual(r.returncode, 0, r.err)
        script = r.out
        self.assertIn("NEVER RUN", script)
        import shlex
        checked, removed = [], []
        mode = None
        for ln in script.splitlines():
            if ln.startswith("git checkout \"$HEAD\" --"):
                mode = checked
            elif ln.startswith("git rm "):
                mode = removed
            elif ln.startswith("  ") and mode is not None:
                mode.append(shlex.split(ln.strip().rstrip("\\"))[0])
                if not ln.rstrip().endswith("\\"):
                    mode = None
            else:
                mode = None
        non_generated = [f for f in d["files"] if f["class"] != "generated" and f["status"] != "D"]
        self.assertEqual(sorted(p for p in checked if not p.startswith(("dist/", "vendor/", "gen/", "package-lock"))), sorted(f["path"] for f in non_generated))
        self.assertEqual(sorted(removed), ["src/dead.py", "src/old_name.py"])
        for f in d["files"]:
            if f["status"] != "D":
                self.assertEqual(checked.count(f["path"]), 1, f["path"])  # every file (generated ones in the bootstrap branch) exactly once
        self.assertIn("slice-0-bootstrap", script)
        self.assertIn("# git push -u origin", script)
        # running it in a COPY rebuilds exactly head, branch by branch
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "copy"
            shutil.copytree(self.repo, repo)
            (Path(td) / "split.sh").write_text(script)
            res = sh(["bash", str(Path(td) / "split.sh")], repo)
            self.assertEqual(res.out.strip(), "", res.out + res.err)
            branches = git(repo, "branch", "--format=%(refname:short)").out.split()
            n = len(self.data("--slices", "--target-lines", "100")["slices"]["slices"])
            self.assertIn(f"slice-{n}", branches)
            self.assertEqual(git(repo, "diff", "--stat", f"slice-{n}", "feature").out.strip(), "")
            self.assertEqual(git(repo, "merge-base", "--is-ancestor", "slice-0-bootstrap", "slice-1", check=False).returncode, 0)

    def test_test_directories_count_as_tests(self):
        mod = runpy.run_path(CLI, run_name="x")
        rules = {"manifest": set(), "generated": [], "tests": list(mod["RM_TESTS"])}
        cls = lambda path: mod["rm_class"](path, False, rules)
        for path in ("src/test_helpers/h.py", "testing/util.py", "fixtures/a.json", "app/testdata/x.csv", "web/__fixtures__/m.js", "test_utils.py"):
            self.assertEqual(cls(path), "tests", path)
        self.assertEqual(cls("data/sample.json"), "ci_config")  # documented: JSON fixtures outside test dirs stay config
        self.assertEqual(cls("src/contest.py"), "product")

    def test_output_piped_to_a_closed_reader_is_quiet(self):
        rfd, wfd = os.pipe()
        os.close(rfd)  # the reader (think `| head`) is already gone
        r = subprocess.run([sys.executable, CLI, "review-map", str(self.repo), "--json"], stdout=wfd, stderr=subprocess.PIPE, env=ENV)
        os.close(wfd)
        self.assertEqual(r.stderr.decode(), "")

    def test_shallow_base_not_a_commit_gets_the_deepen_hint(self):
        with tempfile.TemporaryDirectory() as td:
            clone = Path(td) / "shallow"
            git(td, "clone", "-q", "--depth", "1", "--no-single-branch", "file://" + str(self.repo), str(clone))
            git(clone, "checkout", "-q", "feature")
            r = cli(clone, "review-map", "--base", "HEAD~3")
            self.assertEqual(r.returncode, 2)
            self.assertIn("shallow", r.err)
            self.assertIn("--unshallow", r.err)
            r = cli(self.repo, "review-map", "--base", "HEAD~30")  # not shallow: no hint, still a clear error
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("shallow", r.err)

    def test_review_map_never_writes_to_the_repository(self):
        before = git(self.repo, "status", "--porcelain", "--ignored").out
        mtimes = sorted((p.name, p.stat().st_mtime_ns) for p in (self.repo / ".git").iterdir() if p.is_file())
        self.rm("--slices")
        self.rm("--emit-split-script")
        self.rm("--verify-guide", self.guide("src/alpha.py:1\n"))
        self.assertEqual(git(self.repo, "status", "--porcelain", "--ignored").out, before)
        self.assertEqual(sorted((p.name, p.stat().st_mtime_ns) for p in (self.repo / ".git").iterdir() if p.is_file()), mtimes)


class VerifyGuideTests(RepoBase):
    def test_verify_guide_good(self):
        g = self.guide("""# Guide
Entry points: `src/alpha.py`, src/alpha.py:10 and src/alpha.py:5-20 (the helper is src/alpha.py:helper).

| Property | Enforced in |
| - | - |
| P1 | `Alpha` (src/alpha.py:Alpha), LIMIT in src/alpha.py:LIMIT and gamma.py:12 |
| P2 | beta.py (unique bare name) |

```
this is a fenced block: nope/missing.py:999 and src/alpha.py:nonexistent_symbol are ignored
```
~~~
tilde fence src/also_missing.py:1
~~~
Times like 12:30 and example.com:443 are not references.
""")
        r = self.rm("--verify-guide", g)
        self.assertEqual(r.returncode, 0, r.out + r.err)
        self.assertIn("0 STALE", r.out)
        self.assertIn("src/gamma.py", r.out)  # unique suffix match resolved
        self.assertIn("ok (resolved by suffix -> src/gamma.py)", r.out)
        self.assertIn("checked ", r.out)
        d = json.loads(self.rm("--verify-guide", g, "--json").out)
        st = {x["ref"]: x for x in d["references"]}
        self.assertEqual(st["src/alpha.py:helper"]["detail"], "defined")
        self.assertEqual(st["src/alpha.py:Alpha"]["status"], "ok")
        self.assertEqual(st["src/alpha.py:LIMIT"]["status"], "ok")
        self.assertEqual(st["gamma.py:12"]["status"], "ok (resolved by suffix -> src/gamma.py)")
        self.assertEqual(d["summary"]["stale"], 0)
        self.assertNotIn("nope/missing.py:999", st)
        self.assertNotIn("src/also_missing.py:1", st)

    def test_verify_guide_flags_stale_references(self):
        g = self.guide("""See src/missing.py:3 and src/alpha.py:51 and src/alpha.py:nonexistent_symbol and `docs/gone.md`.
Also `src/alpha.py` (fine) and src/alpha.py:40-60 (range ends past line 50) and src/alpha.py:Helper (wrong case) and dup.py:1.
""")
        r = self.rm("--verify-guide", g)
        self.assertEqual(r.returncode, 1, r.out)
        d = json.loads(self.rm("--verify-guide", g, "--json").out)
        by = {x["ref"]: x for x in d["references"]}
        self.assertEqual(by["src/missing.py:3"]["status"], "STALE")
        self.assertIn("not found", by["src/missing.py:3"]["detail"])
        self.assertEqual(by["src/alpha.py:51"]["status"], "STALE")
        self.assertIn("50 lines", by["src/alpha.py:51"]["detail"])
        self.assertEqual(by["src/alpha.py:nonexistent_symbol"]["status"], "STALE")
        self.assertEqual(by["docs/gone.md"]["status"], "STALE")
        self.assertEqual(by["src/alpha.py"]["status"], "ok")
        self.assertEqual(by["src/alpha.py:40-60"]["status"], "STALE")
        self.assertEqual(by["src/alpha.py:Helper"]["status"], "STALE")  # symbol match is case-sensitive
        self.assertEqual(by["dup.py:1"]["status"], "AMBIGUOUS")  # pkg1/dup.py and pkg2/dup.py
        self.assertIn("pkg1/dup.py", by["dup.py:1"]["detail"])
        self.assertEqual(d["summary"]["stale"], 6)
        self.assertEqual(d["summary"]["ambiguous"], 1)

    def test_verify_guide_ambiguous_fails_and_missing_guide_is_usage_error(self):
        g = self.guide("Look at dup.py:1 please.\n")
        r = self.rm("--verify-guide", g)
        self.assertEqual(r.returncode, 1)
        self.assertIn("AMBIGUOUS", r.out)
        r = self.rm("--verify-guide", str(self.tmp / "nope.md"))
        self.assertEqual(r.returncode, 2)

    def test_verify_guide_dir_paths_never_resolve_by_suffix(self):
        rc, by, _ = self.vg("Cited: lib/deleted.py and lib/deleted.py:4 and deleted.py:1 and h.py:1 and ./src/alpha.py and src\\alpha.py:5.\n")
        self.assertEqual(rc, 1)
        self.assertEqual(by["lib/deleted.py"]["status"], "STALE")  # only vendor/lib/deleted.py exists
        self.assertEqual(by["lib/deleted.py:4"]["status"], "STALE")
        # a bare file name may resolve by suffix, but never silently
        self.assertEqual(by["deleted.py:1"]["status"], "ok (resolved by suffix -> vendor/lib/deleted.py)")
        self.assertEqual(by["h.py:1"]["status"], "ok (resolved by suffix -> src/test_helpers/h.py)")
        self.assertEqual(by["./src/alpha.py"]["status"], "ok")  # './' stripped
        self.assertEqual(by["src/alpha.py:5"]["status"], "ok")  # backslashes normalised (not mis-parsed as alpha.py:5)

    def test_verify_guide_symbol_must_be_defined_not_just_mentioned(self):
        g = "In src/beta.py:frobnicate (comment only) and src/beta.py:string_sym (inside a string) and src/alpha.py:helper (real)."
        rc, by, summ = self.vg(g)
        self.assertEqual(rc, 1)
        self.assertEqual(by["src/beta.py:frobnicate"]["status"], "NOT DEFINED")
        self.assertEqual(by["src/beta.py:string_sym"]["status"], "NOT DEFINED")
        self.assertEqual(by["src/alpha.py:helper"]["status"], "ok")
        self.assertEqual(summ["not_defined"], 2)
        rc, by, summ = self.vg(g, "--allow-mentioned")
        self.assertEqual(rc, 0)
        self.assertEqual(by["src/beta.py:frobnicate"]["status"], "mentioned (allowed)")
        self.assertEqual(summ["mentioned_allowed"], 2)

    def test_symbol_definition_patterns(self):
        state = runpy.run_path(CLI, run_name="x")["gv_symbol_state"]
        defined = [("def run():\n  pass\n", "run", "py"), ("class Foo:\n  pass\n", "Foo", "py"), ("async def go(x):\n  pass\n", "go", "py"),
                   ("MAX_N = 3\n", "MAX_N", "py"), ("MAX_N: int = 3\n", "MAX_N", "py"), ("class A:\n    def method(self):\n        pass\n", "A.method", "py"),
                   ("name: build\njobs:\n  test:\n", "jobs", "yml"), ("build() {\n  echo\n}\n", "build", "sh"), ("function deploy {\n}\n", "deploy", "sh"),
                   ("func (s *Server) Handle(w int) {}\n", "Handle", "go"), ("x := 1\n", "x", "go"), ("type Config struct {\n}\n", "Config", "go"),
                   ("pub fn run() {}\n", "run", "rs"), ("impl Foo {\n}\n", "Foo", "rs"), ("export const API = 1;\n", "API", "ts"),
                   ("export interface Opts {}\n", "Opts", "ts"), ("export default function main() {}\n", "main", "js"),
                   ("# Design\n## The Cache layer\n", "Cache", "md"), ("  public static void main(String[] a) {\n", "main", "java")]
        for text, sym, ext in defined:
            self.assertEqual(state(text, sym, ext), "defined", (text, sym))
        not_defined = [("# def hidden():\n", "hidden", "py"), ("// func Hidden() {}\n", "Hidden", "go"), ("x = \"class Baz\"\n", "Baz", "py"),
                       ("y = call(Qux)\n", "Qux", "py"), ("def Run():\n  pass\n", "run", "py"), ("print(\"def s\")  # def t\n", "t", "py"),
                       ("/* function inBlock() {} */\n", "inBlock", "js"), ("-- func in_sql\n", "in_sql", "sql")]
        for text, sym, ext in not_defined:
            self.assertEqual(state(text, sym, ext), "mentioned" if text.lower().count(sym.lower()) and sym in text else "absent", (text, sym))
        self.assertEqual(state("def Run():\n", "run", "py"), "absent")  # case-sensitive

    def test_verify_guide_declared_runtime_references(self):
        g = """Same line: `.claude/engram_learned.md` is written at runtime <!-- verify-guide: runtime -->
<!-- verify-guide: ignore -->
Previous line marker covers `runtime/cache.json`.
But not `docs/gone.md` on the line after that.
Config glob: `out/report.json` and `out/deep/x.json`, while `src/alpha.py:1` is checked normally.
"""
        r = self.with_config("verify_guide_ignore: [out/**]\n", "--verify-guide", self.guide(g), "--json", as_json=False)
        self.assertEqual(r.returncode, 1)
        d = json.loads(r.out)
        by = {x["ref"]: x for x in d["references"]}
        for ref in (".claude/engram_learned.md", "runtime/cache.json", "out/report.json", "out/deep/x.json"):
            self.assertEqual(by[ref]["status"], "declared (runtime)", ref)
        self.assertEqual(by["docs/gone.md"]["status"], "STALE")  # the marker covers only its own and the next line
        self.assertEqual(d["summary"]["declared"], 4)
        self.assertEqual(d["summary"]["stale"], 1)
        ok = self.with_config("verify_guide_ignore: [out/**]\n", "--verify-guide", self.guide(g.replace("But not `docs/gone.md` on the line after that.\n", "")),
                              as_json=False)
        self.assertEqual(ok.returncode, 0, ok.out)
        self.assertIn("declared (runtime)", ok.out)
        self.assertIn("4 declared (runtime)", ok.out)
        self.assertIn("(4 declared)", ok.out)

    def test_verify_guide_no_silent_skips_and_footer(self):
        g = """[broken](lib/nofile.py) and [good](src/alpha.py) and [web](https://example.com/x/y.py) and [here](#anchor) and [m](mailto:a@b.c)
GitHub style: src/alpha.py#L3 and src/alpha.py#L3-L9 and src/alpha.py#L60 and bare src/missing_bare.py in prose and `weird/file.zzz`.
Windows: src\\alpha.py:60 end.
```
fenced src/hidden.py:1
two
```
"""
        rc, by, summ = self.vg(g)
        self.assertEqual(rc, 1)
        self.assertEqual(by["lib/nofile.py"]["status"], "STALE")
        self.assertEqual(by["src/alpha.py"]["status"], "ok")
        self.assertNotIn("https://example.com/x/y.py", by)
        self.assertEqual(by["src/alpha.py#L3"]["status"], "ok")
        self.assertEqual(by["src/alpha.py#L3-L9"]["status"], "ok")
        self.assertEqual(by["src/alpha.py#L60"]["status"], "STALE")
        self.assertEqual(by["src/missing_bare.py"]["status"], "STALE")
        self.assertEqual(by["src/alpha.py:60"]["status"], "STALE")
        self.assertEqual(summ["skipped_fenced_lines"], 2)
        self.assertEqual(summ["unparsed_candidates"], 1)  # `weird/file.zzz` looks like a path but has an unknown extension
        self.assertIn("checked ", summ["footer"])
        text = self.rm("--verify-guide", self.guide(g)).out
        self.assertIn("skipped 2 fenced-code lines; 1 unparsed candidates", text)

    def test_verify_guide_relative_link_from_a_guide_inside_the_repo(self):
        guide = self.repo / "docs" / "g.md"
        write(self.repo, "docs/g.md", "[up](../src/alpha.py) and [bad](../src/nope.py)\n")
        try:
            r = self.rm("--verify-guide", str(guide), "--json")
        finally:
            shutil.rmtree(self.repo / "docs", True) if not (self.repo / "docs" / "guide.md").exists() else guide.unlink()
        by = {x["ref"]: x for x in json.loads(r.out)["references"]}
        self.assertEqual(by["../src/alpha.py"]["status"], "ok")
        self.assertEqual(by["../src/nope.py"]["status"], "STALE")

    def test_guide_status_missing_current_stale(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "r"
            shutil.copytree(self.repo, repo)
            status = lambda: json.loads(cli(repo, "review-map", "--json").out)
            self.assertEqual(status()["guide_status"], "missing")
            head = git(repo, "rev-parse", "HEAD").out.strip()
            base = git(repo, "rev-parse", "main").out.strip()
            write(repo, "docs/review-guide.md", "<!-- review-guide: base=<sha> head=<sha> -->\n# guide\n")
            self.assertEqual(status()["guide_status"], "stale")  # placeholder marker
            write(repo, "docs/review-guide.md", f"<!-- review-guide: base={base} head={head} -->\n# guide\n")
            d = status()
            self.assertEqual(d["guide_status"], "current")
            self.assertIn("written for this head", d["guide_status_reason"])
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "guide")
            self.assertEqual(status()["guide_status"], "current", "only the guide (docs) changed since")
            write(repo, "README.md", "more docs\n")
            git(repo, "commit", "-q", "-am", "docs only")
            self.assertEqual(status()["guide_status"], "current")
            write(repo, "src/new_code.py", "x = 1\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "code")
            d = status()
            self.assertEqual(d["guide_status"], "stale")
            self.assertIn("code, tests or config changed", d["guide_status_reason"])
            text = cli(repo, "review-map").out
            self.assertIn("guide file docs/review-guide.md: stale", text)
            write(repo, "docs/other.md", f"<!-- review-guide: base={base} head={git(repo, 'rev-parse', 'HEAD').out.strip()} -->\n")
            write(repo, ".autocraft/config.yml", "review_guide_path: docs/other.md\n")
            self.assertEqual(status()["guide_status"], "current")  # configurable path
            self.assertEqual(status()["guide_path"], "docs/other.md")


if __name__ == "__main__":
    unittest.main(verbosity=1)
