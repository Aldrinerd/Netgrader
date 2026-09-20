# validation/harness.py
"""
The measurement itself.

Answers SOP #3's three questions with numbers rather than assertion:

  ACCURACY     Of the injected faults, how many did the engine catch (recall),
               and did it flag anything the fault did not cause (false
               positives)? Reported separately, because they are not equally
               bad: a miss lets a student keep marks they did not earn, a
               false positive takes marks from a student who did the work.

  CONSISTENCY  Does the same submission score the same every time, and do two
               different-but-equally-correct submissions score the same?

  FEEDBACK     Does the guidance attached to a failed checkpoint actually
               describe the fault that was injected?

Nothing here touches src/. It drives the public grading entry points exactly
as the web app does, so what it measures is what students get.
"""

from dataclasses import dataclass, field

from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.models import EvaluationPolicies, EvaluationReport, TopologyResult
from src.parsers import parse_device_bundle
from validation.mutations import CATALOGUE, Mutation
from validation.reference import build_reference
from validation.reference_text import CLI_DEVICES, CONFIG_BUNDLES

REPEATS = 3  # how many times each submission is graded to test determinism


@dataclass
class MutationOutcome:
    mutation: Mutation
    detected: bool
    expected_categories: set
    failed_categories: set
    unexpected_categories: set
    score: float
    deterministic: bool
    guidance_ok: bool
    guidance_note: str = ""

    @property
    def passed(self) -> bool:
        """Did the engine behave correctly on this case?"""
        if self.mutation.is_negative:
            return not self.failed_categories and self.deterministic
        return self.detected and not self.unexpected_categories and self.deterministic


@dataclass
class FidelityReport:
    """
    Whether the parser preserves everything the rubric depends on.

    Every other figure in this suite is taken from constructed ParsedDevice
    objects, so the parser sits entirely outside the measurement. That blind
    spot hid a bug where the first sub-command of a `router ospf` block closed
    the block and discarded every network statement: OSPF went ungraded on any
    realistically written config while this suite reported 100%.
    """
    matched: bool
    findings: list = field(default_factory=list)
    built_score: float = 0.0
    parsed_score: float = 0.0


@dataclass
class ValidationReport:
    reference_clean: bool
    reference_score: float
    fidelity: FidelityReport = field(
        default_factory=lambda: FidelityReport(matched=True)
    )
    outcomes: list = field(default_factory=list)

    # --- SOP #3 metrics -----------------------------------------------------
    @property
    def positives(self) -> list:
        return [o for o in self.outcomes if not o.mutation.is_negative]

    @property
    def negatives(self) -> list:
        return [o for o in self.outcomes if o.mutation.is_negative]

    @property
    def recall(self) -> float:
        """Share of injected faults the engine caught."""
        return _ratio([o.detected for o in self.positives])

    @property
    def specificity(self) -> float:
        """Share of correct submissions the engine left alone."""
        return _ratio([not o.failed_categories for o in self.negatives])

    @property
    def false_positive_rate(self) -> float:
        """Share of ALL cases where the engine failed something it should not have."""
        flagged = [bool(o.unexpected_categories) or
                   (o.mutation.is_negative and bool(o.failed_categories))
                   for o in self.outcomes]
        return _ratio([not f for f in flagged])

    @property
    def consistency(self) -> float:
        return _ratio([o.deterministic for o in self.outcomes])

    @property
    def feedback_reliability(self) -> float:
        checked = [o for o in self.positives if o.mutation.expect_mentions]
        return _ratio([o.guidance_ok for o in checked])

    @property
    def all_correct(self) -> bool:
        return (self.reference_clean
                and self.fidelity.matched
                and all(o.passed for o in self.outcomes))


def _ratio(flags: list) -> float:
    if not flags:
        return 1.0
    return round(100.0 * sum(1 for f in flags if f) / len(flags), 1)


def _grade(reference: TopologyResult, student: TopologyResult,
           policies: EvaluationPolicies) -> EvaluationReport:
    criteria = generate_criteria_from_topology(reference, policies=policies)
    return evaluate_student_submission(criteria, student)


def _check_reference(policies: EvaluationPolicies) -> tuple:
    """
    The precondition everything else rests on: the worked answer must be
    achievable. A rubric its own reference cannot satisfy makes every number
    below meaningless, so this runs first and is reported first.
    """
    reference = build_reference()
    report = _grade(reference, build_reference(), policies)
    return report.percentage == 100.0, report.percentage


