"""Cardwright, as a Python generator beside RedGen.

Writes Marinara / SillyTavern Character Card V2 JSON through KoboldCPP,
packs that JSON into a PNG, and can ask NovelAI for a portrait.
Nothing here needs a GPU. RedGen still draws locally on the Generate tab.
"""

from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

NOVEL_URL = "https://image.novelai.net/ai/generate-image"
DEFAULT_KOBOLD = "http://127.0.0.1:5001/v1"
DEFAULT_NOVEL_MODEL = "nai-diffusion-5-full"
DEFAULT_NOVEL_PREFIX = "score_9_up, detailed skin, high detail, shiny skin,"
DEFAULT_NOVEL_NEGATIVE = "artist name, signature, watermark, holding, blurry, jpeg artifacts, username, signature, normal quality, worst quality, large head."
NOVEL_STYLES = {
    "Anime": {
        "prefix": "very aesthetic, masterpiece, no text",
        "negative": "lowres, bad anatomy, bad hands, extra fingers, missing fingers, worst quality, low quality, jpeg artifacts, watermark, text, signature",
        "note": "Anime tags were added to the prompt prefix.",
    },
    "Semi-realistic": {
        "prefix": "very aesthetic, masterpiece, no text, realistic, semi-realistic",
        "negative": "sketch, lineart, flat color, anime, chibi, simple shading, lowres, bad anatomy, watermark, text",
        "note": "Semi-realistic tags were added to the prompt prefix.",
    },
    "Furry": {
        "prefix": "very aesthetic, masterpiece, no text, furry, anthro",
        "negative": "human, lowres, bad anatomy, extra digits, worst quality, watermark, text",
        "note": "Furry tags were added to the prompt prefix.",
    },
    "Danbooru": {
        "prefix": DEFAULT_NOVEL_PREFIX,
        "negative": DEFAULT_NOVEL_NEGATIVE,
        "note": "Danbooru / Illustrious tags were added to the prompt prefix.",
    },
}
NOVEL_MODELS = (
    ("V5 Full", "nai-diffusion-5-full"),
    ("V5 Curated", "nai-diffusion-5-curated"),
    ("V4.5 Full", "nai-diffusion-4-5-full"),
    ("V4.5 Curated", "nai-diffusion-4-5-curated"),
)
NOVEL_SAMPLERS = (
    "k_euler_ancestral",
    "k_euler",
    "k_dpmpp_2s_ancestral",
    "k_dpmpp_2m",
    "k_dpmpp_sde",
    "k_dpmpp_2m_sde",
)
NOVEL_SCHEDULES = ("karras", "exponential", "polyexponential")
NOVEL_SETTINGS = {
    "novel_token": "",
    "novel_model": DEFAULT_NOVEL_MODEL,
    "novel_seed": "-1",
    "novel_style": "Anime",
    "novel_danbooru": True,
    "novel_steps": 25,
    "novel_guidance": 6.8,
    "novel_rescale": 0.0,
    "novel_uc": 2,
    "novel_prefix": DEFAULT_NOVEL_PREFIX,
    "novel_negative": DEFAULT_NOVEL_NEGATIVE,
    "novel_sampler": "k_euler_ancestral",
    "novel_schedule": "karras",
    "novel_auto": False,
    "novel_width": 1024,
    "novel_height": 1024,
    "novel_strength": 0.65,
    "novel_fidelity": 0.65,
    "novel_plate": "",
    "novel_folder": "",
}

CARD_SYSTEM = """You write character cards for Marinara Engine, which reads SillyTavern Character Card V2.
Return one JSON object and nothing else. No markdown fences. No commentary.
Use {{char}} for the character and {{user}} for the person they meet. Do not invent a name for {{user}}.
Write concrete facts, not adjective piles. first_mes is spoken in character, with actions in asterisks.
mes_example contains two or three exchanges, each block starting with <START>.
summary is one sentence for a library list and is not roleplay prose.
tags is an array of 3 to 6 short labels.
talkativeness is an integer from 0 to 100.
Leave system_prompt and post_history_instructions as empty strings unless the concept demands a hard rule."""

PICTURE_NOTE = """Reference images are attached. They are the character, not a suggestion.
appearance must match what is visible: face, body, clothing, colors, and setting cues.
Do not invent a conflicting look. You may name them and write personality if the concept does not."""

PERSONA_SYSTEM = """You write a Marinara persona: the character card that stands for the human in a chat, not the character they talk to.
Return one JSON object and nothing else. No markdown fences. No commentary.
Use {{user}} for this persona and {{char}} for the other character. Do not invent a name for {{char}}.
Write concrete facts. first_mes must be an empty string. alternate_greetings must be an empty array.
mes_example shows how {{user}} speaks, two short exchanges, each block starting with <START>.
summary is one sentence for a library list.
tags is an array of 3 to 6 short labels.
Leave system_prompt and post_history_instructions as empty strings."""

SCHEMA_HINT = """JSON keys:
{
  "name": "",
  "summary": "",
  "description": "",
  "personality": "",
  "scenario": "",
  "first_mes": "",
  "mes_example": "",
  "creator_notes": "",
  "backstory": "",
  "appearance": "",
  "tags": [],
  "alternate_greetings": [],
  "talkativeness": 50,
  "system_prompt": "",
  "post_history_instructions": ""
}"""

FIELD_GUIDES = {
    "name": "A fitting proper name only.",
    "summary": "One sentence for a library preview. Not roleplay prose.",
    "description": "120 to 220 words. Who they are. Use {{char}} and {{user}}.",
    "personality": "How they behave and speak. Concrete habits.",
    "backstory": "Origin, relationships, facts that stay true.",
    "appearance": "Face, build, clothes, and visual detail. Comma-separated tags are fine.",
    "scenario": "The default opening situation. Use {{char}} and {{user}}.",
    "first_mes": "80 to 180 words, in character, actions in asterisks. End on something {{user}} can answer.",
    "mes_example": "Two exchanges. Each begins with <START> on its own line.",
    "creator_notes": "A short note for the human, including tone or content if it matters.",
    "system_prompt": "Only if a hard rule is required. Otherwise empty string.",
    "post_history_instructions": "Only if a hard rule must sit after history. Otherwise empty string.",
    "creator": "Keep Cardwright unless the concept names an author.",
    "character_version": "A short version string, usually 1.0.",
}

STARTERS = (
    ("Night librarian", "A night librarian who shelves books that only exist between midnight and dawn, and already knows the reader's name."),
    ("Orbital welder", "An orbital welder who patches the station hull on twelve-hour shifts and talks to the dark like it might answer."),
    ("Last dragon", "The last dragon in a drowned valley, keeping a human village because the old bargain still stands."),
    ("Dock rigger", "A dock rigger who can tell a ship's cargo by the way it sits in the water, and who does not ask questions."),
    ("Flood courier", "A flood courier who carries letters across a city that is slowly going under, and never opens them."),
    ("Quiet archivist", "A quiet archivist of other people's secrets, paid to remember what the city would rather lose."),
    ("Train cook", "A train cook on a line that no longer appears on maps, feeding whoever is still riding."),
    ("Lighthouse keeper", "A lighthouse keeper on a coast where the light is for something that is not ships."),
)

STRING_FIELDS = (
    "name",
    "summary",
    "description",
    "personality",
    "scenario",
    "first_mes",
    "mes_example",
    "creator_notes",
    "system_prompt",
    "post_history_instructions",
    "creator",
    "character_version",
    "backstory",
    "appearance",
    "aliases",
    "long_memory",
)


def blank_card() -> dict:
    return {
        "name": "",
        "summary": "",
        "description": "",
        "personality": "",
        "scenario": "",
        "first_mes": "",
        "mes_example": "",
        "creator_notes": "",
        "system_prompt": "",
        "post_history_instructions": "",
        "tags": [],
        "creator": "Cardwright",
        "character_version": "1.0",
        "alternate_greetings": [],
        "backstory": "",
        "appearance": "",
        "talkativeness": 50,
        "aliases": "",
        "long_memory": "",
        "lorebook_id": "",
        "name_color": "",
        "dialogue_color": "",
        "box_color": "",
    }


def kobold_root(base: str) -> str:
    text = (base or DEFAULT_KOBOLD).strip().rstrip("/")
    if not text.startswith("http"):
        text = "http://" + text
    if not re.search(r"/v1$", text, re.I):
        text += "/v1"
    return text


def _request(url: str, payload: dict | None, headers: dict, timeout: int) -> tuple[int, bytes, str]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="GET" if payload is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        body = exc.read()
        raise RuntimeError(_http_error(exc.code, body)) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach KoboldCPP ({exc.reason}).") from exc


def _http_error(code: int, body: bytes) -> str:
    text = body.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        if data.get("error_code") == 1010 or "error-1010" in text:
            return "NovelAI blocked the request. Use this build of RedWright and try Draw again."
        for key in ("message", "detail", "title"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300] or f"The model returned HTTP {code}."


NOVEL_UA = "RedWright"


def novel_headers(token: str, accept: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token.strip()}",
        "Accept": accept,
        "User-Agent": NOVEL_UA,
    }


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


def kobold_chat(base: str, key: str, messages: list[dict], *, model: str = "koboldcpp", temperature: float = 0.8, max_tokens: int = 2200) -> str:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if key.strip():
        headers["Authorization"] = f"Bearer {key.strip()}"
    url = f"{kobold_root(base)}/chat/completions"
    _status, body, _kind = _request(
        url,
        {
            "model": model.strip() or "koboldcpp",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        headers,
        180,
    )
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("KoboldCPP did not return JSON.") from exc
    content = _message_text(((payload.get("choices") or [{}])[0].get("message") or {}).get("content"))
    if content.strip():
        return content
    raise RuntimeError("KoboldCPP returned an empty reply.")


def kobold_ping(base: str, key: str) -> str:
    headers = {"Accept": "application/json"}
    if key.strip():
        headers["Authorization"] = f"Bearer {key.strip()}"
    url = f"{kobold_root(base)}/models"
    try:
        _status, body, _kind = _request(url, None, headers, 8)
    except RuntimeError as exc:
        if "KoboldCPP" in str(exc):
            raise RuntimeError(str(exc).replace("KoboldCPP", "KoboldCPP")) from exc
        raise
    try:
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return "Connected to KoboldCPP."
    rows = data.get("data") if isinstance(data, dict) else None
    if isinstance(rows, list) and rows:
        name = rows[0].get("id") if isinstance(rows[0], dict) else None
        if name:
            return f"Connected. Model: {name}"
    return "Connected to KoboldCPP."


def _json_object(text: str) -> dict:
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if fenced:
        raw = fenced.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("The model did not return a JSON object.")
    value = json.loads(raw[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("The model did not return a JSON object.")
    return value


def _as_strings(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


_GREETING_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def greeting_picture_dir() -> Path:
    path = settings_path().parent / "redvn" / "greeting-pictures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def greeting_image_links(card: dict) -> list[str]:
    texts = [str(card.get("first_mes") or "")]
    texts.extend(str(item) for item in card.get("alternate_greetings") or [])
    found = []
    for text in texts:
        for match in _GREETING_IMAGE.finditer(text):
            url = match.group(2).strip().strip("<>")
            if url.lower().startswith(("http://", "https://")) and url not in found:
                found.append(url)
    return found


def _save_greeting_bytes(url: str, data: bytes) -> str:
    from PIL import Image

    folder = greeting_picture_dir()
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    dest = folder / f"{digest}.png"
    if dest.is_file() and dest.stat().st_size > 32:
        return str(dest)
    image = Image.open(BytesIO(data))
    image.seek(0)
    image.convert("RGB").save(dest, "PNG")
    return str(dest)


def pull_greeting_pictures(card: dict) -> tuple[dict, int, list[str]]:
    saved: dict[str, str] = {}
    errors: list[str] = []
    for url in greeting_image_links(card):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "RedWright"})
            with urllib.request.urlopen(request, timeout=40) as response:
                data = response.read(16_000_000)
            if not data:
                raise RuntimeError("empty picture")
            saved[url] = _save_greeting_bytes(url, data)
        except Exception as exc:
            errors.append(f"{url} ({exc})")

    def rewrite(text: str) -> str:
        def sub(match: re.Match) -> str:
            url = match.group(2).strip().strip("<>")
            local = saved.get(url)
            if not local:
                return match.group(0)
            return f"![{match.group(1)}]({local})"

        return _GREETING_IMAGE.sub(sub, text)

    updated = dict(card)
    updated["first_mes"] = rewrite(str(card.get("first_mes") or ""))
    updated["alternate_greetings"] = [rewrite(str(item)) for item in card.get("alternate_greetings") or []]
    return updated, len(saved), errors


def normalize_card(raw: dict, *, persona: bool = False) -> dict:
    card = blank_card()
    source = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    extensions = source.get("extensions") if isinstance(source.get("extensions"), dict) else {}
    for key in STRING_FIELDS:
        incoming = source.get(key)
        if not isinstance(incoming, str) and key in ("backstory", "appearance"):
            incoming = extensions.get(key)
        if isinstance(incoming, str):
            card[key] = incoming
    tags = _as_strings(source.get("tags"))
    if tags:
        card["tags"] = tags[:8]
    greetings = _as_strings(source.get("alternate_greetings"))
    if greetings:
        card["alternate_greetings"] = greetings
    talk = extensions.get("talkativeness", source.get("talkativeness"))
    if isinstance(talk, (int, float)) and not isinstance(talk, bool):
        card["talkativeness"] = max(0, min(100, int(round(talk))))
    aliases = source.get("aliases") or extensions.get("aliases") or extensions.get("nameAliases") or source.get("nameAliases") or ""
    if isinstance(aliases, list):
        aliases = "\n".join(str(item).strip() for item in aliases if str(item).strip())
    if isinstance(aliases, str):
        card["aliases"] = aliases
    for key, names in (
        ("name_color", ("name_color", "nameColor")),
        ("dialogue_color", ("dialogue_color", "dialogueColor")),
        ("box_color", ("box_color", "boxColor")),
    ):
        for place in (extensions, source):
            for name in names:
                value = place.get(name)
                if isinstance(value, str) and value.strip():
                    card[key] = value.strip()
                    break
            if card[key]:
                break
    memory = extensions.get("long_memory") or extensions.get("longMemory") or source.get("long_memory") or ""
    if isinstance(memory, str):
        card["long_memory"] = memory
    lore = extensions.get("cardwright_lorebook") or source.get("lorebook_id") or ""
    if isinstance(lore, str):
        card["lorebook_id"] = lore
    if not card["creator"].strip():
        card["creator"] = "Cardwright"
    if not card["character_version"].strip():
        card["character_version"] = "1.0"
    if persona:
        card["first_mes"] = ""
        card["alternate_greetings"] = []
    return card


def fill_blanks(current: dict, incoming: dict) -> dict:
    card = normalize_card(current)
    fresh = normalize_card(incoming)
    for key in STRING_FIELDS:
        if not str(card[key]).strip() and str(fresh[key]).strip():
            card[key] = fresh[key]
    if not card["tags"] and fresh["tags"]:
        card["tags"] = list(fresh["tags"])
    if not card["alternate_greetings"] and fresh["alternate_greetings"]:
        card["alternate_greetings"] = list(fresh["alternate_greetings"])
    return card


def character_book_from_lore(book: dict) -> dict:
    entries = []
    for index, row in enumerate(book.get("entries") or []):
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        entry = dict(source)
        keys = row.get("keys") or entry.get("keys") or entry.get("key") or []
        if isinstance(keys, str):
            keys = [part.strip() for part in keys.split(",") if part.strip()]
        entry["keys"] = [str(item) for item in keys if str(item).strip()]
        entry["content"] = row.get("content") or entry.get("content") or ""
        entry["enabled"] = bool(row.get("enabled", entry.get("enabled", True)))
        entry["constant"] = bool(row.get("constant", entry.get("constant", False)))
        entry["name"] = row.get("name") or entry.get("name") or ""
        entry["comment"] = row.get("description") or entry.get("comment") or ""
        entry.setdefault("insertion_order", index)
        entry.setdefault("id", index)
        entry.setdefault("extensions", {})
        entry.setdefault("case_sensitive", False)
        entry.setdefault("priority", 10)
        entry.setdefault("selective", False)
        entry.setdefault("secondary_keys", [])
        entry.setdefault("position", "before_char")
        entries.append(entry)
    return {
        "name": book.get("name") or "Lorebook",
        "description": book.get("description") or "",
        "scan_depth": 2,
        "token_budget": 512,
        "recursive_scanning": False,
        "extensions": {},
        "entries": entries,
    }


def lorebook_by_id(book_id: str) -> dict | None:
    if not book_id:
        return None
    import redvn

    for book in redvn.load_lorebooks():
        if book.get("id") == book_id:
            return book
    return None


def to_v2(card: dict, book: dict | None = None) -> dict:
    card = normalize_card(card)
    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": card["name"].strip() or "Unnamed",
            "summary": card["summary"],
            "description": card["description"],
            "personality": card["personality"],
            "scenario": card["scenario"],
            "first_mes": card["first_mes"],
            "mes_example": card["mes_example"],
            "creator_notes": card["creator_notes"],
            "system_prompt": card["system_prompt"],
            "post_history_instructions": card["post_history_instructions"],
            "tags": list(card["tags"]),
            "creator": card["creator"].strip() or "Cardwright",
            "character_version": card["character_version"].strip() or "1.0",
            "alternate_greetings": [item for item in card["alternate_greetings"] if item.strip()],
            "character_book": character_book_from_lore(book) if book else None,
            "extensions": {
                "talkativeness": card["talkativeness"],
                "fav": False,
                "backstory": card["backstory"],
                "appearance": card["appearance"],
                "aliases": card["aliases"],
                "long_memory": card["long_memory"],
                "cardwright_lorebook": card["lorebook_id"],
                "nameColor": card["name_color"],
                "dialogueColor": card["dialogue_color"],
                "boxColor": card["box_color"],
                "nameAliases": [line.strip() for line in str(card.get("aliases") or "").splitlines() if line.strip()],
            },
        },
    }


