import re


_THINKING_TAG_PATTERNS = [
    r"<thinking\b[^>]*>[\s\S]*?</thinking>",
    r"<reasoning\b[^>]*>[\s\S]*?</reasoning>",
    r"<analysis\b[^>]*>[\s\S]*?</analysis>",
    r"<thought\b[^>]*>[\s\S]*?</thought>",
]


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def strip_thinking_blocks(text: str) -> str:
    cleaned = text
    for pattern in _THINKING_TAG_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _extract_balanced_json(text: str) -> str | None:
    start = -1
    opener = ""
    closer = ""

    for i, ch in enumerate(text):
        if ch == "{":
            start = i
            opener, closer = "{", "}"
            break
        if ch == "[":
            start = i
            opener, closer = "[", "]"
            break

    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == opener:
            depth += 1
            continue
        if ch == closer:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None


def extract_json_payload(text: str) -> str:
    cleaned = strip_thinking_blocks(strip_code_fence(text))
    balanced = _extract_balanced_json(cleaned)
    if balanced is not None:
        return balanced.strip()
    return cleaned.strip()