def build_parsed_reference() -> TopologyResult:
    """
    The reference network as the parser sees it.

    Devices with a CLI come from their config text. Hosts and cabling come
    from the constructed reference, because a PC has no CLI and link discovery
    is a separate concern with its own (much worse) error rate -- mixing it in
    here would drown the signal this check exists to produce.
    """
    built = build_reference()
    devices = {}
    for filename, text in CONFIG_BUNDLES.items():
        device = parse_device_bundle(text, filename)
        devices[device.hostname] = device
    for hostname, device in built.devices.items():
        if hostname not in CLI_DEVICES:
            devices[hostname] = device
    return TopologyResult(devices=devices, links=built.links)


def check_fidelity(policies: EvaluationPolicies | None = None) -> FidelityReport:
    """
    Grade the constructed reference and the parsed one side by side.

    They describe the same network, so they must produce the same rubric and
    the same score. A rule present in one and missing from the other is a fact
    the parser dropped, named by its rule id.
    """
    # Every policy on, so no attribute escapes the comparison by being
    # switched off: a parser gap in a feature this suite does not otherwise
    # exercise still has to surface here.
    policies = policies or EvaluationPolicies(
        grade_security_baseline=True,
        grade_interface_descriptions=True,
    )

    built = build_reference()
    parsed = build_parsed_reference()

    built_criteria = generate_criteria_from_topology(built, policies=policies)
    parsed_criteria = generate_criteria_from_topology(parsed, policies=policies)

    findings = []

    missing_devices = set(built.devices) - set(parsed.devices)
    if missing_devices:
        findings.append(
            f"parser produced no device for {sorted(missing_devices)}"
        )

    built_ids = {r.rule_id for r in built_criteria.rules}
    parsed_ids = {r.rule_id for r in parsed_criteria.rules}

    for rule_id in sorted(built_ids - parsed_ids):
        rule = next(r for r in built_criteria.rules if r.rule_id == rule_id)
        findings.append(
            f"parser lost '{rule_id}' ({rule.category}) -- {rule.description}"
        )
    for rule_id in sorted(parsed_ids - built_ids):
        rule = next(r for r in parsed_criteria.rules if r.rule_id == rule_id)
        findings.append(
            f"parser invented '{rule_id}' ({rule.category}) -- {rule.description}"
        )

    # Cross-grade: the parsed network must satisfy the constructed rubric.
    built_score = evaluate_student_submission(built_criteria, built).percentage
    parsed_score = evaluate_student_submission(built_criteria, parsed).percentage
    if parsed_score != built_score:
        failed = [
            r.rule_id for r in
            evaluate_student_submission(built_criteria, parsed).results
            if not r.passed
        ]
        findings.append(
            f"parsed network scores {parsed_score:.1f}% against the constructed "
            f"rubric, not {built_score:.1f}% -- failing {sorted(failed)}"
        )

    return FidelityReport(
        matched=not findings,
        findings=findings,
        built_score=built_score,
        parsed_score=parsed_score,
    )


def run_mutation(mutation: Mutation) -> MutationOutcome:
    reference = build_reference()
    student = build_reference()
    mutation.apply(student)

    reports = [_grade(reference, student, mutation.policies) for _ in range(REPEATS)]
    report = reports[0]
    deterministic = len({r.percentage for r in reports}) == 1

    failed = {r.category for r in report.results if not r.passed}
    expected = set(mutation.expect_categories)

    guidance_ok, note = _check_guidance(report, mutation)

    return MutationOutcome(
        mutation=mutation,
        detected=bool(expected & failed) if expected else True,
        expected_categories=expected,
        failed_categories=failed,
        unexpected_categories=failed - expected,
        score=report.percentage,
        deterministic=deterministic,
        guidance_ok=guidance_ok,
        guidance_note=note,
    )


def _check_guidance(report: EvaluationReport, mutation: Mutation) -> tuple:
    """Does the explanation name the fault that was actually injected?"""
    if not mutation.expect_mentions:
        return True, ""

    texts = " ".join(
        (r.guidance or "") + " " + (r.feedback or "")
        for r in report.results
        if not r.passed and r.category in mutation.expect_categories
    ).lower()

    if not texts.strip():
        return False, "no guidance produced for the failed checkpoint"

    missing = [m for m in mutation.expect_mentions if m.lower() not in texts]
    if missing:
        return False, f"guidance never mentions {', '.join(missing)}"
    return True, ""


