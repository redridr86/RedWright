"""Anima text-to-image. Kept off the Stable Diffusion path.

Base, Aesthetic, and Turbo are 2B Cosmos DiTs. They need the Qwen3 0.6B
text encoder and the Qwen-Image VAE. Flow-match Euler uses shift 3.
Base and Aesthetic want about 30 steps and CFG 4. Turbo wants CFG 1 and
about 10 steps. A bigger 2.9B or 3.8B merge is loaded when its block count
differs from the 28-block base.
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "anima_tools"
TOKEN_ROOT = ROOT / "anima_tokenizers"
WEIGHTS = {
    "text": (
        "qwen_3_06b_base.safetensors",
        "https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/text_encoders/qwen_3_06b_base.safetensors",
        800_000_000,
    ),
    "vae": (
        "qwen_image_vae.safetensors",
        "https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/vae/qwen_image_vae.safetensors",
        150_000_000,
    ),
}
TOKEN_FILES = (
    "tokenizer/tokenizer.json",
    "tokenizer/tokenizer_config.json",
    "tokenizer/chat_template.jinja",
    "t5_tokenizer/tokenizer.json",
    "t5_tokenizer/tokenizer_config.json",
)
TOKEN_URL = "https://huggingface.co/circlestone-labs/Anima-Base-v1.0-Diffusers/resolve/main/"


def snap_dim(value: int) -> int:
    clamped = max(512, min(1536, int(value)))
    return clamped - (clamped % 32)


def preset_values(name: str) -> tuple[int, float]:
    if name == "Turbo":
        return 10, 1.0
    return 30, 4.0


_PROBE = """
import sys
import traceback
print("python", sys.executable)
try:
    import torch
    print("torch", torch.__version__)
except Exception:
    print("torch import failed")
    traceback.print_exc()
try:
    import transformers
    print("transformers", transformers.__version__)
except Exception:
    print("transformers import failed")
    traceback.print_exc()
try:
    import diffusers
    print("diffusers", getattr(diffusers, "__version__", "?"), diffusers.__file__)
    from diffusers import AnimaAutoBlocks
    print("AnimaAutoBlocks", AnimaAutoBlocks.__name__)
except Exception:
    print("Anima import failed")
    traceback.print_exc()
    raise SystemExit(1)
