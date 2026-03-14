#!/usr/bin/env python3
"""
LLM internal-state visualization backend.

Serves a WebGL frontend and a WebSocket that streams reduced hidden states
(and optional attention) as the model processes a prompt or generates tokens.
Runs with a real small LLM when transformers/torch are available, otherwise
streams mock data so the frontend can be developed without a model.

Run: uvicorn viz_server:app --reload --host 0.0.0.0
Then open http://localhost:8000
"""

import asyncio
import json
import logging
import os
import threading
from queue import Empty, Queue
from typing import Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import numpy as np

# Optional: real LLM for hidden states
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Dimensionality reduction for high-dim hidden states -> 3D
def reduce_to_3d(vectors: "np.ndarray", method: str = "pca") -> "np.ndarray":
    """Reduce [n, dim] to [n, 3]. Uses PCA or random projection if no sklearn."""
    n, dim = vectors.shape
    if dim <= 3:
        pad = np.zeros((n, 3 - dim))
        return np.hstack([vectors, pad]) if pad.size else vectors
    try:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=3)
        return pca.fit_transform(vectors)
    except ImportError:
        # Random projection
        rng = np.random.default_rng(42)
        proj = rng.standard_normal((dim, 3))
        return (vectors @ proj) / np.sqrt(dim)


def _mock_hidden_states(prompt: str, num_tokens: int = 32, dim: int = 128) -> List[List[float]]:
    """Generate deterministic mock hidden states for development (already 3D)."""
    import hashlib
    h = hashlib.sha256(prompt.encode()).hexdigest()
    seed = int(h[:8], 16) % (2**31)
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal((num_tokens, min(dim, 3)))
    if raw.shape[1] < 3:
        raw = np.hstack([raw, np.zeros((num_tokens, 3 - raw.shape[1]))])
    for i in range(num_tokens):
        raw[i] = raw[i] / (np.linalg.norm(raw[i]) + 1e-8)
    return raw.tolist()


_model_cache: dict = {}  # lazy-loaded model and tokenizer
# Optional: PCA fit on first forward for consistent 3D across streamed tokens
_pca_cache: dict = {}

def _real_hidden_states(
    prompt: str,
    model_name: str = "tinyllama/TinyLlama-1.1B-Chat-v1.0",
    max_new_tokens: int = 24,
    device: str = "cpu",
) -> tuple[List[List[List[float]]], List[str], Optional[Any]]:
    """
    Run model on prompt, return per-layer hidden states for each token (after reduction),
    token strings, and token_ids for optional attention.
    Returns (layer_token_3d_list, token_strs, token_ids).
    """
    if model_name not in _model_cache:
        logger.info("Loading model %s (once)...", model_name)
        _model_cache[model_name] = {
            "tokenizer": AutoTokenizer.from_pretrained(model_name),
            "model": AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float32,
                device_map=device,
            ),
        }
        _model_cache[model_name]["model"].eval()
    tokenizer = _model_cache[model_name]["tokenizer"]
    model = _model_cache[model_name]["model"]

    inputs = tokenizer(prompt, return_tensors="pt").to(next(model.parameters()).device)
    input_ids = inputs["input_ids"]
    token_strs = tokenizer.convert_ids_to_tokens(input_ids[0], skip_special_tokens=True)

    with torch.no_grad():
        out = model(
            input_ids,
            output_hidden_states=True,
            output_attentions=False,
        )

    # out.hidden_states: tuple of (batch, seq, hidden_size) per layer
    # We reduce each layer's sequence to 3D and send one point per (layer, token)
    all_layers_3d = []
    for layer_idx, h in enumerate(out.hidden_states):
        # h: (1, seq, hidden_size)
        arr = h[0].cpu().float().numpy()
        reduced = reduce_to_3d(arr)
        all_layers_3d.append(reduced.tolist())

    # Optionally generate more tokens and extend trajectory
    if max_new_tokens > 0:
        gen = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
        new_ids = gen[0, input_ids.shape[1]:]
        new_tokens = tokenizer.convert_ids_to_tokens(new_ids, skip_special_tokens=True)
        token_strs.extend(new_tokens)
        # Re-run with full sequence to get hidden states for generated part
        with torch.no_grad():
            out2 = model(gen.unsqueeze(0), output_hidden_states=True)
        for layer_idx, h in enumerate(out2.hidden_states):
            arr = h[0].cpu().float().numpy()
            reduced = reduce_to_3d(arr)
            all_layers_3d[layer_idx] = reduced.tolist()

    return all_layers_3d, token_strs, None