def _write(base: str, key: str, concept: str, *, persona: bool, model: str, temperature: float, max_tokens: int) -> dict:
    text = concept.strip()
    if len(text) < 8:
        kind = "persona" if persona else "character"
        raise RuntimeError(f"Describe the {kind} in a sentence or two, or add a reference picture.")
    system = PERSONA_SYSTEM if persona else CARD_SYSTEM
    user = ("Write a persona from this concept:\n" if persona else "Write a full character card from this concept:\n") + text + "\n\n" + SCHEMA_HINT
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    reply = kobold_chat(base, key, messages, model=model, temperature=temperature, max_tokens=max_tokens)
    try:
        return normalize_card(_json_object(reply), persona=persona)
    except (ValueError, json.JSONDecodeError):
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": "That was not valid JSON. Reply again with only the JSON object, no fences."})
        reply = kobold_chat(base, key, messages, model=model, temperature=temperature, max_tokens=max_tokens)
        try:
            return normalize_card(_json_object(reply), persona=persona)
        except (ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError("Could not read the card.") from exc


def write_card(base: str, key: str, concept: str, *, model: str = "koboldcpp", temperature: float = 0.8, max_tokens: int = 2200) -> dict:
    return _write(base, key, concept, persona=False, model=model, temperature=temperature, max_tokens=max_tokens)


def write_persona(base: str, key: str, concept: str, *, model: str = "koboldcpp", temperature: float = 0.8, max_tokens: int = 2200) -> dict:
    return _write(base, key, concept, persona=True, model=model, temperature=temperature, max_tokens=max_tokens)


def rewrite_field(base: str, key: str, concept: str, card: dict, field: str, *, model: str = "koboldcpp", temperature: float = 0.8) -> str:
    if field not in FIELD_GUIDES:
        raise RuntimeError(f"Unknown field: {field}")
    guide = FIELD_GUIDES[field]
    current = normalize_card(card)
    box = str(current.get(field) or "").strip()
    concept_text = concept.strip()
    others = {name: current[name] for name in STRING_FIELDS if name != field and str(current.get(name) or "").strip()}
    if not box and not others and len(concept_text) < 8:
        raise RuntimeError("Write a prompt in this box, or fill another field first.")
    if box:
        user = (
            f'Write only the "{field}" field. The note in the box is the prompt. Follow it. Do not write any other field.\n'
            f"Guide: {guide}\n"
            f"Prompt:\n{box}\n\n"
        )
        if others:
            user += "Other fields already filled, for consistency. Do not copy them into this field:\n" + json.dumps(others, ensure_ascii=False) + "\n\n"
        if concept_text:
            user += f"Concept, only if the prompt does not already cover it:\n{concept_text}\n\n"
    else:
        user = (
            f'Write only the "{field}" field. The box is empty, so use the other fields as the guidance. Do not write any other field.\n'
            f"Guide: {guide}\n"
        )
        if concept_text:
            user += f"Concept:\n{concept_text}\n\n"
        if others:
            user += "Other fields:\n" + json.dumps(others, ensure_ascii=False) + "\n\n"
    user += "Return only the field text. No label and no markdown."
    reply = kobold_chat(
        base,
        key,
        [
            {"role": "system", "content": "You fill one character-card field. Return only that field's text."},
            {"role": "user", "content": user},
        ],
        model=model,
        temperature=temperature,
        max_tokens=800,
    )
    text = reply.strip()
    try:
        payload = _json_object(text)
    except (ValueError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        value = payload.get("value", payload.get(field))
        if isinstance(value, str) and value.strip():
            return value.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:\w+)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def novel_prompt(card: dict) -> str:
    card = normalize_card(card)
    parts = [card["appearance"], card["name"], card["scenario"]]
    tags = []
    for part in parts:
        for piece in re.split(r"[,;\n]+", part):
            piece = piece.strip()
            if piece and piece not in tags:
                tags.append(piece)
    return ", ".join(tags)


def add_prefix_tags(current: str, addition: str) -> str:
    have = {part.strip().lower() for part in current.split(",") if part.strip()}
    extra = []
    for part in addition.split(","):
        tag = part.strip().strip(",")
        if tag and tag.lower() not in have:
            extra.append(tag)
            have.add(tag.lower())
    base = current.strip().rstrip(",").strip()
    if not extra:
        return base
    if not base:
        return ", ".join(extra)
    return base + ", " + ", ".join(extra)


def character_count(prompt: str) -> int | None:
    found = False
    total = 0
    for match in re.finditer(r"(\d+)\s*(?:girl|boy|person|people|character)s?", prompt, re.I):
        found = True
        total += int(match.group(1))
    return total if found else None


def novel_size(prompt: str, width: int, height: int, auto: bool) -> tuple[int, int]:
    if not auto:
        return width, height
    count = character_count(prompt)
    if count is None:
        return width, height
    if count <= 1:
        return 832, 1216
    if count == 2:
        return 1024, 1024
    return 1216, 832


def novel_body(prompt: str, settings: dict) -> dict:
    model = str(settings.get("model") or DEFAULT_NOVEL_MODEL).strip() or DEFAULT_NOVEL_MODEL
    prefix = str(settings.get("prefix") or "").strip()
    negative_prefix = str(settings.get("negative") or "").strip()
    text = ", ".join(part for part in (prefix, prompt.strip()) if part)
    negative = ", ".join(part for part in (negative_prefix, str(settings.get("extra_negative") or "").strip()) if part)
    width, height = novel_size(text, int(settings.get("width") or 1024), int(settings.get("height") or 1024), bool(settings.get("auto")))
    width = max(64, min(1792, width - width % 64))
    height = max(64, min(1792, height - height % 64))
    seed = int(settings.get("seed") if settings.get("seed") is not None else -1)
    used = random.randrange(0, 2**32) if seed < 0 else seed & 0xFFFFFFFF
    version = 4 if "diffusion-5" in model else 3
    parameters = {
        "params_version": version,
        "width": width,
        "height": height,
        "scale": float(settings.get("guidance") if settings.get("guidance") is not None else 6.8),
        "sampler": str(settings.get("sampler") or "k_euler_ancestral"),
        "steps": max(1, min(50, int(settings.get("steps") or 25))),
        "seed": used,
        "extra_noise_seed": used,
        "n_samples": 1,
        "prompt": text,
        "negative_prompt": negative,
        "qualityToggle": not bool(prefix),
        "ucPreset": int(settings.get("uc") if settings.get("uc") is not None else 2),
        "cfg_rescale": float(settings.get("rescale") or 0),
        "noise_schedule": str(settings.get("schedule") or "karras"),
        "legacy": False,
        "legacy_v3_extend": False,
        "uncond_scale": 1,
        "sm": False,
        "sm_dyn": False,
        "dynamic_thresholding": False,
        "controlnet_strength": 1,
        "add_original_image": False,
        "reference_image_multiple": [],
        "reference_information_extracted_multiple": [],
        "reference_strength_multiple": [],
        "v4_prompt": {
            "use_coords": False,
            "use_order": False,
            "caption": {"base_caption": text, "char_captions": []},
        },
        "v4_negative_prompt": {
            "use_coords": False,
            "use_order": False,
            "caption": {"base_caption": negative, "char_captions": []},
        },
    }
    plate = str(settings.get("plate") or "").strip()
    if plate and "4-5" in model and Path(plate).is_file():
        encoded = base64.b64encode(Path(plate).read_bytes()).decode("ascii")
        parameters["reference_image_multiple"] = [encoded]
        parameters["reference_strength_multiple"] = [float(settings.get("strength") if settings.get("strength") is not None else 0.65)]
        parameters["reference_information_extracted_multiple"] = [float(settings.get("fidelity") if settings.get("fidelity") is not None else 0.65)]
    return {
        "input": text,
        "model": model,
        "action": "generate",
        "parameters": parameters,
    }


def novel_ping(token: str) -> str:
    token = token.strip()
    if not token:
        raise RuntimeError("Add your NovelAI persistent token.")
    req = urllib.request.Request(
        "https://api.novelai.net/user/subscription",
        headers=novel_headers(token, "application/json"),
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_http_error(exc.code, exc.read()).replace("KoboldCPP", "NovelAI")) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach NovelAI ({exc.reason}).") from exc
    tier = payload.get("tier") if isinstance(payload, dict) else None
    return f"NovelAI accepted the token.{f' Tier {tier}.' if tier is not None else ''}"


def novel_generate(token: str, prompt: str, settings: dict | None = None, **legacy) -> "object":
    from PIL import Image

    token = token.strip()
    if not token:
        raise RuntimeError("Add your NovelAI persistent token.")
    if not prompt.strip() and not str((settings or {}).get("prefix") or legacy.get("negative") or "").strip():
        raise RuntimeError("Write an appearance, or a prompt, before drawing.")
    setup = {
        "model": legacy.get("model") or DEFAULT_NOVEL_MODEL,
        "width": legacy.get("width") or 1024,
        "height": legacy.get("height") or 1024,
        "steps": legacy.get("steps") or 25,
        "guidance": legacy.get("guidance") if legacy.get("guidance") is not None else 6.8,
        "seed": legacy.get("seed") if legacy.get("seed") is not None else -1,
        "extra_negative": legacy.get("negative") or "",
        "sampler": "k_euler_ancestral",
        "schedule": "karras",
        "uc": 2,
        "rescale": 0,
    }
    if settings:
        setup.update(settings)
    body = novel_body(prompt, setup)
    headers = novel_headers(token, "application/zip, image/png, application/json")
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        NOVEL_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            payload = response.read()
            kind = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_http_error(exc.code, exc.read()).replace("KoboldCPP", "NovelAI")) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach NovelAI ({exc.reason}).") from exc
    return _image_from_novel(payload, kind)


def _image_from_novel(payload: bytes, kind: str):
    from PIL import Image

    if payload[:8] == b"\x89PNG\r\n\x1a\n":
        return Image.open(BytesIO(payload)).convert("RGB")
    if payload[:2] == b"PK" or "zip" in kind:
        with zipfile.ZipFile(BytesIO(payload)) as bundle:
            names = [name for name in bundle.namelist() if name.lower().endswith(".png")]
            if not names:
                raise RuntimeError("NovelAI returned no picture.")
            return Image.open(BytesIO(bundle.read(names[0]))).convert("RGB")
    try:
        message = json.loads(payload.decode("utf-8")).get("message")
    except (UnicodeDecodeError, json.JSONDecodeError):
        message = None
    raise RuntimeError(message or "NovelAI did not return a picture.")


def text_plate(card: dict):
    from PIL import Image, ImageDraw

    card = normalize_card(card)
    image = Image.new("RGB", (832, 1216), "#1c1a17")
    draw = ImageDraw.Draw(image)
    draw.rectangle((36, 36, 796, 1180), outline="#e23d2b", width=3)
    name = card["name"].strip() or "Unnamed"
    summary = card["summary"].strip() or "No summary yet."
    draw.text((64, 72), name[:48], fill="#f4efe6")
    y = 130
    for word in _wrap(summary, 42):
        draw.text((64, y), word, fill="#a39b90")
        y += 22
        if y > 1100:
            break
    draw.text((64, 1140), "RedWright  ·  text plate, not a portrait", fill="#e23d2b")
    return image


