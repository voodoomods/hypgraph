# Workflow specs — P0 of the profiles-as-workflows plan

One page per profile, for review before any kernel code (see `../profile-workflows-plan.md`). Each spec names the
method it is taken from, then states what the record would enforce: the stages a question passes through, the gate
out of each stage (predicates the record checks), who works the stage, what later invalidates a claim, what
"fresh" means, the typed artifacts with their required fields, the report, and completion.

Conventions used in every spec:

- **A stage is derived, never set.** A question is in the first stage whose gate is not met. Agents write nodes;
  the record reads the stage off them.
- **Gates are predicates** the record evaluates from the record alone (existing ones in `coord.PREDICATES` and
  `profiles.PRED_DESC`; new ones are marked **new**).
- **Invalidation** names the relations that, when the far end falls, changes version or expires, put dependants
  AT RISK. Today only the scientific set (`requires`, `derived_from`, `based_on`, `works_on`, `rests_on`) does.
- **Fresh** says when a result still speaks for the thing it measured.
- **Typed artifacts** are `artifact` / `source` / `decision` nodes with required fields per `kind`, not new types.

| spec | method it is taken from | the one gate a prompt can't keep |
|---|---|---|
| [scientific](scientific.md) | hypothetico-deductive method, preregistration | a corrected data file after the analysis |
| [software](software.md) | continuous integration and code review | a commit after the tests ran |
| [trading](trading.md) | preregistered backtesting, risk management | a backtest past its review date, a regime notice |
| [knowledge](knowledge.md) | source criticism, fact-checking practice | a retracted or superseded source |
| [optimization](optimization.md) | operations-research practice: model, solve, bound, verify | a changed instance after the solve |

Review questions are at the end of each spec. Nothing here is implemented.
