import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv('GROQ_API_KEY'))
MODEL  = 'llama-3.3-70b-versatile'


def _call_groq(prompt: str) -> str:
    """Single place that calls Groq — returns raw text string."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                'role': 'system',
                'content': 'You are an expert software engineer. Respond with valid JSON only. No markdown, no backticks, no extra text.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        temperature=0.2,
        max_tokens=4000,
    )
    return response.choices[0].message.content


def _parse(raw: str) -> dict:
    """Strip markdown fences and parse JSON."""
    import re
    clean = raw.strip()
    # Remove markdown fences
    if clean.startswith('```'):
        clean = clean.split('\n', 1)[1]
    if clean.endswith('```'):
        clean = clean.rsplit('```', 1)[0]
    clean = clean.strip()
    # Remove control characters that break JSON parsing
    # but preserve actual newlines inside strings by encoding them
    clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean)
    return json.loads(clean)


def build_review_prompt(code: str, language: str) -> str:
    return f"""You are an expert {language} code reviewer with 15+ years of experience.
Analyze the following {language} code and return a detailed review.

CODE TO REVIEW:
```{language}
{code}
```

Return ONLY valid JSON with this exact structure — no markdown, no backticks:
{{
    "quality_score": <integer 0-100>,
    "summary": "<2-3 sentence overall assessment>",
    "categories": {{
        "bugs": "<bugs found>",
        "security": "<security issues>",
        "performance": "<performance issues>",
        "readability": "<code clarity>",
        "best_practices": "<adherence to {language} best practices>"
    }},
    "inline_comments": [
        {{
            "line_number": <integer or null>,
            "severity": "<critical|warning|info>",
            "message": "<issue and why it matters>",
            "suggestion": "<improved code or fix>"
        }}
    ],
    "positive_aspects": ["<thing done well>"],
    "improved_code": "<full rewritten version with all fixes applied>"
}}"""


def get_ai_review(code: str, language: str) -> dict:
    try:
        raw  = _call_groq(build_review_prompt(code, language))
        data = _parse(raw)
        return {'success': True, 'data': data}
    except json.JSONDecodeError as e:
        return {'success': False, 'error': f'Invalid JSON from AI: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_ai_review_stream(code: str, language: str):
    """
    Groq supports streaming too. Yields text chunks.
    """
    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    'role': 'system',
                    'content': 'You are an expert software engineer. Respond with valid JSON only. No markdown, no backticks.'
                },
                {
                    'role': 'user',
                    'content': build_review_prompt(code, language)
                }
            ],
            temperature=0.2,
            max_tokens=4000,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        yield json.dumps({'error': str(e)})


def build_teach_prompt(concept: str, language: str) -> str:
    return f"""You are an expert programming teacher with 15 years of experience
teaching {language} to developers. A student asked: "{concept}"

Return ONLY valid JSON, no markdown:
{{
    "concept_name": "<clean title>",
    "one_line": "<one sentence essence>",
    "explanation": "<3-4 paragraph explanation>",
    "analogy": "<real-world analogy>",
    "code_example": "<complete runnable {language} code with comments>",
    "common_mistakes": [
        {{"mistake": "<what beginners get wrong>", "fix": "<correct approach>"}},
        {{"mistake": "<second mistake>", "fix": "<fix>"}}
    ],
    "practice_exercise": "<one exercise to try>",
    "next_topics": ["<related topic>", "<another>"]
}}"""


def build_convert_prompt(code: str, from_lang: str, to_lang: str) -> str:
    return f"""You are an expert in both {from_lang} and {to_lang}.
Convert this {from_lang} code to idiomatic {to_lang}.

CODE:
```{from_lang}
{code}
```

Return ONLY valid JSON, no markdown:
{{
    "converted_code": "<complete working {to_lang} code>",
    "key_differences": ["<difference 1>", "<difference 2>"],
    "notes": "<caveats or idiomatic changes>",
    "equivalent_concepts": {{
        "<{from_lang} concept>": "<{to_lang} equivalent>"
    }}
}}"""


def get_ai_teach(concept: str, language: str) -> dict:
    try:
        raw  = _call_groq(build_teach_prompt(concept, language))
        print("GROQ RAW RESPONSE:", raw[:200])  # ← ADD THIS
        data = _parse(raw)
        return {'success': True, 'data': data}
    except Exception as e:
        print("GROQ ERROR:", str(e))  # ← ADD THIS
        return {'success': False, 'error': str(e)}


def get_ai_convert(code: str, from_lang: str, to_lang: str) -> dict:
    try:
        raw  = _call_groq(build_convert_prompt(code, from_lang, to_lang))
        data = _parse(raw)
        return {'success': True, 'data': data}
    except Exception as e:
        return {'success': False, 'error': str(e)}