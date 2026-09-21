# Controlled Agentic RAG Architecture

This document describes the design, state management, tool execution lifecycle, and citation verification mechanics of **Version 3 (Controlled Agentic RAG)**.

---

## 1. Why a Controlled Agent Instead of a Framework Wrapper?

Many agent demonstrations wrap high-level libraries (e.g. LangChain, CrewAI) with uncontrolled loops and non-deterministic behavior. In an enterprise legal setting, uncontrolled agents present major risks:
1. **Infinite Loop Risk**: Agents looping repeatedly without converging.
2. **Arbitrary Tool Execution**: Risk of the LLM invoking arbitrary local Python code or unintended network operations.
3. **Speculative Legal Hallucinations**: Agents generating authoritative-sounding legal conclusions without retrieving contract evidence.
4. **Latency & Cost Explosions**: Unchecked multi-step reasoning consuming thousands of tokens and dozens of API calls.

To address these concerns, we built a **controlled, bounded agent architecture** using the official Google GenAI SDK function-calling interface.

---

## 2. Agent State Machine & Execution Lifecycle

```
[ User Query ]
      │
      ▼
┌──────────────┐
│ Initial Step │ ──> Create AgentState(query, contract, max_steps=5)
└──────┬───────┘
       │
       ▼
┌──────────────┐     Tool Call
│ Agent Reason │ ────────────────> Validate Against TOOL_REGISTRY Whitelist
└──────┬───────┘                                │
       ▲                                        ▼
       │                                 Execute Tool
       │                                        │
       │    Append FunctionResponse             ▼
       └────────────────────────────── Accumulate into EvidenceState
       │
       │ Final Text Returned OR Step Limit (5) Reached
       ▼
┌──────────────────────────────┐
│ Evidence Policy Verification │
└──────────────┬───────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
 Zero Evidence?     Evidence Found
       │               │
       ▼               ▼
 Abstain Response   Post-Generation Citation Verifier
                       │
                       ▼
                 Auditable Answer + Trace
```

---

## 3. Whitelisted Tool Registry

The agent cannot execute arbitrary Python code. Every tool call is intercepted by `backend/agent/tool_registry.py` and matched against a strict whitelist:

| Tool Name | Parameters | Responsibility |
|---|---|---|
| `search_contract` | `query: str`, `contract_name: Optional[str]`, `top_k: int` | Executes Version 2 Hybrid Retrieval + Cross-Encoder reranking over contract clauses. |
| `get_clause` | `contract_name: str`, `clause_id: str` | Retrieves full unclipped verbatim text and metadata for a specific clause number or ID. |
| `search_statutes` | `query: str`, `jurisdiction: Optional[str]` | Queries Indian Contract Act 1872, UK UCTA 1977, and US UCC § 2-719 provisions. |
| `search_cases` | `query: str`, `jurisdiction: Optional[str]` | Queries CourtListener API for US Federal and Appellate court opinions. |
| `compare_contracts` | `contract_a: str`, `contract_b: str`, `topic: Optional[str]` | Executes semantic side-by-side comparison across agreements. |

---

## 4. Citation & Evidence Verification

After generation, `backend/agent/verifier.py` executes an independent verification check:
1. **Clause Number Validation**: Parses all cited clause numbers (e.g. `Clause 4`, `Section 9`) and verifies that each clause was actually present in the agent's collected `EvidenceItem` list.
2. **Text Correspondence**: Checks that the cited provisions match the retrieved text.
3. **Statutory Reference Grounding**: Checks that cited external statutes (e.g. `Section 27 Indian Contract Act`) were actually retrieved during tool execution.
4. **Precision Calculation**: Calculates `citation_precision = valid_citations / total_citations`.
5. **Auditable Warnings**: Flags any clause or statute cited by the model that did not exist in retrieved evidence.
