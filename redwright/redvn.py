"""RedVN — chat that can be exported as a visual novel."""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path

import cardwright


def store_root() -> Path:
    path = cardwright.settings_path().parent / "redvn"
    path.mkdir(parents=True, exist_ok=True)
    (path / "chats").mkdir(exist_ok=True)
    (path / "pictures").mkdir(exist_ok=True)
    return path


def _read_json(path: Path, fallback):
    if not path.is_file():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_chats() -> list[dict]:
    rows = []
    for path in (store_root() / "chats").glob("*.json"):
        data = _read_json(path, None)
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            rows.append(data)
    rows.sort(key=lambda row: str(row.get("updated") or ""), reverse=True)
    return rows


def load_chat(chat_id: str) -> dict | None:
    data = _read_json(store_root() / "chats" / f"{chat_id}.json", None)
    return data if isinstance(data, dict) else None


def save_chat(chat: dict) -> None:
    chat["updated"] = datetime.now().isoformat(timespec="seconds")
    _write_json(store_root() / "chats" / f"{chat['id']}.json", chat)


def delete_chat(chat_id: str) -> None:
    path = store_root() / "chats" / f"{chat_id}.json"
    if path.is_file():
        path.unlink()


def load_lorebooks() -> list[dict]:
    data = _read_json(store_root() / "lorebooks.json", {"books": []})
    books = data.get("books") if isinstance(data, dict) else []
    return [book for book in books if isinstance(book, dict) and isinstance(book.get("id"), str)]


def save_lorebooks(books: list[dict]) -> None:
    _write_json(store_root() / "lorebooks.json", {"books": books})


def load_memory() -> list[dict]:
    data = _read_json(store_root() / "memory.json", {"facts": []})
    facts = data.get("facts") if isinstance(data, dict) else []
    return [fact for fact in facts if isinstance(fact, dict) and str(fact.get("text") or "").strip()]


def save_memory(facts: list[dict]) -> None:
    _write_json(store_root() / "memory.json", {"facts": facts})


def blank_chat() -> dict:
    return {
        "id": uuid.uuid4().hex,
        "title": "New chat",
        "created": datetime.now().isoformat(timespec="seconds"),
        "updated": datetime.now().isoformat(timespec="seconds"),
        "character_id": "",
        "character_ids": [],
        "speaker_id": "",
        "persona_id": "",
        "lorebook_id": "",
        "lorebook_ids": [],
        "preset_id": "",
        "auto_background": False,
        "image_engine": "NovelAI",
        "messages": [],
    }


def message(role: str, text: str, speaker_id: str = "") -> dict:
    return {"id": uuid.uuid4().hex, "role": role, "speaker_id": speaker_id, "swipes": [text], "swipe": 0, "image": "", "location": ""}


def character_ids(chat: dict) -> list[str]:
    ids = [str(item) for item in chat.get("character_ids") or [] if str(item).strip()]
    legacy = str(chat.get("character_id") or "")
    if legacy and legacy not in ids:
        ids.insert(0, legacy)
    chat["character_ids"] = ids
    if ids and not chat.get("character_id"):
        chat["character_id"] = ids[0]
    return ids


def speaker_name(chat: dict, row: dict) -> str:
    if row.get("role") == "user":
        return card_name(find_card(chat.get("persona_id") or ""), "You")
    return card_name(find_card(str(row.get("speaker_id") or chat.get("speaker_id") or chat.get("character_id") or "")), "Character")


def appearances(chat: dict) -> str:
    lines = []
    persona = find_card(chat.get("persona_id") or "")
    look = str(((persona or {}).get("card") or {}).get("appearance") or "").strip()
    if look:
        lines.append(f"{card_name(persona, 'You')}: {look}")
    for card_id in character_ids(chat):
        entry = find_card(card_id)
        look = str(((entry or {}).get("card") or {}).get("appearance") or "").strip()
        if look:
            lines.append(f"{card_name(entry, 'Character')}: {look}")
    return "\n".join(lines)


def shown_text(row: dict) -> str:
    swipes = row.get("swipes") if isinstance(row.get("swipes"), list) else [""]
    swipes = [str(item) for item in swipes] or [""]
    index = int(row.get("swipe") or 0)
    index = max(0, min(len(swipes) - 1, index))
    row["swipe"] = index
    row["swipes"] = swipes
    return swipes[index]


_EMBEDDED_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def embedded_pictures(text: str) -> tuple[str, list[str]]:
    paths = []

    def sub(match: re.Match) -> str:
        target = match.group(2).strip().strip("<>")
        if Path(target).is_file():
            paths.append(str(Path(target)))
            return ""
        return match.group(0)

    cleaned = _EMBEDDED_IMAGE.sub(sub, text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, paths


_LIBRARY = {"stamp": None, "rows": [], "by_id": {}}


def library_rows() -> list[dict]:
    path = cardwright.library_path()
    try:
        stamp = path.stat().st_mtime_ns if path.is_file() else 0
    except OSError:
        stamp = 0
    if stamp != _LIBRARY["stamp"]:
        rows = cardwright.load_library()
        _LIBRARY["stamp"] = stamp
        _LIBRARY["rows"] = rows
        _LIBRARY["by_id"] = {str(row.get("id")): row for row in rows if isinstance(row, dict)}
    return _LIBRARY["rows"]


def cards_by_kind() -> tuple[list[dict], list[dict]]:
    characters = []
    personas = []
    for entry in library_rows():
        if entry.get("kind") == "persona":
            personas.append(entry)
        else:
            characters.append(entry)
    return characters, personas


def find_card(card_id: str) -> dict | None:
    library_rows()
    return _LIBRARY["by_id"].get(str(card_id or ""))


def lorebook_ids(chat: dict) -> list[str]:
    ids = [str(item) for item in chat.get("lorebook_ids") or [] if str(item).strip()]
    legacy = str(chat.get("lorebook_id") or "")
    if legacy and legacy not in ids:
        ids.insert(0, legacy)
    chat["lorebook_ids"] = ids
    chat["lorebook_id"] = ids[0] if ids else ""
    return ids


def active_lore_ids(chat: dict) -> list[str]:
    ids = list(lorebook_ids(chat))
    for card_id in [*character_ids(chat), str(chat.get("persona_id") or "")]:
        entry = find_card(card_id)
        linked = str(((entry or {}).get("card") or {}).get("lorebook_id") or "")
        if linked and linked not in ids:
            ids.append(linked)
    return ids


def routed_lore(chat: dict, scene: str) -> list[str]:
    books = {book["id"]: book for book in load_lorebooks()}
    chosen = []
    for book_id in active_lore_ids(chat):
        for entry in route_lore(books.get(book_id), scene, limit=4, budget=900):
            if entry not in chosen:
                chosen.append(entry)
    return chosen[:12]


def expand_names(text: str, user_name: str, char_name: str = "") -> str:
    if not text:
        return ""
    text = re.sub(r"\{\{\s*user\s*\}\}", user_name or "You", text, flags=re.I)
    if char_name:
        text = re.sub(r"\{\{\s*char\s*\}\}", char_name, text, flags=re.I)
    return text


def card_name(entry: dict | None, fallback: str) -> str:
    if not entry:
        return fallback
    return str((entry.get("card") or {}).get("name") or fallback).strip() or fallback


def _words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9']{4,}", text.lower())}


def route_lore(book: dict | None, scene: str, limit: int = 6, budget: int = 1800) -> list[str]:
    if not book:
        return []
    ranked = []
    scene_words = _words(scene)
    lowered = scene.lower()
    for entry in book.get("entries") or []:
        if not isinstance(entry, dict) or entry.get("enabled") is False:
            continue
        content = str(entry.get("content") or "").strip()
        if not content:
            continue
        if entry.get("constant"):
            ranked.append((0, content))
            continue
        keys = entry.get("keys") if isinstance(entry.get("keys"), list) else str(entry.get("keys") or "").split(",")
        keys = [str(key).strip().lower() for key in keys if str(key).strip()]
        if any(key and key in lowered for key in keys):
            ranked.append((1, content))
            continue
        description = str(entry.get("description") or "")
        if _words(description) & scene_words:
            ranked.append((2, content))
    ranked.sort(key=lambda item: item[0])
    chosen = []
    used = 0
    for _rank, content in ranked:
        if len(chosen) >= limit or used + len(content) > budget:
            continue
        chosen.append(content)
        used += len(content)
    return chosen


def recall_memory(facts: list[dict], scene: str, limit: int = 6) -> list[str]:
    scene_words = _words(scene)
    scored = []
    for fact in facts:
        text = str(fact.get("text") or "").strip()
        if not text:
            continue
        score = len(scene_words & _words(text))
        if score:
            scored.append((score, text))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [text for _score, text in scored[:limit]]


def system_prompt(chat: dict, scene: str, speaker_id: str = "", direction: str = "") -> str:
    persona = find_card(chat.get("persona_id") or "")
    person = (persona or {}).get("card") or {}
    user_name = card_name(persona, "You")
    cast = [find_card(card_id) for card_id in character_ids(chat)]
    cast = [entry for entry in cast if entry]
    speaker = find_card(speaker_id) if speaker_id else (cast[0] if cast else None)
    speaker_card = (speaker or {}).get("card") or {}
    name = card_name(speaker, "Character")
    others = [card_name(entry, "Character") for entry in cast if entry is not speaker]
    lines = [
        f"You are {name} in a visual novel chat. The person you are talking with is {user_name}.",
        "Write only the next reply, in character. Use *asterisks* for action.",
    ]
    if others:
        lines.append("Also present: " + ", ".join(others) + ". Do not speak for them.")
    for entry in cast:
        if entry is speaker:
            continue
        card = entry.get("card") or {}
        brief = " ".join(str(card.get(key) or "").strip() for key in ("summary", "personality") if str(card.get(key) or "").strip())
        if brief:
            lines.append(f"{card_name(entry, 'Character')}: {brief[:500]}")
    for label, key in (
        ("Description", "description"),
        ("Personality", "personality"),
        ("Scenario", "scenario"),
        ("Appearance", "appearance"),
        ("Backstory", "backstory"),
        ("Examples", "mes_example"),
    ):
        value = expand_names(str(speaker_card.get(key) or "").strip(), user_name, name)
        if value:
            lines.append(f"{label}:\n{value}")
    if str(speaker_card.get("system_prompt") or "").strip():
        lines.append(expand_names(str(speaker_card["system_prompt"]).strip(), user_name, name))
    if str(person.get("description") or "").strip() or str(person.get("personality") or "").strip():
        lines.append(expand_names(f"{user_name} is:\n{person.get('description', '')}\n{person.get('personality', '')}".strip(), user_name, name))
    if direction.strip():
        lines.append("Follow this for this reply:\n" + direction.strip())
    pinned = str(speaker_card.get("long_memory") or "").strip()
    memories = recall_memory(load_memory() + list(chat.get("memory") or []), scene)
    if pinned:
        memories.insert(0, pinned)
    if memories:
        lines.append("Long-term memory. Use a fact only when it matters:\n" + "\n".join(f"- {item}" for item in memories[:8]))
    lore = routed_lore(chat, scene)
    if lore:
        lines.append("Lore. Use these entries as written:\n" + "\n\n".join(lore))
    return "\n\n".join(lines)


def transcript(chat: dict, stop_id: str = "") -> list[dict]:
    rows = []
    for row in chat.get("messages") or []:
        if stop_id and row.get("id") == stop_id:
            break
        role = "user" if row.get("role") == "user" else "assistant"
        user_name = card_name(find_card(chat.get("persona_id") or ""), "You")
        text = expand_names(shown_text(row), user_name, speaker_name(chat, row))
        if role == "assistant":
            text = f"{speaker_name(chat, row)}: {text}"
        rows.append({"role": role, "content": text})
    return rows


def location_phrase(text: str) -> str:
    match = re.search(
        r"\b(?:arrives? at|arrive[sd]? at|enters?|enter[sd]?|walks? into|steps? into|scene is|location is|now in|now at)\s+([^.\n]{3,80})",
        text,
        re.I,
    )
    return match.group(1).strip(" *\"'") if match else ""


def load_presets() -> list[dict]:
    data = _read_json(store_root() / "presets.json", {"presets": []})
    rows = data.get("presets") if isinstance(data, dict) else []
    return [row for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)]


