# src/narrative.py
"""
Narrative layer (Phase B) - the only place a language model is used.

Two touchpoints, both strictly downstream of grading:

  1. Student:    one short "what to study next" paragraph per report.
  2. Instructor: a class briefing that answers SOP #4 -- turning evaluation
                 results into instructional recommendations.

Design rules inherited from the spec:

- The model receives STRUCTURED FINDINGS, never configuration text and never
  student names. Small input, small hallucination surface, and compliant with
  R.A. 10173.
- One generation per report, not one per checkpoint. A student with 21
  failures would otherwise need ~1,600 tokens and give the model 21
  independent chances to invent something.
- Every function falls back to deterministic text. With no model installed the
  output is still useful, which is what keeps the offline claim true.
- Nothing here can reach a score. These functions receive finished reports and
  return strings.
"""

import re

from src import llm
from src.feedback import class_analysis
from src.models import ClassChatStudent, EvaluationReport

_STUDENT_SYSTEM = (
    "You are a patient Cisco networking lab instructor writing to a student "
    "about their graded lab. Write ONE short paragraph, 3 to 4 sentences. "
    "Tell them which concept to review first and why it matters in a real "
    "network. Be encouraging but direct. Do not invent errors that are not "
    "listed. Do not mention scores, points or grades. Do not give the exact "
    "configuration commands that would fix it - name what to study instead."
)

_INSTRUCTOR_SYSTEM = (
    "You are an assistant to a Cisco Networking Academy instructor, writing a "
    "short briefing about how one class performed on a lab. Write 3 to 5 "
    "sentences. Identify the concepts the class struggled with most, and "
    "suggest one concrete instructional action. Be specific and practical. "
    "Do not invent data that is not provided. Do not name individual students."
)


def _fallback_student_summary(report: EvaluationReport) -> str:
    """Deterministic summary. Always correct, just plainer than the model's."""
    topics = report.study_topics
    if not topics:
        return (
            "Every checkpoint in this lab passed. Your addressing, interface states "
            "and topology all match the specification."
        )
    first = topics[0]
    if len(topics) == 1:
        return (
            f"Focus your review on {first.topic.lower()}. {first.why_it_matters} "
            f"This accounted for all {first.checkpoints_failed} of the checkpoints you missed."
        )
    second = topics[1]
    return (
        f"Start your review with {first.topic.lower()}, which cost the most marks in this lab. "
        f"{first.why_it_matters} After that, look at {second.topic.lower()}. "
        f"Between them they account for {first.checkpoints_failed + second.checkpoints_failed} "
        f"of the {sum(t.checkpoints_failed for t in topics)} checkpoints you missed."
    )


def _fallback_class_briefing(analysis: dict) -> str:
    """Deterministic instructor briefing."""
    total = analysis.get("submissions_analysed", 0)
    concepts = analysis.get("concepts", [])
    if not total:
        return "No submissions were analysed."
    if not concepts:
        return f"All {total} submissions passed every checkpoint. No remediation is indicated."

    lead = concepts[0]
    share = round(lead["share_of_class"] * 100)
    lines = [
        f"Across {total} submissions, the most widespread difficulty was "
        f"{lead['topic'].lower()}, affecting {lead['students_affected']} students ({share}% of the class). "
        f"{lead['why_it_matters']}"
    ]
    if len(concepts) > 1:
        others = ", ".join(
            f"{c['topic'].lower()} ({c['students_affected']})" for c in concepts[1:4]
        )
        lines.append(f"Also affecting multiple students: {others}.")
    lines.append(
        f"Consider revisiting {lead['topic'].lower()} before the next laboratory session."
    )
    return " ".join(lines)


def student_summary(report: EvaluationReport) -> dict:
    """
    A short "what to study next" paragraph for one student.

    Returns {"text", "source"} where source is "model" or "template", so the
    UI and any study of feedback reliability can tell the two apart.
    """
    fallback = _fallback_student_summary(report)
    if not report.study_topics:
        return {"text": fallback, "source": "template"}

    findings = [
        {
            "concept": topic.topic,
            "why_it_matters": topic.why_it_matters,
            "checkpoints_missed": topic.checkpoints_failed,
        }
        for topic in report.study_topics[:5]
    ]
    prompt = (
        "A student completed a Cisco Packet Tracer lab. These are the concepts "
        "they missed, most important first:\n\n"
        + "\n".join(
            f"- {f['concept']}: missed {f['checkpoints_missed']} checkpoint(s). {f['why_it_matters']}"
            for f in findings
        )
        + "\n\nWrite the paragraph."
    )

    # Strip here as well as in the client: a whitespace-only reply is a
    # failure, and narrative must not depend on the client to notice.
    text = (llm.generate(prompt, system=_STUDENT_SYSTEM, max_tokens=220) or "").strip()
    if not text:
        return {"text": fallback, "source": "template"}
    return {"text": text, "source": "model"}


