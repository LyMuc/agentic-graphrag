"""ConversationOrchestrator — lớp điều phối phiên (deterministic, KHÔNG có LLM).

Biến thể *external state management* (LangChain): bọc Router stateless bằng một
lớp xác định giữ ``session_history`` / ``retrieval_memory`` / ``conversation_anchors``
và gọi Router/Synthesizer theo lifecycle cố định. Lớp này KHÔNG kế thừa ``Agent``
và KHÔNG có thuộc tính ``llm``; mọi suy luận ngôn ngữ nằm ở RouterAgent /
RetrieverAgent / SynthesizerAgent.

Tách từ ``presentation/main.py`` trong Phase 4 refactor (3 hook Chainlit:
``on_chat_start`` / ``on_chat_resume`` / ``on_message``).
"""
from __future__ import annotations

import os
from typing import Any

import chainlit as cl

from server.agents.router.agent import RouterAgent
from server.agents.router.tool_factory import build_presentation_tools
from server.agents.synthesizer.agent import SynthesizerAgent
from server.conversation.history import (
    RESPONSE_HISTORY_MAX_TOKENS,
    ROUTER_HISTORY_MAX_TOKENS,
    build_working_history,
)
from server.conversation.memory import (
    build_turn_anchor,
    create_retrieval_memory_entries,
    current_kg_version,
    restore_conversation_state,
)
from server.domain.legal.bundle import process_context_strings
from server.domain.legal.warnings import build_legal_warning_metadata
from server.infrastructure.viz.graph_viz import collect_viz_links

import uuid