def _wrap(text: str, width: int) -> list[str]:
    lines = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        line = ""
        for word in words:
            trial = word if not line else f"{line} {word}"
            if len(trial) > width:
                if line:
                    lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return lines or [""]


def pack_png(image, card: dict, book: dict | None = None) -> bytes:
    from PIL import PngImagePlugin

    info = PngImagePlugin.PngInfo()
    encoded = base64.b64encode(json.dumps(to_v2(card, book), ensure_ascii=False).encode("utf-8")).decode("ascii")
    info.add_text("chara", encoded)
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG", pnginfo=info)
    return buffer.getvalue()


def read_png_card(path: Path) -> dict | None:
    loaded = read_png_source(path)
    if loaded is None:
        return None
    return normalize_card(loaded[0])


def read_png_source(path: Path):
    from PIL import Image

    with Image.open(path) as image:
        raw = image.info.get("chara") or image.info.get("ccv3")
        picture = image.convert("RGB")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        decoded = json.loads(base64.b64decode(raw).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded, picture


def _data_url_image(value):
    if not isinstance(value, str) or not value.startswith("data:image") or "," not in value:
        return None
    from PIL import Image

    try:
        payload = base64.b64decode(value.split(",", 1)[1])
        return Image.open(BytesIO(payload)).convert("RGB")
    except (ValueError, OSError):
        return None


def marinara_kind(obj: dict) -> str | None:
    marker = obj.get("type")
    if marker == "marinara_persona":
        return "persona"
    if marker == "marinara_character":
        return "character"
    if marker in ("marinara_lorebook", "marinara_preset"):
        return ""
    if obj.get("spec") in ("chara_card_v2", "chara_card_v3"):
        return "character"
    persona_keys = {"personaVersion", "avatarCrop", "personaStats", "trackerCardColors", "convoBehavior", "savedStatusOptions", "isActive"}
    if "name" in obj and persona_keys.intersection(obj):
        return "persona"
    if isinstance(obj.get("data"), dict) or "name" in obj:
        return "character"
    return None


def iter_marinara(value):
    if isinstance(value, list):
        for item in value:
            yield from iter_marinara(item)
        return
    if not isinstance(value, dict):
        return
    if value.get("type") in ("marinara_character", "marinara_persona", "marinara_lorebook", "marinara_preset") or value.get("spec") in (
        "chara_card_v2",
        "chara_card_v3",
    ):
        yield value
        return
    listed = False
    for key in ("characters", "personas", "cards"):
        rows = value.get(key)
        if isinstance(rows, list):
            listed = True
            for item in rows:
                yield from iter_marinara(item)
    if not listed:
        yield value


def editor_card_from_source(kind: str, source: dict) -> dict:
    if kind == "persona":
        data = source.get("data") if source.get("type") == "marinara_persona" and isinstance(source.get("data"), dict) else source
        return normalize_card(
            {
                "name": data.get("name") or "",
                "summary": data.get("summary") or "",
                "description": data.get("description") or "",
                "personality": data.get("personality") or "",
                "scenario": data.get("scenario") or "",
                "mes_example": data.get("mes_example") or data.get("mesExample") or "",
                "creator_notes": data.get("creatorNotes") or data.get("creator_notes") or "",
                "creator": data.get("creator") or "",
                "character_version": data.get("personaVersion") or data.get("persona_version") or data.get("character_version") or "",
                "backstory": data.get("backstory") or "",
                "appearance": data.get("appearance") or "",
                "tags": data.get("tags") or [],
                "extensions": data.get("extensions") if isinstance(data.get("extensions"), dict) else {},
            },
            persona=True,
        )
    body = source.get("data") if source.get("type") == "marinara_character" and isinstance(source.get("data"), dict) else source
    return normalize_card(body)


def _write_colors(target: dict, card: dict) -> None:
    extensions = target.get("extensions") if isinstance(target.get("extensions"), dict) else {}
    extensions["aliases"] = card.get("aliases") or ""
    extensions["nameAliases"] = [line.strip() for line in str(card.get("aliases") or "").splitlines() if line.strip()]
    extensions["nameColor"] = card.get("name_color") or ""
    extensions["dialogueColor"] = card.get("dialogue_color") or ""
    extensions["boxColor"] = card.get("box_color") or ""
    target["extensions"] = extensions


def patch_source(source: dict, card: dict, kind: str) -> dict:
    copied = json.loads(json.dumps(source))
    if kind == "persona":
        target = copied["data"] if copied.get("type") == "marinara_persona" and isinstance(copied.get("data"), dict) else copied
        mapping = {
            "name": "name",
            "summary": "summary",
            "description": "description",
            "personality": "personality",
            "scenario": "scenario",
            "mes_example": "mes_example",
            "creator_notes": "creatorNotes",
            "creator": "creator",
            "character_version": "personaVersion",
            "backstory": "backstory",
            "appearance": "appearance",
        }
        for src, dest in mapping.items():
            if dest in target or str(card.get(src) or "").strip():
                target[dest] = card.get(src) or ""
        if "tags" in target or card.get("tags"):
            target["tags"] = list(card.get("tags") or [])
        _write_colors(target, card)
        return copied
    body = copied["data"] if copied.get("type") == "marinara_character" and isinstance(copied.get("data"), dict) else copied
    target = body["data"] if isinstance(body.get("data"), dict) else body
    for key in (
        "name",
        "summary",
        "description",
        "personality",
        "scenario",
        "first_mes",
        "mes_example",
        "creator_notes",
        "system_prompt",
        "post_history_instructions",
        "creator",
        "character_version",
    ):
        target[key] = card.get(key) or ""
    target["tags"] = list(card.get("tags") or [])
    target["alternate_greetings"] = [item for item in card.get("alternate_greetings") or [] if str(item).strip()]
    extensions = target.get("extensions") if isinstance(target.get("extensions"), dict) else {}
    extensions["backstory"] = card.get("backstory") or ""
    extensions["appearance"] = card.get("appearance") or ""
    extensions["aliases"] = card.get("aliases") or ""
    extensions["long_memory"] = card.get("long_memory") or ""
    extensions["talkativeness"] = card.get("talkativeness", 50)
    extensions["nameColor"] = card.get("name_color") or ""
    extensions["dialogueColor"] = card.get("dialogue_color") or ""
    extensions["boxColor"] = card.get("box_color") or ""
    extensions["nameAliases"] = [line.strip() for line in str(card.get("aliases") or "").splitlines() if line.strip()]
    target["extensions"] = extensions
    return copied


def avatar_from_source(source: dict):
    nodes = [source]
    data = source.get("data")
    if isinstance(data, dict):
        nodes.append(data)
        inner = data.get("data")
        if isinstance(inner, dict):
            nodes.append(inner)
    for node in nodes:
        for key in ("avatar", "avatarUrl", "image"):
            picture = _data_url_image(node.get(key))
            if picture is not None:
                return picture
    return None


def library_entry_from_source(source: dict, picture=None) -> dict | None:
    kind = marinara_kind(source)
    if not kind:
        return None
    card = editor_card_from_source(kind, source)
    if not str(card.get("name") or "").strip() and not str(card.get("description") or "").strip():
        return None
    if picture is None:
        picture = avatar_from_source(source)
    return {
        "id": uuid.uuid4().hex,
        "kind": kind,
        "concept": "",
        "card": card,
        "image": encode_card_image(picture) if picture is not None else "",
        "source": source,
    }


def read_marinara_file(path: Path) -> tuple[list[dict], int]:
    name = path.name.lower()
    if name.endswith(".png"):
        loaded = read_png_source(path)
        if loaded is None:
            return [], 1
        source, picture = loaded
        entry = library_entry_from_source(source, picture)
        return ([entry] if entry else []), 0 if entry else 1
    if name.endswith(".zip") or name.endswith(".marinara"):
        try:
            text = path.read_text(encoding="utf-8")
            return read_marinara_payload(json.loads(text))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        entries: list[dict] = []
        skipped = 0
        try:
            with zipfile.ZipFile(path) as bundle:
                names = [item for item in bundle.namelist() if not item.endswith("/")]
                for item in names:
                    lower = item.lower()
                    if lower.endswith(".png"):
                        from PIL import Image

                        raw = bundle.read(item)
                        image = Image.open(BytesIO(raw))
                        chara = image.info.get("chara") or image.info.get("ccv3")
                        if not isinstance(chara, str):
                            skipped += 1
                            continue
                        try:
                            source = json.loads(base64.b64decode(chara).decode("utf-8"))
                        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                            skipped += 1
                            continue
                        entry = library_entry_from_source(source, image.convert("RGB"))
                    elif lower.endswith(".json") or lower.endswith(".marinara"):
                        try:
                            payload = json.loads(bundle.read(item).decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            skipped += 1
                            continue
                        found, missed = read_marinara_payload(payload)
                        entries.extend(found)
                        skipped += missed
                        continue
                    else:
                        skipped += 1
                        continue
                    if entry is None:
                        skipped += 1
                    else:
                        entries.append(entry)
        except zipfile.BadZipFile as exc:
            raise RuntimeError(f"{path.name} is not a Marinara file.") from exc
        return entries, skipped
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{path.name} is not a Marinara JSON file.") from exc
    return read_marinara_payload(payload)


def read_marinara_payload(payload) -> tuple[list[dict], int]:
    entries = []
    skipped = 0
    for item in iter_marinara(payload):
        if not isinstance(item, dict):
            skipped += 1
            continue
        entry = library_entry_from_source(item)
        if entry is None:
            skipped += 1
        else:
            entries.append(entry)
    return entries, skipped


def books_in_path(path: Path) -> list[dict]:
    import redvn

    name = path.name.lower()
    if name.endswith(".png"):
        loaded = read_png_source(path)
        return redvn.books_attached_to(loaded[0]) if loaded else []
    if name.endswith(".zip") or name.endswith(".marinara"):
        try:
            return redvn.books_from_payload(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        books = []
        with zipfile.ZipFile(path) as bundle:
            for item in bundle.namelist():
                lower = item.lower()
                if lower.endswith(".json") or lower.endswith(".marinara"):
                    try:
                        books.extend(redvn.books_from_payload(json.loads(bundle.read(item).decode("utf-8"))))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                elif lower.endswith(".png"):
                    from PIL import Image

                    image = Image.open(BytesIO(bundle.read(item)))
                    chara = image.info.get("chara") or image.info.get("ccv3")
                    if not isinstance(chara, str):
                        continue
                    try:
                        source = json.loads(base64.b64decode(chara).decode("utf-8"))
                    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    books.extend(redvn.books_attached_to(source))
        return books
    payload = json.loads(path.read_text(encoding="utf-8"))
    return redvn.books_from_payload(payload)


def slug(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return text or "character"


def settings_path() -> Path:
    if sys.platform == "win32":
        root = Path.home() / "AppData" / "Roaming" / "RedGen"
    else:
        root = Path.home() / ".redgen"
    return root / "cards.json"


def load_settings() -> dict:
    base = {
        "kobold": DEFAULT_KOBOLD,
        "key": "",
        "model": "koboldcpp",
        "temperature": 0.8,
        "max_tokens": 2200,
    }
    base.update(NOVEL_SETTINGS)
    path = settings_path()
    if not path.is_file():
        return base
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return base
    if isinstance(data, dict):
        for key in base:
            if key in data:
                base[key] = data[key]
    return base


def save_settings(data: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def library_path() -> Path:
    return settings_path().parent / "card-library.json"


def load_library() -> list[dict]:
    path = library_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("cards") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    kept = []
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("id"), str) and isinstance(row.get("card"), dict):
            kept.append(row)
    return kept


def merge_library(entries: list[dict], entry: dict) -> list[dict]:
    items = [item for item in entries if item.get("id") != entry.get("id")]
    items.insert(0, entry)
    return items


def write_library(entries: list[dict]) -> None:
    path = library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"cards": entries}, indent=2, ensure_ascii=False), encoding="utf-8")


def encode_card_image(image, max_side: int = 768) -> str:
    from PIL import Image

    copy = image.convert("RGB") if image.mode != "RGB" else image.copy()
    copy.thumbnail((max_side, max_side))
    buf = BytesIO()
    copy.save(buf, format="JPEG", quality=82)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def default_novel_folder() -> Path:
    return Path.home() / "Pictures" / "RedWright" / "NovelAI"


def novel_library_path() -> Path:
    return settings_path().parent / "novel-library.json"


def load_novel_library() -> list[dict]:
    path = novel_library_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("pictures") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)]


