# Stock Market Intelligence — implementation and learning plan

Draft: 8 October 2026. This document proposes the work; no application has been implemented yet.

## 1. Two equally important outcomes

Build a useful, locally run US stock research CLI and develop practical agentic system engineering skills. Learning topics are an evolving curriculum, not limited to the examples discussed. Every milestone includes an explanation, implementation, experiment, validation, and short design review.

Work in understandable increments. Before implementing a component, explain its responsibility and tradeoffs. Afterward, walk through its behavior and let the learner modify or debug it. Maintain learning notes and short architecture decision records as the system evolves.

## 2. MVP contract

- Onboarding asks the user to select at least five distinct US-listed company stocks. Validate symbols and resolve company identity; do not silently choose stocks or correct ambiguous symbols.
- Generate a daily Markdown report manually or through local scheduling.
- Cover revenue growth, margins, cash flow, debt, valuation, and earnings guidance where evidence is available. Distinguish fresh developments from dated financial context.
- Connect companies to multiple business themes and broader sectors; include relevant macro developments, including rates and Fed policy.
- Save preferences and allow feedback to change future emphasis. Default reporting does not require an approval pause; an optional interactive mode teaches interruption and resumption.
- Support conversational follow-up using saved reports and their underlying evidence. Clearly disclose the evidence cutoff. Fresh research during chat is a later extension.
- Start with free data sources and configurable paid LLM access. English is the initial language assumption.
- Keep domain logic independent of the CLI so a GUI can reuse it later.

Out of scope initially: order execution, portfolio optimization, real-time market feeds, exhaustive market coverage, hosted multi-user operation, and automatic public distribution of source content.

## 3. Proposed architecture

```text
CLI / local scheduler
        |
application services: watchlist, report, chat, preferences
        |
LangGraph report workflow
load preferences -> collect/cache -> normalize -> retrieve evidence
       -> bounded research -> validate -> render/save
                                 |
                    optional human review/resume

LangChain model + tool interfaces
        |
provider adapters / research procedures / retrieval
        |
SQLite records + persistent checkpoints + source files + search index
```

Start with **one research-agent definition**, reusable across companies and follow-up sessions. A graph node is not necessarily an agent. Collection, calculations, validation, rendering, and scheduling are ordinary Python code. The agent gets bounded discretion to choose research tools and inspect evidence gaps.

LangChain supplies model/tool integration; LangGraph supplies explicit workflow state and control flow. This division follows the [official LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview).

Proposed supporting stack: Python, uv for reproducible dependencies, Pydantic for schemas, Typer/Rich for CLI presentation, SQLite for local structured storage, pytest for meaningful checks. Pin compatible versions during setup. Select a local vector index and embedding model during retrieval experiments rather than committing before measuring needs.

