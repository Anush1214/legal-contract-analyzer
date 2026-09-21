import time
import logging
from typing import Dict, Any, Optional

from backend.config import get_gemini_api_key, LLM_MODEL, MAX_AGENT_STEPS
from backend.agent.state import AgentState, EvidenceItem, ToolCallRecord
from backend.agent.tool_registry import get_whitelisted_tools, execute_tool, is_tool_allowed
from backend.agent.verifier import verify_citations
from backend.agent.prompts import AGENT_SYSTEM_PROMPT, build_agent_synthesis_prompt

logger = logging.getLogger("agent.orchestrator")

def run_agent_analysis(
    question: str,
    contract_name: Optional[str] = None,
    max_steps: int = MAX_AGENT_STEPS
) -> Dict[str, Any]:
    """
    Version 3: Controlled Agentic RAG Execution Loop.
    Executes a bounded reasoning loop with Google GenAI tool calling, evidence accumulation,
    and post-generation citation verification.
    """
    start_total_time = time.time()
    state = AgentState(
        user_query=question,
        contract_name=contract_name,
        max_steps=max_steps
    )

    api_key = get_gemini_api_key()
    if not api_key or api_key.startswith("demo_"):
        # Graceful analytical agent execution for offline / demo mode
        return _run_offline_agent_flow(state)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        tools = get_whitelisted_tools()

        config = types.GenerateContentConfig(
            system_instruction=AGENT_SYSTEM_PROMPT,
            temperature=0.1,
            tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )

        chat = client.chats.create(model=LLM_MODEL, config=config)

        # Initial prompt to the agent
        initial_msg = (
            f"Please research the following inquiry regarding contract '{contract_name or 'the loaded contract'}':\n"
            f"\"{question}\"\n\n"
            f"Select appropriate tools to inspect the contract and relevant legal frameworks."
        )

        response = chat.send_message(initial_msg)

        while state.step_count < state.max_steps:
            state.step_count += 1
            step_num = state.step_count

            # Check if model selected tool calls
            function_calls = getattr(response, "function_calls", None)
            if not function_calls:
                # No more tools requested; model produced final synthesis
                if response.text:
                    state.final_answer = response.text
                break

            # Execute tool calls for this step
            tool_responses = []
            for call in function_calls:
                tool_name = call.name
                tool_args = dict(call.args) if call.args else {}

                # Default contract_name if omitted by model
                if "contract_name" in tool_args and not tool_args["contract_name"] and contract_name:
                    tool_args["contract_name"] = contract_name

                logger.info(f"[Agent Step {step_num}] Invoking tool: {tool_name}({tool_args})")
                t_tool_start = time.time()
                tool_output = execute_tool(tool_name, tool_args)
                tool_latency = time.time() - t_tool_start

                # Parse tool output into state evidence
                new_evidence_count = _ingest_tool_output(state, tool_name, tool_args, tool_output)

                summary_str = f"Returned {new_evidence_count} evidence item(s)" if "error" not in tool_output else f"Error: {tool_output['error']}"
                state.tool_call_history.append(
                    ToolCallRecord(
                        step=step_num,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        output_summary=summary_str,
                        latency_seconds=tool_latency,
                        success="error" not in tool_output,
                        num_evidence_items=new_evidence_count
                    )
                )

                tool_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"result": tool_output}
                    )
                )

            # Send function execution results back to the conversation
            response = chat.send_message(tool_responses)

        # If loop reached max steps without final answer, synthesize from collected evidence
        if not state.final_answer:
            if response and response.text:
                state.final_answer = response.text
            else:
                synthesis_prompt = build_agent_synthesis_prompt(
                    query=question,
                    contract_name=contract_name or "Contract",
                    state_evidence=state.evidence
                )
                final_res = client.models.generate_content(
                    model=LLM_MODEL,
                    contents=synthesis_prompt
                )
                state.final_answer = final_res.text if final_res else "Analysis could not be completed within step bounds."

    except Exception as e:
        logger.error(f"Agent execution encountered an error: {e}", exc_info=True)
        state.errors.append(str(e))
        return _run_offline_agent_flow(state)

    # Post-Execution: Evidence Policy Check & Abstention
    contract_evidence = state.get_contract_evidence()
    if not contract_evidence:
        state.abstained = True
        state.abstention_reason = "No relevant contract clauses were discovered by the research agent."
        state.final_answer = (
            f"### Insufficient Evidence Found (Agent Abstention)\n\n"
            f"The research agent searched '{contract_name or 'the contract'}' but could not identify clauses relevant to: *\"{question}\"*.\n\n"
            f"> **Policy Enforcement**: The system will not generate speculative legal conclusions when zero contract evidence was retrieved.\n\n"
            f"*Tools executed: {[t.tool_name for t in state.tool_call_history]}*"
        )

    # Post-Execution: Citation Verification
    if state.final_answer and not state.abstained:
        state.verification_result = verify_citations(state.final_answer, state)

    total_latency = time.time() - start_total_time

    return {
        "version": "v3",
        "answer": state.final_answer,
        "clauses_referenced": [f"Clause {e.metadata.get('clause_number', '?')} from {e.contract_name}" for e in contract_evidence],
        "legal_precedents": [e.source_identifier for e in state.get_external_evidence()],
        "agent_trace": state.to_trace_summary(),
        "verification": state.verification_result,
        "retrieval": {
            "method": "controlled_agentic_rag",
            "results": [e.to_dict() for e in state.evidence],
            "abstained": state.abstained
        },
        "system": {
            "total_latency": round(total_latency, 4),
            "steps": state.step_count,
            "tool_calls_count": len(state.tool_call_history)
        }
    }

