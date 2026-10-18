# src/chat_guard.py
"""
Deterministic safeguards around the student chat (issue #19).

The system prompt alone is easy to talk a 3B model out of. So questions are
checked BEFORE the model is called, and replies AFTER it answers:

  1. gate_question  -- injection attempts, off-topic tasks and requests for
                       the whole answer get a fixed refusal; the model is
                       never called.
  2. needs_classifier -- a question with no networking signal at all is put
                       to the model as a yes/no topic check first.
  3. filter_reply   -- long runs of IOS configuration are cut from a reply,
                       so the tutor explains rather than hands over the fix.

Refusals are template text, never model-written, so they cannot be argued
with and are the same every time.
"""

import re

from src.models import EvaluationReport

REFUSE_OFF_TOPIC = (
    "I can only help with this networking lab and the concepts behind it. "
    "Try asking about one of your missed checkpoints, or a command you are unsure of."
)
REFUSE_INJECTION = (
    "I can't change how I work or what I'm allowed to answer. "
    "Ask me about your lab results and I'll help."
)
REFUSE_FULL_SOLUTION = (
    "I can't write out the whole configuration for you -- working it out is the point of the lab. "
    "Ask about one checkpoint or one command at a time and I'll explain how it works."
)
CONFIG_WITHHELD = (
    "That answer spelled out the configuration step by step, so it was withheld. "
    "Ask about one checkpoint or one command at a time and I'll explain how it works."
)
CONFIG_REMOVED = (
    "[A block of configuration was removed from this answer. Try writing those "
    "commands yourself, and ask about any single command you are unsure of.]"
)

MAX_CONFIG_LINES = 4          # a short example is teaching; more is the answer
MAX_CONFIG_IN_REPLY = 6       # all commands in a reply, however they are formatted
SHORT_FOLLOW_UP_WORDS = 8     # "why?", "can you say that more simply?"

_INJECTION = re.compile(
    r"\b(ignore|disregard|forget|override)\b.{0,40}\b(instructions?|rules?|prompts?|guidelines?|findings)\b"
    r"|\bsystem\s+prompt\b|\byou\s+are\s+now\b|\bpretend\s+(to\s+be|you\s+are)\b"
    r"|\bjailbreak\b|\bdeveloper\s+mode\b|(?-i:\bDAN\b)",
    re.IGNORECASE,
)

_OFF_TOPIC_TASK = re.compile(
    r"\b(essays?|poems?|poetry|stor(y|ies)|lyrics|song|recipes?|novel|jokes?|horoscope|"
    r"cover\s+letter|love\s+letter|book\s+report|thesis\s+statement)\b",
    re.IGNORECASE,
)

_FULL_SOLUTION = re.compile(
    r"\b(full|complete|whole|entire|all(\s+of)?\s+the|every)\b.{0,30}"
    r"\b(config(uration)?s?|commands|answers?|solutions?|running-config)\b"
    r"|\b(give|write|send|paste)\b.{0,20}\b(me\s+)?the\s+(answers?|solution)\b"
    r"|\bexactly\s+what\s+to\s+(type|enter|write|put)\b|\bevery\s+(single\s+)?line\b",
    re.IGNORECASE,
)

_NETWORKING = re.compile(
    r"\b(ip|ipv4|ipv6|subnets?|subnetting|mask|cidr|prefix|vlans?|trunk(s|ing)?|native|ospf|eigrp|rip|bgp|"
    r"routes?|routing|routers?|switch(es|port|ing)?|gateway|interfaces?|ports?|cables?|cabling|links?|"
    r"ping|traceroute|packets?|tracer|cisco|ios|config(ure|uration)?|commands?|show|dhcp|dns|nat|pat|acl|"
    r"mac|arp|cdp|lldp|stp|spanning|area|networks?|address(es|ing)?|hosts?|pc|ethernet|gigabit|fast|serial|"
    r"duplex|speed|mtu|hello|dead|adjacency|neighbou?rs?|loopback|wildcard|broadcast|octet|binary|"
    r"layer|osi|tcp|udp|protocol|lab|checkpoints?|mistakes?|missed|wrong|errors?|results?|points?|"
    r"grade|score|fail(ed)?|pass(ed)?|practi[cs]e|study|fix|topology|device|r\d+|sw\d+|pc\d+|g\d+/\d+|"
    r"fa\d+/\d+|gi\d+/\d+|se\d+/\d+|shut(down)?|hostname|encapsulation|vty|console|telnet|ssh|"
    r"(running|startup)-config|enable\s+secret|wan|lan|wi-?fi|wireless|firewall|server|client)\b",
    re.IGNORECASE,
)