def list_novel_folder(folder: Path) -> list[dict]:
    if not folder.is_dir():
        return []
    rows = []
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        meta: dict = {}
        side = path.with_suffix(".json")
        if side.is_file():
            try:
                data = json.loads(side.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    meta = data
            except (OSError, json.JSONDecodeError):
                meta = {}
        if not str(meta.get("prompt") or "").strip():
            text_path = path.with_suffix(".txt")
            if text_path.is_file():
                try:
                    meta["prompt"] = text_path.read_text(encoding="utf-8").strip()
                except OSError:
                    pass
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0
        rows.append(
            {
                "id": path.name,
                "path": str(path),
                "prompt": str(meta.get("prompt") or ""),
                "at": str(meta.get("at") or ""),
                "model": str(meta.get("model") or ""),
                "seed": meta.get("seed", -1),
                "mtime": mtime,
            }
        )
    rows.sort(key=lambda item: item.get("mtime") or 0, reverse=True)
    return rows


def save_novel_render(image, prompt: str, setup: dict | None = None, folder: str = "") -> dict:
    from datetime import datetime

    setup = setup or {}
    entry = {
        "id": uuid.uuid4().hex,
        "prompt": prompt.strip(),
        "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "model": str(setup.get("model") or ""),
        "seed": setup.get("seed", -1),
    }
    dest = Path(folder).expanduser() if str(folder or "").strip() else None
    if dest is None:
        entry["image"] = encode_card_image(image, 1216)
        path = novel_library_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"pictures": [entry, *load_novel_library()]}, ensure_ascii=False), encoding="utf-8")
        return entry
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file = dest / f"novelai-{stamp}.png"
    count = 2
    while file.exists():
        file = dest / f"novelai-{stamp}-{count}.png"
        count += 1
    image.save(file, "PNG")
    file.with_suffix(".json").write_text(
        json.dumps({key: entry[key] for key in ("prompt", "at", "model", "seed")}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    entry["id"] = file.name
    entry["path"] = str(file)
    return entry


def migrate_novel_rows(rows: list[dict], folder: Path) -> tuple[list[dict], int]:
    folder.mkdir(parents=True, exist_ok=True)
    kept = []
    moved = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        existing = str(row.get("path") or "")
        if existing and Path(existing).is_file():
            continue
        image = decode_card_image(str(row.get("image") or ""))
        if image is None:
            kept.append(row)
            continue
        ident = re.sub(r"[^A-Za-z0-9_-]", "", str(row.get("id") or ""))[:12] or uuid.uuid4().hex[:12]
        dest = folder / f"novelai-{ident}.png"
        if not dest.exists():
            image.save(dest, "PNG")
            dest.with_suffix(".json").write_text(
                json.dumps(
                    {
                        "prompt": str(row.get("prompt") or ""),
                        "at": str(row.get("at") or ""),
                        "model": str(row.get("model") or ""),
                        "seed": row.get("seed", -1),
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            moved += 1
    return kept, moved


def migrate_novel_library(folder: Path) -> int:
    kept, moved = migrate_novel_rows(load_novel_library(), folder)
    path = novel_library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pictures": kept}, ensure_ascii=False), encoding="utf-8")
    return moved


def remove_novel_render(entry: dict) -> None:
    path = Path(str(entry.get("path") or ""))
    if path.is_file():
        for extra in (path, path.with_suffix(".json"), path.with_suffix(".txt")):
            try:
                if extra.is_file():
                    extra.unlink()
            except OSError:
                pass
        return
    wanted = str(entry.get("id") or "")
    rows = [row for row in load_novel_library() if row.get("id") != wanted]
    path = novel_library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pictures": rows}, ensure_ascii=False), encoding="utf-8")


def decode_card_image(data: str):
    from PIL import Image

    if not isinstance(data, str) or not data.strip():
        return None
    try:
        return Image.open(BytesIO(base64.b64decode(data))).convert("RGB")
    except (OSError, ValueError):
        return None


def _link_slug(name: str, used: set[str]) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not text or text[0].isdigit():
        text = f"item_{text}".strip("_")
    text = (text[:40] or "item")
    choice = text
    count = 2
    while choice in used:
        choice = f"{text[:34]}_{count}"
        count += 1
    used.add(choice)
    return choice


def publish_link(home: Path, generated: str = "", subfolders: bool = False, novel: str = "") -> Path:
    """Write the folder Vangard reads when its RedWright button is clicked."""
    home = Path(home)
    link = home / "redwright-link"
    cards = link / "cards"
    held = link / "novel-held"
    cards.mkdir(parents=True, exist_ok=True)
    held.mkdir(parents=True, exist_ok=True)
    for folder in (cards, held):
        for old in folder.iterdir():
            if old.is_file() and old.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".json", ".txt"}:
                old.unlink()
    used: set[str] = set()
    for entry in load_library():
        card = entry.get("card") if isinstance(entry.get("card"), dict) else {}
        name = str(card.get("name") or "Unnamed").strip() or "Unnamed"
        slug_name = _link_slug(name, used)
        image = decode_card_image(str(entry.get("image") or ""))
        if image is not None:
            image.save(cards / f"{slug_name}.png", "PNG")
        (cards / f"{slug_name}.json").write_text(
            json.dumps(
                {
                    "name": name,
                    "summary": str(card.get("summary") or "")[:500],
                    "personality": str(card.get("personality") or "")[:500],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    loose = ""
    if not str(novel or "").strip():
        wrote = False
        for row in load_novel_library():
            image = decode_card_image(str(row.get("image") or ""))
            if image is None:
                continue
            name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(row.get("id") or "novel"))[:48] or "novel"
            image.save(held / f"{name}.png", "PNG")
            (held / f"{name}.json").write_text(
                json.dumps({"prompt": str(row.get("prompt") or "")}, ensure_ascii=False),
                encoding="utf-8",
            )
            wrote = True
        if wrote:
            loose = str(held)
    bridge = {
        "generated": str(generated or ""),
        "generatedSubfolders": bool(subfolders),
        "novel": str(novel or ""),
        "looseNovel": loose,
        "cards": str(cards),
        "home": str(home),
    }
    dest = link / "bridge.json"
    dest.write_text(json.dumps(bridge, indent=2), encoding="utf-8")
    pointer = settings_path().parent / "redwright-link.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps(bridge, indent=2), encoding="utf-8")
    return dest


def attach(app, book) -> None:
    import threading
    import tkinter as tk
    from tkinter import filedialog, ttk

    from PIL import Image

    BG, SURFACE, INSET, FG, MUTED = "#16080a", "#2a1214", "#140709", "#f6eee8", "#b39b94"
    PRIMARY, ACCENT_INK = "#e39b88", "#2a1210"
    PAPER, INK, GOLD = "#e6e1dc", "#1c1210", "#d4a574"
    frame = ttk.Frame(book, style="TFrame")
    book.add(frame, text="Cards")
    frame.columnconfigure(0, weight=1, minsize=280)
    frame.columnconfigure(1, weight=2, minsize=340)
    frame.columnconfigure(2, weight=1, minsize=260)
    frame.rowconfigure(0, weight=1)
    columns = []
    for index in range(3):
        host = ttk.Frame(frame, style="TFrame")
        host.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 6, 0))
        columns.append(app._make_scroller(host, bg=PAPER if index == 2 else SURFACE, style="Card.TFrame"))
    left, form, sheet = columns

    def heading(parent, text: str) -> None:
        ttk.Label(parent, text=text, style="Card.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(10, 0))

    def label(text: str) -> None:
        ttk.Label(form, text=text, style="Card.TLabel").pack(anchor="w", pady=(8, 0))

    def entry(parent, variable, secret: bool = False):
        widget = tk.Entry(
            parent,
            textvariable=variable,
            show="*" if secret else "",
            bg=INSET,
            fg=FG,
            insertbackground=FG,
            relief="flat",
        )
        widget.pack(fill="x", pady=(4, 0), ipady=4)
        return widget

    def area(parent, height: int) -> tk.Text:
        widget = tk.Text(parent, height=height, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word")
        widget.pack(fill="x", pady=(4, 0))
        return widget

    stored = load_settings()
    concept = area(left, 6)
    current_id = tk.StringVar()
    lore_choice = tk.StringVar()
    lore_ui = {"refresh": lambda: None}
    held = {"source": None, "kind": "character"}
    shown: list[str] = []
    kobold = tk.StringVar(value=stored["kobold"])
    key = tk.StringVar(value=stored["key"])
    model = tk.StringVar(value=stored["model"])
    temperature = tk.DoubleVar(value=float(stored.get("temperature") or 0.8))
    max_tokens = tk.IntVar(value=int(stored.get("max_tokens") or 16000))
    fill_empty = tk.BooleanVar(value=False)
    novel_token = tk.StringVar(value=str(stored.get("novel_token") or ""))
    novel_model = tk.StringVar(value=str(stored.get("novel_model") or DEFAULT_NOVEL_MODEL))
    novel_seed = tk.StringVar(value=str(stored.get("novel_seed") or "-1"))
    novel_style = tk.StringVar(value=str(stored.get("novel_style") or "Anime"))
    novel_danbooru = tk.BooleanVar(value=bool(stored.get("novel_danbooru", True)))
    novel_steps = tk.IntVar(value=int(stored.get("novel_steps") or 25))
    novel_guidance = tk.DoubleVar(value=float(stored.get("novel_guidance") if stored.get("novel_guidance") is not None else 6.8))
    novel_rescale = tk.DoubleVar(value=float(stored.get("novel_rescale") or 0))
    novel_uc = tk.IntVar(value=int(stored.get("novel_uc") if stored.get("novel_uc") is not None else 2))
    novel_sampler = tk.StringVar(value=str(stored.get("novel_sampler") or "k_euler_ancestral"))
    novel_schedule = tk.StringVar(value=str(stored.get("novel_schedule") or "karras"))
    novel_auto = tk.BooleanVar(value=bool(stored.get("novel_auto")))
    novel_width = tk.IntVar(value=int(stored.get("novel_width") or 1024))
    novel_height = tk.IntVar(value=int(stored.get("novel_height") or 1024))
    novel_strength = tk.DoubleVar(value=float(stored.get("novel_strength") if stored.get("novel_strength") is not None else 0.65))
    novel_fidelity = tk.DoubleVar(value=float(stored.get("novel_fidelity") if stored.get("novel_fidelity") is not None else 0.65))
    novel_plate = tk.StringVar(value=str(stored.get("novel_plate") or ""))
    novel_folder = tk.StringVar(value=str(stored.get("novel_folder") or ""))
    app._novel_folder_value = novel_folder
    fields: dict[str, tk.Text] = {}
    prefix_saved = str(stored.get("novel_prefix") or "")
    negative_saved = str(stored.get("novel_negative") or "")
    talk = tk.IntVar(value=50)
    name_color = tk.StringVar()
    dialogue_color = tk.StringVar()
    box_color = tk.StringVar()
    tags_var = tk.StringVar()
    greetings = None
    status = tk.Label(form, text="Idle", bg=SURFACE, fg=MUTED, wraplength=640, justify="left")
    sheet_name = tk.Label(sheet, text="Unnamed", bg=PAPER, fg=INK, font=("Georgia", 22), wraplength=280, justify="left")
    sheet_summary = tk.Label(sheet, text="No summary yet.", bg=PAPER, fg=INK, wraplength=280, justify="left")
    sheet_body = tk.Label(sheet, text="", bg=PAPER, fg=INK, wraplength=280, justify="left")
    sheet_photo = tk.Label(sheet, bg=PAPER)
    card_image = {"pil": None, "photo": None}
    painter = {"fn": lambda: None}

    def say(message: str) -> None:
        status.configure(text=message)

    def snapshot() -> dict:
        card = blank_card()
        for name, widget in fields.items():
            card[name] = widget.get("1.0", "end").strip()
        card["talkativeness"] = max(0, min(100, int(talk.get() or 0)))
        card["tags"] = [part.strip() for part in tags_var.get().split(",") if part.strip()]
        raw = greetings.get("1.0", "end") if greetings is not None else ""
        card["alternate_greetings"] = [part.strip() for part in re.split(r"\n\s*\n", raw) if part.strip()]
        card["lorebook_id"] = lore_choice.get()
        card["name_color"] = name_color.get().strip()
        card["dialogue_color"] = dialogue_color.get().strip()
        card["box_color"] = box_color.get().strip()
        return card

    def refresh_sheet() -> None:
        card = snapshot()
        sheet_name.configure(text=card["name"].strip() or "Unnamed")
        sheet_summary.configure(text=card["summary"].strip() or "No summary yet.")
        parts = []
        for key, title in (("description", "Description"), ("personality", "Personality"), ("scenario", "Scenario"), ("first_mes", "First message")):
            text = str(card.get(key) or "").strip()
            if text:
                parts.append(title.upper() + "\n" + text)
        sheet_body.configure(text="\n\n".join(parts))

    def show(card: dict) -> None:
        card = normalize_card(card)
        for name, widget in fields.items():
            widget.delete("1.0", "end")
            widget.insert("1.0", card.get(name, ""))
        talk.set(int(card["talkativeness"]))
        tags_var.set(", ".join(card.get("tags") or []))
        if greetings is not None:
            greetings.delete("1.0", "end")
            greetings.insert("1.0", "\n\n".join(card.get("alternate_greetings") or []))
        lore_choice.set(str(card.get("lorebook_id") or ""))
        name_color.set(str(card.get("name_color") or ""))
        dialogue_color.set(str(card.get("dialogue_color") or ""))
        box_color.set(str(card.get("box_color") or ""))
        lore_ui["refresh"]()
        refresh_sheet()

    def remember() -> None:
        save_settings(
            {
                "kobold": kobold.get().strip() or DEFAULT_KOBOLD,
                "key": key.get(),
                "model": model.get().strip() or "koboldcpp",
                "temperature": float(temperature.get() or 0.8),
                "max_tokens": int(max_tokens.get() or 16000),
                "novel_token": novel_token.get(),
                "novel_model": novel_model.get().strip() or DEFAULT_NOVEL_MODEL,
                "novel_seed": novel_seed.get().strip() or "-1",
                "novel_style": novel_style.get().strip() or "Anime",
                "novel_danbooru": bool(novel_danbooru.get()),
                "novel_steps": int(novel_steps.get() or 25),
                "novel_guidance": float(novel_guidance.get() or 6.8),
                "novel_rescale": float(novel_rescale.get() or 0),
                "novel_uc": int(novel_uc.get() or 0),
                "novel_prefix": novel_prefix.get("1.0", "end").strip(),
                "novel_negative": novel_negative.get("1.0", "end").strip(),
                "novel_sampler": novel_sampler.get().strip() or "k_euler_ancestral",
                "novel_schedule": novel_schedule.get().strip() or "karras",
                "novel_auto": bool(novel_auto.get()),
                "novel_width": int(novel_width.get() or 1024),
                "novel_height": int(novel_height.get() or 1024),
                "novel_strength": float(novel_strength.get() or 0.65),
                "novel_fidelity": float(novel_fidelity.get() or 0.65),
                "novel_plate": novel_plate.get().strip(),
                "novel_folder": novel_folder.get().strip(),
            }
        )

    def run(work, ok) -> None:
        say("Working…")

        def task() -> None:
            try:
                result = work()
            except Exception as exc:
                detail = str(exc)
                app.after(0, lambda detail=detail: say(detail))
                return
            app.after(0, lambda result=result: ok(result))

        threading.Thread(target=task, daemon=True).start()

    def on_card(card: dict, note: str) -> None:
        if fill_empty.get():
            current = snapshot()
            for name in STRING_FIELDS:
                if str(current.get(name) or "").strip():
                    card[name] = current[name]
            if current.get("tags"):
                card["tags"] = current["tags"]
            if current.get("alternate_greetings"):
                card["alternate_greetings"] = current["alternate_greetings"]
        show(card)
        persist(normalize_card({**card, "lorebook_id": card.get("lorebook_id") or lore_choice.get()}), concept.get("1.0", "end"), new=False)
        say(note + " Saved to the card library.")

    find = tk.StringVar()
    box = tk.Listbox(left, height=8, bg=INSET, fg=FG, selectbackground=PRIMARY, activestyle="none", relief="flat", highlightthickness=0)

    def refresh_library() -> None:
        box.unbind("<<ListboxSelect>>")
        shown.clear()
        box.delete(0, "end")
        query = find.get().strip().lower()
        chosen = current_id.get()
        pick = None
        for entry in load_library():
            name = str((entry.get("card") or {}).get("name") or "Unnamed")
            if entry.get("kind") == "persona":
                name = f"Persona · {name}"
            concept_text = str(entry.get("concept") or "")
            if query and query not in name.lower() and query not in concept_text.lower() and query not in str(entry.get("kind") or ""):
                continue
            shown.append(str(entry["id"]))
            box.insert("end", name)
            if entry["id"] == chosen:
                pick = len(shown) - 1
        if pick is not None:
            box.selection_set(pick)
            box.see(pick)
        box.bind("<<ListboxSelect>>", open_saved)
        painter["fn"]()

    def persist(card: dict, concept_text: str, *, new: bool) -> None:
        if not (str(card.get("name") or "").strip() or str(card.get("summary") or "").strip() or str(card.get("description") or "").strip()):
            return
        if new or not current_id.get():
            current_id.set(uuid.uuid4().hex)
            held["source"] = None
        stored = normalize_card(card, persona=held["kind"] == "persona")
        entry = {
            "id": current_id.get(),
            "kind": held["kind"],
            "concept": concept_text.strip(),
            "card": stored,
            "image": encode_card_image(card_image["pil"]) if card_image["pil"] is not None else "",
        }
        if held["source"] is not None:
            held["source"] = patch_source(held["source"], stored, held["kind"])
            entry["source"] = held["source"]
        write_library(merge_library(load_library(), entry))
        refresh_library()

    def set_card_image(image, *, save: bool = True) -> None:
        from PIL import ImageTk

        if image is None:
            card_image["pil"] = None
            card_image["photo"] = None
            sheet_photo.configure(image="")
        else:
            card_image["pil"] = image.convert("RGB") if image.mode != "RGB" else image.copy()
            preview = card_image["pil"].copy()
            preview.thumbnail((260, 360))
            photo = ImageTk.PhotoImage(preview)
            card_image["photo"] = photo
            sheet_photo.configure(image=photo)
        if save:
            persist(snapshot(), concept.get("1.0", "end"), new=False)

    def open_by_id(wanted: str, *, switch: bool) -> None:
        entry = next((item for item in load_library() if item.get("id") == wanted), None)
        if entry is None:
            return
        current_id.set(wanted)
        held["source"] = entry.get("source") if isinstance(entry.get("source"), dict) else None
        held["kind"] = "persona" if entry.get("kind") == "persona" else "character"
        show(entry["card"])
        concept.delete("1.0", "end")
        concept.insert("1.0", str(entry.get("concept") or ""))
        set_card_image(decode_card_image(str(entry.get("image") or "")), save=False)
        if switch:
            app.book.select(frame)
        say(f"Opened {entry['card'].get('name') or 'the card'}.")

    def open_saved(_event=None) -> None:
        selected = box.curselection()
        if not selected:
            return
        open_by_id(shown[selected[0]], switch=False)

    def remove_saved() -> None:
        selected = box.curselection()
        if not selected:
            return
        wanted = shown[selected[0]]
        write_library([item for item in load_library() if item.get("id") != wanted])
        if current_id.get() == wanted:
            current_id.set("")
            set_card_image(None, save=False)
        refresh_library()
        say("Removed that card from the library.")

    def clear_card() -> None:
        current_id.set("")
        held["source"] = None
        held["kind"] = "character"
        show(blank_card())
        set_card_image(None, save=False)
        concept.delete("1.0", "end")
        say("Started a new card.")

    def import_marinara() -> None:
        from tkinter import messagebox
        import redvn

        picked = filedialog.askopenfilenames(
            title="Marinara cards and personas",
            filetypes=[
                ("Marinara and cards", "*.json *.png *.zip *.marinara"),
                ("All files", "*.*"),
            ],
        )
        if not picked:
            return
        entries = load_library()
        added = 0
        skipped = 0
        problems = []
        linked: list[tuple[dict, list[dict]]] = []
        loose: list[dict] = []
        for item in picked:
            path = Path(item)
            try:
                found, missed = read_marinara_file(path)
                file_books = books_in_path(path)
            except Exception as exc:
                problems.append(f"{path.name}: {exc}")
                continue
            skipped += missed
            used = set()
            for record in found:
                attached = redvn.books_attached_to(record.get("source") or {})
                linked.append((record, attached))
                for book in attached:
                    used.add((str(book.get("name") or ""), len(book.get("entries") or [])))
                entries = merge_library(entries, record)
                added += 1
            for book in file_books:
                mark = (str(book.get("name") or ""), len(book.get("entries") or []))
                if mark not in used:
                    loose.append(book)
                    used.add(mark)
        if linked or loose:
            incoming = [book for _record, books in linked for book in books] + loose
            unique = []
            seen = set()
            for book in incoming:
                rows = book.get("entries") or []
                first = str(rows[0].get("content") or "")[:80] if rows else ""
                mark = (str(book.get("name") or ""), len(rows), first)
                if mark in seen:
                    continue
                seen.add(mark)
                unique.append(book)
            incoming = unique
            saved, names_note = redvn.ask_store_lorebooks(messagebox, incoming)
            if saved:

                def mark_of(book: dict) -> tuple:
                    rows = book.get("entries") or []
                    first = str(rows[0].get("content") or "")[:80] if rows else ""
                    return (str(book.get("name") or "Imported lorebook"), len(rows), first)

                by_mark = {mark_of(book): book for book in saved}
                for record, books in linked:
                    if not books:
                        continue
                    match = by_mark.get(mark_of(books[0]))
                    if match:
                        record.setdefault("card", {})["lorebook_id"] = match["id"]
                if len(linked) == 1 and not linked[0][1] and loose:
                    match = by_mark.get(mark_of(loose[0]))
                    if match:
                        linked[0][0].setdefault("card", {})["lorebook_id"] = match["id"]
        else:
            names_note = ""
        picture_cards = [record for record, _books in linked if greeting_image_links(record.get("card") or {})]

        def finish(extra: str = "") -> None:
            if added:
                write_library(entries)
                refresh_library()
            names = []
            if added:
                names.append(f"Imported {added}.")
            if skipped:
                names.append(f"Skipped {skipped} that were not cards or personas.")
            if problems:
                names.append(problems[0])
            say((" ".join(names) or "Nothing was imported.") + names_note + extra)

        if picture_cards and messagebox.askyesno(
            "Greeting pictures",
            f"{len(picture_cards)} card{'s' if len(picture_cards) != 1 else ''} link to pictures in the greetings.\nDownload them and keep them in the greetings for chat?",
        ):
            def work():
                total = 0
                failed = 0
                for record in picture_cards:
                    updated, count, errors = pull_greeting_pictures(record.get("card") or {})
                    record["card"] = updated
                    total += count
                    failed += len(errors)
                note = f" Saved {total} greeting picture{'s' if total != 1 else ''}."
                if failed:
                    note += f" {failed} could not be downloaded."
                return note

            run(work, lambda note: finish(note))
            return
        finish()

    heading(left, "Concept")
    ttk.Label(left, text="Who are they, where are they, and what should a chat feel like?", style="Muted.TLabel", wraplength=280).pack(anchor="w")
    concept.pack_forget()
    concept.pack(fill="x", pady=(4, 0))

    def ping() -> None:
        remember()
        run(lambda: kobold_ping(kobold.get(), key.get()), lambda note: say(note))

    def generate(persona: bool) -> None:
        remember()
        if not current_id.get():
            held["source"] = None
        if held["source"] is None:
            held["kind"] = "persona" if persona else "character"
        text = concept.get("1.0", "end")

        def work():
            kwargs = {"model": model.get(), "temperature": float(temperature.get() or 0.8), "max_tokens": int(max_tokens.get() or 16000)}
            if persona:
                return write_persona(kobold.get(), key.get(), text, **kwargs)
            return write_card(kobold.get(), key.get(), text, **kwargs)

        kind = "persona" if persona else "card"
        run(work, lambda card: on_card(card, f"Wrote the {kind}."))

    ttk.Button(left, text="Write the card", style="Primary.TButton", command=lambda: generate(False)).pack(fill="x", pady=(8, 0))
    ttk.Button(left, text="Write persona", command=lambda: generate(True)).pack(fill="x", pady=(6, 0))
    ttk.Button(left, text="Import Marinara", command=import_marinara).pack(fill="x", pady=(6, 0))
    tk.Checkbutton(
        left,
        text="Fill empty fields only",
        variable=fill_empty,
        bg=SURFACE,
        fg=FG,
        selectcolor=INSET,
        activebackground=SURFACE,
        activeforeground=FG,
    ).pack(anchor="w", pady=(6, 0))
    heading(left, "Starters")

    def use_starter(text: str) -> None:
        concept.delete("1.0", "end")
        concept.insert("1.0", text)

    for title, starter_text in STARTERS:
        ttk.Button(left, text=title, command=lambda starter_text=starter_text: use_starter(starter_text)).pack(fill="x", pady=(4, 0))
    heading(left, "KoboldCPP")
    ttk.Label(left, text="OpenAI endpoint", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    entry(left, kobold)
    ttk.Label(left, text="Usually http://127.0.0.1:5001/v1.", style="Muted.TLabel", wraplength=280).pack(anchor="w")
    ttk.Label(left, text="Password, if you set one", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    entry(left, key, secret=True)
    ttk.Label(left, text="Model", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    entry(left, model)
    ttk.Label(left, text="Temperature", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    tk.Spinbox(left, from_=0, to=2, increment=0.05, textvariable=temperature, bg=INSET, fg=FG, relief="flat").pack(anchor="w", pady=(4, 0))
    ttk.Label(left, text="Max tokens", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    entry(left, max_tokens)
    ttk.Button(left, text="Test connection", command=ping).pack(fill="x", pady=(8, 0))
    heading(left, "Library")
    entry(left, find)
    box.pack(fill="x", pady=(6, 0))
    box.bind("<<ListboxSelect>>", open_saved)
    find.trace_add("write", lambda *_args: refresh_library())
    library_row = ttk.Frame(left, style="Card.TFrame")
    library_row.pack(fill="x", pady=(6, 0))
    ttk.Button(library_row, text="New", command=clear_card).pack(side="left")
    ttk.Button(library_row, text="Remove", command=remove_saved).pack(side="left", padx=8)
    refresh_library()

    name_row = ttk.Frame(form, style="Card.TFrame")
    name_row.pack(fill="x")
    name_row.columnconfigure(0, weight=1)
    name_row.columnconfigure(1, weight=1)

    def field_block(name: str, title: str, tall: int) -> None:
        head = ttk.Frame(form, style="Card.TFrame")
        head.pack(fill="x", pady=(8, 0))
        ttk.Label(head, text=title, style="Card.TLabel").pack(side="left")

        def fill(field: str = name, label_text: str = title) -> None:
            remember()
            prompt = concept.get("1.0", "end")
            used_box = bool(fields[field].get("1.0", "end").strip())

            def work() -> str:
                return rewrite_field(
                    kobold.get(),
                    key.get(),
                    prompt,
                    snapshot(),
                    field,
                    model=model.get(),
                    temperature=float(temperature.get() or 0.8),
                )

            def ok(value: str) -> None:
                widget = fields[field]
                widget.delete("1.0", "end")
                widget.insert("1.0", value.strip())
                refresh_sheet()
                persist(snapshot(), prompt, new=False)
                source = "the note in that box" if used_box else "the other fields"
                say(f"Rewrote {label_text} from {source} and saved the card.")

            run(work, ok)

        ttk.Button(head, text="Rewrite", command=fill).pack(side="right")
        fields[name] = area(form, tall)
        fields[name].bind("<KeyRelease>", lambda _event: refresh_sheet())

    for name, title in (("name", "Name"), ("summary", "Summary")):
        cell = ttk.Frame(name_row, style="Card.TFrame")
        cell.grid(row=0, column=0 if name == "name" else 1, sticky="nsew", padx=(0 if name == "name" else 8, 0))
        ttk.Label(cell, text=title, style="Card.TLabel").pack(anchor="w")
        fields[name] = area(cell, 2)
        fields[name].bind("<KeyRelease>", lambda _event: refresh_sheet())
    for name, title, tall in (
        ("description", "Description", 6),
        ("personality", "Personality", 5),
        ("backstory", "Backstory", 5),
        ("appearance", "Appearance", 5),
        ("scenario", "Scenario", 4),
        ("first_mes", "First message", 5),
        ("mes_example", "Examples", 5),
        ("creator_notes", "Creator notes", 3),
        ("system_prompt", "System prompt", 3),
        ("post_history_instructions", "After history", 3),
        ("creator", "Creator", 2),
    ):
        field_block(name, title, tall)
    label("Tags")
    entry(form, tags_var)
    label("Alternate greetings")
    ttk.Label(form, text="Separate openings with a blank line.", style="Muted.TLabel").pack(anchor="w")
    greetings = area(form, 4)

    def download_greeting_pictures() -> None:
        from tkinter import messagebox

        card = snapshot()
        links = greeting_image_links(card)
        if not links:
            say("No picture links in the first message or alternate greetings.")
            return
        if not messagebox.askyesno(
            "Greeting pictures",
            f"Download {len(links)} picture{'s' if len(links) != 1 else ''} and keep them in the greetings?",
        ):
            return

        def work():
            return pull_greeting_pictures(card)

        def ok(result) -> None:
            updated, count, errors = result
            show(updated)
            persist(updated, concept.get("1.0", "end"), new=False)
            note = f"Saved {count} greeting picture{'s' if count != 1 else ''} into the greetings."
            if errors:
                note += f" {len(errors)} could not be downloaded."
            say(note)

        run(work, ok)

    ttk.Button(form, text="Download greeting pictures", command=download_greeting_pictures).pack(anchor="w", pady=(4, 0))
    label("Talkativeness, 0 to 100")
    tk.Scale(form, from_=0, to=100, orient="horizontal", variable=talk, bg=SURFACE, fg=FG, highlightthickness=0, troughcolor=INSET).pack(fill="x")

    def display_color(value: str, fallback: str) -> str:
        match = re.search(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", value or "")
        if not match:
            return fallback
        hexed = match.group(0)
        if len(hexed) == 4:
            hexed = "#" + "".join(ch * 2 for ch in hexed[1:])
        return hexed

    ttk.Label(form, text="Chat colors", style="Card.TLabel").pack(anchor="w", pady=(14, 0))
    ttk.Label(
        form,
        text="These colors travel with the card and color this character's messages. Empty dialogue uses the default. Empty box uses the sheet.",
        style="Muted.TLabel",
        wraplength=520,
    ).pack(anchor="w", pady=(2, 6))
    swatches = {}

    def color_line(title: str, variable: tk.StringVar, hint: str) -> None:
        from tkinter import colorchooser

        ttk.Label(form, text=title, style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        line = ttk.Frame(form, style="Card.TFrame")
        line.pack(fill="x")
        swatch = tk.Label(line, width=3, bg=INSET, relief="flat")
        swatch.pack(side="left", padx=(0, 8), ipady=6)
        box = tk.Entry(line, textvariable=variable, bg=INSET, fg=FG, insertbackground=FG, relief="flat")
        box.pack(side="left", fill="x", expand=True, ipady=4)
        swatches[title] = swatch

        def pick(_event=None) -> None:
            chosen = colorchooser.askcolor(color=display_color(variable.get(), "#e8b86d"), title=title)
            if chosen and chosen[1]:
                variable.set(chosen[1])

        swatch.bind("<Button-1>", pick)
        ttk.Label(form, text=hint, style="Muted.TLabel").pack(anchor="w")

    color_line("Name color", name_color, "Colors the name in chat.")
    color_line("Dialogue color", dialogue_color, "Empty uses the default text color. Colors words inside quotes.")
    color_line("Box color", box_color, "Empty uses the chat paper. Colors the message box.")
    preview = tk.Frame(form, bg="#f6f1e8", padx=12, pady=10, highlightthickness=0)
    preview.pack(fill="x", pady=(8, 4))
    preview_name = tk.Label(preview, text="Character", bg="#f6f1e8", fg="#e8b86d", font=("Segoe UI", 12, "bold"))
    preview_name.pack(anchor="w")
    preview_line = tk.Label(preview, text='They look over. "Stay close."', bg="#f6f1e8", fg="#2a211c", font=("Segoe UI", 11), justify="left")
    preview_line.pack(anchor="w")
    preview_act = tk.Label(preview, text="*A lamp flickers.*", bg="#f6f1e8", fg="#2a211c", font=("Segoe UI", 11))
    preview_act.pack(anchor="w")

    def paint_colors(*_args) -> None:
        name_hex = display_color(name_color.get(), "#e8b86d")
        dialogue_hex = display_color(dialogue_color.get(), "#2a211c")
        box_hex = display_color(box_color.get(), "#f6f1e8")
        swatches["Name color"].configure(bg=display_color(name_color.get(), INSET))
        swatches["Dialogue color"].configure(bg=display_color(dialogue_color.get(), INSET))
        swatches["Box color"].configure(bg=display_color(box_color.get(), INSET))
        preview.configure(bg=box_hex)
        preview_name.configure(bg=box_hex, fg=name_hex, text=(fields["name"].get("1.0", "end").strip() or "Character") if "name" in fields else "Character")
        preview_line.configure(bg=box_hex, fg=dialogue_hex)
        preview_act.configure(bg=box_hex, fg="#2a211c" if box_color.get().strip() else "#2a211c")

    for variable in (name_color, dialogue_color, box_color):
        variable.trace_add("write", paint_colors)
    paint_colors()
    label("Aliases")
    ttk.Label(form, text="Other names, one per line. Used when you write who should answer.", style="Muted.TLabel", wraplength=520).pack(anchor="w")
    fields["aliases"] = area(form, 3)

    def use_prompt() -> None:
        prompt = novel_prompt(snapshot())
        if not prompt:
            say("Write an appearance first.")
            return
        app.prompt.delete("1.0", "end")
        app.prompt.insert("1.0", prompt)
        app.book.select(0)
        say("Appearance is now the Generate prompt.")

    def draw_redgen() -> None:
        use_prompt()
        if not app._models:
            say("Add a model on Generate, then press Generate.")
            return
        app._generate(for_card=True)

    def draw_novel() -> None:
        text = novel_prompt(snapshot())
        if text:
            novel_prompt_box.delete("1.0", "end")
            novel_prompt_box.insert("1.0", text)
        app.book.select(novel_tab)
        draw_on_novel()

    def save_json() -> None:
        card = snapshot()
        book = lorebook_by_id(card.get("lorebook_id") or "")
        path = filedialog.asksaveasfilename(
            title="Save Character Card V2",
            defaultextension=".json",
            initialfile=f"{slug(card['name'])}.json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(json.dumps(to_v2(card, book), indent=2, ensure_ascii=False), encoding="utf-8")
        extra = f" The lorebook {book.get('name') or ''} is inside the card." if book else ""
        say("Saved a Character Card V2 file. Marinara imports it as JSON." + extra)

    def save_png() -> None:
        card = snapshot()
        book = lorebook_by_id(card.get("lorebook_id") or "")
        image = card_image["pil"]
        plate = image if image is not None else text_plate(card)
        path = filedialog.asksaveasfilename(
            title="Save PNG card",
            defaultextension=".png",
            initialfile=f"{slug(card['name'])}.png",
            filetypes=[("PNG", "*.png")],
        )
        if not path:
            return
        Path(path).write_bytes(pack_png(plate, card, book))
        note = "portrait" if image is not None else "text plate"
        extra = f" The lorebook {book.get('name') or ''} is inside the card." if book else ""
        say(f"Saved a PNG card. The picture is the {note}, and the card JSON is stored inside the file.{extra}")

    def load_file() -> None:
        from tkinter import messagebox
        import redvn

        path = filedialog.askopenfilename(title="Open a card", filetypes=[("Card", "*.json *.png"), ("All", "*.*")])
        if not path:
            return
        file = Path(path)
        portrait = None
        source = None
        if file.suffix.lower() == ".png":
            loaded = read_png_source(file)
            if loaded is None:
                say("That PNG has no character card in it.")
                return
            source, portrait = loaded
            card = normalize_card(source)
        else:
            try:
                source = json.loads(file.read_text(encoding="utf-8"))
                card = normalize_card(source)
            except (OSError, json.JSONDecodeError):
                say("That file is not a Cardwright card.")
                return
        attached = redvn.books_attached_to(source) if isinstance(source, dict) else []
        lore_note = ""
        if attached:
            saved, lore_note = redvn.ask_store_lorebooks(messagebox, attached)
            if saved:
                card["lorebook_id"] = saved[0]["id"]
        show(card)
        set_card_image(portrait, save=False)

        def finish(updated: dict, note: str) -> None:
            show(updated)
            set_card_image(portrait, save=False)
            persist(updated, concept.get("1.0", "end"), new=True)
            say(note)

        links = greeting_image_links(card)
        if links and messagebox.askyesno(
            "Greeting pictures",
            f"The greetings link to {len(links)} picture{'s' if len(links) != 1 else ''}.\nDownload them and keep them in the greeting for chat?",
        ):
            def work():
                updated, count, errors = pull_greeting_pictures(card)
                note = f"Loaded {file.name}. Saved {count} greeting picture{'s' if count != 1 else ''}."
                if errors:
                    note += f" {len(errors)} could not be downloaded."
                return updated, note

            run(work, lambda result: finish(result[0], result[1] + lore_note))
            return
        finish(card, f"Loaded {file.name}. Saved to the card library.{lore_note}")

    actions = ttk.Frame(form, style="Card.TFrame")
    actions.pack(fill="x", pady=(12, 4))
    ttk.Button(actions, text="Use appearance as prompt", command=use_prompt).pack(side="left")
    ttk.Button(actions, text="Draw with RedGen", command=draw_redgen).pack(side="left", padx=8)
    ttk.Button(actions, text="Draw with NovelAI", command=draw_novel).pack(side="left")
    def save_card() -> None:
        card = snapshot()
        if not (str(card.get("name") or "").strip() or str(card.get("summary") or "").strip() or str(card.get("description") or "").strip()):
            say("Write a name or some card text before saving.")
            return
        persist(card, concept.get("1.0", "end"), new=False)
        say("Saved the card in the library.")

    file_row = ttk.Frame(form, style="Card.TFrame")
    file_row.pack(fill="x", pady=(8, 0))
    ttk.Button(file_row, text="Save card", style="Primary.TButton", command=save_card).pack(side="left")
    ttk.Button(file_row, text="Save JSON", command=save_json).pack(side="left", padx=8)
    ttk.Button(file_row, text="Save PNG", command=save_png).pack(side="left", padx=8)
    ttk.Button(file_row, text="Open", command=load_file).pack(side="left")
    lore_row = ttk.Frame(form, style="Card.TFrame")
    lore_row.pack(fill="x", pady=(8, 0))
    ttk.Label(lore_row, text="Lorebook", style="Card.TLabel").pack(side="left")
    lore_label = tk.StringVar(value="None")
    lore_state = {"books": []}
    lore_box = ttk.Combobox(lore_row, textvariable=lore_label, state="readonly", width=32)
    lore_box.pack(side="left", padx=8)

    def refresh_lore_choices() -> None:
        import redvn

        books = redvn.load_lorebooks()
        lore_state["books"] = books
        labels = ["None"]
        chosen = "None"
        wanted = lore_choice.get()
        for book in books:
            label = f"{book.get('name') or 'Lorebook'} ({len(book.get('entries') or [])})"
            labels.append(label)
            if book.get("id") == wanted:
                chosen = label
        lore_box["values"] = labels
        lore_label.set(chosen)

    def pick_lore(_event=None) -> None:
        index = lore_box.current() - 1
        books = lore_state["books"]
        lore_choice.set(books[index]["id"] if 0 <= index < len(books) else "")
        persist(snapshot(), concept.get("1.0", "end"), new=False)
        book = lorebook_by_id(lore_choice.get())
        say("No lorebook on this card." if book is None else f"Attached {book.get('name') or 'the lorebook'}. Save JSON or Save PNG to put it inside the file.")

    lore_ui["refresh"] = refresh_lore_choices
    import redvn

    redvn.watch_lorebooks(refresh_lore_choices)
    lore_box.bind("<<ComboboxSelected>>", pick_lore)
    refresh_lore_choices()
    status.pack(anchor="w", pady=(10, 4))

    sheet_photo.pack(anchor="w", pady=(0, 8))
    tk.Label(sheet, text="CHARACTER SHEET", bg=PAPER, fg="#7a655c", font=("Segoe UI", 9, "bold")).pack(anchor="w")
    sheet_name.pack(anchor="w", pady=(6, 0))
    sheet_summary.pack(anchor="w", pady=(6, 0))
    tk.Frame(sheet, bg=GOLD, height=2).pack(fill="x", pady=(10, 8))
    sheet_body.pack(anchor="w")
    tk.Label(
        sheet,
        text="Backstory and appearance stay on the card. A PNG download uses the portrait and hides the same card inside the file.",
        bg=PAPER,
        fg="#7a655c",
        wraplength=280,
        justify="left",
    ).pack(anchor="w", pady=(12, 0))
    refresh_sheet()

    novel_tab = ttk.Frame(book, style="TFrame")
    book.add(novel_tab, text="NovelAI")
    novel_tab.columnconfigure(0, weight=1)
    novel_tab.columnconfigure(1, weight=1)
    novel_tab.rowconfigure(0, weight=1)
    left_host = ttk.Frame(novel_tab, style="TFrame")
    left_host.grid(row=0, column=0, sticky="nsew")
    right_host = ttk.Frame(novel_tab, style="TFrame")
    right_host.grid(row=0, column=1, sticky="nsew")
    left = app._make_scroller(left_host, bg=SURFACE, style="Card.TFrame")
    right = app._make_scroller(right_host, bg=SURFACE, style="Card.TFrame")
    from PIL import ImageTk

    novel_status = tk.Label(left, text="Idle", bg=SURFACE, fg=MUTED, wraplength=420, justify="left")

    def novel_say(message: str) -> None:
        novel_status.configure(text=message)

    def novel_setup() -> dict:
        seed_text = novel_seed.get().strip()
        try:
            seed = int(seed_text) if seed_text else -1
        except ValueError:
            seed = -1
        return {
            "model": novel_model.get(),
            "prefix": novel_prefix.get("1.0", "end"),
            "negative": novel_negative.get("1.0", "end"),
            "width": int(novel_width.get() or 1024),
            "height": int(novel_height.get() or 1024),
            "steps": int(novel_steps.get() or 25),
            "guidance": float(novel_guidance.get() or 6.8),
            "seed": seed,
            "rescale": float(novel_rescale.get() or 0),
            "uc": int(novel_uc.get() or 0),
            "sampler": novel_sampler.get(),
            "schedule": novel_schedule.get(),
            "auto": bool(novel_auto.get()),
            "plate": novel_plate.get(),
            "strength": float(novel_strength.get() or 0.65),
            "fidelity": float(novel_fidelity.get() or 0.65),
        }

    ttk.Label(left, text="Prompt", style="Card.TLabel").pack(anchor="w")
    novel_prompt_box = tk.Text(left, height=8, bg=BG, fg=FG, insertbackground=FG, relief="flat", wrap="word")
    novel_prompt_box.pack(fill="x", pady=(4, 6))
    prompt_row = ttk.Frame(left, style="Card.TFrame")
    prompt_row.pack(fill="x", pady=(0, 6))

    def use_appearance() -> None:
        text = novel_prompt(snapshot())
        novel_prompt_box.delete("1.0", "end")
        novel_prompt_box.insert("1.0", text)
        width, height = novel_size(text, int(novel_width.get() or 1024), int(novel_height.get() or 1024), bool(novel_auto.get()))
        novel_say(f"Appearance is the prompt. Requested size is {width}×{height} unless character count changes it.")

    def show_novel_image(image) -> None:
        copy = image.copy()
        copy.thumbnail((440, 620))
        photo = ImageTk.PhotoImage(copy)
        novel_view.image = photo
        novel_view.delete("all")
        novel_view.create_image(220, 300, image=photo)
        novel_caption.configure(text=snapshot()["name"].strip() or "Picture")

    def draw_on_novel() -> None:
        remember()
        prompt = novel_prompt_box.get("1.0", "end")
        setup = novel_setup()

        def work():
            return novel_generate(novel_token.get(), prompt, setup)

        def ok(image, elapsed: float = 0) -> None:
            took = f"{elapsed:.1f}s" if elapsed < 60 else f"{int(elapsed // 60)}m {int(round(elapsed % 60))}s"
            app._novel_image = image.convert("RGB") if image.mode != "RGB" else image.copy()
            show_novel_image(app._novel_image)
            name = snapshot()["name"].strip() or "Picture"
            novel_caption.configure(text=f"{name} · {took}")
            if novel_folder.get().strip():
                ready = "Picture ready. It is saved in the Novel library folder."
            else:
                ready = "Picture ready. Choose a Novel library folder and these pictures will move there."
            novel_say(f"{ready} Took {took}.")
            save_novel_render(app._novel_image, prompt, setup, novel_folder.get().strip())
            paint_novel()

        novel_say("Drawing with NovelAI…")
        started = time.perf_counter()

        def task() -> None:
            try:
                image = work()
            except Exception as exc:
                detail = str(exc)
                app.after(0, lambda detail=detail: novel_say(detail))
                return
            elapsed = time.perf_counter() - started
            app.after(0, lambda image=image, elapsed=elapsed: ok(image, elapsed))

        threading.Thread(target=task, daemon=True).start()

    def test_novel() -> None:
        remember()

        def task() -> None:
            try:
                note = novel_ping(novel_token.get())
            except Exception as exc:
                detail = str(exc)
                app.after(0, lambda detail=detail: novel_say(detail))
                return
            app.after(0, lambda note=note: novel_say(note))

        novel_say("Checking the NovelAI token…")
        threading.Thread(target=task, daemon=True).start()

    ttk.Button(prompt_row, text="Use appearance", command=use_appearance).pack(side="left")
    ttk.Button(prompt_row, text="Draw", style="Primary.TButton", command=draw_on_novel).pack(side="left", padx=8)
    ttk.Button(prompt_row, text="Test NovelAI", command=test_novel).pack(side="left")
    ttk.Label(
        left,
        text="Requested size is 1024×1024 unless character count changes it. A draw sends Anlas.",
        style="Muted.TLabel",
        wraplength=420,
    ).pack(anchor="w", pady=(4, 0))
    novel_caption = tk.Label(left, text="No picture yet", bg=SURFACE, fg=FG)
    novel_caption.pack(anchor="w", pady=(8, 0))
    novel_view = tk.Canvas(left, bg=BG, height=460, highlightthickness=0, cursor="hand2")
    novel_view.pack(fill="x", pady=(4, 6))

    def expand_novel(_event=None) -> None:
        image = getattr(app, "_novel_image", None)
        if image is None:
            novel_say("Draw a picture first.")
            return
        app._open_full_view(image, novel_caption.cget("text") or "NovelAI")

    novel_view.bind("<Button-1>", expand_novel)
    picture_row = ttk.Frame(left, style="Card.TFrame")
    picture_row.pack(fill="x")

    def save_picture() -> None:
        image = getattr(app, "_novel_image", None)
        if image is None:
            novel_say("Draw a picture first.")
            return
        path = filedialog.asksaveasfilename(title="Save picture", defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path:
            image.save(path)
            novel_say("Saved the picture.")

    def use_on_card() -> None:
        image = getattr(app, "_novel_image", None)
        if image is None:
            novel_say("Draw a picture first.")
            return
        novel_say("This picture is on the character sheet and saved with the card.")
        set_card_image(image, save=True)

    ttk.Button(picture_row, text="Save", style="Primary.TButton", command=save_picture).pack(side="left")
    ttk.Button(picture_row, text="Use on card", command=use_on_card).pack(side="left", padx=8)
    novel_status.pack(anchor="w", pady=(8, 4))

    ttk.Label(right, text="Account", style="Card.TLabel").pack(anchor="w")
    ttk.Label(right, text="Persistent token", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    tk.Entry(right, textvariable=novel_token, show="*", bg=BG, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", ipady=4)
    ttk.Label(right, text="The pst- token stays on this computer and is sent only to NovelAI.", style="Muted.TLabel", wraplength=420).pack(anchor="w")
    ttk.Label(right, text="Model", style="Muted.TLabel").pack(anchor="w", pady=(8, 0))
    model_names = [label for label, _mid in NOVEL_MODELS]
    model_ids = {label: mid for label, mid in NOVEL_MODELS}
    model_labels = {mid: label for label, mid in NOVEL_MODELS}
    model_label = tk.StringVar(value=model_labels.get(novel_model.get(), "V5 Full"))
    plate_note = tk.Label(right, text="", bg=SURFACE, fg=MUTED, wraplength=420, justify="left")

    def apply_model(*_args) -> None:
        novel_model.set(model_ids.get(model_label.get(), DEFAULT_NOVEL_MODEL))
        if "diffusion-5" in novel_model.get():
            plate_note.configure(text="V5 does not take a style plate. Switch to V4.5 to use it.")
        else:
            plate_note.configure(text="A persistent style-only reference applied first to every V4.5 generation, including scenes without characters.")

    ttk.Combobox(right, textvariable=model_label, values=model_names, state="readonly").pack(fill="x", pady=(2, 0))
    model_label.trace_add("write", apply_model)

    ttk.Label(right, text="NovelAI generation setup", style="Card.TLabel").pack(anchor="w", pady=(14, 0))
    ttk.Label(right, text="Prompt prefixes, sampler, scheduler, steps, guidance, seed, and resolution.", style="Muted.TLabel", wraplength=420).pack(anchor="w")
    head_row = ttk.Frame(right, style="Card.TFrame")
    head_row.pack(fill="x", pady=(6, 0))
    ttk.Label(head_row, text="Seed -1 keeps generation random. Any non-negative seed is reused exactly.", style="Muted.TLabel", wraplength=280).pack(side="left")

    def fill_text(widget: tk.Text, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def reset_novel() -> None:
        novel_seed.set("-1")
        novel_style.set("Anime")
        novel_danbooru.set(False)
        novel_steps.set(25)
        novel_guidance.set(6.8)
        novel_rescale.set(0)
        novel_uc.set(2)
        novel_sampler.set("k_euler_ancestral")
        novel_schedule.set("karras")
        novel_auto.set(False)
        novel_width.set(1024)
        novel_height.set(1024)
        novel_strength.set(0.65)
        novel_fidelity.set(0.65)
        fill_text(novel_prefix, DEFAULT_NOVEL_PREFIX)
        fill_text(novel_negative, DEFAULT_NOVEL_NEGATIVE)
        apply_style()
        novel_say("Reset the NovelAI setup.")

    ttk.Button(head_row, text="Reset", command=reset_novel).pack(side="right")

    def pair_row() -> ttk.Frame:
        row = ttk.Frame(right, style="Card.TFrame")
        row.pack(fill="x", pady=(8, 0))
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        return row

    def entry_cell(row: ttk.Frame, column: int, title: str, variable) -> None:
        cell = ttk.Frame(row, style="Card.TFrame")
        cell.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        ttk.Label(cell, text=title, style="Muted.TLabel").pack(anchor="w")
        tk.Entry(cell, textvariable=variable, bg=BG, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", ipady=4)

    seed_row = pair_row()
    entry_cell(seed_row, 0, "Seed", novel_seed)
    style_cell = ttk.Frame(seed_row, style="Card.TFrame")
    style_cell.grid(row=0, column=1, sticky="ew", padx=(8, 0))
    style_head = ttk.Frame(style_cell, style="Card.TFrame")
    style_head.pack(fill="x")
    ttk.Label(style_head, text="Style profile", style="Muted.TLabel").pack(side="left")

    def use_danbooru() -> None:
        novel_style.set("Danbooru")
        apply_style()

    ttk.Button(style_head, text="Use Danbooru / Illustrious", command=use_danbooru).pack(side="right")
    style_box = ttk.Combobox(style_cell, textvariable=novel_style, values=("Anime", "Semi-realistic", "Furry", "Danbooru"), state="readonly")
    style_box.pack(fill="x", pady=(2, 0))
    style_hint = ttk.Label(style_cell, text="Choosing a profile adds its tags to the prompt prefix. It does not replace what is already there.", style="Muted.TLabel", wraplength=220)
    style_hint.pack(anchor="w")

    numbers = pair_row()
    entry_cell(numbers, 0, "Steps", novel_steps)
    entry_cell(numbers, 1, "Prompt guidance", novel_guidance)
    guides = pair_row()
    entry_cell(guides, 0, "Guidance rescale", novel_rescale)
    entry_cell(guides, 1, "UC preset", novel_uc)
    ttk.Label(right, text="UC preset: 0 heavy, 1 light, 2 human focus, 3 none, 4 as in your setup.", style="Muted.TLabel", wraplength=420).pack(anchor="w")

    def prefix_box(saved: str) -> tk.Text:
        widget = tk.Text(right, height=3, bg=BG, fg=FG, insertbackground=FG, relief="flat", wrap="word")
        widget.pack(fill="x", pady=(2, 0))
        if saved:
            widget.insert("1.0", saved)
        return widget

    ttk.Label(right, text="Prompt prefix", style="Muted.TLabel").pack(anchor="w", pady=(8, 0))
    novel_prefix = prefix_box(prefix_saved)
    ttk.Label(right, text="Negative prefix", style="Muted.TLabel").pack(anchor="w", pady=(8, 0))
    novel_negative = prefix_box(negative_saved)

    def apply_style(*_args) -> None:
        profile = NOVEL_STYLES.get(novel_style.get().strip())
        if profile is None:
            novel_say("That style profile is not set up.")
            return
        current = novel_prefix.get("1.0", "end")
        fill_text(novel_prefix, add_prefix_tags(current, profile["prefix"]))
        novel_danbooru.set(novel_style.get().strip() == "Danbooru")
        style_hint.configure(text=profile["note"])
        novel_say(profile["note"])

    style_box.bind("<<ComboboxSelected>>", apply_style)
    sample_row = pair_row()
    sample_cell = ttk.Frame(sample_row, style="Card.TFrame")
    sample_cell.grid(row=0, column=0, sticky="ew")
    ttk.Label(sample_cell, text="Sampler", style="Muted.TLabel").pack(anchor="w")
    sampler_values = list(NOVEL_SAMPLERS)
    if novel_sampler.get() not in sampler_values:
        sampler_values.insert(0, novel_sampler.get())
    ttk.Combobox(sample_cell, textvariable=novel_sampler, values=sampler_values, state="readonly").pack(fill="x", pady=(2, 0))
    noise_cell = ttk.Frame(sample_row, style="Card.TFrame")
    noise_cell.grid(row=0, column=1, sticky="ew", padx=(8, 0))
    ttk.Label(noise_cell, text="Noise schedule", style="Muted.TLabel").pack(anchor="w")
    schedule_values = list(NOVEL_SCHEDULES)
    if novel_schedule.get() not in schedule_values:
        schedule_values.insert(0, novel_schedule.get())
    ttk.Combobox(noise_cell, textvariable=novel_schedule, values=schedule_values, state="readonly").pack(fill="x", pady=(2, 0))
    tk.Checkbutton(
        right,
        text="Choose resolution from character count",
        variable=novel_auto,
        bg=SURFACE,
        fg=FG,
        selectcolor=BG,
        activebackground=SURFACE,
        activeforeground=FG,
    ).pack(anchor="w", pady=(8, 0))
    ttk.Label(
        right,
        text="Uses portrait for one subject, square for two, and landscape for three or more. Free-form prompts without a detectable count keep the requested size.",
        style="Muted.TLabel",
        wraplength=420,
    ).pack(anchor="w")
    size_row = pair_row()
    entry_cell(size_row, 0, "Width", novel_width)
    entry_cell(size_row, 1, "Height", novel_height)
    plate_head = ttk.Frame(right, style="Card.TFrame")
    plate_head.pack(fill="x", pady=(12, 0))
    ttk.Label(plate_head, text="NovelAI V4.5 style plate", style="Card.TLabel").pack(side="left")

    def choose_plate() -> None:
        path = filedialog.askopenfilename(title="Style plate", filetypes=[("Pictures", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")])
        if path:
            novel_plate.set(path)
            novel_say("Style plate selected. V4.5 uses it. V5 ignores it.")

    ttk.Button(plate_head, text="Choose image", command=choose_plate).pack(side="right")
    plate_note.pack(anchor="w")
    ttk.Label(right, textvariable=novel_plate, style="Muted.TLabel", wraplength=420).pack(anchor="w")
    vibe = pair_row()
    entry_cell(vibe, 0, "Style strength", novel_strength)
    entry_cell(vibe, 1, "Style fidelity", novel_fidelity)
    apply_model()

    library_tab = ttk.Frame(book, style="TFrame")
    book.insert(book.index(frame) + 1, library_tab, text="Card library")
    library_tab.columnconfigure(0, weight=1)
    library_tab.rowconfigure(1, weight=1)
    bar = ttk.Frame(library_tab, style="Card.TFrame", padding=12)
    bar.grid(row=0, column=0, sticky="ew")
    ttk.Label(bar, text="Card library", style="Card.TLabel").pack(anchor="w")
    ttk.Label(bar, text="Click a card to open it. Import keeps every Marinara field, including sprites, gallery, colors, and stats.", style="Muted.TLabel", wraplength=720).pack(anchor="w", pady=(2, 0))
    ttk.Button(bar, text="Import Marinara", command=import_marinara).pack(anchor="w", pady=(8, 0))
    card_find = tk.StringVar()
    tk.Entry(bar, textvariable=card_find, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", pady=(6, 0), ipady=4)
    host = ttk.Frame(library_tab, style="TFrame")
    host.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
    card_canvas = tk.Canvas(host, bg=BG, highlightthickness=0, bd=0)
    card_scroll = ttk.Scrollbar(host, orient="vertical", command=card_canvas.yview)
    card_canvas.configure(yscrollcommand=card_scroll.set)
    card_scroll.pack(side="right", fill="y")
    card_canvas.pack(side="left", fill="both", expand=True)
    card_inner = ttk.Frame(card_canvas, style="TFrame")
    card_window = card_canvas.create_window((0, 0), window=card_inner, anchor="nw")
    thumbs: list = []

    def fit_cards(_event=None) -> None:
        if getattr(card_canvas, "_fit_job", None):
            return

        def run() -> None:
            card_canvas._fit_job = None
            try:
                width = max(card_canvas.winfo_width(), 1)
                if getattr(card_canvas, "_fit_width", None) != width:
                    card_canvas._fit_width = width
                    card_canvas.itemconfigure(card_window, width=width)
                card_canvas.configure(scrollregion=card_canvas.bbox("all") or (0, 0, 0, 0))
            except tk.TclError:
                pass

        card_canvas._fit_job = card_canvas.after_idle(run)

    card_inner.bind("<Configure>", fit_cards)
    card_canvas.bind("<Configure>", fit_cards)
    app._scroll_canvases.append(card_canvas)

    def paint_cards() -> None:
        from PIL import ImageTk

        for child in card_inner.winfo_children():
            child.destroy()
        thumbs.clear()
        query = card_find.get().strip().lower()
        row = 0
        col = 0
        count = 0
        for entry in load_library():
            card = entry.get("card") or {}
            name = str(card.get("name") or "Unnamed")
            if entry.get("kind") == "persona":
                name = f"{name}\nPersona"
            blurb = str(entry.get("concept") or "")
            if query and query not in name.lower() and query not in blurb.lower() and query not in str(entry.get("kind") or ""):
                continue
            count += 1
            cell = tk.Frame(card_inner, bg=SURFACE, padx=8, pady=8, highlightbackground="#5a3330", highlightthickness=1)
            cell.grid(row=row, column=col, sticky="n", padx=8, pady=8)
            image = decode_card_image(str(entry.get("image") or ""))
            if image is not None:
                thumb = image.copy()
                thumb.thumbnail((140, 186))
                photo = ImageTk.PhotoImage(thumb)
                thumbs.append(photo)
                pic = tk.Label(cell, image=photo, bg=SURFACE, cursor="hand2")
            else:
                pic = tk.Label(cell, text="No picture", bg=INSET, fg=MUTED, width=16, height=9, cursor="hand2")
            pic.pack()
            caption = tk.Label(cell, text=name, bg=SURFACE, fg=FG, wraplength=140, cursor="hand2")
            caption.pack(pady=(6, 0))

            def open_entry(_event=None, wanted=str(entry["id"])) -> None:
                open_by_id(wanted, switch=True)

            for widget in (pic, caption, cell):
                widget.bind("<Button-1>", open_entry)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        if count == 0:
            tk.Label(card_inner, text="No cards yet. Write one on the Cards tab.", bg=BG, fg=MUTED).grid(row=0, column=0, sticky="w", padx=8, pady=8)
        fit_cards()

    painter["fn"] = paint_cards
    card_find.trace_add("write", lambda *_args: paint_cards())
    paint_cards()
    app._apply_card_portrait = lambda image: set_card_image(image, save=True)

    novel_library_tab = ttk.Frame(book, style="TFrame")
    book.add(novel_library_tab, text="Novel library")
    novel_library_tab.columnconfigure(0, weight=1)
    novel_library_tab.rowconfigure(1, weight=1)
    novel_bar = ttk.Frame(novel_library_tab, style="Card.TFrame", padding=12)
    novel_bar.grid(row=0, column=0, sticky="ew")
    ttk.Label(novel_bar, text="Novel library", style="Card.TLabel").pack(anchor="w")
    ttk.Label(novel_bar, text="Pick a folder. Pictures that were only stored in the app are copied in the first time you choose it.", style="Muted.TLabel", wraplength=720).pack(anchor="w", pady=(2, 0))
    folder_row = ttk.Frame(novel_bar, style="Card.TFrame")
    folder_row.pack(fill="x", pady=(8, 0))
    tk.Entry(folder_row, textvariable=novel_folder, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, ipady=4)

    def pick_novel_folder() -> None:
        current = novel_folder.get().strip()
        initial = current if current and Path(current).is_dir() else str(Path.home() / "Pictures")
        picked = filedialog.askdirectory(title="NovelAI library folder", initialdir=initial)
        if not picked:
            return
        novel_folder.set(picked)
        try:
            moved = migrate_novel_library(Path(picked))
        except OSError as exc:
            novel_say(f"Could not use that folder. {exc}")
            return
        remember()
        paint_novel()
        if moved:
            novel_say(f"Novel library folder is {picked}. Moved {moved} saved picture{'s' if moved != 1 else ''} into it.")
        else:
            novel_say(f"Novel library folder is {picked}.")

    ttk.Button(folder_row, text="Browse", command=pick_novel_folder).pack(side="left", padx=(8, 0))
    ttk.Button(folder_row, text="Refresh", command=lambda: paint_novel()).pack(side="left", padx=(8, 0))
    novel_find = tk.StringVar()
    tk.Entry(novel_bar, textvariable=novel_find, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", pady=(6, 0), ipady=4)
    novel_host = ttk.Frame(novel_library_tab, style="TFrame")
    novel_host.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
    novel_canvas = tk.Canvas(novel_host, bg=BG, highlightthickness=0, bd=0)
    novel_scroll = ttk.Scrollbar(novel_host, orient="vertical", command=novel_canvas.yview)
    novel_canvas.configure(yscrollcommand=novel_scroll.set)
    novel_scroll.pack(side="right", fill="y")
    novel_canvas.pack(side="left", fill="both", expand=True)
    novel_inner = ttk.Frame(novel_canvas, style="TFrame")
    novel_window = novel_canvas.create_window((0, 0), window=novel_inner, anchor="nw")
    novel_thumbs: list = []

    def fit_novel(_event=None) -> None:
        if getattr(novel_canvas, "_fit_job", None):
            return

        def run() -> None:
            novel_canvas._fit_job = None
            try:
                width = max(novel_canvas.winfo_width(), 1)
                if getattr(novel_canvas, "_fit_width", None) != width:
                    novel_canvas._fit_width = width
                    novel_canvas.itemconfigure(novel_window, width=width)
                novel_canvas.configure(scrollregion=novel_canvas.bbox("all") or (0, 0, 0, 0))
            except tk.TclError:
                pass

        novel_canvas._fit_job = novel_canvas.after_idle(run)

    novel_inner.bind("<Configure>", fit_novel)
    novel_canvas.bind("<Configure>", fit_novel)
    app._scroll_canvases.append(novel_canvas)

    def view_novel(entry: dict) -> None:
        path = str(entry.get("path") or "")
        image = None
        if path and Path(path).is_file():
            try:
                image = Image.open(path).convert("RGB")
            except OSError:
                image = None
        if image is None:
            image = decode_card_image(str(entry.get("image") or ""))
        if image is None:
            novel_say("That picture could not be opened.")
            return
        prompt = str(entry.get("prompt") or "")
        app._novel_image = image
        show_novel_image(image)
        novel_prompt_box.delete("1.0", "end")
        novel_prompt_box.insert("1.0", prompt)
        title = prompt.replace("\n", " ").strip() or str(entry.get("at") or "NovelAI")
        novel_caption.configure(text=title[:80])
        gallery = [str(item.get("path") or "") for item in getattr(app, "_novel_gallery", [])]
        gallery = [item for item in gallery if item and Path(item).is_file()]
        index = gallery.index(path) if path in gallery else 0
        app._open_full_view(image, title[:80], prompt or "No prompt was saved with this picture.", gallery, index)
        novel_say("Opened the picture. Escape closes it.")

    def paint_novel() -> None:
        from PIL import ImageTk

        for child in novel_inner.winfo_children():
            child.destroy()
        novel_thumbs.clear()
        query = novel_find.get().strip().lower()
        row = 0
        col = 0
        count = 0
        folder_text = novel_folder.get().strip()
        entries = list_novel_folder(Path(folder_text)) if folder_text else load_novel_library()
        visible = []
        for entry in entries:
            prompt = str(entry.get("prompt") or "")
            if query and query not in prompt.lower():
                continue
            visible.append(entry)
            count += 1
            cell = tk.Frame(novel_inner, bg=SURFACE, padx=8, pady=8, highlightbackground="#5a3330", highlightthickness=1)
            cell.grid(row=row, column=col, sticky="n", padx=8, pady=8)
            image = None
            picture_path = str(entry.get("path") or "")
            if picture_path and Path(picture_path).is_file():
                try:
                    image = Image.open(picture_path).convert("RGB")
                except OSError:
                    image = None
            if image is None:
                image = decode_card_image(str(entry.get("image") or ""))
            if image is not None:
                thumb = image.copy()
                thumb.thumbnail((140, 186))
                photo = ImageTk.PhotoImage(thumb)
                novel_thumbs.append(photo)
                pic = tk.Label(cell, image=photo, bg=SURFACE, cursor="hand2")
            else:
                pic = tk.Label(cell, text="No picture", bg=INSET, fg=MUTED, width=16, height=9)
            pic.pack()
            caption_text = prompt.replace("\n", " ").strip() or "Untitled"
            if len(caption_text) > 80:
                caption_text = caption_text[:77] + "..."
            caption = tk.Label(cell, text=caption_text, bg=SURFACE, fg=FG, wraplength=140, cursor="hand2")
            caption.pack(pady=(6, 0))
            when = tk.Label(cell, text=str(entry.get("at") or ""), bg=SURFACE, fg=MUTED)
            when.pack()

            def open_picture(_event=None, item=entry) -> None:
                view_novel(item)

            def drop_picture(item=entry) -> None:
                remove_novel_render(item)
                paint_novel()

            for widget in (pic, caption, cell):
                widget.bind("<Button-1>", open_picture)
            ttk.Button(cell, text="Remove", command=drop_picture).pack(pady=(4, 0))
            col += 1
            if col >= 4:
                col = 0
                row += 1
        app._novel_gallery = visible
        if count == 0:
            tk.Label(novel_inner, text="No pictures in this folder yet." if folder_text else "No NovelAI pictures yet. Choose a folder, or draw one on the NovelAI tab.", bg=BG, fg=MUTED).grid(row=0, column=0, sticky="w", padx=8, pady=8)
        fit_novel()

    novel_find.trace_add("write", lambda *_args: paint_novel())
    paint_novel()

    def remember_card() -> None:
        remember()
        persist(snapshot(), concept.get("1.0", "end"), new=False)

    app.cards_remember = remember_card


def selftest() -> int:
    from PIL import Image

    card = normalize_card(
        {
            "spec": "chara_card_v2",
            "data": {
                "name": "June Pell",
                "description": "Keeps the clinic calendar.",
                "extensions": {"talkativeness": 140, "appearance": "short brown hair, wool coat"},
                "tags": ["town", ""],
            },
        }
    )
    assert card["name"] == "June Pell"
    assert card["talkativeness"] == 100
    assert card["appearance"] == "short brown hair, wool coat"
    assert card["tags"] == ["town"]
    packed = to_v2(card)
    assert packed["spec"] == "chara_card_v2"
    assert packed["data"]["extensions"]["appearance"].startswith("short")
    assert kobold_root("127.0.0.1:5001") == "http://127.0.0.1:5001/v1"
    assert kobold_root("http://127.0.0.1:5001/v1/") == "http://127.0.0.1:5001/v1"
    assert novel_headers("pst-x", "application/json")["User-Agent"] == "RedWright"
    image = text_plate(card)
    raw = pack_png(image, card)
    path = Path(__file__).resolve().parent / "_selftest_card.png"
    path.write_bytes(raw)
    try:
        loaded = read_png_card(path)
        assert loaded is not None and loaded["name"] == "June Pell"
        with Image.open(path) as check:
            assert check.size == (832, 1216)
    finally:
        path.unlink(missing_ok=True)
    prompt = novel_prompt(card)
    assert "wool coat" in prompt
    counted = novel_body(
        "1girl, red coat",
        {
            "model": "nai-diffusion-5-full",
            "prefix": "score_9",
            "negative": "low quality",
            "width": 1024,
            "height": 1024,
            "steps": 25,
            "guidance": 6.8,
            "seed": 5,
            "uc": 2,
            "sampler": "k_euler_ancestral",
            "schedule": "karras",
            "rescale": 0,
            "auto": True,
            "plate": "missing.png",
        },
    )
    assert counted["parameters"]["params_version"] == 4
    assert counted["parameters"]["ucPreset"] == 2
    assert counted["parameters"]["sampler"] == "k_euler_ancestral"
    assert counted["parameters"]["prompt"] == counted["input"]
    assert counted["parameters"]["v4_prompt"]["caption"]["base_caption"] == counted["input"]
    assert counted["parameters"]["width"] == 832 and counted["parameters"]["height"] == 1216
    assert counted["parameters"]["reference_image_multiple"] == []
    assert counted["input"].startswith("score_9")
    assert novel_size("1girl and 1boy", 832, 1216, True) == (1024, 1024)
    assert novel_size("a quiet room", 1024, 1024, True) == (1024, 1024)
    assert add_prefix_tags("score_9_up, detailed skin", "very aesthetic, detailed skin, masterpiece") == "score_9_up, detailed skin, very aesthetic, masterpiece"
    merged = merge_library([{"id": "a", "card": {"name": "Old"}}], {"id": "b", "card": {"name": "New"}})
    assert [item["id"] for item in merged] == ["b", "a"]
    plate = Image.new("RGB", (32, 48), (180, 90, 70))
    restored = decode_card_image(encode_card_image(plate))
    assert restored is not None and restored.size == (32, 48)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        kept, moved = migrate_novel_rows(
            [{"id": "oldpic", "prompt": "red coat", "image": encode_card_image(plate), "at": "2026-11-21 01:00"}],
            Path(tmp),
        )
        assert moved == 1 and kept == []
        assert (Path(tmp) / "novelai-oldpic.png").is_file()
        again, moved_again = migrate_novel_rows(
            [{"id": "filepic", "path": str(Path(tmp) / "novelai-oldpic.png"), "prompt": "already filed"}],
            Path(tmp),
        )
        assert moved_again == 0 and again == []
    persona = {
        "type": "marinara_persona",
        "version": 1,
        "data": {
            "name": "June",
            "description": "The night clerk.",
            "personality": "Dry.",
            "personaVersion": "3.2",
            "creatorNotes": "Do not rush her.",
            "sprites": [{"id": "coat", "label": "Coat"}],
            "trackerCardColors": {"nameColor": "#e39b88"},
            "avatar": "data:image/png;base64,aaa",
        },
    }
    found, missed = read_marinara_payload(persona)
    assert missed == 0 and len(found) == 1 and found[0]["kind"] == "persona"
    assert found[0]["card"]["description"] == "The night clerk."
    assert found[0]["card"]["creator_notes"] == "Do not rush her."
    assert found[0]["source"]["data"]["sprites"][0]["id"] == "coat"
    changed = dict(found[0]["card"])
    changed["description"] = "The morning clerk."
    patched = patch_source(found[0]["source"], changed, "persona")
    assert patched["data"]["description"] == "The morning clerk."
    assert patched["data"]["sprites"][0]["label"] == "Coat"
    assert patched["data"]["trackerCardColors"]["nameColor"] == "#e39b88"
    character = {
        "type": "marinara_character",
        "version": 1,
        "data": {
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "sprites": [{"id": "smile"}],
            "gallery": [{"id": "sheet"}],
            "data": {"name": "Pell", "description": "Keeps the ledger.", "extensions": {"appearance": "wool coat"}},
        },
    }
    found, missed = read_marinara_payload([character, {"type": "marinara_lorebook", "version": 1, "data": {}}])
    assert missed == 1 and found[0]["kind"] == "character"
    assert found[0]["card"]["appearance"] == "wool coat"
    assert found[0]["source"]["data"]["gallery"][0]["id"] == "sheet"
    print("cardwright selftest ok")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        raise SystemExit(selftest())
    print("Open Redwright from redgen.py. This file is the card generator it imports.", flush=True)
