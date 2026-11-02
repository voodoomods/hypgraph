"""
HypGraph — a research record that can't flatter itself.

    Don't believe the hype. Test the hyp.

    >>> from hypgraph import Graph, Policy
    >>> g = Graph(policy=Policy(reviewers={"ada"}))          # in memory; Graph("study.hypgraph") for a file
    >>> me = g.author("sam")
    >>> inv = me.investigation("Plant growth", "Find out whether light colour changes how fast cress grows.")["id"]
    >>> h = me.add("hypothesis", inv, statement="Blue light makes cress grow faster than red light.",
    ...            predictions=["Blue-lit trays are taller after 7 days."])
    >>> h["state"]["sentence"]
    'active hypothesis · unchecked · no live support · unverified report · no external replication'

Standing is derived on every read, never stored; every write is an event in a SHA-256 hash chain; claims carry
their numbers; reviews pin versions; independence is counted, not assumed. See https://hypgraph.com.
"""

__version__ = "0.8.1"

from .bundle import anchored, verify_bundle  # noqa: E402
from .graph import Author, Graph, GraphError, file_sha256  # noqa: E402
from .policy import Policy  # noqa: E402
from .references import verify_reference  # noqa: E402
from .schema import FORMAT, describe  # noqa: E402
from .store import verify_file  # noqa: E402

__all__ = ["Graph", "GraphError", "Policy", "Author", "verify_bundle", "anchored", "verify_file", "file_sha256", "describe", "verify_reference",
           "FORMAT", "__version__"]
