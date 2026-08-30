# Revenue Recovery — Architecture Diagram

Renders natively on GitHub. Editable Mermaid source (identical diagram body): [`revenue-recovery-architecture.mmd`](revenue-recovery-architecture.mmd). Pre-rendered image: [`revenue-recovery-architecture.svg`](revenue-recovery-architecture.svg) (generated from the `.mmd` file via `@mermaid-js/mermaid-cli`).

```mermaid
flowchart TD
    subgraph Z1["1 . Input / Simulator"]
        A["Payment failure event"] --> B["Simulator draws episode<br/>population.yaml + episode.yaml<br/>decline_code, invoice_amount"]
    end

    subgraph Z2["2 . Episode State"]
        B --> C["EpisodeView<br/>observable fields only<br/>no hidden/latent state exposed"]
    end

    subgraph Z3["3 . Policy / Planner"]
        C --> E["A3-D<br/>deterministic 16-rule table<br/>decline routing, retry-window timing,<br/>remedy matching, withhold_applies restraint,<br/>STOP / WAIT / CONTACT"]
        C --> F["A3-LLM<br/>gpt-5-mini prompted planner<br/>DEV / TUNING ONLY<br/>not holdout validated"]
        F -->|"fallback on timeout, parse error,<br/>schema violation, gate reject"| E
    end

    subgraph Z4["4 . Safety Gate"]
        E --> G{"Gate: rules R1-R8<br/>remedy match, budget cap,<br/>quiet hours, risk stop"}
        F --> G
    end

    subgraph Z5["5 . Executor and Ledger"]
        G -->|reject| REJ["Enforcement fallback / no action"]
        G -->|accept| H{"Executed action"}
        H -->|CONTACT| I["Send message"]
        H -->|WAIT| J["No action this tick"]
        H -->|STOP| K["End future contact,<br/>forfeit remaining budget"]
        I --> L["Ledger record:<br/>rule id, reason_code,<br/>gate verdict, action"]
        J --> L
        K --> L
        REJ --> L
    end
    L -->|next tick| C

    subgraph Z6["6 . Evaluation Harness"]
        M["DEV<br/>tuning, GPT-C1 to C6,<br/>Day 9 diagnostics,<br/>dev-only threshold frontier"]
        N["FROZEN HOLDOUT<br/>single sealed run, A3-D only,<br/>criteria 1-5 evaluation,<br/>no post-hoc tuning, no A3.1"]
    end
    E --> M
    E --> N
    F --> M

    classDef holdout fill:#e6f4ea,stroke:#2e7d32,stroke-width:2px;
    classDef devonly fill:#fdecea,stroke:#c62828,stroke-width:2px,stroke-dasharray: 5 3;
    classDef gate fill:#fff8e1,stroke:#f9a825,stroke-width:2px;
    class E,N holdout
    class F,M devonly
    class G gate
```

## Legend

- **Green, solid border** — part of A3-D, the deterministic policy actually scored on the frozen holdout run (`RESULTS.md`).
- **Red, dashed border** — A3-LLM and its evaluation surface: development/tuning only. A3-LLM has no edge to the "FROZEN HOLDOUT" box anywhere in this diagram, on purpose — it never ran on holdout (`EVAL.md §7.1` item A).
- **Yellow** — the safety gate (`src/rrx/agent/gate.py`, rules R1–R8, `EVAL.md §5.2`), the single chokepoint both A3-D and A3-LLM proposals pass through before anything is executed.

## Notes

- Grounded in `ARCHITECTURE.md` §2–§4 and `docs/A3-DESIGN.md` §10A; no component here is invented.
- **A0, A1, A2-strengthened, and A4 are intentionally not drawn.** They share the simulator via a simpler `(opening_condition_key, day, subscription_state) -> action` interface with no `EpisodeView`, gate, or ledger (`ARCHITECTURE.md` §2) — a materially different, simpler path than the one this diagram shows. This diagram covers the A3-D / A3-LLM path only.
- The `A3-D → FROZEN HOLDOUT` edge represents the one sealed, single-use holdout run this candidate has (`results/holdout/4d45db461943/`). It does not imply repeated or ongoing holdout access, and the `A3-D → DEV` edge is a separate, uncapped surface (dev runs, stress runs, Day 9 diagnostics — none of which touch holdout).
- This diagram does not depict the Day 9 dev-only restraint-threshold frontier (`docs/analysis/DAY9-FRONTIER.md`) as a distinct policy variant — that sweep used a parameterized copy of the decision table kept entirely outside `src/rrx/agent/`, never the shipped `A3-D` box shown here, and is not a deployed or holdout-evaluated configuration.
