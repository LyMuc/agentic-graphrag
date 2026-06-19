from __future__ import annotations

from typing import Any

import chainlit as cl

from adapter.comparison_llm import comparison_is_enabled
from application.comparison.schemas import ComparisonInput, ComparisonResult, CriterionComparison

COMPARE_ACTION_NAME = "compare_baselines"

_WINNER_LABELS = {
    "app": "Chatbot đồ án (GraphRAG)",
    "gpt": "ChatGPT baseline",
    "gemini": "Gemini baseline",
    "tie": "Ngang bằng",
    "unclear": "Không rõ",
}


def build_compare_action(compare_id: str) -> cl.Action:
    return cl.Action(
        name=COMPARE_ACTION_NAME,
        label="Xem so sánh",
        icon="scale",
        tooltip="So sánh với LLM khác (Gemini; ChatGPT khi bật OpenAI)",
        payload={"compare_id": compare_id},
    )


def stash_comparison_data(compare_id: str, question: str, app_answer: str) -> None:
    store: dict[str, Any] = cl.user_session.get("comparison_store") or {}
    store[compare_id] = {
        "question": question,
        "app_answer": app_answer,
    }
    cl.user_session.set("comparison_store", store)


def _get_comparison_data(compare_id: str) -> dict[str, Any] | None:
    store: dict[str, Any] = cl.user_session.get("comparison_store") or {}
    return store.get(compare_id)


def _get_cached_result(compare_id: str) -> ComparisonResult | None:
    results: dict[str, Any] = cl.user_session.get("comparison_results") or {}
    raw = results.get(compare_id)
    if raw is None:
        return None
    if isinstance(raw, ComparisonResult):
        return raw
    return ComparisonResult.model_validate(raw)


def _cache_result(compare_id: str, result: ComparisonResult) -> None:
    results: dict[str, Any] = cl.user_session.get("comparison_results") or {}
    results[compare_id] = result
    cl.user_session.set("comparison_results", results)


def _format_criterion(title: str, criterion: CriterionComparison) -> str:
    best = _WINNER_LABELS.get(criterion.best, criterion.best)
    return (
        f"### {title}\n"
        f"- **Tốt hơn:** {best}\n"
        f"- **App:** {criterion.app_note}\n"
        f"- **ChatGPT:** {criterion.gpt_note}\n"
        f"- **Gemini:** {criterion.gemini_note}\n"
        f"- **So sánh:** {criterion.comparison_vi}\n"
    )


def format_comparison_markdown(result: ComparisonResult) -> str:
    verdict = result.verdict
    overall = _WINNER_LABELS.get(verdict.winner_overall, verdict.winner_overall)

    parts = [
        "## Kết quả so sánh câu trả lời",
        f"**Đánh giá tổng thể:** {overall}",
        "",
        verdict.summary_vi,
        "",
    ]

    if result.openai_baseline_note:
        parts.extend([f"_{result.openai_baseline_note}_", ""])

    parts.append(_format_criterion("1. Chi tiết điều khoản luật áp dụng", verdict.citation_detail))
    parts.append(_format_criterion("2. Thời hạn hiệu lực và cảnh báo", verdict.validity_warnings))
    parts.append(_format_criterion("3. Giải đáp vấn đề người dùng", verdict.problem_accuracy))

    parts.append(
        "\n_Câu trả lời baseline (Gemini/ChatGPT) xem trong các bước «So sánh baseline» bên sidebar._"
    )
    parts.append(
        "_Lưu ý: App dùng GraphRAG + đồ thị tri thức; baseline chỉ là LLM thuần với cùng câu hỏi._"
    )
    return "\n".join(parts)


async def attach_compare_to_message(
    msg: cl.Message,
    question: str,
    app_answer: str,
) -> None:
    if not comparison_is_enabled():
        return
    if not msg.id:
        await msg.update()
    compare_id = str(msg.id)
    stash_comparison_data(compare_id, question, app_answer)
    msg.metadata = {"compare_available": True, "compare_id": compare_id}
    msg.actions = [build_compare_action(compare_id)]
    await msg.update()


