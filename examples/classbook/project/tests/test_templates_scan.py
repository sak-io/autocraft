"""Architecture s5/T-6: every <form method=post> in any template must contain csrf_field()."""
import re
from pathlib import Path

TEMPLATES = Path(__file__).parent.parent / "classbook" / "web" / "templates"
FORM = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.I | re.S)
POST = re.compile(r"""\bmethod\s*=\s*["']?post\b""", re.I)


def forms(directory=TEMPLATES):
    for path in sorted(directory.rglob("*.html")):
        for attrs, body in FORM.findall(path.read_text()):
            yield path.name, attrs, body


def missing_csrf(directory=TEMPLATES):
    """Names of templates holding a POST form without csrf_field() - the real scan, used by the tests below."""
    return [name for name, attrs, body in forms(directory) if POST.search(attrs) and "csrf_field()" not in body]


def test_scan_finds_templates_and_the_logout_form():
    assert any(a and POST.search(a) for _, a, _ in forms())


def test_every_post_form_uses_csrf_field():
    assert missing_csrf() == []


def test_every_form_declares_a_method_explicitly():
    # a form without method is a GET form; require it spelled out so the scan cannot be dodged
    assert [n for n, a, _ in forms() if not re.search(r"\bmethod\s*=", a, re.I)] == []


def test_scan_would_catch_a_missing_field(tmp_path):
    (tmp_path / "bad.html").write_text('<form method="post" action="/x"><button>go</button></form>')
    (tmp_path / "good.html").write_text('<form method="post" action="/x">{{ csrf_field() }}<button>go</button></form>')
    (tmp_path / "get.html").write_text('<form method="get" action="/x"><button>go</button></form>')
    assert missing_csrf(tmp_path) == ["bad.html"]