def class_briefing(categories_per_student: list[list[str]]) -> dict:
    """
    Instructor-facing analysis of a whole class (SOP #4).

    Input is one list of failed rule categories per student -- no names, no
    configurations, no scores. The deterministic aggregate is always returned;
    the narrative is model-written when available and templated otherwise.
    """
    analysis = class_analysis([], categories_per_student)
    fallback = _fallback_class_briefing(analysis)

    concepts = analysis.get("concepts", [])
    total = analysis.get("submissions_analysed", 0)
    if not concepts or not total:
        return {"analysis": analysis, "briefing": fallback, "source": "template"}

    prompt = (
        f"A class of {total} students submitted a Cisco networking lab. "
        "These concepts were missed, with the number of students affected:\n\n"
        + "\n".join(
            f"- {c['topic']}: {c['students_affected']} of {total} students. {c['why_it_matters']}"
            for c in concepts[:6]
        )
        + "\n\nWrite the briefing."
    )

    text = (llm.generate(prompt, system=_INSTRUCTOR_SYSTEM, max_tokens=320) or "").strip()
    if not text:
        return {"analysis": analysis, "briefing": fallback, "source": "template"}
    return {"analysis": analysis, "briefing": text, "source": "model"}


# --------------------------------------------------------------------------
# Follow-up chat
#
# Same boundary as the paragraphs above: the model sees findings that grading
# already produced, never a score it could change. The student chat carries no
# name. The instructor's class chat does carry names and scores (see
# class_chat) -- it is instructor-only and the model is local.
# Unlike the paragraphs there is no template fallback -- a canned answer to a
# free-form question would be exactly the "premade AI" this layer must not
# pretend to be. When the model is unavailable the caller says so.
# --------------------------------------------------------------------------

MAX_CHAT_TURNS = 12          # messages of history sent to the model
MAX_CHAT_MESSAGE_CHARS = 1000
MAX_FINDINGS_IN_CONTEXT = 30

_STUDENT_CHAT_SYSTEM = (
    "You are a patient Cisco networking lab tutor. A student is asking follow-up "
    "questions about their graded Packet Tracer lab. The findings below were "
    "produced by an automated grader and are final: you cannot change the grade, "
    "and if the student disputes a result, tell them to raise it with their "
    "instructor. Answer only questions about this lab and the networking concepts "
    "behind it; politely decline anything else. Base every statement about their "
    "work on the findings listed -- never invent an error. Explain concepts and "
    "which show commands would help them check their work, but do not write out "
    "the complete configuration that would fix the lab for them. Keep answers "
    "short: a few sentences, or a short list when steps help."
)

_CLASS_CHAT_SYSTEM = (
    "You are an assistant to a Cisco Networking Academy instructor, answering "
    "follow-up questions about how their class performed on one lab. You have the "
    "class results table below, including student names; it is private to the "
    "instructor. The ranking, the lowest and highest scores, and the list of "
    "students per concept are already computed -- read them from the table, never "
    "recompute or estimate numbers. Answer only from the table; if a question needs "
    "information it does not contain, say what is missing. Do not speculate about "
    "a student's effort, ability or character. Give practical teaching suggestions "
    "when asked. Keep answers concise."
)


def clean_chat_messages(messages: list) -> list[dict]:
    """
    Normalise client-supplied history: user/assistant roles only, strings only,
    each message capped, only the most recent turns kept. The caller must still
    check the result ends with a user message.
    """
    cleaned = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        content = content.strip()[:MAX_CHAT_MESSAGE_CHARS]
        if content:
            cleaned.append({"role": role, "content": content})
    return cleaned[-MAX_CHAT_TURNS:]


def _report_context(report: EvaluationReport) -> str:
    missed = [r for r in report.results if not r.passed]
    lines = [
        f"Lab: {report.lab_title}",
        f"Checkpoints: {report.passed_count} passed, {report.failed_count} missed.",
    ]
    if report.study_topics:
        lines.append("\nConcepts missed, most costly first:")
        lines += [
            f"- {t.topic}: {t.checkpoints_failed} checkpoint(s). {t.why_it_matters}"
            for t in report.study_topics
        ]
    if missed:
        lines.append("\nMissed checkpoints:")
        for r in missed[:MAX_FINDINGS_IN_CONTEXT]:
            where = r.target_device + (f" {r.target_interface}" if r.target_interface else "")
            found = f" Found: {r.actual_value}." if r.actual_value else ""
            lines.append(f"- [{where}] {r.description}. {r.feedback}{found}")
        if len(missed) > MAX_FINDINGS_IN_CONTEXT:
            lines.append(f"- ...and {len(missed) - MAX_FINDINGS_IN_CONTEXT} more.")
    else:
        lines.append("\nEvery checkpoint passed.")
    return "\n".join(lines)