async def _run_comparison_with_steps(data: ComparisonInput) -> ComparisonResult:
    from application.comparison.baseline import fetch_gemini_baseline, fetch_openai_baseline
    from application.comparison.judge import judge_comparison
    from adapter.comparison_llm import openai_baseline_enabled

    question = data.question
    gpt_answer: str | None = None
    gemini_answer: str | None = None

    async with cl.Step(name="So sánh baseline", type="run") as parent_step:
        parent_step.input = question

        if openai_baseline_enabled():
            async with cl.Step(name="Baseline ChatGPT (OpenAI)", type="llm") as gpt_step:
                gpt_step.input = question
                gpt_answer = await fetch_openai_baseline(question)
                gpt_step.output = gpt_answer or "(Không có / tạm tắt)"

        async with cl.Step(name="Baseline Gemini", type="llm") as gem_step:
            gem_step.input = question
            gemini_answer = await fetch_gemini_baseline(question)
            gem_step.output = gemini_answer or "(Lỗi / không có)"

        if gemini_answer is None:
            raise RuntimeError("Không lấy được câu trả lời baseline từ Gemini.")

        async with cl.Step(name="LLM Judge (Gemini)", type="llm") as judge_step:
            judge_step.input = (
                f"So sánh app vs ChatGPT vs Gemini cho câu hỏi: {question[:200]}"
            )
            verdict = await judge_comparison(
                question=question,
                app_answer=data.app_answer,
                gpt_answer=gpt_answer,
                gemini_answer=gemini_answer,
            )
            judge_step.output = verdict.summary_vi

        parent_step.output = f"Winner: {verdict.winner_overall}"

    from adapter.comparison_llm import COMPARISON_USE_OPENAI

    openai_skipped = not COMPARISON_USE_OPENAI or gpt_answer is None
    openai_note = ""
    if not COMPARISON_USE_OPENAI:
        openai_note = "ChatGPT baseline tạm tắt (COMPARISON_USE_OPENAI=false / hết quota OpenAI)."
    elif gpt_answer is None:
        openai_note = "ChatGPT baseline không trả về nội dung."

    return ComparisonResult(
        question=question,
        app_answer=data.app_answer,
        gpt_answer=gpt_answer,
        gemini_answer=gemini_answer,
        verdict=verdict,
        openai_baseline_skipped=openai_skipped,
        openai_baseline_note=openai_note,
    )


async def restore_compare_actions_from_thread(steps: list[dict[str, Any]]) -> None:
    """Re-stash data and offer compare button for assistant messages after resume."""
    if not comparison_is_enabled():
        return

    for idx, step in enumerate(steps):
        if step.get("type") != "assistant_message":
            continue
        metadata = step.get("metadata") or {}
        if not metadata.get("compare_available"):
            continue

        compare_id = str(metadata.get("compare_id") or step.get("id") or "")
        if not compare_id:
            continue

        app_answer = str(step.get("output") or "").strip()
        question = ""
        for prev in reversed(steps[:idx]):
            if prev.get("type") == "user_message":
                question = str(prev.get("output") or "").strip()
                break

        if question and app_answer:
            stash_comparison_data(compare_id, question, app_answer)

        await cl.Message(
            content="Bạn có thể so sánh lại câu trả lời trên với baseline LLM:",
            actions=[build_compare_action(compare_id)],
        ).send()


@cl.action_callback(COMPARE_ACTION_NAME)
async def on_compare_baselines(action: cl.Action) -> None:
    compare_id = str((action.payload or {}).get("compare_id", ""))
    if not compare_id:
        await cl.Message(content="Không tìm thấy dữ liệu so sánh.").send()
        await cl.context.emitter.task_end()
        return

    cached = _get_cached_result(compare_id)
    if cached is not None:
        await cl.Message(content=format_comparison_markdown(cached)).send()
        await action.remove()
        await cl.context.emitter.task_end()
        return

    data = _get_comparison_data(compare_id)
    if not data:
        await cl.Message(
            content="Không còn dữ liệu so sánh trong phiên này. Vui lòng hỏi lại hoặc mở lại hội thoại."
        ).send()
        await cl.context.emitter.task_end()
        return

    await action.remove()

    status_msg = cl.Message(
        content="Đang lấy câu trả lời baseline và đánh giá (Gemini)..."
    )
    await status_msg.send()

    try:
        comparison_input = ComparisonInput(
            question=str(data["question"]),
            app_answer=str(data["app_answer"]),
        )
        result = await _run_comparison_with_steps(comparison_input)
        _cache_result(compare_id, result)
        await cl.Message(content=format_comparison_markdown(result)).send()
    except Exception as exc:
        await cl.Message(
            content=(
                "Không thể hoàn tất so sánh. "
                f"Lỗi: {exc}\n\n"
                "Kiểm tra GOOGLE_API_KEY/GEMINI_API_KEY và thử lại sau."
            )
        ).send()
    finally:
        try:
            await status_msg.remove()
        except Exception:
            pass
        await cl.context.emitter.task_end()
