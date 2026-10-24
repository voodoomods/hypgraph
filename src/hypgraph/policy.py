"""
Who the record trusts for what. These are the host application's decisions — HypGraph enforces them but never
authenticates anyone: whoever calls ``Graph.create(author=...)`` is taken at their word, so a host exposing the graph
to others (an HTTP API, an MCP server, a team of agents) must fix ``author`` itself and refuse the reserved names.

    reviewers    whose verdicts count (official reviews). An investigation can add its own (field ``reviewers``).
    instrument   the author whose ``kind=lab`` runs are records the instrument made (a lab job runner) — the only
                 author that can file a lab-recorded run and what it produced.
    operator     the person in charge: revises anything, settles disputes, withdraws and retracts.
    importer     brings in a legacy record: may attribute a node to its original author, isn't held to the claim
                 checks (the old record is imported as written), settles disputes like the operator.
    system       reserved for the host's own bookkeeping.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Policy:
    reviewers: frozenset = field(default_factory=frozenset)
    instrument: str = "lab"
    operator: str = "operator"
    importer: str = "importer"
    system: str = "system"
    max_creates_per_minute: int = 60

    def __post_init__(self):
        object.__setattr__(self, "reviewers", frozenset(self.reviewers))

    @property
    def curators(self) -> frozenset:
        """Operator and importer: may revise anything, settle disputes, and aren't held to the claim checks."""
        return frozenset({self.operator, self.importer})

    @property
    def reserved(self) -> frozenset:
        """Names a host must never let an outside caller write as."""
        return frozenset({self.instrument, self.operator, self.importer, self.system})

    def to_dict(self) -> dict:
        return {"reviewers": sorted(self.reviewers), "instrument": self.instrument, "operator": self.operator,
                "importer": self.importer, "system": self.system,
                "max_creates_per_minute": self.max_creates_per_minute}

    @classmethod
    def from_dict(cls, d: dict) -> "Policy":
        d = dict(d or {})
        return cls(reviewers=frozenset(d.pop("reviewers", ()) or ()),
                   **{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