def save_presets(rows: list[dict]) -> None:
    _write_json(store_root() / "presets.json", {"presets": rows})


def find_preset(preset_id: str) -> dict | None:
    for row in load_presets():
        if row.get("id") == preset_id:
            return row
    return None


def _as_list(value) -> list:
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip().startswith(("[", "{")):
        try:
            return _as_list(json.loads(value))
        except json.JSONDecodeError:
            return []
    return []


def _flat_value(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(part) for part in value if str(part).strip())
    if isinstance(value, bool):
        return "on" if value else ""
    if value is None:
        return ""
    return str(value)


def _value_map(raw) -> dict[str, str]:
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                return {}
        else:
            return {}
    found: dict[str, str] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            found[str(key)] = _flat_value(value)
        return found
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("variableName") or item.get("key") or "")
                if name and ("value" in item or "values" in item):
                    found[name] = _flat_value(item.get("value", item.get("values")))
                else:
                    for key, value in item.items():
                        if key not in ("id", "presetId", "createdAt"):
                            found[str(key)] = _flat_value(value)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                found[str(item[0])] = _flat_value(item[1])
    return found


def _flag(value, default: bool = True) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "0", "no", "off", "")
    if value is None:
        return default
    return bool(value)


def _variables_from(body: dict, payload: dict) -> list[dict]:
    raw = body.get("variableGroups") or payload.get("variableGroups") or body.get("choiceBlocks") or payload.get("choiceBlocks") or []
    rows = []
    for item in _as_list(raw):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("variableName") or "").strip()
        if not name:
            continue
        options = item.get("options") or []
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except json.JSONDecodeError:
                options = []
        copied = dict(item)
        copied["name"] = name
        copied["label"] = str(item.get("label") or item.get("question") or name)
        copied["options"] = options if isinstance(options, list) else []
        rows.append(copied)
    return rows


def _section_from_raw(raw: dict) -> dict:
    identifier = str(raw.get("identifier") or raw.get("name") or "")
    return {
        "id": str(raw.get("id") or uuid.uuid4().hex),
        "name": str(raw.get("name") or identifier or "Section")[:120],
        "identifier": identifier,
        "content": str(raw.get("content") or ""),
        "role": str(raw.get("role") or "system"),
        "enabled": _flag(raw.get("enabled", True)),
        "is_marker": bool(raw.get("isMarker") or raw.get("marker") or raw.get("is_marker")),
        "group_id": str(raw.get("groupId") or raw.get("group_id") or "") or None,
        "injection": "depth" if str(raw.get("injectionPosition") or "") == "depth" else "ordered",
        "source": raw,
    }


def preset_from_payload(payload) -> dict | None:
    if isinstance(payload, list):
        found = [item for item in (preset_from_payload(row) for row in payload) if item]
        return found[0] if found else None
    if not isinstance(payload, dict):
        return None
    if payload.get("type") == "marinara_preset" and isinstance(payload.get("data"), dict):
        data = payload["data"]
        body = data.get("preset") if isinstance(data.get("preset"), dict) else data
        if isinstance(body, dict) and body is not data:
            body = dict(body)
            for key in ("variableGroups", "choiceBlocks", "variableValues", "defaultChoices", "parameters", "sectionOrder"):
                if key not in body and key in data:
                    body[key] = data[key]
        sections = _as_list(data.get("sections") or body.get("sections") or [])
        groups = _as_list(data.get("groups") or body.get("groups") or [])
    elif isinstance(payload.get("prompts"), list):
        body = payload
        sections = payload.get("prompts") or []
        enabled = {}
        for row in payload.get("prompt_order") or []:
            rows = row.get("order") if isinstance(row, dict) and isinstance(row.get("order"), list) else [row]
            for item in rows:
                if isinstance(item, dict):
                    enabled[str(item.get("identifier") or "")] = bool(item.get("enabled", True))
        sections = []
        for raw in payload.get("prompts") or []:
            if not isinstance(raw, dict):
                continue
            copied = dict(raw)
            ident = str(copied.get("identifier") or "")
            if ident in enabled:
                copied["enabled"] = enabled[ident]
            sections.append(copied)
        groups = _as_list(payload.get("groups") or [])
    else:
        body = payload.get("preset") if isinstance(payload.get("preset"), dict) else payload
        sections = _as_list(payload.get("sections") or body.get("sections") or [])
        groups = _as_list(payload.get("groups") or body.get("groups") or [])
    if not isinstance(body, dict):
        return None
    name = str(body.get("name") or payload.get("name") or "").strip()
    if not name and not sections:
        return None
    order = _as_list(body.get("sectionOrder") or payload.get("sectionOrder") or [])
    if order:
        by_id = {str(row.get("id")): row for row in sections if isinstance(row, dict)}
        ordered = [by_id[str(item)] for item in order if str(item) in by_id]
        seen = {str(item) for item in order}
        sections = ordered + [row for row in sections if isinstance(row, dict) and str(row.get("id")) not in seen]
    values = _value_map(body.get("variableValues") if body.get("variableValues") is not None else payload.get("variableValues"))
    defaults = _value_map(body.get("defaultChoices") or payload.get("defaultChoices"))
    for key, value in defaults.items():
        values.setdefault(key, value)
    params = body.get("parameters") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            params = {}
    if not isinstance(params, dict):
        params = {}
    return {
        "id": uuid.uuid4().hex,
        "name": name or "Imported preset",
        "description": str(body.get("description") or ""),
        "wrap": str(body.get("wrapFormat") or body.get("wrap") or "xml"),
        "sections": [_section_from_raw(row) for row in sections if isinstance(row, dict)],
        "groups": [
            {
                "id": str(row.get("id") or uuid.uuid4().hex),
                "name": str(row.get("name") or "Group"),
                "enabled": _flag(row.get("enabled", True)),
                "parent_id": str(row.get("parentGroupId") or "") or None,
                "source": row,
            }
            for row in groups
            if isinstance(row, dict)
        ],
        "variables": _variables_from(body, payload),
        "values": values,
        "parameters": params,
        "source": payload,
    }


def _group_enabled(preset: dict, group_id: str | None, seen: set[str] | None = None) -> bool:
    if not group_id:
        return True
    seen = seen or set()
    if group_id in seen:
        return True
    seen.add(group_id)
    for group in preset.get("groups") or []:
        if group.get("id") == group_id:
            if group.get("enabled") is False:
                return False
            return _group_enabled(preset, group.get("parent_id"), seen)
    return True


def _marker_kind(section: dict) -> str:
    ident = re.sub(r"[^a-z]", "", str(section.get("identifier") or section.get("name") or "").lower())
    table = {
        "chardescription": "character",
        "characterinfo": "character",
        "characterdescription": "character",
        "charpersonality": "personality",
        "persona": "persona",
        "personadescription": "persona",
        "chathistory": "history",
        "dialogueexamples": "examples",
        "mesexamples": "examples",
        "worldinfo": "lore",
        "worldinfobefore": "lore",
        "worldinfoafter": "lore",
        "lorebook": "lore",
        "lore": "lore",
        "chatsummary": "memory",
        "memory": "memory",
        "scenario": "scenario",
    }
    if ident in table:
        return table[ident]
    return ident if section.get("is_marker") else ""


def _apply_macros(text: str, user_name: str, char_name: str, values: dict) -> str:
    text = expand_names(text, user_name, char_name)
    for key, value in values.items():
        text = text.replace("{{" + str(key) + "}}", str(value))
        text = text.replace("{{getvar::" + str(key) + "}}", str(value))
    return text


def _wrap_block(name: str, body: str, fmt: str) -> str:
    if fmt == "none":
        return body
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "section"
    if fmt == "markdown":
        return f"## {name}\n{body}"
    return f"<{slug}>\n{body}\n</{slug}>"


def preset_values(preset: dict) -> dict[str, str]:
    values = {str(key): str(value) for key, value in (preset.get("values") or {}).items()}
    for variable in preset.get("variables") or []:
        name = str(variable.get("name") or "")
        if not name or name in values:
            continue
        options = variable.get("options") if isinstance(variable.get("options"), list) else []
        if len(options) == 1 and isinstance(options[0], dict):
            values[name] = ""
        elif options and isinstance(options[0], dict):
            values[name] = str(options[0].get("value") or "")
    return values


