# src/topics/weights.py
"""
How a lab's points are split between topics.

All arithmetic is in integer tenths (of a point, or of a percent), split with
largest-remainder apportionment, so every total comes out exact.

  default_weights   the split today's rubric already has, as percentages
  validate_weights  checks an instructor's requested split (TopicWeightError)
  apply_weights     rescales rule points to a requested split; a 0% topic's
                    rules become ungraded (graded=False, points=0)
"""
import math
from typing import Sequence

from src.models import EvaluationRule
from src.topics.registry import TOPICS, TOPICS_BY_KEY, topic_for_category

TENTHS = 10
PERCENT_UNITS = 100 * TENTHS        # 100.0% in tenths of a percent
SUM_TOLERANCE = 0.05                # percent
DEFAULTS_TOLERANCE = 0.001          # percent
_FORMAT_ERROR = "topic_weights must be a JSON object of topic -> percent"


class TopicWeightError(ValueError):
    """An instructor's topic weights cannot be applied. The message names the topic."""


def largest_remainder(weights: Sequence[float], units: int) -> list[int]:
    """
    Split `units` whole units in proportion to non-negative `weights`,
    exactly. Floors every share, then hands the leftover units to the largest
    fractional remainders (earliest index first on ties). All-zero weights
    get nothing.
    """
    total = float(sum(weights))
    if units <= 0 or total <= 0:
        return [0] * len(weights)
    exact = [units * w / total for w in weights]
    alloc = [math.floor(x + 1e-9) for x in exact]
    leftover = max(0, units - sum(alloc))
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - alloc[i]), i))
    for i in order[:leftover]:
        alloc[i] += 1
    return alloc


def normalize_rule_points(rules: list[EvaluationRule], target_total: float) -> None:
    """
    Rescale rule weights in place so they sum to exactly `target_total`.

    Uses largest-remainder (Hamilton) apportionment in tenths of a point.
    Every rule is guaranteed a strictly positive score whenever the target
    allows it, because a rule worth zero or fewer points corrupts grading:
    a negative weight means PASSING a checkpoint would lower a student's
    percentage.
    """
    if not rules or target_total <= 0:
        return

    total_tenths = int(round(target_total * TENTHS))
    count = len(rules)

    # Degenerate case: fewer tenths than rules, so not every rule can be worth
    # something. Spread what exists as evenly as possible rather than going
    # negative, and let the caller's total stand.
    if total_tenths < count:
        base, remainder = divmod(total_tenths, count)
        for i, rule in enumerate(rules):
            rule.points = round((base + (1 if i < remainder else 0)) / TENTHS, 1)
        return

    weights = [max(float(r.points), 0.0) for r in rules]
    weight_sum = sum(weights)
    if weight_sum <= 0:
        weights = [1.0] * count
        weight_sum = float(count)

    # Ideal share for each rule, floored, with a guaranteed minimum of one tenth.
    exact = [total_tenths * w / weight_sum for w in weights]
    allocation = [max(1, int(share)) for share in exact]

    # Hand out or claw back tenths until the allocation sums exactly to target.
    drift = total_tenths - sum(allocation)
    if drift > 0:
        # Largest fractional remainder gets the surplus tenths first.
        order = sorted(range(count), key=lambda i: exact[i] - int(exact[i]), reverse=True)
        for step in range(drift):
            allocation[order[step % count]] += 1
    elif drift < 0:
        # Over-allocated by the minimum floor: reclaim from the largest rules,
        # never dropping any rule below one tenth of a point.
        order = sorted(range(count), key=lambda i: allocation[i], reverse=True)
        step = 0
        while drift < 0:
            index = order[step % count]
            if allocation[index] > 1:
                allocation[index] -= 1
                drift += 1
            step += 1
            if step > count * total_tenths + count:  # safety valve
                break

    for rule, tenths in zip(rules, allocation):
        rule.points = round(tenths / TENTHS, 1)