"""


def _runtime_env() -> dict:
    env = os.environ.copy()
    previous = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT / "anima_runtime") + (os.pathsep + previous if previous else "")
    return env


def _probe(python: str, env: dict) -> tuple[bool, str]:
    result = subprocess.run([python, "-c", _PROBE], capture_output=True, text=True, env=env)
    detail = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    return result.returncode == 0, detail[-2500:]


def runtime(status=None) -> tuple[str, dict]:
    python = sys.executable
    env = _runtime_env()
    ok, _detail = _probe(python, env)
    if ok:
        return python, env
    if status:
        status("Installing the Anima runtime into the app folder. This happens once and can take several minutes.")
    target = ROOT / "anima_runtime"
    target.mkdir(parents=True, exist_ok=True)
    command = [
        python,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--target",
        str(target),
        "--no-deps",
        "https://github.com/huggingface/diffusers/archive/refs/heads/main.zip",
        "transformers>=4.57",
        "huggingface-hub>=1.0",
        "tokenizers>=0.22",
        "safetensors",
        "regex",
        "tqdm",
        "pyyaml",
        "packaging",
        "filelock",
        "requests",
        "fsspec",
        "httpx2",
        "httpcore2",
        "anyio",
        "idna",
        "truststore",
        "typing_extensions",
        "sentencepiece",
        "protobuf",
        "accelerate",
        "peft>=0.17.0",
    ]
    installed = subprocess.run(command, capture_output=True, text=True)
    if installed.returncode != 0:
        tail = ((installed.stdout or "") + "\n" + (installed.stderr or "")).strip()
        raise RuntimeError(tail[-2500:] or "pip could not install the Anima runtime.")
    ok, detail = _probe(python, env)
    if not ok:
        raise RuntimeError(detail or "AnimaAutoBlocks still did not import.")
    return python, env


def weight_path(kind: str) -> Path:
    return ROOT / WEIGHTS[kind][0]


def _download_file(url: str, dest: Path, minimum: int, status) -> None:
    part = dest.with_name(dest.name + ".part")
    if status:
        status(f"Downloading {dest.name} into the app folder")
    request = urllib.request.Request(url, headers={"User-Agent": "RedWright"})
    with urllib.request.urlopen(request, timeout=60) as response, part.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        reported = -1
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            done += len(chunk)
            if status and total:
                percent = int(done * 100 / total)
                if percent >= reported + 10:
                    reported = percent
                    status(f"{dest.name} {percent}%")
    if not part.is_file() or part.stat().st_size < minimum:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"{dest.name} did not finish downloading.")
    part.replace(dest)


def ensure_weights(status=None) -> tuple[Path, Path]:
    saved = []
    for kind in ("text", "vae"):
        name, url, minimum = WEIGHTS[kind]
        dest = ROOT / name
        if dest.is_file() and dest.stat().st_size >= minimum:
            saved.append(dest)
            continue
        if dest.is_file():
            dest.unlink()
        _download_file(url, dest, minimum, status)
        saved.append(dest)
    return saved[0], saved[1]


def _download_tokenizers(status) -> tuple[Path, Path]:
    for name in TOKEN_FILES:
        dest = TOKEN_ROOT / name
        if dest.is_file() and dest.stat().st_size > 0:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if status:
            status(f"Downloading {name}")
        request = urllib.request.Request(TOKEN_URL + name, headers={"User-Agent": "RedWright"})
        with urllib.request.urlopen(request, timeout=120) as response:
            dest.write_bytes(response.read())
    return TOKEN_ROOT / "tokenizer", TOKEN_ROOT / "t5_tokenizer"


def _block_count(state: dict) -> int:
    import re

    found = set()
    for key in state:
        match = re.search(r"(?:transformer_)?blocks\.(?:block)?(\d+)\.", key)
        if match:
            found.add(int(match.group(1)))
    return (max(found) + 1) if found else 28


def _looks_diffusers(state: dict) -> bool:
    for key in state:
        if "transformer_blocks." in key or ".attn1." in key or key.startswith("patch_embed."):
            return True
    return False


def _load_diffusers_transformer(state: dict, dtype):
    from accelerate import init_empty_weights
    from diffusers import CosmosTransformer3DModel

    sys.path.insert(0, str(TOOLS))
    from convert_cosmos_to_diffusers import TRANSFORMER_CONFIGS

    cleaned = {}
    for key, value in state.items():
        new = key[len("transformer.") :] if key.startswith("transformer.") else key
        cleaned[new] = value
    layers = _block_count(cleaned)
    config = dict(TRANSFORMER_CONFIGS["Cosmos-2.0-Diffusion-2B-Text2Image"])
    config["num_layers"] = layers
    query = cleaned.get("transformer_blocks.0.attn1.to_q.weight")
    norm = cleaned.get("transformer_blocks.0.attn1.norm_q.weight")
    if query is not None and norm is not None and int(norm.shape[0]) > 0:
        head_dim = int(norm.shape[0])
        config["attention_head_dim"] = head_dim
        config["num_attention_heads"] = max(1, int(query.shape[0]) // head_dim)
    cross = cleaned.get("transformer_blocks.0.attn2.to_k.weight")
    if cross is not None and cross.ndim == 2:
        config["text_embed_dim"] = int(cross.shape[1])
    with init_empty_weights():
        transformer = CosmosTransformer3DModel(**config)
    expected = set(transformer.state_dict().keys())
    missing = sorted(expected - set(cleaned))
    if len(missing) > 30:
        sample = ", ".join(missing[:6])
        raise RuntimeError(
            f"This file does not match an Anima transformer ({layers} blocks). "
            f"{len(missing)} weights are missing, including {sample}."
        )
    transformer.load_state_dict({key: value for key, value in cleaned.items() if key in expected}, strict=False, assign=True)
    return transformer.to(dtype=dtype)


def _normalize_anima_keys(state: dict) -> dict:
    """ComfyUI saves Anima as model.diffusion_model.*; the official file uses net.*."""
    prefixes = ("model.diffusion_model.", "diffusion_model.", "net.")
    normalized = {}
    for key, value in state.items():
        new = key
        for prefix in prefixes:
            if new.startswith(prefix):
                new = new[len(prefix) :]
                break
        if new.startswith("net."):
            new = new[len("net.") :]
        normalized[new] = value
    return normalized


def _split_checkpoint(state: dict) -> tuple[dict, dict, bool]:
    state = _normalize_anima_keys(state)
    transformer, conditioner = {}, {}
    for key, value in state.items():
        if key.startswith("text_conditioner."):
            conditioner[key[len("text_conditioner.") :]] = value
        elif key.startswith("llm_adapter."):
            conditioner[key[len("llm_adapter.") :]] = value
        elif key.startswith("transformer."):
            transformer[key[len("transformer.") :]] = value
        else:
            transformer[key] = value
    return transformer, conditioner, _looks_diffusers(transformer)


def _load_split(model: Path, text: Path, vae: Path, shift: float, dtype, write=None):
    import torch
    from safetensors.torch import load_file

    sys.path.insert(0, str(TOOLS))
    from convert_anima_to_diffusers import (  # noqa: WPS433
        convert_qwen_image_vae,
        convert_text_conditioner,
        convert_text_encoder,
    )
    from convert_cosmos_to_diffusers import TRANSFORMER_CONFIGS, convert_transformer
    from diffusers import AnimaAutoBlocks, FlowMatchEulerDiscreteScheduler
    from transformers import AutoTokenizer, T5TokenizerFast

    if write:
        write(f"Loading Anima model {model.name}")
    dit_state = load_file(str(model), device="cpu")
    transformer_state, conditioner_state, diffusers_file = _split_checkpoint(dit_state)
    layers = _block_count(transformer_state)
    if write:
        write(f"{layers}-block Anima transformer")
    sample_keys = ", ".join(list(transformer_state)[:6])
    try:
        if diffusers_file:
            transformer = _load_diffusers_transformer(transformer_state, dtype)
        else:
            TRANSFORMER_CONFIGS["Cosmos-2.0-Diffusion-2B-Text2Image"]["num_layers"] = layers
            transformer = convert_transformer(
                "Cosmos-2.0-Diffusion-2B-Text2Image", state_dict=transformer_state, weights_only=True
            )
    except RuntimeError as exc:
        raise RuntimeError(f"{exc} This file's weights look like: {sample_keys}") from exc
    if not conditioner_state:
        raise RuntimeError(
            "This Anima file has no LLM adapter. Use the original DiT file, not a converted transformer by itself."
        )
    if write:
        write(f"Loading Qwen3 text encoder {text.name}")
    text_encoder = convert_text_encoder(load_file(str(text), device="cpu"))
    if write:
        write(f"Loading Qwen-Image VAE {vae.name}")
    vae_model = convert_qwen_image_vae(load_file(str(vae), device="cpu"))
    if dtype == torch.float16:
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float32
    vae_dtype = torch.float32 if dtype == torch.float32 else torch.bfloat16
    conditioner = convert_text_conditioner(conditioner_state)
    if write:
        write("Loading tokenizers")
    qwen_dir, t5_dir = _download_tokenizers(write)
    if write:
        write("Building the Anima pipeline")
    pipe = AnimaAutoBlocks().init_pipeline()
    pipe.update_components(
        text_encoder=text_encoder.to(dtype=dtype),
        tokenizer=AutoTokenizer.from_pretrained(str(qwen_dir)),
        t5_tokenizer=T5TokenizerFast.from_pretrained(str(t5_dir)),
        text_conditioner=conditioner.to(dtype=dtype),
        transformer=transformer.to(dtype=dtype),
        vae=vae_model.to(dtype=vae_dtype),
        scheduler=FlowMatchEulerDiscreteScheduler(shift=shift),
    )
    return pipe


def _load_folder(folder: Path, shift: float, dtype):
    from diffusers import FlowMatchEulerDiscreteScheduler, ModularPipeline

    pipe = ModularPipeline.from_pretrained(str(folder))
    pipe.load_components(torch_dtype=dtype)
    pipe.scheduler = FlowMatchEulerDiscreteScheduler(shift=shift)
    return pipe


_BASE_TO_29 = (
    0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 16, 18, 19, 20, 22, 23, 25, 26, 28, 29, 31, 32, 34, 35, 37, 38, 39
)

_LORA_COMPOUNDS = (
    "adaln_modulation_self_attn",
    "adaln_modulation_cross_attn",
    "adaln_modulation_mlp",
    "self_attn",
    "cross_attn",
    "output_proj",
    "q_proj",
    "k_proj",
    "v_proj",
    "q_norm",
    "k_norm",
    "layer1",
    "layer2",
    "final_layer",
    "t_embedder",
    "t_embedding_norm",
    "x_embedder",
    "llm_adapter",
)

_LORA_RENAMES = (
    ("self_attn.", "attn1."),
    ("cross_attn.", "attn2."),
    ("q_proj", "to_q"),
    ("k_proj", "to_k"),
    ("v_proj", "to_v"),
    ("output_proj", "to_out.0"),
    ("q_norm", "norm_q"),
    ("k_norm", "norm_k"),
    ("mlp.layer1", "ff.net.0.proj"),
    ("mlp.layer2", "ff.net.2"),
    ("adaln_modulation_self_attn.1", "norm1.linear_1"),
    ("adaln_modulation_self_attn.2", "norm1.linear_2"),
    ("adaln_modulation_cross_attn.1", "norm2.linear_1"),
    ("adaln_modulation_cross_attn.2", "norm2.linear_2"),
    ("adaln_modulation_mlp.1", "norm3.linear_1"),
    ("adaln_modulation_mlp.2", "norm3.linear_2"),
)


def _kohya_body(body: str) -> str:
    protected = body
    tokens = {}
    for index, name in enumerate(_LORA_COMPOUNDS):
        token = f"#{index}#"
        if name in protected:
            protected = protected.replace(name, token)
            tokens[token] = name
    protected = protected.replace("_", ".")
    for token, name in tokens.items():
        protected = protected.replace(token, name)
    return protected


def _normalize_lora_module(key: str) -> str:
    if key.startswith("lora_unet_"):
        key = _kohya_body(key[len("lora_unet_") :])
    for prefix in ("base_model.model.", "diffusion_model.", "transformer.", "unet.", "net."):
        if key.startswith(prefix):
            key = key[len(prefix) :]
    if not key.startswith("transformer_blocks."):
        key = key.replace("blocks.", "transformer_blocks.")
    for source, dest in _LORA_RENAMES:
        key = key.replace(source, dest)
    return key


def _convert_lora_key(key: str) -> str:
    if key.endswith(".alpha"):
        module = _normalize_lora_module(key[: -len(".alpha")])
        return f"{module}.alpha" if module else ""
    suffix = ""
    for old, new in (
        (".lora_down.weight", ".lora_A.weight"),
        (".lora_up.weight", ".lora_B.weight"),
        (".lora_down.bias", ".lora_A.bias"),
        (".lora_up.bias", ".lora_B.bias"),
    ):
        if key.endswith(old):
            key = key[: -len(old)]
            suffix = new
            break
    else:
        for marker in (".lora_A.", ".lora_B."):
            if marker in key:
                suffix = key[key.index(marker) :].replace(".default.", ".")
                key = key[: key.index(marker)]
                break
        else:
            return ""
    return _normalize_lora_module(key) + suffix


def _lora_block_indexes(state: dict) -> set[int]:
    import re

    found = set()
    for key in state:
        match = re.search(r"transformer_blocks\.(\d+)\.", key)
        if match:
            found.add(int(match.group(1)))
    return found


def _remap_lora_blocks(state: dict, layers: int) -> dict:
    import re

    indexes = _lora_block_indexes(state)
    if not indexes or max(indexes) > 27 or layers != 40:
        return state
    remapped = {}
    for key, value in state.items():
        match = re.search(r"transformer_blocks\.(\d+)\.", key)
        if match:
            source = int(match.group(1))
            if source < len(_BASE_TO_29):
                key = key[: match.start(1)] + str(_BASE_TO_29[source]) + key[match.end(1) :]
        remapped[key] = value
    return remapped


def _convert_lora_state(path: Path, layers: int) -> dict:
    from safetensors.torch import load_file

    converted = {}
    for key, value in load_file(str(path)).items():
        new = _convert_lora_key(key)
        if new:
            converted[new] = value
    return _remap_lora_blocks(converted, layers)


def _fuse_lora(transformer, state: dict, strength: float, write=None) -> int:
    """Fold the LoRA into the weights. This model has no load_lora_weights, and a fused LoRA is also faster to sample."""
    import torch

    grouped: dict[str, dict] = {}
    for key, tensor in state.items():
        if key.endswith(".lora_A.weight"):
            grouped.setdefault(key[: -len(".lora_A.weight")], {})["A"] = tensor
        elif key.endswith(".lora_B.weight"):
            grouped.setdefault(key[: -len(".lora_B.weight")], {})["B"] = tensor
        elif key.endswith(".alpha"):
            grouped.setdefault(key[: -len(".alpha")], {})["alpha"] = tensor
    modules = dict(transformer.named_modules())
    fused = 0
    skipped = 0
    with torch.no_grad():
        for name, parts in grouped.items():
            first, second = parts.get("A"), parts.get("B")
            module = modules.get(name)
            if first is None or second is None or module is None or not hasattr(module, "weight"):
                skipped += 1
                continue
            weight = module.weight.data
            first = first.to(dtype=torch.float32)
            second = second.to(dtype=torch.float32)
            delta = second @ first
            if tuple(delta.shape) != tuple(weight.shape):
                skipped += 1
                continue
            rank = max(1, int(first.shape[0]))
            scale = float(strength)
            alpha = parts.get("alpha")
            if alpha is not None:
                scale *= float(alpha.detach().float().reshape(-1)[0].item()) / rank
            weight.add_(delta.to(dtype=weight.dtype) * scale)
            fused += 1
    if fused == 0:
        raise RuntimeError(
            "The LoRA did not match this Anima model, so it was not applied. Use an Anima LoRA, not a Stable Diffusion one."
        )
    if write:
        note = f"Merged {fused} LoRA layers into the model"
        if skipped:
            note += f" ({skipped} did not match)"
        write(note)
    return fused


def _inference_dtype(device: str):
    import torch

    if device != "cuda":
        return torch.float32
    # fp16 overflows this DiT and the Qwen-Image VAE, so the picture comes out black.
    # bf16 is the precision the Anima weights were saved in.
    if torch.cuda.is_bf16_supported():
        return torch.bfloat16
    return torch.float32


def _prefer_fast_attention() -> None:
    import torch

    if not torch.cuda.is_available():
        return
    name = ""
    try:
        name = torch.cuda.get_device_name(0).lower()
    except Exception:
        name = ""
    amd = bool(getattr(torch.version, "hip", None)) or "amd" in name or "radeon" in name
    try:
        # ROCm's flash kernel returns empty latents on these cards. Memory-efficient attention is the fast safe path.
        torch.backends.cuda.enable_flash_sdp(not amd)
        torch.backends.cuda.enable_mem_efficient_sdp(True)
        torch.backends.cuda.enable_math_sdp(True)
    except Exception:
        pass
    try:
        torch.backends.cudnn.benchmark = True
    except Exception:
        pass


def _gpu_note() -> str:
    import torch

    if not torch.cuda.is_available():
        return "GPU memory is not available"
    try:
        free, total = torch.cuda.mem_get_info()
    except Exception:
        free, total = 0, 0
    held = torch.cuda.memory_allocated()
    return (
        f"GPU free {free / (1024**3):.1f} GB of {total / (1024**3):.1f}, "
        f"this model holds {held / (1024**3):.1f} GB"
    )


def _strip_offload(pipe) -> None:
    try:
        from accelerate.hooks import remove_hook_from_module
    except Exception:
        remove_hook_from_module = None
    for name in ("transformer", "text_encoder", "text_conditioner", "vae"):
        module = getattr(pipe, name, None)
        if module is None or remove_hook_from_module is None:
            continue
        try:
            remove_hook_from_module(module, recurse=True)
        except Exception:
            pass
    for attr in ("_all_hooks",):
        if hasattr(pipe, attr):
            try:
                setattr(pipe, attr, [])
            except Exception:
                pass


def _pin_on_gpu(pipe, device: str) -> str:
    _strip_offload(pipe)
    for name in ("transformer", "text_encoder", "text_conditioner", "vae"):
        module = getattr(pipe, name, None)
        if module is not None and hasattr(module, "to"):
            module.to(device)
    try:
        param = next(pipe.transformer.parameters())
        return str(param.device)
    except Exception:
        return device


def _drop_session(session: dict) -> None:
    import gc

    pipe = session.pop("pipe", None)
    session.pop("key", None)
    session.pop("model_path", None)
    if pipe is None:
        gc.collect()
        return
    _strip_offload(pipe)
    for name in ("transformer", "text_encoder", "text_conditioner", "vae"):
        module = getattr(pipe, name, None)
        if module is None:
            continue
        try:
            module.to("cpu")
        except Exception:
            pass
        try:
            setattr(pipe, name, None)
        except Exception:
            pass
    del pipe
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass


def _release_run() -> None:
    import gc

    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _place_pipe(pipe, device: str, write) -> None:
    import torch

    def move_pieces() -> None:
        for name in ("transformer", "text_encoder", "text_conditioner", "vae"):
            module = getattr(pipe, name, None)
            if module is not None and hasattr(module, "to"):
                module.to(device)

    if device != "cuda":
        try:
            pipe.to(device)
        except Exception:
            move_pieces()
        return
    try:
        free, total = torch.cuda.mem_get_info()
    except Exception:
        free, total = 0, 0
    free_gb = free / (1024**3)
    total_gb = total / (1024**3)
    if total_gb >= 12 and free_gb >= 8:
        write(f"Keeping the whole model on the GPU ({free_gb:.1f} GB free of {total_gb:.1f})")
        _pin_on_gpu(pipe, device)
        return
    write(f"Only {free_gb:.1f} GB free. Moving pieces on and off the GPU, which is slower.")
    pipe.enable_model_cpu_offload()


def _job_key(job: dict, dtype) -> tuple:
    loras = tuple(
        (str(Path(path).resolve()), round(float(weight), 4))
        for path, weight in (job.get("loras") or [])
        if path
    )
    text = str(job.get("text") or "")
    vae = str(job.get("vae") or "")
    return (
        str(Path(job["model"]).resolve()),
        str(Path(text).resolve()) if text else "",
        str(Path(vae).resolve()) if vae else "",
        round(float(job.get("shift") or 3), 4),
        str(dtype),
        loras,
    )


def _load_pipe(job: dict, dtype, write):
    model = Path(job["model"])
    shift = float(job.get("shift") or 3)
    if model.is_dir():
        write(f"Loading diffusers folder {model.name}")
        pipe = _load_folder(model, shift, dtype)
    else:
        text = Path(job.get("text") or "")
        vae = Path(job.get("vae") or "")
        if not text.is_file() or not vae.is_file():
            raise RuntimeError("Anima needs the Qwen3 0.6B text encoder and the Qwen-Image VAE, or a diffusers folder.")
        pipe = _load_split(model, text, vae, shift, dtype, write)
    for path, weight in job.get("loras") or []:
        if not path or not Path(path).is_file():
            continue
        layers = int(getattr(getattr(pipe.transformer, "config", None), "num_layers", 0) or 0)
        state = _convert_lora_state(Path(path), layers)
        if not state:
            raise RuntimeError(f"{Path(path).name} has no Anima LoRA weights.")
        write(f"Loading LoRA {Path(path).name}")
        _fuse_lora(pipe.transformer, state, float(weight), write)
    return pipe


def draw(job: dict, write, on_preview=None, session: dict | None = None) -> None:
    import torch
    from PIL import Image

    _prefer_fast_attention()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = _inference_dtype(device)
    kind = "fp16" if dtype == torch.float16 else "bf16" if dtype == torch.bfloat16 else "fp32"
    write(f"Device {device}, precision {kind}")
    if dtype != torch.float16:
        write("Anima stays in this precision. fp16 makes a black picture.")
    key = _job_key(job, dtype)
    requested = str(Path(job["model"]).resolve())
    requested_name = Path(requested).name
    pipe = None if session is None else session.get("pipe")
    loaded = None if session is None else session.get("model_path")
    same = session is not None and session.get("key") == key and loaded == requested and pipe is not None
    if same:
        where = _pin_on_gpu(pipe, device)
        write(f"Using {requested_name} already on the GPU ({where})")
        write(_gpu_note())
    else:
        if pipe is not None:
            old_name = Path(loaded).name if loaded else "the previous model"
            write(f"Unloading {old_name} before loading {requested_name}")
            _drop_session(session)
            write(_gpu_note())
        write(f"Loading {requested_name}")
        pipe = _load_pipe(job, dtype, write)
        write("Moving the model onto the GPU")
        _place_pipe(pipe, device, write)
        if session is not None:
            session["key"] = key
            session["pipe"] = pipe
            session["model_path"] = requested
            write(f"{requested_name} stays loaded for the next picture. Use Unload to free the card.")
        write(_gpu_note())
    steps = int(job["steps"])
    model_name = Path(job["model"]).name.lower()
    if "turbo" in model_name and steps > 12:
        write(f"Turbo is usually about 8 to 10 steps. This run is {steps}.")
    seed = job.get("seed")
    generator = None
    if seed is not None:
        generator = torch.Generator(device=device).manual_seed(int(seed))
    width = int(job["width"])
    height = int(job["height"])
    write(f"Encoding the prompt, {width}x{height}, {steps} steps")
    cfg = float(job.get("cfg") or 4)
    transformer = pipe.transformer
    original_forward = transformer.forward
    seen = {"n": 0}

    def counting_forward(*args, **kwargs):
        result = original_forward(*args, **kwargs)
        seen["n"] += 1
        step = seen["n"] if cfg <= 1 else (seen["n"] + 1) // 2
        if 1 <= step <= steps and (cfg <= 1 or seen["n"] % 2 == 0):
            write(f"Step {step} / {steps}")
        return result

    transformer.forward = counting_forward

    kwargs = {
        "prompt": job.get("prompt") or "",
        "negative_prompt": job.get("negative") or "",
        "num_inference_steps": steps,
        "guidance_scale": float(job.get("cfg") or 4),
        "height": height,
        "width": width,
        "max_sequence_length": int(job.get("max_length") or 512),
        "generator": generator,
    }
    source = str(job.get("init_image") or "")
    if source and Path(source).is_file():
        write(f"Reading the source picture at denoise {float(job.get('init_denoise') or 0.6):.2f}")
        kwargs["image"] = Image.open(source).convert("RGB")
        kwargs["strength"] = float(job.get("init_denoise") or 0.6)
    write(f"Step 0 / {steps}")
    try:
        with torch.inference_mode():
            result = pipe(**{item: value for item, value in kwargs.items() if value is not None})
    finally:
        transformer.forward = original_forward
    images = getattr(result, "images", None)
    if images is None and isinstance(result, dict):
        images = result.get("images")
    if not images:
        raise RuntimeError("Anima did not return a picture.")
    write("Decoding and saving the picture")
    image = images[0]
    if not isinstance(image, Image.Image):
        import numpy as np

        array = image.detach().float().cpu().numpy() if hasattr(image, "detach") else np.asarray(image)
        if array.ndim == 4:
            array = array[0]
        if array.ndim == 3 and array.shape[0] in (1, 3):
            array = array.transpose(1, 2, 0)
        if array.max() <= 1:
            array = array * 255
        image = Image.fromarray(array.clip(0, 255).astype("uint8"))
    image = image.copy()
    del images, result
    _release_run()
    Path(job["out"]).parent.mkdir(parents=True, exist_ok=True)
    image.save(job["out"])
    bands = image.getextrema()
    if isinstance(bands, tuple) and bands and all(isinstance(item, tuple) and item[1] == 0 for item in bands):
        write("The picture is black. Close RedWright so the old fp16 model unloads, then generate again.")
    if on_preview is not None:
        on_preview(image, "Final")
    if session is not None and session.get("pipe") is pipe and device == "cuda":
        try:
            where = _pin_on_gpu(pipe, device)
            write(f"Ready for the next picture on {where}. {_gpu_note()}")
        except Exception:
            pass
    write("done")


def serve() -> int:
    import json
    import traceback

    session: dict = {}
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
            print(f"error\nCould not read the Anima job. {exc}", flush=True)
            continue
        status = Path(job["status"])

        def write(message: str, status=status) -> None:
            status.write_text(message, encoding="utf-8")
            print(message, flush=True)

        try:
            draw(job, write, session=session)
        except Exception as exc:
            _drop_session(session)
            write(f"error\n{exc}")
            traceback.print_exc()


def _buckets(base: int) -> list[tuple[int, int]]:
    step = 16
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


def _fit_bucket(image, buckets: list[tuple[int, int]]):
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


def _caption(subject: str, trigger: str, caption: str, stem: str) -> str:
    trigger = trigger.strip()
    caption = caption.strip()
    if subject == "style":
        if trigger and trigger.lower() not in caption.lower():
            caption = f"{caption}, {trigger}".strip(", ") if caption else trigger
        return caption or stem
    if trigger and trigger.lower() not in caption.lower():
        caption = f"{trigger}, {caption}".strip(", ") if caption else trigger
    return caption or trigger or stem


def _encode_text(pipe, caption: str, device, dtype):
    import torch

    tokens = pipe.tokenizer(caption, padding="longest", max_length=512, truncation=True, return_tensors="pt")
    ids = tokens.input_ids.to(device)
    mask = tokens.attention_mask.to(device)
    hidden = pipe.text_encoder(input_ids=ids, attention_mask=mask).last_hidden_state
    hidden = hidden.to(dtype=dtype) * mask.to(dtype=hidden.dtype).unsqueeze(-1)
    t5 = pipe.t5_tokenizer(caption, padding="longest", max_length=512, truncation=True, return_tensors="pt")
    embeds = pipe.text_conditioner(
        source_hidden_states=hidden.to(dtype=pipe.text_conditioner.dtype),
        target_input_ids=t5.input_ids.to(device),
        target_attention_mask=t5.attention_mask.to(device),
        source_attention_mask=mask,
    )
    if isinstance(embeds, tuple):
        embeds = embeds[0]
    if not torch.is_tensor(embeds):
        embeds = getattr(embeds, "last_hidden_state", None) or embeds[0]
    return embeds.detach().to(dtype=dtype).cpu()


def _encode_pixels(vae, pixel, device, fp32: bool):
    import torch

    dtype = torch.float32 if fp32 else next(vae.parameters()).dtype
    image = pixel.to(device=device, dtype=dtype).unsqueeze(2)
    encoded = vae.encode(image)
    latents = encoded.latent_dist.mode() if hasattr(encoded, "latent_dist") else encoded.latents
    if latents.dim() == 4:
        latents = latents.unsqueeze(2)
    channels = latents.shape[1]
    mean = torch.tensor(vae.config.latents_mean, device=latents.device, dtype=latents.dtype).view(1, channels, 1, 1, 1)
    std = torch.tensor(vae.config.latents_std, device=latents.device, dtype=latents.dtype).view(1, channels, 1, 1, 1)
    return ((latents - mean) / std).detach().cpu()


def _save_anima_lora(path: Path, transformer, rank: int, alpha: int, trigger: str) -> None:
    import torch
    from peft.utils import get_peft_model_state_dict
    from safetensors.torch import save_file

    state = get_peft_model_state_dict(transformer)
    tensors = {}
    for key, value in state.items():
        if not torch.isfinite(value).all():
            raise RuntimeError("Training produced invalid LoRA weights. Lower the learning rate and train again.")
        name = key.replace("base_model.model.", "").replace(".default.", ".")
        tensors["transformer." + name] = value.detach().float().cpu().contiguous()
    if not any(key.endswith("lora_B.weight") or key.endswith("lora_B.default.weight") for key in tensors):
        raise RuntimeError("Nothing was trained.")
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file(
        tensors,
        str(path),
        metadata={
            "format": "pt",
            "modelspec.architecture": "Anima LoRA",
            "modelspec.trigger_phrase": trigger.strip(),
            "ss_network_dim": str(rank),
            "ss_network_alpha": str(alpha),
        },
    )


def train(job: dict, write) -> None:
    import gc
    import random

    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image
    from peft import LoraConfig

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
    size = max(256, int(job["resolution"]) - int(job["resolution"]) % 16)
    trigger = (job.get("trigger") or "").strip()
    subject = job.get("subject") if job.get("subject") in {"character", "style", "concept"} else "character"
    use_buckets = bool(job.get("buckets", True))
    checkpoint = bool(job.get("checkpoint", True))
    cache_latents = bool(job.get("cache_latents", True))
    fp32_vae = bool(job.get("fp32_vae", True))
    shift = float(job.get("shift") or 3)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float16
    model = Path(job["model"])
    write(f"Loading {model.name}")
    if model.is_dir():
        pipe = _load_folder(model, shift, dtype)
    else:
        text = Path(job.get("text") or "")
        vae = Path(job.get("vae") or "")
        if not text.is_file() or not vae.is_file():
            raise RuntimeError("Anima training needs the Qwen3 text encoder and the Qwen-Image VAE.")
        pipe = _load_split(model, text, vae, shift, dtype, write)
    pipe.vae.to(device=device, dtype=torch.float32 if fp32_vae else dtype)
    pipe.text_encoder.to(device)
    pipe.text_conditioner.to(device)
    buckets = _buckets(size) if use_buckets else [(size, size)]
    write(
        f"{subject} · rank {rank} · alpha {alpha} · shift {shift:g} · "
        + ("aspect buckets" if use_buckets else "square crop")
        + (" · float32 VAE" if fp32_vae else "")
    )
    pairs = []
    used = set()
    for path in images:
        caption_file = path.with_suffix(".txt")
        caption = caption_file.read_text(encoding="utf-8").strip() if caption_file.is_file() else ""
        caption = _caption(subject, trigger, caption, path.stem)
        image = Image.open(path).convert("RGB")
        if use_buckets:
            image, bucket_w, bucket_h = _fit_bucket(image, buckets)
        else:
            width, height = image.size
            side = min(width, height)
            left = (width - side) // 2
            top = (height - side) // 2
            image = image.crop((left, top, left + side, top + side)).resize((size, size), Image.Resampling.LANCZOS)
            bucket_w, bucket_h = size, size
        used.add((bucket_w, bucket_h))
        pixel = torch.from_numpy(np.asarray(image, dtype="float32")).permute(2, 0, 1).unsqueeze(0) / 127.5 - 1
        embeds = _encode_text(pipe, caption, device, dtype)
        if cache_latents:
            with torch.no_grad():
                latent = _encode_pixels(pipe.vae, pixel, device, fp32_vae)
            stored = latent
        else:
            stored = pixel.cpu()
        pairs.append((stored, embeds, bucket_w, bucket_h, cache_latents))
        write(f"Prepared {path.name} at {bucket_w}×{bucket_h}")
    pipe.text_encoder.to("cpu")
    pipe.text_conditioner.to("cpu")
    if cache_latents:
        pipe.vae.to("cpu")
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    transformer = pipe.transformer
    transformer.to(device)
    if checkpoint and hasattr(transformer, "enable_gradient_checkpointing"):
        transformer.enable_gradient_checkpointing()
    transformer.add_adapter(LoraConfig(r=rank, lora_alpha=alpha, target_modules=["to_q", "to_k", "to_v", "to_out.0"]))
    transformer.train()
    trainable = [param for param in transformer.parameters() if param.requires_grad]
    if not trainable:
        raise RuntimeError("No Anima attention layers were found to train.")
    masters = [param.detach().float().clone().requires_grad_(True) for param in trainable]
    opt = torch.optim.AdamW(masters, lr=float(job["lr"]), foreach=False)
    weight_dtype = next(param.dtype for param in transformer.parameters() if not param.requires_grad)
    write(f"Training {len(pairs)} pictures in {len(used)} bucket sizes")
    skipped = 0
    for step in range(steps):
        stored, embeds, bucket_w, bucket_h, cached = random.choice(pairs)
        embeds = embeds.to(device=device, dtype=weight_dtype)
        if cached:
            latent = stored.to(device=device, dtype=torch.float32)
        else:
            with torch.no_grad():
                latent = _encode_pixels(pipe.vae, stored, device, fp32_vae).to(device=device, dtype=torch.float32)
        noise = torch.randn_like(latent)
        draw_u = torch.rand((), device=device)
        sigma = (draw_u * shift) / (1 + (shift - 1) * draw_u)
        sigma = sigma.clamp(1e-4, 1 - 1e-4)
        noisy = ((1 - sigma) * latent + sigma * noise).to(dtype=weight_dtype)
        target = noise - latent
        pad = noisy.new_zeros(1, 1, bucket_h, bucket_w)
        pred = transformer(
            hidden_states=noisy,
            timestep=sigma.expand(noisy.shape[0]).to(dtype=weight_dtype),
            encoder_hidden_states=embeds,
            padding_mask=pad,
            return_dict=False,
        )[0]
        if not torch.isfinite(pred).all():
            opt.zero_grad(set_to_none=True)
            skipped += 1
            write(f"Step {step + 1} skipped because the picture became invalid")
            continue
        loss = F.mse_loss(pred.float(), target)
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
    _save_anima_lora(Path(job["out"]), transformer, rank, alpha, trigger)
    transformer.to("cpu")
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    write(f"Saved {job['out']}")