def assemble_preset(chat: dict, scene: str, speaker_id: str, direction: str, history: list[dict]) -> list[dict] | None:
    preset = find_preset(str(chat.get("preset_id") or ""))
    if not preset or not preset.get("sections"):
        return None
    speaker = find_card(speaker_id)
    persona = find_card(chat.get("persona_id") or "")
    char_name = card_name(speaker, "Character")
    user_name = card_name(persona, "You")
    card = (speaker or {}).get("card") or {}
    person = (persona or {}).get("card") or {}
    values = preset_values(preset)
    lore = "\n\n".join(routed_lore(chat, scene))
    memories = recall_memory(load_memory() + list(chat.get("memory") or []), scene)
    pinned = str(card.get("long_memory") or "").strip()
    if pinned:
        memories.insert(0, pinned)
    memory_text = "\n".join(f"- {item}" for item in memories[:8])
    character_text = "\n\n".join(
        f"{label}:\n{card.get(key)}"
        for label, key in (
            ("Description", "description"),
            ("Personality", "personality"),
            ("Scenario", "scenario"),
            ("Appearance", "appearance"),
            ("Backstory", "backstory"),
        )
        if str(card.get(key) or "").strip()
    )
    markers = {
        "character": character_text,
        "personality": str(card.get("personality") or ""),
        "persona": "\n".join(part for part in (str(person.get("description") or ""), str(person.get("personality") or "")) if part.strip()),
        "examples": str(card.get("mes_example") or ""),
        "scenario": str(card.get("scenario") or ""),
        "lore": lore,
        "memory": memory_text,
    }
    system_parts: list[str] = []
    before: list[dict] = []
    after: list[dict] = []
    seen_history = False
    for section in preset.get("sections") or []:
        if section.get("enabled") is False or not _group_enabled(preset, section.get("group_id")):
            continue
        kind = _marker_kind(section)
        if kind == "history":
            seen_history = True
            continue
        body = markers.get(kind, "") if kind else str(section.get("content") or "")
        body = _apply_macros(body, user_name, char_name, values).strip()
        if not body:
            continue
        wrapped = _wrap_block(str(section.get("name") or "Section"), body, str(preset.get("wrap") or "xml"))
        role = "assistant" if section.get("role") == "assistant" else "user" if section.get("role") == "user" else "system"
        if seen_history or section.get("injection") == "depth":
            after.append({"role": role, "content": wrapped})
        elif role == "system":
            system_parts.append(wrapped)
        else:
            before.append({"role": role, "content": wrapped})
    if direction.strip():
        system_parts.append("Follow this for this reply:\n" + direction.strip())
    if not system_parts and not before and not after:
        return None
    messages = [{"role": "system", "content": "\n\n".join(system_parts) or f"You are {char_name}."}]
    messages.extend(before)
    messages.extend(history)
    messages.extend(after)
    return messages