def _stream_real_hidden_states(
    queue: "Queue",
    prompt: str,
    max_new_tokens: int,
    model_name: str = "tinyllama/TinyLlama-1.1B-Chat-v1.0",
    device: str = "cpu",
) -> None:
    """Run in a thread: generate token-by-token, push stream_start/stream_token/stream_end to queue."""
    try:
        if model_name not in _model_cache:
            logger.info("Loading model %s (once)...", model_name)
            _model_cache[model_name] = {
                "tokenizer": AutoTokenizer.from_pretrained(model_name),
                "model": AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float32,
                    device_map=device,
                ),
            }
            _model_cache[model_name]["model"].eval()
        tokenizer = _model_cache[model_name]["tokenizer"]
        model = _model_cache[model_name]["model"]
        dev = next(model.parameters()).device
    except Exception as e:
        queue.put({"cmd": "error", "message": str(e)})
        queue.put(None)
        return

    try:
        inputs = tokenizer(prompt, return_tensors="pt").to(dev)
        input_ids = inputs["input_ids"]
        prompt_len = input_ids.shape[1]
        prompt_tokens = tokenizer.convert_ids_to_tokens(input_ids[0], skip_special_tokens=True)

        with torch.no_grad():
            out = model(input_ids, output_hidden_states=True)
        # Use last layer only for a single trajectory
        h = out.hidden_states[-1][0].cpu().float().numpy()  # (seq, hidden_size)
        pca = _pca_cache.get(model_name)
        if pca is None:
            try:
                from sklearn.decomposition import PCA
                pca = PCA(n_components=3)
                pca.fit(h)
                _pca_cache[model_name] = pca
            except ImportError:
                rng = np.random.default_rng(42)
                proj = rng.standard_normal((h.shape[1], 3))
                class RP:
                    def transform(self, x): return (x @ proj) / np.sqrt(x.shape[1])
                pca = RP()
                _pca_cache[model_name] = pca
        traj_3d = pca.transform(h)  # (seq, 3)

        queue.put({"cmd": "stream_start", "mode": "real"})
        for i in range(len(traj_3d)):
            queue.put({
                "cmd": "stream_token",
                "point": traj_3d[i].tolist(),
                "token": prompt_tokens[i] if i < len(prompt_tokens) else "",
                "index": i,
            })

        gen_ids = input_ids.clone()
        for step in range(max_new_tokens):
            with torch.no_grad():
                out = model(gen_ids, output_hidden_states=True)
            last_h = out.hidden_states[-1][0, -1].cpu().float().numpy().reshape(1, -1)
            point_3d = pca.transform(last_h)[0].tolist()
            next_token_id = model.generate(
                gen_ids,
                max_new_tokens=1,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )[0, -1].item()
            token_str = tokenizer.convert_ids_to_tokens([next_token_id], skip_special_tokens=True)[0]
            queue.put({
                "cmd": "stream_token",
                "point": point_3d,
                "token": token_str,
                "index": prompt_len + step,
            })
            gen_ids = torch.cat([
                gen_ids,
                torch.tensor([[next_token_id]], device=gen_ids.device, dtype=gen_ids.dtype),
            ], dim=1)
            if next_token_id == tokenizer.eos_token_id:
                break

        queue.put({"cmd": "stream_end", "mode": "real"})
    except Exception as e:
        logger.exception("Stream generation failed")
        queue.put({"cmd": "error", "message": str(e)})
    finally:
        queue.put(None)


