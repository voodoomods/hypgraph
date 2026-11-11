"""A link that adds support to a claim is checked as the claim's create would have been.

Claim checks ran when a claim was created or revised, never when a link added to what it rests on. So any check that
reads the support could be stepped round: write the claim with harmless support, link the rest a minute later. Found
in a HypSwarm swarm on gpt-oss-20b (BC-250, 2026-11-10): an answer resting on a source that names no sources was
created on a result, and the `cites` link to that source was added 53 s later by a separate link. The link is refused
only for problems it brings; one the claim already had (the record changed around it) doesn't block new links."""
import pytest

from hypgraph import Graph, GraphError, Policy

SCOPE = "The ten inventory items and the 36 kg limit given in the memo."
POUNDS = "The weight limit doesn't apply as stated, because the weights are recorded in pounds, not kilograms."


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}))
    cur = g.author("curator")
    inv = cur.investigation("Load", "What is the highest total value that fits within the 36 kg limit?")["id"]
    kg = cur.add("source", inv, citation="Units note", passage="Units note: every weight in the inventory is in "
                 "kilograms.", kind="primary")["id"]
    memo = cur.add("source", inv, citation="Loading memo", passage="The container takes at most 36 kg in total.",
                   kind="primary")["id"]
    return g, inv, kg, memo


def claim(g, inv, who, statement, support):
    return g.author(who).add("claim", inv, statement=statement, scope=SCOPE,
                             links=[{"rel": "supports", "from": x, "why": "The party cites this for its claim."}
                                    for x in support])["id"]


def codes(e) -> list[str]:
    return [p["code"] for p in e.value.problems]


@pytest.mark.parametrize("rel,src_is_source", [("supports", True), ("cites", False)])
def test_support_added_by_a_link_is_checked(env, rel, src_is_source):
    g, inv, kg, memo = env
    with pytest.raises(GraphError) as e:                   # the create the link would step round
        claim(g, inv, "b", POUNDS, [memo, kg])
    assert codes(e) == ["SOURCE_CONTRADICTS"]
    c = claim(g, inv, "b", POUNDS, [memo])
    with pytest.raises(GraphError) as e:
        if src_is_source:
            g.link(author="b", src=kg, rel=rel, dst=c, why="The units note is cited for the claim.")
        else:
            g.link(author="b", src=c, rel=rel, dst=kg, why="The units note is cited for the claim.")
    assert codes(e) == ["SOURCE_CONTRADICTS"]
    assert "every weight in the inventory is in kilograms" in str(e.value)
    assert not any(x["src"] == kg and x["dst"] == c or x["src"] == c and x["dst"] == kg
                   for x in g.snapshot().edges.values())
    log = [r for r in g.refusals(inv=inv) if r["op"] == "link"]
    assert log and log[-1]["problems"][0]["code"] == "SOURCE_CONTRADICTS"


def test_support_that_agrees_still_links(env):
    g, inv, kg, memo = env
    c = claim(g, inv, "b", "The weights are recorded in kilograms, not pounds.", [kg])
    out = g.link(author="b", src=memo, rel="supports", dst=c, why="The memo states the limit in kilograms.")
    assert out["edge"]


def test_a_problem_the_claim_already_had_does_not_block_a_link(env):
    g, inv, kg, memo = env
    c = claim(g, inv, "b", POUNDS, [memo])
    # the record changes around the claim: the operator adds the contradicting support (curators aren't checked)
    g.link(author="operator", src=kg, rel="supports", dst=c, why="Filed by the operator for completeness.")
    other = g.author("curator").add("source", inv, citation="Shipping manifest", passage="Ten items are listed on the manifest.",
                                    kind="primary")["id"]
    # a link that brings nothing new is not refused for what was already there
    assert g.link(author="b", src=other, rel="supports", dst=c, why="The manifest lists the items it covers.")["edge"]


def test_links_that_add_no_support_are_not_rechecked(env):
    g, inv, kg, memo = env
    c = claim(g, inv, "b", POUNDS, [memo])
    q = g.author("curator").add("question", inv, text="Are the weights in kilograms?")["id"]
    assert g.link(author="b", src=c, rel="answers", dst=q, why="The claim says what unit the weights are in.")["edge"]


def test_curators_link_unchecked(env):
    g, inv, kg, memo = env
    c = claim(g, inv, "b", POUNDS, [memo])
    assert g.link(author="operator", src=kg, rel="supports", dst=c, why="Imported with the case file.")["edge"]