def attach(app, page) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    BG, SURFACE, INSET, FG, MUTED = "#16080a", "#2a1214", "#140709", "#f6eee8", "#b39b94"
    PRIMARY = "#e39b88"
    page.columnconfigure(1, weight=1)
    page.rowconfigure(0, weight=1)
    state = {"chat": blank_chat(), "busy": False, "editing": "", "books": load_lorebooks(), "book_id": "", "entry_id": ""}

    left = ttk.Frame(page, style="TFrame")
    left.grid(row=0, column=0, sticky="nsew")
    left_box = app._make_scroller(left, bg=SURFACE, width=280, style="Card.TFrame")
    center = ttk.Frame(page, style="TFrame")
    center.grid(row=0, column=1, sticky="nsew", padx=8)
    center.rowconfigure(1, weight=1)
    center.columnconfigure(0, weight=1)
    right = ttk.Frame(page, style="TFrame")
    right.grid(row=0, column=2, sticky="nsew")
    right.rowconfigure(0, weight=1)
    right.columnconfigure(0, weight=1)

    ttk.Label(left_box, text="Chats", style="Card.TLabel").pack(anchor="w")
    chat_list = tk.Listbox(left_box, height=8, bg=INSET, fg=FG, selectbackground=PRIMARY, relief="flat", highlightthickness=0, activestyle="none")
    chat_list.pack(fill="x", pady=4)
    chat_buttons = ttk.Frame(left_box, style="Card.TFrame")
    chat_buttons.pack(fill="x", pady=(0, 8))

    ttk.Label(left_box, text="Characters", style="Card.TLabel").pack(anchor="w")
    cast_list = tk.Listbox(left_box, height=5, bg=INSET, fg=FG, selectbackground=PRIMARY, relief="flat", highlightthickness=0, activestyle="none")
    cast_list.pack(fill="x", pady=4)
    add_row = ttk.Frame(left_box, style="Card.TFrame")
    add_row.pack(fill="x", pady=(0, 4))
    character_var = tk.StringVar()
    character_box = ttk.Combobox(add_row, textvariable=character_var, state="readonly")
    character_box.pack(side="left", fill="x", expand=True)
    ttk.Button(add_row, text="Add", command=lambda: add_character()).pack(side="left", padx=(6, 0))
    ttk.Button(left_box, text="Remove character", command=lambda: remove_character()).pack(anchor="w", pady=(0, 6))
    ttk.Label(left_box, text="Who answers", style="Card.TLabel").pack(anchor="w")
    speaker_var = tk.StringVar()
    speaker_box = ttk.Combobox(left_box, textvariable=speaker_var, state="readonly")
    speaker_box.pack(fill="x", pady=4)
    ttk.Label(left_box, text="Persona", style="Card.TLabel").pack(anchor="w")
    persona_var = tk.StringVar()
    persona_box = ttk.Combobox(left_box, textvariable=persona_var, state="readonly")
    persona_box.pack(fill="x", pady=4)
    ttk.Label(left_box, text="Lorebooks", style="Card.TLabel").pack(anchor="w")
    lore_list = tk.Listbox(left_box, height=4, bg=INSET, fg=FG, selectbackground=PRIMARY, relief="flat", highlightthickness=0, activestyle="none")
    lore_list.pack(fill="x", pady=4)
    lore_add = ttk.Frame(left_box, style="Card.TFrame")
    lore_add.pack(fill="x", pady=(0, 4))
    lore_var = tk.StringVar()
    lore_box = ttk.Combobox(lore_add, textvariable=lore_var, state="readonly")
    lore_box.pack(side="left", fill="x", expand=True)
    ttk.Button(lore_add, text="Add", command=lambda: add_lore()).pack(side="left", padx=(6, 0))
    ttk.Button(left_box, text="Remove lorebook", command=lambda: remove_lore()).pack(anchor="w", pady=(0, 6))
    ttk.Label(left_box, text="Preset", style="Card.TLabel").pack(anchor="w")
    preset_var = tk.StringVar()
    preset_box = ttk.Combobox(left_box, textvariable=preset_var, state="readonly")
    preset_box.pack(fill="x", pady=4)
    ttk.Label(left_box, text="Text size", style="Card.TLabel").pack(anchor="w", pady=(6, 0))
    text_size = tk.IntVar(value=14)
    size_row = ttk.Frame(left_box, style="Card.TFrame")
    size_row.pack(fill="x", pady=(0, 6))
    size_scale = tk.Scale(size_row, from_=11, to=24, orient="horizontal", variable=text_size, bg=SURFACE, fg=FG, highlightthickness=0, troughcolor=INSET, showvalue=False)
    size_scale.pack(side="left", fill="x", expand=True)
    size_label = tk.Label(size_row, text="14", bg=SURFACE, fg=MUTED)
    size_label.pack(side="left", padx=(6, 0))
    ttk.Button(left_box, text="Refresh cast", command=lambda: refresh_cast()).pack(anchor="w", pady=(0, 8))
    auto_bg = tk.BooleanVar(value=False)
    tk.Checkbutton(left_box, text="Auto scene background", variable=auto_bg, bg=SURFACE, fg=FG, selectcolor=BG, activebackground=SURFACE, activeforeground=FG).pack(anchor="w")
    ttk.Label(left_box, text="Illustrator", style="Muted.TLabel").pack(anchor="w", pady=(8, 0))
    engine_var = tk.StringVar(value="NovelAI")
    ttk.Combobox(left_box, textvariable=engine_var, state="readonly", values=("NovelAI", "RedGen", "Anima")).pack(fill="x", pady=4)
    ttk.Label(
        left_box,
        text="Export writes a browser visual novel. It plays outside RedWright.",
        style="Muted.TLabel",
        wraplength=250,
    ).pack(anchor="w", pady=(8, 0))

    status = tk.Label(center, text="New chat", bg=BG, fg=MUTED, anchor="w")
    status.grid(row=0, column=0, sticky="ew")
    log = tk.Text(center, bg=BG, fg=FG, insertbackground=FG, relief="flat", wrap="word", padx=10, pady=8, cursor="arrow", state="disabled", borderwidth=0, highlightthickness=0)
    log._spell_skip = True
    log.grid(row=1, column=0, sticky="nsew")
    log.tag_configure("picked", foreground=PRIMARY)
    photos: list = []
    edit_frame = ttk.Frame(center, style="Card.TFrame")
    edit_box = tk.Text(edit_frame, height=5, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word")
    edit_box.pack(fill="x", padx=8, pady=(8, 4))
    actions = ttk.Frame(center, style="Card.TFrame")
    actions.grid(row=3, column=0, sticky="ew", pady=(6, 0))

    composer = ttk.Frame(center, style="Card.TFrame")
    composer.grid(row=4, column=0, sticky="ew", pady=(8, 0))
    ttk.Label(composer, text="Follow this when answering", style="Muted.TLabel").pack(anchor="w", padx=8, pady=(8, 0))
    direction_row = ttk.Frame(composer, style="Card.TFrame")
    direction_row.pack(fill="x", padx=8, pady=(2, 0))
    direction = tk.Text(direction_row, height=2, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word")
    direction.pack(side="left", fill="both", expand=True)
    draft = tk.Text(composer, height=4, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word")
    draft.pack(fill="x", padx=8, pady=8)
    send_row = ttk.Frame(composer, style="Card.TFrame")
    send_row.pack(fill="x", padx=8, pady=(0, 4))
    image_row = ttk.Frame(composer, style="Card.TFrame")
    image_row.pack(fill="x", padx=8, pady=(0, 4))
    ttk.Label(image_row, text="Last", style="Muted.TLabel").pack(side="left")
    image_count = tk.IntVar(value=4)
    tk.Spinbox(image_row, from_=1, to=40, textvariable=image_count, width=4, bg=INSET, fg=FG, buttonbackground=SURFACE).pack(side="left", padx=6)
    ttk.Label(image_row, text="messages", style="Muted.TLabel").pack(side="left")
    image_prompt = tk.Text(composer, height=3, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word")
    image_prompt.pack(fill="x", padx=8, pady=(0, 8))

    tools = ttk.Notebook(right)
    tools.grid(row=0, column=0, sticky="nsew")
    memory_page = ttk.Frame(tools, style="TFrame")
    tools.add(memory_page, text="Memory")
    memory_form = app._make_scroller(memory_page, bg=SURFACE, width=320, style="Card.TFrame")

    def say(text: str) -> None:
        status.configure(text=text[:180])

    def current() -> dict:
        return state["chat"]

    def persist() -> None:
        chat = current()
        character = find_card(chat.get("character_id") or "")
        title = card_name(character, "")
        first = ""
        for row in chat.get("messages") or []:
            text = shown_text(row).strip()
            if text:
                first = text.replace("\n", " ")[:48]
                break
        chat["title"] = title or first or "New chat"
        if first and title:
            chat["title"] = f"{title} — {first}"
        chat["auto_background"] = bool(auto_bg.get())
        chat["image_engine"] = engine_var.get() or "NovelAI"
        save_chat(chat)
        refresh_chats(select=True)

    def refresh_chats(select: bool = False) -> None:
        rows = list_chats()
        state["rows"] = rows
        chat_list.delete(0, "end")
        picked = None
        for index, row in enumerate(rows):
            chat_list.insert("end", str(row.get("title") or "Chat"))
            if row.get("id") == current().get("id"):
                picked = index
        if select and picked is not None:
            chat_list.selection_clear(0, "end")
            chat_list.selection_set(picked)
            chat_list.see(picked)

    def refresh_cast() -> None:
        characters, personas = cards_by_kind()
        state["characters"] = characters
        state["personas"] = personas
        character_box["values"] = [card_name(row, "Unnamed") for row in characters]
        persona_box["values"] = ["None"] + [card_name(row, "Unnamed") for row in personas]
        books = load_lorebooks()
        state["books"] = books
        lore_box["values"] = [str(book.get("name") or "Lorebook") for book in books]
        presets = load_presets()
        state["presets"] = presets
        preset_box["values"] = ["None"] + [str(row.get("name") or "Preset") for row in presets]
        apply_cast_labels()

    def apply_cast_labels() -> None:
        chat = current()
        ids = character_ids(chat)
        cast_list.delete(0, "end")
        names = []
        for card_id in ids:
            entry = find_card(card_id)
            label = card_name(entry, "Unnamed")
            names.append(label)
            cast_list.insert("end", label)
        speaker_box["values"] = names or ["None"]
        speaker = find_card(chat.get("speaker_id") or "")
        speaker_var.set(card_name(speaker, names[0] if names else "None"))
        if speaker is None and ids:
            chat["speaker_id"] = ids[0]
        persona_var.set("None")
        for row in state.get("personas") or []:
            if row.get("id") == chat.get("persona_id"):
                persona_var.set(card_name(row, "Unnamed"))
        lore_list.delete(0, "end")
        for book_id in lorebook_ids(chat):
            book = next((row for row in state.get("books") or [] if row.get("id") == book_id), None)
            lore_list.insert("end", str((book or {}).get("name") or "Missing lorebook"))
        preset_var.set("None")
        for row in state.get("presets") or []:
            if row.get("id") == chat.get("preset_id"):
                preset_var.set(str(row.get("name") or "Preset"))
        auto_bg.set(bool(chat.get("auto_background")))
        engine_var.set(str(chat.get("image_engine") or "NovelAI"))

    def add_character() -> None:
        name = character_var.get()
        chat = current()
        ids = character_ids(chat)
        for row in state.get("characters") or []:
            if card_name(row, "Unnamed") != name or row["id"] in ids:
                continue
            ids.append(row["id"])
            chat["character_ids"] = ids
            chat["character_id"] = ids[0]
            if not chat.get("speaker_id"):
                chat["speaker_id"] = row["id"]
            if not chat["messages"]:
                greeting = str((row.get("card") or {}).get("first_mes") or "").strip()
                if greeting:
                    chat["messages"].append(message("assistant", greeting, row["id"]))
            break
        persist()
        apply_cast_labels()
        paint()

    def remove_character() -> None:
        picked = cast_list.curselection()
        ids = character_ids(current())
        if not picked or picked[0] >= len(ids):
            return
        removed = ids.pop(picked[0])
        current()["character_ids"] = ids
        current()["character_id"] = ids[0] if ids else ""
        if current().get("speaker_id") == removed:
            current()["speaker_id"] = ids[0] if ids else ""
        persist()
        apply_cast_labels()
        paint()

    def choose_speaker(_event=None) -> None:
        name = speaker_var.get()
        current()["speaker_id"] = ""
        for card_id in character_ids(current()):
            if card_name(find_card(card_id), "Unnamed") == name:
                current()["speaker_id"] = card_id
        persist()

    def choose_persona(_event=None) -> None:
        name = persona_var.get()
        current()["persona_id"] = ""
        for row in state.get("personas") or []:
            if card_name(row, "Unnamed") == name:
                current()["persona_id"] = row["id"]
        persist()

    def choose_preset(_event=None) -> None:
        name = preset_var.get()
        current()["preset_id"] = ""
        for row in state.get("presets") or []:
            if str(row.get("name") or "Preset") == name:
                current()["preset_id"] = row["id"]
        persist()

    def add_lore() -> None:
        name = lore_var.get()
        ids = lorebook_ids(current())
        for book in state.get("books") or []:
            if str(book.get("name") or "Lorebook") == name and book["id"] not in ids:
                ids.append(book["id"])
                current()["lorebook_ids"] = ids
                current()["lorebook_id"] = ids[0]
                break
        persist()
        apply_cast_labels()

    def remove_lore() -> None:
        picked = lore_list.curselection()
        ids = lorebook_ids(current())
        if not picked or picked[0] >= len(ids):
            return
        ids.pop(picked[0])
        current()["lorebook_ids"] = ids
        current()["lorebook_id"] = ids[0] if ids else ""
        persist()
        apply_cast_labels()

    def open_chat(_event=None) -> None:
        picked = chat_list.curselection()
        if not picked:
            return
        row = state.get("rows", [])[picked[0]]
        loaded = load_chat(row["id"])
        if loaded:
            state["chat"] = loaded
            character_ids(loaded)
            apply_cast_labels()
            direction.delete("1.0", "end")
            direction.insert("1.0", str(loaded.get("direction") or ""))
            paint()

    def new_chat() -> None:
        state["chat"] = blank_chat()
        direction.delete("1.0", "end")
        apply_cast_labels()
        persist()
        paint()
        say("New chat.")

    def remove_chat() -> None:
        chat_id = current().get("id")
        if not chat_id:
            return
        delete_chat(chat_id)
        state["chat"] = blank_chat()
        apply_cast_labels()
        refresh_chats()
        paint()

    def chat_font(bold: bool = False) -> tuple:
        return ("Segoe UI", max(11, min(24, int(text_size.get()))), "bold") if bold else ("Segoe UI", max(11, min(24, int(text_size.get()))))

    def apply_text_size(_value=None) -> None:
        size = max(11, min(24, int(float(text_size.get() or 14))))
        size_label.configure(text=str(size))
        font = chat_font()
        bold = chat_font(True)
        draft.configure(font=font)
        direction.configure(font=font)
        image_prompt.configure(font=font)
        edit_box.configure(font=font)
        log.configure(font=font)
        for name in log.tag_names():
            if name.startswith("name-") or name == "picked":
                log.tag_configure(name, font=bold)
            elif name.startswith("body-"):
                log.tag_configure(name, font=font)
        pending = state.get("size_job")
        if pending:
            app.after_cancel(pending)

        def save_size(kept=size) -> None:
            state["size_job"] = None
            _write_json(store_root() / "ui.json", {"text_size": kept})

        state["size_job"] = app.after(400, save_size)

    def selected_row() -> dict | None:
        picked = state.get("selected") or ""
        rows = current().get("messages") or []
        for row in rows:
            if row.get("id") == picked:
                return row
        return rows[-1] if rows else None

    def mark_selected() -> None:
        try:
            log.tag_remove("picked", "1.0", "end")
        except tk.TclError:
            return
        span = (state.get("marks") or {}).get(state.get("selected") or "")
        if not span:
            return
        log.tag_add("picked", span[0], f"{span[0]} lineend")
        log.tag_raise("picked")

    def pick_message(row_id: str) -> None:
        state["selected"] = row_id
        mark_selected()

    def paint() -> None:
        chat = current()
        character_ids(chat)
        persona = find_card(chat.get("persona_id") or "")
        user_name = card_name(persona, "You")
        font = chat_font()
        bold = chat_font(True)

        def ink_color(value: str, fallback: str) -> str:
            match = re.search(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", str(value or ""))
            if not match:
                return fallback
            hexed = match.group(0)
            if len(hexed) == 4:
                return "#" + "".join(character * 2 for character in hexed[1:])
            return hexed

        photos.clear()
        state["marks"] = {}
        state["image_at"] = {}
        log.configure(state="normal", font=font)
        log.delete("1.0", "end")
        for name in list(log.tag_names()):
            if name != "picked":
                log.tag_delete(name)
        log.tag_configure("picked", foreground=PRIMARY, font=bold)
        for row in chat.get("messages") or []:
            owner = persona if row.get("role") == "user" else find_card(str(row.get("speaker_id") or chat.get("speaker_id") or chat.get("character_id") or ""))
            colors = (owner or {}).get("card") or {}
            box = ink_color(colors.get("box_color"), "")
            name_ink = ink_color(colors.get("name_color"), MUTED)
            say_ink = ink_color(colors.get("dialogue_color"), "")
            who = user_name if row.get("role") == "user" else speaker_name(chat, row)
            char_name = who if row.get("role") != "user" else card_name(find_card(chat.get("speaker_id") or chat.get("character_id") or ""), "Character")
            spoken, embedded = embedded_pictures(expand_names(shown_text(row), user_name, char_name))
            if not spoken and not embedded:
                spoken = "…"
            swipes = row.get("swipes") or [""]
            row_id = str(row.get("id") or "")
            name_tag = f"name-{row_id}"
            body_tag = f"body-{row_id}"
            msg_tag = f"msg-{row_id}"
            start = log.index("end-1c")
            log.tag_configure(name_tag, foreground=name_ink, font=bold, spacing1=8)
            log.insert("end", f"{who}    {int(row.get('swipe') or 0) + 1}/{len(swipes)}\n", name_tag)
            body_style = {"foreground": FG, "font": font, "spacing3": 6, "lmargin1": 8, "lmargin2": 8, "rmargin": 8}
            if box:
                body_style["background"] = box
            log.tag_configure(body_tag, **body_style)
            say_tag = ""
            if say_ink:
                say_tag = f"say-{row_id}"
                log.tag_configure(say_tag, foreground=say_ink, font=font, background=box or BG)
            if spoken:
                cursor = 0
                for match in re.finditer(r'(["“«])([^"”»]+)(["”»])', spoken):
                    if match.start() > cursor:
                        log.insert("end", spoken[cursor:match.start()], body_tag)
                    log.insert("end", match.group(0), (body_tag, say_tag) if say_tag else body_tag)
                    cursor = match.end()
                log.insert("end", spoken[cursor:] + "\n", body_tag)
            else:
                log.insert("end", "\n", body_tag)

            def place_picture(path: str) -> None:
                try:
                    from PIL import Image, ImageTk

                    image = Image.open(path).convert("RGB")
                    image.thumbnail((220, 220))
                    photo = ImageTk.PhotoImage(image)
                except OSError:
                    return
                photos.append(photo)
                mark = log.index("end-1c")
                log.image_create(mark, image=photo, padx=8)
                state["image_at"][str(mark)] = path
                log.insert("end", "\n", body_tag)

            seen = set()
            for path in embedded:
                if path not in seen:
                    seen.add(path)
                    place_picture(path)
            image_path = str(row.get("image") or "")
            if image_path and image_path not in seen and Path(image_path).is_file():
                place_picture(image_path)
            end = log.index("end-1c")
            state["marks"][row_id] = (start, end)
            log.tag_add(msg_tag, start, end)
        if not state.get("selected") and chat.get("messages"):
            state["selected"] = str(chat["messages"][-1].get("id") or "")
        mark_selected()
        log.see("end")
        log.configure(insertwidth=0)

    def open_picture(path: str) -> None:
        from PIL import Image

        try:
            image = Image.open(path).convert("RGB")
        except OSError:
            return
        app._open_full_view(image, Path(path).name, shown_text(current()["messages"][-1]) if current()["messages"] else "")

    def edit_message(row: dict | None = None) -> None:
        row = row or selected_row()
        if not row:
            say("Click a message first.")
            return
        state["editing"] = row["id"]
        state["selected"] = row["id"]
        edit_box.delete("1.0", "end")
        edit_box.insert("1.0", shown_text(row))
        edit_frame.grid(row=2, column=0, sticky="ew")
        mark_selected()

    def save_edit() -> None:
        row_id = state.get("editing")
        for item in current().get("messages") or []:
            if item.get("id") != row_id:
                continue
            item.setdefault("swipes", [""])
            item["swipes"][int(item.get("swipe") or 0)] = edit_box.get("1.0", "end").strip()
            break
        state["editing"] = ""
        edit_frame.grid_remove()
        persist()
        paint()

    def cycle_swipe(row: dict | None = None) -> None:
        row = row or selected_row()
        if not row:
            return
        swipes = row.get("swipes") or [""]
        row["swipe"] = (int(row.get("swipe") or 0) + 1) % max(1, len(swipes))
        persist()
        paint()

    def remove_message(row: dict | None = None) -> None:
        row = row or selected_row()
        if not row:
            return
        current()["messages"] = [item for item in current()["messages"] if item.get("id") != row.get("id")]
        if state.get("selected") == row.get("id"):
            state["selected"] = ""
        state["editing"] = ""
        edit_frame.grid_remove()
        persist()
        paint()

    def kobold_messages(chat: dict, stop_id: str = "", direction_text: str = "") -> list[dict]:
        scene = "\n".join(item["content"] for item in transcript(chat, stop_id)[-8:])
        speaker = chat.get("speaker_id") or (character_ids(chat)[:1] or [""])[0]
        history = transcript(chat, stop_id)
        preset_messages = assemble_preset(chat, scene, speaker, direction_text, history)
        if preset_messages:
            return preset_messages
        return [{"role": "system", "content": system_prompt(chat, scene, speaker, direction_text)}, *history]

    def kobold_settings() -> tuple[str, str, str]:
        stored = cardwright.load_settings()
        url = app.kobold_url.get().strip() if hasattr(app, "kobold_url") else str(stored.get("kobold") or "")
        key = app.kobold_key.get().strip() if hasattr(app, "kobold_key") else str(stored.get("key") or "")
        model = str(stored.get("model") or "koboldcpp")
        return url, key, model

    def remember_from(exchange: str) -> None:
        url, key, model = kobold_settings()
        if not url:
            return
        try:
            reply = cardwright.kobold_chat(
                url,
                key,
                [
                    {"role": "system", "content": "Pull out lasting facts. Reply with one short fact per line, or NONE."},
                    {"role": "user", "content": exchange[-4000:]},
                ],
                model=model,
                temperature=0.2,
                max_tokens=180,
            )
        except Exception:
            return
        facts = load_memory()
        chat_facts = list(current().get("memory") or [])
        for line in reply.splitlines():
            text = line.strip(" -\t")
            if not text or text.upper() == "NONE" or len(text) < 8:
                continue
            fact = {"id": uuid.uuid4().hex, "text": text[:240], "chat": current().get("id"), "at": datetime.now().isoformat(timespec="seconds")}
            facts.insert(0, fact)
            chat_facts.insert(0, fact)
        save_memory(facts[:400])
        current()["memory"] = chat_facts[:80]
        save_chat(current())
        app.after(0, paint_memory)

    def generate_into(row: dict | None, prelude: list[dict]) -> None:
        if state["busy"]:
            say("Wait for the reply that is already running.")
            return
        url, key, model = kobold_settings()
        if not url:
            say("Set the Kobold address on the Captions tab.")
            return
        state["busy"] = True
        say("Kobold is writing…")
        heat = 0.85
        preset = find_preset(str(current().get("preset_id") or ""))
        params = (preset or {}).get("parameters") or {}
        if isinstance(params.get("temperature"), (int, float)):
            heat = float(params["temperature"])

        def work() -> None:
            try:
                reply = cardwright.kobold_chat(url, key, prelude, model=model, temperature=heat, max_tokens=700)
            except Exception as exc:
                app.after(0, lambda detail=exc: finish_error(str(detail)))
                return
            app.after(0, lambda text=reply.strip(): finish_reply(row, text))

        threading.Thread(target=work, daemon=True).start()

    def finish_error(detail: str) -> None:
        state["busy"] = False
        say(detail)

    def finish_reply(row: dict | None, text: str) -> None:
        state["busy"] = False
        if not text:
            say("Kobold returned an empty reply.")
            return
        if row is None:
            made = message("assistant", text, str(current().get("speaker_id") or ""))
            made["direction"] = str(current().get("direction") or "")
            current()["messages"].append(made)
            target = made
        else:
            row.setdefault("swipes", [shown_text(row)])
            row["swipes"].append(text)
            row["swipe"] = len(row["swipes"]) - 1
            target = row
        place = location_phrase(text)
        if place:
            target["location"] = place
        persist()
        paint()
        say("Reply saved.")
        previous = ""
        if len(current()["messages"]) >= 2:
            previous = shown_text(current()["messages"][-2])
        threading.Thread(target=lambda: remember_from(previous + "\n" + text), daemon=True).start()
        if auto_bg.get() and place:
            illustrate(target, True)

    def send() -> None:
        text = draft.get("1.0", "end").strip()
        if not text:
            say("Write a message first.")
            return
        if not character_ids(current()):
            say("Add a character first.")
            return
        note = direction.get("1.0", "end").strip()
        current()["direction"] = note
        draft.delete("1.0", "end")
        current()["messages"].append(message("user", text, str(current().get("persona_id") or "")))
        persist()
        paint()
        generate_into(None, kobold_messages(current(), direction_text=note))

    def answer_direction() -> None:
        if not character_ids(current()):
            say("Add a character first.")
            return
        note = direction.get("1.0", "end").strip()
        if not note:
            say("Write what the character should do.")
            return
        current()["direction"] = note
        persist()
        prelude = kobold_messages(current(), direction_text=note)
        prelude.append({"role": "user", "content": "Write your next reply now. Follow the instruction. Do not mention these directions."})
        generate_into(None, prelude)

    def say_as() -> None:
        text = draft.get("1.0", "end").strip()
        speaker = str(current().get("speaker_id") or "")
        if not text or not speaker:
            say("Pick who answers, then write the line.")
            return
        draft.delete("1.0", "end")
        current()["messages"].append(message("assistant", text, speaker))
        persist()
        paint()
        say(f"{card_name(find_card(speaker), 'Character')} said that line.")

    def regenerate(row: dict | None = None) -> None:
        row = row or selected_row()
        if not row:
            say("Click a message first.")
            return
        note = str(row.get("direction") or direction.get("1.0", "end").strip())
        if row.get("speaker_id"):
            current()["speaker_id"] = row["speaker_id"]
        prelude = kobold_messages(current(), row["id"], note)
        prelude.append({"role": "user", "content": "Stay in the same voice and write another version of your last line."})
        generate_into(row, prelude)

    def illustrate(row: dict, background: bool, prompt_text: str = "") -> None:
        looks = appearances(current())
        text = shown_text(row)
        if prompt_text.strip():
            prompt = prompt_text.strip()
        elif background:
            prompt = f"background scenery, no people, no characters, {row.get('location') or text}"
        else:
            prompt = ", ".join(part for part in (looks.replace("\n", ", "), text.replace("\n", ", ")) if part)[:1500]
        engine = engine_var.get() or "NovelAI"
        say(f"{engine} is drawing…")

        def accept(path: str, item=row) -> None:
            item["image"] = path
            persist()
            paint()
            say(f"Picture saved. {Path(path).name}")

        if engine == "NovelAI":
            token = str(cardwright.load_settings().get("novel_token") or "")

            def work() -> None:
                try:
                    image = cardwright.novel_generate(token, prompt)
                    dest = store_root() / "pictures" / f"{uuid.uuid4().hex}.png"
                    image.save(dest)
                except Exception as exc:
                    app.after(0, lambda detail=exc: say(str(detail)))
                    return
                app.after(0, lambda: accept(str(dest)))

            threading.Thread(target=work, daemon=True).start()
            return
        folder = str(store_root() / "pictures")
        override = {"prompt": prompt, "count": 1, "folder": folder, "skip_init": True, "vn_hook": accept}
        if engine == "Anima":
            job = app._collect_anima_job(override)
            voice = app._anima_say
        else:
            job = app._collect_job(override)
            voice = app._say
        if job is None:
            say("The image generator needs a model on its own tab first.")
            return
        if app.hold.busy:
            app.hold.queue.append(job)
            app._show_queue()
            voice(f"RedVN picture queued. {len(app.hold.queue)} waiting.")
            return
        app._start_job(job)

    def write_image_prompt() -> None:
        try:
            count = max(1, int(image_count.get()))
        except (tk.TclError, ValueError):
            count = 4
        rows = (current().get("messages") or [])[-count:]
        if not rows:
            say("There are no messages to read.")
            return
        script = "\n".join(f"{speaker_name(current(), row)}: {shown_text(row)}" for row in rows)
        looks = appearances(current())
        url, key, model = kobold_settings()
        if not url:
            say("Set the Kobold address on the Captions tab.")
            return
        say("Writing the image prompt…")

        def work() -> None:
            try:
                reply = cardwright.kobold_chat(
                    url,
                    key,
                    [
                        {"role": "system", "content": "Write one image prompt for this scene. Use the character appearances. No commentary, no labels."},
                        {"role": "user", "content": f"Appearances:\n{looks}\n\nScene:\n{script[-4000:]}"},
                    ],
                    model=model,
                    temperature=0.7,
                    max_tokens=300,
                )
            except Exception as exc:
                app.after(0, lambda detail=exc: say(str(detail)))
                return

            def show() -> None:
                image_prompt.delete("1.0", "end")
                image_prompt.insert("1.0", reply.strip())
                say("Look over the prompt, then press Generate prompt.")

            app.after(0, show)

        threading.Thread(target=work, daemon=True).start()

    def generate_prompt() -> None:
        text = image_prompt.get("1.0", "end").strip()
        rows = current().get("messages") or []
        if not text or not rows:
            say("Write an image prompt, and have at least one message.")
            return
        illustrate(rows[-1], False, text)

    ttk.Button(edit_frame, text="Save edit", command=save_edit).pack(anchor="w", padx=8, pady=(0, 8))
    ttk.Button(actions, text="Edit", command=edit_message).pack(side="left", padx=(0, 4))
    ttk.Button(actions, text="Regen", command=regenerate).pack(side="left", padx=4)
    ttk.Button(actions, text="Delete", command=remove_message).pack(side="left", padx=4)
    ttk.Button(actions, text="Swipe", command=cycle_swipe).pack(side="left", padx=4)
    def draw_selected() -> None:
        row = selected_row()
        if not row:
            say("Click a message first.")
            return
        illustrate(row, False)

    ttk.Button(actions, text="Picture", command=draw_selected).pack(side="left", padx=4)

    def open_selected() -> None:
        row = selected_row()
        path = str((row or {}).get("image") or "")
        if not path and row:
            _text, pics = embedded_pictures(shown_text(row))
            path = pics[0] if pics else ""
        if not path:
            say("That message has no picture.")
            return
        open_picture(path)

    ttk.Button(actions, text="Open picture", command=open_selected).pack(side="left", padx=4)
    ttk.Label(actions, text="Click a message, then use these.", style="Muted.TLabel").pack(side="left", padx=8)
    def click_log(event) -> str:
        try:
            index = log.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return "break"
        picture = (state.get("image_at") or {}).get(str(index))
        if picture:
            open_picture(picture)
        for name in log.tag_names(index):
            if name.startswith("msg-"):
                pick_message(name[4:])
                break
        return "break"

    log.bind("<Button-1>", click_log)
    log.bind("<Key>", lambda _event: "break")
    ttk.Button(direction_row, text="Send", command=answer_direction).pack(side="right", padx=(8, 0), anchor="n")
    ttk.Button(chat_buttons, text="New", command=new_chat).pack(side="left")
    ttk.Button(chat_buttons, text="Delete", command=remove_chat).pack(side="left", padx=6)
    ttk.Button(send_row, text="Send", style="Primary.TButton", command=send).pack(side="left")
    ttk.Button(send_row, text="Say as character", command=say_as).pack(side="left", padx=8)
    ttk.Button(send_row, text="Export VN", command=lambda: export_vn()).pack(side="left")
    ttk.Button(image_row, text="Write prompt", command=lambda: write_image_prompt()).pack(side="left", padx=(8, 0))
    ttk.Button(image_row, text="Generate prompt", style="Primary.TButton", command=lambda: generate_prompt()).pack(side="left", padx=8)
    speaker_box.bind("<<ComboboxSelected>>", choose_speaker)
    persona_box.bind("<<ComboboxSelected>>", choose_persona)
    preset_box.bind("<<ComboboxSelected>>", choose_preset)
    chat_list.bind("<<ListboxSelect>>", open_chat)
    stored_ui = _read_json(store_root() / "ui.json", {})
    if isinstance(stored_ui, dict):
        try:
            text_size.set(max(11, min(24, int(stored_ui.get("text_size") or 14))))
        except (TypeError, ValueError):
            text_size.set(14)
    size_scale.configure(command=apply_text_size)

    ttk.Label(memory_form, text="Long-term memory", style="Card.TLabel").pack(anchor="w")
    ttk.Label(memory_form, text="Facts come back only when the scene shares their words. Replies can add new ones.", style="Muted.TLabel", wraplength=280).pack(anchor="w", pady=(2, 6))
    memory_list = tk.Listbox(memory_form, height=16, bg=INSET, fg=FG, selectbackground=PRIMARY, relief="flat", highlightthickness=0)
    memory_list.pack(fill="x", pady=4)
    memory_text = tk.StringVar()
    tk.Entry(memory_form, textvariable=memory_text, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", ipady=4)
    memory_row = ttk.Frame(memory_form, style="Card.TFrame")
    memory_row.pack(fill="x", pady=4)

    def paint_memory() -> None:
        memory_list.delete(0, "end")
        for fact in load_memory():
            memory_list.insert("end", str(fact.get("text") or "")[:80])

    def add_memory() -> None:
        text = memory_text.get().strip()
        if not text:
            return
        facts = load_memory()
        facts.insert(0, {"id": uuid.uuid4().hex, "text": text, "chat": current().get("id"), "at": datetime.now().isoformat(timespec="seconds")})
        save_memory(facts)
        memory_text.set("")
        paint_memory()

    def delete_memory() -> None:
        picked = memory_list.curselection()
        if not picked:
            return
        facts = load_memory()
        if picked[0] < len(facts):
            del facts[picked[0]]
        save_memory(facts)
        paint_memory()

    ttk.Button(memory_row, text="Add", command=add_memory).pack(side="left")
    ttk.Button(memory_row, text="Delete", command=delete_memory).pack(side="left", padx=4)

    def export_vn() -> None:
        chat = current()
        if not chat.get("messages"):
            say("This chat has no messages to export.")
            return
        folder = filedialog.askdirectory(title="Folder for the visual novel")
        if not folder:
            return
        dest = Path(folder)
        dest.mkdir(parents=True, exist_ok=True)
        character = find_card(chat.get("character_id") or "")
        persona = find_card(chat.get("persona_id") or "")
        scenes = []
        for index, row in enumerate(chat["messages"], start=1):
            image_name = ""
            source = str(row.get("image") or "")
            if source and Path(source).is_file():
                image_name = f"scene-{index}{Path(source).suffix.lower() or '.png'}"
                target = dest / image_name
                target.write_bytes(Path(source).read_bytes())
            scenes.append(
                {
                    "speaker": speaker_name(chat, row),
                    "text": shown_text(row),
                    "image": image_name,
                }
            )
        title = str(chat.get("title") or "RedVN")
        payload = json.dumps({"title": title, "scenes": scenes}, ensure_ascii=False).replace("<", "\\u003c")
        safe_title = title.replace("&", "&" + "amp;").replace("<", "&" + "lt;").replace(">", "&" + "gt;")
        html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{safe_title}</title>
<style>
body {{ margin:0; background:#16080a; color:#f6eee8; font:18px/1.45 "Segoe UI", sans-serif; }}
main {{ min-height:100vh; display:grid; place-items:end center; background:#16080a center/cover no-repeat; }}
.box {{ width:min(760px, calc(100% - 32px)); margin:24px; background:#2a1214ee; border-radius:22px; padding:18px 20px 16px; }}
.name {{ color:#e39b88; font-weight:700; }}
p {{ white-space:pre-wrap; }}
button {{ border:0; border-radius:999px; background:#e39b88; color:#2a1210; padding:8px 16px; font:inherit; cursor:pointer; }}
</style></head><body><main id="stage"><section class="box"><div class="name" id="name"></div><p id="line"></p><button id="next">Next</button></section></main>
<script>
const story = {payload};
let index = 0;
const stage = document.getElementById("stage");
function show() {{
  const scene = story.scenes[index];
  document.getElementById("name").textContent = scene.speaker;
  document.getElementById("line").textContent = scene.text;
  stage.style.backgroundImage = scene.image ? "url('" + scene.image + "')" : "none";
  document.getElementById("next").textContent = index < story.scenes.length - 1 ? "Next" : "Start over";
}}
document.getElementById("next").onclick = () => {{ index = (index + 1) % story.scenes.length; show(); }};
show();
</script></body></html>"""
        (dest / "index.html").write_text(html, encoding="utf-8")
        say(f"Exported. Open {dest / 'index.html'} in a browser.")
        messagebox.showinfo("RedVN", f"The visual novel is here:\n{dest / 'index.html'}")

    refresh_cast()
    paint_memory()
    refresh_chats()
    apply_text_size()


def _key_text(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def entry_from_raw(raw: dict) -> dict | None:
    content = str(raw.get("content") or raw.get("text") or "").strip()
    keys = _key_text(raw.get("keys") if raw.get("keys") not in (None, "") else raw.get("key") or raw.get("keywords") or raw.get("primaryKeys"))
    secondary = _key_text(raw.get("secondaryKeys") or raw.get("secondary_keys") or raw.get("keysecondary") or "")
    if secondary:
        keys = ", ".join(part for part in (keys, secondary) if part)
    name = str(raw.get("name") or raw.get("comment") or "").strip()
    description = str(raw.get("description") or raw.get("comment") or name or "").strip()
    if not content and not keys and not name:
        return None
    enabled = raw.get("enabled", True)
    if raw.get("disable") is True:
        enabled = False
    return {
        "id": str(raw.get("id") or uuid.uuid4().hex),
        "name": name[:120],
        "keys": keys,
        "description": description[:240],
        "content": content,
        "enabled": bool(enabled),
        "constant": bool(raw.get("constant")),
        "source": raw,
    }


def books_from_payload(payload) -> list[dict]:
    found: list[dict] = []
    seen: set[tuple] = set()

    def add(lore, entries, folders=None) -> None:
        if isinstance(entries, dict):
            entries = list(entries.values())
        rows = []
        for item in entries or []:
            if isinstance(item, dict):
                row = entry_from_raw(item)
                if row:
                    rows.append(row)
        meta = lore if isinstance(lore, dict) else {}
        if not rows and not str(meta.get("name") or "").strip():
            return
        first = str(rows[0].get("content") or "")[:80] if rows else ""
        mark = (str(meta.get("name") or "Imported lorebook"), len(rows), first)
        if mark in seen:
            return
        seen.add(mark)
        found.append(
            {
                "id": uuid.uuid4().hex,
                "name": str(meta.get("name") or "Imported lorebook")[:120],
                "description": str(meta.get("description") or ""),
                "entries": rows,
                "folders": list(folders or []),
                "source": meta if isinstance(meta, dict) else {},
            }
        )

    def entry_rows(entries) -> list:
        if isinstance(entries, dict):
            return [item for item in entries.values() if isinstance(item, dict)]
        if isinstance(entries, list):
            return [item for item in entries if isinstance(item, dict)]
        return []

    def entryish(rows: list) -> bool:
        for row in rows[:8]:
            if any(key in row for key in ("content", "keys", "key", "keywords", "comment", "text")):
                return True
        return False

    def walk(value, depth: int = 0) -> None:
        if depth > 10:
            return
        if isinstance(value, str):
            text = value.strip()
            if not text or text[0] not in "{[" or len(text) > 2_000_000:
                return
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                return
        if isinstance(value, list):
            for item in value:
                walk(item, depth + 1)
            return
        if not isinstance(value, dict):
            return
        if value.get("type") == "marinara_lorebook" and isinstance(value.get("data"), dict):
            data = value["data"]
            add(data.get("lorebook") or data, data.get("entries") or [], data.get("folders") or [])
            return
        rows = entry_rows(value.get("entries"))
        if rows and entryish(rows):
            add(value, rows, value.get("folders") or [])
        for key, item in value.items():
            if key in ("entries", "embedding", "embeddings", "image", "avatar", "avatarUrl", "png", "gallery", "sprites"):
                continue
            if isinstance(item, (dict, list)):
                walk(item, depth + 1)
            elif isinstance(item, str) and key in (
                "character_book",
                "characterBook",
                "lorebook",
                "lorebooks",
                "embeddedLorebook",
                "embedded_lorebook",
                "worldinfo",
                "world_info",
                "world",
                "data",
            ):
                walk(item, depth + 1)

    walk(payload)
    return found


def books_attached_to(source: dict) -> list[dict]:
    if not isinstance(source, dict):
        return []
    return books_from_payload(source)


LORE_REFRESH: list = []


def watch_lorebooks(callback) -> None:
    if callback not in LORE_REFRESH:
        LORE_REFRESH.append(callback)


def refresh_lorebook_views() -> None:
    for callback in list(LORE_REFRESH):
        try:
            callback()
        except Exception:
            pass


def verify_lorebooks(saved: list[dict]) -> str:
    on_disk = {str(book.get("id")): book for book in load_lorebooks()}
    lines = []
    for book in saved:
        name = str(book.get("name") or "Lorebook")
        wanted = len(book.get("entries") or [])
        found = on_disk.get(str(book.get("id")))
        if found is None:
            lines.append(f"{name}: not in the lorebook library.")
            continue
        got = len(found.get("entries") or [])
        if got != wanted:
            lines.append(f"{name}: saved, but it has {got} entries instead of {wanted}.")
        else:
            lines.append(f"{name}: saved, {got} entries, in the lorebook library.")
    refresh_lorebook_views()
    return "\n".join(lines)


def ask_store_lorebooks(box, books: list[dict]) -> tuple[list[dict], str]:
    if not books:
        return [], ""
    lines = [f"• {book.get('name') or 'Lorebook'} — {len(book.get('entries') or [])} entries" for book in books]
    shown = "\n".join(lines[:12])
    more = "" if len(lines) <= 12 else f"\n…and {len(lines) - 12} more"
    if not box.askyesno(
        "Lorebook found",
        "This card includes a lorebook.\n\n" + shown + more + "\n\nSave it to the lorebook library and link it to the card?",
    ):
        return [], " The lorebook was left inside the card only."
    saved = store_lorebooks(books)
    report = verify_lorebooks(saved)
    box.showinfo("Lorebook check", report or "No lorebook was saved.")
    failed = "not in the lorebook library" in report
    return saved, (" Lorebook check failed." if failed else " " + " ".join(report.splitlines()))


def store_lorebooks(books: list[dict]) -> list[dict]:
    existing = load_lorebooks()
    saved = []
    for book in books:
        entries = book.get("entries") or []
        first = str(entries[0].get("content") or "")[:80] if entries else ""
        key = (str(book.get("name") or ""), len(entries), first)
        match = next(
            (
                row
                for row in existing
                if (
                    str(row.get("name") or ""),
                    len(row.get("entries") or []),
                    str((row.get("entries") or [{}])[0].get("content") or "")[:80],
                )
                == key
            ),
            None,
        )
        if match:
            saved.append(match)
            continue
        stored = dict(book)
        stored["id"] = str(stored.get("id") or uuid.uuid4().hex)
        existing.insert(0, stored)
        saved.append(stored)
    save_lorebooks(existing)
    return saved


def books_from_file(path: Path) -> list[dict]:
    import zipfile

    if path.suffix.lower() == ".zip":
        books = []
        with zipfile.ZipFile(path) as bundle:
            for name in bundle.namelist():
                if name.lower().endswith(".json"):
                    try:
                        payload = json.loads(bundle.read(name).decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    books.extend(books_from_payload(payload))
        return books
    payload = json.loads(path.read_text(encoding="utf-8"))
    return books_from_payload(payload)


def attach_lorebooks(app, page) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    BG, SURFACE, INSET, FG, PRIMARY = "#16080a", "#2a1214", "#140709", "#f6eee8", "#e39b88"
    page.columnconfigure(0, weight=1)
    page.rowconfigure(0, weight=1)
    form = app._make_scroller(page, bg=SURFACE, width=720, style="Card.TFrame")
    state = {"books": load_lorebooks(), "book_id": "", "entry_id": ""}
    ttk.Label(form, text="Lorebooks", style="Card.TLabel").pack(anchor="w")
    ttk.Label(
        form,
        text="Import a Marinara lorebook (.marinara.json), a World Info JSON file, or a zip of them. The original fields stay on each entry. RedVN uses the keys, the short description, and the content as written.",
        style="Muted.TLabel",
        wraplength=680,
    ).pack(anchor="w", pady=(2, 6))
    book_var = tk.StringVar()
    book_menu = ttk.Combobox(form, textvariable=book_var, state="readonly")
    book_menu.pack(fill="x", pady=4)
    book_name = tk.StringVar()
    tk.Entry(form, textvariable=book_name, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", ipady=4)
    book_row = ttk.Frame(form, style="Card.TFrame")
    book_row.pack(fill="x", pady=4)
    status = tk.Label(form, text="", bg=SURFACE, fg="#b39b94", anchor="w")
    status.pack(fill="x")
    ttk.Label(form, text="Entries", style="Card.TLabel").pack(anchor="w", pady=(8, 0))
    entry_list = tk.Listbox(form, height=8, bg=INSET, fg=FG, selectbackground=PRIMARY, relief="flat", highlightthickness=0)
    entry_list.pack(fill="x", pady=4)
    ttk.Label(form, text="Keys, comma separated", style="Muted.TLabel").pack(anchor="w")
    keys_var = tk.StringVar()
    tk.Entry(form, textvariable=keys_var, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", ipady=4)
    ttk.Label(form, text="Short description, used by the router", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    desc_var = tk.StringVar()
    tk.Entry(form, textvariable=desc_var, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", ipady=4)
    ttk.Label(form, text="Text given to the AI as written", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    content_box = tk.Text(form, height=8, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word")
    content_box.pack(fill="x", pady=4)
    constant_var = tk.BooleanVar(value=False)
    tk.Checkbutton(form, text="Always include", variable=constant_var, bg=SURFACE, fg=FG, selectcolor=BG, activebackground=SURFACE, activeforeground=FG).pack(anchor="w")
    entry_row = ttk.Frame(form, style="Card.TFrame")
    entry_row.pack(fill="x", pady=4)

    def say(text: str) -> None:
        status.configure(text=text[:220])

    def selected_book() -> dict | None:
        for book in state["books"]:
            if book.get("id") == state["book_id"]:
                return book
        return None

    def selected_entry() -> dict | None:
        book = selected_book()
        if not book:
            return None
        for entry in book.get("entries") or []:
            if entry.get("id") == state["entry_id"]:
                return entry
        return None

    def paint() -> None:
        state["books"] = load_lorebooks()
        book_menu["values"] = [str(book.get("name") or "Lorebook") for book in state["books"]]
        book = selected_book()
        if book:
            book_var.set(str(book.get("name") or "Lorebook"))
            book_name.set(str(book.get("name") or ""))
        entry_list.delete(0, "end")
        for entry in (book or {}).get("entries") or []:
            label = str(entry.get("name") or entry.get("description") or entry.get("keys") or "Entry")
            entry_list.insert("end", label[:80])

    def new_book() -> None:
        book = {"id": uuid.uuid4().hex, "name": "New lorebook", "description": "", "entries": [], "folders": [], "source": {}}
        books = load_lorebooks()
        books.insert(0, book)
        save_lorebooks(books)
        state["book_id"] = book["id"]
        paint()

    def open_book(_event=None) -> None:
        picked = book_menu.current()
        if picked < 0 or picked >= len(state["books"]):
            return
        state["book_id"] = state["books"][picked]["id"]
        state["entry_id"] = ""
        paint()

    def rename_book() -> None:
        book = selected_book()
        if not book:
            return
        book["name"] = book_name.get().strip() or "Lorebook"
        save_lorebooks(state["books"])
        paint()

    def delete_book() -> None:
        state["books"] = [book for book in state["books"] if book.get("id") != state["book_id"]]
        save_lorebooks(state["books"])
        state["book_id"] = state["books"][0]["id"] if state["books"] else ""
        paint()

    def import_books() -> None:
        path = filedialog.askopenfilename(
            title="Marinara lorebook",
            filetypes=[("Lorebook", "*.json *.marinara.json *.zip"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            incoming = books_from_file(Path(path))
        except (OSError, json.JSONDecodeError, zipfile_error()) as exc:
            messagebox.showerror("Lorebooks", f"Could not read that file.\n{exc}")
            return
        if not incoming:
            say("That file had no lorebook entries.")
            return
        books = load_lorebooks()
        books = incoming + books
        save_lorebooks(books)
        state["book_id"] = incoming[0]["id"]
        paint()
        count = sum(len(book.get("entries") or []) for book in incoming)
        say(f"Imported {len(incoming)} lorebook{'s' if len(incoming) != 1 else ''}, {count} entries.")

    watch_lorebooks(paint)

    def new_entry() -> None:
        book = selected_book()
        if not book:
            say("Make a lorebook first.")
            return
        entry = {"id": uuid.uuid4().hex, "name": "New entry", "keys": "", "description": "", "content": "", "enabled": True, "constant": False, "source": {}}
        book.setdefault("entries", []).append(entry)
        state["entry_id"] = entry["id"]
        save_lorebooks(state["books"])
        paint()

    def show_entry(_event=None) -> None:
        book = selected_book()
        picked = entry_list.curselection()
        if not book or not picked:
            return
        entry = book["entries"][picked[0]]
        state["entry_id"] = entry["id"]
        keys_var.set(str(entry.get("keys") or ""))
        desc_var.set(str(entry.get("description") or ""))
        constant_var.set(bool(entry.get("constant")))
        content_box.delete("1.0", "end")
        content_box.insert("1.0", str(entry.get("content") or ""))

    def save_entry() -> None:
        entry = selected_entry()
        if not entry:
            return
        entry["keys"] = keys_var.get().strip()
        entry["description"] = desc_var.get().strip()
        entry["content"] = content_box.get("1.0", "end").strip()
        entry["constant"] = bool(constant_var.get())
        entry["enabled"] = True
        if not entry.get("name"):
            entry["name"] = entry["description"][:80] or "Entry"
        source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
        source["keys"] = [part.strip() for part in entry["keys"].split(",") if part.strip()]
        source["description"] = entry["description"]
        source["content"] = entry["content"]
        source["constant"] = entry["constant"]
        source["enabled"] = True
        entry["source"] = source
        save_lorebooks(state["books"])
        paint()
        say("Entry saved. The original Marinara fields stay in the entry.")

    def delete_entry() -> None:
        book = selected_book()
        if not book:
            return
        book["entries"] = [entry for entry in book.get("entries") or [] if entry.get("id") != state["entry_id"]]
        state["entry_id"] = ""
        save_lorebooks(state["books"])
        paint()

    ttk.Button(book_row, text="New", command=new_book).pack(side="left")
    ttk.Button(book_row, text="Rename", command=rename_book).pack(side="left", padx=4)
    ttk.Button(book_row, text="Delete", command=delete_book).pack(side="left", padx=4)
    ttk.Button(book_row, text="Import Marinara", command=import_books).pack(side="left")
    ttk.Button(entry_row, text="Add entry", command=new_entry).pack(side="left")
    ttk.Button(entry_row, text="Save entry", style="Primary.TButton", command=save_entry).pack(side="left", padx=4)
    ttk.Button(entry_row, text="Delete entry", command=delete_entry).pack(side="left")
    book_menu.bind("<<ComboboxSelected>>", open_book)
    entry_list.bind("<<ListboxSelect>>", show_entry)
    paint()


def zipfile_error():
    import zipfile

    return zipfile.BadZipFile


def presets_from_payload(payload) -> list[dict]:
    if isinstance(payload, list):
        found = []
        for row in payload:
            item = preset_from_payload(row) if isinstance(row, dict) else None
            if item:
                found.append(item)
        return found
    if isinstance(payload, dict) and isinstance(payload.get("presets"), list):
        return presets_from_payload(payload["presets"])
    item = preset_from_payload(payload)
    return [item] if item else []


def attach_presets(app, page) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    BG, SURFACE, INSET, FG, PRIMARY = "#16080a", "#2a1214", "#140709", "#f6eee8", "#e39b88"
    page.columnconfigure(0, weight=1)
    page.rowconfigure(0, weight=1)
    form = app._make_scroller(page, bg=SURFACE, width=720, style="Card.TFrame")
    state = {"id": "", "vars": []}
    ttk.Label(form, text="Presets", style="Card.TLabel").pack(anchor="w")
    ttk.Label(
        form,
        text="Import a Marinara preset. Turn sections, groups, and boolean variables on or off. RedVN uses the enabled ones when that preset is selected on the chat.",
        style="Muted.TLabel",
        wraplength=680,
    ).pack(anchor="w", pady=(2, 6))
    preset_var = tk.StringVar()
    preset_menu = ttk.Combobox(form, textvariable=preset_var, state="readonly")
    preset_menu.pack(fill="x", pady=4)
    row = ttk.Frame(form, style="Card.TFrame")
    row.pack(fill="x", pady=4)
    status = tk.Label(form, text="", bg=SURFACE, fg="#b39b94", anchor="w")
    status.pack(fill="x")
    toggles = ttk.Frame(form, style="Card.TFrame")
    toggles.pack(fill="x", pady=(8, 0))

    def say(text: str) -> None:
        status.configure(text=text[:220])

    def selected() -> dict | None:
        for preset in load_presets():
            if preset.get("id") == state["id"]:
                return preset
        return None

    def paint_menu() -> None:
        rows = load_presets()
        preset_menu["values"] = [str(preset.get("name") or "Preset") for preset in rows]
        current = selected()
        if current:
            preset_var.set(str(current.get("name") or "Preset"))

    def paint_toggles() -> None:
        for child in toggles.winfo_children():
            child.destroy()
        state["vars"] = []
        preset = selected()
        if not preset:
            return
        ttk.Label(toggles, text="Groups", style="Card.TLabel").pack(anchor="w")
        for group in preset.get("groups") or []:
            flag = tk.BooleanVar(value=bool(group.get("enabled", True)))
            state["vars"].append(flag)
            tk.Checkbutton(
                toggles,
                text=str(group.get("name") or "Group"),
                variable=flag,
                command=lambda item=group, var=flag: set_enabled(item, var),
                bg=SURFACE,
                fg=FG,
                selectcolor=BG,
                activebackground=SURFACE,
                activeforeground=FG,
            ).pack(anchor="w")
        ttk.Label(toggles, text="Sections", style="Card.TLabel").pack(anchor="w", pady=(8, 0))
        for section in preset.get("sections") or []:
            flag = tk.BooleanVar(value=bool(section.get("enabled", True)))
            state["vars"].append(flag)
            label = str(section.get("name") or section.get("identifier") or "Section")
            if section.get("is_marker"):
                label += " (marker)"
            tk.Checkbutton(
                toggles,
                text=label,
                variable=flag,
                command=lambda item=section, var=flag: set_enabled(item, var),
                bg=SURFACE,
                fg=FG,
                selectcolor=BG,
                activebackground=SURFACE,
                activeforeground=FG,
            ).pack(anchor="w")
        if preset.get("variables"):
            ttk.Label(toggles, text="Variables", style="Card.TLabel").pack(anchor="w", pady=(8, 0))
        values = preset.setdefault("values", {})
        for variable in preset.get("variables") or []:
            name = str(variable.get("name") or "")
            options = [option for option in variable.get("options") or [] if isinstance(option, dict)]
            title = str(variable.get("label") or name or "Variable")
            if len(options) <= 1:
                chosen = str(values.get(name) or "")
                on_value = str(options[0].get("value") or "on") if options else "on"
                flag = tk.BooleanVar(value=bool(chosen))
                state["vars"].append(flag)

                def flip(item_name=name, on=on_value, var=flag) -> None:
                    current = selected()
                    if not current:
                        return
                    current.setdefault("values", {})[item_name] = on if var.get() else ""
                    save_presets(load_presets_replacing(current))
                    say("Saved the variable toggle.")

                tk.Checkbutton(
                    toggles,
                    text=title,
                    variable=flag,
                    command=flip,
                    bg=SURFACE,
                    fg=FG,
                    selectcolor=BG,
                    activebackground=SURFACE,
                    activeforeground=FG,
                ).pack(anchor="w")
            else:
                labels = [str(option.get("label") or option.get("value") or "") for option in options]
                current_value = str(values.get(name) or options[0].get("value") or "")
                shown = labels[0]
                for option, label in zip(options, labels):
                    if str(option.get("value") or "") == current_value:
                        shown = label
                var = tk.StringVar(value=shown)
                state["vars"].append(var)
                line = ttk.Frame(toggles, style="Card.TFrame")
                line.pack(fill="x", pady=2)
                ttk.Label(line, text=title, style="Muted.TLabel").pack(side="left")
                box = ttk.Combobox(line, textvariable=var, state="readonly", values=labels, width=24)
                box.pack(side="left", padx=8)

                def pick(_event=None, item_name=name, opts=options, labels=labels, var=var) -> None:
                    current = selected()
                    if not current:
                        return
                    value = ""
                    for option, label in zip(opts, labels):
                        if label == var.get():
                            value = str(option.get("value") or "")
                    current.setdefault("values", {})[item_name] = value
                    save_presets(load_presets_replacing(current))

                box.bind("<<ComboboxSelected>>", pick)

    def load_presets_replacing(preset: dict) -> list[dict]:
        rows = [row for row in load_presets() if row.get("id") != preset.get("id")]
        rows.insert(0, preset)
        return rows

    def set_enabled(item: dict, var) -> None:
        preset = selected()
        if not preset:
            return
        item["enabled"] = bool(var.get())
        source = item.get("source")
        if isinstance(source, dict):
            source["enabled"] = item["enabled"]
        save_presets(load_presets_replacing(preset))
        say("Saved the toggle.")

    def open_preset(_event=None) -> None:
        rows = load_presets()
        picked = preset_menu.current()
        if picked < 0 or picked >= len(rows):
            return
        state["id"] = rows[picked]["id"]
        paint_menu()
        paint_toggles()

    def import_preset() -> None:
        path = filedialog.askopenfilename(title="Marinara preset", filetypes=[("Preset", "*.json *.marinara.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            incoming = presets_from_payload(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Presets", f"Could not read that file.\n{exc}")
            return
        if not incoming:
            say("That file had no preset.")
            return
        rows = incoming + load_presets()
        save_presets(rows)
        state["id"] = incoming[0]["id"]
        paint_menu()
        paint_toggles()
        say(f"Imported {len(incoming)} preset{'s' if len(incoming) != 1 else ''}.")

    def delete_preset() -> None:
        if not state["id"]:
            return
        save_presets([row for row in load_presets() if row.get("id") != state["id"]])
        rows = load_presets()
        state["id"] = rows[0]["id"] if rows else ""
        paint_menu()
        paint_toggles()

    ttk.Button(row, text="Import Marinara", command=import_preset).pack(side="left")
    ttk.Button(row, text="Delete", command=delete_preset).pack(side="left", padx=8)
    preset_menu.bind("<<ComboboxSelected>>", open_preset)
    rows = load_presets()
    if rows:
        state["id"] = rows[0]["id"]
    paint_menu()
    paint_toggles()


