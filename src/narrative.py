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

from src import llm
from src.feedback import class_analysis
from src.models import EvaluationReport

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
