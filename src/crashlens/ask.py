"""Ask-your-data: turn a plain-English question into SQL with Claude and run it.

Requires ANTHROPIC_API_KEY in the environment. If it's not set, the feature is
disabled gracefully (the dashboard shows instructions instead of erroring).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import duckdb
import pandas as pd

from crashlens import config

MODEL = "claude-opus-4-8"

SCHEMA_DOC = """\
Table: crashes  (one row per NYC motor vehicle collision)
Columns:
  collision_id BIGINT           -- unique crash id
  crash_datetime TIMESTAMP      -- when the crash happened
  crash_year INTEGER
  crash_month VARCHAR           -- 'YYYY-MM'
  crash_hour INTEGER            -- 0-23
  day_of_week VARCHAR           -- 'Monday'..'Sunday'
  borough VARCHAR               -- BRONX, BROOKLYN, MANHATTAN, QUEENS, STATEN ISLAND, UNKNOWN
  latitude DOUBLE, longitude DOUBLE  -- may be NULL
  persons_injured INTEGER, persons_killed INTEGER
  pedestrians_injured INTEGER, pedestrians_killed INTEGER
  cyclists_injured INTEGER, cyclists_killed INTEGER
  motorists_injured INTEGER, motorists_killed INTEGER
  contributing_factor VARCHAR   -- e.g. 'Driver Inattention/Distraction', 'Unspecified'
  vehicle_type VARCHAR          -- e.g. 'Sedan', 'Taxi', 'Bike'
  is_fatal BOOLEAN
"""

SYSTEM_PROMPT = f"""You are a SQL analyst for a DuckDB database of NYC vehicle collisions.

{SCHEMA_DOC}

Write a single DuckDB SELECT statement that answers the user's question.
Rules:
- SELECT statements only — never modify data.
- Limit results to 500 rows unless the question implies an aggregate.
- Prefer readable column aliases.
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "sql": {"type": "string", "description": "A single DuckDB SELECT statement."},
        "explanation": {
            "type": "string",
            "description": "One sentence explaining what the query computes.",
        },
    },
    "required": ["sql", "explanation"],
    "additionalProperties": False,
}


@dataclass
class AskResult:
    sql: str
    explanation: str
    data: pd.DataFrame


def is_available() -> bool:
    """AI querying is enabled only when an API key is configured."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _guard_sql(sql: str) -> str:
    """Reject anything that isn't a plain SELECT (defense in depth — the
    connection is also opened read-only)."""
    stripped = sql.strip().rstrip(";").strip()
    lowered = stripped.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError(f"Only SELECT queries are allowed, got: {stripped[:60]}...")
    return stripped


def generate_sql(question: str) -> tuple[str, str]:
    """Ask Claude for SQL answering the question. Returns (sql, explanation)."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        messages=[{"role": "user", "content": question}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    payload = json.loads(text)
    return payload["sql"], payload["explanation"]


def ask(question: str) -> AskResult:
    """Full round trip: question -> SQL -> results from the warehouse."""
    sql, explanation = generate_sql(question)
    sql = _guard_sql(sql)
    con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    try:
        data = con.execute(sql).fetchdf()
    finally:
        con.close()
    return AskResult(sql=sql, explanation=explanation, data=data)