class ConversationOrchestrator:
    """Điều phối một lượt hội thoại: build history → route → update memory →
    synthesize → viz footer → ghi session. Stateful nhưng deterministic.

    Aggregate (composition) một ``RouterAgent`` và một ``SynthesizerAgent``.
    """

    def __init__(
        self,
        *,
        router: RouterAgent,
        synthesizer: SynthesizerAgent,
        tools: dict[str, Any] | None = None,
    ):
        self.router = router
        self.synthesizer = synthesizer
        self.tools = tools if tools is not None else build_presentation_tools()

    # ------------------------------------------------------------------ hooks
    async def on_chat_start(self) -> None:
        """Khởi tạo state hội thoại rỗng + lời chào cho phiên mới."""
        cl.user_session.set("session_history", [])
        cl.user_session.set("retrieval_memory", {})
        cl.user_session.set("conversation_anchors", [])

        user = cl.user_session.get("user")
        name = user.metadata.get("name") if user and user.metadata else "bạn"
        if user and user.metadata.get("auth_mode") == "guest":
            name = "bạn"

        await cl.Message(
            content=(
                f"Chào {name}, tôi là trợ lý ảo về Luật Hôn nhân và Gia đình Việt Nam. "
                "Tôi có thể giúp gì cho bạn?"
            )
        ).send()

    async def on_chat_resume(self, thread: Any) -> None:
        """Khôi phục lịch sử, retrieval memory và anchor lượt cũ từ thread."""
        steps = thread.get("steps", [])
        session_history, retrieval_memory, anchors = restore_conversation_state(steps)
        cl.user_session.set("session_history", session_history)
        cl.user_session.set("retrieval_memory", retrieval_memory)
        cl.user_session.set("conversation_anchors", anchors)

    # --------------------------------------------------------------- internals
    def _viz_footer(self, tool_response: list) -> str:
        """Build Markdown visualization links from retriever results."""
        base = os.environ.get("VIZ_BASE_URL", "").rstrip("/")
        links = collect_viz_links(tool_response)
        if not links:
            return ""
        parts = []
        for viz_id, retriever_name, _ in links:
            href = f"{base}/viz/{viz_id}" if base else f"/viz/{viz_id}"
            parts.append(f"[Link visualize đồ thị tri thức — {retriever_name}]({href})")
        return "\n\n" + "\n".join(parts)

    async def _route_with_optional_steps(
        self,
        updated_question: str,
        router_history: list[dict[str, str]],
        retrieval_memory: dict[str, dict[str, Any]],
        conversation_anchors: list[dict[str, Any]],
        *,
        turn_id: str,
        thread_id: str,
        kg_version: str,
    ) -> tuple[list[Any], Any, dict[str, Any]]:
        async def _route_and_update_memory() -> tuple[list[Any], Any, dict[str, Any]]:
            tool_response, router_policy = await self.router.run(
                updated_question,
                self.tools,
                router_history,
                retrieval_memory=retrieval_memory,
                thread_id=thread_id,
                kg_version=kg_version,
            )
            new_memory_entries = create_retrieval_memory_entries(
                tool_response,
                turn_id=turn_id,
                thread_id=thread_id,
                kg_version=kg_version,
            )
            for entry in new_memory_entries:
                retrieval_memory[entry["context_ref"]] = entry
            turn_anchor = build_turn_anchor(
                turn_id=turn_id,
                tool_response=tool_response,
                new_memory_entries=new_memory_entries,
            )
            if turn_anchor:
                conversation_anchors.append(turn_anchor)
            cl.user_session.set("retrieval_memory", retrieval_memory)
            cl.user_session.set("conversation_anchors", conversation_anchors)
            metadata = {
                "retrieval_memory_entries": new_memory_entries,
                "turn_anchor": turn_anchor,
                "kg_version": kg_version,
            }
            return tool_response, router_policy, metadata

        async with cl.Step(name="Luồng truy xuất ngữ cảnh") as p_step:
            async with cl.Step(name="Router Agent", type="tool") as step2:
                step2.input = f'Router Input: "{updated_question}"'
                tool_response, router_policy, metadata = await _route_and_update_memory()
                step2.metadata = {
                    "tool_response": tool_response,
                    **metadata,
                }
                step2.output = "Retriever cuối cùng đã chạy xong."
            p_step.output = "Hoàn tất truy xuất ngữ cảnh pháp lý."
        return tool_response, router_policy, metadata

    async def _stream_answer(
        self,
        llm_messages: list[dict[str, str]],
        contexts_text_for_llm: str,
        msg: "cl.Message",
    ) -> str:
        llm_response = ""
        async with cl.Step(name="Tổng hợp đáp án", type="llm") as ans_step:
            ans_step.input = "Context:\n" + contexts_text_for_llm
            async for token in self.synthesizer.stream(llm_messages):
                llm_response += token
                await msg.stream_token(token)
            ans_step.output = llm_response
        return llm_response

    # ----------------------------------------------------------------- message
    async def on_message(self, message: "cl.Message") -> None:
        """Xử lý một tin nhắn người dùng: route → retrieve → tổng hợp đáp án."""
        input_text = message.content
        session_history = cl.user_session.get("session_history") or []
        retrieval_memory = cl.user_session.get("retrieval_memory") or {}
        conversation_anchors = cl.user_session.get("conversation_anchors") or []
        turn_id = uuid.uuid4().hex
        thread_id = str(getattr(message, "thread_id", "") or "")
        kg_version = current_kg_version()
        router_history = build_working_history(
            session_history,
            conversation_anchors,
            current_query=input_text,
            max_tokens=ROUTER_HISTORY_MAX_TOKENS,
        )

        updated_question = input_text
        tool_response, _router_policy, routing_metadata = await self._route_with_optional_steps(
            updated_question,
            router_history,
            retrieval_memory,
            conversation_anchors,
            turn_id=turn_id,
            thread_id=thread_id,
            kg_version=kg_version,
        )

        contexts_for_llm: list[Any] = []
        for res in tool_response:
            if isinstance(res, dict) and "contexts" in res:
                contexts_for_llm.extend(res["contexts"])
            elif isinstance(res, list):
                contexts_for_llm.extend(str(item) for item in res if item is not None)
            else:
                contexts_for_llm.append(res)

        # Chỉ bỏ qua LLM khi tool trả thẳng 1 chuỗi (vd `respond` / answer_given).
        # Retriever trả list[str] sau khi extend vẫn phải qua bước tổng hợp đáp án.
        if (
            len(tool_response) == 1
            and isinstance(tool_response[0], str)
            and not any(isinstance(res, dict) and "contexts" in res for res in tool_response)
        ):
            direct_answer = tool_response[0]
            viz_extra = self._viz_footer(tool_response)
            msg = cl.Message(content=direct_answer + viz_extra)
            if routing_metadata.get("retrieval_memory_entries") or routing_metadata.get("turn_anchor"):
                msg.metadata = routing_metadata
            await msg.send()
            session_history.append({"role": "user", "content": input_text})
            session_history.append({"role": "assistant", "content": direct_answer + viz_extra})
            cl.user_session.set("session_history", session_history)
            return

        context_pipeline = process_context_strings(contexts_for_llm)
        contexts_text_for_llm = context_pipeline.rendered_text
        legal_warnings = build_legal_warning_metadata(context_pipeline.bundles)
        resolved_queries = [
            str(res.get("resolved_query"))
            for res in tool_response
            if isinstance(res, dict) and res.get("resolved_query")
        ]
        resolved_question = " | ".join(dict.fromkeys(resolved_queries)) or input_text

        response_history = build_working_history(
            session_history,
            conversation_anchors,
            current_query=resolved_question,
            max_tokens=RESPONSE_HISTORY_MAX_TOKENS,
        )

        llm_messages = self.synthesizer.build_messages(
            response_history,
            contexts_text_for_llm,
            input_text=input_text,
            resolved_question=resolved_question,
        )
        msg = cl.Message(content="")
        llm_response = await self._stream_answer(llm_messages, contexts_text_for_llm, msg)

        viz_extra = self._viz_footer(tool_response)
        if viz_extra:
            llm_response += viz_extra
            await msg.stream_token(viz_extra)

        if routing_metadata.get("retrieval_memory_entries") or routing_metadata.get("turn_anchor") or legal_warnings:
            msg.metadata = dict(routing_metadata or {})
            if legal_warnings:
                msg.metadata["legal_warnings"] = legal_warnings
        await msg.update()

        session_history.append({"role": "user", "content": input_text})
        session_history.append({"role": "assistant", "content": llm_response})
        cl.user_session.set("session_history", session_history)