def _ingest_tool_output(state: AgentState, tool_name: str, args: Dict[str, Any], output: Dict[str, Any]) -> int:
    """Normalize tool return values into structured EvidenceItem records in state."""
    count = 0
    if "clauses" in output:
        for c in output["clauses"]:
            state.add_evidence(
                EvidenceItem(
                    source_type="contract",
                    source_identifier=f"Clause {c.get('clause_number', '?')}",
                    title=c.get("title", ""),
                    content=c.get("text", ""),
                    contract_name=c.get("contract", state.contract_name),
                    page=c.get("page", 1),
                    confidence_score=c.get("rerank_score") or c.get("retrieval_score", 1.0),
                    metadata={"clause_number": c.get("clause_number"), "category": c.get("category")}
                )
            )
            count += 1
    elif "found" in output and output["found"]:
        state.add_evidence(
            EvidenceItem(
                source_type="contract",
                source_identifier=f"Clause {output.get('clause_number', '?')}",
                title=output.get("title", ""),
                content=output.get("text", ""),
                contract_name=output.get("contract", state.contract_name),
                page=output.get("page", 1),
                confidence_score=1.0,
                metadata={"clause_number": output.get("clause_number"), "category": output.get("category")}
            )
        )
        count += 1
    elif "results" in output:
        for item in output["results"]:
            state.add_evidence(
                EvidenceItem(
                    source_type="statute",
                    source_identifier=item.get("source", "Statute"),
                    title=item.get("topic", item.get("jurisdiction", "")),
                    content=item.get("summary", ""),
                    confidence_score=1.0,
                    metadata={"jurisdiction": item.get("jurisdiction")}
                )
            )
            count += 1
    elif "cases" in output:
        for item in output["cases"]:
            state.add_evidence(
                EvidenceItem(
                    source_type="case",
                    source_identifier=item.get("source", "Case Law"),
                    title=item.get("court", "Appellate Court"),
                    content=item.get("summary", ""),
                    confidence_score=1.0,
                    metadata={"jurisdiction": item.get("jurisdiction", "United States")}
                )
            )
            count += 1
    return count

def _run_offline_agent_flow(state: AgentState) -> Dict[str, Any]:
    """Deterministic fallback for offline or unauthenticated testing."""
    t_start = time.time()
    state.step_count = 2

    # Step 1: Search contract
    tool_out_1 = execute_tool("search_contract", {"query": state.user_query, "contract_name": state.contract_name, "top_k": 3})
    _ingest_tool_output(state, "search_contract", {"query": state.user_query}, tool_out_1)
    state.tool_call_history.append(
        ToolCallRecord(1, "search_contract", {"query": state.user_query}, "Fallback search executed", 0.05, True, len(state.evidence))
    )

    # Step 2: Search statutes
    tool_out_2 = execute_tool("search_statutes", {"query": state.user_query, "jurisdiction": "all"})
    _ingest_tool_output(state, "search_statutes", {"query": state.user_query}, tool_out_2)
    state.tool_call_history.append(
        ToolCallRecord(2, "search_statutes", {"query": state.user_query}, "Statutes checked", 0.02, True, len(state.evidence))
    )

    c_ev = state.get_contract_evidence()
    ext_ev = state.get_external_evidence()

    if not c_ev:
        state.abstained = True
        state.final_answer = "No relevant clauses found in contract evidence (Offline Agent Mode)."
    else:
        state.final_answer = (
            f"### Controlled Agent Synthesis (Analytical Offline Mode)\n\n"
            f"**Target Inquiry**: *\"{state.user_query}\"*\n\n"
            f"**Contract Findings:**\n"
            + "\n".join([f"- **Clause {e.metadata.get('clause_number')} ({e.title})**: {e.content[:200]}..." for e in c_ev])
            + "\n\n**Statutory Frameworks:**\n"
            + "\n".join([f"- **{e.source_identifier}**: {e.content[:180]}..." for e in ext_ev])
        )

    state.verification_result = verify_citations(state.final_answer, state)

    return {
        "version": "v3",
        "answer": state.final_answer,
        "clauses_referenced": [f"Clause {e.metadata.get('clause_number', '?')} from {e.contract_name}" for e in c_ev],
        "legal_precedents": [e.source_identifier for e in ext_ev],
        "agent_trace": state.to_trace_summary(),
        "verification": state.verification_result,
        "retrieval": {
            "method": "controlled_agentic_rag_offline",
            "results": [e.to_dict() for e in state.evidence],
            "abstained": state.abstained
        },
        "system": {
            "total_latency": round(time.time() - t_start, 4),
            "steps": 2,
            "tool_calls_count": 2
        }
    }