def rules_by_topic(rules: list[EvaluationRule]) -> dict[str, list[EvaluationRule]]:
    """Topic key -> its rules, in registry order, topics with no rules left out."""
    grouped: dict[str, list[EvaluationRule]] = {t.key: [] for t in TOPICS}
    for rule in rules:
        grouped[topic_for_category(rule.category).key].append(rule)
    return {key: topic_rules for key, topic_rules in grouped.items() if topic_rules}


def default_weights(rules: list[EvaluationRule]) -> dict[str, float]:
    """
    Each topic's share of the rules' current points, as one-decimal percents
    summing to exactly 100.0. Called on the legacy-normalized rubric, so at a
    100-point total a topic's default percent equals its points.
    """
    groups = rules_by_topic(rules)
    keys = list(groups)
    units = largest_remainder([sum(r.points for r in groups[k]) for k in keys], PERCENT_UNITS)
    return {k: u / TENTHS for k, u in zip(keys, units)}


def minimum_percent(checkpoints: int, total_points: float) -> float:
    """Smallest one-decimal percent that gives every checkpoint at least 0.1 pt."""
    return math.ceil(checkpoints * 100 / total_points - 1e-9) / TENTHS


def validate_weights(raw: object, defaults: dict[str, float]) -> dict[str, float]:
    """
    Check an instructor's requested split against the topics this rubric has.
    Returns {topic key: percent} rounded to one decimal. Raises TopicWeightError.
    """
    if not isinstance(raw, dict):
        raise TopicWeightError(_FORMAT_ERROR)
    weights: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TopicWeightError(_FORMAT_ERROR)
        topic = TOPICS_BY_KEY.get(key)
        if topic is None:
            raise TopicWeightError(f'Unknown topic "{key}"')
        if not topic.gradeable:
            raise TopicWeightError(f'"{key}" cannot be weighted: it is not graded yet')
        if key not in defaults:
            raise TopicWeightError(f'"{topic.label}" is not part of this rubric')
        if not 0 <= value <= 100:
            raise TopicWeightError(f'"{topic.label}" must be between 0 and 100')
        if abs(round(value, 1) - value) > 1e-9:
            raise TopicWeightError(f'"{topic.label}" allows one decimal place')
        weights[key] = round(float(value), 1)
    for key in defaults:
        if key not in weights:
            raise TopicWeightError(f'Missing a weight for "{TOPICS_BY_KEY[key].label}"')
    if all(v == 0 for v in weights.values()):
        raise TopicWeightError("At least one topic must carry points")
    total = sum(weights.values())
    if abs(total - 100) > SUM_TOLERANCE:
        raise TopicWeightError(f"Weights add up to {total:.1f}%, they must add up to 100%")
    return weights


def same_weights(a: dict[str, float], b: dict[str, float]) -> bool:
    return a.keys() == b.keys() and all(abs(a[k] - b[k]) < DEFAULTS_TOLERANCE for k in a)


def apply_weights(rules: list[EvaluationRule], base_points: dict[str, float],
                  weights: dict[str, float], total_points: float) -> None:
    """
    Rescale rule points in place to `weights`. Topics split the total by
    percent; inside a topic the rules keep their base-point proportions.
    A 0% topic's rules become graded=False with 0 points.
    """
    groups = rules_by_topic(rules)
    keys = list(groups)
    shares = dict(zip(keys, largest_remainder([weights[k] for k in keys], round(total_points * TENTHS))))

    # Check every topic before changing any rule.
    for key, topic_rules in groups.items():
        if weights[key] > 0 and shares[key] < len(topic_rules):
            raise TopicWeightError(
                f'"{TOPICS_BY_KEY[key].label}" needs at least '
                f"{minimum_percent(len(topic_rules), total_points):.1f}% "
                f"for its {len(topic_rules)} checkpoints"
            )

    for key, topic_rules in groups.items():
        if weights[key] == 0:
            for rule in topic_rules:
                rule.graded = False
                rule.points = 0.0
            continue
        for rule in topic_rules:
            rule.points = base_points[rule.rule_id]
        normalize_rule_points(topic_rules, shares[key] / TENTHS)