def _stream_mock_hidden_states(queue: "Queue", prompt: str, num_tokens: int = 48) -> None:
    """Run in a thread: emit mock trajectory points one-by-one for streaming UX."""
    import hashlib
    h = hashlib.sha256(prompt.encode()).hexdigest()
    seed = int(h[:8], 16) % (2**31)
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal((num_tokens, 3))
    for i in range(num_tokens):
        raw[i] = raw[i] / (np.linalg.norm(raw[i]) + 1e-8)
    points = raw.tolist()
    queue.put({"cmd": "stream_start", "mode": "mock"})
    for i, p in enumerate(points):
        queue.put({
            "cmd": "stream_token",
            "point": p,
            "token": f"t{i}",
            "index": i,
        })
    queue.put({"cmd": "stream_end", "mode": "mock"})
    queue.put(None)


# --- FastAPI app ---
STATIC_DIR = os.path.join(os.path.dirname(__file__), "viz_static")
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(title="LLM State Viz", description="Stream LLM internal state to WebGL viewer")


@app.get("/")
async def index():
    path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(path):
        return FileResponse(path, media_type="text/html")
    return HTMLResponse("<p>LLM State Viz. Put index.html in viz_static/.</p>")


@app.get("/viz.js")
async def viz_js():
    path = os.path.join(STATIC_DIR, "viz.js")
    if os.path.isfile(path):
        return FileResponse(path, media_type="application/javascript")
    return HTMLResponse("// viz.js not found", status_code=404)


@app.websocket("/ws")
async def websocket_viz(ws: WebSocket):
    await ws.accept()
    use_mock = not HAS_TORCH
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            cmd = msg.get("cmd")
            if cmd == "ping":
                await ws.send_json({"cmd": "pong"})
                continue
            if cmd != "prompt":
                await ws.send_json({"error": "unknown cmd"})
                continue

            prompt = msg.get("prompt", "Hello, world.")
            max_tokens = int(msg.get("max_tokens", 48))
            stream = msg.get("stream", True)
            force_mock = msg.get("stream_mock", False)

            await ws.send_json({"cmd": "status", "status": "computing"})

            if stream:
                # Token-by-token: run stream worker in thread, send each message as it arrives
                q = Queue()
                use_stream_real = HAS_TORCH and not force_mock
                worker = threading.Thread(
                    target=_stream_real_hidden_states if use_stream_real else _stream_mock_hidden_states,
                    args=(q, prompt, max_tokens),
                )
                worker.start()
                loop = asyncio.get_event_loop()
                while True:
                    next_msg = await loop.run_in_executor(None, lambda: q.get())
                    if next_msg is None:
                        break
                    if next_msg.get("cmd") == "error":
                        await ws.send_json(next_msg)
                        continue
                    await ws.send_json(next_msg)
                worker.join(timeout=1.0)
                continue

            # Non-streaming (batch) path
            if use_mock or force_mock:
                states_3d = _mock_hidden_states(prompt, num_tokens=max_tokens)
                payload = {
                    "cmd": "states",
                    "layers": [states_3d],
                    "tokens": [f"t{i}" for i in range(len(states_3d))],
                    "mode": "mock",
                }
            else:
                try:
                    layers_3d, token_strs, _ = _real_hidden_states(
                        prompt, max_new_tokens=max(0, max_tokens - 32)
                    )
                    payload = {
                        "cmd": "states",
                        "layers": layers_3d,
                        "tokens": token_strs,
                        "mode": "real",
                    }
                except Exception as e:
                    logger.exception("Real model run failed, falling back to mock")
                    states_3d = _mock_hidden_states(prompt, num_tokens=max_tokens)
                    payload = {
                        "cmd": "states",
                        "layers": [states_3d],
                        "tokens": [f"t{i}" for i in range(len(states_3d))],
                        "mode": "mock",
                        "error": str(e),
                    }
            await ws.send_json(payload)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await ws.send_json({"cmd": "error", "message": str(e)})
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
