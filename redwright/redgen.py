"""RedGen — local image studio for Windows 11 and AMD GPUs.

Uses PyTorch with ROCm, the same kind of build as a working Comfy install.
Nothing is sent off the PC.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP = "RedWright"
BUILD = "62"  # stamp: RedWright build 62.
BG = "#16080a"
SURFACE = "#2a1214"
INSET = "#140709"
FG = "#f6eee8"
MUTED = "#b39b94"
PRIMARY = "#e39b88"
ACCENT_INK = "#2a1210"
BORDER = "#5a3330"
PAPER = "#e6e1dc"
INK = "#1c1210"
GOLD = "#d4a574"
DEFAULT_THEME = {
    "bg": BG,
    "surface": SURFACE,
    "inset": INSET,
    "fg": FG,
    "muted": MUTED,
    "line": BORDER,
    "accent": PRIMARY,
    "accent_ink": ACCENT_INK,
    "paper": PAPER,
    "ink": INK,
    "gold": GOLD,
    "font": "Segoe UI",
    "size": 10,
    "button": "#1c0d10",
    "button_text": FG,
    "button_shape": "Pill",
}
THEME_PRESETS = {
    "Cardwright": dict(DEFAULT_THEME),
    "RedWright": {
        **DEFAULT_THEME,
        "bg": "#12110f",
        "surface": "#1c1a17",
        "inset": "#0e0d0b",
        "fg": "#f4efe6",
        "muted": "#a39b90",
        "line": "#3a342c",
        "accent": "#e23d2b",
        "accent_ink": "#fff8f4",
        "paper": "#f3ead7",
        "ink": "#241c16",
        "gold": "#e23d2b",
        "button": "#241f1b",
        "button_text": "#f4efe6",
        "button_shape": "Pill",
    },
    "Paper": {
        **DEFAULT_THEME,
        "bg": "#efe4d4",
        "surface": "#f7f1e6",
        "inset": "#fffaf3",
        "fg": "#241c16",
        "muted": "#6d5c50",
        "line": "#ddcbb6",
        "accent": "#c45c3e",
        "accent_ink": "#fff8f4",
        "paper": "#fffdf8",
        "ink": "#241c16",
        "gold": "#c45c3e",
        "button": "#e7d8c4",
        "button_text": "#241c16",
        "button_shape": "Pill",
    },
    "Night": {
        **DEFAULT_THEME,
        "bg": "#0c1016",
        "surface": "#161c27",
        "inset": "#0a0e14",
        "fg": "#e7eef8",
        "muted": "#93a0b5",
        "line": "#2c384c",
        "accent": "#8eb6ff",
        "accent_ink": "#0c1016",
        "paper": "#dfe7f2",
        "ink": "#121820",
        "gold": "#8eb6ff",
        "button": "#121822",
        "button_text": "#e7eef8",
        "button_shape": "Pill",
    },
}
_THEME_ROLES = {
    "#16080a": "bg",
    "#2a1214": "surface",
    "#140709": "inset",
    "#f6eee8": "fg",
    "#b39b94": "muted",
    "#5a3330": "line",
    "#e39b88": "accent",
    "#2a1210": "accent_ink",
    "#e6e1dc": "paper",
    "#1c1210": "ink",
    "#d4a574": "gold",
    "#1c0d10": "button",
    "#fff8f5": "accent_ink",
    "#fff8f4": "accent_ink",
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

LIVE_THEME = dict(DEFAULT_THEME)
_THEME_BUTTONS: list = []


def _theme_hex(value, fallback: str) -> str:
    text = str(value or "").strip()
    if len(text) == 7 and text.startswith("#"):
        return text
    return fallback


def _surface_of(widget) -> str:
    current = widget
    while current is not None:
        try:
            value = str(current.cget("bg"))
            if value.startswith("#"):
                return value
        except tk.TclError:
            pass
        try:
            name = str(current.cget("style"))
        except tk.TclError:
            name = ""
        if "Card" in name:
            return _theme_hex(LIVE_THEME.get("surface"), SURFACE)
        if name:
            return _theme_hex(LIVE_THEME.get("bg"), BG)
        current = getattr(current, "master", None)
    return _theme_hex(LIVE_THEME.get("bg"), BG)


class ThemeButton(tk.Canvas):
    """Pill button drawn with canvas shapes. A picture per button was stalling scroll and clicks."""

    def __init__(self, master=None, **kwargs):
        self._text = str(kwargs.pop("text", "") or "")
        self._command = kwargs.pop("command", None)
        self._style_name = str(kwargs.pop("style", "") or "TButton")
        self._state = str(kwargs.pop("state", "normal") or "normal")
        for unused in ("width", "padding", "cursor", "takefocus", "compound", "image", "underline"):
            kwargs.pop(unused, None)
        width = max(88, len(self._text) * 8 + 36)
        super().__init__(master, highlightthickness=0, bd=0, bg=_surface_of(master), cursor="hand2", height=40, width=width)
        self._drawn = (0, 0)
        self._busy = False
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", self._on_configure)
        _THEME_BUTTONS.append(self)
        self.after_idle(self._render)

    def destroy(self):
        try:
            _THEME_BUTTONS.remove(self)
        except ValueError:
            pass
        super().destroy()

    def _on_click(self, _event=None):
        if str(self._state) == "disabled" or not callable(self._command):
            return
        self._command()

    def _on_configure(self, event):
        if self._busy or event.widget is not self or event.width < 2:
            return
        if abs(event.width - self._drawn[0]) < 2 and event.height == self._drawn[1]:
            return
        self._render(event.width, event.height)

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
        elif isinstance(cnf, str):
            return self.cget(cnf)
        changed = False
        if "text" in kwargs:
            self._text = str(kwargs.pop("text") or "")
            changed = True
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "state" in kwargs:
            self._state = str(kwargs.pop("state") or "normal")
            changed = True
        if "style" in kwargs:
            self._style_name = str(kwargs.pop("style") or "TButton")
            changed = True
        if kwargs:
            self._busy = True
            try:
                super().configure(**kwargs)
            finally:
                self._busy = False
        if changed:
            self._drawn = (0, 0)
            self._render()
        return None

    config = configure

    def cget(self, key):
        if key == "text":
            return self._text
        if key == "state":
            return self._state
        if key == "style":
            return self._style_name
        return super().cget(key)

    def __getitem__(self, key):
        return self.cget(key)

    def _palette(self):
        primary = "Primary" in self._style_name
        if primary:
            fill = _theme_hex(LIVE_THEME.get("accent"), PRIMARY)
            ink = _theme_hex(LIVE_THEME.get("accent_ink"), ACCENT_INK)
            edge = fill
        else:
            fill = _theme_hex(LIVE_THEME.get("button"), "#1c0d10")
            ink = _theme_hex(LIVE_THEME.get("button_text"), FG)
            edge = _theme_hex(LIVE_THEME.get("line"), BORDER)
        if str(self._state) == "disabled":
            ink = _theme_hex(LIVE_THEME.get("muted"), MUTED)
        return fill, ink, edge

    def _radius(self, height: int) -> int:
        shape = str(LIVE_THEME.get("button_shape") or "Pill")
        if shape == "Square":
            return 2
        if shape == "Rounded":
            return 12
        return max(2, height // 2)

    def _blob(self, x1: int, y1: int, x2: int, y2: int, radius: int, fill: str) -> None:
        radius = max(1, min(int(radius), (x2 - x1) // 2, (y2 - y1) // 2))
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline=fill)
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline=fill)
        self.create_oval(x1, y1, x1 + 2 * radius, y1 + 2 * radius, fill=fill, outline=fill)
        self.create_oval(x2 - 2 * radius, y1, x2, y1 + 2 * radius, fill=fill, outline=fill)
        self.create_oval(x1, y2 - 2 * radius, x1 + 2 * radius, y2, fill=fill, outline=fill)
        self.create_oval(x2 - 2 * radius, y2 - 2 * radius, x2, y2, fill=fill, outline=fill)

    def _render(self, width: int | None = None, height: int | None = None) -> None:
        self._busy = True
        try:
            actual = int(width or self.winfo_width() or 0)
            if actual < 2:
                actual = max(88, len(self._text) * 8 + 36)
            tall = 40 if not height or height < 8 else int(height)
            fill, ink, edge = self._palette()
            outside = _surface_of(self.master)
            size = max(11, int(LIVE_THEME.get("size") or 10) + 2)
            self.delete("all")
            super().configure(bg=outside)
            if edge != fill:
                self._blob(1, 2, actual - 2, tall - 2, self._radius(tall - 4), edge)
                self._blob(2, 3, actual - 3, tall - 3, self._radius(tall - 6), fill)
            else:
                self._blob(1, 2, actual - 2, tall - 2, self._radius(tall - 4), fill)
            self.create_text(actual / 2, tall / 2, text=self._text, fill=ink, font=("Segoe UI", size))
            self._drawn = (actual, tall)
        except tk.TclError:
            pass
        finally:
            self._busy = False


# Buttons stay real ttk widgets. A canvas per button made every click and scroll repaint the whole window.
CAPTION_PROMPTS = {
    "character": "Describe this person for a training caption. Cover face, hair, clothes, pose, and the setting. Use one line of comma-separated phrases. Do not invent a name.",
    "style": "Describe the visual style of this picture for a training caption. Cover medium, lighting, and rendering. Use one line of comma-separated phrases.",
    "concept": "Describe the main subject of this picture for a training caption. Use one line of comma-separated phrases. Do not add a story.",
}

CLIP_TAGS = (
    "portrait", "close-up", "headshot", "upper body", "full body", "side view", "from behind", "profile",
    "looking at viewer", "looking away", "smile", "serious expression", "open mouth", "woman", "man", "girl",
    "boy", "child", "person", "face", "long hair", "short hair", "blonde hair", "brown hair", "black hair",
    "red hair", "white hair", "blue hair", "ponytail", "braid", "bun", "bangs", "glasses", "hat", "cap",
    "hood", "earrings", "necklace", "blue eyes", "brown eyes", "green eyes", "shirt", "t-shirt", "jacket",
    "coat", "dress", "skirt", "pants", "jeans", "suit", "armor", "uniform", "standing", "sitting", "walking",
    "running", "arms crossed", "hand on hip", "holding an object", "outdoors", "indoors", "studio", "street",
    "forest", "beach", "room", "plain background", "city", "night", "day", "sunlight", "soft light", "rim light",
    "photograph", "anime", "illustration", "painting", "3d render", "sketch", "watercolor", "oil painting",
    "pixel art", "cinematic", "film still", "blurry background", "sharp focus", "colorful", "monochrome",
    "red", "blue", "green", "yellow", "white", "black", "pastel", "dark", "bright", "logo", "text", "weapon",
    "flower", "animal", "cat", "dog", "car", "building", "landscape", "food", "robot", "fantasy", "science fiction",
    "medieval", "modern", "low angle", "high angle", "wide shot", "macro", "two people", "crowd", "hands",
    "boots", "sneakers", "scarf", "tie", "makeup", "beard", "freckles", "pale skin", "dark skin", "curly hair",
    "straight hair", "wet hair", "window light", "neon light", "fog", "rain", "snow", "fire", "water", "sky",
)

CONFIG = Path.home() / "AppData" / "Roaming" / "RedGen" / "config.json"
if sys.platform != "win32":
    CONFIG = Path.home() / ".redgen" / "config.json"

_SPELL_WORD = re.compile(r"[A-Za-z][A-Za-z']*")


class Spell:
    def __init__(self) -> None:
        self.words: set[str] | None = None
        self.common: dict[str, int] = {}
        self.added: set[str] = set()
        self._lock = threading.Lock()
        self._added_path = CONFIG.parent / "spell-added.txt"

    def load(self) -> None:
        if self.words is not None:
            return
        with self._lock:
            if self.words is not None:
                return
            path = Path(__file__).with_name("spell_words.gz")
            words: set[str] = set()
            common: dict[str, int] = {}
            if path.is_file():
                import gzip

                lines = gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()
                if lines and lines[0].isdigit():
                    count = int(lines[0])
                    lines = lines[1:]
                    common = {word: index for index, word in enumerate(lines[:count])}
                words = set(lines)
            try:
                if self._added_path.is_file():
                    self.added = {
                        line.strip().lower()
                        for line in self._added_path.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    }
            except OSError:
                self.added = set()
            self.common = common
            self.words = words

    def known(self, word: str) -> bool:
        bank = self.words
        if bank is None:
            return True
        text = word.lower().strip("'")
        if not text or text in bank or text in self.added:
            return True
        if text.endswith("'s") and text[:-2] in bank:
            return True
        for suffix in ("n't", "'re", "'ve", "'ll", "'d", "'m"):
            if text.endswith(suffix) and text[: -len(suffix)] in bank:
                return True
        return False

    def add(self, word: str) -> None:
        text = word.lower().strip("'")
        if not text:
            return
        self.load()
        self.added.add(text)
        self._added_path.parent.mkdir(parents=True, exist_ok=True)
        self._added_path.write_text("\n".join(sorted(self.added)) + "\n", encoding="utf-8")

    def suggest(self, word: str, limit: int = 6) -> list[str]:
        self.load()
        text = word.lower().strip("'")
        if not text or self.known(word):
            return []
        found = self._known(self._edits(text))
        if not found and 3 <= len(text) <= 10:
            for edit in self._edits(text):
                found.update(self._known(self._edits(edit)))
                if len(found) >= 12:
                    break
        common = {item for item in found if item in self.common}
        pool = common or found
        ranked = sorted(
            pool,
            key=lambda item: (self.common.get(item, 100000), abs(len(item) - len(text)), item[:1] != text[:1], item),
        )
        return [self._match_case(word, item) for item in ranked[:limit]]

    def _known(self, edits: set[str]) -> set[str]:
        bank = self.words or set()
        return {item for item in edits if item in bank or item in self.added}

    def _edits(self, word: str) -> set[str]:
        letters = "abcdefghijklmnopqrstuvwxyz'"
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [left + right[1:] for left, right in splits if right]
        transposes = [left + right[1] + right[0] + right[2:] for left, right in splits if len(right) > 1]
        replaces = [left + letter + right[1:] for left, right in splits if right for letter in letters]
        inserts = [left + letter + right for left, right in splits for letter in letters]
        return set(deletes + transposes + replaces + inserts)

    def _match_case(self, source: str, guess: str) -> str:
        if source.isupper() and len(source) > 1:
            return guess.upper()
        if source[:1].isupper():
            return guess[:1].upper() + guess[1:]
        return guess


SPELL = Spell()


def snap_dim(value: int) -> int:
    clamped = max(64, min(1536, int(value)))
    return clamped - (clamped % 8)


def checkpoint_is_sdxl(path: Path) -> bool:
    name = path.name.lower()
    if any(mark in name for mark in ("sdxl", "pony", "illustrious", "_xl", "-xl")):
        return True
    if path.is_dir():
        index = path / "model_index.json"
        try:
            return index.exists() and "XL" in index.read_text(encoding="utf-8")
        except OSError:
            return False
    if path.suffix.lower() != ".safetensors":
        return False
    try:
        from safetensors import safe_open

        with safe_open(str(path), framework="pt", device="cpu") as handle:
            for key in handle.keys():
                if "conditioner.embedders.1" in key or key.startswith("add_embedding"):
                    return True
    except Exception:
        return False
    return False


def clip_warning(text: str) -> str:
    words = [word for word in text.replace(",", " ").split() if word]
    if len(words) <= 60:
        return ""
    return " The prompt is longer than 77 tokens. The extra words are kept."


def _token_chunks(tokenizer, text: str, block: int) -> list[list[int]]:
    old = tokenizer.model_max_length
    tokenizer.model_max_length = 1_000_000
    try:
        ids = tokenizer.encode(text or "", add_special_tokens=False)
    finally:
        tokenizer.model_max_length = old
    bos = tokenizer.bos_token_id if tokenizer.bos_token_id is not None else 49406
    eos = tokenizer.eos_token_id if tokenizer.eos_token_id is not None else 49407
    pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else eos
    room = max(1, int(block) - 2)
    chunks = []
    start = 0
    while True:
        piece = ids[start : start + room]
        chunk = [bos, *piece, eos]
        if len(chunk) < block:
            chunk.extend([pad] * (block - len(chunk)))
        chunks.append(chunk[:block])
        start += room
        if start >= max(len(ids), 1):
            break
    return chunks


def _match_embed_length(left, right):
    import torch

    length = max(int(left.shape[1]), int(right.shape[1]))

    def grow(tensor):
        if int(tensor.shape[1]) == length:
            return tensor
        extra = tensor.new_zeros(tensor.shape[0], length - int(tensor.shape[1]), tensor.shape[2])
        return torch.cat((tensor, extra), dim=1)

    return grow(left), grow(right)


def _vae_state(raw: dict) -> dict:
    state = {}
    for key, value in raw.items():
        name = str(key)
        for prefix in ("first_stage_model.", "model.vae.", "vae."):
            if name.startswith(prefix):
                name = name[len(prefix) :]
        if name.startswith(("encoder.", "decoder.", "quant_conv", "post_quant_conv")):
            state[name] = value
    return state


def _squeeze_conv(value):
    shape = getattr(value, "shape", None)
    ndim = getattr(value, "ndim", None)
    if shape is None or ndim != 4:
        return value
    if int(shape[-1]) == 1 and int(shape[-2]) == 1 and hasattr(value, "reshape"):
        return value.reshape(int(shape[0]), int(shape[1]))
    return value


def _convert_ldm_vae(raw: dict) -> dict:
    state = _vae_state(raw)
    if any("down_blocks" in key or "up_blocks" in key for key in state):
        return state
    if not any(".down.0." in key or ".mid.block_1." in key for key in state):
        return state
    new = {}
    direct = {
        "encoder.norm_out.weight": "encoder.conv_norm_out.weight",
        "encoder.norm_out.bias": "encoder.conv_norm_out.bias",
        "decoder.norm_out.weight": "decoder.conv_norm_out.weight",
        "decoder.norm_out.bias": "decoder.conv_norm_out.bias",
    }
    plain = (
        "encoder.conv_in.weight",
        "encoder.conv_in.bias",
        "encoder.conv_out.weight",
        "encoder.conv_out.bias",
        "decoder.conv_in.weight",
        "decoder.conv_in.bias",
        "decoder.conv_out.weight",
        "decoder.conv_out.bias",
        "quant_conv.weight",
        "quant_conv.bias",
        "post_quant_conv.weight",
        "post_quant_conv.bias",
    )
    for key in plain:
        if key in state:
            new[key] = state[key]
    for src, dst in direct.items():
        if src in state:
            new[dst] = state[src]

    def copy(keys: list[str], old: str, replacement: str, attention: bool) -> None:
        for key in keys:
            if old not in key:
                continue
            renamed = key.replace(old, replacement, 1)
            value = state[key]
            if attention:
                renamed = (
                    renamed.replace("norm.weight", "group_norm.weight")
                    .replace("norm.bias", "group_norm.bias")
                    .replace("q.weight", "to_q.weight")
                    .replace("q.bias", "to_q.bias")
                    .replace("k.weight", "to_k.weight")
                    .replace("k.bias", "to_k.bias")
                    .replace("v.weight", "to_v.weight")
                    .replace("v.bias", "to_v.bias")
                    .replace("proj_out.weight", "to_out.0.weight")
                    .replace("proj_out.bias", "to_out.0.bias")
                )
                if renamed.endswith(("to_q.weight", "to_k.weight", "to_v.weight", "to_out.0.weight")):
                    value = _squeeze_conv(value)
            else:
                renamed = renamed.replace("nin_shortcut", "conv_shortcut")
            new[renamed] = value

    for index in range(8):
        prefix = f"encoder.down.{index}."
        keys = [key for key in state if key.startswith(prefix) and "downsample" not in key and ".attn" not in key]
        if not keys and f"encoder.down.{index}.downsample.conv.weight" not in state:
            continue
        copy(keys, f"encoder.down.{index}.block", f"encoder.down_blocks.{index}.resnets", False)
        weight = f"encoder.down.{index}.downsample.conv.weight"
        if weight in state:
            new[f"encoder.down_blocks.{index}.downsamplers.0.conv.weight"] = state[weight]
            bias = weight.replace("weight", "bias")
            if bias in state:
                new[f"encoder.down_blocks.{index}.downsamplers.0.conv.bias"] = state[bias]
    up_ids = sorted({int(key.split(".")[2]) for key in state if key.startswith("decoder.up.") and key.split(".")[2].isdigit()})
    for index, block_id in enumerate(reversed(up_ids)):
        prefix = f"decoder.up.{block_id}."
        keys = [key for key in state if key.startswith(prefix) and "upsample" not in key]
        copy(keys, f"decoder.up.{block_id}.block", f"decoder.up_blocks.{index}.resnets", False)
        weight = f"decoder.up.{block_id}.upsample.conv.weight"
        if weight in state:
            new[f"decoder.up_blocks.{index}.upsamplers.0.conv.weight"] = state[weight]
            bias = weight.replace("weight", "bias")
            if bias in state:
                new[f"decoder.up_blocks.{index}.upsamplers.0.conv.bias"] = state[bias]
    for side in ("encoder", "decoder"):
        for slot, source in enumerate((1, 2)):
            keys = [key for key in state if key.startswith(f"{side}.mid.block_{source}.")]
            copy(keys, f"{side}.mid.block_{source}", f"{side}.mid_block.resnets.{slot}", False)
        copy(
            [key for key in state if key.startswith(f"{side}.mid.attn_1.")],
            f"{side}.mid.attn_1",
            f"{side}.mid_block.attentions.0",
            True,
        )
    return new or state


def _quiet_rocm_attention() -> None:
    try:
        import torch
    except Exception:
        return
    cuda = getattr(getattr(torch, "backends", None), "cuda", None)
    if cuda is None:
        return
    for name in ("enable_mem_efficient_sdp", "enable_flash_sdp"):
        switch = getattr(cuda, name, None)
        if switch is None:
            continue
        try:
            switch(False)
        except Exception:
            pass


def _vae_scaling(path: Path, sdxl: bool) -> float:
    if path.suffix.lower() != ".safetensors":
        return 0.13025 if sdxl else 0.18215
    import json
    import struct

    meta = {}
    try:
        with path.open("rb") as handle:
            raw = handle.read(8)
            if len(raw) < 8:
                raise OSError
            size = struct.unpack("<Q", raw)[0]
            header = json.loads(handle.read(size))
        meta = header.get("__metadata__") or {}
    except (OSError, json.JSONDecodeError, struct.error, UnicodeDecodeError):
        meta = {}
    for key in ("scaling_factor", "vae_scaling_factor", "ss_vae_scale"):
        if key in meta:
            try:
                return float(meta[key])
            except (TypeError, ValueError):
                pass
    return 0.13025 if sdxl else 0.18215


def _tile_spots(length: int, tile: int, overlap: int) -> list[int]:
    if length <= tile:
        return [0]
    step = max(1, tile - overlap)
    spots = list(range(0, length - tile + 1, step))
    last = length - tile
    if not spots or spots[-1] != last:
        spots.append(last)
    return spots


def _decode_vae_tiles(vae, latents, tile_px: int, overlap_px: int):
    import torch

    tile_px = max(64, int(tile_px) - int(tile_px) % 8)
    overlap_px = max(0, min(int(overlap_px) - int(overlap_px) % 8, tile_px // 2))
    _batch, _channels, height, width = latents.shape
    tile_lat = max(1, tile_px // 8)
    overlap_lat = overlap_px // 8
    if height <= tile_lat and width <= tile_lat:
        return vae.decode(latents, return_dict=False)[0]
    result = torch.zeros(1, 3, height * 8, width * 8, dtype=torch.float32)
    weights = torch.zeros(1, 1, height * 8, width * 8, dtype=torch.float32)
    row_tile = min(tile_lat, height)
    col_tile = min(tile_lat, width)
    rows = _tile_spots(height, row_tile, min(overlap_lat, max(0, row_tile - 1)))
    cols = _tile_spots(width, col_tile, min(overlap_lat, max(0, col_tile - 1)))
    for top in rows:
        for left in cols:
            bottom = min(height, top + tile_lat)
            right = min(width, left + tile_lat)
            piece = vae.decode(latents[:, :, top:bottom, left:right], return_dict=False)[0].float().cpu()
            py, px = top * 8, left * 8
            ph, pw = int(piece.shape[-2]), int(piece.shape[-1])
            mask = torch.ones(1, 1, ph, pw)
            feather = min(overlap_px, ph // 2, pw // 2)
            if feather > 0:
                ramp = torch.linspace(0, 1, feather)
                if top > 0:
                    mask[:, :, :feather, :] *= ramp.view(1, 1, -1, 1)
                if left > 0:
                    mask[:, :, :, :feather] *= ramp.view(1, 1, 1, -1)
                if bottom < height:
                    mask[:, :, -feather:, :] *= ramp.flip(0).view(1, 1, -1, 1)
                if right < width:
                    mask[:, :, :, -feather:] *= ramp.flip(0).view(1, 1, 1, -1)
            result[:, :, py : py + ph, px : px + pw] += piece * mask
            weights[:, :, py : py + ph, px : px + pw] += mask
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    return result / weights.clamp(min=1e-6)


EYE_MODEL_URL = "https://huggingface.co/killjoyelite/anime-eye-yolov8/resolve/main/eye_yolov8n.pt"


def _ensure_eye_model(path: str) -> Path:
    if path and Path(path).is_file():
        return Path(path)
    dest = CONFIG.parent / "eyes" / "eye_yolov8n.pt"
    if dest.is_file() and dest.stat().st_size > 100_000:
        return dest
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(EYE_MODEL_URL, dest)
    if not dest.is_file() or dest.stat().st_size < 100_000:
        raise RuntimeError("Could not download the eye detector. Pick eye_yolov8n.pt yourself.")
    return dest


def _ensure_ultralytics() -> None:
    try:
        import ultralytics  # noqa: F401
        return
    except ImportError:
        pass
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics", "--no-deps"])
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "opencv-python-headless", "pyyaml", "tqdm", "psutil", "ultralytics-thop"]
    )


def _detect_eyes(image, path: Path, conf: float) -> list[tuple[float, float, float, float]]:
    _ensure_ultralytics()
    from ultralytics import YOLO

    found = YOLO(str(path))
    result = found.predict(image, conf=max(0.05, min(0.9, conf)), verbose=False, device="cpu")[0]
    if result.boxes is None or len(result.boxes) == 0:
        return []
    scores = result.boxes.conf.detach().cpu().numpy()
    boxes = result.boxes.xyxy.detach().cpu().numpy()
    order = scores.argsort()[::-1][:8]
    return [tuple(float(value) for value in boxes[index]) for index in order]


def _eye_window(image, box: tuple, pad: float = 0.9):
    width, height = image.size
    x1, y1, x2, y2 = box
    side = max(96.0, max(x2 - x1, y2 - y1) * (1 + pad))
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    left = int(round(cx - side / 2))
    top = int(round(cy - side / 2))
    right = int(round(left + side))
    bottom = int(round(top + side))
    if left < 0:
        right -= left
        left = 0
    if top < 0:
        bottom -= top
        top = 0
    if right > width:
        left = max(0, left - (right - width))
        right = width
    if bottom > height:
        top = max(0, top - (bottom - height))
        bottom = height
    left, top = max(0, left), max(0, top)
    right, bottom = max(left + 8, min(width, right)), max(top + 8, min(height, bottom))
    return image.crop((left, top, right, bottom)), (left, top, right, bottom)


def _fit_guide(image, guide: int):
    from PIL import Image

    width, height = image.size
    scale = guide / max(width, height, 1)
    new_w = max(64, int(width * scale) // 8 * 8)
    new_h = max(64, int(height * scale) // 8 * 8)
    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)


def _pil_tensor(image):
    import numpy as np
    import torch

    array = np.asarray(image.convert("RGB"), dtype="float32")
    return torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0) / 127.5 - 1


def _paste_eye(base, patch, window, feather: int = 12):
    from PIL import Image, ImageDraw, ImageFilter

    left, top, right, bottom = window
    patch = patch.resize((max(1, right - left), max(1, bottom - top)), Image.Resampling.LANCZOS)
    mask = Image.new("L", patch.size, 0)
    inset = max(2, min(feather, patch.width // 4, patch.height // 4))
    ImageDraw.Draw(mask).ellipse((inset, inset, max(inset + 1, patch.width - inset), max(inset + 1, patch.height - inset)), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(1, feather // 2)))
    out = base.copy()
    out.paste(patch, (left, top), mask)
    return out


_CLIP_PREFIXES = (
    "cond_stage_model.transformer.",
    "cond_stage_model.",
    "conditioner.embedders.0.model.",
    "conditioner.embedders.1.model.",
    "conditioner.embedders.0.",
    "conditioner.embedders.1.",
    "text_encoder_2.",
    "text_encoder.",
    "clip_g.",
    "clip_l.",
    "clip.",
)


def clip_key(key: str) -> str:
    name = key
    for prefix in _CLIP_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    if name.startswith("transformer.text_model."):
        name = name[len("transformer.") :]
    if name.startswith("model.text_model."):
        name = name[len("model.") :]
    return name


def _openclip_to_hf(state: dict) -> dict:
    converted = {}
    if "positional_embedding" in state:
        converted["text_model.embeddings.position_embedding.weight"] = state["positional_embedding"]
    if "token_embedding.weight" in state:
        converted["text_model.embeddings.token_embedding.weight"] = state["token_embedding.weight"]
    if "ln_final.weight" in state:
        converted["text_model.final_layer_norm.weight"] = state["ln_final.weight"]
    if "ln_final.bias" in state:
        converted["text_model.final_layer_norm.bias"] = state["ln_final.bias"]
    projection = state.get("text_projection")
    if projection is not None and not hasattr(projection, "shape"):
        projection = None
    if projection is not None and getattr(projection, "ndim", 0) == 2:
        converted["text_projection.weight"] = projection
    layers = set()
    for key in state:
        if not key.startswith("transformer.resblocks."):
            continue
        parts = key.split(".")
        if len(parts) > 2 and parts[2].isdigit():
            layers.add(int(parts[2]))
    for index in sorted(layers):
        source = f"transformer.resblocks.{index}."
        dest = f"text_model.encoder.layers.{index}."
        pairs = (
            ("ln_1.weight", "layer_norm1.weight"),
            ("ln_1.bias", "layer_norm1.bias"),
            ("ln_2.weight", "layer_norm2.weight"),
            ("ln_2.bias", "layer_norm2.bias"),
            ("mlp.c_fc.weight", "mlp.fc1.weight"),
            ("mlp.c_fc.bias", "mlp.fc1.bias"),
            ("mlp.c_proj.weight", "mlp.fc2.weight"),
            ("mlp.c_proj.bias", "mlp.fc2.bias"),
            ("attn.out_proj.weight", "self_attn.out_proj.weight"),
            ("attn.out_proj.bias", "self_attn.out_proj.bias"),
            ("attn.q_proj.weight", "self_attn.q_proj.weight"),
            ("attn.q_proj.bias", "self_attn.q_proj.bias"),
            ("attn.k_proj.weight", "self_attn.k_proj.weight"),
            ("attn.k_proj.bias", "self_attn.k_proj.bias"),
            ("attn.v_proj.weight", "self_attn.v_proj.weight"),
            ("attn.v_proj.bias", "self_attn.v_proj.bias"),
        )
        for src_name, dst_name in pairs:
            if source + src_name in state:
                converted[dest + dst_name] = state[source + src_name]
        packed_weight = state.get(source + "attn.in_proj_weight")
        packed_bias = state.get(source + "attn.in_proj_bias")
        if packed_weight is not None and int(packed_weight.shape[0]) % 3 == 0:
            query, key, value = packed_weight.chunk(3, dim=0)
            converted[dest + "self_attn.q_proj.weight"] = query
            converted[dest + "self_attn.k_proj.weight"] = key
            converted[dest + "self_attn.v_proj.weight"] = value
        if packed_bias is not None and int(packed_bias.shape[0]) % 3 == 0:
            query, key, value = packed_bias.chunk(3, dim=0)
            converted[dest + "self_attn.q_proj.bias"] = query
            converted[dest + "self_attn.k_proj.bias"] = key
            converted[dest + "self_attn.v_proj.bias"] = value
    return converted


def _normalize_clip_state(state: dict) -> dict:
    if any(key.startswith("model.diffusion_model") or key.startswith("unet.") for key in state):
        raise RuntimeError("That file is a full image model, not a CLIP text encoder.")
    cleaned = {clip_key(key): value for key, value in state.items()}
    if "text_model.embeddings.position_embedding.weight" in cleaned or "text_model.embeddings.token_embedding.weight" in cleaned:
        return cleaned
    converted = _openclip_to_hf(cleaned)
    if converted:
        cleaned.update(converted)
    return cleaned


_TRIGGER_KEYS = {
    "modelspec.trigger_phrase",
    "activation_text",
    "trigger_phrase",
    "trigger_word",
    "trigger_words",
    "trained_words",
    "trainedwords",
    "instance_prompt",
    "instance_token",
    "ss_trigger_words",
}
_GENERIC_TAGS = {
    "1girl",
    "1boy",
    "solo",
    "simple background",
    "white background",
    "looking at viewer",
    "smile",
    "long hair",
    "blush",
    "open mouth",
    "breasts",
    "highres",
    "absurdres",
}


def _split_triggers(value) -> list[str]:
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            parts.extend(_split_triggers(item))
        return parts
    if isinstance(value, dict):
        return []
    if not isinstance(value, str):
        return []
    text = value.strip()
    if not text:
        return []
    if text[:1] in "[{":
        try:
            return _split_triggers(json.loads(text))
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in re.split(r"[,;\n|]+", text) if part.strip()]


def _walk_trigger_meta(value, found: list[str], depth: int = 0) -> None:
    if depth > 6:
        return
    if isinstance(value, dict):
        for key, item in value.items():
            name = str(key).lower().replace("-", "_")
            if name in _TRIGGER_KEYS or name.endswith("trigger_phrase") or name.endswith("trigger_words") or name.endswith("trained_words"):
                found.extend(_split_triggers(item))
            if isinstance(item, str) and item[:1] in "[{":
                try:
                    _walk_trigger_meta(json.loads(item), found, depth + 1)
                    continue
                except json.JSONDecodeError:
                    pass
            _walk_trigger_meta(item, found, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _walk_trigger_meta(item, found, depth + 1)


def _frequency_triggers(meta: dict) -> list[str]:
    raw = meta.get("ss_tag_frequency")
    if not raw:
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    found: list[str] = []
    for bucket in data.values():
        if not isinstance(bucket, dict):
            continue
        counts = []
        for tag, count in bucket.items():
            try:
                counts.append((str(tag).strip(), int(count)))
            except (TypeError, ValueError):
                continue
        counts = [(tag, count) for tag, count in counts if tag and count > 0]
        if not counts:
            continue
        top = max(count for _, count in counts)
        picks = [tag for tag, count in counts if count == top]
        specific = [tag for tag in picks if tag.lower() not in _GENERIC_TAGS and " " not in tag]
        plain = [tag for tag in picks if tag.lower() not in _GENERIC_TAGS]
        found.extend((specific or plain or picks)[:8])
    return found


def _read_safetensors_meta(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        import struct

        with path.open("rb") as handle:
            raw = handle.read(8)
            if len(raw) < 8:
                return {}
            header_len = struct.unpack("<Q", raw)[0]
            if header_len <= 2 or header_len > 8_000_000:
                return {}
            header = json.loads(handle.read(header_len))
    except (OSError, ValueError, json.JSONDecodeError, struct.error):
        return {}
    if not isinstance(header, dict):
        return {}
    meta = header.get("__metadata__")
    return meta if isinstance(meta, dict) else {}


def _sidecar_meta(path: Path) -> dict:
    names = [path.with_suffix(".json"), path.with_name(path.name + ".civitai.info"), path.with_name(path.stem + ".civitai.info")]
    merged: dict = {}
    for candidate in names:
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            merged.update(payload)
    return merged


def _merge_trigger_text(*sources: str) -> str:
    found: list[str] = []
    seen: set[str] = set()
    for source in sources:
        for part in _split_triggers(source):
            key = part.lower()
            if key in seen or key.startswith("no trigger") or key.startswith("civitai") or key.startswith("asking"):
                continue
            seen.add(key)
            found.append(part)
    return ", ".join(found[:24])


def _local_triggers(path: Path) -> str:
    meta = _read_safetensors_meta(path)
    sidecar = _sidecar_meta(path)
    if sidecar:
        meta = {**sidecar, **meta}
    found: list[str] = []
    _walk_trigger_meta(meta, found)
    found.extend(_frequency_triggers(meta))
    return _merge_trigger_text(", ".join(found))


def _local_lora_info(path: Path) -> str:
    meta = _read_safetensors_meta(path)
    sidecar = _sidecar_meta(path)
    if sidecar:
        meta = {**sidecar, **meta}
    parts = []
    for key in ("modelspec.title", "ss_output_name", "ss_session_name", "name"):
        value = str(meta.get(key) or "").strip()
        if value:
            parts.append(value)
            break
    for key in ("modelspec.architecture", "ss_base_model_version", "ss_sd_model_name", "baseModel"):
        value = str(meta.get(key) or "").strip()
        if value:
            parts.append(value)
            break
    dim = str(meta.get("ss_network_dim") or meta.get("modelspec.network_dim") or "").strip()
    alpha = str(meta.get("ss_network_alpha") or "").strip()
    if dim:
        parts.append(f"rank {dim}" + (f", alpha {alpha}" if alpha else ""))
    return " · ".join(parts)


def _local_thumb(path: Path) -> str:
    for candidate in (
        path.with_suffix(".preview.png"),
        path.with_name(path.stem + ".preview.png"),
        path.with_suffix(".png"),
        path.with_suffix(".jpg"),
        path.with_suffix(".jpeg"),
        path.with_suffix(".webp"),
    ):
        if candidate.is_file() and candidate != path:
            return str(candidate)
    return ""


def _civitai_blurb(payload: dict) -> str:
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    title = " · ".join(part for part in (str(model.get("name") or ""), str(payload.get("name") or "")) if part)
    base = str(payload.get("baseModel") or "").strip()
    description = re.sub(r"<[^>]+>", " ", str(model.get("description") or payload.get("description") or ""))
    description = " ".join(description.split())[:180]
    line = " · ".join(part for part in (title, base) if part)
    if description:
        line = f"{line}\n{description}" if line else description
    return line


def gpu_device():
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError(
            "ROCm did not see the AMD card. RedGen needs PyTorch 2.12 built for ROCm 7.14, and the card has to be free."
        )
    return torch.device("cuda")


def stamp_name(when: datetime | None = None) -> str:
    moment = when or datetime.now()
    return f"redgen-{moment:%Y%m%d-%H%M%S}.png"


def load_config() -> dict:
    if not CONFIG.exists():
        return {}
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ensure_peft() -> None:
    try:
        import peft  # noqa: F401
    except ImportError:
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "peft==0.13.2"])


class Hold:
    def __init__(self) -> None:
        self.pipe = None
        self.path = ""
        self.sdxl = False
        self.stock = None
        self.clip_sig = None
        self.photo = None
        self.busy = False
        self.proc = None
        self.caption_stop = False
        self.batch_stop = False
        self.token = None
        self.queue = []


def format_elapsed(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rest = divmod(int(round(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {rest}s"
    return f"{minutes}m {rest}s"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP + " build " + BUILD)
        self.geometry("1280x860")
        self.minsize(980, 700)
        self.configure(bg=BG)
        self.hold = Hold()
        self._loras: list[tuple[tk.StringVar, tk.DoubleVar, ttk.Frame]] = []
        self._models: list[str] = []
        self._prompts: list[dict] = []
        self._scroll_canvases: list = []
        self._stop_train = threading.Event()
        self._build()
        self._restore()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Card.TLabel", background=SURFACE, foreground=FG)
        style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED)
        style.configure("TButton", background="#1c0d10", foreground=FG, bordercolor=BORDER, padding=(14, 8), focuscolor="#1c0d10")
        style.map("TButton", background=[("pressed", PRIMARY), ("active", PRIMARY)], foreground=[("pressed", ACCENT_INK), ("active", ACCENT_INK)])
        style.configure("Primary.TButton", background=PRIMARY, foreground=ACCENT_INK, bordercolor=PRIMARY, padding=(16, 8), focuscolor=PRIMARY)
        style.map("Primary.TButton", background=[("active", PRIMARY)], foreground=[("active", ACCENT_INK)])

        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
        try:
            style.layout("TNotebook.Tab", [])
        except tk.TclError:
            pass
        style.configure(
            "Red.Horizontal.TProgressbar",
            troughcolor=BG,
            background=PRIMARY,
            bordercolor=BG,
            lightcolor=PRIMARY,
            darkcolor=PRIMARY,
        )

        outer = ttk.Frame(self, style="TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        title = tk.Label(outer, text="RedWright", bg=BG, fg=FG, font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, sticky="w")
        sub = tk.Label(
            outer,
            text="RedGen pictures  ·  Cardwright cards  ·  build " + BUILD,
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        sub.grid(row=0, column=0, sticky="e")

        self.pill_bar = tk.Frame(outer, bg=BG)
        self.pill_bar.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        book = ttk.Notebook(outer)
        book.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        generate = ttk.Frame(book, style="TFrame")
        anima = ttk.Frame(book, style="TFrame")
        captions = ttk.Frame(book, style="TFrame")
        train = ttk.Frame(book, style="TFrame")
        anima_train = ttk.Frame(book, style="TFrame")
        library = ttk.Frame(book, style="TFrame")
        vn = ttk.Frame(book, style="TFrame")
        redvn_page = ttk.Frame(book, style="TFrame")
        book.add(generate, text="Generate")
        book.add(anima, text="Anima")
        book.add(library, text="Library")
        book.add(captions, text="Captions")
        book.add(train, text="Train")
        book.add(anima_train, text="Anima train")
        book.add(vn, text="Vangard")
        book.add(redvn_page, text="RedVN")
        lore_page = ttk.Frame(book, style="TFrame")
        preset_page = ttk.Frame(book, style="TFrame")
        book.add(lore_page, text="Lorebooks")
        book.add(preset_page, text="Presets")
        import cardwright

        cardwright.attach(self, book)
        self._build_theme(book)
        self.book = book
        self.train_tab = train
        generate.columnconfigure(0, weight=0)
        generate.columnconfigure(1, weight=1)
        generate.rowconfigure(0, weight=1)

        left_host = ttk.Frame(generate, style="TFrame")
        left_host.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left = self._make_scroller(left_host, bg=SURFACE, width=400, style="Card.TFrame")
        right = ttk.Frame(generate, style="TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        settings_host = ttk.Frame(right, style="TFrame")
        settings_host.grid(row=0, column=0, sticky="nsew")
        settings = self._make_scroller(settings_host, bg=BG)
        self.bind_all("<MouseWheel>", self._wheel)
        self.bind_all("<Button-4>", self._wheel)
        self.bind_all("<Button-5>", self._wheel)
        self.bind_class("Text", "<Button-3>", self._text_popup)
        self.bind_class("Text", "<<Modified>>", self._spell_modified)
        self.bind_class("Entry", "<Button-3>", self._entry_popup)
        self.bind_class("Listbox", "<Button-3>", self._list_popup)
        self._spell_ready = False
        threading.Thread(target=self._warm_spell, daemon=True).start()
        self.after(200, self._spell_poll)

        ttk.Label(left, text="Prompt", style="Card.TLabel").pack(anchor="w")
        self.prompt = tk.Text(
            left, width=42, height=8, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word"
        )
        self.prompt.pack(fill="x", pady=(4, 0))
        self.prompt_count = tk.Label(left, text="0 words", bg=SURFACE, fg=MUTED, font=("Segoe UI", 9))
        self.prompt_count.pack(anchor="w", pady=(2, 4))
        self._watch_words(self.prompt, self.prompt_count)
        ttk.Label(left, text="Negative prompt", style="Card.TLabel").pack(anchor="w")
        self.negative = tk.Text(
            left, width=42, height=4, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word"
        )
        self.negative.pack(fill="x", pady=(4, 0))
        self.negative_count = tk.Label(left, text="0 words", bg=SURFACE, fg=MUTED, font=("Segoe UI", 9))
        self.negative_count.pack(anchor="w", pady=(2, 4))
        self._watch_words(self.negative, self.negative_count)
        ttk.Label(
            left,
            text="Prompts longer than 77 tokens are kept. A Long CLIP file reads them in one pass.",
            style="Muted.TLabel",
            wraplength=320,
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(left, text="Save prompt", style="Card.TLabel").pack(anchor="w")
        name_row = ttk.Frame(left, style="Card.TFrame")
        name_row.pack(fill="x", pady=4)
        self.prompt_name = tk.StringVar()
        tk.Entry(name_row, textvariable=self.prompt_name, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(name_row, text="Save", command=self._save_prompt).pack(side="left", padx=(8, 0))

        self.prompt_list = tk.Listbox(
            left, height=6, bg=INSET, fg=FG, selectbackground=PRIMARY, relief="flat", highlightthickness=0
        )
        self.prompt_list.pack(fill="x", pady=4)
        self.prompt_list.bind("<<ListboxSelect>>", self._load_prompt)
        ttk.Button(left, text="Delete saved prompt", command=self._delete_prompt).pack(anchor="w", pady=(0, 8))

        grid = ttk.Frame(left, style="Card.TFrame")
        grid.pack(fill="x")
        self.steps = tk.IntVar(value=20)
        self.cfg = tk.DoubleVar(value=7)
        self.width = tk.IntVar(value=512)
        self.height = tk.IntVar(value=512)
        self.batch = tk.IntVar(value=1)
        self.seed = tk.StringVar()
        for col, (label, var) in enumerate(
            (("Steps", self.steps), ("CFG", self.cfg), ("Width", self.width), ("Height", self.height))
        ):
            box = ttk.Frame(grid, style="Card.TFrame")
            box.grid(row=0, column=col, padx=4, sticky="ew")
            ttk.Label(box, text=label, style="Muted.TLabel").pack(anchor="w")
            tk.Entry(box, textvariable=var, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(ipady=4)
        batch_box = ttk.Frame(grid, style="Card.TFrame")
        batch_box.grid(row=1, column=0, columnspan=2, padx=4, pady=(8, 0), sticky="ew")
        ttk.Label(batch_box, text="Batch count", style="Muted.TLabel").pack(anchor="w")
        tk.Entry(batch_box, textvariable=self.batch, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            anchor="w", ipady=4
        )
        seed_box = ttk.Frame(left, style="Card.TFrame")
        seed_box.pack(fill="x", pady=8)
        ttk.Label(seed_box, text="Seed, blank is random", style="Muted.TLabel").pack(anchor="w")
        tk.Entry(seed_box, textvariable=self.seed, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            fill="x", ipady=4
        )

        row = ttk.Frame(left, style="Card.TFrame")
        row.pack(fill="x", pady=(8, 4))
        ttk.Button(row, text="Generate", style="Primary.TButton", command=self._generate).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Stop", command=self._stop_generation).pack(side="left", padx=(8, 0))
        self.queue_count = tk.Label(row, text="Queue 0", bg=SURFACE, fg=FG, font=("Segoe UI", 10, "bold"))
        self.queue_count.pack(side="left", padx=(8, 0))
        self.status = tk.Label(left, text="Idle", bg=SURFACE, fg=MUTED, wraplength=320, justify="left")
        self.status.pack(anchor="w")

        model_card = ttk.Frame(settings, style="Card.TFrame", padding=12)
        model_card.pack(fill="x", pady=(0, 8))
        ttk.Label(model_card, text="Model", style="Card.TLabel").pack(anchor="w")
        model_buttons = ttk.Frame(model_card, style="Card.TFrame")
        model_buttons.pack(fill="x", pady=4)
        ttk.Button(model_buttons, text="Add file", command=self._add_model_file).pack(side="left")
        ttk.Button(model_buttons, text="Scan folder", command=self._scan_folder).pack(side="left", padx=8)
        self.model_box = ttk.Combobox(model_card, state="readonly")
        self.model_box.pack(fill="x", pady=4)
        model_actions = ttk.Frame(model_card, style="Card.TFrame")
        model_actions.pack(fill="x")
        ttk.Button(model_actions, text="Remove selected model", command=self._remove_model).pack(side="left")
        ttk.Button(model_actions, text="Unload model", command=self._unload_model).pack(side="left", padx=(8, 0))
        self.keep_loaded = tk.BooleanVar(value=True)
        self._keep_buttons = []
        keep_model = ttk.Button(model_actions, text=self._keep_label(), command=self._toggle_keep_loaded)
        keep_model.pack(side="left", padx=(8, 0))
        self._keep_buttons.append(keep_model)

        clip_card = ttk.Frame(settings, style="Card.TFrame", padding=12)
        clip_card.pack(fill="x", pady=(0, 8))
        ttk.Label(clip_card, text="CLIP", style="Card.TLabel").pack(anchor="w")
        ttk.Label(
            clip_card,
            text="Optional text encoder. Blank uses the one packed in the model.",
            style="Muted.TLabel",
            wraplength=520,
        ).pack(anchor="w", pady=(2, 4))
        self.clip = tk.StringVar()
        self._clip_row(clip_card, self.clip, "CLIP", "CLIP", "clip")
        ttk.Label(clip_card, text="CLIP-G, SDXL only", style="Muted.TLabel").pack(anchor="w", pady=(8, 2))
        self.clip_g = tk.StringVar()
        self._clip_row(clip_card, self.clip_g, "CLIP-G", "CLIP", "clip")
        ttk.Label(clip_card, text="VAE", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(
            clip_card,
            text="Optional decoder. Blank uses the VAE packed in the model.",
            style="Muted.TLabel",
            wraplength=520,
        ).pack(anchor="w", pady=(2, 4))
        self.vae_path = tk.StringVar()
        self._clip_row(clip_card, self.vae_path, "VAE", "VAE", "vae")
        tile_row = ttk.Frame(clip_card, style="Card.TFrame")
        tile_row.pack(fill="x", pady=(8, 0))
        self.vae_tile = tk.BooleanVar(value=True)
        tk.Checkbutton(
            tile_row,
            text="Tile the VAE",
            variable=self.vae_tile,
            bg=SURFACE,
            fg=FG,
            selectcolor=BG,
            activebackground=SURFACE,
            activeforeground=FG,
        ).pack(side="left")
        ttk.Label(tile_row, text="Tile", style="Muted.TLabel").pack(side="left", padx=(12, 4))
        self.vae_tile_size = tk.IntVar(value=512)
        tk.Entry(tile_row, textvariable=self.vae_tile_size, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", ipady=4
        )
        ttk.Label(tile_row, text="Overlap", style="Muted.TLabel").pack(side="left", padx=(12, 4))
        self.vae_tile_overlap = tk.IntVar(value=64)
        tk.Entry(
            tile_row, textvariable=self.vae_tile_overlap, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat"
        ).pack(side="left", ipady=4)
        ttk.Label(
            clip_card,
            text="Tile and overlap are in pixels. A smaller tile uses less VRAM.",
            style="Muted.TLabel",
            wraplength=520,
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(clip_card, text="Eyes", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(
            clip_card,
            text="Finds anime eyes, then redraws only those spots. Leave the file blank and the small detector is downloaded once.",
            style="Muted.TLabel",
            wraplength=520,
        ).pack(anchor="w", pady=(2, 4))
        self.eye_fix = tk.BooleanVar(value=False)
        tk.Checkbutton(
            clip_card,
            text="Redraw eyes",
            variable=self.eye_fix,
            bg=SURFACE,
            fg=FG,
            selectcolor=BG,
            activebackground=SURFACE,
            activeforeground=FG,
        ).pack(anchor="w")
        self.eye_model = tk.StringVar()
        self._clip_row(clip_card, self.eye_model, "Eye detector", "Eye detector")
        eye_row = ttk.Frame(clip_card, style="Card.TFrame")
        eye_row.pack(fill="x", pady=(4, 0))
        ttk.Label(eye_row, text="Denoise", style="Muted.TLabel").pack(side="left")
        self.eye_denoise = tk.DoubleVar(value=0.55)
        tk.Entry(eye_row, textvariable=self.eye_denoise, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", padx=(4, 12), ipady=4
        )
        ttk.Label(eye_row, text="Confidence", style="Muted.TLabel").pack(side="left")
        self.eye_conf = tk.DoubleVar(value=0.3)
        tk.Entry(eye_row, textvariable=self.eye_conf, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", padx=(4, 0), ipady=4
        )
        ttk.Label(clip_card, text="Eye prompt", style="Muted.TLabel").pack(anchor="w", pady=(6, 2))
        self.eye_prompt = tk.StringVar(value="detailed eyes, sharp pupils, clear iris")
        tk.Entry(clip_card, textvariable=self.eye_prompt, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", ipady=4)

        lora_card = ttk.Frame(settings, style="Card.TFrame", padding=12)
        lora_card.pack(fill="x", pady=(0, 8))
        head = ttk.Frame(lora_card, style="Card.TFrame")
        head.pack(fill="x")
        ttk.Label(head, text="LoRAs", style="Card.TLabel").pack(side="left")
        ttk.Button(head, text="Add LoRA", command=self._add_lora).pack(side="right")
        self.lora_host = ttk.Frame(lora_card, style="Card.TFrame")
        self.lora_host.pack(fill="x", pady=4)

        image_card = ttk.Frame(settings, style="Card.TFrame", padding=12)
        image_card.pack(fill="x", pady=(0, 8))
        ttk.Label(image_card, text="Image to image", style="Card.TLabel").pack(anchor="w")
        ttk.Label(
            image_card,
            text="Pick a source picture and it is redrawn. Denoise is how much of it changes. CLIP Vision or JoyCaption can read it into the prompt first.",
            style="Muted.TLabel",
            wraplength=520,
        ).pack(anchor="w", pady=(2, 4))
        self.init_image = tk.StringVar()
        self.init_denoise = tk.DoubleVar(value=0.55)
        self.init_reader = tk.StringVar(value="off")
        self.init_read = tk.BooleanVar(value=True)
        self.clip_vision = tk.StringVar()
        self.clip_vision_text = tk.StringVar()
        self.joy_model = tk.StringVar()
        self.joy_mmproj = tk.StringVar()
        init_row = ttk.Frame(image_card, style="Card.TFrame")
        init_row.pack(fill="x")
        tk.Entry(init_row, textvariable=self.init_image, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=4
        )
        ttk.Button(init_row, text="Browse", command=self._pick_init_image).pack(side="left", padx=(8, 0))
        ttk.Button(init_row, text="Clear", command=self._clear_init_image).pack(side="left", padx=(8, 0))
        self.init_preview = tk.Label(image_card, text="", bg=BG)
        self.init_preview.pack(anchor="w", pady=(6, 0))
        denoise_row = ttk.Frame(image_card, style="Card.TFrame")
        denoise_row.pack(fill="x", pady=(6, 0))
        ttk.Label(denoise_row, text="Denoise", style="Muted.TLabel").pack(side="left")
        tk.Entry(denoise_row, textvariable=self.init_denoise, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", padx=(4, 0), ipady=4
        )
        ttk.Label(denoise_row, text="0.30 keeps the picture. 0.80 invents more.", style="Muted.TLabel").pack(side="left", padx=(8, 0))
        reader_row = ttk.Frame(image_card, style="Card.TFrame")
        reader_row.pack(fill="x", pady=(6, 0))
        for value, label in (("off", "Don't read"), ("clip", "CLIP Vision"), ("joy", "JoyCaption")):
            tk.Radiobutton(
                reader_row,
                text=label,
                value=value,
                variable=self.init_reader,
                bg=SURFACE,
                fg=FG,
                selectcolor=BG,
                activebackground=SURFACE,
                activeforeground=FG,
            ).pack(side="left", padx=(0, 12))
        tk.Checkbutton(
            image_card,
            text="Read it into the prompt before generating",
            variable=self.init_read,
            bg=SURFACE,
            fg=FG,
            selectcolor=BG,
            activebackground=SURFACE,
            activeforeground=FG,
        ).pack(anchor="w", pady=(4, 0))
        ttk.Button(image_card, text="Read into prompt", command=self._read_init_image).pack(anchor="w", pady=(6, 0))
        ttk.Label(image_card, text="CLIP Vision file", style="Muted.TLabel").pack(anchor="w", pady=(8, 0))
        self._file_line(image_card, self.clip_vision, "CLIP Vision", "*.safetensors;*.bin;*.pt")
        ttk.Label(image_card, text="Matching CLIP text file", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        self._file_line(image_card, self.clip_vision_text, "CLIP text", "*.safetensors;*.bin;*.pt")
        ttk.Label(image_card, text="JoyCaption Beta One GGUF", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        self._file_line(image_card, self.joy_model, "JoyCaption GGUF", "*.gguf")
        ttk.Label(image_card, text="JoyCaption mmproj", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        self._file_line(image_card, self.joy_mmproj, "JoyCaption mmproj", "*.gguf")

        out_card = ttk.Frame(settings, style="Card.TFrame", padding=12)
        out_card.pack(fill="x", pady=(0, 8))
        ttk.Label(out_card, text="Image save location", style="Card.TLabel").pack(anchor="w")
        out_row = ttk.Frame(out_card, style="Card.TFrame")
        out_row.pack(fill="x", pady=4)
        pictures = Path.home() / "Pictures" / "RedGen"
        self.output = tk.StringVar(value=str(pictures))
        tk.Entry(out_row, textvariable=self.output, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(out_row, text="Browse", command=self._pick_output).pack(side="left", padx=(8, 0))

        view = ttk.Frame(right, style="Card.TFrame", padding=12)
        view.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        self.view_caption = tk.Label(view, text="No picture yet", bg=SURFACE, fg=FG, font=("Segoe UI", 10))
        self.view_caption.pack(anchor="w")
        self.progress = ttk.Progressbar(view, style="Red.Horizontal.TProgressbar", maximum=100)
        self.progress.pack(fill="x", pady=(6, 0))
        self.viewport = tk.Canvas(view, bg=BG, highlightthickness=0, height=320, cursor="hand2")
        self.viewport.pack(fill="both", expand=True, pady=(6, 0))
        self.viewport.bind("<Button-1>", self._click_preview)
        self.viewport.bind("<Button-3>", self._picture_popup)

        self.log = tk.Text(right, height=5, bg=INSET, fg=FG, relief="flat", wrap="word", state="disabled")
        self.log.grid(row=2, column=0, sticky="ew")
        self._build_library(library)
        self._build_anima(anima)
        self._build_captions(captions)
        self._build_train(train)
        self._build_anima_train(anima_train)
        self._build_vangard(vn)
        import redvn

        redvn.attach(self, redvn_page)
        redvn.attach_lorebooks(self, lore_page)
        redvn.attach_presets(self, preset_page)
        self._index_paint(self)
        self._install_menu()
        self._install_pills()
        book.bind("<<NotebookTabChanged>>", lambda _event: self._paint_pills())

    def _index_paint(self, widget) -> None:
        for child in widget.winfo_children():
            self._index_paint(child)
        try:
            keys = set(widget.keys())
        except tk.TclError:
            return
        pairs = (
            ("bg", "_role_bg"),
            ("fg", "_role_fg"),
            ("insertbackground", "_role_insert"),
            ("selectbackground", "_role_select"),
            ("selectcolor", "_role_select"),
            ("activebackground", "_role_active"),
            ("activeforeground", "_role_active_fg"),
        )
        for option, attr in pairs:
            if option not in keys or hasattr(widget, attr):
                continue
            try:
                role = _THEME_ROLES.get(str(widget.cget(option)).lower())
            except tk.TclError:
                continue
            if role:
                setattr(widget, attr, role)

    def _paint(self, widget, theme: dict) -> None:
        for child in widget.winfo_children():
            self._paint(child, theme)
        options = {}
        for attr, option in (
            ("_role_bg", "bg"),
            ("_role_fg", "fg"),
            ("_role_insert", "insertbackground"),
            ("_role_select", "selectbackground"),
            ("_role_active", "activebackground"),
            ("_role_active_fg", "activeforeground"),
        ):
            role = getattr(widget, attr, None)
            if role and role in theme:
                options[option] = theme[role]
        for option, value in options.items():
            try:
                widget.configure(**{option: value})
            except tk.TclError:
                pass
        role = getattr(widget, "_role_select", None)
        if role and role in theme:
            for option in ("selectbackground", "selectcolor"):
                try:
                    widget.configure(**{option: theme[role]})
                except tk.TclError:
                    pass
        if widget.winfo_class() in {"Entry", "Text", "Listbox", "Spinbox"}:
            try:
                widget.configure(relief="flat", highlightthickness=1, highlightbackground=theme["line"], highlightcolor=theme["accent"])
            except tk.TclError:
                pass
        if widget.winfo_class() in {"Label", "Text", "Entry", "Listbox", "Button", "Checkbutton", "Spinbox"}:
            try:
                import tkinter.font as tkfont

                current = tkfont.Font(font=widget.cget("font")).actual()
                size = int(current.get("size") or theme["size"])
                if size < 14:
                    size = int(theme["size"])
                widget.configure(font=(theme["font"], size, "bold" if current.get("weight") == "bold" else "normal"))
            except (tk.TclError, ValueError):
                pass

    def _apply_theme(self, theme: dict, *, save: bool = True) -> None:
        merged = {**DEFAULT_THEME, **{key: value for key, value in theme.items() if value not in ("", None)}}
        try:
            merged["size"] = max(8, min(18, int(merged["size"])))
        except (TypeError, ValueError):
            merged["size"] = 10
        self._theme = merged
        LIVE_THEME.clear()
        LIVE_THEME.update(merged)
        style = ttk.Style(self)
        style.configure("TFrame", background=merged["bg"])
        style.configure("Card.TFrame", background=merged["surface"])
        style.configure("TLabel", background=merged["bg"], foreground=merged["fg"], font=(merged["font"], merged["size"]))
        style.configure("Card.TLabel", background=merged["surface"], foreground=merged["fg"], font=(merged["font"], merged["size"]))
        style.configure("Muted.TLabel", background=merged["surface"], foreground=merged["muted"], font=(merged["font"], merged["size"]))
        style.configure("TNotebook", background=merged["bg"], borderwidth=0, tabmargins=0)
        try:
            style.layout("TNotebook.Tab", [])
        except tk.TclError:
            pass
        style.configure(
            "TCombobox",
            fieldbackground=merged["inset"],
            background=merged["surface"],
            foreground=merged["fg"],
            arrowcolor=merged["fg"],
            bordercolor=merged["line"],
            lightcolor=merged["inset"],
            darkcolor=merged["inset"],
            padding=6,
        )
        style.map("TCombobox", fieldbackground=[("readonly", merged["inset"])], foreground=[("readonly", merged["fg"])])
        style.configure(
            "Red.Horizontal.TProgressbar",
            troughcolor=merged["inset"],
            background=merged["accent"],
            bordercolor=merged["inset"],
            lightcolor=merged["accent"],
            darkcolor=merged["accent"],
        )
        self.configure(bg=merged["bg"])
        self._paint(self, merged)
        button = merged.get("button") or "#1c0d10"
        button_text = merged.get("button_text") or merged["fg"]
        style.configure(
            "TButton",
            background=button,
            foreground=button_text,
            bordercolor=merged["line"],
            lightcolor=button,
            darkcolor=button,
            padding=(14, 8),
            font=(merged["font"], merged["size"]),
            focuscolor=button,
        )
        style.map(
            "TButton",
            background=[("pressed", merged["accent"]), ("active", merged["accent"])],
            foreground=[("pressed", merged["accent_ink"]), ("active", merged["accent_ink"]), ("disabled", merged["muted"])],
        )
        style.configure(
            "Primary.TButton",
            background=merged["accent"],
            foreground=merged["accent_ink"],
            bordercolor=merged["accent"],
            lightcolor=merged["accent"],
            darkcolor=merged["accent"],
            padding=(16, 8),
            font=(merged["font"], merged["size"]),
            focuscolor=merged["accent"],
        )
        style.map(
            "Primary.TButton",
            background=[("pressed", merged["accent"]), ("active", merged["accent"])],
            foreground=[("disabled", merged["muted"])],
        )
        if getattr(self, "pill_bar", None) is not None:
            self.pill_bar.configure(bg=merged["bg"])
            self._paint_pills()
        if save:
            data = load_config()
            data["theme"] = merged
            save_config(data)

    def _install_bubbles(self, style, accent: str, surface: str) -> None:
        from PIL import Image, ImageDraw, ImageTk

        def blob(color: str):
            image = Image.new("RGBA", (72, 44), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((1, 1, 70, 42), radius=20, fill=color)
            return ImageTk.PhotoImage(image)

        normal = blob(surface)
        hot = blob(accent)
        self._bubble_photos = (normal, hot)
        if getattr(self, "_bubble_ready", False):
            return
        layout = [
            (
                "Button.padding",
                {
                    "sticky": "nsew",
                    "children": [("Button.label", {"sticky": "nsew"})],
                },
            )
        ]
        try:
            style.element_create("Bubble.normal", "image", normal, ("pressed", hot), ("active", hot), border=(20, 16, 20, 16), sticky="nsew")
            style.element_create("Bubble.primary", "image", hot, ("pressed", normal), ("active", normal), border=(20, 16, 20, 16), sticky="nsew")
            style.layout("TButton", [("Bubble.normal", {"sticky": "nsew", "children": layout})])
            style.layout("Primary.TButton", [("Bubble.primary", {"sticky": "nsew", "children": layout})])
            style.configure("TButton", foreground=FG, anchor="center")
            style.configure("Primary.TButton", foreground=ACCENT_INK, anchor="center")
            self._bubble_ready = True
        except tk.TclError:
            return

    def _install_menu(self) -> None:
        menu = tk.Menu(self, tearoff=0, bg=SURFACE, fg=FG, activebackground=PRIMARY, activeforeground=ACCENT_INK, relief="flat", bd=0)
        file_menu = tk.Menu(menu, tearoff=0, bg=SURFACE, fg=FG, activebackground=PRIMARY, activeforeground=ACCENT_INK)
        file_menu.add_command(label="Settings", command=self._open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_close)
        menu.add_cascade(label="File", menu=file_menu)

        go = tk.Menu(menu, tearoff=0, bg=SURFACE, fg=FG, activebackground=PRIMARY, activeforeground=ACCENT_INK)
        names = []
        if getattr(self, "book", None) is not None:
            names = [self.book.tab(index, "text") for index in range(self.book.index("end"))]
        if not names:
            names = ["Generate", "Anima", "Library", "Captions", "Train", "Anima train", "Cards", "NovelAI", "Novel library", "Vangard", "Theme"]
        for name in names:
            go.add_command(label=name, command=lambda tab=name: self._show_tab(tab))
        menu.add_cascade(label="Go", menu=go)

        anima = tk.Menu(menu, tearoff=0, bg=SURFACE, fg=FG, activebackground=PRIMARY, activeforeground=ACCENT_INK)
        anima.add_command(label="Generate", command=lambda: self._show_tab("Anima"))
        anima.add_command(label="Unload model", command=self._unload_model)
        anima.add_command(label="Refresh model list", command=self._refresh_anima_picks)
        menu.add_cascade(label="Anima", menu=anima)

        library = tk.Menu(menu, tearoff=0, bg=SURFACE, fg=FG, activebackground=PRIMARY, activeforeground=ACCENT_INK)
        library.add_command(label="Open library", command=lambda: self._show_tab("Library"))
        library.add_command(label="Refresh", command=self._refresh_library)
        menu.add_cascade(label="Library", menu=library)

        menu.add_command(label="Settings", command=self._open_settings)
        self.config(menu=menu)

    def _show_tab(self, name: str) -> None:
        book = getattr(self, "book", None)
        if book is None:
            return
        for index in range(book.index("end")):
            if book.tab(index, "text") == name:
                book.select(index)
                self._paint_pills()
                return

    def _pill_image(self, text: str, selected: bool):
        from PIL import Image, ImageDraw, ImageFont, ImageTk

        theme = getattr(self, "_theme", None) or DEFAULT_THEME
        fill = theme.get("accent", PRIMARY) if selected else theme.get("button", SURFACE)
        ink = theme.get("accent_ink", ACCENT_INK) if selected else theme.get("button_text", FG)
        shape = str(theme.get("button_shape") or "Pill")
        try:
            font = ImageFont.truetype("segoeui.ttf", 15)
        except OSError:
            font = ImageFont.load_default()
        probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
        left, top, right, bottom = probe.textbbox((0, 0), text, font=font)
        text_w = right - left
        text_h = bottom - top
        width = text_w + 36
        height = max(34, text_h + 16)
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=height // 2 if shape == "Pill" else 10 if shape == "Rounded" else 2, fill=fill)
        draw.text(((width - text_w) / 2, (height - text_h) / 2 - top), text, font=font, fill=ink)
        return ImageTk.PhotoImage(image)

    def _install_pills(self) -> None:
        self._paint_pills()

    def _paint_pills(self) -> None:
        bar = getattr(self, "pill_bar", None)
        book = getattr(self, "book", None)
        if bar is None or book is None:
            return
        theme = getattr(self, "_theme", None) or DEFAULT_THEME
        for child in bar.winfo_children():
            child.destroy()
        photos = []
        try:
            current = str(book.select())
        except tk.TclError:
            current = ""
        for index in range(book.index("end")):
            name = book.tab(index, "text")
            tab_id = str(book.tabs()[index])
            photo = self._pill_image(name, tab_id == current)
            photos.append(photo)
            label = tk.Label(bar, image=photo, bg=str(theme.get("bg", BG)), bd=0, cursor="hand2")
            label.pack(side="left", padx=3, pady=2)
            label.bind("<Button-1>", lambda _event, tab=name: self._show_tab(tab))
        self._pill_photos = photos

    def _roots_map(self) -> dict:
        roots = getattr(self, "_roots", None)
        if not isinstance(roots, dict):
            roots = {}
            self._roots = roots
        return roots

    def _dialog_dir(self, kind: str, current: str = "") -> str:
        if current and Path(current).exists():
            path = Path(current)
            return str(path.parent if path.is_file() else path)
        saved = self._roots_map().get(kind, "")
        if isinstance(saved, str) and Path(saved).is_dir():
            return saved
        return ""

    def _remember_root(self, kind: str, folder: str) -> None:
        if not kind or not folder or not Path(folder).is_dir():
            return
        self._roots_map()[kind] = folder
        variables = getattr(self, "_settings_vars", None)
        if isinstance(variables, dict) and kind in variables:
            variables[kind].set(folder)

    def _open_settings(self) -> None:
        existing = getattr(self, "_settings_window", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return
        window = tk.Toplevel(self)
        self._settings_window = window
        window.title("Settings")
        window.configure(bg=BG)
        window.geometry("760x560")
        window.minsize(640, 420)
        tk.Label(window, text="Folders", bg=BG, fg=FG, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 0))
        tk.Label(
            window,
            text="File dialogs open in these folders. Pick each one once, then models, LoRAs, VAEs, and CLIP files are a short list instead of a long walk.",
            bg=BG,
            fg=MUTED,
            wraplength=700,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(4, 10))
        host = ttk.Frame(window, style="TFrame")
        host.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        form = self._make_scroller(host, bg=SURFACE, style="Card.TFrame")
        fields = (
            ("models", "Stable Diffusion models"),
            ("anima_models", "Anima models"),
            ("loras", "SDXL LoRAs"),
            ("anima_loras", "Anima LoRAs"),
            ("vae", "VAE files"),
            ("clip", "CLIP and text encoders"),
            ("pictures", "Picture library"),
            ("training", "Training pictures"),
        )
        variables = {}
        roots = self._roots_map()
        for key, label in fields:
            ttk.Label(form, text=label, style="Card.TLabel").pack(anchor="w", pady=(10, 2))
            row = ttk.Frame(form, style="Card.TFrame")
            row.pack(fill="x")
            variable = tk.StringVar(value=str(roots.get(key) or ""))
            variables[key] = variable
            tk.Entry(row, textvariable=variable, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, ipady=6)

            def browse(item=key, var=variable) -> None:
                options = {"title": "Choose folder"}
                start = var.get().strip()
                if start and Path(start).is_dir():
                    options["initialdir"] = start
                picked = filedialog.askdirectory(**options)
                if picked:
                    var.set(picked)
                    self._remember_root(item, picked)

            ttk.Button(row, text="Browse", command=browse).pack(side="left", padx=(8, 0))
        self._settings_vars = variables

        def save() -> None:
            for key, variable in variables.items():
                folder = variable.get().strip()
                if folder and Path(folder).is_dir():
                    self._roots_map()[key] = folder
                elif not folder:
                    self._roots_map().pop(key, None)
            pictures = self._roots_map().get("pictures", "")
            if pictures and hasattr(self, "library_folder") and not self.library_folder.get().strip():
                self.library_folder.set(pictures)
            self._refresh_anima_picks()
            self._say("Folder settings saved.")
            if hasattr(self, "_anima_say"):
                self._anima_say("Folder settings saved. The Anima lists use those folders.")
            window.destroy()

        bar = ttk.Frame(window, style="TFrame")
        bar.pack(fill="x", padx=16, pady=(0, 14))
        ttk.Button(bar, text="Save", style="Primary.TButton", command=save).pack(side="right")
        ttk.Button(bar, text="Close", command=window.destroy).pack(side="right", padx=(0, 8))

    def _build_theme(self, book: ttk.Notebook) -> None:
        from tkinter import colorchooser

        page = ttk.Frame(book, style="TFrame")
        book.add(page, text="Theme")
        host = ttk.Frame(page, style="TFrame")
        host.pack(fill="both", expand=True)
        form = self._make_scroller(host, bg=SURFACE, style="Card.TFrame")
        labels = (
            ("bg", "Background"),
            ("surface", "Panels"),
            ("inset", "Fields"),
            ("fg", "Text"),
            ("muted", "Muted text"),
            ("line", "Lines"),
            ("accent", "Accent"),
            ("accent_ink", "Text on accent"),
            ("button", "Button color"),
            ("button_text", "Button text"),
            ("paper", "Character sheet"),
            ("ink", "Sheet text"),
            ("gold", "Sheet rule"),
        )
        vars: dict[str, tk.StringVar] = {}
        for key, _title in labels:
            vars[key] = tk.StringVar(value=DEFAULT_THEME[key])
        font_var = tk.StringVar(value=DEFAULT_THEME["font"])
        size_var = tk.IntVar(value=int(DEFAULT_THEME["size"]))
        shape_var = tk.StringVar(value=str(DEFAULT_THEME["button_shape"]))
        self._theme_vars = vars
        self._theme_font = font_var
        self._theme_size = size_var
        self._theme_shape = shape_var

        def collect() -> dict:
            theme = {key: var.get().strip() for key, var in vars.items()}
            theme["font"] = font_var.get().strip() or "Segoe UI"
            theme["size"] = size_var.get()
            theme["button_shape"] = shape_var.get().strip() or "Pill"
            return theme

        def push(theme: dict) -> None:
            for key, var in vars.items():
                if key in theme:
                    var.set(str(theme[key]))
            if theme.get("font"):
                font_var.set(str(theme["font"]))
            if theme.get("size"):
                try:
                    size_var.set(int(theme["size"]))
                except (tk.TclError, ValueError):
                    pass
            if theme.get("button_shape"):
                shape_var.set(str(theme["button_shape"]))
            self._apply_theme(collect())

        ttk.Label(form, text="App theme", style="Card.TLabel", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(
            form,
            text="Colors match the preview. Buttons are pills. Accent is the main action, such as Write the card and Generate. Button color and button text are the other buttons.",
            style="Muted.TLabel",
            wraplength=720,
        ).pack(anchor="w", pady=(4, 8))
        presets = ttk.Frame(form, style="Card.TFrame")
        presets.pack(fill="x", pady=(0, 8))
        for name in THEME_PRESETS:
            ttk.Button(presets, text=name, command=lambda name=name: push(THEME_PRESETS[name])).pack(side="left", padx=(0, 8))
        for key, title in labels:
            row = ttk.Frame(form, style="Card.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=title, style="Card.TLabel", width=18).pack(side="left")
            chip = tk.Label(row, text="    ", bg=vars[key].get(), width=4, relief="flat")
            chip.pack(side="left", padx=(0, 8))
            tk.Entry(row, textvariable=vars[key], bg=INSET, fg=FG, insertbackground=FG, relief="flat", width=12).pack(side="left", ipady=4)

            def pick(key=key, chip=chip) -> None:
                chosen = colorchooser.askcolor(color=vars[key].get() or None, parent=self)
                if chosen and chosen[1]:
                    vars[key].set(chosen[1])

            def watch(*_args, key=key, chip=chip) -> None:
                color = vars[key].get().strip()
                if len(color) == 7 and color.startswith("#"):
                    try:
                        chip.configure(bg=color)
                    except tk.TclError:
                        pass
                self._apply_theme(collect())

            ttk.Button(row, text="Pick", command=pick).pack(side="left", padx=8)
            vars[key].trace_add("write", watch)
            chip._role_bg = key
        font_row = ttk.Frame(form, style="Card.TFrame")
        font_row.pack(fill="x", pady=(10, 3))
        ttk.Label(font_row, text="Font", style="Card.TLabel", width=18).pack(side="left")
        tk.Entry(font_row, textvariable=font_var, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, ipady=4)
        size_row = ttk.Frame(form, style="Card.TFrame")
        size_row.pack(fill="x", pady=3)
        ttk.Label(size_row, text="Text size", style="Card.TLabel", width=18).pack(side="left")
        tk.Spinbox(size_row, from_=8, to=18, textvariable=size_var, bg=INSET, fg=FG, relief="flat", width=6).pack(side="left", ipady=2)

        def typed(*_args) -> None:
            self._apply_theme(collect())

        font_var.trace_add("write", typed)
        size_var.trace_add("write", typed)
        shape_row = ttk.Frame(form, style="Card.TFrame")
        shape_row.pack(fill="x", pady=3)
        ttk.Label(shape_row, text="Button theme", style="Card.TLabel", width=18).pack(side="left")
        shape_box = ttk.Combobox(shape_row, textvariable=shape_var, state="readonly", width=16, values=("Pill", "Rounded", "Square"))
        shape_box.pack(side="left")
        shape_var.trace_add("write", typed)
        actions = ttk.Frame(form, style="Card.TFrame")
        actions.pack(fill="x", pady=(12, 4))

        def reset() -> None:
            push(THEME_PRESETS["Cardwright"])

        def export_theme() -> None:
            path = filedialog.asksaveasfilename(title="Save theme", defaultextension=".json", filetypes=[("JSON", "*.json")])
            if path:
                Path(path).write_text(json.dumps(collect(), indent=2), encoding="utf-8")

        def import_theme() -> None:
            path = filedialog.askopenfilename(title="Open theme", filetypes=[("JSON", "*.json")])
            if not path:
                return
            try:
                loaded = json.loads(Path(path).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                messagebox.showerror(APP, "That file is not a theme.")
                return
            if isinstance(loaded, dict):
                push(loaded)

        ttk.Button(actions, text="Reset", style="Primary.TButton", command=reset).pack(side="left")
        ttk.Button(actions, text="Save JSON", command=export_theme).pack(side="left", padx=8)
        ttk.Button(actions, text="Open JSON", command=import_theme).pack(side="left")
        self._theme_push = push

    def _make_scroller(self, parent, *, bg=BG, width=0, style="TFrame") -> ttk.Frame:
        shell = ttk.Frame(parent, style="TFrame")
        shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(shell, bg=bg, highlightthickness=0, bd=0)
        if width:
            canvas.configure(width=width)
        bar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas, style=style, padding=12 if style == "Card.TFrame" else 0)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _fit(_event=None) -> None:
            if getattr(canvas, "_fit_job", None):
                return

            def run() -> None:
                canvas._fit_job = None
                try:
                    width = max(canvas.winfo_width(), 1)
                    if getattr(canvas, "_fit_width", None) != width:
                        canvas._fit_width = width
                        canvas.itemconfigure(window, width=width)
                    canvas.configure(scrollregion=canvas.bbox("all") or (0, 0, 0, 0))
                except tk.TclError:
                    pass

            canvas._fit_job = canvas.after_idle(run)

        inner.bind("<Configure>", _fit)
        canvas.bind("<Configure>", _fit)
        self._scroll_canvases.append(canvas)
        return inner

    def _wheel(self, event) -> str | None:
        current = getattr(event, "widget", None)
        while current is not None and current not in self._scroll_canvases:
            if isinstance(current, (tk.Text, tk.Listbox)):
                return None
            current = getattr(current, "master", None)
        if current is None:
            return None
        if getattr(event, "delta", 0):
            notches = int(event.delta / 120) or (1 if event.delta > 0 else -1)
            current.yview_scroll(-notches * 2, "units")
        elif getattr(event, "num", None) == 4:
            current.yview_scroll(-2, "units")
        elif getattr(event, "num", None) == 5:
            current.yview_scroll(2, "units")
        return "break"

    def _popup(self, event, items: list[tuple[str, object]]) -> str:
        menu = tk.Menu(self, tearoff=0, bg=SURFACE, fg=FG, activebackground=PRIMARY, activeforeground="#fff8f5", bd=0)
        for label, action in items:
            if not label:
                menu.add_separator()
            else:
                menu.add_command(label=label, command=action)
        menu.tk_popup(event.x_root, event.y_root)
        menu.bind("<Unmap>", lambda _event: menu.destroy())
        return "break"

    def _warm_spell(self) -> None:
        SPELL.load()
        self._spell_ready = True

    def _spell_poll(self) -> None:
        if not self._spell_ready:
            self.after(200, self._spell_poll)
            return
        if not SPELL.words:
            self._say("Spell check dictionary was not found. Copy spell_words.gz next to redgen.py.")
            return

    def _spell_all(self) -> None:
        return

    def _spell_modified(self, event) -> None:
        widget = event.widget
        if not isinstance(widget, tk.Text) or getattr(widget, "_spell_skip", False) or getattr(widget, "_spell_busy", False):
            return
        pending = getattr(widget, "_spell_after", None)
        if pending:
            try:
                self.after_cancel(pending)
            except tk.TclError:
                pass

        def run(target=widget) -> None:
            target._spell_after = None
            try:
                if str(target.cget("state")) == "disabled":
                    return
            except tk.TclError:
                return
            self._mark_spelling(target)
            try:
                target._spell_busy = True
                target.edit_modified(False)
            except tk.TclError:
                pass
            finally:
                target._spell_busy = False

        try:
            widget._spell_after = self.after(350, run)
        except tk.TclError:
            return

    def _mark_spelling(self, widget: tk.Text) -> None:
        if SPELL.words is None:
            return
        try:
            widget.tag_configure("misspelled", foreground="#ff8d8d", underline=True)
            widget.tag_remove("misspelled", "1.0", "end")
        except tk.TclError:
            return
        text = widget.get("1.0", "end-1c")
        if len(text) > 6000:
            text = text[:6000]
        marks = 0
        for match in _SPELL_WORD.finditer(text):
            if marks >= 40:
                break
            word = match.group()
            if len(word) < 2 or SPELL.known(word):
                continue
            widget.tag_add("misspelled", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
            marks += 1
        try:
            widget.tag_raise("sel")
        except tk.TclError:
            pass

    def _word_at(self, widget: tk.Text, event) -> tuple[str, str, str]:
        try:
            index = widget.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return "", "", ""
        line_no, col_text = index.split(".")
        col = int(col_text)
        line = widget.get(f"{line_no}.0", f"{line_no}.end")
        if col > len(line):
            return "", "", ""
        if col == len(line) or not (line[col].isalpha() or line[col] == "'"):
            if col == 0 or not (line[col - 1].isalpha() or line[col - 1] == "'"):
                return "", "", ""
            col -= 1
        left = col
        while left > 0 and (line[left - 1].isalpha() or line[left - 1] == "'"):
            left -= 1
        right = col + 1
        while right < len(line) and (line[right].isalpha() or line[right] == "'"):
            right += 1
        word = line[left:right].strip("'")
        if len(word) < 2 or not word[0].isalpha():
            return "", "", ""
        return word, f"{line_no}.{left}", f"{line_no}.{right}"

    def _text_popup(self, event) -> str:
        widget = event.widget
        widget.focus_set()
        locked = str(widget.cget("state")) == "disabled"

        def cut() -> None:
            widget.event_generate("<<Cut>>")

        def copy() -> None:
            if locked:
                self._copy_text(widget.get("1.0", "end").strip())
            else:
                widget.event_generate("<<Copy>>")

        def paste() -> None:
            widget.event_generate("<<Paste>>")

        def select_all() -> None:
            widget.tag_add("sel", "1.0", "end")

        items: list[tuple[str, object]] = []
        if not locked:
            word, start, end = self._word_at(widget, event)
            if word and not SPELL.known(word):
                for guess in SPELL.suggest(word):

                    def use(replacement=guess, start=start, end=end) -> None:
                        widget.delete(start, end)
                        widget.insert(start, replacement)

                    items.append((guess, use))

                def remember(word=word) -> None:
                    SPELL.add(word)
                    self._mark_spelling(widget)
                    self._say(f'Added "{word}" to the dictionary.')

                if items:
                    items.append(("", None))
                items.append(("Add to dictionary", remember))
                items.append(("", None))
        items.extend([("Copy", copy)] if locked else [("Cut", cut), ("Copy", copy), ("Paste", paste), ("", None), ("Select all", select_all)])
        return self._popup(event, items)

    def _entry_popup(self, event) -> str:
        widget = event.widget
        widget.focus_set()

        def cut() -> None:
            widget.event_generate("<<Cut>>")

        def copy() -> None:
            try:
                self._copy_text(widget.selection_get())
            except tk.TclError:
                self._copy_text(widget.get())

        def paste() -> None:
            widget.event_generate("<<Paste>>")

        def select_all() -> None:
            widget.selection_range(0, "end")
            widget.icursor("end")

        return self._popup(event, [("Cut", cut), ("Copy", copy), ("Paste", paste), ("", None), ("Select all", select_all)])

    def _list_popup(self, event) -> str:
        widget = event.widget
        index = widget.nearest(event.y)
        if index >= 0 and widget.size():
            widget.selection_clear(0, "end")
            widget.selection_set(index)
            widget.activate(index)
        if widget is self.prompt_list:
            return self._popup(event, [("Load", lambda: self._load_prompt(None)), ("Delete", self._delete_prompt)])
        if widget is self.caption_list:
            return self._popup(event, [("View full size", self._click_caption_picture), ("Remove", self._remove_caption_files)])
        return self._popup(event, [("Copy", lambda: self._copy_text(widget.get(index) if widget.size() else ""))])

    def _picture_popup(self, event) -> str:
        return self._popup(
            event,
            [
                ("View full size", self._click_preview),
                ("Copy picture", self._copy_picture),
                ("Show in folder", self._show_picture),
            ],
        )

    def _caption_popup(self, event) -> str:
        return self._popup(event, [("View full size", self._click_caption_picture)])

    def _copy_text(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)

    def _copy_picture(self) -> None:
        image = getattr(self, "_full_image", None)
        if image is None:
            self._say("No picture yet.")
            return
        if sys.platform != "win32":
            self._say("Copy picture works on Windows.")
            return
        import ctypes
        import io

        payload = io.BytesIO()
        image.convert("RGB").save(payload, "BMP")
        dib = payload.getvalue()[14:]
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        user32.OpenClipboard.argtypes = [ctypes.c_void_p]
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        if not user32.OpenClipboard(None):
            self._say("Could not open the clipboard.")
            return
        try:
            user32.EmptyClipboard()
            handle = kernel32.GlobalAlloc(0x0002, len(dib))
            locked = kernel32.GlobalLock(handle)
            ctypes.memmove(locked, dib, len(dib))
            kernel32.GlobalUnlock(handle)
            user32.SetClipboardData(8, handle)
        finally:
            user32.CloseClipboard()
        self._say("Picture copied.")

    def _show_picture(self) -> None:
        path = getattr(self, "_last_picture", "")
        if path and Path(path).is_file() and sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(path)])
            return
        folder = self.output.get().strip()
        if folder and Path(folder).is_dir():
            if sys.platform == "win32":
                os_start = getattr(__import__("os"), "startfile", None)
                if os_start is not None:
                    os_start(folder)
                    return
        self._say("No saved picture yet.")

    def _build_library(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        bar = ttk.Frame(parent, style="Card.TFrame", padding=12)
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        ttk.Label(bar, text="Folder", style="Card.TLabel").pack(anchor="w")
        row = ttk.Frame(bar, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        self.library_folder = tk.StringVar(value=str(Path.home() / "Pictures" / "RedGen"))
        tk.Entry(row, textvariable=self.library_folder, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(row, text="Browse", command=self._pick_library).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="Refresh", command=self._refresh_library).pack(side="left", padx=(8, 0))
        self.library_sub = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar,
            text="Include subfolders when All pictures is selected",
            variable=self.library_sub,
            bg=SURFACE,
            fg=FG,
            selectcolor=BG,
            activebackground=SURFACE,
            activeforeground=FG,
            command=self._refresh_library,
        ).pack(anchor="w")
        self.library_note = tk.Label(bar, text="No pictures yet", bg=SURFACE, fg=MUTED, font=("Segoe UI", 9))
        self.library_note.pack(anchor="w", pady=(4, 0))
        body = ttk.Frame(parent, style="TFrame")
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        side = ttk.Frame(body, style="Card.TFrame", padding=8)
        side.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        ttk.Label(side, text="Folders", style="Card.TLabel").pack(anchor="w")
        self.library_folders = tk.Listbox(
            side, width=22, bg=INSET, fg=FG, selectbackground=PRIMARY, relief="flat", highlightthickness=0, activestyle="none"
        )
        self.library_folders.pack(fill="y", expand=True, pady=(4, 0))
        self.library_folders.insert("end", "All pictures")
        self.library_folders.bind("<<ListboxSelect>>", self._pick_library_folder)
        self._library_scope = ""
        host = ttk.Frame(body, style="TFrame")
        host.grid(row=0, column=1, sticky="nsew")
        canvas = tk.Canvas(host, bg=BG, highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas, style="TFrame")
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        self.library_canvas = canvas
        self.library_inner = inner
        self.library_window = window
        self._library_photos = []
        self._library_files: list[str] = []
        self._library_token = None
        self._scroll_canvases.append(canvas)

        def _fit(_event=None) -> None:
            if getattr(canvas, "_fit_job", None):
                return

            def run() -> None:
                canvas._fit_job = None
                try:
                    width = max(canvas.winfo_width(), 1)
                    if getattr(canvas, "_fit_width", None) != width:
                        canvas._fit_width = width
                        canvas.itemconfigure(window, width=width)
                    canvas.configure(scrollregion=canvas.bbox("all") or (0, 0, 0, 0))
                except tk.TclError:
                    pass

            canvas._fit_job = canvas.after_idle(run)

        inner.bind("<Configure>", _fit)
        canvas.bind("<Configure>", self._reflow_library)

    def _pick_library(self) -> None:
        options = {"title": "Picture folder"}
        start = self._dialog_dir("pictures", self.library_folder.get().strip())
        if start:
            options["initialdir"] = start
        picked = filedialog.askdirectory(**options)
        if not picked:
            return
        self.library_folder.set(picked)
        self._remember_root("pictures", picked)
        self._library_scope = ""
        self._refresh_library()

    def _pick_library_folder(self, _event=None) -> None:
        if getattr(self, "_library_filling", False):
            return
        selected = self.library_folders.curselection()
        label = self.library_folders.get(selected[0]) if selected else "All pictures"
        self._library_scope = "" if label == "All pictures" else label
        self._refresh_library(keep_folders=True)

    def _fill_library_folders(self, root: Path) -> None:
        box = getattr(self, "library_folders", None)
        if box is None:
            return
        current = self._library_scope or "All pictures"
        names = ["All pictures"]
        if root.is_dir():
            found = []
            for path in root.rglob("*"):
                if not path.is_dir():
                    continue
                if any(child.is_file() and child.suffix.lower() in IMAGE_EXTS for child in path.iterdir()):
                    found.append(str(path.relative_to(root)))
            names.extend(sorted(found)[:300])
        self._library_filling = True
        box.delete(0, "end")
        for name in names:
            box.insert("end", name)
        if current in names:
            box.selection_set(names.index(current))
        else:
            self._library_scope = ""
            box.selection_set(0)
        self._library_filling = False

    def _refresh_library(self, keep_folders: bool = False) -> None:
        folder = Path(self.library_folder.get().strip())
        if not folder.is_dir():
            self.library_note.configure(text="That folder does not exist.")
            self._show_library(self._library_token, [])
            return
        if not keep_folders:
            self._fill_library_folders(folder)
        scope = getattr(self, "_library_scope", "")
        target = folder / scope if scope else folder
        if not target.is_dir():
            target = folder
            self._library_scope = ""
        files = []
        nested = (not scope) and bool(self.library_sub.get())
        walker = target.rglob("*") if nested else target.iterdir()
        for path in walker:
            if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
                files.append(path)
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        extra = f" Folder {scope}." if scope else ""
        if len(files) > 400:
            extra += " Showing the newest 400."
            files = files[:400]
        self.library_note.configure(text=(f"{len(files)} pictures.{extra}" if files else f"No pictures.{extra}"))
        token = object()
        self._library_token = token
        threading.Thread(target=self._load_library, args=(token, [str(path) for path in files]), daemon=True).start()

    def _load_library(self, token, files: list[str]) -> None:
        from PIL import Image

        thumbs = []
        for path in files:
            if self._library_token is not token:
                return
            try:
                with Image.open(path) as image:
                    preview = image.convert("RGB")
                    preview.thumbnail((176, 176))
                    thumbs.append((path, preview.copy()))
            except OSError:
                continue
        self.after(0, lambda: self._show_library(token, thumbs))

    def _show_library(self, token, thumbs) -> None:
        from PIL import ImageTk

        if token is not self._library_token and thumbs:
            return
        for child in self.library_inner.winfo_children():
            child.destroy()
        self._library_photos = []
        self._library_files = []
        for path, image in thumbs:
            photo = ImageTk.PhotoImage(image)
            self._library_photos.append(photo)
            self._library_files.append(path)
            cell = ttk.Frame(self.library_inner, style="Card.TFrame", padding=6)
            picture = tk.Label(cell, image=photo, bg=SURFACE, cursor="hand2")
            picture.pack()
            name = Path(path).name
            if len(name) > 22:
                name = name[:19] + "..."
            tk.Label(cell, text=name, bg=SURFACE, fg=MUTED, font=("Segoe UI", 8)).pack()
            picture.bind("<Button-1>", lambda _event, item=path: self._library_open(item))
            picture.bind("<Button-3>", lambda event, item=path: self._library_menu(event, item))
        self._reflow_library()

    def _reflow_library(self, _event=None) -> None:
        cells = self.library_inner.winfo_children()
        width = max(self.library_canvas.winfo_width(), 1)
        columns = max(1, width // 200)
        signature = (width, columns, len(cells))
        if getattr(self, "_library_layout", None) == signature:
            return
        self._library_layout = signature
        for index, cell in enumerate(cells):
            cell.grid(row=index // columns, column=index % columns, padx=6, pady=6, sticky="n")
        self.library_canvas.configure(scrollregion=self.library_canvas.bbox("all") or (0, 0, 0, 0))
        self.library_canvas.itemconfigure(self.library_window, width=width)

    def _picture_prompt(self, path: str) -> str:
        file = Path(path)
        text_path = file.with_suffix(".txt")
        if text_path.is_file():
            try:
                text = text_path.read_text(encoding="utf-8").strip()
                if text:
                    return text
            except OSError:
                pass
        side = file.with_suffix(".json")
        if side.is_file():
            try:
                data = json.loads(side.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = None
            if isinstance(data, dict) and str(data.get("prompt") or "").strip():
                return str(data["prompt"]).strip()
        return ""

    def _library_open(self, path: str) -> None:
        from PIL import Image

        try:
            image = Image.open(path).convert("RGB")
        except OSError:
            self._say(f"Could not open {path}")
            return
        prompt = self._picture_prompt(path) or "No prompt was saved with this picture."
        gallery = list(self._library_files) or [path]
        index = gallery.index(path) if path in gallery else 0
        self._open_full_view(image, Path(path).name, prompt, gallery, index)

    def _library_menu(self, event, path: str) -> str:
        def reveal() -> None:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", path])

        return self._popup(
            event,
            [
                ("View full size", lambda: self._library_open(path)),
                ("Show in folder", reveal),
                ("Copy path", lambda: self._copy_text(path)),
            ],
        )

    def _build_captions(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        host = ttk.Frame(parent, style="TFrame")
        host.grid(row=0, column=0, sticky="nsew")
        inner = self._make_scroller(host, bg=BG)
        card = ttk.Frame(inner, style="Card.TFrame", padding=16)
        card.pack(fill="x", padx=8, pady=8)
        ttk.Label(card, text="Training folder", style="Card.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Copies pictures into one folder and writes a matching .txt caption beside each one. Use KoboldAI, or CLIP Vision so the caption is based on the picture itself.",
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(4, 8))

        self.kobold_url = tk.StringVar(value="http://127.0.0.1:5001")
        self.kobold_key = tk.StringVar()
        self.caption_trigger = tk.StringVar()
        self.caption_dest = tk.StringVar()
        self.caption_subject = tk.StringVar(value="character")
        self.caption_copy = tk.BooleanVar(value=True)
        self.caption_skip = tk.BooleanVar(value=True)
        self.caption_engine = tk.StringVar(value="kobold")
        self._caption_files: list[str] = []
        self._caption_photo = None

        engine_row = ttk.Frame(card, style="Card.TFrame")
        engine_row.pack(fill="x", pady=(0, 8))
        ttk.Label(engine_row, text="Caption with", style="Muted.TLabel").pack(anchor="w")
        choice = ttk.Frame(card, style="Card.TFrame")
        choice.pack(fill="x")
        for value, label in (("kobold", "KoboldAI"), ("clip", "CLIP Vision"), ("joy", "JoyCaption")):
            tk.Radiobutton(
                choice,
                text=label,
                value=value,
                variable=self.caption_engine,
                command=self._sync_caption_engine,
                bg=SURFACE,
                fg=FG,
                selectcolor=BG,
                activebackground=SURFACE,
                activeforeground=FG,
            ).pack(side="left", padx=(0, 16))

        self.kobold_box = ttk.Frame(card, style="Card.TFrame")
        self.kobold_box.pack(fill="x", pady=(8, 0))
        ttk.Label(self.kobold_box, text="Kobold address", style="Muted.TLabel").pack(anchor="w")
        url_row = ttk.Frame(self.kobold_box, style="Card.TFrame")
        url_row.pack(fill="x")
        tk.Entry(url_row, textvariable=self.kobold_url, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(url_row, text="Test", command=self._test_kobold).pack(side="left", padx=(8, 0))
        ttk.Label(self.kobold_box, text="API key, if Kobold has a password", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        tk.Entry(self.kobold_box, textvariable=self.kobold_key, show="*", bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            fill="x", ipady=6
        )

        self.clip_box = ttk.Frame(card, style="Card.TFrame")
        ttk.Label(self.clip_box, text="CLIP Vision file", style="Muted.TLabel").pack(anchor="w")
        vision_row = ttk.Frame(self.clip_box, style="Card.TFrame")
        vision_row.pack(fill="x")
        tk.Entry(vision_row, textvariable=self.clip_vision, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(vision_row, text="File", command=lambda: self._pick_weight(self.clip_vision, "CLIP Vision")).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(vision_row, text="Check", command=self._test_clip_vision).pack(side="left", padx=(8, 0))
        ttk.Label(self.clip_box, text="Matching CLIP text file, CLIP-L or CLIP-G", style="Muted.TLabel").pack(
            anchor="w", pady=(6, 0)
        )
        text_row = ttk.Frame(self.clip_box, style="Card.TFrame")
        text_row.pack(fill="x")
        tk.Entry(text_row, textvariable=self.clip_vision_text, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(text_row, text="File", command=lambda: self._pick_weight(self.clip_vision_text, "CLIP text")).pack(
            side="left", padx=(8, 0)
        )

        self.joy_box = ttk.Frame(card, style="Card.TFrame")
        ttk.Label(self.joy_box, text="JoyCaption Beta One GGUF, IQ4_XS", style="Muted.TLabel").pack(anchor="w")
        joy_row = ttk.Frame(self.joy_box, style="Card.TFrame")
        joy_row.pack(fill="x")
        tk.Entry(joy_row, textvariable=self.joy_model, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(joy_row, text="File", command=lambda: self._pick_file(self.joy_model, "JoyCaption GGUF", "*.gguf")).pack(
            side="left", padx=(8, 0)
        )
        ttk.Label(self.joy_box, text="mmproj, llama-joycaption-beta-one-llava-mmproj-model-f16.gguf", style="Muted.TLabel").pack(
            anchor="w", pady=(6, 0)
        )
        mm_row = ttk.Frame(self.joy_box, style="Card.TFrame")
        mm_row.pack(fill="x")
        tk.Entry(mm_row, textvariable=self.joy_mmproj, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(mm_row, text="File", command=lambda: self._pick_file(self.joy_mmproj, "JoyCaption mmproj", "*.gguf")).pack(
            side="left", padx=(8, 0)
        )

        self.caption_anchor = ttk.Label(card, text="What the pictures are", style="Card.TLabel")
        self.caption_anchor.pack(anchor="w", pady=(10, 2))
        kind_row = ttk.Frame(card, style="Card.TFrame")
        kind_row.pack(fill="x")
        for value, label in (
            ("character", "Character / likeness"),
            ("style", "A specific style"),
            ("concept", "A concept"),
        ):
            tk.Radiobutton(
                kind_row,
                text=label,
                value=value,
                variable=self.caption_subject,
                command=self._apply_caption_preset,
                bg=SURFACE,
                fg=FG,
                selectcolor=BG,
                activebackground=SURFACE,
                activeforeground=FG,
            ).pack(side="left", padx=(0, 16))

        self.caption_ask_label = ttk.Label(card, text="What to ask Kobold", style="Muted.TLabel")
        self.caption_ask_label.pack(anchor="w", pady=(8, 2))
        self.caption_prompt = tk.Text(card, height=3, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word")
        self.caption_prompt.pack(fill="x")
        self.caption_prompt.insert("1.0", CAPTION_PROMPTS["character"])

        trig = ttk.Frame(card, style="Card.TFrame")
        trig.pack(fill="x", pady=(8, 0))
        ttk.Label(trig, text="Trigger word, added at the start of each saved caption", style="Muted.TLabel").pack(anchor="w")
        tk.Entry(trig, textvariable=self.caption_trigger, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            fill="x", ipady=6
        )

        dest = ttk.Frame(card, style="Card.TFrame")
        dest.pack(fill="x", pady=(8, 0))
        ttk.Label(dest, text="Training folder", style="Muted.TLabel").pack(anchor="w")
        dest_row = ttk.Frame(card, style="Card.TFrame")
        dest_row.pack(fill="x")
        tk.Entry(dest_row, textvariable=self.caption_dest, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(dest_row, text="Folder", command=self._pick_caption_dest).pack(side="left", padx=(8, 0))

        picks = ttk.Frame(card, style="Card.TFrame")
        picks.pack(fill="x", pady=8)
        ttk.Button(picks, text="Add pictures", command=self._add_caption_files).pack(side="left")
        ttk.Button(picks, text="Add folder", command=self._add_caption_folder).pack(side="left", padx=8)
        ttk.Button(picks, text="Remove", command=self._remove_caption_files).pack(side="left")
        ttk.Button(picks, text="Remove all", command=self._clear_caption_files).pack(side="left", padx=(8, 0))
        picture_row = ttk.Frame(card, style="Card.TFrame")
        picture_row.pack(fill="x")
        self.caption_list = tk.Listbox(
            picture_row, height=8, bg=INSET, fg=FG, selectbackground=PRIMARY, relief="flat", activestyle="none"
        )
        self.caption_list.pack(side="left", fill="both", expand=True)
        self.caption_list.bind("<<ListboxSelect>>", self._preview_caption_pick)
        self.caption_view = tk.Canvas(picture_row, width=220, height=180, bg=BG, highlightthickness=0, cursor="hand2")
        self.caption_view.pack(side="left", padx=(8, 0))
        self.caption_view.bind("<Button-1>", self._click_caption_picture)
        self.caption_view.bind("<Button-3>", self._caption_popup)

        checks = ttk.Frame(card, style="Card.TFrame")
        checks.pack(fill="x", pady=8)
        tk.Checkbutton(
            checks,
            text="Copy pictures into the folder",
            variable=self.caption_copy,
            bg=SURFACE,
            fg=FG,
            selectcolor=BG,
            activebackground=SURFACE,
            activeforeground=FG,
        ).pack(side="left", padx=(0, 14))
        tk.Checkbutton(
            checks,
            text="Skip pictures that already have a caption",
            variable=self.caption_skip,
            bg=SURFACE,
            fg=FG,
            selectcolor=BG,
            activebackground=SURFACE,
            activeforeground=FG,
        ).pack(side="left")

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Caption", style="Primary.TButton", command=self._caption_all).pack(side="left")
        ttk.Button(actions, text="Stop", command=self._stop_captions).pack(side="left", padx=8)
        ttk.Button(actions, text="Use for training", command=self._use_caption_folder).pack(side="left")
        self.caption_log = tk.Text(card, height=6, bg=INSET, fg=FG, relief="flat", wrap="word", state="disabled")
        self.caption_log.pack(fill="both", expand=True)

    def _apply_caption_preset(self) -> None:
        if self.caption_engine.get() == "clip":
            return
        subject = self.caption_subject.get()
        text = CAPTION_PROMPTS.get(subject, CAPTION_PROMPTS["character"])
        self.caption_prompt.delete("1.0", "end")
        self.caption_prompt.insert("1.0", text)

    def _sync_caption_engine(self) -> None:
        self.kobold_box.pack_forget()
        self.clip_box.pack_forget()
        self.joy_box.pack_forget()
        engine = self.caption_engine.get()
        box = {"clip": self.clip_box, "joy": self.joy_box}.get(engine, self.kobold_box)
        box.pack(fill="x", pady=(8, 0), before=self.caption_anchor)
        label = {
            "clip": "Extra words for CLIP Vision, separated by commas",
            "joy": "What to ask JoyCaption",
        }.get(engine, "What to ask Kobold")
        self.caption_ask_label.configure(text=label)

    def _pick_file(self, variable: tk.StringVar, title: str, pattern: str) -> None:
        picked = filedialog.askopenfilename(
            title=title,
            filetypes=[(title, pattern), ("All files", "*.*")],
        )
        if picked:
            variable.set(picked)

    def _pick_weight(self, variable: tk.StringVar, title: str) -> None:
        self._pick_file(variable, title, "*.safetensors;*.bin;*.pt")

    def _preview_caption_pick(self, _event=None) -> None:
        selected = self.caption_list.curselection()
        if not selected:
            return
        self._show_caption_picture(self._caption_files[selected[0]])

    def _show_caption_picture(self, path: str) -> None:
        from PIL import Image, ImageTk

        try:
            image = Image.open(path).convert("RGB")
        except OSError:
            return
        self._caption_path = path
        image.thumbnail((220, 180))
        self._caption_photo = ImageTk.PhotoImage(image)
        self.caption_view.delete("all")
        self.caption_view.create_image(110, 90, image=self._caption_photo)

    def _test_clip_vision(self) -> None:
        path = self.clip_vision.get().strip()
        if not path or not Path(path).is_file():
            self._caption_say("Pick a CLIP Vision file first.")
            return
        try:
            summary = describe_clip_file(Path(path))
        except Exception as exc:
            self._caption_say(str(exc))
            return
        text = self.clip_vision_text.get().strip()
        extra = f" Text file: {Path(text).name}." if text and Path(text).is_file() else " Pick the matching CLIP text file too."
        self._caption_say(summary + "." + extra)

    def _caption_say(self, text: str) -> None:
        self.caption_log.configure(state="normal")
        self.caption_log.insert("end", text + "\n")
        self.caption_log.see("end")
        self.caption_log.configure(state="disabled")
        self._say(text)

    def _remember_caption_file(self, path: str) -> None:
        if path not in self._caption_files and Path(path).suffix.lower() in IMAGE_EXTS:
            self._caption_files.append(path)
            self.caption_list.insert("end", Path(path).name)

    def _add_caption_files(self) -> None:
        picked = filedialog.askopenfilenames(
            title="Pictures to caption",
            filetypes=[("Pictures", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("All files", "*.*")],
        )
        for path in picked:
            self._remember_caption_file(path)

    def _add_caption_folder(self) -> None:
        picked = filedialog.askdirectory(title="Folder of pictures")
        if not picked:
            return
        for path in sorted(Path(picked).iterdir()):
            self._remember_caption_file(str(path))

    def _remove_caption_files(self) -> None:
        selected = list(self.caption_list.curselection())
        for index in reversed(selected):
            self.caption_list.delete(index)
            del self._caption_files[index]
        if not self._caption_files:
            self._clear_caption_preview()

    def _clear_caption_files(self) -> None:
        self.caption_list.delete(0, "end")
        self._caption_files.clear()
        self._clear_caption_preview()
        self._caption_say("Removed every picture from the caption list.")

    def _clear_caption_preview(self) -> None:
        self._caption_path = ""
        self._caption_photo = None
        self.caption_view.delete("all")

    def _pick_caption_dest(self) -> None:
        picked = filedialog.askdirectory(title="Training folder")
        if picked:
            self.caption_dest.set(picked)

    def _test_kobold(self) -> None:
        url = self.kobold_url.get().strip()
        key = self.kobold_key.get().strip()

        def work() -> None:
            try:
                name = kobold_ping(url, key)
            except Exception as exc:
                detail = str(exc)
                self.after(0, lambda detail=detail: self._caption_say(f"Kobold did not answer. {detail}"))
                return
            self.after(0, lambda: self._caption_say(f"Kobold is there. Model: {name}"))

        threading.Thread(target=work, daemon=True).start()

    def _stop_captions(self) -> None:
        if self.hold.busy:
            self.hold.caption_stop = True
            self._caption_say("Stopping after the current picture.")
            return
        self._caption_say("Nothing is captioning.")

    def _use_caption_folder(self) -> None:
        dest = self.caption_dest.get().strip()
        if not dest:
            messagebox.showerror(APP, "Choose a training folder first.")
            return
        self.train_folder.set(dest)
        trigger = self.caption_trigger.get().strip()
        if trigger:
            self.train_trigger.set(trigger)
        self.book.select(self.train_tab)
        self._caption_say("The Train tab is using this folder.")

    def _caption_all(self) -> None:
        if self.hold.busy:
            self._caption_say("Wait until the current job finishes.")
            return
        dest = self.caption_dest.get().strip()
        if not dest:
            messagebox.showerror(APP, "Choose the training folder where the pictures and captions should go.")
            return
        if not self._caption_files:
            messagebox.showerror(APP, "Add pictures first.")
            return
        instruction = self.caption_prompt.get("1.0", "end").strip()
        engine = self.caption_engine.get()
        vision = self.clip_vision.get().strip()
        vision_text = self.clip_vision_text.get().strip()
        joy_model = self.joy_model.get().strip()
        joy_mmproj = self.joy_mmproj.get().strip()
        if engine == "clip":
            if not vision or not Path(vision).is_file():
                messagebox.showerror(APP, "Pick a CLIP Vision file.")
                return
            if vision_text and not Path(vision_text).is_file():
                messagebox.showerror(APP, "The CLIP text file could not be found.")
                return
        elif engine == "joy":
            if not joy_model or not Path(joy_model).is_file():
                messagebox.showerror(APP, "Pick the JoyCaption Beta One GGUF, such as the IQ4_XS file.")
                return
            if not joy_mmproj or not Path(joy_mmproj).is_file():
                messagebox.showerror(APP, "Pick llama-joycaption-beta-one-llava-mmproj-model-f16.gguf.")
                return
        elif not instruction:
            messagebox.showerror(APP, "Write what Kobold should say about each picture.")
            return
        self.hold.busy = True
        self.hold.caption_stop = False
        job = {
            "files": list(self._caption_files),
            "dest": dest,
            "url": self.kobold_url.get().strip(),
            "key": self.kobold_key.get().strip(),
            "trigger": self.caption_trigger.get().strip(),
            "instruction": instruction,
            "copy": bool(self.caption_copy.get()),
            "skip": bool(self.caption_skip.get()),
            "subject": self.caption_subject.get(),
            "engine": engine,
            "vision": vision,
            "vision_text": vision_text,
            "joy_model": joy_model,
            "joy_mmproj": joy_mmproj,
        }
        label = {"clip": "CLIP Vision", "joy": "JoyCaption"}.get(engine, "Kobold")
        self._caption_say(f"Captioning {len(job['files'])} pictures with {label}.")
        threading.Thread(target=self._caption_run, args=(job,), daemon=True).start()

    def _caption_run(self, job: dict) -> None:
        import shutil

        dest = Path(job["dest"])
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            detail = str(exc)
            self.after(0, lambda detail=detail: self._caption_say(f"Could not create the folder. {detail}"))
            self.hold.busy = False
            return
        done = 0
        captioner = None
        try:
            if job.get("engine") == "clip":
                self.after(0, lambda: self._caption_say("Loading CLIP Vision."))
                text_path = Path(job["vision_text"]) if job.get("vision_text") else None
                captioner = ClipCaptioner(Path(job["vision"]), text_path)
            elif job.get("engine") == "joy":
                self.after(0, lambda: self._caption_say("Loading JoyCaption."))
                captioner = JoyCaptioner(
                    Path(job["joy_model"]),
                    Path(job["joy_mmproj"]),
                    lambda text: self.after(0, lambda text=text: self._caption_say(text)),
                )
            for source in job["files"]:
                if self.hold.caption_stop:
                    self.after(0, lambda: self._caption_say("Stopped. Finished captions were kept."))
                    return
                src = Path(source)
                self.after(0, lambda path=str(src): self._show_caption_picture(path))
                target = dest / src.name if job["copy"] else src
                caption_path = target.with_suffix(".txt")
                if job["skip"] and caption_path.is_file() and caption_path.stat().st_size > 0:
                    self.after(0, lambda name=src.name: self._caption_say(f"Skipped {name}"))
                    continue
                try:
                    if job["copy"]:
                        if src.resolve() != target.resolve():
                            shutil.copy2(src, target)
                    elif not target.is_file():
                        raise RuntimeError("The picture is not in the training folder, and copying is off.")
                    if captioner is not None:
                        text = captioner.caption(target, job["instruction"])
                    else:
                        text = kobold_caption(job["url"], job["key"], target, job["instruction"])
                    trigger = job["trigger"].strip()
                    if trigger and trigger.lower() not in text.lower():
                        if job["subject"] == "style":
                            text = f"{text}, {trigger}".strip(", ")
                        else:
                            text = f"{trigger}, {text}".strip(", ")
                    caption_path.write_text(text + "\n", encoding="utf-8")
                    done += 1
                    self.after(0, lambda name=src.name, text=text: self._caption_say(f"{name}: {text}"))
                except Exception as exc:
                    self.after(0, lambda name=src.name, exc=exc: self._caption_say(f"{name} failed. {exc}"))
            self.after(0, lambda: self._caption_say(f"Wrote {done} captions in {dest}"))
        except Exception as exc:
            detail = str(exc)
            self.after(0, lambda detail=detail: self._caption_say(f"Captioning failed. {detail}"))
        finally:
            if captioner is not None:
                captioner.close()
            self.hold.busy = False
            self.hold.caption_stop = False

    def _build_vangard(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        host = ttk.Frame(parent, style="TFrame")
        host.grid(row=0, column=0, sticky="nsew")
        inner = self._make_scroller(host, bg=BG)
        card = ttk.Frame(inner, style="Card.TFrame", padding=16)
        card.pack(fill="x", padx=8, pady=8)
        ttk.Label(card, text="Vangard Studio", style="Card.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="This is the Vangard Studio Ren'Py IDE, included in full. Open it for its own window: the editor, canvases, diagnostics, assets, translation, statistics, and its settings. Ctrl+, inside that window is Settings.",
            style="Muted.TLabel",
            wraplength=720,
        ).pack(anchor="w", pady=(4, 8))
        self.vangard_sdk = tk.StringVar()
        self.vangard_project = tk.StringVar()
        found = self._find_renpy_sdk()
        if found:
            self.vangard_sdk.set(found)
        ttk.Label(card, text="Ren'Py SDK folder", style="Muted.TLabel").pack(anchor="w")
        sdk_row = ttk.Frame(card, style="Card.TFrame")
        sdk_row.pack(fill="x")
        tk.Entry(sdk_row, textvariable=self.vangard_sdk, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, ipady=4)
        ttk.Button(sdk_row, text="SDK", command=self._pick_vangard_sdk).pack(side="left", padx=(8, 0))
        ttk.Label(card, text="This folder is written into Vangard's settings as the Ren'Py path before it opens. Change it later with Ctrl+, inside Vangard.", style="Muted.TLabel", wraplength=720).pack(anchor="w", pady=(4, 8))
        ttk.Label(card, text="Project to open", style="Muted.TLabel").pack(anchor="w")
        project_row = ttk.Frame(card, style="Card.TFrame")
        project_row.pack(fill="x")
        tk.Entry(project_row, textvariable=self.vangard_project, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, ipady=4)
        ttk.Button(project_row, text="Folder", command=self._pick_vangard_project).pack(side="left", padx=(8, 0))
        ttk.Label(card, text="Leave this blank to let Vangard open its recent project, or to use File, Open inside Vangard. A path here is passed with --project.", style="Muted.TLabel", wraplength=720).pack(anchor="w", pady=(4, 8))
        ttk.Button(card, text="Open Vangard Studio", style="Primary.TButton", command=self._open_vangard).pack(anchor="w")
        ttk.Button(card, text="Send resources", command=self._publish_redwright_link).pack(anchor="w", pady=(8, 0))
        ttk.Label(card, text="Send resources writes the pictures and cards Vangard can see. In Vangard, open a project and click the RedWright button. That one click copies them into game/images/redwright and writes game/redwright.rpy. Opening Vangard also sends the current libraries.", style="Muted.TLabel", wraplength=720).pack(anchor="w", pady=(8, 0))
        ttk.Label(card, text="The first open installs Vangard with npm, which needs Node.js 18 or newer. After that it builds and opens the IDE. Vangard Studio is AGPL-3.0, by Blue Moon Foundry. The license is vangard/LICENSE.", style="Muted.TLabel", wraplength=720).pack(anchor="w", pady=(8, 0))

    def _find_renpy_sdk(self) -> str:
        root = Path(__file__).resolve().parent
        folders = [root / "renpy-8.6.1-sdk", root / "renpy-sdk"]
        folders.extend(path for path in root.glob("renpy-*-sdk") if path.is_dir())
        for folder in folders:
            if (folder / "renpy.exe").is_file() or (folder / "renpy.sh").is_file():
                return str(folder)
        return ""

    def _pick_vangard_sdk(self) -> None:
        picked = filedialog.askdirectory(title="Ren'Py SDK folder")
        if picked:
            self.vangard_sdk.set(picked)

    def _pick_vangard_project(self) -> None:
        picked = filedialog.askdirectory(title="Ren'Py project")
        if picked:
            self.vangard_project.set(picked)

    def _vangard_settings_file(self) -> Path:
        import os

        if sys.platform == "win32":
            root = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        elif sys.platform == "darwin":
            root = Path.home() / "Library" / "Application Support"
        else:
            root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        return root / "vangard-studio" / "app-settings.json"

    def _open_vangard(self) -> None:
        folder = Path(__file__).resolve().parent / "vangard"
        bat = folder / "Run Vangard.bat"
        if not bat.is_file() or not (folder / "electron.js").is_file():
            self._say("The vangard folder is missing. Copy it next to redgen.py.")
            return
        settings_path = self._vangard_settings_file()
        try:
            current = {}
            if settings_path.is_file():
                loaded = json.loads(settings_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    current = loaded
            sdk = self.vangard_sdk.get().strip()
            if sdk:
                current["renpyPath"] = sdk
            current["redwrightHome"] = str(Path(__file__).resolve().parent)
            self._publish_redwright_link(announce=False)
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        except (OSError, json.JSONDecodeError) as exc:
            self._say(f"Could not write Vangard settings. {exc}")
            return
        project = self.vangard_project.get().strip()
        command = ["cmd", "/c", str(bat)]
        if project:
            command.append(project)
        flags = {}
        creation = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        if sys.platform == "win32" and creation:
            flags["creationflags"] = creation
        subprocess.Popen(command, cwd=str(folder), **flags)
        self._say("Opening Vangard Studio. The first time installs it, then its window opens.")

    def _build_train(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        host = ttk.Frame(parent, style="TFrame")
        host.grid(row=0, column=0, sticky="nsew")
        inner = self._make_scroller(host, bg=BG)
        card = ttk.Frame(inner, style="Card.TFrame", padding=16)
        card.pack(fill="x", padx=8, pady=8)
        ttk.Label(card, text="Train a LoRA", style="Card.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Uses the model selected on Generate. A matching .txt file captions each picture. Aspect buckets keep the picture's shape instead of forcing a square.",
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(4, 8))

        self.train_folder = tk.StringVar()
        self.train_trigger = tk.StringVar()
        self.train_name = tk.StringVar(value="trained")
        self.train_rank = tk.IntVar(value=32)
        self.train_alpha = tk.IntVar(value=16)
        self.train_lr = tk.StringVar(value="0.0001")
        self.train_steps = tk.IntVar(value=400)
        self.train_res = tk.IntVar(value=512)
        self.train_subject = tk.StringVar(value="character")
        self.train_buckets = tk.BooleanVar(value=True)
        self.train_checkpoint = tk.BooleanVar(value=True)
        self.train_cache = tk.BooleanVar(value=True)
        self.train_no_half = tk.BooleanVar(value=True)

        ttk.Label(card, text="What you are training", style="Card.TLabel").pack(anchor="w", pady=(4, 2))
        kind_row = ttk.Frame(card, style="Card.TFrame")
        kind_row.pack(fill="x", pady=(0, 4))
        for value, label in (
            ("character", "Character / likeness"),
            ("style", "A specific style"),
            ("concept", "A concept"),
        ):
            tk.Radiobutton(
                kind_row,
                text=label,
                value=value,
                variable=self.train_subject,
                command=self._apply_train_preset,
                bg=SURFACE,
                fg=FG,
                selectcolor=BG,
                activebackground=SURFACE,
                activeforeground=FG,
            ).pack(side="left", padx=(0, 16))
        self.train_hint = tk.Label(
            card,
            text="A person. The trigger word is their name. Rank 32, alpha 16.",
            bg=SURFACE,
            fg=MUTED,
            wraplength=760,
            justify="left",
        )
        self.train_hint.pack(anchor="w", pady=(0, 8))

        folder_row = ttk.Frame(card, style="Card.TFrame")
        folder_row.pack(fill="x", pady=4)
        tk.Entry(folder_row, textvariable=self.train_folder, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(folder_row, text="Image folder", command=self._pick_train_folder).pack(side="left", padx=(8, 0))

        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(fill="x", pady=4)
        fields = (
            ("Trigger word", self.train_trigger, 16),
            ("LoRA name", self.train_name, 14),
            ("Network rank", self.train_rank, 6),
            ("Network alpha", self.train_alpha, 6),
            ("Learning rate", self.train_lr, 10),
            ("Steps", self.train_steps, 8),
            ("Resolution", self.train_res, 8),
        )
        for label, var, width in fields:
            box = ttk.Frame(form, style="Card.TFrame")
            box.pack(side="left", padx=(0, 10))
            ttk.Label(box, text=label, style="Muted.TLabel").pack(anchor="w")
            tk.Entry(box, textvariable=var, width=width, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(ipady=4)

        checks = ttk.Frame(card, style="Card.TFrame")
        checks.pack(fill="x", pady=8)
        for text, var in (
            ("Aspect-ratio buckets", self.train_buckets),
            ("Gradient checkpointing", self.train_checkpoint),
            ("Cache latents", self.train_cache),
            ("No half VAE", self.train_no_half),
        ):
            tk.Checkbutton(
                checks,
                text=text,
                variable=var,
                bg=SURFACE,
                fg=FG,
                selectcolor=BG,
                activebackground=SURFACE,
                activeforeground=FG,
            ).pack(side="left", padx=(0, 14))

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Train", style="Primary.TButton", command=self._train).pack(side="left")
        ttk.Button(actions, text="Stop", command=self._stop_training).pack(side="left", padx=8)
        self.train_progress = ttk.Progressbar(card, style="Red.Horizontal.TProgressbar", maximum=100)
        self.train_progress.pack(fill="x", pady=(0, 8))
        self.train_log = tk.Text(card, height=12, bg=INSET, fg=FG, relief="flat", wrap="word", state="disabled")
        self.train_log.pack(fill="both", expand=True)

    def _apply_train_preset(self) -> None:
        subject = self.train_subject.get()
        presets = {
            "character": (32, 16, "A person. The trigger word is their name. Rank 32, alpha 16."),
            "style": (16, 16, "A look. The trigger word is the style name, added at the end of each caption. Rank 16, alpha 16."),
            "concept": (16, 8, "An object or idea. The trigger word is the concept, added at the start. Rank 16, alpha 8."),
        }
        rank, alpha, hint = presets.get(subject, presets["character"])
        self.train_rank.set(rank)
        self.train_alpha.set(alpha)
        self.train_hint.configure(text=hint)

    def _pick_train_folder(self) -> None:
        picked = filedialog.askdirectory(title="Training pictures")
        if picked:
            self.train_folder.set(picked)

    def _train_say(self, text: str) -> None:
        self.train_log.configure(state="normal")
        self.train_log.insert("end", text + "\n")
        self.train_log.see("end")
        self.train_log.configure(state="disabled")
        self._say(text)

    def _stop_training(self) -> None:
        proc = self.hold.proc
        if proc is not None and proc.poll() is None:
            self._kill_job()
            self.hold.busy = False
            self._train_say("Training stopped. The card is clear. Nothing was saved.")
            return
        self._train_say("Nothing is training.")

    def _train(self) -> None:
        if self.hold.busy:
            self._train_say("Wait until the current job finishes.")
            return
        folder = self.train_folder.get().strip()
        model = self.model_box.get().strip()
        if not model or not Path(model).exists():
            messagebox.showerror(APP, "Select a model on the Generate tab first.")
            return
        if not folder or not Path(folder).is_dir():
            messagebox.showerror(APP, "Choose a folder of training pictures.")
            return
        try:
            rank = max(1, min(128, int(self.train_rank.get())))
            alpha = max(1, min(128, int(self.train_alpha.get())))
            steps = max(1, int(self.train_steps.get()))
            res = max(64, int(self.train_res.get()))
            res -= res % 64
            lr = float(self.train_lr.get())
        except (tk.TclError, ValueError):
            messagebox.showerror(APP, "Rank, alpha, steps, resolution, and learning rate must be numbers.")
            return
        if res < 64:
            res = 64
        name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in self.train_name.get().strip()) or "trained"
        out = Path(self.output.get().strip() or str(Path.home() / "Pictures" / "RedGen")) / f"{name}.safetensors"
        subject = self.train_subject.get()
        if subject not in {"character", "style", "concept"}:
            subject = "character"
        job = {
            "kind": "train",
            "model": model,
            "folder": folder,
            "trigger": self.train_trigger.get().strip(),
            "subject": subject,
            "rank": rank,
            "alpha": alpha,
            "lr": lr,
            "steps": steps,
            "resolution": res,
            "buckets": bool(self.train_buckets.get()),
            "checkpoint": bool(self.train_checkpoint.get()),
            "cache_latents": bool(self.train_cache.get()),
            "no_half_vae": bool(self.train_no_half.get()),
            "out": str(out),
            "clip": self.clip.get().strip(),
            "clip_g": self.clip_g.get().strip(),
        }
        self.hold.busy = True
        self.train_progress["value"] = 0
        self._train_say(f"Training {name} as a {subject}. Rank {rank}, alpha {alpha}.")
        threading.Thread(target=self._train_run, args=(job,), daemon=True).start()

    def _train_run(self, job: dict) -> None:
        import json as _json

        work = Path(tempfile.gettempdir()) / "RedGen"
        work.mkdir(parents=True, exist_ok=True)
        status_path = work / "train-status.txt"
        if status_path.exists():
            status_path.unlink()
        out = job["out"]
        job["status"] = str(status_path)
        job_path = work / "train-job.json"
        job_path.write_text(_json.dumps(job), encoding="utf-8")
        proc = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--job", str(job_path)])
        self.hold.proc = proc
        seen = ""
        try:
            while proc.poll() is None:
                text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
                if text and text != seen and not text.startswith("error"):
                    seen = text
                    self.after(0, lambda line=text: self._train_note(line))
                time.sleep(0.4)
            text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
            if proc.returncode == 0 and Path(out).is_file():
                self.after(0, lambda: self._add_lora(out, 0.8))
                self.after(0, lambda: self.train_progress.configure(value=100))
                self.after(0, lambda: self._train_say(f"Saved {out}. It is on the LoRA list."))
            else:
                detail = text.split("\n", 1)[-1] if text.startswith("error") else f"Training stopped ({proc.returncode})."
                self.after(0, lambda d=detail: self._train_say(f"Training failed: {d}"))
        finally:
            self._kill_job()
            self.hold.busy = False

    def _build_anima_train(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        host = ttk.Frame(parent, style="TFrame")
        host.grid(row=0, column=0, sticky="nsew")
        inner = self._make_scroller(host, bg=BG)
        card = ttk.Frame(inner, style="Card.TFrame", padding=16)
        card.pack(fill="x", padx=8, pady=8)
        ttk.Label(card, text="Train an Anima LoRA", style="Card.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Uses the Anima model, Qwen3 text encoder, and Qwen-Image VAE from the Anima tab. A matching .txt file captions each picture. Rank 8 is the usual start on a 16 GB card. The saved file is added to the Anima LoRA list, not the Stable Diffusion one.",
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(4, 8))

        self.anima_train_folder = tk.StringVar()
        self.anima_train_trigger = tk.StringVar()
        self.anima_train_name = tk.StringVar(value="anima-trained")
        self.anima_train_rank = tk.IntVar(value=8)
        self.anima_train_alpha = tk.IntVar(value=8)
        self.anima_train_lr = tk.StringVar(value="0.0001")
        self.anima_train_steps = tk.IntVar(value=400)
        self.anima_train_res = tk.IntVar(value=512)
        self.anima_train_subject = tk.StringVar(value="character")
        self.anima_train_buckets = tk.BooleanVar(value=True)
        self.anima_train_checkpoint = tk.BooleanVar(value=True)
        self.anima_train_cache = tk.BooleanVar(value=True)
        self.anima_train_fp32_vae = tk.BooleanVar(value=True)

        ttk.Label(card, text="What you are training", style="Card.TLabel").pack(anchor="w", pady=(4, 2))
        kind_row = ttk.Frame(card, style="Card.TFrame")
        kind_row.pack(fill="x", pady=(0, 4))
        for value, label in (
            ("character", "Character / likeness"),
            ("style", "A specific style"),
            ("concept", "A concept"),
        ):
            tk.Radiobutton(
                kind_row,
                text=label,
                value=value,
                variable=self.anima_train_subject,
                command=self._apply_anima_train_preset,
                bg=SURFACE,
                fg=FG,
                selectcolor=BG,
                activebackground=SURFACE,
                activeforeground=FG,
            ).pack(side="left", padx=(0, 16))
        self.anima_train_hint = tk.Label(
            card,
            text="A person. The trigger word is their name. Rank 8, alpha 8.",
            bg=SURFACE,
            fg=MUTED,
            wraplength=760,
            justify="left",
        )
        self.anima_train_hint.pack(anchor="w", pady=(0, 8))

        folder_row = ttk.Frame(card, style="Card.TFrame")
        folder_row.pack(fill="x", pady=4)
        tk.Entry(folder_row, textvariable=self.anima_train_folder, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )
        ttk.Button(folder_row, text="Image folder", command=self._pick_anima_train_folder).pack(side="left", padx=(8, 0))

        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(fill="x", pady=4)
        fields = (
            ("Trigger word", self.anima_train_trigger, 16),
            ("LoRA name", self.anima_train_name, 14),
            ("Network rank", self.anima_train_rank, 6),
            ("Network alpha", self.anima_train_alpha, 6),
            ("Learning rate", self.anima_train_lr, 10),
            ("Steps", self.anima_train_steps, 8),
            ("Resolution", self.anima_train_res, 8),
        )
        for label, var, width in fields:
            box = ttk.Frame(form, style="Card.TFrame")
            box.pack(side="left", padx=(0, 10))
            ttk.Label(box, text=label, style="Muted.TLabel").pack(anchor="w")
            tk.Entry(box, textvariable=var, width=width, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(ipady=4)

        checks = ttk.Frame(card, style="Card.TFrame")
        checks.pack(fill="x", pady=8)
        for text, var in (
            ("Aspect-ratio buckets", self.anima_train_buckets),
            ("Gradient checkpointing", self.anima_train_checkpoint),
            ("Cache latents", self.anima_train_cache),
            ("Float32 VAE", self.anima_train_fp32_vae),
        ):
            tk.Checkbutton(
                checks,
                text=text,
                variable=var,
                bg=SURFACE,
                fg=FG,
                selectcolor=BG,
                activebackground=SURFACE,
                activeforeground=FG,
            ).pack(side="left", padx=(0, 14))

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Train", style="Primary.TButton", command=self._anima_train).pack(side="left")
        ttk.Button(actions, text="Stop", command=self._stop_anima_training).pack(side="left", padx=8)
        self.anima_train_progress = ttk.Progressbar(card, style="Red.Horizontal.TProgressbar", maximum=100)
        self.anima_train_progress.pack(fill="x", pady=(0, 8))
        self.anima_train_log = tk.Text(card, height=12, bg=INSET, fg=FG, relief="flat", wrap="word", state="disabled")
        self.anima_train_log.pack(fill="both", expand=True)

    def _apply_anima_train_preset(self) -> None:
        subject = self.anima_train_subject.get()
        presets = {
            "character": (8, 8, "A person. The trigger word is their name. Rank 8, alpha 8."),
            "style": (4, 4, "A look. The trigger word is the style name, added at the end of each caption. Rank 4, alpha 4."),
            "concept": (8, 4, "An object or idea. The trigger word is the concept, added at the start. Rank 8, alpha 4."),
        }
        rank, alpha, hint = presets.get(subject, presets["character"])
        self.anima_train_rank.set(rank)
        self.anima_train_alpha.set(alpha)
        self.anima_train_hint.configure(text=hint)

    def _pick_anima_train_folder(self) -> None:
        picked = filedialog.askdirectory(title="Anima training pictures")
        if picked:
            self.anima_train_folder.set(picked)

    def _anima_train_say(self, text: str) -> None:
        self.anima_train_log.configure(state="normal")
        self.anima_train_log.insert("end", text + "\n")
        self.anima_train_log.see("end")
        self.anima_train_log.configure(state="disabled")
        print(f"Anima train: {text}", flush=True)

    def _anima_train_note(self, line: str) -> None:
        self._anima_train_say(line)
        self._note_progress(line, bar=self.anima_train_progress)

    def _stop_anima_training(self) -> None:
        proc = self.hold.proc
        if proc is not None and proc.poll() is None:
            self._kill_job()
            self.hold.busy = False
            self._anima_train_say("Training stopped. The card is clear. Nothing was saved.")
            return
        self._anima_train_say("Nothing is training.")

    def _anima_train(self) -> None:
        if self.hold.busy:
            self._anima_train_say("Wait until the current job finishes.")
            return
        folder = self.anima_train_folder.get().strip()
        model = self.anima_model.get().strip()
        text = self.anima_text.get().strip()
        vae = self.anima_vae.get().strip()
        if not model or not Path(model).exists():
            messagebox.showerror(APP, "Choose an Anima model on the Anima tab first.")
            return
        if Path(model).is_file() and (not text or not Path(text).is_file() or not vae or not Path(vae).is_file()):
            messagebox.showerror(APP, "A single Anima file needs the Qwen3 text encoder and the Qwen-Image VAE on the Anima tab.")
            return
        if not folder or not Path(folder).is_dir():
            messagebox.showerror(APP, "Choose a folder of training pictures.")
            return
        try:
            rank = max(1, min(64, int(self.anima_train_rank.get())))
            alpha = max(1, min(64, int(self.anima_train_alpha.get())))
            steps = max(1, int(self.anima_train_steps.get()))
            res = max(256, int(self.anima_train_res.get()))
            res -= res % 16
            lr = float(self.anima_train_lr.get())
        except (tk.TclError, ValueError):
            messagebox.showerror(APP, "Rank, alpha, steps, resolution, and learning rate must be numbers.")
            return
        if res < 256:
            res = 256
        name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in self.anima_train_name.get().strip()) or "anima-trained"
        dest = self.anima_output.get().strip() or self.output.get().strip() or str(Path.home() / "Pictures" / "RedGen")
        out = Path(dest) / f"{name}.safetensors"
        subject = self.anima_train_subject.get()
        if subject not in {"character", "style", "concept"}:
            subject = "character"
        job = {
            "kind": "anima_train",
            "model": model,
            "text": text,
            "vae": vae,
            "folder": folder,
            "trigger": self.anima_train_trigger.get().strip(),
            "subject": subject,
            "rank": rank,
            "alpha": alpha,
            "lr": lr,
            "steps": steps,
            "resolution": res,
            "buckets": bool(self.anima_train_buckets.get()),
            "checkpoint": bool(self.anima_train_checkpoint.get()),
            "cache_latents": bool(self.anima_train_cache.get()),
            "fp32_vae": bool(self.anima_train_fp32_vae.get()),
            "shift": float(self.anima_shift.get() or 3),
            "out": str(out),
        }
        self.hold.busy = True
        self.anima_train_progress["value"] = 0
        self._anima_train_say(f"Training {name} as a {subject}. Rank {rank}, alpha {alpha}.")
        threading.Thread(target=self._anima_train_run, args=(job,), daemon=True).start()

    def _anima_train_run(self, job: dict) -> None:
        import json as _json

        import anima

        work = Path(tempfile.gettempdir()) / "RedGen"
        work.mkdir(parents=True, exist_ok=True)
        status_path = work / "anima-train-status.txt"
        if status_path.exists():
            status_path.unlink()
        out = job["out"]
        job["status"] = str(status_path)
        job_path = work / "anima-train-job.json"
        job_path.write_text(_json.dumps(job), encoding="utf-8")
        try:
            self._release_anima_worker()
            python, env = anima.runtime(lambda text: self.after(0, lambda note=text: self._anima_train_say(note)))
        except Exception as exc:
            self.hold.busy = False
            self.after(0, lambda detail=exc: self._anima_train_say(f"Could not start the Anima runtime. {detail}"))
            return
        child_env = dict(env)
        child_env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            [python, "-u", "-B", str(Path(__file__).resolve()), "--job", str(job_path)],
            env=child_env,
        )
        self.hold.proc = proc
        seen = ""
        try:
            while proc.poll() is None:
                text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
                if text and text != seen and not text.startswith("error"):
                    seen = text
                    self.after(0, lambda line=text: self._anima_train_note(line))
                time.sleep(0.4)
            text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
            if proc.returncode == 0 and Path(out).is_file():
                self.after(0, lambda path=out: self._add_anima_lora(path, 0.8))
                self.after(0, lambda: self.anima_train_progress.configure(value=100))
                self.after(0, lambda path=out: self._anima_train_say(f"Saved {path}. It is on the Anima LoRA list."))
            else:
                detail = text.split("\n", 1)[-1] if text.startswith("error") else f"Training stopped ({proc.returncode})."
                self.after(0, lambda d=detail: self._anima_train_say(f"Training failed: {d}"))
        finally:
            self._kill_job()
            self.hold.busy = False

    def _empty_cache(self) -> None:
        import gc

        gc.collect()
        try:
            import torch
        except Exception:
            return
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return

    def _release_modules(self, pipe, names: tuple[str, ...]) -> None:
        import torch

        if pipe is None:
            return
        for name in names:
            module = getattr(pipe, name, None)
            if module is None:
                continue
            try:
                module.to("cpu")
            except Exception:
                pass
            try:
                for param in module.parameters(recurse=True):
                    param.data = torch.empty(0)
                for buf in module.buffers(recurse=True):
                    if torch.is_tensor(buf):
                        buf.data = torch.empty(0)
            except Exception:
                pass
            try:
                setattr(pipe, name, None)
            except Exception:
                pass
        self._empty_cache()

    def _modules_to(self, pipe, names: tuple[str, ...], device) -> None:
        for name in names:
            module = getattr(pipe, name, None)
            if module is None:
                continue
            module.to(device)

    def _kill_job(self) -> None:
        proc = self.hold.proc
        if proc is not None and proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        if proc is getattr(self, "_anima_proc", None):
            self._anima_proc = None
        if proc is getattr(self, "_sd_proc", None):
            self._sd_proc = None
        self.hold.proc = None

    def _release_sd_worker(self) -> None:
        proc = getattr(self, "_sd_proc", None)
        if proc is None:
            return
        if proc.poll() is None:
            try:
                if proc.stdin:
                    proc.stdin.write("quit\n")
                    proc.stdin.flush()
            except Exception:
                pass
            proc.kill()
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        self._sd_proc = None
        if self.hold.proc is proc:
            self.hold.proc = None

    def _ensure_sd_worker(self):
        proc = getattr(self, "_sd_proc", None)
        if proc is not None and proc.poll() is None and proc.stdin:
            return proc
        work = Path(tempfile.gettempdir()) / "RedGen"
        work.mkdir(parents=True, exist_ok=True)
        handle = (work / "sd-worker-error.txt").open("a", encoding="utf-8")
        self._sd_error_handle = handle
        proc = subprocess.Popen(
            [sys.executable, "-u", "-B", str(Path(__file__).resolve()), "--sd-serve"],
            stdin=subprocess.PIPE,
            stderr=handle,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._sd_proc = proc
        return proc

    def _keep_label(self) -> str:
        return "Unload after picture" if self.keep_loaded.get() else "Keep model loaded"

    def _toggle_keep_loaded(self) -> None:
        self.keep_loaded.set(not self.keep_loaded.get())
        for button in getattr(self, "_keep_buttons", []):
            try:
                button.configure(text=self._keep_label())
            except tk.TclError:
                pass
        if self.keep_loaded.get():
            note = "The model stays loaded until you press Unload."
        else:
            self._release_sd_worker()
            self._release_anima_worker()
            note = "The model unloads after each picture."
        self._say(note)
        if hasattr(self, "_anima_say"):
            self._anima_say(note)

    def _release_anima_worker(self) -> None:
        proc = getattr(self, "_anima_proc", None)
        if proc is None:
            return
        if proc.poll() is None:
            try:
                if proc.stdin:
                    proc.stdin.write("quit\n")
                    proc.stdin.flush()
            except Exception:
                pass
            proc.kill()
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        self._anima_proc = None
        if self.hold.proc is proc:
            self.hold.proc = None

    def _ensure_anima_worker(self, python: str, env: dict):
        proc = getattr(self, "_anima_proc", None)
        if proc is not None and proc.poll() is None and proc.stdin:
            return proc
        work = Path(tempfile.gettempdir()) / "RedGen"
        work.mkdir(parents=True, exist_ok=True)
        handle = (work / "anima-worker-error.txt").open("a", encoding="utf-8")
        self._anima_error_handle = handle
        child_env = dict(env)
        child_env["PYTHONUNBUFFERED"] = "1"
        child_env["PYTORCH_CUDA_ALLOC_CONF"] = "garbage_collection_threshold:0.6,max_split_size_mb:512"
        proc = subprocess.Popen(
            [python, "-u", "-B", str(Path(__file__).resolve()), "--anima-serve"],
            stdin=subprocess.PIPE,
            stderr=handle,
            env=child_env,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._anima_proc = proc
        return proc

    def _unload_model(self) -> None:
        proc = self.hold.proc
        if proc is not None and proc.poll() is None:
            self.hold.batch_stop = True
            self.hold.queue.clear()
            self._show_queue()
            self._kill_job()
            self._release_sd_worker()
            self._release_anima_worker()
            self.hold.busy = False
            self._say("Unloaded the model. The AMD card is clear.")
            if hasattr(self, "_anima_say"):
                self._anima_say("Unloaded the model. The next picture loads the file you have selected.")
            return
        self._release_sd_worker()
        self._release_anima_worker()
        self._say("Unloaded the model. The AMD card is clear.")
        if hasattr(self, "_anima_say"):
            self._anima_say("Nothing is loaded. The card is clear.")

    def _stop_generation(self) -> None:
        proc = self.hold.proc
        running = self.hold.busy or (proc is not None and proc.poll() is None)
        if not running:
            if self.hold.queue:
                self.hold.queue.clear()
                self._show_queue()
                self._say("Cleared the queue.")
                return
            self._say("Nothing is generating.")
            return
        self.hold.batch_stop = True
        self.hold.token = None
        self.hold.queue.clear()
        self._show_queue()
        self._kill_job()
        self.hold.busy = False
        self.view_caption.configure(text="Stopped")
        self._say("Generation stopped. The queue was cleared. The AMD card is clear.")

    def _status_tick(self, caption: str, index: int, count: int) -> None:
        anima = getattr(self, "_frame_target", "") == "anima"
        label = self.anima_caption if anima else self.view_caption
        bar = self.anima_progress if anima else self.progress
        label.configure(text=caption)
        self._note_progress(caption, index, count, bar=bar)

    def _train_note(self, line: str) -> None:
        self._train_say(line)
        self._note_progress(line, bar=self.train_progress)

    def _note_progress(self, text: str, index: int = 0, count: int = 1, bar=None) -> None:
        import re

        bar = self.progress if bar is None else bar
        count = max(1, int(count))
        index = max(0, min(int(index), count - 1))
        fraction = None
        match = re.search(r"Step\s+(\d+)\s*/\s*(\d+)", text)
        lowered = text.lower()
        if match:
            done = int(match.group(1))
            total = max(1, int(match.group(2)))
            fraction = (index + min(done, total) / total) / count
        elif lowered.startswith("vae"):
            fraction = (index + 0.97) / count
        elif lowered.startswith("final") or text.strip() == "done":
            fraction = (index + 1) / count
        elif "load" in lowered or lowered.startswith("starting") or lowered.startswith("loading") or lowered.startswith("building") or lowered.startswith("moving"):
            fraction = (index + 0.04) / count
        elif lowered.startswith("encoding") or lowered.startswith("reading the source"):
            fraction = (index + 0.12) / count
        elif lowered.startswith("decoding") or lowered.startswith("saving"):
            fraction = (index + 0.96) / count
        if fraction is None:
            return
        bar["value"] = max(0, min(100, fraction * 100))

    def _show_frame(self, image, caption: str, index: int = 0, count: int = 1) -> None:
        from PIL import ImageTk

        anima = getattr(self, "_frame_target", "") == "anima"
        canvas = self.anima_viewport if anima else self.viewport
        caption_label = self.anima_caption if anima else self.view_caption
        bar = self.anima_progress if anima else self.progress
        width = max(canvas.winfo_width(), 360)
        height = max(canvas.winfo_height(), 280)
        preview = image.copy()
        preview.thumbnail((width - 8, height - 8))
        photo = ImageTk.PhotoImage(preview)
        if anima:
            self._anima_photo = photo
            self._anima_full = image.copy()
        else:
            self.hold.photo = photo
            self._full_image = image.copy()
        canvas.delete("all")
        canvas.create_image(width // 2, height // 2, image=photo)
        caption_label.configure(text=caption)
        self._note_progress(caption, index, count, bar=bar)
        if getattr(self, "_portrait_for_card", False):
            hook = getattr(self, "_apply_card_portrait", None)
            if hook is not None:
                hook(image)

    def _click_preview(self, _event=None) -> None:
        image = getattr(self, "_full_image", None)
        if image is None:
            return
        self._open_full_view(image, self.view_caption.cget("text"))

    def _click_caption_picture(self, _event=None) -> None:
        path = getattr(self, "_caption_path", "")
        if not path or not Path(path).is_file():
            return
        from PIL import Image

        try:
            image = Image.open(path).convert("RGB")
        except OSError:
            return
        self._open_full_view(image, Path(path).name)

    def _open_full_view(self, image, title: str, prompt: str = "", gallery: list | None = None, index: int = 0) -> None:
        from PIL import Image, ImageTk

        window = tk.Toplevel(self)
        window.title(title or APP)
        window.configure(bg=BG)
        paths = [item for item in (gallery or []) if item]
        start = index if paths and 0 <= index < len(paths) else 0
        state = {"index": start, "image": image}
        wide = min(max(image.width + 20, 560), max(480, window.winfo_screenwidth() - 80))
        tall = min(image.height + 190, max(420, window.winfo_screenheight() - 80))
        window.geometry(f"{wide}x{tall}")
        canvas = tk.Canvas(window, bg=BG, highlightthickness=0)
        ybar = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
        xbar = ttk.Scrollbar(window, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)
        photo = ImageTk.PhotoImage(image)
        window._photo = photo
        picture_id = canvas.create_image(0, 0, image=photo, anchor="nw")
        canvas.configure(scrollregion=(0, 0, image.width, image.height))
        box = tk.Text(window, height=4, wrap="word", bg=INSET, fg=FG, insertbackground=FG, relief="flat", font=("Segoe UI", 10))
        box.insert("1.0", prompt.strip())
        box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(6, 0))

        def keep_prompt(event) -> str | None:
            if (event.state & 0x4) and event.keysym.lower() in {"c", "a"}:
                return None
            if event.keysym in {"Left", "Right", "Up", "Down", "Home", "End", "Next", "Prior", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
                return None
            return "break"

        box.bind("<Key>", keep_prompt)
        nav = ttk.Frame(window, style="TFrame")
        nav.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        position = tk.Label(nav, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10))
        position.pack(side="left", padx=(0, 8))

        def show(next_index: int) -> None:
            if not paths:
                position.configure(text="")
                return
            next_index = max(0, min(len(paths) - 1, next_index))
            path = paths[next_index]
            try:
                opened = Image.open(path).convert("RGB")
            except OSError:
                return
            state["index"] = next_index
            state["image"] = opened
            photo = ImageTk.PhotoImage(opened)
            window._photo = photo
            canvas.itemconfigure(picture_id, image=photo)
            canvas.configure(scrollregion=(0, 0, opened.width, opened.height))
            canvas.yview_moveto(0)
            canvas.xview_moveto(0)
            note = self._picture_prompt(path) or "No prompt was saved with this picture."
            box.delete("1.0", "end")
            box.insert("1.0", note)
            window.title(Path(path).name)
            position.configure(text=f"{next_index + 1} of {len(paths)}")

        def step(delta: int, event=None):
            if event is not None and str(event.widget.winfo_class()) == "Text":
                return None
            if not paths:
                return "break"
            show(state["index"] + delta)
            return "break"

        if paths:
            ttk.Button(nav, text="Previous", command=lambda: step(-1)).pack(side="left")
            ttk.Button(nav, text="Next", command=lambda: step(1)).pack(side="left", padx=(8, 0))
            show(start)
        ttk.Button(nav, text="Close", command=window.destroy).pack(side="right")
        window.bind("<Escape>", lambda _event: window.destroy())
        window.bind("<Left>", lambda event: step(-1, event))
        window.bind("<Right>", lambda event: step(1, event))
        window.bind("<Prior>", lambda event: step(-1, event))
        window.bind("<Next>", lambda event: step(1, event))

    def _image_is_blank(self, image) -> bool:
        extrema = image.getextrema()
        if not extrema:
            return True
        if isinstance(extrema[0], tuple):
            return max(high - low for low, high in extrema) < 3
        return extrema[1] - extrema[0] < 3

    def _mount_vae(self, pipe, path: str, sdxl: bool) -> None:
        if not path:
            return
        file = Path(path)
        if not file.exists():
            raise RuntimeError(f"VAE not found: {path}")
        import torch
        from diffusers import AutoencoderKL

        if file.is_dir():
            try:
                vae = AutoencoderKL.from_pretrained(str(file), torch_dtype=torch.float32, local_files_only=True)
            except Exception as exc:
                raise RuntimeError(f"That folder is not a VAE. {exc}") from exc
        else:
            vae = None
            try:
                vae = AutoencoderKL.from_single_file(str(file), torch_dtype=torch.float32)
            except Exception:
                vae = None
            if vae is None:
                if file.suffix.lower() == ".safetensors":
                    from safetensors.torch import load_file

                    raw = load_file(str(file))
                else:
                    try:
                        raw = torch.load(str(file), map_location="cpu", weights_only=True)
                    except TypeError:
                        raw = torch.load(str(file), map_location="cpu")
                    if hasattr(raw, "state_dict"):
                        raw = raw.state_dict()
                    if isinstance(raw, dict) and isinstance(raw.get("state_dict"), dict):
                        raw = raw["state_dict"]
                if not isinstance(raw, dict):
                    raise RuntimeError("That file is not a VAE.")
                state = _convert_ldm_vae(raw)
                if "encoder.conv_in.weight" not in state:
                    sample = ", ".join(list(raw)[:3]) or "no known keys"
                    raise RuntimeError(f"That file is not a VAE. First keys: {sample}")
                vae = AutoencoderKL.from_config(
                    {
                        "sample_size": 512,
                        "in_channels": 3,
                        "out_channels": 3,
                        "down_block_types": ["DownEncoderBlock2D", "DownEncoderBlock2D", "DownEncoderBlock2D", "DownEncoderBlock2D"],
                        "up_block_types": ["UpDecoderBlock2D", "UpDecoderBlock2D", "UpDecoderBlock2D", "UpDecoderBlock2D"],
                        "block_out_channels": [128, 256, 512, 512],
                        "layers_per_block": 2,
                        "act_fn": "silu",
                        "latent_channels": 4,
                        "norm_num_groups": 32,
                        "scaling_factor": _vae_scaling(file, sdxl),
                    }
                )
                try:
                    missing, _unexpected = vae.load_state_dict(state, strict=False)
                except RuntimeError as exc:
                    raise RuntimeError("That VAE does not match this model.") from exc
                expected = [key for key in vae.state_dict() if key.startswith(("encoder.", "decoder."))]
                missed = sum(1 for key in expected if key in set(missing))
                if expected and missed > len(expected) * 0.4:
                    sample = ", ".join(list(state)[:3]) or "no known keys"
                    raise RuntimeError(f"That file is not a VAE this app can load. First keys: {sample}")
        pipe.vae = vae
        writer = self.__dict__.get("_status_write")
        if writer is not None:
            writer(f"VAE {file.name}")

    def _latents_to_image(self, pipe, latents):
        import torch
        from PIL import Image

        vae = pipe.vae
        latents = latents.detach().float()
        if latents.shape[0] > 1:
            latents = latents[-1:]
        if not torch.isfinite(latents).all():
            raise RuntimeError(
                "This LoRA made the picture invalid before the VAE. Lower its weight, or train it again. Civitai LoRAs are not affected."
            )
        weight = next(vae.parameters())
        latents = latents.to(device=weight.device, dtype=weight.dtype)
        scaling = float(getattr(vae.config, "scaling_factor", None) or 0.18215)
        decoded = latents / scaling
        shift = getattr(vae.config, "shift_factor", None)
        if isinstance(shift, (int, float)) and shift:
            decoded = decoded + float(shift)
        vae.eval()
        tile = bool(self.__dict__.get("_vae_tile"))
        with torch.no_grad():
            if tile:
                image = _decode_vae_tiles(
                    vae,
                    decoded,
                    int(self.__dict__.get("_vae_tile_size") or 512),
                    int(self.__dict__.get("_vae_tile_overlap") or 64),
                )
            else:
                image = vae.decode(decoded, return_dict=False)[0]
        image = image[0].detach().float().cpu()
        if not torch.isfinite(image).all():
            raise RuntimeError("The VAE returned invalid numbers.")
        image = image.clamp(-1, 1)
        image = (image / 2 + 0.5).clamp(0, 1).mul(255).byte().permute(1, 2, 0).numpy()
        return Image.fromarray(image)

    def _latent_preview(self, latents):
        import torch
        from PIL import Image

        sample = latents.detach()
        if sample.shape[0] > 1:
            sample = sample[-1:]
        take = min(3, int(sample.shape[1]))
        rgb = sample[0, :take].float().cpu()
        if take < 3:
            rgb = torch.cat([rgb, rgb[: 3 - take]], dim=0)
        low = rgb.amin(dim=(1, 2), keepdim=True)
        peak = (rgb.amax(dim=(1, 2), keepdim=True) - low).clamp(min=1e-6)
        rgb = ((rgb - low) / peak).clamp(0, 1)
        array = (rgb * 255).byte().permute(1, 2, 0).numpy()
        image = Image.fromarray(array)
        return image.resize((array.shape[1] * 8, array.shape[0] * 8), Image.Resampling.NEAREST)

    def _on_step(self, _pipe, step_index, _timestep, callback_kwargs, total):
        latents = callback_kwargs.get("latents")
        if latents is not None:
            try:
                image = self._latent_preview(latents)
                caption = f"Step {step_index + 1} / {total}"
                hook = self.__dict__.get("on_preview")
                if hook is not None:
                    hook(image, caption)
            except Exception:
                pass
        return callback_kwargs

    def _restore(self) -> None:
        data = load_config()
        if isinstance(data.get("roots"), dict):
            self._roots = {key: value for key, value in data["roots"].items() if isinstance(key, str) and isinstance(value, str)}
        if isinstance(data.get("lora_dir"), str):
            self._lora_dir = data["lora_dir"]
        if isinstance(data.get("anima_lora_dir"), str):
            self._anima_lora_dir = data["anima_lora_dir"]
        self._models = [item for item in data.get("models", []) if isinstance(item, str)]
        self.model_box["values"] = self._models
        selected = data.get("model", "")
        if selected in self._models:
            self.model_box.set(selected)
        elif self._models:
            self.model_box.current(0)
        if data.get("output"):
            self.output.set(data["output"])
        if data.get("clip"):
            self.clip.set(data["clip"])
        if data.get("clip_g"):
            self.clip_g.set(data["clip_g"])
        if data.get("vae"):
            self.vae_path.set(data["vae"])
        if "vae_tile" in data:
            self.vae_tile.set(bool(data["vae_tile"]))
        if "eye_fix" in data:
            self.eye_fix.set(bool(data["eye_fix"]))
        if isinstance(data.get("eye_model"), str):
            self.eye_model.set(data["eye_model"])
        if isinstance(data.get("eye_prompt"), str) and data["eye_prompt"]:
            self.eye_prompt.set(data["eye_prompt"])
        for key, var in (
            ("vae_tile_size", self.vae_tile_size),
            ("vae_tile_overlap", self.vae_tile_overlap),
        ):
            if key in data:
                try:
                    var.set(int(data[key]))
                except (tk.TclError, TypeError, ValueError):
                    pass
        for key, var in (("eye_denoise", self.eye_denoise), ("eye_conf", self.eye_conf)):
            if key in data:
                try:
                    var.set(float(data[key]))
                except (tk.TclError, TypeError, ValueError):
                    pass
        if data.get("prompt"):
            self.prompt.insert("1.0", data["prompt"])
        if data.get("negative"):
            self.negative.insert("1.0", data["negative"])
        for key, var in (("steps", self.steps), ("cfg", self.cfg), ("width", self.width), ("height", self.height), ("batch", self.batch)):
            if key in data:
                try:
                    var.set(data[key])
                except (tk.TclError, ValueError):
                    pass
        if data.get("seed") is not None:
            self.seed.set(str(data.get("seed", "")))
        self._prompts = [item for item in data.get("prompts", []) if isinstance(item, dict) and item.get("text")]
        self._refresh_prompts()
        for item in data.get("loras", []):
            if isinstance(item, dict):
                self._add_lora(
                    item.get("path", ""),
                    float(item.get("weight", 0.8)),
                    item.get("triggers", "") if isinstance(item.get("triggers"), str) else "",
                    item.get("thumb", "") if isinstance(item.get("thumb"), str) else "",
                )
        self.prompt.event_generate("<<Modified>>")
        self.negative.event_generate("<<Modified>>")
        train = data.get("train")
        if isinstance(train, dict):
            if isinstance(train.get("folder"), str):
                self.train_folder.set(train["folder"])
            if isinstance(train.get("trigger"), str):
                self.train_trigger.set(train["trigger"])
            if isinstance(train.get("name"), str) and train["name"]:
                self.train_name.set(train["name"])
            if train.get("subject") in {"character", "style", "concept"}:
                self.train_subject.set(train["subject"])
                self._apply_train_preset()
            for key, var in (
                ("rank", self.train_rank),
                ("alpha", self.train_alpha),
                ("steps", self.train_steps),
                ("resolution", self.train_res),
            ):
                if key in train:
                    try:
                        var.set(int(train[key]))
                    except (tk.TclError, TypeError, ValueError):
                        pass
            if isinstance(train.get("lr"), str):
                self.train_lr.set(train["lr"])
            for key, var in (
                ("buckets", self.train_buckets),
                ("checkpoint", self.train_checkpoint),
                ("cache_latents", self.train_cache),
                ("no_half_vae", self.train_no_half),
            ):
                if key in train:
                    var.set(bool(train[key]))
        anima_train = data.get("anima_train")
        if isinstance(anima_train, dict) and hasattr(self, "anima_train_folder"):
            if isinstance(anima_train.get("folder"), str):
                self.anima_train_folder.set(anima_train["folder"])
            if isinstance(anima_train.get("trigger"), str):
                self.anima_train_trigger.set(anima_train["trigger"])
            if isinstance(anima_train.get("name"), str) and anima_train["name"]:
                self.anima_train_name.set(anima_train["name"])
            if anima_train.get("subject") in {"character", "style", "concept"}:
                self.anima_train_subject.set(anima_train["subject"])
                self._apply_anima_train_preset()
            for key, var in (
                ("rank", self.anima_train_rank),
                ("alpha", self.anima_train_alpha),
                ("steps", self.anima_train_steps),
                ("resolution", self.anima_train_res),
            ):
                if key in anima_train:
                    try:
                        var.set(int(anima_train[key]))
                    except (tk.TclError, TypeError, ValueError):
                        pass
            if isinstance(anima_train.get("lr"), str):
                self.anima_train_lr.set(anima_train["lr"])
            for key, var in (
                ("buckets", self.anima_train_buckets),
                ("checkpoint", self.anima_train_checkpoint),
                ("cache_latents", self.anima_train_cache),
                ("fp32_vae", self.anima_train_fp32_vae),
            ):
                if key in anima_train:
                    var.set(bool(anima_train[key]))
        captions = data.get("captions")
        if isinstance(captions, dict):
            if isinstance(captions.get("url"), str) and captions["url"]:
                self.kobold_url.set(captions["url"])
            if isinstance(captions.get("key"), str):
                self.kobold_key.set(captions["key"])
            if isinstance(captions.get("trigger"), str):
                self.caption_trigger.set(captions["trigger"])
            if isinstance(captions.get("dest"), str):
                self.caption_dest.set(captions["dest"])
            if captions.get("subject") in CAPTION_PROMPTS:
                self.caption_subject.set(captions["subject"])
            if isinstance(captions.get("instruction"), str) and captions["instruction"]:
                self.caption_prompt.delete("1.0", "end")
                self.caption_prompt.insert("1.0", captions["instruction"])
            if "copy" in captions:
                self.caption_copy.set(bool(captions["copy"]))
            if "skip" in captions:
                self.caption_skip.set(bool(captions["skip"]))
            if isinstance(captions.get("engine"), str) and captions["engine"] in ("kobold", "clip", "joy"):
                self.caption_engine.set(captions["engine"])
            if isinstance(captions.get("vision"), str):
                self.clip_vision.set(captions["vision"])
            if isinstance(captions.get("vision_text"), str):
                self.clip_vision_text.set(captions["vision_text"])
            if isinstance(captions.get("joy_model"), str):
                self.joy_model.set(captions["joy_model"])
            if isinstance(captions.get("joy_mmproj"), str):
                self.joy_mmproj.set(captions["joy_mmproj"])
            self._sync_caption_engine()
            for path in captions.get("files") or []:
                if isinstance(path, str) and Path(path).is_file():
                    self._remember_caption_file(path)
        if isinstance(data.get("init_image"), str):
            self.init_image.set(data["init_image"])
            self._show_init_preview()
        if data.get("init_denoise") is not None:
            try:
                self.init_denoise.set(float(data["init_denoise"]))
            except (TypeError, ValueError, tk.TclError):
                pass
        if data.get("init_reader") in ("off", "clip", "joy"):
            self.init_reader.set(data["init_reader"])
        if "init_read" in data:
            self.init_read.set(bool(data["init_read"]))

        if isinstance(data.get("library"), str) and data["library"]:
            self.library_folder.set(data["library"])
        elif self.output.get().strip():
            self.library_folder.set(self.output.get().strip())
        if "library_sub" in data:
            self.library_sub.set(bool(data["library_sub"]))
        if isinstance(data.get("vangard_sdk"), str) and hasattr(self, "vangard_sdk"):
            self.vangard_sdk.set(data["vangard_sdk"])
        if isinstance(data.get("vangard_project"), str) and hasattr(self, "vangard_project"):
            self.vangard_project.set(data["vangard_project"])
        anima_state = data.get("anima")
        if isinstance(anima_state, dict) and hasattr(self, "anima_model"):
            self._restore_anima(anima_state)
        if isinstance(data.get("theme"), dict) and hasattr(self, "_theme_push"):
            self._theme_push(data["theme"])
        self.after(300, self._refresh_library)
        self.after(500, self._refresh_anima_picks)
        self.after(800, lambda: self._publish_redwright_link(announce=False))
        self.after(400, self._ensure_anima_files)

    def _publish_redwright_link(self, announce: bool = True) -> None:
        import cardwright

        novel = getattr(self, "_novel_folder_value", None)
        novel_path = novel.get().strip() if novel is not None else ""
        try:
            dest = cardwright.publish_link(
                Path(__file__).resolve().parent,
                self.library_folder.get().strip(),
                bool(self.library_sub.get()) if hasattr(self, "library_sub") else False,
                novel_path,
            )
        except Exception as exc:
            if announce:
                self._say(f"Could not send resources to Vangard. {exc}")
            return
        if announce:
            self._say(f"Resources sent. In Vangard, click RedWright. Link: {dest}")

    def _snapshot(self) -> dict:
        return {
            "models": self._models,
            "model": self.model_box.get(),
            "clip": self.clip.get(),
            "clip_g": self.clip_g.get(),
            "vae": self.vae_path.get(),
            "vae_tile": bool(self.vae_tile.get()),
            "vae_tile_size": self.vae_tile_size.get(),
            "vae_tile_overlap": self.vae_tile_overlap.get(),
            "eye_fix": bool(self.eye_fix.get()),
            "eye_model": self.eye_model.get(),
            "eye_denoise": self.eye_denoise.get(),
            "eye_conf": self.eye_conf.get(),
            "eye_prompt": self.eye_prompt.get(),
            "init_image": self.init_image.get(),
            "init_denoise": self.init_denoise.get(),
            "init_reader": self.init_reader.get(),
            "init_read": bool(self.init_read.get()),
            "loras": [
                {
                    "path": path.get(),
                    "weight": weight.get(),
                    "triggers": block.triggers.get(),
                    "thumb": block.thumb_path,
                }
                for path, weight, block in self._loras
            ],
            "lora_dir": getattr(self, "_lora_dir", ""),
            "anima_lora_dir": getattr(self, "_anima_lora_dir", ""),
            "roots": self._roots_map(),
            "output": self.output.get(),
            "library": self.library_folder.get(),
            "library_sub": bool(self.library_sub.get()),
            "vangard_sdk": self.vangard_sdk.get(),
            "vangard_project": self.vangard_project.get(),
            "anima": {
                "model": self.anima_model.get(),
                "text": self.anima_text.get(),
                "vae": self.anima_vae.get(),
                "preset": self.anima_preset.get(),
                "steps": self.anima_steps.get(),
                "cfg": self.anima_cfg.get(),
                "shift": self.anima_shift.get(),
                "width": self.anima_width.get(),
                "height": self.anima_height.get(),
                "batch": self.anima_batch.get(),
                "seed": self.anima_seed.get(),
                "max_length": self.anima_max_length.get(),
                "output": self.anima_output.get(),
                "init": self.anima_init.get(),
                "denoise": self.anima_denoise.get(),
                "prompt": self.anima_prompt.get("1.0", "end").strip(),
                "negative": self.anima_negative.get("1.0", "end").strip(),
                "loras": [
                    {
                        "path": path.get(),
                        "weight": weight.get(),
                        "triggers": block.triggers.get() if hasattr(block, "triggers") else "",
                        "thumb": getattr(block, "thumb_path", ""),
                    }
                    for path, weight, block in self._anima_loras
                ],
            },
            "prompt": self.prompt.get("1.0", "end").strip(),
            "negative": self.negative.get("1.0", "end").strip(),
            "prompts": self._prompts,
            "steps": self.steps.get(),
            "cfg": self.cfg.get(),
            "width": self.width.get(),
            "height": self.height.get(),
            "batch": self.batch.get(),
            "seed": self.seed.get(),
            "train": {
                "folder": self.train_folder.get(),
                "trigger": self.train_trigger.get(),
                "name": self.train_name.get(),
                "rank": self.train_rank.get(),
                "alpha": self.train_alpha.get(),
                "lr": self.train_lr.get(),
                "steps": self.train_steps.get(),
                "resolution": self.train_res.get(),
                "subject": self.train_subject.get(),
                "buckets": self.train_buckets.get(),
                "checkpoint": self.train_checkpoint.get(),
                "cache_latents": self.train_cache.get(),
                "no_half_vae": self.train_no_half.get(),
            },
            "anima_train": {
                "folder": self.anima_train_folder.get(),
                "trigger": self.anima_train_trigger.get(),
                "name": self.anima_train_name.get(),
                "rank": self.anima_train_rank.get(),
                "alpha": self.anima_train_alpha.get(),
                "lr": self.anima_train_lr.get(),
                "steps": self.anima_train_steps.get(),
                "resolution": self.anima_train_res.get(),
                "subject": self.anima_train_subject.get(),
                "buckets": self.anima_train_buckets.get(),
                "checkpoint": self.anima_train_checkpoint.get(),
                "cache_latents": self.anima_train_cache.get(),
                "fp32_vae": self.anima_train_fp32_vae.get(),
            },
            "captions": {
                "url": self.kobold_url.get(),
                "key": self.kobold_key.get(),
                "trigger": self.caption_trigger.get(),
                "dest": self.caption_dest.get(),
                "subject": self.caption_subject.get(),
                "instruction": self.caption_prompt.get("1.0", "end").strip(),
                "copy": self.caption_copy.get(),
                "skip": self.caption_skip.get(),
                "engine": self.caption_engine.get(),
                "vision": self.clip_vision.get(),
                "vision_text": self.clip_vision_text.get(),
                "joy_model": self.joy_model.get(),
                "joy_mmproj": self.joy_mmproj.get(),
                "files": list(self._caption_files),
            },
            "theme": getattr(self, "_theme", DEFAULT_THEME),
        }

    def _on_close(self) -> None:
        self._kill_job()
        remember = getattr(self, "cards_remember", None)
        if remember:
            try:
                remember()
            except OSError:
                pass
        try:
            save_config(self._snapshot())
        except OSError as exc:
            messagebox.showerror(APP, f"Could not save settings.\n{exc}")
        self.destroy()

    def _remember_picture(self, path) -> None:
        self._last_picture = str(path)
        folder = self.library_folder.get().strip()
        if folder and Path(path).parent == Path(folder):
            self.after(200, self._refresh_library)

    def _say(self, text: str) -> None:
        self.status.configure(text=text)
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _add_model_file(self) -> None:
        options = {"title": "Model", "filetypes": [("Model", "*.safetensors *.ckpt"), ("All files", "*.*")]}
        initial = self._dialog_dir("models")
        if initial:
            options["initialdir"] = initial
        picked = filedialog.askopenfilename(**options)
        if picked:
            self._remember_root("models", str(Path(picked).parent))
            self._remember_model(picked)

    def _scan_folder(self) -> None:
        options = {"title": "Models folder"}
        initial = self._dialog_dir("models")
        if initial:
            options["initialdir"] = initial
        folder = filedialog.askdirectory(**options)
        if not folder:
            return
        self._remember_root("models", folder)
        found = 0
        root = Path(folder)
        for path in sorted(root.iterdir()):
            if path.suffix.lower() in {".safetensors", ".ckpt"} or (path / "model_index.json").exists():
                self._remember_model(str(path))
                found += 1
        self._say(f"Found {found} models in {folder}")

    def _remember_model(self, path: str) -> None:
        if path not in self._models:
            self._models.append(path)
        self.model_box["values"] = self._models
        self.model_box.set(path)

    def _remove_model(self) -> None:
        current = self.model_box.get()
        self._models = [item for item in self._models if item != current]
        self.model_box["values"] = self._models
        self.model_box.set(self._models[0] if self._models else "")

    def _watch_words(self, widget: tk.Text, label: tk.Label) -> None:
        def changed(_event=None) -> None:
            widget.edit_modified(False)
            text = widget.get("1.0", "end").strip()
            count = 0 if not text else len(text.split())
            label.configure(text=f"{count} word" if count == 1 else f"{count} words")

        widget.bind("<<Modified>>", changed)
        changed()

    def _add_lora(self, path: str = "", weight: float = 0.8, triggers: str = "", thumb: str = "") -> None:
        block = ttk.Frame(self.lora_host, style="Card.TFrame")
        block.pack(fill="x", pady=4)
        row = ttk.Frame(block, style="Card.TFrame")
        row.pack(fill="x")
        path_var = tk.StringVar(value=path)
        weight_var = tk.DoubleVar(value=weight)
        tk.Entry(row, textvariable=path_var, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=4
        )

        def browse() -> None:
            picked = self._pick_lora_file("LoRA", path_var.get(), "sd")
            if picked:
                path_var.set(picked)
                self._apply_lora_file(block)

        ttk.Button(row, text="File", command=browse).pack(side="left", padx=4)
        tk.Entry(row, textvariable=weight_var, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", ipady=4
        )
        ttk.Button(row, text="Civitai", command=lambda: self._fetch_civitai(block)).pack(side="left", padx=4)

        def remove() -> None:
            self._loras = [item for item in self._loras if item[2] is not block]
            block.destroy()

        ttk.Button(row, text="Remove", command=remove).pack(side="left")

        info = ttk.Frame(block, style="Card.TFrame")
        info.pack(fill="x", pady=(4, 0))
        thumb_label = tk.Label(info, text="", bg=BG, width=12, height=5)
        thumb_label.pack(side="left")
        triggers_var = tk.StringVar(value=triggers)
        tk.Entry(info, textvariable=triggers_var, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=4, padx=6
        )
        ttk.Button(info, text="Use", command=lambda: self._use_triggers(triggers_var)).pack(side="left")
        block.path_var = path_var
        block.triggers = triggers_var
        block.thumb_label = thumb_label
        block.thumb_path = thumb if thumb and Path(thumb).is_file() else ""
        block.thumb_photo = None
        if block.thumb_path:
            self._show_thumb(block, block.thumb_path)
        if path and not triggers.strip() and Path(path).is_file():
            found = _local_triggers(Path(path))
            if found:
                triggers_var.set(found)
        self._loras.append((path_var, weight_var, block))

        def lora_menu(event, this=block, drop=remove, words=triggers_var) -> str:
            def copy_words() -> None:
                self._copy_text(words.get())

            return self._popup(event, [("Use trigger words", lambda: self._use_triggers(words)), ("Copy trigger words", copy_words), ("", None), ("Remove", drop)])

        self._bind_tree(block, "<Button-3>", lora_menu)

    def _bind_tree(self, widget, sequence: str, handler) -> None:
        widget.bind(sequence, handler)
        for child in widget.winfo_children():
            self._bind_tree(child, sequence, handler)

    def _use_triggers(self, variable: tk.StringVar) -> None:
        text = variable.get().strip()
        if not text or text.startswith("No trigger") or text.startswith("Civitai"):
            self._say("No trigger words to add.")
            return
        current = self.prompt.get("1.0", "end").strip()
        self.prompt.delete("1.0", "end")
        self.prompt.insert("1.0", text if not current else f"{text}, {current}")

    def _show_thumb(self, block, path: str) -> None:
        from PIL import Image, ImageTk

        image = Image.open(path).convert("RGB")
        image.thumbnail((96, 96))
        photo = ImageTk.PhotoImage(image)
        block.thumb_photo = photo
        block.thumb_label.configure(image=photo, text="", width=0, height=0)
        block.thumb_path = path

    def _pick_lora_file(self, title: str, current: str, kind: str) -> str:
        root_key = "anima_loras" if kind == "anima" else "loras"
        initial = self._dialog_dir(root_key, current)
        if not initial:
            saved = getattr(self, "_anima_lora_dir" if kind == "anima" else "_lora_dir", "")
            if isinstance(saved, str) and Path(saved).is_dir():
                initial = saved
        options = {"title": title, "filetypes": [("LoRA", "*.safetensors"), ("All files", "*.*")]}
        if initial:
            options["initialdir"] = initial
        picked = filedialog.askopenfilename(**options)
        if picked:
            folder = str(Path(picked).parent)
            self._remember_root(root_key, folder)
            if kind == "anima":
                self._anima_lora_dir = folder
            else:
                self._lora_dir = folder
        return picked

    def _apply_lora_file(self, block) -> None:
        path = block.path_var.get().strip()
        report = getattr(block, "report", self._say)
        file_path = Path(path) if path else None
        local = _local_triggers(file_path) if file_path and file_path.is_file() else ""
        info = _local_lora_info(file_path) if file_path and file_path.is_file() else ""
        label = getattr(block, "info_label", None)
        if label is not None:
            label.configure(text=info)
        thumb = _local_thumb(file_path) if file_path and file_path.is_file() else ""
        if thumb:
            self._show_thumb(block, thumb)
        if local:
            block.triggers.set(local)
            report(f"Trigger words from the file: {local}")
        else:
            report("No trigger words in that file. Asking Civitai.")
        self._fetch_civitai(block)

    def _fetch_civitai(self, block) -> None:
        path = block.path_var.get().strip()
        if not path or not Path(path).is_file():
            self._say("Pick a LoRA file before asking Civitai.")
            return
        local = _local_triggers(Path(path))
        current = block.triggers.get().strip()
        report = getattr(block, "report", self._say)
        if local and (not current or current.startswith("Asking") or current.startswith("No trigger") or current.startswith("Civitai")):
            block.triggers.set(local)
        elif not current:
            block.triggers.set("Asking Civitai…")
        report("Asking Civitai…")
        threading.Thread(target=self._civitai_worker, args=(path, block, local), daemon=True).start()

    def _civitai_worker(self, path: str, block, local: str = "") -> None:
        import hashlib
        import json
        import urllib.error
        import urllib.request

        try:
            digest = hashlib.sha256()
            with open(path, "rb") as handle:
                while True:
                    chunk = handle.read(1 << 20)
                    if not chunk:
                        break
                    digest.update(chunk)
            sha = digest.hexdigest()
            request = urllib.request.Request(
                f"https://civitai.com/api/v1/model-versions/by-hash/{sha}",
                headers={"User-Agent": "RedGen"},
            )
            with urllib.request.urlopen(request, timeout=40) as response:
                payload = json.loads(response.read().decode("utf-8"))
            words = [item.strip() for item in payload.get("trainedWords") or [] if isinstance(item, str) and item.strip()]
            images = [item for item in payload.get("images") or [] if isinstance(item, dict) and item.get("url")]
            images.sort(key=lambda item: item.get("nsfwLevel") or 1)
            image_url = ""
            for image in images:
                image_url = image["url"]
                if (image.get("nsfwLevel") or 1) <= 2:
                    break
            model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
            title = " · ".join(part for part in (model.get("name", ""), payload.get("name", "")) if part)
            thumb = ""
            if image_url:
                picture = urllib.request.Request(image_url, headers={"User-Agent": "RedGen"})
                with urllib.request.urlopen(picture, timeout=40) as response:
                    raw = response.read()
                folder = CONFIG.parent / "thumbs"
                folder.mkdir(parents=True, exist_ok=True)
                dest = folder / f"{sha[:16]}.png"
                from PIL import Image
                import io

                Image.open(io.BytesIO(raw)).convert("RGB").save(dest, "PNG")
                thumb = str(dest)

            def apply() -> None:
                try:
                    if not block.winfo_exists():
                        return
                except tk.TclError:
                    return
                block.triggers.set(_merge_trigger_text(", ".join(words), local) or "No trigger words in the file or on Civitai.")
                if thumb:
                    self._show_thumb(block, thumb)
                label = getattr(block, "info_label", None)
                if label is not None:
                    remote = _civitai_blurb(payload)
                    current = label.cget("text").strip()
                    label.configure(text="\n".join(part for part in (remote, current) if part))
                getattr(block, "report", self._say)(f"Civitai: {title or Path(path).name}")

            self.after(0, apply)
        except urllib.error.HTTPError as exc:
            message = "Civitai does not have this file." if exc.code == 404 else f"Civitai returned {exc.code}."

            def fail_http() -> None:
                try:
                    if not block.winfo_exists():
                        return
                except tk.TclError:
                    return
                report = getattr(block, "report", self._say)
                if local:
                    block.triggers.set(local)
                    report(f"{message} Kept the trigger words from the file.")
                    return
                block.triggers.set("No trigger words in the file or on Civitai.")
                report(message)

            self.after(0, fail_http)
        except Exception as exc:
            detail = str(exc)

            def fail() -> None:
                try:
                    if not block.winfo_exists():
                        return
                except tk.TclError:
                    return
                report = getattr(block, "report", self._say)
                if local:
                    block.triggers.set(local)
                    report("Civitai lookup failed. Kept the trigger words from the file.")
                    return
                block.triggers.set("")
                report(f"Civitai lookup failed: {detail}")

            self.after(0, fail)

    def _clip_row(self, parent: ttk.Frame, variable: tk.StringVar, title: str, kind: str = "CLIP", root_key: str = "") -> None:
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        tk.Entry(row, textvariable=variable, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=6
        )

        def browse_file() -> None:
            options = {
                "title": title,
                "filetypes": [(kind, "*.safetensors;*.bin;*.pt;*.ckpt"), ("All files", "*.*")],
            }
            initial = self._dialog_dir(root_key, variable.get().strip()) if root_key else ""
            if initial:
                options["initialdir"] = initial
            picked = filedialog.askopenfilename(**options)
            if picked:
                variable.set(picked)
                if root_key:
                    self._remember_root(root_key, str(Path(picked).parent))

        def browse_folder() -> None:
            options = {"title": title}
            initial = self._dialog_dir(root_key, variable.get().strip()) if root_key else ""
            if initial:
                options["initialdir"] = initial
            picked = filedialog.askdirectory(**options)
            if picked:
                variable.set(picked)
                if root_key:
                    self._remember_root(root_key, picked)

        ttk.Button(row, text="File", command=browse_file).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="Folder", command=browse_folder).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="Clear", command=lambda: variable.set("")).pack(side="left", padx=(8, 0))

    def _file_line(self, parent, variable: tk.StringVar, title: str, pattern: str) -> None:
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x")
        tk.Entry(row, textvariable=variable, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=4
        )
        ttk.Button(row, text="File", command=lambda: self._pick_file(variable, title, pattern)).pack(side="left", padx=(8, 0))

    def _pick_init_image(self) -> None:
        picked = filedialog.askopenfilename(
            title="Source picture",
            filetypes=[("Pictures", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("All files", "*.*")],
        )
        if not picked:
            return
        self.init_image.set(picked)
        self._show_init_preview()

    def _clear_init_image(self) -> None:
        self.init_image.set("")
        self.init_preview.configure(image="", text="")
        self._init_photo = None

    def _show_init_preview(self) -> None:
        from PIL import Image, ImageTk

        path = self.init_image.get().strip()
        if not path or not Path(path).is_file():
            self.init_preview.configure(image="", text="")
            self._init_photo = None
            return
        try:
            image = Image.open(path).convert("RGB")
        except OSError:
            self.init_preview.configure(image="", text="That picture could not be opened.")
            return
        image.thumbnail((96, 96))
        self._init_photo = ImageTk.PhotoImage(image)
        self.init_preview.configure(image=self._init_photo, text="")

    def _init_reader_error(self) -> str:
        reader = self.init_reader.get()
        path = self.init_image.get().strip()
        if reader == "off":
            return ""
        if not path or not Path(path).is_file():
            return "Pick a source picture before reading it."
        if reader == "clip":
            vision = self.clip_vision.get().strip()
            text = self.clip_vision_text.get().strip()
            if not vision or not Path(vision).is_file():
                return "Pick a CLIP Vision file."
            if text and not Path(text).is_file():
                return "The CLIP text file could not be found."
        elif reader == "joy":
            model = self.joy_model.get().strip()
            mmproj = self.joy_mmproj.get().strip()
            if not model or not Path(model).is_file():
                return "Pick the JoyCaption Beta One GGUF."
            if not mmproj or not Path(mmproj).is_file():
                return "Pick the JoyCaption mmproj file."
        return ""

    def _caption_source(self, path: str) -> str:
        reader = self.init_reader.get()
        extras = self.prompt.get("1.0", "end").strip()
        if reader == "clip":
            text_path = self.clip_vision_text.get().strip()
            captioner = ClipCaptioner(Path(self.clip_vision.get().strip()), Path(text_path) if text_path else None)
            try:
                return captioner.caption(Path(path), extras)
            finally:
                captioner.close()
        instruction = "Write a detailed caption for this image in one line of comma-separated phrases."
        captioner = JoyCaptioner(Path(self.joy_model.get().strip()), Path(self.joy_mmproj.get().strip()), lambda _text: None)
        try:
            return captioner.caption(Path(path), instruction)
        finally:
            captioner.close()

    def _put_caption(self, text: str) -> None:
        text = " ".join(text.split())
        if not text:
            self._say("The reader returned an empty caption.")
            return
        current = self.prompt.get("1.0", "end").strip()
        if not current:
            self.prompt.delete("1.0", "end")
            self.prompt.insert("1.0", text)
        elif text.lower() not in current.lower():
            self.prompt.insert("1.0", text + ", ")
        self._say("The picture was read into the prompt.")

    def _read_init_image(self) -> None:
        self._read_init_then(None)

    def _read_init_then(self, after) -> None:
        if getattr(self, "_reading_init", False):
            self._say("Still reading the picture.")
            return
        problem = self._init_reader_error()
        if problem:
            self._say(problem)
            return
        path = self.init_image.get().strip()
        label = "JoyCaption" if self.init_reader.get() == "joy" else "CLIP Vision"
        self._reading_init = True
        self._say(f"Reading the picture with {label}…")

        def work() -> None:
            try:
                text = self._caption_source(path)
            except Exception as exc:
                detail = str(exc)
                self.after(0, lambda detail=detail: self._finish_read(f"Could not read the picture. {detail}", None))
                return
            self.after(0, lambda text=text: self._finish_read("", text, after))

        threading.Thread(target=work, daemon=True).start()

    def _finish_read(self, error: str, text: str | None = None, after=None) -> None:
        self._reading_init = False
        if error:
            self._say(error)
            return
        self._put_caption(text or "")
        if after is not None and self.prompt.get("1.0", "end").strip():
            after()

    def _pick_output(self) -> None:
        picked = filedialog.askdirectory(title="Save pictures in")
        if picked:
            self.output.set(picked)

    def _refresh_prompts(self) -> None:
        self.prompt_list.delete(0, "end")
        for item in self._prompts:
            self.prompt_list.insert("end", item.get("name") or "Untitled")

    def _save_prompt(self) -> None:
        text = self.prompt.get("1.0", "end").strip()
        negative = self.negative.get("1.0", "end").strip()
        name = self.prompt_name.get().strip() or text[:32]
        if len(text) < 2 or not name:
            self._say("Write a prompt, then give it a name.")
            return
        self._prompts = [item for item in self._prompts if item.get("name") != name]
        self._prompts.insert(0, {"name": name, "text": text, "negative": negative})
        self._prompts = self._prompts[:40]
        self.prompt_name.set("")
        self._refresh_prompts()
        self._say(f"Saved prompt “{name}”.")

    def _load_prompt(self, _event: object) -> None:
        selection = self.prompt_list.curselection()
        if not selection:
            return
        item = self._prompts[selection[0]]
        self.prompt.delete("1.0", "end")
        self.prompt.insert("1.0", item["text"])
        self.negative.delete("1.0", "end")
        self.negative.insert("1.0", item.get("negative") or "")

    def _delete_prompt(self) -> None:
        selection = self.prompt_list.curselection()
        if not selection:
            return
        del self._prompts[selection[0]]
        self._refresh_prompts()

    def _show_queue(self) -> None:
        waiting = len(self.hold.queue)
        self.queue_count.configure(text=f"Queue {waiting}")
        label = getattr(self, "anima_queue", None)
        if label is not None:
            label.configure(text=f"Queue {waiting}")

    def _collect_job(self, override: dict | None = None) -> dict | None:
        override = override or {}
        if sys.platform != "win32":
            self._say("Generate needs Windows 11 with an AMD driver. This copy is the local app, not a browser.")
            return None
        model = self.model_box.get().strip()
        prompt = override["prompt"].strip() if isinstance(override.get("prompt"), str) else self.prompt.get("1.0", "end").strip()
        negative = self.negative.get("1.0", "end").strip()
        folder = override["folder"].strip() if isinstance(override.get("folder"), str) else self.output.get().strip()
        clip = self.clip.get().strip()
        clip_g = self.clip_g.get().strip()
        vae = self.vae_path.get().strip()
        if len(prompt) < 2:
            self._say("Write a prompt first.")
            return None
        source = "" if override.get("skip_init") else self.init_image.get().strip()
        denoise = 0.55
        if source:
            if not Path(source).is_file():
                self._say("The source picture could not be found.")
                return None
            try:
                denoise = float(self.init_denoise.get())
            except (tk.TclError, ValueError):
                self._say("Image denoise must be a number.")
                return None
            if not 0.05 <= denoise <= 1:
                self._say("Image denoise needs to be between 0.05 and 1.")
                return None
        if not model or not Path(model).exists():
            self._say("Pick a model file that exists on this PC.")
            return None
        if not folder:
            self._say("Set a folder for the pictures.")
            return None
        if clip and not Path(clip).exists():
            self._say(f"CLIP not found: {clip}")
            return None
        if clip_g and not Path(clip_g).exists():
            self._say(f"CLIP-G not found: {clip_g}")
            return None
        if vae and not Path(vae).exists():
            self._say(f"VAE not found: {vae}")
            return None
        try:
            self._vae_tile_values()
            denoise = float(self.eye_denoise.get())
            conf = float(self.eye_conf.get())
        except (tk.TclError, ValueError):
            self._say("VAE tile, eye denoise, and confidence must be numbers.")
            return None
        if self.eye_fix.get() and not 0.15 <= denoise <= 0.9:
            self._say("Eye denoise needs to be between 0.15 and 0.9.")
            return None
        if self.eye_fix.get() and not 0.05 <= conf <= 0.95:
            self._say("Eye confidence needs to be between 0.05 and 0.95.")
            return None
        loras = []
        for path_var, weight_var, _row in self._loras:
            path = path_var.get().strip()
            if not path:
                self._say("Every LoRA row needs a file, or remove the empty row.")
                return None
            if not Path(path).exists():
                self._say(f"LoRA not found: {path}")
                return None
            loras.append((path, float(weight_var.get())))
        try:
            steps = max(1, min(60, int(self.steps.get())))
            cfg = float(self.cfg.get())
            width = snap_dim(int(self.width.get()))
            height = snap_dim(int(self.height.get()))
            count = override.get("count") if isinstance(override.get("count"), int) else max(1, min(100, int(self.batch.get())))
        except (tk.TclError, ValueError):
            self._say("Steps, CFG, width, height, and batch count must be numbers.")
            return None
        seed_text = self.seed.get().strip()
        seed = None
        if seed_text:
            try:
                seed = int(seed_text)
            except ValueError:
                self._say("Seed must be a whole number, or left blank.")
                return None
        return {
            "model": model,
            "prompt": prompt,
            "negative": negative,
            "folder": folder,
            "loras": loras,
            "steps": steps,
            "cfg": cfg,
            "width": width,
            "height": height,
            "count": count,
            "seed": seed,
            "clip": clip,
            "clip_g": clip_g,
            "vae": vae,
            "init_image": source if source and Path(source).is_file() else "",
            "init_denoise": denoise if source else 1.0,
            "vn_hook": override.get("vn_hook"),
        }

    def _generate(self, for_card: bool = False) -> None:
        source = self.init_image.get().strip()
        if (
            not self.hold.busy
            and source
            and Path(source).is_file()
            and self.init_reader.get() in ("clip", "joy")
            and bool(self.init_read.get())
        ):
            self._read_init_then(lambda: self._queue_generation(for_card))
            return
        self._queue_generation(for_card)

    def _queue_generation(self, for_card: bool = False) -> None:
        job = self._collect_job()
        if job is None:
            return
        job["for_card"] = for_card
        if self.hold.busy:
            self.hold.queue.append(job)
            self._show_queue()
            short = job["prompt"].split("\n", 1)[0][:60]
            self._say(f"Queued “{short}”. {len(self.hold.queue)} waiting.")
            return
        self._start_job(job)

    def _build_anima(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        left_host = ttk.Frame(parent, style="TFrame")
        left_host.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left = self._make_scroller(left_host, bg=SURFACE, width=400, style="Card.TFrame")
        right = ttk.Frame(parent, style="TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        settings_host = ttk.Frame(right, style="TFrame")
        settings_host.grid(row=0, column=0, sticky="nsew")
        settings = self._make_scroller(settings_host, bg=BG)

        ttk.Label(left, text="Prompt", style="Card.TLabel").pack(anchor="w")
        self.anima_prompt = tk.Text(left, height=8, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word")
        self.anima_prompt.pack(fill="x", pady=(4, 0))
        self.anima_prompt_count = tk.Label(left, text="0 words", bg=SURFACE, fg=MUTED, font=("Segoe UI", 9))
        self.anima_prompt_count.pack(anchor="w", pady=(2, 4))
        self._watch_words(self.anima_prompt, self.anima_prompt_count)
        ttk.Label(left, text="Negative", style="Card.TLabel").pack(anchor="w")
        self.anima_negative = tk.Text(left, height=4, bg=INSET, fg=FG, insertbackground=FG, relief="flat", wrap="word")
        self.anima_negative.pack(fill="x", pady=(4, 0))
        ttk.Label(
            left,
            text="Danbooru tags, a sentence, or both. Aesthetic does not need score tags. Turbo ignores the negative because CFG is 1.",
            style="Muted.TLabel",
            wraplength=360,
        ).pack(anchor="w", pady=(4, 8))

        grid = ttk.Frame(left, style="Card.TFrame")
        grid.pack(fill="x")
        self.anima_steps = tk.IntVar(value=30)
        self.anima_cfg = tk.DoubleVar(value=4)
        self.anima_shift = tk.DoubleVar(value=3)
        self.anima_width = tk.IntVar(value=1024)
        self.anima_height = tk.IntVar(value=1024)
        self.anima_batch = tk.IntVar(value=1)
        self.anima_seed = tk.StringVar()
        self.anima_max_length = tk.IntVar(value=512)
        for col, (label, var) in enumerate(
            (("Steps", self.anima_steps), ("CFG", self.anima_cfg), ("Shift", self.anima_shift), ("Length", self.anima_max_length))
        ):
            box = ttk.Frame(grid, style="Card.TFrame")
            box.grid(row=0, column=col, padx=4, sticky="ew")
            ttk.Label(box, text=label, style="Muted.TLabel").pack(anchor="w")
            tk.Entry(box, textvariable=var, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(ipady=4)
        for col, (label, var) in enumerate((("Width", self.anima_width), ("Height", self.anima_height), ("Batch", self.anima_batch))):
            box = ttk.Frame(grid, style="Card.TFrame")
            box.grid(row=1, column=col, padx=4, pady=(8, 0), sticky="ew")
            ttk.Label(box, text=label, style="Muted.TLabel").pack(anchor="w")
            tk.Entry(box, textvariable=var, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(ipady=4)
        ttk.Label(left, text="Seed, blank is random", style="Muted.TLabel").pack(anchor="w", pady=(8, 0))
        tk.Entry(left, textvariable=self.anima_seed, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", ipady=4)
        preset_row = ttk.Frame(left, style="Card.TFrame")
        preset_row.pack(fill="x", pady=(8, 0))
        ttk.Label(preset_row, text="Preset", style="Muted.TLabel").pack(side="left")
        self.anima_preset = tk.StringVar(value="Base")
        preset = ttk.Combobox(preset_row, textvariable=self.anima_preset, state="readonly", width=12, values=("Base", "Aesthetic", "Turbo"))
        preset.pack(side="left", padx=(8, 0))
        preset.bind("<<ComboboxSelected>>", self._apply_anima_preset)
        ttk.Label(left, text="Width and height snap to 32, from 512 to 1536. Shift 3 is the Anima default.", style="Muted.TLabel", wraplength=360).pack(anchor="w", pady=(6, 8))
        ttk.Label(left, text="Model from the Anima folder", style="Card.TLabel").pack(anchor="w")
        model_pick_row = ttk.Frame(left, style="Card.TFrame")
        model_pick_row.pack(fill="x", pady=(2, 4))
        self.anima_model_pick = ttk.Combobox(model_pick_row, state="readonly")
        self.anima_model_pick.pack(side="left", fill="x", expand=True)
        self.anima_model_pick.bind("<<ComboboxSelected>>", self._choose_anima_model_pick)
        ttk.Button(model_pick_row, text="Refresh", command=self._refresh_anima_picks).pack(side="left", padx=(8, 0))
        ttk.Label(left, text="LoRA from the Anima LoRA folder", style="Muted.TLabel").pack(anchor="w", pady=(4, 0))
        lora_pick_row = ttk.Frame(left, style="Card.TFrame")
        lora_pick_row.pack(fill="x", pady=(2, 8))
        self.anima_lora_pick = ttk.Combobox(lora_pick_row, state="readonly")
        self.anima_lora_pick.pack(side="left", fill="x", expand=True)
        self.anima_lora_pick.bind("<<ComboboxSelected>>", self._choose_anima_lora_pick)
        self._anima_model_files: list[str] = []
        self._anima_lora_files: list[str] = []
        row = ttk.Frame(left, style="Card.TFrame")
        row.pack(fill="x", pady=(8, 4))
        ttk.Button(row, text="Generate", style="Primary.TButton", command=self._generate_anima).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Stop", command=self._stop_generation).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="Unload", command=self._unload_model).pack(side="left", padx=(8, 0))
        keep_anima = ttk.Button(row, text=self._keep_label(), command=self._toggle_keep_loaded)
        keep_anima.pack(side="left", padx=(8, 0))
        self._keep_buttons.append(keep_anima)
        self.anima_queue = tk.Label(row, text="Queue 0", bg=SURFACE, fg=FG, font=("Segoe UI", 10, "bold"))
        self.anima_queue.pack(side="left", padx=(8, 0))
        self.anima_status = tk.Label(left, text="Idle", bg=SURFACE, fg=MUTED, wraplength=360, justify="left")
        self.anima_status.pack(anchor="w")

        model_card = ttk.Frame(settings, style="Card.TFrame", padding=12)
        model_card.pack(fill="x", pady=(0, 8))
        ttk.Label(model_card, text="Anima model", style="Card.TLabel").pack(anchor="w")
        ttk.Label(
            model_card,
            text="The DiT file, such as anima-base or anima-turbo, or a diffusers folder. A single file also needs the two rows below. 2.9B and 3.8B merges are loaded from their block count.",
            style="Muted.TLabel",
            wraplength=520,
        ).pack(anchor="w", pady=(2, 4))
        self.anima_model = tk.StringVar()
        self._clip_row(model_card, self.anima_model, "Anima model", "Model", "anima_models")
        ttk.Label(model_card, text="Qwen3 0.6B text encoder", style="Muted.TLabel").pack(anchor="w", pady=(8, 2))
        ttk.Label(
            model_card,
            text="If this is empty, it downloads into the app folder and is filled in here.",
            style="Muted.TLabel",
            wraplength=520,
        ).pack(anchor="w")
        self.anima_text = tk.StringVar()
        self._clip_row(model_card, self.anima_text, "Qwen3 text encoder", "Text encoder", "clip")
        ttk.Label(model_card, text="Qwen-Image VAE", style="Muted.TLabel").pack(anchor="w", pady=(8, 2))
        ttk.Label(
            model_card,
            text="If this is empty, it downloads into the app folder and is filled in here.",
            style="Muted.TLabel",
            wraplength=520,
        ).pack(anchor="w")
        self.anima_vae = tk.StringVar()
        self._clip_row(model_card, self.anima_vae, "Qwen-Image VAE", "VAE", "vae")

        lora_card = ttk.Frame(settings, style="Card.TFrame", padding=12)
        lora_card.pack(fill="x", pady=(0, 8))
        ttk.Label(lora_card, text="Anima LoRAs", style="Card.TLabel").pack(anchor="w")
        ttk.Label(lora_card, text="These only work on Anima. Picking a file reads its trigger words and picture, then asks Civitai.", style="Muted.TLabel", wraplength=520).pack(anchor="w", pady=(2, 4))
        self.anima_lora_host = ttk.Frame(lora_card, style="Card.TFrame")
        self.anima_lora_host.pack(fill="x")
        self._anima_loras = []
        ttk.Button(lora_card, text="Add LoRA", command=lambda: self._add_anima_lora()).pack(anchor="w", pady=(4, 0))

        image_card = ttk.Frame(settings, style="Card.TFrame", padding=12)
        image_card.pack(fill="x", pady=(0, 8))
        ttk.Label(image_card, text="Image to image", style="Card.TLabel").pack(anchor="w")
        ttk.Label(image_card, text="Denoise is how much of the source picture changes.", style="Muted.TLabel", wraplength=520).pack(anchor="w", pady=(2, 4))
        self.anima_init = tk.StringVar()
        self.anima_denoise = tk.DoubleVar(value=0.6)
        init_row = ttk.Frame(image_card, style="Card.TFrame")
        init_row.pack(fill="x")
        tk.Entry(init_row, textvariable=self.anima_init, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, ipady=4)
        ttk.Button(init_row, text="Browse", command=self._pick_anima_init).pack(side="left", padx=(8, 0))
        ttk.Button(init_row, text="Clear", command=lambda: self.anima_init.set("")).pack(side="left", padx=(8, 0))
        denoise_row = ttk.Frame(image_card, style="Card.TFrame")
        denoise_row.pack(fill="x", pady=(6, 0))
        ttk.Label(denoise_row, text="Denoise", style="Muted.TLabel").pack(side="left")
        tk.Entry(denoise_row, textvariable=self.anima_denoise, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(side="left", padx=(4, 0), ipady=4)

        out_card = ttk.Frame(settings, style="Card.TFrame", padding=12)
        out_card.pack(fill="x")
        ttk.Label(out_card, text="Image save location", style="Card.TLabel").pack(anchor="w")
        ttk.Label(out_card, text="Point this at the Generate library folder if you want the pictures in that grid.", style="Muted.TLabel", wraplength=520).pack(anchor="w", pady=(2, 4))
        out_row = ttk.Frame(out_card, style="Card.TFrame")
        out_row.pack(fill="x")
        self.anima_output = tk.StringVar(value=str(Path.home() / "Pictures" / "RedWright" / "Anima"))
        tk.Entry(out_row, textvariable=self.anima_output, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, ipady=6)
        ttk.Button(out_row, text="Browse", command=self._pick_anima_output).pack(side="left", padx=(8, 0))

        view = ttk.Frame(right, style="Card.TFrame", padding=12)
        view.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        self.anima_caption = tk.Label(view, text="No picture yet", bg=SURFACE, fg=FG, font=("Segoe UI", 10))
        self.anima_caption.pack(anchor="w")
        self.anima_progress = ttk.Progressbar(view, style="Red.Horizontal.TProgressbar", maximum=100)
        self.anima_progress.pack(fill="x", pady=(6, 0))
        self.anima_viewport = tk.Canvas(view, bg=BG, highlightthickness=0, height=320, cursor="hand2")
        self.anima_viewport.pack(fill="both", expand=True, pady=(6, 0))
        self.anima_viewport.bind("<Button-1>", self._click_anima)
        self.anima_log = tk.Text(right, height=5, bg=INSET, fg=FG, relief="flat", wrap="word", state="disabled")
        self.anima_log.grid(row=2, column=0, sticky="ew")

    def _apply_anima_preset(self, _event=None) -> None:
        steps, cfg = __import__("anima").preset_values(self.anima_preset.get())
        self.anima_steps.set(steps)
        self.anima_cfg.set(cfg)

    def _weight_files(self, folder: str) -> list[str]:
        root = Path(folder) if folder else None
        if root is None or not root.is_dir():
            return []
        found = []
        for path in sorted(root.iterdir()):
            if path.suffix.lower() in {".safetensors", ".ckpt", ".pt", ".bin"} or (path / "model_index.json").exists():
                found.append(str(path))
        return found

    def _refresh_anima_picks(self) -> None:
        if not hasattr(self, "anima_model_pick"):
            return
        models = self._weight_files(self._dialog_dir("anima_models"))
        loras = self._weight_files(self._dialog_dir("anima_loras") or getattr(self, "_anima_lora_dir", ""))
        self._anima_model_files = models
        self._anima_lora_files = loras
        self.anima_model_pick["values"] = [Path(path).name for path in models]
        self.anima_lora_pick["values"] = [Path(path).name for path in loras]
        current = self.anima_model.get().strip() if hasattr(self, "anima_model") else ""
        if current in models:
            self.anima_model_pick.set(Path(current).name)
        elif not models:
            self.anima_model_pick.set("")

    def _choose_anima_model_pick(self, _event=None) -> None:
        name = self.anima_model_pick.get()
        for path in self._anima_model_files:
            if Path(path).name == name:
                self.anima_model.set(path)
                self._anima_say(f"Anima model is {name}. Unload first if another model is still on the card.")
                return

    def _choose_anima_lora_pick(self, _event=None) -> None:
        name = self.anima_lora_pick.get()
        for path in self._anima_lora_files:
            if Path(path).name != name:
                continue
            if self._anima_loras:
                block = self._anima_loras[0][2]
                self._anima_loras[0][0].set(path)
                self._apply_lora_file(block)
            else:
                self._add_anima_lora(path, 0.8)
            self._anima_say(f"Anima LoRA is {name}.")
            return

    def _add_anima_lora(self, path: str = "", weight: float = 0.8, triggers: str = "", thumb: str = "") -> None:
        block = ttk.Frame(self.anima_lora_host, style="Card.TFrame")
        block.pack(fill="x", pady=4)
        row = ttk.Frame(block, style="Card.TFrame")
        row.pack(fill="x")
        path_var = tk.StringVar(value=path)
        weight_var = tk.DoubleVar(value=weight)
        tk.Entry(row, textvariable=path_var, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=4
        )

        def browse() -> None:
            picked = self._pick_lora_file("Anima LoRA", path_var.get(), "anima")
            if picked:
                path_var.set(picked)
                self._apply_lora_file(block)

        ttk.Button(row, text="File", command=browse).pack(side="left", padx=4)
        tk.Entry(row, textvariable=weight_var, width=6, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(side="left", ipady=4)
        ttk.Button(row, text="Civitai", command=lambda: self._fetch_civitai(block)).pack(side="left", padx=4)

        def remove() -> None:
            self._anima_loras = [item for item in self._anima_loras if item[2] is not block]
            block.destroy()

        ttk.Button(row, text="Remove", command=remove).pack(side="left")
        info = ttk.Frame(block, style="Card.TFrame")
        info.pack(fill="x", pady=(4, 0))
        thumb_label = tk.Label(info, text="", bg=BG, width=12, height=5)
        thumb_label.pack(side="left")
        triggers_var = tk.StringVar(value=triggers)
        tk.Entry(info, textvariable=triggers_var, bg=INSET, fg=FG, insertbackground=FG, relief="flat").pack(
            side="left", fill="x", expand=True, ipady=4, padx=6
        )
        ttk.Button(info, text="Use", command=lambda: self._use_anima_triggers(triggers_var)).pack(side="left")
        info_label = tk.Label(block, text="", bg=SURFACE, fg=MUTED, wraplength=480, justify="left")
        info_label.pack(anchor="w", pady=(2, 0))
        block.path_var = path_var
        block.triggers = triggers_var
        block.thumb_label = thumb_label
        block.thumb_path = thumb if thumb and Path(thumb).is_file() else ""
        block.thumb_photo = None
        block.info_label = info_label
        block.report = self._anima_say
        if block.thumb_path:
            self._show_thumb(block, block.thumb_path)
        if path and Path(path).is_file():
            if not triggers.strip():
                found = _local_triggers(Path(path))
                if found:
                    triggers_var.set(found)
            info_label.configure(text=_local_lora_info(Path(path)))
            if not block.thumb_path:
                local_thumb = _local_thumb(Path(path))
                if local_thumb:
                    self._show_thumb(block, local_thumb)
        self._anima_loras.append((path_var, weight_var, block))

    def _use_anima_triggers(self, variable: tk.StringVar) -> None:
        text = variable.get().strip()
        if not text or text.startswith("No trigger") or text.startswith("Civitai") or text.startswith("Asking"):
            self._anima_say("No trigger words to add.")
            return
        current = self.anima_prompt.get("1.0", "end").strip()
        self.anima_prompt.delete("1.0", "end")
        self.anima_prompt.insert("1.0", text if not current else f"{text}, {current}")

    def _pick_anima_init(self) -> None:
        picked = filedialog.askopenfilename(title="Source picture", filetypes=[("Pictures", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("All files", "*.*")])
        if picked:
            self.anima_init.set(picked)

    def _pick_anima_output(self) -> None:
        picked = filedialog.askdirectory(title="Anima pictures")
        if picked:
            self.anima_output.set(picked)

    def _click_anima(self, _event=None) -> None:
        image = getattr(self, "_anima_full", None)
        if image is None:
            return
        self._full_image = image
        self._click_preview()

    def _restore_anima(self, data: dict) -> None:
        for key, var in (
            ("model", self.anima_model),
            ("text", self.anima_text),
            ("vae", self.anima_vae),
            ("preset", self.anima_preset),
            ("seed", self.anima_seed),
            ("output", self.anima_output),
            ("init", self.anima_init),
        ):
            if isinstance(data.get(key), str):
                var.set(data[key])
        for key, var in (
            ("steps", self.anima_steps),
            ("width", self.anima_width),
            ("height", self.anima_height),
            ("batch", self.anima_batch),
            ("max_length", self.anima_max_length),
        ):
            if data.get(key) is not None:
                try:
                    var.set(int(data[key]))
                except (TypeError, ValueError, tk.TclError):
                    pass
        for key, var in (("cfg", self.anima_cfg), ("shift", self.anima_shift), ("denoise", self.anima_denoise)):
            if data.get(key) is not None:
                try:
                    var.set(float(data[key]))
                except (TypeError, ValueError, tk.TclError):
                    pass
        if isinstance(data.get("prompt"), str) and data["prompt"]:
            self.anima_prompt.delete("1.0", "end")
            self.anima_prompt.insert("1.0", data["prompt"])
        if isinstance(data.get("negative"), str) and data["negative"]:
            self.anima_negative.delete("1.0", "end")
            self.anima_negative.insert("1.0", data["negative"])
        for item in data.get("loras") or []:
            if isinstance(item, dict):
                self._add_anima_lora(
                    str(item.get("path") or ""),
                    float(item.get("weight") or 0.8),
                    str(item.get("triggers") or ""),
                    str(item.get("thumb") or ""),
                )

    def _ensure_anima_files(self) -> None:
        import anima

        text = self.anima_text.get().strip()
        vae = self.anima_vae.get().strip()
        local_text = anima.weight_path("text")
        local_vae = anima.weight_path("vae")
        if not (text and Path(text).is_file()) and local_text.is_file() and local_text.stat().st_size >= anima.WEIGHTS["text"][2]:
            self.anima_text.set(str(local_text))
        if not (vae and Path(vae).is_file()) and local_vae.is_file() and local_vae.stat().st_size >= anima.WEIGHTS["vae"][2]:
            self.anima_vae.set(str(local_vae))
        text = self.anima_text.get().strip()
        vae = self.anima_vae.get().strip()
        if text and Path(text).is_file() and vae and Path(vae).is_file():
            return
        if getattr(self, "_anima_fetching", False):
            return
        self._anima_fetching = True
        self._anima_say("Downloading the Qwen3 text encoder and Qwen-Image VAE into the app folder.")
        threading.Thread(target=self._fetch_anima_weights, daemon=True).start()

    def _fetch_anima_weights(self) -> None:
        import anima

        try:
            text, vae = anima.ensure_weights(lambda note: self.after(0, lambda text=note: self._anima_say(text)))
        except Exception as exc:
            self._anima_fetching = False
            self.after(0, lambda detail=exc: self._anima_say(f"Could not download the Anima text encoder or VAE. {detail}"))
            return

        def apply() -> None:
            self._anima_fetching = False
            if not Path(self.anima_text.get().strip()).is_file():
                self.anima_text.set(str(text))
            if not Path(self.anima_vae.get().strip()).is_file():
                self.anima_vae.set(str(vae))
            self._anima_say("Added the Qwen3 text encoder and Qwen-Image VAE from the app folder.")

        self.after(0, apply)

    def _anima_say(self, text: str) -> None:
        self.anima_status.configure(text=text.split("\n", 1)[0][:180])
        self.anima_log.configure(state="normal")
        self.anima_log.insert("end", text + "\n")
        self.anima_log.see("end")
        self.anima_log.configure(state="disabled")

    def _generate_anima(self) -> None:
        job = self._collect_anima_job()
        if job is None:
            return
        if self.hold.busy:
            self.hold.queue.append(job)
            self._show_queue()
            self._anima_say(f"Queued. {len(self.hold.queue)} waiting.")
            return
        self._start_job(job)

    def _collect_anima_job(self, override: dict | None = None) -> dict | None:
        import anima

        override = override or {}

        if sys.platform != "win32":
            self._anima_say("Anima needs Windows 11 with an AMD driver. This copy is the local app, not a browser.")
            return None
        model = self.anima_model.get().strip()
        if not model or not Path(model).exists():
            self._anima_say("Choose an Anima model file or a diffusers folder.")
            return None
        folder_model = Path(model).is_dir()
        text = self.anima_text.get().strip()
        vae = self.anima_vae.get().strip()
        if not text or not Path(text).is_file():
            local = anima.weight_path("text")
            if local.is_file():
                text = str(local)
                self.anima_text.set(text)
        if not vae or not Path(vae).is_file():
            local = anima.weight_path("vae")
            if local.is_file():
                vae = str(local)
                self.anima_vae.set(vae)
        if not folder_model and (not text or not Path(text).is_file() or not vae or not Path(vae).is_file()):
            self._ensure_anima_files()
            self._anima_say("The Qwen3 text encoder and Qwen-Image VAE are still downloading into the app folder.")
            return None
        prompt = override["prompt"].strip() if isinstance(override.get("prompt"), str) else self.anima_prompt.get("1.0", "end").strip()
        if not prompt:
            self._anima_say("The prompt is empty.")
            return None
        folder = override["folder"].strip() if isinstance(override.get("folder"), str) else self.anima_output.get().strip()
        if not folder:
            self._anima_say("Choose a folder for the pictures.")
            return None
        loras = []
        for path_var, weight_var, _block in self._anima_loras:
            path = path_var.get().strip()
            if not path:
                continue
            if not Path(path).is_file():
                self._anima_say(f"LoRA not found: {path}")
                return None
            loras.append((path, float(weight_var.get())))
        try:
            steps = max(1, min(80, int(self.anima_steps.get())))
            cfg = float(self.anima_cfg.get())
            shift = float(self.anima_shift.get())
            width = anima.snap_dim(int(self.anima_width.get()))
            height = anima.snap_dim(int(self.anima_height.get()))
            count = override.get("count") if isinstance(override.get("count"), int) else max(1, min(100, int(self.anima_batch.get())))
            max_length = max(32, min(1024, int(self.anima_max_length.get())))
        except (tk.TclError, ValueError):
            self._anima_say("Steps, CFG, shift, size, and batch must be numbers.")
            return None
        seed = None
        seed_text = self.anima_seed.get().strip()
        if seed_text:
            try:
                seed = int(seed_text)
            except ValueError:
                self._anima_say("Seed must be a whole number, or left blank.")
                return None
        source = self.anima_init.get().strip()
        return {
            "kind": "anima",
            "model": model,
            "text": text,
            "vae": vae,
            "prompt": prompt,
            "negative": self.anima_negative.get("1.0", "end").strip(),
            "folder": folder,
            "loras": loras,
            "steps": steps,
            "cfg": cfg,
            "shift": shift,
            "width": width,
            "height": height,
            "count": count,
            "seed": seed,
            "max_length": max_length,
            "init_image": "" if override.get("skip_init") else (source if source and Path(source).is_file() else ""),
            "init_denoise": float(self.anima_denoise.get() or 0.6),
            "vn_hook": override.get("vn_hook"),
        }

    def _start_anima_job(self, job: dict) -> None:
        self._release_sd_worker()
        self._frame_target = "anima"
        self.hold.busy = True
        self.hold.batch_stop = False
        self._portrait_for_card = False
        self._active_vn_hook = job.get("vn_hook")
        token = object()
        self.hold.token = token
        self.anima_caption.configure(text="Starting…")
        self.anima_progress["value"] = 0
        waiting = len(self.hold.queue)
        extra = f" {waiting} still waiting." if waiting else ""
        self._anima_say(f"Batch count {job['count']}.{extra}")
        threading.Thread(target=self._run_anima_batch, args=(token, job), daemon=True).start()

    def _run_anima_batch(self, token, job: dict) -> None:
        import anima

        saved = 0
        try:
            try:
                python, env = anima.runtime(lambda text: self.after(0, lambda note=text: self._anima_say(note)))
            except Exception as exc:
                self.after(0, lambda detail=exc: self._anima_say(f"Could not install the Anima runtime. {detail}"))
                return
            try:
                worker = self._ensure_anima_worker(python, env)
            except Exception as exc:
                self.after(0, lambda detail=exc: self._anima_say(f"Could not start Anima. {detail}"))
                return
            count = int(job["count"])
            batch_started = time.perf_counter()
            for index in range(count):
                if self.hold.batch_stop or self.hold.token is not token:
                    self.after(0, lambda done=saved: self._anima_say(f"Batch stopped. {done} pictures were saved."))
                    return
                this = dict(job)
                this["seed"] = None if job["seed"] is None else int(job["seed"]) + index
                model_name = Path(this["model"]).name
                self.after(0, lambda number=index + 1, total=count, name=model_name: self._anima_say(f"Picture {number} of {total} with {name}"))
                ok, out = self._run_anima_once(worker, this, index, count)
                if self.hold.batch_stop or self.hold.token is not token:
                    self.after(0, lambda done=saved: self._anima_say(f"Batch stopped. {done} pictures were saved."))
                    return
                if not ok:
                    return
                saved += 1
                took = format_elapsed(getattr(self, "_last_gen_seconds", 0))
                self.after(0, lambda path=out: self._remember_picture(path))
                self.after(0, lambda path=out: self._emit_vn_picture(path))
                self.after(0, lambda path=out, number=index + 1, total=count, took=took: self._anima_say(f"Saved {number} of {total} in {took}: {path}"))
            if count > 1 and saved:
                took = format_elapsed(time.perf_counter() - batch_started)
                self.after(0, lambda done=saved, took=took: self._anima_say(f"Finished {done} pictures in {took}."))
        finally:
            def finish(token=token) -> None:
                if self.hold.token is not token:
                    return
                stopped = self.hold.batch_stop
                self.hold.busy = False
                self.hold.batch_stop = False
                self._frame_target = ""
                self._active_vn_hook = None
                if self.hold.proc is getattr(self, "_anima_proc", None):
                    self.hold.proc = None
                if stopped:
                    self._show_queue()
                    return
                if not self.keep_loaded.get() and not self.hold.queue:
                    self._release_anima_worker()
                    self._anima_say("Unloaded the Anima model.")
                self._start_next_queued()

            self.after(0, finish)

    def _run_anima_once(self, proc, job: dict, index: int, count: int) -> tuple[bool, str]:
        import json as _json
        from PIL import Image

        work = Path(tempfile.gettempdir()) / "RedGen"
        work.mkdir(parents=True, exist_ok=True)
        out = Path(job["folder"]) / stamp_name()
        if count > 1:
            out = out.with_name(f"{out.stem}-{index + 1}{out.suffix}")
        status_path = work / "anima-status.txt"
        preview_path = work / "anima-preview.png"
        for path in (status_path, preview_path):
            if path.exists():
                path.unlink()
        payload = dict(job)
        payload.update({"out": str(out), "status": str(status_path), "preview": str(preview_path)})
        job_path = work / f"anima-job-{index}.json"
        job_path.write_text(_json.dumps(payload), encoding="utf-8")
        error_path = work / "anima-worker-error.txt"
        print(f"Anima: picture {index + 1} of {count} starting", flush=True)
        started = time.perf_counter()
        self.hold.proc = proc
        try:
            if proc.poll() is not None or not proc.stdin:
                self.after(0, lambda: self._anima_say("Anima stopped before the picture started."))
                self._anima_proc = None
                return False, ""
            proc.stdin.write(str(job_path) + "\n")
            proc.stdin.flush()
            seen = ""
            while True:
                if proc.poll() is not None:
                    error_text = error_path.read_text(encoding="utf-8")[-2000:] if error_path.exists() else ""
                    detail = error_text.strip() or f"Anima stopped ({proc.returncode})."
                    self._anima_proc = None
                    if not self.hold.batch_stop:
                        self.after(0, lambda d=detail: self._anima_say(f"Generation failed: {d}"))
                    return False, ""
                text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
                if text and text != seen and not text.startswith("error"):
                    seen = text
                    caption = text
                    print(f"Anima: {caption}", flush=True)
                    self.after(0, lambda cap=caption, i=index, n=count: self._status_tick(cap, i, n))
                    self.after(0, lambda note=caption: self.anima_status.configure(text=note[:180]))
                    if not caption.lower().startswith("step "):
                        self.after(0, lambda note=caption: self._anima_say(note))
                if text == "done" and out.exists():
                    with Image.open(out) as frame:
                        image = frame.copy()
                    note = job["prompt"] if not job.get("negative") else f"{job['prompt']}\n\nNegative:\n{job['negative']}"
                    out.with_suffix(".txt").write_text(note, encoding="utf-8")
                    self._last_gen_seconds = time.perf_counter() - started
                    took = format_elapsed(self._last_gen_seconds)
                    print(f"Anima: finished in {took}", flush=True)
                    caption = "Final" if count == 1 else f"Final {index + 1} of {count}"
                    self.after(0, lambda img=image, cap=f"{caption} · {took}", i=index, n=count: self._show_frame(img, cap, i, n))
                    return True, str(out)
                if text.startswith("error"):
                    detail = text.split("\n", 1)[-1]
                    if not self.hold.batch_stop:
                        self.after(0, lambda d=detail: self._anima_say(f"Generation failed: {d}"))
                    return False, ""
                if self.hold.batch_stop or self.hold.token is None:
                    return False, ""
                time.sleep(0.3)
        finally:
            if self.hold.proc is proc and proc.poll() is None:
                self.hold.proc = None

    def _start_job(self, job: dict) -> None:
        if job.get("kind") == "anima":
            self._start_anima_job(job)
            return
        self._release_anima_worker()
        self._frame_target = ""
        self.hold.busy = True
        self.hold.batch_stop = False
        self._portrait_for_card = bool(job.get("for_card"))
        self._active_vn_hook = job.get("vn_hook")
        token = object()
        self.hold.token = token
        self.view_caption.configure(text="Starting…")
        self.progress["value"] = 0
        note = "" if job["clip"] else clip_warning(job["prompt"])
        if job.get("init_image"):
            note = f" Redrawing the source picture at denoise {float(job.get('init_denoise') or 0):.2f}." + note
        waiting = len(self.hold.queue)
        extra = f" {waiting} still waiting." if waiting else ""
        self._say(f"Batch count {job['count']}. Each picture runs on its own, then the card is cleared.{extra}" + note)
        threading.Thread(
            target=self._run_batch,
            args=(
                token,
                job["count"],
                job["model"],
                job["prompt"],
                job["negative"],
                job["folder"],
                job["loras"],
                job["steps"],
                job["cfg"],
                job["width"],
                job["height"],
                job["seed"],
                job["clip"],
                job["clip_g"],
                job["vae"],
                job.get("init_image") or "",
                float(job.get("init_denoise") or 1),
            ),
            daemon=True,
        ).start()

    def _start_next_queued(self) -> None:
        if self.hold.busy or not self.hold.queue:
            self._show_queue()
            return
        self._start_job(self.hold.queue.pop(0))
        self._show_queue()

    def _run_batch(self, token, count, model, prompt, negative, folder, loras, steps, cfg, width, height, seed, clip, clip_g, vae, init_image="", init_denoise=1.0) -> None:
        saved = 0
        batch_started = time.perf_counter()
        try:
            for index in range(count):
                if self.hold.batch_stop or self.hold.token is not token:
                    self.after(0, lambda done=saved: self._say(f"Batch stopped. {done} pictures were saved."))
                    return
                this_seed = None if seed is None else seed + index
                label = f"Picture {index + 1} of {count}"
                self.after(0, lambda text=label: self._say(text))
                ok, out = self._run(
                    model, prompt, negative, folder, loras, steps, cfg, width, height, this_seed, clip, clip_g, vae, index, count, init_image, init_denoise
                )
                if self.hold.batch_stop or self.hold.token is not token:
                    self.after(0, lambda done=saved: self._say(f"Batch stopped. {done} pictures were saved."))
                    return
                if not ok:
                    return
                saved += 1
                took = format_elapsed(getattr(self, "_last_gen_seconds", 0))
                if count == 1:
                    self.after(0, lambda path=out: self._remember_picture(path))
                    self.after(0, lambda path=out: self._emit_vn_picture(path))
                    self.after(0, lambda path=out, took=took: self._say(f"Saved {path}\nTook {took}. The AMD card is clear."))
                else:
                    self.after(0, lambda path=out, number=index + 1: self._remember_picture(path))
                    self.after(0, lambda path=out: self._emit_vn_picture(path))
                    self.after(0, lambda path=out, number=index + 1, took=took: self._say(f"Saved {number} of {count} in {took}: {path}"))
            if count > 1 and saved:
                took = format_elapsed(time.perf_counter() - batch_started)
                self.after(0, lambda done=saved, took=took: self._say(f"Saved {done} pictures in {took}. The AMD card is clear."))
        finally:
            def finish(token=token) -> None:
                if self.hold.token is not token:
                    return
                stopped = self.hold.batch_stop
                self.hold.busy = False
                self.hold.batch_stop = False
                self._portrait_for_card = False
                self._active_vn_hook = None
                if stopped:
                    self._show_queue()
                    return
                self._start_next_queued()

            self.after(0, finish)

    def _emit_vn_picture(self, path: str) -> None:
        hook = getattr(self, "_active_vn_hook", None)
        if not callable(hook):
            return
        try:
            hook(str(path))
        except Exception as exc:
            self._say(f"RedVN could not take the picture. {exc}")

    def _vae_tile_values(self) -> tuple[bool, int, int]:
        try:
            size = max(128, min(2048, int(self.vae_tile_size.get())))
            overlap = max(0, min(size // 2, int(self.vae_tile_overlap.get())))
        except (tk.TclError, ValueError) as exc:
            raise ValueError("VAE tile size and overlap must be numbers.") from exc
        size -= size % 8
        overlap -= overlap % 8
        return bool(self.vae_tile.get()), size, overlap

    def _run(self, model, prompt, negative, folder, loras, steps, cfg, width, height, seed, clip, clip_g, vae="", index=0, count=1, init_image="", init_denoise=1.0) -> tuple[bool, str]:
        import json as _json
        from PIL import Image

        work = Path(tempfile.gettempdir()) / "RedGen"
        work.mkdir(parents=True, exist_ok=True)
        out = Path(folder) / stamp_name()
        if count > 1:
            out = out.with_name(f"{out.stem}-{index + 1}{out.suffix}")
        status_path = work / "status.txt"
        preview_path = work / "preview.png"
        for path in (status_path, preview_path):
            if path.exists():
                path.unlink()
        job = {
            "model": model,
            "prompt": prompt,
            "negative": negative,
            "loras": loras,
            "steps": steps,
            "cfg": cfg,
            "width": width,
            "height": height,
            "seed": seed,
            "clip": clip,
            "clip_g": clip_g,
            "vae": vae,
            "vae_tile": self._vae_tile_values()[0],
            "vae_tile_size": self._vae_tile_values()[1],
            "vae_tile_overlap": self._vae_tile_values()[2],
            "eye_fix": bool(self.eye_fix.get()),
            "eye_model": self.eye_model.get().strip(),
            "eye_denoise": float(self.eye_denoise.get() or 0.55),
            "eye_conf": float(self.eye_conf.get() or 0.3),
            "eye_prompt": self.eye_prompt.get().strip(),
            "init_image": init_image,
            "init_denoise": init_denoise,
            "out": str(out),
            "status": str(status_path),
            "preview": str(preview_path),
            "keep": bool(self.keep_loaded.get()),
        }
        job_path = work / "job.json"
        job_path.write_text(_json.dumps(job), encoding="utf-8")
        if job["keep"]:
            return self._run_sd_kept(job_path, out, status_path, preview_path, index, count)
        proc = subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--job", str(job_path)]
        )
        self.hold.proc = proc
        seen = ""
        shown = 0.0
        started = time.perf_counter()
        try:
            while proc.poll() is None:
                text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
                if text and text != seen and not text.startswith("error"):
                    seen = text
                    caption = "Loading the model…" if text == "load" else text
                    self.after(0, lambda cap=caption, i=index, n=count: self._status_tick(cap, i, n))
                if preview_path.exists() and preview_path.stat().st_mtime != shown:
                    try:
                        with Image.open(preview_path) as frame:
                            image = frame.copy()
                        shown = preview_path.stat().st_mtime
                        caption = seen if seen and seen != "load" else "Step"
                        self.after(0, lambda img=image, cap=caption, i=index, n=count: self._show_frame(img, cap, i, n))
                    except OSError:
                        pass
                time.sleep(0.3)
            text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
            if proc.returncode == 0 and out.exists():
                with Image.open(out) as frame:
                    image = frame.copy()
                self._last_gen_seconds = time.perf_counter() - started
                took = format_elapsed(self._last_gen_seconds)
                print(f"Generation finished in {took}", flush=True)
                caption = "Final" if count == 1 else f"Final {index + 1} of {count}"
                self.after(0, lambda img=image, cap=f"{caption} · {took}", i=index, n=count: self._show_frame(img, cap, i, n))
                return True, str(out)
            detail = text.split("\n", 1)[-1] if text.startswith("error") else f"The picture job stopped ({proc.returncode})."
            if not self.hold.batch_stop:
                self.after(0, lambda d=detail: self._say(f"Generation failed: {d}"))
            return False, ""
        finally:
            self._kill_job()

    def _run_sd_kept(self, job_path: Path, out: Path, status_path: Path, preview_path: Path, index: int, count: int) -> tuple[bool, str]:
        from PIL import Image

        error_path = Path(tempfile.gettempdir()) / "RedGen" / "sd-worker-error.txt"
        proc = self._ensure_sd_worker()
        self.hold.proc = proc
        started = time.perf_counter()
        try:
            if proc.poll() is not None or not proc.stdin:
                self._sd_proc = None
                self.after(0, lambda: self._say("The picture model stopped before the picture started."))
                return False, ""
            proc.stdin.write(str(job_path) + "\n")
            proc.stdin.flush()
            seen = ""
            shown = 0.0
            while True:
                if proc.poll() is not None:
                    error_text = error_path.read_text(encoding="utf-8")[-2000:] if error_path.exists() else ""
                    self._sd_proc = None
                    if not self.hold.batch_stop:
                        detail = error_text.strip() or f"The picture model stopped ({proc.returncode})."
                        self.after(0, lambda d=detail: self._say(f"Generation failed: {d}"))
                    return False, ""
                text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
                if text and text != seen and not text.startswith("error"):
                    seen = text
                    caption = "Loading the model…" if text == "load" else text
                    print(caption, flush=True)
                    self.after(0, lambda cap=caption, i=index, n=count: self._status_tick(cap, i, n))
                if preview_path.exists() and preview_path.stat().st_mtime != shown:
                    try:
                        with Image.open(preview_path) as frame:
                            image = frame.copy()
                        shown = preview_path.stat().st_mtime
                        caption = seen if seen and seen != "load" else "Step"
                        self.after(0, lambda img=image, cap=caption, i=index, n=count: self._show_frame(img, cap, i, n))
                    except OSError:
                        pass
                if text == "done" and out.exists():
                    with Image.open(out) as frame:
                        image = frame.copy()
                    self._last_gen_seconds = time.perf_counter() - started
                    took = format_elapsed(self._last_gen_seconds)
                    print(f"Generation finished in {took}", flush=True)
                    caption = "Final" if count == 1 else f"Final {index + 1} of {count}"
                    self.after(0, lambda img=image, cap=f"{caption} · {took}", i=index, n=count: self._show_frame(img, cap, i, n))
                    return True, str(out)
                if text.startswith("error"):
                    detail = text.split("\n", 1)[-1]
                    if not self.hold.batch_stop:
                        self.after(0, lambda d=detail: self._say(f"Generation failed: {d}"))
                    return False, ""
                if self.hold.batch_stop or self.hold.token is None:
                    return False, ""
                time.sleep(0.3)
        finally:
            if self.hold.proc is proc and proc.poll() is None:
                self.hold.proc = None

    def _load_pipe(self, path: Path, sdxl: bool):
        import torch
        from diffusers import AutoPipelineForText2Image, StableDiffusionPipeline, StableDiffusionXLPipeline

        dtype = torch.float16
        if path.is_dir():
            pipe = AutoPipelineForText2Image.from_pretrained(
                path, torch_dtype=dtype, safety_checker=None, requires_safety_checker=False
            )
        else:
            kind = StableDiffusionXLPipeline if sdxl else StableDiffusionPipeline
            pipe = kind.from_single_file(str(path), torch_dtype=dtype)
        if hasattr(pipe, "safety_checker"):
            pipe.safety_checker = None
        if hasattr(pipe, "requires_safety_checker"):
            pipe.requires_safety_checker = False
        return pipe

    def _restore_stock(self, pipe) -> None:
        stock = self.hold.stock
        pipe.text_encoder = stock["text_encoder"]
        if stock["tokenizer"] is not None:
            pipe.tokenizer = stock["tokenizer"]
            pipe.tokenizer.model_max_length = stock["tok_len"]
        if stock["text_encoder_2"] is not None and hasattr(pipe, "text_encoder_2"):
            pipe.text_encoder_2 = stock["text_encoder_2"]
        if stock["tokenizer_2"] is not None and hasattr(pipe, "tokenizer_2"):
            pipe.tokenizer_2 = stock["tokenizer_2"]
            pipe.tokenizer_2.model_max_length = stock["tok_len_2"]

    def _capture_stock(self, pipe) -> None:
        tokenizer = getattr(pipe, "tokenizer", None)
        tokenizer_2 = getattr(pipe, "tokenizer_2", None)
        self.hold.stock = {
            "text_encoder": pipe.text_encoder,
            "text_encoder_2": getattr(pipe, "text_encoder_2", None),
            "tokenizer": tokenizer,
            "tokenizer_2": tokenizer_2,
            "tok_len": tokenizer.model_max_length if tokenizer is not None else 77,
            "tok_len_2": tokenizer_2.model_max_length if tokenizer_2 is not None else 77,
        }

    def _clip_token_length(self, encoder) -> int:
        weight = encoder.text_model.embeddings.position_embedding.weight
        return int(weight.shape[0])

    def _resize_clip_positions(self, encoder, new_len: int) -> None:
        import torch
        import torch.nn.functional as F

        embeddings = encoder.text_model.embeddings
        weight = embeddings.position_embedding.weight
        old_len, width = int(weight.shape[0]), int(weight.shape[1])
        new_len = int(new_len)
        if old_len == new_len:
            encoder.config.max_position_embeddings = new_len
            return
        data = weight.detach().float().cpu()
        if new_len > old_len:
            keep = min(20, old_len)
            head = data[:keep]
            tail = data[keep:]
            stretched = F.interpolate(tail.T.unsqueeze(0), size=new_len - keep, mode="linear", align_corners=True)
            data = torch.cat([head, stretched.squeeze(0).T], dim=0)
        else:
            data = data[:new_len]
        device, dtype = weight.device, weight.dtype
        replacement = torch.nn.Embedding(new_len, width)
        replacement.weight.data.copy_(data.to(dtype=torch.float32))
        replacement.to(device=device, dtype=dtype)
        embeddings.position_embedding = replacement
        positions = torch.arange(new_len, device=device).unsqueeze(0)
        embeddings.register_buffer("position_ids", positions, persistent=False)
        encoder.config.max_position_embeddings = new_len
        text_config = getattr(encoder.text_model, "config", None)
        if text_config is not None:
            text_config.max_position_embeddings = new_len

    def _set_tokenizer_length(self, pipe, which: str, length: int) -> None:
        name = "tokenizer" if which == "l" else "tokenizer_2"
        tokenizer = getattr(pipe, name, None)
        if tokenizer is not None:
            tokenizer.model_max_length = int(length)

    def _match_clip_lengths(self, pipe) -> str:
        encoders = [(pipe.text_encoder, "tokenizer", "CLIP")]
        second = getattr(pipe, "text_encoder_2", None)
        if second is not None:
            encoders.append((second, "tokenizer_2", "CLIP-G"))
        lengths = [self._clip_token_length(encoder) for encoder, _name, _label in encoders]
        target = max(lengths)
        if target <= 77 or len(set(lengths)) == 1:
            for encoder, name, _label in encoders:
                tokenizer = getattr(pipe, name, None)
                if tokenizer is not None:
                    tokenizer.model_max_length = self._clip_token_length(encoder)
            return ""
        for encoder, name, label in encoders:
            if self._clip_token_length(encoder) != target:
                self._resize_clip_positions(encoder, target)
            tokenizer = getattr(pipe, name, None)
            if tokenizer is not None:
                tokenizer.model_max_length = target
        return f"Both text encoders are set to {target} tokens."

    def _mount_clip(self, pipe, path: Path, which: str) -> str:
        import torch

        stock = pipe.text_encoder if which == "l" else getattr(pipe, "text_encoder_2", None)
        label = "CLIP" if which == "l" else "CLIP-G"
        if stock is None:
            raise RuntimeError("This checkpoint has no CLIP-G encoder. Clear that row.")
        weight = next(pipe.unet.parameters())
        device, dtype = weight.device, weight.dtype
        if path.is_dir():
            encoder = type(stock).from_pretrained(str(path), torch_dtype=dtype)
            length = int(getattr(encoder.config, "max_position_embeddings", 77))
            if (path / "tokenizer_config.json").exists():
                from transformers import CLIPTokenizer

                tokenizer = CLIPTokenizer.from_pretrained(str(path))
                tokenizer.model_max_length = length
                if which == "l":
                    pipe.tokenizer = tokenizer
                else:
                    pipe.tokenizer_2 = tokenizer
            encoder.to(device=device, dtype=dtype)
            if which == "l":
                pipe.text_encoder = encoder
            else:
                pipe.text_encoder_2 = encoder
            self._set_tokenizer_length(pipe, which, self._clip_token_length(encoder))
            return f"{label} loaded, {self._clip_token_length(encoder)} tokens."

        if path.suffix.lower() == ".safetensors":
            from safetensors.torch import load_file

            raw_state = load_file(str(path))
        else:
            try:
                raw_state = torch.load(str(path), map_location="cpu", weights_only=True)
            except TypeError:
                raw_state = torch.load(str(path), map_location="cpu")
            if hasattr(raw_state, "state_dict"):
                raw_state = raw_state.state_dict()
            if isinstance(raw_state, dict) and isinstance(raw_state.get("state_dict"), dict):
                raw_state = raw_state["state_dict"]
        if not isinstance(raw_state, dict):
            raise RuntimeError("That CLIP file is not a weight file.")
        state = _normalize_clip_state(raw_state)
        token = state.get("text_model.embeddings.token_embedding.weight")
        hidden = int(getattr(stock.config, "hidden_size", 0) or 0)
        if token is not None and hidden and int(token.shape[1]) != hidden:
            raise RuntimeError(
                f"That file is a {int(token.shape[1])}-wide CLIP. This row needs {hidden}. "
                + ("Put it in the first CLIP row." if which == "g" else "Put it in CLIP-G if this is an SDXL model.")
            )
        position = state.get("text_model.embeddings.position_embedding.weight")
        length = int(position.shape[0]) if position is not None else int(getattr(stock.config, "max_position_embeddings", 77))
        config = stock.config
        if length != int(getattr(config, "max_position_embeddings", 77)):
            config = type(config).from_dict(config.to_dict())
            config.max_position_embeddings = length
        encoder = type(stock)(config)
        state = self._fit_clip_projection(encoder, state)
        try:
            missing, unexpected = encoder.load_state_dict(state, strict=False)
        except RuntimeError as exc:
            if position is None or "position_embedding" not in str(exc):
                raise
            config = type(stock.config).from_dict(stock.config.to_dict())
            config.max_position_embeddings = int(position.shape[0])
            encoder = type(stock)(config)
            state = self._fit_clip_projection(encoder, state)
            missing, unexpected = encoder.load_state_dict(state, strict=False)
        expected = [key for key in encoder.state_dict() if not key.endswith("position_ids")]
        missing_names = set(missing)
        matched = sum(1 for key in expected if key not in missing_names)
        if matched < max(10, int(len(expected) * 0.6)):
            sample = ", ".join(list(state)[:4]) or "no known keys"
            raise RuntimeError(f"Could not read a CLIP text encoder from that file. First keys: {sample}")
        if which == "g" and getattr(encoder, "text_projection", None) is not None:
            projection = state.get("text_projection.weight", state.get("text_projection"))
            if projection is None and "text_projection.weight" in missing:
                raise RuntimeError("That file has no CLIP-G text projection. Put CLIP-L in the first row.")
        encoder.to(device=device, dtype=dtype)
        if which == "l":
            pipe.text_encoder = encoder
        else:
            pipe.text_encoder_2 = encoder
        self._set_tokenizer_length(pipe, which, self._clip_token_length(encoder))
        return f"{label} loaded, {self._clip_token_length(encoder)} tokens."

    def _fit_clip_projection(self, encoder, state: dict) -> dict:
        import torch

        module = getattr(encoder, "text_projection", None)
        raw = state.get("text_projection.weight", state.get("text_projection"))
        if module is None or raw is None or not torch.is_tensor(raw):
            return state
        fitted = dict(state)
        if isinstance(module, torch.nn.Linear):
            target = tuple(module.weight.shape)
            value = raw.T.contiguous() if raw.ndim == 2 and tuple(raw.shape) != target and tuple(raw.T.shape) == target else raw
            fitted["text_projection.weight"] = value
            fitted.pop("text_projection", None)
            return fitted
        if torch.is_tensor(module):
            target = tuple(module.shape)
            value = raw.T.contiguous() if raw.ndim == 2 and tuple(raw.shape) != target and tuple(raw.T.shape) == target else raw
            if tuple(value.shape) == target:
                module.data.copy_(value.to(dtype=module.dtype))
            fitted.pop("text_projection.weight", None)
            fitted.pop("text_projection", None)
        return fitted

    def _apply_clips(self, pipe, clip: str, clip_g: str) -> None:
        self._restore_stock(pipe)
        notes = []
        if clip:
            notes.append(self._mount_clip(pipe, Path(clip), "l"))
        if clip_g:
            notes.append(self._mount_clip(pipe, Path(clip_g), "g"))
        if not notes:
            return
        matched = self._match_clip_lengths(pipe)
        if matched:
            notes.append(matched)
        message = " ".join(notes)
        writer = self.__dict__.get("_status_write")
        if writer is not None:
            writer(message)
        else:
            print(message, flush=True)

    def _open_pipe(self, path: Path, model: str, sdxl: bool, clip: str, clip_g: str):
        signature = (str(model), bool(sdxl), clip or "", clip_g or "")
        if self.hold.pipe is not None and getattr(self.hold, "pipe_sig", None) == signature:
            writer = self.__dict__.get("_status_write")
            if writer is not None:
                writer("Using the model already loaded")
            return self.hold.pipe
        if self.hold.pipe is not None:
            self.hold.pipe = None
            self.hold.stock = None
            self.hold.pipe_sig = None
            self._empty_cache()
        pipe = self._load_pipe(path, sdxl)
        self.hold.pipe = pipe
        self.hold.path = model
        self.hold.sdxl = sdxl
        self.hold.pipe_sig = signature
        self._capture_stock(pipe)
        self._apply_clips(pipe, clip, clip_g)
        self.hold.clip_sig = (model, clip, clip_g)
        return pipe

    def _force_execution_device(self, pipe, device) -> None:
        cls = pipe.__class__
        if not getattr(cls, "_redgen_patched", False):
            original = cls._execution_device

            def _execution_device(self):
                forced = getattr(self, "_redgen_device", None)
                if forced is not None:
                    return forced
                return original.__get__(self, self.__class__)

            cls._execution_device = property(_execution_device)
            cls._redgen_patched = True
        pipe._redgen_device = device

    def _encode(self, pipe, prompt, negative, cfg, device, sdxl):
        positive = self._encode_text(pipe, prompt or "", device, sdxl)
        if cfg <= 1:
            if sdxl:
                hidden, pooled = positive
                return hidden, None, pooled, None
            return positive, None
        negative_out = self._encode_text(pipe, negative or "", device, sdxl)
        if sdxl:
            hidden, pooled = positive
            neg_hidden, neg_pooled = negative_out
            hidden, neg_hidden = _match_embed_length(hidden, neg_hidden)
            return hidden, neg_hidden, pooled, neg_pooled
        hidden, neg_hidden = _match_embed_length(positive, negative_out)
        return hidden, neg_hidden

    def _encode_text(self, pipe, text, device, sdxl):
        import torch

        hidden, _pooled = self._encode_one(pipe.text_encoder, pipe.tokenizer, text, device, sdxl)
        second = getattr(pipe, "text_encoder_2", None)
        if not sdxl or second is None:
            return hidden
        other, pooled = self._encode_one(second, pipe.tokenizer_2, text, device, True)
        hidden, other = _match_embed_length(hidden, other)
        return torch.cat([hidden, other], dim=-1), pooled

    def _encode_one(self, encoder, tokenizer, text, device, penultimate):
        import torch

        _quiet_rocm_attention()

        block = self._clip_token_length(encoder)
        chunks = _token_chunks(tokenizer, text, block)
        hiddens = []
        pooled = None
        for chunk in chunks:
            tokens = torch.tensor([chunk], dtype=torch.long, device=device)
            output = encoder(tokens, output_hidden_states=penultimate)
            hidden = output.hidden_states[-2] if penultimate else output[0]
            hiddens.append(hidden)
            if pooled is None:
                pooled = getattr(output, "text_embeds", None)
                if pooled is None:
                    pooled = getattr(output, "pooler_output", None)
        return torch.cat(hiddens, dim=1), pooled

    def _draw(self, model, prompt, negative, loras, steps, cfg, width, height, seed, clip, clip_g, vae=""):
        import torch

        path = Path(model)
        sdxl = checkpoint_is_sdxl(path)
        pipe = self._open_pipe(path, model, sdxl, clip, clip_g)
        pipe = self._attach_loras(pipe, loras)
        self._check_lora_weights(pipe)
        if hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing("max")
        device = gpu_device()
        self._modules_to(pipe, ("text_encoder", "text_encoder_2"), device)
        encoded = self._encode(pipe, prompt, negative, cfg, device, sdxl)
        encoded = tuple(tensor.detach().cpu() if torch.is_tensor(tensor) else tensor for tensor in encoded)
        self._modules_to(pipe, ("text_encoder", "text_encoder_2"), "cpu")
        self._empty_cache()
        self._modules_to(pipe, ("unet",), device)
        self._force_execution_device(pipe, device)
        encoded = tuple(tensor.to(device) if torch.is_tensor(tensor) else tensor for tensor in encoded)
        init_image = str(self.__dict__.get("_init_image") or "")
        init_denoise = min(1.0, max(0.05, float(self.__dict__.get("_init_denoise") or 1)))
        kwargs = {
            "num_inference_steps": steps,
            "guidance_scale": cfg,
            "width": width,
            "height": height,
            "output_type": "latent",
            "callback_on_step_end": lambda pipe, index, timestep, callback_kwargs: self._on_step(
                pipe, index, timestep, callback_kwargs, steps
            ),
            "callback_on_step_end_tensor_inputs": ["latents"],
        }
        if sdxl:
            prompt_embeds, negative_prompt_embeds, pooled, negative_pooled = encoded
            kwargs["prompt_embeds"] = prompt_embeds
            kwargs["negative_prompt_embeds"] = negative_prompt_embeds
            kwargs["pooled_prompt_embeds"] = pooled
            kwargs["negative_pooled_prompt_embeds"] = negative_pooled
        else:
            prompt_embeds, negative_prompt_embeds = encoded
            kwargs["prompt_embeds"] = prompt_embeds
            kwargs["negative_prompt_embeds"] = negative_prompt_embeds
        try:
            if init_image and Path(init_image).is_file():
                latents = self._run_img2img(pipe, kwargs, device, torch.float16, seed, init_image, init_denoise, width, height)
            else:
                latents = self._run_denoise(pipe, kwargs, device, torch.float16, seed)
        except TypeError as exc:
            if "NoneType" not in str(exc):
                raise
            self._release_modules(pipe, ("unet",))
            pipe = self._open_pipe(path, model, not sdxl, clip, clip_g)
            pipe = self._attach_loras(pipe, loras)
            self._check_lora_weights(pipe)
            if hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing("max")
            if init_image and Path(init_image).is_file():
                latents = self._run_img2img(pipe, kwargs, device, torch.float16, seed, init_image, init_denoise, width, height)
            else:
                latents = self._run_denoise(pipe, kwargs, device, torch.float16, seed)
        if not torch.isfinite(latents).all():
            self._empty_cache()
            try:
                if init_image and Path(init_image).is_file():
                    latents = self._run_img2img(pipe, kwargs, device, torch.float32, seed, init_image, init_denoise, width, height)
                else:
                    latents = self._run_denoise(pipe, kwargs, device, torch.float32, seed)
            except RuntimeError as exc:
                raise RuntimeError(
                    "This trained LoRA overflows in half precision, and full precision ran out of memory. Lower its weight and try again."
                ) from exc
        latents = latents.to("cpu").float()
        if not torch.isfinite(latents).all():
            raise RuntimeError(
                "This LoRA made the picture invalid before the VAE. Lower its weight, or train it again. Civitai LoRAs are not affected."
            )
        self._release_modules(pipe, ("unet", "text_encoder", "text_encoder_2"))
        self._mount_vae(pipe, vae, sdxl)
        hook = self.__dict__.get("on_preview")
        if hook is not None:
            hook(self._latent_preview(latents), "VAE")
        try:
            pipe.vae.to(device=device, dtype=torch.float32)
        except RuntimeError:
            pipe.vae.to(device="cpu", dtype=torch.float32)
        image = self._latents_to_image(pipe, latents)
        if self._image_is_blank(image):
            pipe.vae.to(device="cpu", dtype=torch.float32)
            image = self._latents_to_image(pipe, latents)
        if self._image_is_blank(image):
            raise RuntimeError("The VAE returned a blank picture.")
        self._release_modules(pipe, ("vae",))
        if self.__dict__.get("_keep_loaded"):
            self.hold.pipe = pipe
        else:
            self.hold.pipe = None
            self.hold.stock = None
            self.hold.pipe_sig = None
            self._empty_cache()
        if self.__dict__.get("_eye_fix"):
            image = self._redraw_eyes(image, model, prompt, negative, loras, steps, cfg, seed, clip, clip_g, vae, sdxl)
        if hook is not None:
            hook(image, "Final")
        return image

    def _redraw_eyes(self, image, model, prompt, negative, loras, steps, cfg, seed, clip, clip_g, vae, sdxl):
        from PIL import Image

        writer = self.__dict__.get("_status_write")
        if writer is not None:
            writer("Finding eyes")
        try:
            detector = _ensure_eye_model(self.__dict__.get("_eye_model") or "")
            boxes = _detect_eyes(image, detector, float(self.__dict__.get("_eye_conf") or 0.3))
        except Exception as exc:
            raise RuntimeError(f"The eye finder failed. {exc}") from exc
        if not boxes:
            if writer is not None:
                writer("No eyes found")
            return image
        eye_prompt = (self.__dict__.get("_eye_prompt") or "").strip() or "detailed eyes, sharp pupils, clear iris"
        denoise = min(0.9, max(0.15, float(self.__dict__.get("_eye_denoise") or 0.55)))
        pipe = self._open_pipe(Path(model), model, sdxl, clip, clip_g)
        pipe = self._attach_loras(pipe, loras)
        if hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing("max")
        device = gpu_device()
        self._modules_to(pipe, ("text_encoder", "text_encoder_2"), device)
        encoded = self._encode(pipe, eye_prompt, negative, cfg, device, sdxl)
        self._modules_to(pipe, ("text_encoder", "text_encoder_2"), "cpu")
        self._empty_cache()
        total = len(boxes)
        for index, box in enumerate(boxes):
            if writer is not None:
                writer(f"Redrawing eye {index + 1} of {total}")
            crop, window = _eye_window(image, box)
            guide = _fit_guide(crop, 512)
            fixed = self._refine_crop(pipe, guide, encoded, steps, cfg, denoise, None if seed is None else int(seed) + index + 1, sdxl, device)
            image = _paste_eye(image, fixed, window)
        self._release_modules(pipe, ("unet", "vae", "text_encoder", "text_encoder_2"))
        if not self.__dict__.get("_keep_loaded"):
            self.hold.pipe = None
            self.hold.stock = None
            self.hold.pipe_sig = None
            self._empty_cache()
        return image

    def _refine_crop(self, pipe, crop, encoded, steps, cfg, strength, seed, sdxl, device, as_latent=False, compute=None):
        import torch

        pixel = _pil_tensor(crop).to(device=device, dtype=torch.float32)
        self._modules_to(pipe, ("unet",), "cpu")
        self._modules_to(pipe, ("vae",), device)
        pipe.vae.to(dtype=torch.float32)
        with torch.no_grad():
            dist = pipe.vae.encode(pixel).latent_dist
            latent = dist.mode() if as_latent else dist.sample()
            latent = latent * float(getattr(pipe.vae.config, "scaling_factor", None) or 0.18215)
        self._modules_to(pipe, ("vae",), "cpu")
        self._empty_cache()
        scheduler = pipe.scheduler
        scheduler.set_timesteps(int(steps), device="cpu")
        take = max(1, min(int(steps), int(round(int(steps) * strength))))
        timesteps = scheduler.timesteps[-take:]
        noise = torch.randn(latent.shape, generator=torch.Generator(device="cpu").manual_seed(int(seed or 0)))
        latent = scheduler.add_noise(latent.cpu().float(), noise, timesteps[:1])
        self._modules_to(pipe, ("unet",), device)
        pipe.unet.to(dtype=compute or torch.float16)
        self._force_execution_device(pipe, device)
        if sdxl:
            prompt_embeds, neg_embeds, pooled, neg_pooled = encoded
        else:
            prompt_embeds, neg_embeds = encoded
            pooled = neg_pooled = None
        guided = cfg > 1 and neg_embeds is not None
        cond = torch.cat([neg_embeds, prompt_embeds], dim=0) if guided else prompt_embeds
        pooled_in = torch.cat([neg_pooled, pooled], dim=0) if guided and pooled is not None else pooled
        dtype = compute or torch.float16
        latent = latent.to(device=device, dtype=dtype)
        cond = cond.to(device=device, dtype=dtype)
        height, width = crop.size[1], crop.size[0]
        time_ids = torch.tensor([[height, width, 0, 0, height, width]], device=device, dtype=dtype)
        writer = self.__dict__.get("_status_write")
        total = len(timesteps)
        for index, timestep in enumerate(timesteps):
            step = timestep.detach().cpu()
            if as_latent and writer is not None:
                writer(f"Step {index + 1} of {total}")
            latent_in = torch.cat([latent, latent], dim=0) if guided else latent
            latent_in = scheduler.scale_model_input(latent_in.float().cpu(), step).to(device=device, dtype=dtype)
            step_ids = step.to(device=device)
            if step_ids.ndim == 0:
                step_ids = step_ids.expand(latent_in.shape[0])
            extra = {}
            if sdxl and pooled_in is not None:
                text = pooled_in.to(device=device, dtype=dtype)
                if text.shape[0] != latent_in.shape[0]:
                    text = text.expand(latent_in.shape[0], -1)
                extra["added_cond_kwargs"] = {"text_embeds": text, "time_ids": time_ids.expand(latent_in.shape[0], -1)}
            hidden = cond
            if hidden.shape[0] != latent_in.shape[0]:
                hidden = hidden.expand(latent_in.shape[0], -1, -1)
            with torch.no_grad():
                noise_pred = pipe.unet(latent_in, step_ids, encoder_hidden_states=hidden, **extra).sample
            if guided:
                uncond, text_pred = noise_pred.chunk(2)
                noise_pred = uncond + float(cfg) * (text_pred - uncond)
            latent = scheduler.step(noise_pred.float().cpu(), step, latent.float().cpu()).prev_sample
            latent = latent.to(device=device, dtype=dtype)
        self._modules_to(pipe, ("unet",), "cpu")
        self._empty_cache()
        if as_latent:
            return latent.detach().cpu().float()
        image = self._latents_to_image(pipe, latent)
        self._modules_to(pipe, ("vae",), "cpu")
        self._empty_cache()
        return image

    def _check_lora_weights(self, pipe) -> None:
        import torch

        for name, param in pipe.unet.named_parameters():
            if "lora" not in name.lower():
                continue
            if not torch.isfinite(param).all():
                raise RuntimeError(
                    "This LoRA file has invalid weights, so it cannot be used. Train it again. Civitai files are fine."
                )

    def _run_denoise(self, pipe, kwargs, device, dtype, seed):
        import torch

        pipe.unet.to(device=device, dtype=dtype)
        self._force_execution_device(pipe, device)
        local = {}
        for key, value in kwargs.items():
            if torch.is_tensor(value) and value.is_floating_point():
                local[key] = value.to(device=device, dtype=dtype)
            else:
                local[key] = value
        if seed is not None:
            local["generator"] = torch.Generator(device="cpu").manual_seed(int(seed))
        result = pipe(**local)
        images = result.images
        if not hasattr(images, "detach"):
            raise RuntimeError("The pipeline did not return latents, so the model could not be unloaded before the VAE.")
        return images.detach()

    def _run_img2img(self, pipe, kwargs, device, dtype, seed, image_path: str, strength: float, width: int, height: int):
        from PIL import Image

        image = Image.open(image_path).convert("RGB").resize((int(width), int(height)), Image.Resampling.LANCZOS)
        self._modules_to(pipe, ("unet",), "cpu")
        self._empty_cache()
        sdxl = "pooled_prompt_embeds" in kwargs
        if sdxl:
            encoded = (
                kwargs["prompt_embeds"],
                kwargs.get("negative_prompt_embeds"),
                kwargs.get("pooled_prompt_embeds"),
                kwargs.get("negative_pooled_prompt_embeds"),
            )
        else:
            encoded = (kwargs["prompt_embeds"], kwargs.get("negative_prompt_embeds"))
        return self._refine_crop(
            pipe,
            image,
            encoded,
            int(kwargs["num_inference_steps"]),
            float(kwargs["guidance_scale"]),
            float(strength),
            seed,
            sdxl,
            device,
            as_latent=True,
            compute=dtype,
        )

    def _attach_loras(self, pipe, loras):
        if hasattr(pipe, "unload_lora_weights"):
            try:
                pipe.unload_lora_weights()
            except Exception:
                pass
        if loras:
            names = []
            weights = []
            for index, (lora_path, weight) in enumerate(loras):
                name = f"lora{index}"
                pipe.load_lora_weights(lora_path, adapter_name=name)
                names.append(name)
                weights.append(weight)
            pipe.set_adapters(names, adapter_weights=weights)
        return pipe


def tensor_shapes(path: Path) -> dict[str, tuple]:
    import json
    import struct

    with path.open("rb") as handle:
        raw = handle.read(8)
        if len(raw) < 8:
            raise RuntimeError("That file is not a safetensors weight file.")
        header_len = struct.unpack("<Q", raw)[0]
        if header_len <= 0 or header_len > 20_000_000:
            raise RuntimeError("That file is not a safetensors weight file.")
        header = json.loads(handle.read(header_len))
    shapes = {}
    for key, meta in header.items():
        if key == "__metadata__" or not isinstance(meta, dict):
            continue
        shapes[key] = tuple(meta.get("shape") or [])
    return shapes


def _strip_known_prefix(key: str) -> str:
    for prefix in ("clip_vision.", "cond_stage_model.transformer.", "cond_stage_model.", "model."):
        if key.startswith(prefix):
            return key[len(prefix) :]
    return key


def _vision_format(shapes: dict[str, tuple]) -> str:
    for key in shapes:
        if key.endswith("visual.conv1.weight"):
            return "openclip"
        if key.endswith("vision_model.embeddings.patch_embedding.weight"):
            return "hf"
    if "conv1.weight" in shapes:
        return "bare"
    return ""


def _vision_family(layers: int, width: int) -> str:
    if layers >= 40 or width >= 1400:
        return "CLIP-G"
    if layers >= 30 or width >= 1200:
        return "CLIP-H"
    return "CLIP-L"


def _layer_count(shapes: dict[str, tuple], marker: str) -> int:
    layers = -1
    for key in shapes:
        if marker not in key:
            continue
        part = key.split(marker, 1)[1].split(".", 1)[0]
        if part.isdigit():
            layers = max(layers, int(part))
    return layers + 1


def _require_vision(shapes: dict[str, tuple], path: Path) -> str:
    kind = _vision_format(shapes)
    if kind:
        return kind
    if any("token_embedding.weight" in key for key in shapes):
        raise RuntimeError(
            f"{path.name} is a CLIP text encoder. Put it in the CLIP text row. "
            "The first row needs a clip_vision file, such as clip_vision_g.safetensors."
        )
    full_model = any(
        key.startswith("model.diffusion_model") or ".diffusion_model." in key or key.startswith("unet.")
        for key in shapes
    )
    if full_model:
        raise RuntimeError(
            f"{path.name} is a full image model, and it has no CLIP Vision tower inside it. "
            "Put clip_vision_g.safetensors in the first row if the text file is CLIP-G."
        )
    raise RuntimeError("That file is not a CLIP Vision model. Choose a ComfyUI clip_vision safetensors file.")


def _shape_named(shapes: dict[str, tuple], suffix: str) -> tuple:
    for key, shape in shapes.items():
        if key == suffix or key.endswith(suffix):
            return shape
    return ()


def _vision_summary(shapes: dict[str, tuple], path: Path) -> str:
    kind = _require_vision(shapes, path)
    if kind == "hf":
        conv = _shape_named(shapes, "vision_model.embeddings.patch_embedding.weight")
        pos = _shape_named(shapes, "vision_model.embeddings.position_embedding.weight")
        layers = _layer_count(shapes, "vision_model.encoder.layers.")
    else:
        conv = _shape_named(shapes, "visual.conv1.weight") or _shape_named(shapes, "conv1.weight")
        pos = _shape_named(shapes, "visual.positional_embedding") or _shape_named(shapes, "positional_embedding")
        layers = _layer_count(shapes, ".resblocks.")
    if len(conv) < 4:
        raise RuntimeError("That CLIP Vision file uses a layout RedGen cannot read.")
    patch = int(conv[-1])
    grid = int(round((pos[0] - 1) ** 0.5)) if pos else 0
    size = grid * patch if grid else 0
    family = _vision_family(layers, int(conv[0]))
    return f"CLIP Vision, {size or '?'} px, {layers} layers, {int(conv[0])} wide. Use a {family} text file with it."


def _hf_vision_to_openclip(state: dict) -> dict:
    import torch

    renamed = {}
    for key, value in state.items():
        if "vision_model." in key:
            renamed[key[key.find("vision_model.") :]] = value
        elif key.endswith("visual_projection.weight"):
            renamed["visual_projection.weight"] = value
    out = {
        "visual.conv1.weight": renamed["vision_model.embeddings.patch_embedding.weight"],
        "visual.positional_embedding": renamed["vision_model.embeddings.position_embedding.weight"],
        "visual.ln_pre.weight": renamed["vision_model.pre_layrnorm.weight"],
        "visual.ln_pre.bias": renamed["vision_model.pre_layrnorm.bias"],
        "visual.ln_post.weight": renamed["vision_model.post_layernorm.weight"],
        "visual.ln_post.bias": renamed["vision_model.post_layernorm.bias"],
    }
    klass = renamed["vision_model.embeddings.class_embedding"]
    out["visual.class_embedding"] = klass.reshape(-1) if getattr(klass, "ndim", 1) > 1 else klass
    layers = _layer_count({key: tuple(value.shape) for key, value in renamed.items() if hasattr(value, "shape")}, "encoder.layers.")
    for index in range(layers):
        source = f"vision_model.encoder.layers.{index}."
        dest = f"visual.transformer.resblocks.{index}."
        out[dest + "ln_1.weight"] = renamed[source + "layer_norm1.weight"]
        out[dest + "ln_1.bias"] = renamed[source + "layer_norm1.bias"]
        out[dest + "ln_2.weight"] = renamed[source + "layer_norm2.weight"]
        out[dest + "ln_2.bias"] = renamed[source + "layer_norm2.bias"]
        out[dest + "mlp.c_fc.weight"] = renamed[source + "mlp.fc1.weight"]
        out[dest + "mlp.c_fc.bias"] = renamed[source + "mlp.fc1.bias"]
        out[dest + "mlp.c_proj.weight"] = renamed[source + "mlp.fc2.weight"]
        out[dest + "mlp.c_proj.bias"] = renamed[source + "mlp.fc2.bias"]
        out[dest + "attn.out_proj.weight"] = renamed[source + "self_attn.out_proj.weight"]
        out[dest + "attn.out_proj.bias"] = renamed[source + "self_attn.out_proj.bias"]
        out[dest + "attn.in_proj_weight"] = torch.cat(
            [
                renamed[source + "self_attn.q_proj.weight"],
                renamed[source + "self_attn.k_proj.weight"],
                renamed[source + "self_attn.v_proj.weight"],
            ],
            dim=0,
        )
        out[dest + "attn.in_proj_bias"] = torch.cat(
            [
                renamed[source + "self_attn.q_proj.bias"],
                renamed[source + "self_attn.k_proj.bias"],
                renamed[source + "self_attn.v_proj.bias"],
            ],
            dim=0,
        )
    projection = renamed.get("visual_projection.weight")
    if projection is not None:
        width = int(out["visual.conv1.weight"].shape[0])
        out["visual.proj"] = projection.T.contiguous() if int(projection.shape[1]) == width else projection
    return out


def _openclip_vision_keys(state: dict) -> dict:
    out = {}
    for key, value in state.items():
        index = key.find("visual.")
        if index >= 0:
            out[key[index:]] = value
        elif key in {"conv1.weight", "class_embedding", "positional_embedding", "proj"} or key.startswith(
            ("ln_pre.", "ln_post.", "transformer.resblocks.")
        ):
            out["visual." + key] = value
    return out


def describe_clip_file(path: Path) -> str:
    if path.is_dir():
        return "CLIP folder"
    if path.suffix.lower() != ".safetensors":
        return path.name
    return _vision_summary(tensor_shapes(path), path)


class ClipCaptioner:
    def __init__(self, vision_path: Path, text_path: Path | None) -> None:
        import torch
        from transformers import CLIPTextConfig, CLIPTextModel, CLIPTokenizer

        _install_vision_class()
        self.torch = torch
        device = gpu_device()
        vision_state = load_vision_weights(vision_path)
        text_state = _load_weight_map(text_path) if text_path is not None else {}
        if not _has_text(vision_state) and not _has_text(text_state):
            raise RuntimeError("CLIP Vision can see the picture, but it needs the matching CLIP text file to name what it sees.")
        if not _has_text(text_state):
            text_state = vision_state
        self.vision = _OpenVision(vision_state).to(device=device, dtype=torch.float16).eval()
        text_hf = _normalize_clip_state(text_state)
        token = text_hf.get("text_model.embeddings.token_embedding.weight")
        pos = text_hf.get("text_model.embeddings.position_embedding.weight")
        if token is None or pos is None:
            raise RuntimeError("Could not read a CLIP text encoder from that file.")
        hidden = int(token.shape[1])
        layers = 0
        for key in text_hf:
            if key.startswith("text_model.encoder.layers."):
                index = key.split(".")[3]
                if index.isdigit():
                    layers = max(layers, int(index) + 1)
        first = text_hf.get("text_model.encoder.layers.0.mlp.fc1.weight")
        intermediate = int(first.shape[0]) if first is not None else hidden * 4
        heads = 12 if hidden <= 768 else 20 if hidden == 1280 else 16
        config = CLIPTextConfig(
            vocab_size=int(token.shape[0]),
            hidden_size=hidden,
            intermediate_size=intermediate,
            num_hidden_layers=layers,
            num_attention_heads=heads,
            max_position_embeddings=int(pos.shape[0]),
        )
        self.text = CLIPTextModel(config)
        self.text.load_state_dict(text_hf, strict=False)
        self.projection = text_hf.get("text_projection.weight")
        if self.projection is not None:
            self.projection = self.projection.detach().float()
        self.text.to(device=device, dtype=torch.float16).eval()
        tokenizer_dir = Path(__file__).resolve().parent / "clip_tokenizer"
        if not (tokenizer_dir / "vocab.json").is_file():
            raise RuntimeError("The CLIP word list is missing next to redgen.py.")
        self.tokenizer = CLIPTokenizer.from_pretrained(str(tokenizer_dir))
        self.device = device
        self._checked = self._match_space()

    def _match_space(self) -> str:
        vision_hidden = int(self.vision.width)
        vision_proj = None if self.vision.proj is None else int(self.vision.proj.shape[1])
        text_hidden = int(self.text.config.hidden_size)
        text_proj = None
        if self.projection is not None and self.projection.ndim == 2:
            if int(self.projection.shape[0]) == text_hidden:
                text_proj = int(self.projection.shape[1])
            elif int(self.projection.shape[1]) == text_hidden:
                text_proj = int(self.projection.shape[0])
        if vision_proj is not None and text_proj == vision_proj:
            return "projected"
        if vision_hidden == text_hidden:
            return "hidden"
        if vision_proj is not None and vision_proj == text_hidden:
            return "vision-projected"
        raise RuntimeError("That CLIP text file does not match this CLIP Vision file. Use the CLIP from the same model.")

    def close(self) -> None:
        import gc

        vision = getattr(self, "vision", None)
        text = getattr(self, "text", None)
        if vision is not None:
            vision.to("cpu")
        if text is not None:
            text.to("cpu")
        self.vision = None
        self.text = None
        self.projection = None
        gc.collect()
        if self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()

    def caption(self, image_path: Path, extras: str) -> str:
        import torch
        import torch.nn.functional as F
        from PIL import Image

        phrases = _caption_phrases(extras)
        image = Image.open(image_path)
        pixels = _clip_pixels(image, self.vision.image_size).to(device=self.device, dtype=torch.float16)
        with torch.no_grad():
            hidden, projected = self.vision(pixels)
            text_hidden, text_projected = self._encode_text(phrases)
        if self._checked == "projected":
            image_embed, text_embed = projected, text_projected
        elif self._checked == "vision-projected":
            image_embed, text_embed = projected, text_hidden
        else:
            image_embed, text_embed = hidden, text_hidden
        if image_embed is None or text_embed is None:
            raise RuntimeError("CLIP Vision and the CLIP text file did not line up.")
        image_embed = F.normalize(image_embed.float(), dim=-1)
        text_embed = F.normalize(text_embed.float(), dim=-1)
        scores = (image_embed @ text_embed.T).squeeze(0)
        order = torch.argsort(scores, descending=True)
        best = float(scores[order[0]])
        chosen = []
        for index in order.tolist():
            score = float(scores[index])
            if len(chosen) >= 14:
                break
            if len(chosen) >= 6 and score < max(0.2, best - 0.035):
                break
            chosen.append(phrases[index])
        if not chosen:
            raise RuntimeError("CLIP Vision could not describe this picture.")
        return ", ".join(chosen)

    def _encode_text(self, phrases: list[str]):
        import torch

        hidden_rows = []
        projected_rows = []
        for start in range(0, len(phrases), 32):
            batch = phrases[start : start + 32]
            tokens = self.tokenizer(batch, padding=True, truncation=True, max_length=77, return_tensors="pt")
            tokens = {key: value.to(self.device) for key, value in tokens.items()}
            with torch.no_grad():
                pooled = self.text(**tokens).pooler_output
            hidden_rows.append(pooled)
            if self.projection is not None:
                proj = self.projection.to(device=pooled.device, dtype=torch.float32)
                flat = pooled.float()
                if proj.shape[0] == flat.shape[-1]:
                    projected_rows.append(flat @ proj)
                elif proj.shape[1] == flat.shape[-1]:
                    projected_rows.append(flat @ proj.T)
        hidden = torch.cat(hidden_rows, dim=0)
        projected = torch.cat(projected_rows, dim=0) if projected_rows else None
        return hidden, projected


class _OpenVision:
    pass


def _install_vision_class() -> None:
    import torch
    import torch.nn as nn

    class QuickGELU(nn.Module):
        def forward(self, x):
            import torch

            return x * torch.sigmoid(1.702 * x)

    class Block(nn.Module):
        def __init__(self, width: int, heads: int, mlp: int, quick: bool) -> None:
            super().__init__()
            self.ln_1 = nn.LayerNorm(width)
            self.attn = nn.MultiheadAttention(width, heads, batch_first=True)
            self.ln_2 = nn.LayerNorm(width)
            self.mlp = nn.Sequential(nn.Linear(width, mlp), QuickGELU() if quick else nn.GELU(), nn.Linear(mlp, width))

        def forward(self, x):
            normed = self.ln_1(x)
            hidden, _ = self.attn(normed, normed, normed, need_weights=False)
            x = x + hidden
            x = x + self.mlp(self.ln_2(x))
            return x

    class OpenVision(nn.Module):
        def __init__(self, state: dict) -> None:
            import torch
            import torch.nn as nn

            super().__init__()
            named = {_strip_known_prefix(key): value for key, value in state.items()}
            conv = named.get("visual.conv1.weight")
            pos = named.get("visual.positional_embedding")
            if conv is None or pos is None:
                raise RuntimeError("That file is not a CLIP Vision model. Choose a ComfyUI clip_vision safetensors file.")
            width = int(conv.shape[0])
            patch = int(conv.shape[-1])
            grid = int(round((int(pos.shape[0]) - 1) ** 0.5))
            if grid * grid + 1 != int(pos.shape[0]):
                raise RuntimeError("That CLIP Vision file has an unsupported position table.")
            mlp_key = next(key for key in named if key.endswith("resblocks.0.mlp.c_fc.weight"))
            mlp = int(named[mlp_key].shape[0])
            layers = 0
            for key in named:
                marker = ".resblocks."
                if marker in key:
                    index = key.split(marker, 1)[1].split(".", 1)[0]
                    if index.isdigit():
                        layers = max(layers, int(index) + 1)
            heads = 12 if width <= 768 else 16
            quick = layers <= 24
            self.width = width
            self.image_size = grid * patch
            self.conv = nn.Conv2d(3, width, kernel_size=patch, stride=patch, bias=False)
            self.class_embedding = nn.Parameter(torch.empty(width))
            self.positional_embedding = nn.Parameter(torch.empty(int(pos.shape[0]), width))
            self.ln_pre = nn.LayerNorm(width)
            self.blocks = nn.ModuleList(Block(width, heads, mlp, quick) for _ in range(layers))
            self.ln_post = nn.LayerNorm(width)
            proj = named.get("visual.proj")
            self.proj = nn.Parameter(torch.empty_like(proj)) if proj is not None else None
            mapped = {
                "conv.weight": conv,
                "class_embedding": named["visual.class_embedding"],
                "positional_embedding": pos,
                "ln_pre.weight": named["visual.ln_pre.weight"],
                "ln_pre.bias": named["visual.ln_pre.bias"],
                "ln_post.weight": named["visual.ln_post.weight"],
                "ln_post.bias": named["visual.ln_post.bias"],
            }
            if proj is not None:
                mapped["proj"] = proj
            for index in range(layers):
                root = f"visual.transformer.resblocks.{index}."
                dest = f"blocks.{index}."
                mapped[dest + "ln_1.weight"] = named[root + "ln_1.weight"]
                mapped[dest + "ln_1.bias"] = named[root + "ln_1.bias"]
                mapped[dest + "ln_2.weight"] = named[root + "ln_2.weight"]
                mapped[dest + "ln_2.bias"] = named[root + "ln_2.bias"]
                mapped[dest + "mlp.0.weight"] = named[root + "mlp.c_fc.weight"]
                mapped[dest + "mlp.0.bias"] = named[root + "mlp.c_fc.bias"]
                mapped[dest + "mlp.2.weight"] = named[root + "mlp.c_proj.weight"]
                mapped[dest + "mlp.2.bias"] = named[root + "mlp.c_proj.bias"]
                mapped[dest + "attn.in_proj_weight"] = named[root + "attn.in_proj_weight"]
                mapped[dest + "attn.in_proj_bias"] = named[root + "attn.in_proj_bias"]
                mapped[dest + "attn.out_proj.weight"] = named[root + "attn.out_proj.weight"]
                mapped[dest + "attn.out_proj.bias"] = named[root + "attn.out_proj.bias"]
            self.load_state_dict(mapped, strict=True)

        def forward(self, pixels):
            import torch

            batch = pixels.shape[0]
            hidden = self.conv(pixels)
            hidden = hidden.reshape(batch, self.width, -1).permute(0, 2, 1)
            token = self.class_embedding.to(dtype=hidden.dtype).view(1, 1, -1).expand(batch, -1, -1)
            hidden = torch.cat([token, hidden], dim=1)
            hidden = hidden + self.positional_embedding.to(dtype=hidden.dtype)
            hidden = self.ln_pre(hidden)
            for block in self.blocks:
                hidden = block(hidden)
            pooled = self.ln_post(hidden[:, 0, :])
            projected = None if self.proj is None else pooled @ self.proj.to(dtype=pooled.dtype)
            return pooled, projected

    globals()["_OpenVision"] = OpenVision
    globals()["_QuickGELU"] = QuickGELU


def load_vision_weights(path: Path) -> dict:
    if path.suffix.lower() == ".safetensors":
        shapes = tensor_shapes(path)
        kind = _require_vision(shapes, path)
        from safetensors import safe_open

        raw = {}
        with safe_open(str(path), framework="pt", device="cpu") as handle:
            for key in handle.keys():
                if "vision_model." in key or "visual." in key or key.endswith("visual_projection.weight") or key in {
                    "conv1.weight",
                    "class_embedding",
                    "positional_embedding",
                    "proj",
                } or key.startswith(("ln_pre.", "ln_post.", "transformer.resblocks.")):
                    raw[key] = handle.get_tensor(key)
    else:
        raw = _load_weight_map(path)
        shapes = {key: tuple(value.shape) for key, value in raw.items() if hasattr(value, "shape")}
        kind = _require_vision(shapes, path)
    if kind == "hf":
        return _hf_vision_to_openclip(raw)
    return _openclip_vision_keys(raw)


def _load_weight_map(path: Path) -> dict:
    import torch

    if path is None:
        return {}
    if path.is_dir():
        raise RuntimeError("Pick the CLIP Vision .safetensors file, not a folder.")
    if path.suffix.lower() == ".safetensors":
        from safetensors.torch import load_file

        return load_file(str(path))
    try:
        state = torch.load(str(path), map_location="cpu", weights_only=True)
    except TypeError:
        state = torch.load(str(path), map_location="cpu")
    if hasattr(state, "state_dict"):
        state = state.state_dict()
    if isinstance(state, dict) and isinstance(state.get("state_dict"), dict):
        state = state["state_dict"]
    if not isinstance(state, dict):
        raise RuntimeError("That CLIP file is not a weight file.")
    return state


def _has_text(state: dict) -> bool:
    for key in state:
        name = _strip_known_prefix(key)
        if name in ("token_embedding.weight", "text_model.embeddings.token_embedding.weight") or name.endswith("token_embedding.weight"):
            return True
    return False


def _caption_phrases(extras: str) -> list[str]:
    phrases = list(CLIP_TAGS)
    seen = {item.lower() for item in phrases}
    for piece in extras.replace("\n", ",").split(","):
        phrase = " ".join(piece.strip().split())
        if len(phrase) < 2 or phrase.lower() in seen:
            continue
        if len(phrase) > 80:
            continue
        phrases.append(phrase)
        seen.add(phrase.lower())
    return phrases


def _clip_pixels(image, size: int):
    import numpy as np
    import torch
    from PIL import Image

    image = image.convert("RGB")
    width, height = image.size
    scale = size / max(min(width, height), 1)
    resized = image.resize((max(size, round(width * scale)), max(size, round(height * scale))), Image.Resampling.BICUBIC)
    left = max(0, (resized.width - size) // 2)
    top = max(0, (resized.height - size) // 2)
    resized = resized.crop((left, top, left + size, top + size))
    values = torch.from_numpy(np.asarray(resized, dtype="float32")) / 255.0
    mean = torch.tensor([0.48145466, 0.4578275, 0.40821073])
    std = torch.tensor([0.26862954, 0.26130258, 0.27577711])
    values = (values - mean) / std
    return values.permute(2, 0, 1).unsqueeze(0)


LLAMA_RUNNER = "https://github.com/ggml-org/llama.cpp/releases/download/b12554/llama-b12554-bin-win-vulkan-x64.zip"


def _llama_home() -> Path:
    return CONFIG.parent / "llama"


def _find_llama_cli() -> Path | None:
    import shutil

    for name in ("llama-mtmd-cli", "llama-mtmd-cli.exe"):
        found = shutil.which(name)
        if found:
            return Path(found)
    home = _llama_home()
    if home.is_dir():
        hits = sorted(home.rglob("llama-mtmd-cli.exe"))
        if hits:
            return hits[0]
    return None


def ensure_llama_cli(notify) -> Path:
    found = _find_llama_cli()
    if found is not None:
        return found
    import urllib.request
    import zipfile

    home = _llama_home()
    home.mkdir(parents=True, exist_ok=True)
    archive = home / "llama-vulkan.zip"
    notify("Downloading the JoyCaption runner. This file is already built, so nothing is compiled.")
    try:
        urllib.request.urlretrieve(LLAMA_RUNNER, archive)
    except OSError as exc:
        raise RuntimeError("Could not download the JoyCaption runner. Leave the internet on and try again.") from exc
    try:
        with zipfile.ZipFile(archive) as packed:
            packed.extractall(home)
    except zipfile.BadZipFile as exc:
        archive.unlink(missing_ok=True)
        raise RuntimeError("The JoyCaption runner download was damaged. Try again.") from exc
    archive.unlink(missing_ok=True)
    found = _find_llama_cli()
    if found is None:
        raise RuntimeError("The runner downloaded, but llama-mtmd-cli.exe was not in it.")
    return found


class JoyCaptioner:
    def __init__(self, model_path: Path, mmproj_path: Path, notify=None) -> None:
        if not model_path.is_file():
            raise RuntimeError("Pick the JoyCaption Beta One GGUF.")
        if not mmproj_path.is_file():
            raise RuntimeError("Pick llama-joycaption-beta-one-llava-mmproj-model-f16.gguf.")
        self.model_path = model_path
        self.mmproj_path = mmproj_path
        self.cli = ensure_llama_cli(notify or (lambda _text: None))

    def close(self) -> None:
        return None

    def caption(self, image_path: Path, instruction: str) -> str:
        prompt = instruction.strip() or "Write a detailed caption for this image in one line of comma-separated phrases."
        text, error = self._run(image_path, prompt, "99")
        if not text:
            text, error = self._run(image_path, prompt, "0")
        if not text:
            raise RuntimeError(error or "JoyCaption returned an empty caption.")
        return _clean_caption(text)

    def _run(self, image_path: Path, prompt: str, layers: str) -> tuple[str, str]:
        import subprocess

        command = [
            str(self.cli),
            "-m",
            str(self.model_path),
            "--mmproj",
            str(self.mmproj_path),
            "--image",
            str(image_path),
            "-p",
            prompt,
            "-n",
            "220",
            "--temp",
            "0.4",
            "-c",
            "8192",
            "-ngl",
            layers,
            "-lv",
            "0",
        ]
        flags = {}
        if sys.platform == "win32":
            flags["creationflags"] = 0x08000000
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
                cwd=str(self.cli.parent),
                **flags,
            )
        except OSError as exc:
            return "", str(exc)
        blob = (completed.stdout or "") + "\n" + (completed.stderr or "")
        text = _joy_answer(completed.stdout or "", completed.stderr or "", prompt)
        if completed.returncode != 0 and not text:
            return "", blob[-700:] or "JoyCaption stopped."
        return text, blob[-700:]


def _joy_answer(stdout: str, stderr: str, prompt: str) -> str:
    import re

    text = _joy_keep(stdout, prompt)
    if text:
        return text
    return _joy_keep(stderr, prompt)


def _joy_keep(blob: str, prompt: str) -> str:
    import re

    if prompt and prompt in blob:
        blob = blob.rsplit(prompt, 1)[-1]
    kept = []
    log_line = re.compile(r"^\d+\.\d+\.\d+\.\d+\s+[IWE]\s")
    for raw in blob.splitlines():
        line = raw.strip()
        if not line or line == prompt:
            continue
        if log_line.match(line):
            continue
        lower = line.lower()
        if "experimental cli" in lower or "loading model" in lower or "mtmd batch" in lower:
            continue
        if lower in {"how are you?", "how are you"}:
            continue
        if "start_header_id" in line or "end_header_id" in line or "<|eot_id|>" in line or "<|" in line:
            line = re.sub(r"<\|[^|]+?\|>", " ", line)
            line = re.sub(r"^(how are you\??|assistant|user|system)\b", "", line, flags=re.IGNORECASE)
            line = " ".join(line.split()).strip(" ?.!,")
            if len(line) < 12:
                continue
        kept.append(line)
    text = " ".join(kept).strip()
    text = re.sub(r"<\|[^|]+?\|>", " ", text)
    text = re.sub(r"^(assistant|user|system)\b", "", text, flags=re.IGNORECASE)
    text = " ".join(text.split())
    if text.lower().startswith("how are you"):
        text = text[len("how are you") :].lstrip(" ?.!,")
    return text.strip()


def kobold_ping(url: str, key: str) -> str:
    import json
    import urllib.error
    import urllib.request

    base = url.strip().rstrip("/")
    if not base.startswith("http://") and not base.startswith("https://"):
        raise RuntimeError("The address needs to start with http://")
    headers = {"Accept": "application/json"}
    if key.strip():
        headers["Authorization"] = f"Bearer {key.strip()}"
    request = urllib.request.Request(base + "/v1/models", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError("Start KoboldCpp, then try again. Nothing answered at that address.") from exc
    models = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(models, list) and models and isinstance(models[0], dict):
        return str(models[0].get("id") or "connected")
    return "connected"


def kobold_caption(url: str, key: str, image_path: Path, instruction: str) -> str:
    import base64
    import io
    import json
    import urllib.error
    import urllib.request

    from PIL import Image

    base = url.strip().rstrip("/")
    picture = Image.open(image_path).convert("RGB")
    picture.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if key.strip():
        headers["Authorization"] = f"Bearer {key.strip()}"
    prompt = instruction.strip()
    attempts = (
        (
            "/api/v1/generate",
            {
                "prompt": prompt + "\nCaption:",
                "images": [encoded],
                "max_length": 160,
                "max_context_length": 4096,
                "temperature": 0.3,
                "top_p": 0.9,
                "rep_pen": 1.1,
                "stop_sequence": ["\n\n"],
                "quiet": True,
            },
        ),
        (
            "/v1/chat/completions",
            {
                "model": "koboldcpp",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + encoded}},
                        ],
                    }
                ],
                "max_tokens": 160,
                "temperature": 0.3,
            },
        ),
        ("/sdapi/v1/interrogate", {"image": encoded, "model": "clip"}),
    )
    errors: list[str] = []
    for path, body in attempts:
        request = urllib.request.Request(
            base + path,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:240]
            if exc.code == 401:
                raise RuntimeError("Kobold refused the API key.") from exc
            if "vision" in detail.lower() or "mmproj" in detail.lower():
                raise RuntimeError("Kobold has no vision model. Load an mmproj file in KoboldCpp.") from exc
            errors.append(f"{path} returned {exc.code}")
            continue
        except urllib.error.URLError as exc:
            raise RuntimeError("Kobold stopped answering. Leave KoboldCpp open while captioning.") from exc
        text = _caption_from_payload(payload)
        if text:
            return text
        errors.append(f"{path} returned an empty caption")
    raise RuntimeError("Kobold could not caption this picture. " + " ".join(errors))


def _caption_from_payload(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    results = payload.get("results")
    if isinstance(results, list) and results and isinstance(results[0], dict):
        return _clean_caption(str(results[0].get("text") or ""))
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message") or {}
        content = message.get("content") if isinstance(message, dict) else ""
        if isinstance(content, list):
            content = " ".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
        return _clean_caption(str(content or choices[0].get("text") or ""))
    return _clean_caption(str(payload.get("caption") or ""))


def _clean_caption(text: str) -> str:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return ""
    line = lines[0]
    lowered = line.lower()
    for prefix in ("caption:", "output:", "description:"):
        if lowered.startswith(prefix):
            line = line[len(prefix) :].strip()
            break
    return " ".join(line.strip(" \"'`").split())[:700]


def aspect_buckets(base: int) -> list[tuple[int, int]]:
    step = 64
    base = max(step, int(base) - int(base) % step)
    area = base * base
    limit = base * 2
    found: set[tuple[int, int]] = set()
    width = step
    while width <= limit:
        height = int(round(area / width / step)) * step
        height = max(step, min(limit, height))
        found.add((width, height))
        found.add((height, width))
        width += step
    return sorted(found)


def fit_bucket(image, buckets: list[tuple[int, int]]):
    from PIL import Image
    width, height = image.size
    aspect = width / max(height, 1)
    bucket_w, bucket_h = min(buckets, key=lambda item: abs((item[0] / item[1]) - aspect))
    scale = max(bucket_w / width, bucket_h / height)
    resized_w = max(bucket_w, int(round(width * scale)))
    resized_h = max(bucket_h, int(round(height * scale)))
    image = image.resize((resized_w, resized_h), Image.Resampling.LANCZOS)
    left = max(0, (resized_w - bucket_w) // 2)
    top = max(0, (resized_h - bucket_h) // 2)
    return image.crop((left, top, left + bucket_w, top + bucket_h)), bucket_w, bucket_h


def training_caption(subject: str, trigger: str, caption: str, stem: str) -> str:
    trigger = trigger.strip()
    caption = caption.strip()
    if subject == "style":
        if trigger and trigger.lower() not in caption.lower():
            caption = f"{caption}, {trigger}".strip(", ") if caption else trigger
        return caption or stem
    if trigger and trigger.lower() not in caption.lower():
        caption = f"{trigger}, {caption}".strip(", ") if caption else trigger
    return caption or trigger or stem


def train_job(job: dict, write) -> None:
    import random

    import torch
    import torch.nn.functional as F
    from PIL import Image

    ensure_peft()
    engine = object.__new__(App)
    engine.hold = Hold()
    engine._status_write = write
    folder = Path(job["folder"])
    images = [
        path
        for path in sorted(folder.iterdir())
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    ]
    if not images:
        raise RuntimeError("That folder has no pictures.")
    rank = int(job["rank"])
    alpha = int(job.get("alpha") or rank)
    steps = int(job["steps"])
    size = int(job["resolution"])
    trigger = (job.get("trigger") or "").strip()
    subject = job.get("subject") if job.get("subject") in {"character", "style", "concept"} else "character"
    use_buckets = bool(job.get("buckets", True))
    checkpoint = bool(job.get("checkpoint", True))
    cache_latents = bool(job.get("cache_latents", True))
    no_half = bool(job.get("no_half_vae", True))
    device = gpu_device()
    model = job["model"]
    sdxl = checkpoint_is_sdxl(Path(model))
    write(f"Loading {Path(model).name}")
    pipe = engine._open_pipe(Path(model), model, sdxl, job.get("clip") or "", job.get("clip_g") or "")
    if no_half:
        pipe.vae.to(device=device, dtype=torch.float32)
    else:
        pipe.vae.to(device)
    engine._modules_to(pipe, ("text_encoder", "text_encoder_2"), device)
    buckets = aspect_buckets(size) if use_buckets else [(size, size)]
    write(
        f"{subject} · rank {rank} · alpha {alpha} · "
        + ("aspect buckets" if use_buckets else "square crop")
        + (" · no half VAE" if no_half else "")
    )
    pairs = []
    used_buckets: set[tuple[int, int]] = set()
    import numpy as np

    for path in images:
        caption_file = path.with_suffix(".txt")
        caption = caption_file.read_text(encoding="utf-8").strip() if caption_file.is_file() else ""
        caption = training_caption(subject, trigger, caption, path.stem)
        image = Image.open(path).convert("RGB")
        if use_buckets:
            image, bucket_w, bucket_h = fit_bucket(image, buckets)
        else:
            width, height = image.size
            side = min(width, height)
            left = (width - side) // 2
            top = (height - side) // 2
            image = image.crop((left, top, left + side, top + side)).resize((size, size), Image.Resampling.LANCZOS)
            bucket_w, bucket_h = size, size
        used_buckets.add((bucket_w, bucket_h))
        pixel = torch.from_numpy(np.asarray(image, dtype="float32")).permute(2, 0, 1).unsqueeze(0) / 127.5 - 1
        if cache_latents:
            with torch.no_grad():
                latent = pipe.vae.encode(pixel.to(device=device, dtype=pipe.vae.dtype)).latent_dist.sample()
                latent = latent * pipe.vae.config.scaling_factor
            stored = latent.detach().cpu()
        else:
            stored = pixel.cpu()
        encoded = engine._encode(pipe, caption, "", 1, device, sdxl)
        if sdxl:
            prompt_embeds, _, pooled, _ = encoded
            time_ids = torch.tensor(
                [[bucket_h, bucket_w, 0, 0, bucket_h, bucket_w]],
                dtype=prompt_embeds.dtype,
            )
            pairs.append((stored, prompt_embeds.detach().cpu(), pooled.detach().cpu(), time_ids))
        else:
            pairs.append((stored, encoded[0].detach().cpu(), None, None))
        write(f"Prepared {path.name} at {bucket_w}×{bucket_h}")
    if cache_latents:
        engine._release_modules(pipe, ("vae", "text_encoder", "text_encoder_2"))
    else:
        engine._release_modules(pipe, ("text_encoder", "text_encoder_2"))
    from diffusers import DDPMScheduler
    from peft import LoraConfig

    pipe.unet.to(device)
    if checkpoint and hasattr(pipe.unet, "enable_gradient_checkpointing"):
        pipe.unet.enable_gradient_checkpointing()
    elif hasattr(pipe.unet, "disable_gradient_checkpointing"):
        pipe.unet.disable_gradient_checkpointing()
    pipe.unet.add_adapter(LoraConfig(r=rank, lora_alpha=alpha, target_modules=["to_q", "to_k", "to_v", "to_out.0"]))
    pipe.unet.train()
    pin_half_embeddings(pipe.unet)
    trainable = [param for param in pipe.unet.parameters() if param.requires_grad]
    masters = [param.detach().float().clone().requires_grad_(True) for param in trainable]
    opt = torch.optim.AdamW(masters, lr=float(job["lr"]), foreach=False)
    scheduler = DDPMScheduler.from_config(pipe.scheduler.config)
    unet_dtype = next(param.dtype for param in pipe.unet.parameters() if not param.requires_grad)
    write(f"Training {len(pairs)} pictures in {len(used_buckets)} bucket sizes")
    scaling = float(pipe.vae.config.scaling_factor) if pipe.vae is not None else 0.18215
    skipped = 0
    for step in range(steps):
        stored, prompt_embeds, pooled, time_ids = random.choice(pairs)
        prompt_embeds = prompt_embeds.to(device=device, dtype=unet_dtype)
        if cache_latents:
            latent = stored.to(device=device, dtype=torch.float32)
        else:
            with torch.no_grad():
                latent = pipe.vae.encode(stored.to(device=device, dtype=pipe.vae.dtype)).latent_dist.sample()
                latent = latent * scaling
            latent = latent.float()
        noise = torch.randn_like(latent)
        timestep = torch.randint(0, scheduler.config.num_train_timesteps, (1,), device=device).long()
        noisy = scheduler.add_noise(latent, noise, timestep).to(dtype=unet_dtype)
        if sdxl:
            pred = pipe.unet(
                noisy,
                timestep,
                prompt_embeds,
                added_cond_kwargs={
                    "text_embeds": pooled.to(device=device, dtype=unet_dtype),
                    "time_ids": time_ids.to(device=device, dtype=unet_dtype),
                },
            ).sample
        else:
            pred = pipe.unet(noisy, timestep, prompt_embeds).sample
        if not torch.isfinite(pred).all():
            opt.zero_grad(set_to_none=True)
            skipped += 1
            write(f"Step {step + 1} skipped because the picture became invalid")
            continue
        loss = F.mse_loss(pred.float(), noise)
        if not torch.isfinite(loss):
            opt.zero_grad(set_to_none=True)
            skipped += 1
            continue
        loss.backward()
        grads_ok = True
        for param, master in zip(trainable, masters):
            grad = None if param.grad is None else param.grad.detach().float()
            param.grad = None
            if grad is None or not torch.isfinite(grad).all():
                grads_ok = False
                master.grad = None
                continue
            master.grad = grad
        if not grads_ok:
            opt.zero_grad(set_to_none=True)
            skipped += 1
            continue
        torch.nn.utils.clip_grad_norm_(masters, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        with torch.no_grad():
            for param, master in zip(trainable, masters):
                param.copy_(master.to(dtype=param.dtype))
        if step % 5 == 0 or step + 1 == steps:
            write(f"Step {step + 1}/{steps}  loss {loss.item():.4f}")
    if skipped > steps // 2:
        raise RuntimeError("Training kept producing invalid numbers. Lower the learning rate and try again.")
    save_kohya_lora(Path(job["out"]), pipe.unet, rank, alpha, str(job.get("trigger") or ""))
    engine._release_modules(pipe, ("unet",))
    engine.hold.pipe = None
    engine._empty_cache()
    write(f"Saved {job['out']}")


def pin_half_embeddings(unet) -> None:
    import torch

    def hook(module, args):
        dtype = module.linear_1.weight.dtype
        fixed = []
        for arg in args:
            if torch.is_tensor(arg) and arg.is_floating_point() and arg.dtype != dtype:
                fixed.append(arg.to(dtype=dtype))
            else:
                fixed.append(arg)
        return tuple(fixed)

    for module in unet.modules():
        linear = getattr(module, "linear_1", None)
        if isinstance(linear, torch.nn.Linear):
            module.register_forward_pre_hook(hook)


def save_kohya_lora(path: Path, unet, rank: int, alpha: int, trigger: str = "") -> None:
    import torch
    from peft.utils import get_peft_model_state_dict
    from safetensors.torch import save_file

    state = get_peft_model_state_dict(unet)
    tensors = {}
    for key, value in state.items():
        if not torch.isfinite(value).all():
            raise RuntimeError("Training produced invalid LoRA weights. Lower the learning rate and train again.")
        name = key.replace("base_model.model.", "").replace(".default.", ".")
        if name.endswith(".lora_A.weight"):
            body = name[: -len(".lora_A.weight")]
            prefix = "lora_unet_" + body.replace(".", "_")
            tensors[prefix + ".lora_down.weight"] = value.detach().float().cpu().contiguous()
            tensors[prefix + ".alpha"] = torch.tensor(float(alpha))
        elif name.endswith(".lora_B.weight"):
            body = name[: -len(".lora_B.weight")]
            prefix = "lora_unet_" + body.replace(".", "_")
            tensors[prefix + ".lora_up.weight"] = value.detach().float().cpu().contiguous()
    if not any(key.endswith(".lora_up.weight") for key in tensors):
        raise RuntimeError("Nothing was trained.")
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file(
        tensors,
        str(path),
        metadata={
            "ss_network_module": "networks.lora",
            "ss_network_dim": str(rank),
            "ss_network_alpha": str(alpha),
            "modelspec.trigger_phrase": trigger.strip(),
            "format": "pt",
        },
    )


def _save_preview(preview: Path, status: Path, image, caption: str) -> None:
    preview.parent.mkdir(parents=True, exist_ok=True)
    temporary = preview.with_suffix(".part.png")
    image.save(temporary)
    temporary.replace(preview)
    status.write_text(caption, encoding="utf-8")


def run_job(path: str) -> int:
    import traceback

    ensure_peft()
    job = json.loads(Path(path).read_text(encoding="utf-8"))
    status = Path(job["status"])
    if job.get("kind") == "train":

        def write(message: str) -> None:
            status.write_text(message, encoding="utf-8")
            print(message, flush=True)

        try:
            train_job(job, write)
            write("done")
            return 0
        except Exception as exc:
            import traceback

            write(f"error\n{exc}")
            traceback.print_exc()
            return 1
    if job.get("kind") == "anima_train":

        def write(message: str) -> None:
            status.write_text(message, encoding="utf-8")
            print(message, flush=True)

        try:
            import anima

            anima.train(job, write)
            write("done")
            return 0
        except Exception as exc:
            import traceback

            write(f"error\n{exc}")
            traceback.print_exc()
            return 1
    preview = Path(job["preview"])

    def write(message: str) -> None:
        status.write_text(message, encoding="utf-8")
        print(message, flush=True)

    if job.get("kind") == "anima":
        import anima

        try:
            anima.draw(job, write)
            return 0
        except Exception as exc:
            import traceback

            write(f"error\n{exc}")
            traceback.print_exc()
            return 1

    engine = object.__new__(App)
    engine.hold = Hold()
    return render_image_job(engine, job, write)


def render_image_job(engine, job: dict, write) -> int:
    import traceback

    preview = Path(job["preview"])
    status = Path(job["status"])
    engine._status_write = write
    engine.on_preview = lambda image, caption: _save_preview(preview, status, image, caption)
    engine._vae_tile = bool(job.get("vae_tile"))
    engine._vae_tile_size = int(job.get("vae_tile_size") or 512)
    engine._vae_tile_overlap = int(job.get("vae_tile_overlap") or 64)
    engine._eye_fix = bool(job.get("eye_fix"))
    engine._eye_model = job.get("eye_model") or ""
    engine._eye_denoise = float(job.get("eye_denoise") or 0.55)
    engine._eye_conf = float(job.get("eye_conf") or 0.3)
    engine._eye_prompt = job.get("eye_prompt") or "detailed eyes, sharp pupils, clear iris"
    engine._init_image = job.get("init_image") or ""
    engine._init_denoise = float(job.get("init_denoise") or 1)
    engine._keep_loaded = bool(job.get("keep"))
    try:
        write("load")
        image = engine._draw(
            job["model"],
            job["prompt"],
            job["negative"],
            [tuple(item) for item in job["loras"]],
            int(job["steps"]),
            float(job["cfg"]),
            int(job["width"]),
            int(job["height"]),
            job["seed"],
            job["clip"],
            job["clip_g"],
            job.get("vae") or "",
        )
        out = Path(job["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out)
        note = job["prompt"] if not job["negative"] else f"{job['prompt']}\n\nNegative:\n{job['negative']}"
        out.with_suffix(".txt").write_text(note, encoding="utf-8")
        write("done")
        return 0
    except Exception as exc:
        if not job.get("keep"):
            engine.hold.pipe = None
            engine.hold.stock = None
            engine.hold.pipe_sig = None
        write(f"error\n{exc}")
        traceback.print_exc()
        return 1


def serve_sd() -> int:
    ensure_peft()
    engine = object.__new__(App)
    engine.hold = Hold()
    while True:
        try:
            line = sys.stdin.readline()
        except Exception:
            return 0
        if not line:
            return 0
        command = line.strip()
        if not command or command == "quit":
            return 0
        try:
            job = json.loads(Path(command).read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"error\nCould not read the picture job. {exc}", flush=True)
            continue
        status = Path(job["status"])

        def write(message: str, status=status) -> None:
            status.write_text(message, encoding="utf-8")
            print(message, flush=True)

        render_image_job(engine, job, write)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--sd-serve":
        raise SystemExit(serve_sd())
    if len(sys.argv) >= 2 and sys.argv[1] == "--anima-serve":
        import anima

        raise SystemExit(anima.serve())
    if len(sys.argv) >= 3 and sys.argv[1] == "--job":
        raise SystemExit(run_job(sys.argv[2]))
    print(f"RedWright build {BUILD} — {Path(__file__).resolve()}", flush=True)
    App().mainloop()
