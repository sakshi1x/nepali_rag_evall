"""Small Anthropic (Claude) client with a disk cache (cache/llm_cache.jsonl).
Needs ANTHROPIC_API_KEY in .env (never commit .env). Install: pip install anthropic python-dotenv
Note: current Claude models reject `temperature`, so no temperature is sent; reruns are made
repeatable by the cache instead (same model + same messages + same settings -> cached answer)."""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
CACHE = ROOT / "cache" / "llm_cache.jsonl"
EFFORT = "medium"
MAX_TOKENS = 16000
# Server-side refusal fallback: if Claude declines (safety classifier), the API retries on a fallback model.
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-2", "claude-fable-5-1", "claude-opus-5"}

_cache = None
_client = None


def _key(model, messages):
    return hashlib.sha256(json.dumps([model, messages, EFFORT], ensure_ascii=False).encode()).hexdigest()


def _load_cache():
    if not CACHE.exists():
        return {}
    return {r["key"]: r["response"] for r in map(json.loads, CACHE.open(encoding="utf-8"))}


def chat(model: str, messages: list) -> str:
    """Send messages to Claude and return the text of the answer (cached)."""
    global _cache, _client
    if _cache is None:
        _cache = _load_cache()
    k = _key(model, messages)
    if k in _cache:
        return _cache[k]

    import anthropic
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    kwargs = dict(model=model, max_tokens=MAX_TOKENS, messages=messages,
                  output_config={"effort": EFFORT})
    if model in FALLBACK_MODELS:
        resp = _client.beta.messages.create(**kwargs, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    else:
        resp = _client.messages.create(**kwargs)

    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Claude refused this request (category: {getattr(resp.stop_details, 'category', None)})")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("Answer was cut off at max_tokens")
    text = "".join(b.text for b in resp.content if b.type == "text")

    CACHE.parent.mkdir(exist_ok=True)
    with CACHE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"key": k, "model": model, "served_by": resp.model, "effort": EFFORT,
                            "messages": messages, "response": text,
                            "usage": {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}},
                           ensure_ascii=False) + "\n")
    _cache[k] = text
    return text