def run(policies: EvaluationPolicies | None = None) -> ValidationReport:
    clean, score = _check_reference(policies or EvaluationPolicies())
    return ValidationReport(
        reference_clean=clean,
        reference_score=score,
        fidelity=check_fidelity(),
        outcomes=[run_mutation(m) for m in CATALOGUE],
    )


def format_report(report: ValidationReport) -> str:
    lines = []
    lines.append("=" * 78)
    lines.append("GRADING ENGINE VALIDATION  --  SOP #3")
    lines.append("=" * 78)
    lines.append("")

    status = "PASS" if report.reference_clean else "FAIL"
    lines.append(f"Precondition -- reference scores 100% against its own rubric : "
                 f"{report.reference_score:.1f}%  [{status}]")
    if not report.reference_clean:
        lines.append("  ! Every figure below is meaningless until this passes: the rubric")
        lines.append("  ! is demanding something the worked answer does not do.")
    fidelity = "PASS" if report.fidelity.matched else "FAIL"
    lines.append(f"Precondition -- parsed config yields the same rubric as the model : "
                 f"[{fidelity}]")
    if not report.fidelity.matched:
        for finding in report.fidelity.findings:
            lines.append(f"  ! {finding}")
        lines.append("  ! Everything below is measured on constructed objects, so a gap")
        lines.append("  ! here is invisible to every figure in this report.")
    lines.append("")

    lines.append("-" * 78)
    lines.append(f"{'Case':<34} {'Score':>7}  {'Detected':>8}  {'Clean':>6}  {'Guide':>6}")
    lines.append("-" * 78)

    for group, title in ((report.positives, "INJECTED FAULTS"),
                         (report.negatives, "CORRECT WORK (must not be flagged)")):
        lines.append(f"  {title}")
        for o in group:
            detected = "-" if o.mutation.is_negative else ("yes" if o.detected else "NO")
            clean = "yes" if not o.unexpected_categories else "NO"
            if o.mutation.is_negative:
                clean = "yes" if not o.failed_categories else "NO"
            guide = "-" if not o.mutation.expect_mentions else ("yes" if o.guidance_ok else "NO")
            flag = " " if o.passed else "<"
            lines.append(f"{flag} {o.mutation.id:<32} {o.score:>6.1f}%  "
                         f"{detected:>8}  {clean:>6}  {guide:>6}")
        lines.append("")

    failures = [o for o in report.outcomes if not o.passed]
    if failures:
        lines.append("-" * 78)
        lines.append("DETAIL ON FAILING CASES")
        lines.append("-" * 78)
        for o in failures:
            lines.append(f"  {o.mutation.id}  --  {o.mutation.label}")
            lines.append(f"    injected : {o.mutation.fault}")
            if o.expected_categories and not o.detected:
                lines.append(f"    MISSED   : expected a failure in "
                             f"{sorted(o.expected_categories)}, engine reported "
                             f"{sorted(o.failed_categories) or 'nothing'}")
            if o.unexpected_categories:
                lines.append(f"    EXTRA    : also failed {sorted(o.unexpected_categories)}, "
                             "which this fault does not cause")
            if o.mutation.is_negative and o.failed_categories:
                lines.append(f"    FALSE POSITIVE: correct work marked wrong in "
                             f"{sorted(o.failed_categories)}")
            if not o.deterministic:
                lines.append("    NON-DETERMINISTIC: repeated grading gave different scores")
            if not o.guidance_ok:
                lines.append(f"    GUIDANCE : {o.guidance_note}")
            lines.append("")

    lines.append("=" * 78)
    lines.append("SUMMARY")
    lines.append("-" * 78)
    lines.append(f"  Accuracy -- faults detected (recall)        : {report.recall:.1f}%  "
                 f"({len(report.positives)} faults)")
    lines.append(f"  Accuracy -- correct work left alone         : {report.specificity:.1f}%  "
                 f"({len(report.negatives)} cases)")
    lines.append(f"  Accuracy -- cases with no spurious failures : {report.false_positive_rate:.1f}%")
    lines.append(f"  Consistency -- identical score on {REPEATS} runs  : {report.consistency:.1f}%")
    lines.append(f"  Feedback reliability -- names the fault     : {report.feedback_reliability:.1f}%")
    lines.append("=" * 78)
    return "\n".join(lines)
