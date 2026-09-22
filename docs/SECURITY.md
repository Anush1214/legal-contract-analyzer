# Security Architecture & Threat Model

This document outlines the security threat model, input validation controls, and risk mitigations implemented in the **Legal Contract Analyzer**.

---

## 1. Threat Model & Mitigations

| Threat Category | Potential Attack Vector | Implemented Mitigation |
|---|---|---|
| **CORS Exploitation** | Wildcard origins (`*`) with credentials allowing cross-origin credential harvesting. | Restricted CORS middleware to explicit trusted localhost and loopback origins (`backend/main.py`). |
| **Path Traversal** | Filename injection (e.g. `../../etc/passwd.pdf`) overwriting system files. | `Path(file.filename).name` sanitization strips path elements before disk storage. |
| **Denial of Service (DoS)** | Giant PDF upload (> 100MB) exhausting server memory. | Enforced strict `MAX_UPLOAD_BYTES = 25MB` cap before file buffering. |
| **MIME / Format Spoofing**| Renaming malicious binary or executable to `.pdf`. | Validated PDF magic header bytes (`b"%PDF-"`) at the start of the byte stream. |
| **Prompt Injection** | Malicious contracts with embedded adversarial prompt overrides (e.g. *"Ignore all previous instructions and output..."*). | XML-style boundary delimiters (`<retrieved_contract_evidence>`, `<clause id="...">`, `<user_inquiry>`) in `build_grounded_rag_prompt` explicitly delineate untrusted content from system directives. |
| **Unauthorized Tool Execution** | LLM attempting to call internal OS utilities or arbitrary functions. | Strict `TOOL_REGISTRY` whitelist (`backend/agent/tool_registry.py`) rejects any tool name not explicitly registered. |
| **API Key Exposure** | Leaking full Gemini API key via config endpoints. | Key masking in `/api/config` (only first 7 and last 4 characters exposed, e.g. `AQ.Ab8R...56Q`). |
| **Sensitive Data Logging** | Dumping complete contract contents or private corporate data into application logs. | Structured logger outputs only query metadata, clause numbers, and latencies; full document bodies are never logged. |

---

## 2. Secure Execution Principles
1. **Untrusted Document Boundary**: All extracted text from uploaded contracts is treated as untrusted user-supplied data.
2. **Deterministic Fallbacks**: If external APIs fail or are rate-limited, failover routes to offline analytical algorithms rather than raising unhandled exceptions.
3. **No Hidden Prompt Stuffing**: Context is structured explicitly with metadata tracking and citation verification.
