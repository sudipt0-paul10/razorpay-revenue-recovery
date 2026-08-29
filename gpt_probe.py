from openai import OpenAI

client = OpenAI()

schema = {
    "type": "object",
    "properties": {
        "action_type": {
            "type": "string",
            "enum": ["retry", "hold", "stop"]
        },
        "remedy": {
            "type": "string",
            "enum": ["none", "same_method", "alternate_method"]
        },
        "reason_code": {
            "type": "string",
            "enum": ["insufficient_funds", "temporary_failure", "hard_decline"]
        },
        "rationale": {
            "type": "string"
        }
    },
    "required": ["action_type", "remedy", "reason_code", "rationale"],
    "additionalProperties": False
}

configs = [
    ("probe1", "minimal", "low"),
    ("probe2", "medium", "medium"),
    ("probe3", "low", None),
]

for name, reasoning_effort, verbosity in configs:
    print(f"\n===== {name} =====")
    print(f"reasoning_effort={reasoning_effort}, verbosity={verbosity}")

    kwargs = {
        "model": "gpt-5-mini",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Return exactly one valid JSON object matching the supplied "
                    "schema. No explanation outside the JSON object."
                ),
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "planner_output",
                "strict": True,
                "schema": schema,
            },
        },
        "reasoning_effort": reasoning_effort,
    }

    if verbosity is not None:
        kwargs["verbosity"] = verbosity

    try:
        response = client.chat.completions.create(**kwargs)

        print("STATUS: SUCCESS")
        print("RAW_CONTENT:")
        print(response.choices[0].message.content)

    except Exception as e:
        print("STATUS: ERROR")
        print(type(e).__name__)
        print(str(e))