Try DeepSeek first if credentials are supplied. Smoke-test tool calling, structured output, latency, and error behavior for the actual selected model. Tool calling is documented in the [DeepSeek API guide](https://api-docs.deepseek.com/guides/tool_calls/); that is not a guarantee of identical behavior across integrations. Keep model configuration separate from business logic. Embeddings are a separate model choice, with a local option preferred initially.

## 4. Data feasibility and sourcing

| Need | Initial candidate | Design consequence |
|---|---|---|
| Filings and reported fundamentals | SEC submissions and Company Facts | Map ticker to issuer; retain filing date, reporting period, units, accession, and source. |
| Earnings guidance and business segments | Company investor-relations releases and filings | Availability and extraction differ by issuer; mark missing values instead of fabricating them. |
| End-of-day prices and valuation inputs | yfinance as a provisional personal-demo adapter | Cache results, label as-of times, and expect provider failures. |
| Macro series | FRED | Requires an API key; retain observation and retrieval dates and account for revisions. |
| Fed announcements | Federal Reserve RSS and linked releases | Ingest authoritative policy evidence. |
| Industry/company news | Selected accessible publisher feeds, company releases, and industry sources | Audit available feeds for the chosen watchlist; expose coverage gaps and deduplicate syndicated stories. |

SEC documents its public data interfaces in its [API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). FRED explains its [API key requirement](https://fred.stlouisfed.org/docs/api/api_key.html). The Fed publishes [RSS feeds](https://www.federalreserve.gov/feeds/feeds.htm). The [yfinance documentation](https://ranaroussi.github.io/yfinance/) describes its unofficial status and personal-use limitations; broader distribution will require a data-rights and provider review.

Do a five-stock coverage spike before promising a complete report. Check access from the user's machine, rate limits, extraction quality, available history, and permitted storage. A headline-only feed cannot support claims about an inaccessible article's full contents.

Numeric calculations run in Python. Define each metric's formula, period, and units. Handle quarterly versus cumulative cash flows, fiscal calendars, amended filings, negative earnings, and unavailable values. Do not compare incompatible periods or label derived metrics as directly reported facts. Retain publication dates so historical demonstrations cannot use evidence that was unavailable at the time.

## 5. Context, knowledge, and memory

| Layer | Contents | Policy |
|---|---|---|
| Run state | Current step, errors, tool results, evidence references | Checkpoint and resume; keep large documents outside graph state. |
| Conversation memory | Recent messages and a compact summary | Persist by session; trim to budget; keep evidence IDs across summaries. |
| User memory | Metric priorities, topic interests, explicit corrections | Store versioned preferences; support view/edit/reset; do not infer permanent preferences from casual questions. |
| Research history | Prior themes, observations, supporting sources | Timestamp, reconcile duplicates, and distinguish interpretations from facts. |
| Knowledge corpus | Source documents, structured metrics, chunks | Retrieve with ticker/topic/date filters and provenance. |

LangGraph distinguishes thread-scoped checkpointers from cross-thread stores; local persistent checkpoints are appropriate here. Application preferences can live in ordinary SQLite tables behind a repository interface rather than forcing everything into a framework store. See [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence).

Build each model context deliberately: instructions, current task, relevant preferences, selected evidence, then necessary conversation history. Allocate explicit input/output budgets, cap tool output and tool iterations, and log usage. Summaries are navigation aids; original evidence remains authoritative. Retrieved content is untrusted data and cannot override instructions or trigger preference updates.

RAG progresses from a keyword baseline to semantic retrieval, then a measured hybrid experiment. Compare chunk boundaries, metadata filtering, recall, and answer support. Retrieve numerical values from structured records and explanatory passages from documents. Follow-up answers cite original evidence, not merely earlier generated reports. The [official retrieval guide](https://docs.langchain.com/oss/python/deepagents/retrieval) describes these retrieval building blocks.

## 6. Milestones and learning checkpoints

### M0 — Foundations, contracts, and data spike

**Build:** Project setup, configuration, watchlist entry/validation, provider interfaces, source schema, and cached samples for five user-selected stocks. Establish initial report examples and evaluation questions. Keep secrets out of source control.

**Learn:** Agent versus workflow, dependency management, schemas, adapters, provenance, API limits, and time-aware data.

**Experiment:** Inspect how the same metric differs across a filing and a convenience API.

**Exit:** A coverage matrix identifies supported metrics and explicit gaps for all five stocks; missing credentials have actionable setup messages.

### M1 — First useful report

**Build:** A thin collect → normalize → summarize → Markdown path. Add a configurable LangChain model, structured report output, source IDs, Python metric calculations, and cached offline demonstration inputs. Capture timing and token usage from the first model call.

**Learn:** Prompt design, structured outputs, grounding, deterministic versus probabilistic work, provider abstraction, and basic evaluation.

**Experiment:** Compare an unconstrained summary with a schema-driven, evidence-backed report.

**Exit:** One command creates a five-stock report with dated metrics, citations, explicit missing data, and bounded model usage.

### M2 — Tools and LangGraph orchestration

**Build:** Tools such as get_fundamentals, list_recent_disclosures, retrieve_evidence, and get_macro_context. Add explicit graph state, conditional steps, timeouts, bounded retries, persistent checkpoints, and a run identifier. Keep preference writes outside autonomous research tools.

**Learn:** Tool schemas, tool-selection loops, state transitions, error propagation, idempotency, persistence, and traces.

**Experiment:** Inject a provider timeout and resume an interrupted run without duplicating completed report writes.

**Exit:** A partial source failure produces an explicitly incomplete report when sufficient evidence remains; insufficient evidence produces a clear failed run. Both are inspectable.

### M3 — Industry and macro trend monitoring

**Build:** Editable company → business themes → sector mappings; shared topic collection; deduplicated historical observations; trend sections linked to affected stocks. Use a configurable recent window and prior baseline. Label candidates as new, strengthening, recurring, or uncertain with supporting evidence.

**Learn:** Entity resolution, hierarchical classification, temporal aggregation, novelty detection, shared work, and uncertainty.

**Experiment:** Compare counts before and after deduplication; test whether syndicated articles falsely create a trend.

**Exit:** Related companies share sector evidence; company-specific effects remain distinct. Cold-start runs state that history is insufficient rather than claiming a trend is accelerating. Macro relevance is explained as an interpretation, not asserted causation.

### M4 — RAG and follow-up conversation

**Build:** Document parsing, chunking, searchable evidence, metadata filters, citations, chat sessions, and a local embedding/index option. Constrain chat to saved evidence for the MVP.

**Learn:** Keyword versus vector retrieval, embeddings, chunking, retrieval evaluation, context assembly, query rewriting, and abstention.

**Experiment:** Compare keyword, vector, and hybrid retrieval on the same curated questions; retain the simplest adequate approach.

**Exit:** Follow-up answers use relevant sources, preserve date boundaries, and say when saved evidence cannot answer the question.

### M5 — Human feedback, memory, and reusable research procedures

**Build:** Explicit preference editing plus natural-language feedback that previews structured changes before saving. Add memory inspection/reset, conversation summarization, and optional LangGraph review interruption/resumption. Routine daily runs continue unattended with saved preferences.

**Learn:** Short- versus long-term memory, memory write policies, conflict resolution, context compression, human control, and procedural reuse.

**Custom skills:** Versioned research playbooks describing purpose, inputs, evidence requirements, permitted tools, steps, and output schema—for example earnings review, balance-sheet review, and semiconductor supply-chain review. These are application research procedures, not automatically desktop skill installations. Load only the relevant playbook into context.

**Experiment:** Ask to emphasize margins over daily price moves, restart the CLI, and compare the next report. Test that a one-off question does not silently overwrite preferences.

**Exit:** Preferences persist, can be reversed, and visibly influence reports. A paused review resumes after restart. Historical facts remain distinct from remembered user preferences.

### M6 — Scheduling and MVP hardening

**Build:** Local scheduler invoking the same report service, status commands, run locking, duplicate protection, logs, retention settings, and a documented demonstration. Proposed default: after US market close using America/New_York time with an exchange calendar; display local times in Asia/Shanghai. Support a configurable catch-up policy when the computer was asleep.

**Learn:** Time zones and daylight saving, scheduling, concurrency limits, graceful degradation, integration tests, reproducibility, and operational ownership.

**Experiment:** Simulate a holiday, a missed run, a duplicate trigger, an empty feed, and invalid credentials.

**Exit:** The user can install, configure, schedule, inspect, and stop the application using documented commands; repeated triggers do not create duplicate reports.

### M7 — Required learning experiment: multiple agents

**Build:** An experimental branch/configuration with a company-research agent and an industry/macro agent, followed by a synthesis step. Give workers explicit input/output contracts and bounded evidence access. The synthesis step need not be an autonomous third agent.

**Learn:** Delegation, isolated context, aggregation, parallel execution, duplicated work, error propagation, and coordination overhead.

**Experiment:** Compare the single-agent baseline and two-agent alternative using identical saved inputs and comparable budgets. Measure evidence support, omissions, latency, tool calls, and cost.

**Exit:** Record an evidence-based architecture decision. Complete the learning experiment even if one agent remains the MVP default; more agents are not a success criterion.

## 7. Quality gates

Create a small curated evaluation set early and extend it at each milestone. Proposed final set: 20 questions covering numerical lookup, comparisons, industry themes, macro context, time cutoffs, and unanswerable questions.

- Numeric fixtures must match independently checked calculations, units, and periods.
- Every cited identifier must resolve to stored evidence; this mechanical check does not prove semantic support.
- Manually review a sample of factual claims for actual support. Use model-based grading only as supplementary feedback.
- Target relevant evidence in the top five results for at least 90% of answerable evaluation questions; tune this proposed target after establishing the baseline.
- All deliberately unanswerable cases must disclose insufficient evidence rather than invent an answer.
- Test source failures, duplicate writes, restart/resume, persisted preferences, and retrieved prompt-injection text.
- Record model, prompt/skill versions, source cutoff, calls, token use, elapsed time, and estimated cost per run. Set a configurable hard usage ceiling; choose the default after measuring a five-stock report.

Maintain local structured traces first. Hosted tracing is optional and requires an explicit decision about sending prompts and source content externally. Do not log secrets.

## 8. Proposed user experience

These are design examples, not implemented commands:

```sh
market init
market watchlist add <TICKER>
market watchlist list
market report
market report --review
market chat --report latest
market preferences show
market feedback "Focus more on margins and data-center demand"
market runs list
market schedule enable
market schedule status
market schedule disable
```

Report structure: summary of new developments; watchlist fundamentals; industry themes; relevant macro changes; open questions; data gaps and source cutoff; references. Include an as-of date and distinguish observation from interpretation. Save a structured report record alongside Markdown so a future GUI need not parse prose.

Suggested module boundaries: cli, application, domain, providers, tools, workflows, retrieval, memory, research_skills, reporting, and evaluation. Introduce modules as needed rather than generating an empty framework upfront.

## 9. Completion and future evolution

MVP completion requires all core behavior through M6 plus the M7 learning comparison: a reproducible five-stock demonstration, a scheduled run, grounded follow-ups, a preference change surviving restart, visible source failures, and a documented architecture explanation by the learner.

Select the actual five stocks and obtain model credentials before live integration; a FRED key is needed for its API. These do not block drafting or basic scaffolding. Provider coverage, embedding choice, model choice, and numeric cost ceilings remain measured decisions rather than promises.

Later topics include GUI/API design, authenticated users and memory isolation, deployment, paid source contracts, fresh-research chat, advanced reranking, MCP tool interoperability, and model routing. Add them when they create useful product or learning outcomes. There is no fixed calendar estimate until the first data spike and learning cadence are established.
