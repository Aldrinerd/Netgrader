# src/sanitizer.py
import re

COMMAND_PATTERNS = {
    "show running-config": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+run(?:ning-config)?.*$", re.IGNORECASE),
    "show cdp neighbors detail": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+cdp\s+neigh(?:bors)?(?:\s+detail)?.*$", re.IGNORECASE),
    "show ip interface brief": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+ip\s+int(?:erface)?\s+br(?:ief)?.*$", re.IGNORECASE),
    "show ip route": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+ip\s+route.*$", re.IGNORECASE),
    "show vlan brief": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+vlan(?:\s+br(?:ief)?)?.*$", re.IGNORECASE),
    "show interfaces trunk": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+int(?:erfaces)?\s+trunk.*$", re.IGNORECASE),
    "show mac address-table": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+mac(?:\s+address-table)?.*$", re.IGNORECASE),
}

def sanitize_terminal_output(raw_text: str) -> str:
    """Sanitizes terminal control characters, paginations, and normalizes newlines."""
    cleaned = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove --More-- banners and backspace sequences
    cleaned = re.sub(r"--\s*More\s*--(?:\x08|\s)*", "", cleaned)
    # Remove ANSI escape sequences
    cleaned = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", cleaned)
    return cleaned

def split_command_sections(raw_text: str) -> dict[str, tuple[str, int]]:
    """
    Splits multi-command terminal output into distinct command sections.
    Returns dict: command_name -> (section_text, line_number_offset)
    """
    sanitized = sanitize_terminal_output(raw_text)
    lines = sanitized.splitlines()
    matches = []
    
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        for cmd_name, pattern in COMMAND_PATTERNS.items():
            if pattern.match(stripped):
                matches.append((idx, cmd_name))
                break

    if not matches:
        # If no explicit command headers found, treat entire file as running-config
        return {"show running-config": (sanitized, 1)}

    sections: dict[str, tuple[str, int]] = {}
    
    # Check if there is preamble content before the first command match
    if matches and matches[0][0] > 1:
        first_cmd_line = matches[0][0]
        preamble_lines = lines[0:first_cmd_line - 1]
        preamble_text = "\n".join(preamble_lines).strip()
        if preamble_text:
            sections["show running-config"] = (preamble_text, 1)

    for i in range(len(matches)):
        start_line_idx, cmd = matches[i]
        end_line_idx = matches[i+1][0] - 1 if i + 1 < len(matches) else len(lines)
        section_lines = lines[start_line_idx:end_line_idx]
        section_content = "\n".join(section_lines)
        
        if cmd in sections:
            prev_content, prev_line = sections[cmd]
            sections[cmd] = (prev_content + "\n" + section_content, prev_line)
        else:
            sections[cmd] = (section_content, start_line_idx + 1)
    
    return sections

