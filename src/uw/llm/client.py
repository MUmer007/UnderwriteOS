import os
import json
import time
import base64
from typing import Type, List
from pydantic import BaseModel, ValidationError
from openai import OpenAI, RateLimitError, APIConnectionError

# Initialize OpenAI client pointing to OpenRouter
client = OpenAI(
    base_url=os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "")
)

def write_audit_trail(model: str, messages: list, raw_response: str, usage: dict, latency: float):
    pass

def call_structured(
    model: str, 
    system_prompt: str, 
    user_text: str,
    schema: Type[BaseModel],
    images: List[bytes] = None,
    max_retries: int = 3
) -> tuple[BaseModel, dict, float]:
    
    images = images or []
    content = [{
        "type": "text", 
        "text": f"{user_text}\n\nReturn ONLY valid JSON matching this schema:\n{json.dumps(schema.model_json_schema())}"
    }]
    
    for img in images:
        b64 = base64.b64encode(img).decode('utf-8')
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ]

    extra_headers = {
        "HTTP-Referer": "http://localhost:8000", 
        "X-Title": "UnderwriteOS"
    }

    for attempt in range(max_retries + 1):
        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"},
                extra_headers=extra_headers
            )
            
            raw = resp.choices[0].message.content
            latency = time.time() - t0
            
            try:
                parsed = schema.model_validate_json(raw)
                write_audit_trail(model, messages, raw, resp.usage.model_dump(), latency)
                return parsed, resp.usage.model_dump(), latency
            except ValidationError as e:
                if attempt == max_retries:
                    raise ValueError(f"Schema validation failed: {e}")
                messages.extend([
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": f"Invalid JSON. Errors: {e.errors()}. Return corrected JSON ONLY."}
                ])
                
        except RateLimitError:
            wait_time = (2 ** attempt) + 1
            print(f"\n   ?? Rate limited (429). Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            continue
        except APIConnectionError:
            wait_time = (2 ** attempt) + 1
            print(f"\n   ?? Connection error. Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            continue
            
    raise ValueError("Extraction failed after max retries.")
