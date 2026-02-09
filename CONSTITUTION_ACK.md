# Constitution Acknowledgment

The following constraints from `claude.md` govern all work in this repository:

- **Promoter inputs are hard constraints.** Ticketmaster does not control pricing, inventory, or release strategy; rights owners define all boundaries and the system operates strictly within them.
- **No default optimization objective.** The system must never assume "maximize revenue" by default. If the objective is ambiguous, options must be enumerated and explicit selection requested before proceeding.
- **Fairness and regulatory awareness.** Designs must avoid speed-based competition, misleading price anchoring, or illusory availability. All allocation logic must be explainable in plain language under the assumption of public and regulatory scrutiny.
- **Strict modeling scope.** Simulation of synthetic demand, WTP distributions, and heuristic/optimization solvers is permitted. Building or implying production-ready systems, referencing proprietary data, or optimizing resale outcomes is prohibited.
- **Explainability for every decision.** Every allocation must document the constraints applied, the objective function used, alternatives considered, reasons alternatives were rejected, and sensitivity analysis where relevant.
- **Careful language and framing.** The system "allocates given constraints" rather than "decides" prices. Normative claims like "best" or "fairest" require defined metrics; preferred terms are "feasible," "infeasible," "dominant," and "tradeoff."
- **Iterative, assumption-explicit development.** Start with the simplest viable model, list all assumptions explicitly, propose incremental enhancements, and treat all outputs as experimental and revisable.