MAX_STUDENTS_IN_CONTEXT = 120
_NAME_MAX_CHARS = 80


def _clean_name(name: str) -> str:
    """Names come from filenames: keep them to one short, printable line."""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(name)).strip()[:_NAME_MAX_CHARS] or "(unnamed)"


def _class_context(students: list[ClassChatStudent]) -> str:
    """
    The class table as the model sees it. Everything a question could hinge on
    -- rank, lowest, highest, average, who missed which concept -- is computed
    here, because a 3B model is unreliable at comparing numbers. The model's
    job is to read and explain, not to calculate.
    """
    students = students[:MAX_STUDENTS_IN_CONTEXT]
    graded = [s for s in students if s.status == "graded"]
    failed_to_grade = [s for s in students if s.status != "graded"]

    lines = [f"{len(students)} submissions: {len(graded)} graded, {len(failed_to_grade)} could not be graded."]
    if graded:
        ranked = sorted(graded, key=lambda s: (s.percentage, _clean_name(s.name).lower()))
        low, high = ranked[0].percentage, ranked[-1].percentage
        average = round(sum(s.percentage for s in graded) / len(graded), 1)
        lowest = [_clean_name(s.name) for s in ranked if s.percentage == low]
        highest = [_clean_name(s.name) for s in ranked if s.percentage == high]
        lines += [
            f"Class average: {average}%.",
            f"LOWEST score: {low}% -- {'; '.join(lowest)}.",
            f"HIGHEST score: {high}% -- {'; '.join(highest)}.",
            "",
            "Results, lowest to highest (rank. name: percentage, grade, score, checkpoints missed; concepts missed):",
        ]
        for rank, s in enumerate(ranked, 1):
            topics = ", ".join(s.topics) or "none"
            lines.append(
                f"{rank}. {_clean_name(s.name)}: {s.percentage}%, grade {s.grade_letter}, "
                f"{s.total_score}/{s.max_score}, {s.failed_count} missed; concepts missed: {topics}"
            )

        by_topic: dict[str, list[str]] = {}
        for s in ranked:
            for topic in s.topics:
                by_topic.setdefault(topic, []).append(_clean_name(s.name))
        if by_topic:
            lines += ["", "Students per concept missed (most widespread first):"]
            for topic, names in sorted(by_topic.items(), key=lambda kv: (-len(kv[1]), kv[0])):
                lines.append(f"- {topic}: {len(names)} of {len(graded)} -- {'; '.join(names)}")

    if failed_to_grade:
        lines += ["", "Could not be graded (file unreadable; no score):"]
        lines += [f"- {_clean_name(s.name)}: {s.status}" for s in failed_to_grade]
    return "\n".join(lines)


FINDINGS_MARKER = "=== GRADED FINDINGS ==="


def _chat(system: str, context: str, messages: list[dict]) -> str | None:
    """
    The findings are attached to the LATEST question, every turn, rather than
    placed in the system prompt. Measured on llama3.2:3b with a two-turn
    class chat: findings in the system prompt were misread on the follow-up
    7-9 times in 20 ("neither student missed OSPF" when both had); findings
    next to the question were read correctly 20/20. Being rebuilt on every
    request, they also cannot be lost to history trimming.
    """
    *history, question = messages
    grounded = {"role": "user", "content": f"{FINDINGS_MARKER}\n{context}\n\nQuestion: {question['content']}"}
    return llm.chat(history + [grounded], system=system, max_tokens=400)


def report_chat(report: EvaluationReport, messages: list[dict]) -> str | None:
    """Answer a student's follow-up question about their own report."""
    return _chat(_STUDENT_CHAT_SYSTEM, _report_context(report), messages)


def class_chat(students: list[ClassChatStudent], messages: list[dict]) -> str | None:
    """
    Answer an instructor's follow-up question about the class results.

    Unlike the briefing, this sees student names and scores. That is
    deliberate: the model runs on the instructor's own computer, only the
    instructor can reach this endpoint, and nothing leaves the machine.
    """
    return _chat(_CLASS_CHAT_SYSTEM, _class_context(students), messages)
