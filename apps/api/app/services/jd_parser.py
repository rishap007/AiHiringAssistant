from __future__ import annotations

import json
import re
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings


class JDParseError(Exception):
    def __init__(self, message: str, raw_output: str) -> None:
        self.raw_output = raw_output
        super().__init__(f"{message}. Raw LLM output: {raw_output}")


SYSTEM_PROMPT = """Extract structured hiring criteria from the job description below. Return
ONLY valid JSON with this exact shape, no prose, no markdown fences:
{"title": string, "seniority": string, "skills": [string], "location": string,
"keywords": [string]}. If a field is not mentioned, use an empty string or
empty list."""


def _strip_code_fences(output: str) -> str:
    cleaned = output.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


async def parse_job_description(jd_text: str) -> dict[str, Any]:
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": jd_text},
            ],
        )
    finally:
        await client.close()

    raw_output = response.choices[0].message.content or ""
    try:
        parsed = json.loads(_strip_code_fences(raw_output))
    except (json.JSONDecodeError, TypeError) as exc:
        raise JDParseError("LLM returned invalid JSON", raw_output) from exc
    if not isinstance(parsed, dict):
        raise JDParseError("LLM returned JSON that is not an object", raw_output)
    return parsed
