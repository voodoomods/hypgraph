"""The website names the newest profile versions wherever it says what to pin, and its example prints what it shows.
A new profile version without these pages moving fails here (the site said scientific@2 / trading@3 /
optimization@3 two releases after the newer versions shipped)."""
import re
from pathlib import Path

from hypgraph import Graph, Policy
from hypgraph import profiles as P

SITE = Path(__file__).resolve().parents[1] / "site"
PIN = re.compile(r"\b(scientific|software|trading|knowledge|optimization)@(\d+)\b")


def newest() -> dict[str, str]:
    return {n: P.latest(n).id for n in ("scientific", "software", "trading", "knowledge", "optimization")}


def pins(text: str) -> dict[str, str]:
    found = {}
    for name, v in PIN.findall(text):
        assert found.setdefault(name, f"{name}@{v}") == f"{name}@{v}", f"two versions of {name}: {text[:200]}"
    return found


def test_the_home_pages_workflow_table_names_the_newest_versions():
    page = (SITE / "index.html").read_text(encoding="utf-8")
    table = page[page.index('id="workflows"'):]
    table = table[:table.index("</table>")]
    assert pins(table) == newest()


def test_the_agents_page_says_to_pin_the_newest_versions():
    page = (SITE / "agents" / "index.html").read_text(encoding="utf-8")
    para = page[page.index("An investigation pinned to"):]
    para = para[:para.index("</p>")]
    assert pins(para) == newest()


def test_llms_txt_lists_the_newest_versions():
    text = (SITE / "llms.txt").read_text(encoding="utf-8")
    line = text[text.index("An investigation may pin a profile:"):]
    line = line[:line.index(" — the newest versions")]
    assert pins(line) == newest()


def test_the_engineers_example_pins_the_newest_software_profile_and_prints_what_it_shows():
    page = (SITE / "engineers" / "index.html").read_text(encoding="utf-8")
    pinned = re.search(r'"profile": "(software@\d+)"', page).group(1)
    assert pinned == newest()["software"]
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.create(author="operator", type="investigation", fields={
        "title": "Issue 412", "objective": "Fix the importer and prove it.", "profile": pinned})["id"]
    q = g.create(author="operator", type="question", inv=inv,
                 fields={"text": "Does the importer keep quoted commas?"})["id"]
    s = g.stage(q)
    shown = (f'{{"stage": "{s["stage"]}", "index": {s["index"]}, "of": {s["of"]}, "complete": {s["complete"]},'
             f'\n                  #  "next": "{s["next"]}"')
    assert "g.stage(q)        # " + shown in page