_PROMPT_PREFIX = re.compile(r"^\s*[\w\-.]*(\(config[^)]*\))?[#>]\s*")
_CONFIG_LINE = re.compile(
    r"^(interface|int|ip|ipv6|router|network|switchport|vlan|hostname|no|shutdown|enable|line|password|"
    r"login|service|encapsulation|clock|access-list|description|exit|end|conf(igure)?|spanning-tree|"
    r"default-router|duplex|speed|channel-group|passive-interface|router-id|redistribute|standby|"
    r"dns-server|banner|username|transport|exec-timeout|logging|crypto|default-information)\b",
    re.IGNORECASE,
)


def _lab_entities(report: EvaluationReport | None) -> set[str]:
    if report is None:
        return set()
    names = set()
    for r in report.results:
        if r.target_device:
            names.add(r.target_device.lower())
        if r.target_interface:
            names.add(r.target_interface.lower())
    return names


def has_networking_signal(question: str, report: EvaluationReport | None = None) -> bool:
    if _NETWORKING.search(question):
        return True
    lowered = question.lower()
    return any(name and name in lowered for name in _lab_entities(report))


def gate_question(question: str) -> str | None:
    """A fixed refusal for a question the model must not see, else None."""
    if _INJECTION.search(question):
        return REFUSE_INJECTION
    if _FULL_SOLUTION.search(question):
        return REFUSE_FULL_SOLUTION
    if _OFF_TOPIC_TASK.search(question):
        return REFUSE_OFF_TOPIC
    return None


def needs_classifier(question: str, report: EvaluationReport | None, has_history: bool) -> bool:
    """True when nothing in the question ties it to networking or this lab."""
    if has_networking_signal(question, report):
        return False
    # A short follow-up ("why?", "say that more simply") leans on the
    # conversation so far, which was itself on topic.
    if has_history and len(question.split()) <= SHORT_FOLLOW_UP_WORDS:
        return False
    return True


CLASSIFIER_SYSTEM = "You are a strict topic filter. Reply with exactly one word: yes or no."


def classifier_prompt(question: str) -> str:
    return (
        "Is the following question about computer networking, Cisco equipment, "
        "Packet Tracer, or a student's networking lab work?\n\n"
        f"Question: {question}"
    )


def classifier_says_off_topic(reply: str | None) -> bool:
    """Only a clear "no" blocks. No answer at all leaves the decision to the tutor prompt."""
    return bool(reply) and reply.strip().lower().lstrip("\"'*").startswith("no")


def _is_config_line(line: str) -> bool:
    text = _PROMPT_PREFIX.sub("", line.strip().strip("`"))
    if not text or len(text) > 80 or text.endswith((".", ":", "?", "!")):
        return False
    return bool(_CONFIG_LINE.match(text))


_INLINE_CODE = re.compile(r"`([^`\n]+)`")


def _config_command_count(reply: str) -> int:
    """Config commands anywhere in a reply: on their own line or in `inline code`."""
    count = 0
    for line in reply.split("\n"):
        spans = _INLINE_CODE.findall(line)
        if spans:
            count += sum(_is_config_line(span) for span in spans)
        elif _is_config_line(line):
            count += 1
    return count


def filter_reply(reply: str) -> tuple[str, bool]:
    """Cut every run of more than MAX_CONFIG_LINES configuration lines.

    Blank lines and code fences inside a run don't end it, so a config pasted
    in a ``` block with spacing is still one run. A reply that walks through
    more than MAX_CONFIG_IN_REPLY commands in any layout -- a numbered list of
    `inline code`, say -- is withheld whole. Returns (text, was_filtered).
    """
    if _config_command_count(reply) > MAX_CONFIG_IN_REPLY:
        return CONFIG_WITHHELD, True
    lines = reply.split("\n")
    out: list[str] = []
    run: list[str] = []
    run_config = 0
    filtered = False

    def flush():
        nonlocal run, run_config, filtered
        if run_config > MAX_CONFIG_LINES:
            # The run took any closing fence with it; drop the opening one.
            while out and not out[-1].strip():
                out.pop()
            if out and out[-1].strip().startswith("```"):
                out.pop()
            out.append(CONFIG_REMOVED)
            filtered = True
        else:
            out.extend(run)
        run, run_config = [], 0

    for line in lines:
        neutral = not line.strip() or line.strip().startswith("```") or line.strip() == "!"
        if _is_config_line(line):
            run.append(line)
            run_config += 1
        elif neutral and run:
            run.append(line)
        else:
            flush()
            out.append(line)
    flush()

    return "\n".join(out).strip(), filtered
