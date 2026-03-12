"""
linguistic_topographer.py
─────────────────────────
Rehabilitated entry point for petals-2-metal.

Original intent: explore the topology of linguistic space — treat a language
model's hidden states as points in a high-dimensional manifold and watch how
language *moves* through it as text is generated.

Architecture:
  VectorSpaceExplorer  — tracks token-by-token trajectories, computes fractal
                         dimension of the path, exposes resonant probes
  Storyteller          — extracts thematic/emotional metadata from activations
  FlockGenerator       — runs multiple generation paths as a boid murmuration
  OSCEmitter           — pipes live metrics to Max/MSP (optional)
  SwarmVignettes       — Pyglet visual layer (launch separately or embedded)

No Petals / distributed infrastructure required. Works with any local
HuggingFace model; defaults to gpt2 for zero-download demo runs.

Usage:
    python linguistic_topographer.py --model gpt2 --prompt "The nature of light"
    python linguistic_topographer.py --model gpt2 --flock --osc
"""

import argparse
import asyncio
import logging
import sys
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from vector_space_explorer import VectorSpaceExplorer
from storyteller import Storyteller
from pattern_manager import PatternManager

logger = logging.getLogger(__name__)


# ─── Model loading ────────────────────────────────────────────────────────────

def load_model(model_name: str, device: str):
    """Load a local HuggingFace model and tokenizer."""
    logger.info("Loading model: %s on %s", model_name, device)
    dtype = torch.float16 if device == "cuda" else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=dtype,
        output_hidden_states=True,
    ).to(device)
    model.eval()
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer


# ─── Single trajectory run ────────────────────────────────────────────────────

async def run_single(
    model,
    tokenizer,
    prompt: str,
    max_new_tokens: int,
    device: str,
    osc_emitter=None,
):
    """Generate text, track the trajectory through embedding space, narrate it."""
    pattern_manager = PatternManager(model=model, pattern_depth=3, base_seed=42)
    explorer = VectorSpaceExplorer(model=model, tokenizer=tokenizer, device=device)
    storyteller = Storyteller(pattern_manager=pattern_manager)

    print(f"\n{'─'*60}")
    print(f"Prompt: {prompt!r}")
    print(f"{'─'*60}")

    trajectory = await explorer.trace_generation(
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        on_token=lambda step, token, state, metrics: _on_token(
            step, token, state, metrics, osc_emitter
        ),
    )

    # Weave narrative threads from trajectory waypoints
    for i, (token, hidden_state, _) in enumerate(trajectory.waypoints):
        pattern = hidden_state.squeeze(0)  # [seq, hidden]
        storyteller.add_thread(
            pattern=pattern,
            mandala=f"mode_{i % 5}",
            concretion=token,
            context={"step": i, "token": token},
        )

    # Generate and print narrative
    narrative = storyteller.generate_narrative(max_threads=6)
    print("\n── Narrative ────────────────────────────────────────────")
    print(narrative["narrative"])

    # Print trajectory metrics
    stats = explorer.trajectory_stats(trajectory)
    print("\n── Trajectory Metrics ───────────────────────────────────")
    for k, v in stats.items():
        print(f"  {k:<28} {v:.4f}" if isinstance(v, float) else f"  {k:<28} {v}")

    print(f"{'─'*60}\n")
    return trajectory, narrative


def _on_token(step, token, hidden_state, metrics, osc_emitter):
    """Called for each generated token."""
    frac_dim = metrics.get("fractal_dim", 0.0)
    valence = metrics.get("valence", 0.0)
    speed = metrics.get("speed", 0.0)

    print(
        f"  [{step:3d}] {token!r:<20} "
        f"fd={frac_dim:.3f}  val={valence:+.3f}  Δ={speed:.4f}",
        flush=True,
    )

    if osc_emitter:
        osc_emitter.send_token_metrics(step=step, token=token, **metrics)


# ─── Flock mode ───────────────────────────────────────────────────────────────

async def run_flock(
    model,
    tokenizer,
    prompts: list[str],
    max_new_tokens: int,
    device: str,
    osc_emitter=None,
):
    """Run multiple generation paths as a murmuration."""
    from flock_generator import FlockGenerator, FlockConfig

    # FlockGenerator expects multiple model names; wrap ours in a single-model flock
    config = FlockConfig(
        num_models=min(len(prompts), 4),
        max_length=max_new_tokens + 32,
        flock_cohesion=0.4,
        flock_separation=0.3,
        flock_alignment=0.5,
    )

    # For local mode, use the same model name for all flock slots
    model_name = model.config._name_or_path if hasattr(model.config, "_name_or_path") else "gpt2"
    model_names = [model_name] * config.num_models

    print(f"\n── Flock mode: {len(prompts)} paths, {config.num_models} models ──")

    def flock_callback(iteration, texts, tensors):
        print(f"\n  Flock iteration {iteration}:")
        for i, text in enumerate(texts):
            preview = text[:60].replace("\n", " ")
            print(f"    [{i}] {preview!r}")
        if osc_emitter:
            osc_emitter.send_flock_state(iteration=iteration, num_paths=len(texts))

    generator = FlockGenerator(model_names=model_names, config=config)
    results = await generator.generate_batch(
        prompts=prompts,
        num_iterations=3,
        iteration_callback=flock_callback,
    )

    print("\n── Flock Final Outputs ──────────────────────────────────")
    for prompt, (text, _tensor) in zip(prompts, results):
        print(f"\n  Prompt: {prompt!r}")
        print(f"  Output: {text[:200]!r}")


# ─── OSC emitter stub ─────────────────────────────────────────────────────────

class OSCEmitter:
    """
    Thin wrapper around python-osc for sending linguistic metrics to Max/MSP.

    Default target: localhost:7400 (change in Max patch to match).
    OSC address space:
        /petals/token/step        int
        /petals/token/fractal_dim float
        /petals/token/valence     float
        /petals/token/speed       float
        /petals/flock/iteration   int
        /petals/flock/num_paths   int
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 7400):
        try:
            from pythonosc import udp_client
            self._client = udp_client.SimpleUDPClient(host, port)
            self._enabled = True
            logger.info("OSC emitter → %s:%d", host, port)
        except ImportError:
            logger.warning("python-osc not installed; OSC output disabled")
            self._enabled = False

    def send_token_metrics(self, *, step: int, token: str, **metrics):
        if not self._enabled:
            return
        self._client.send_message("/petals/token/step", step)
        for key, val in metrics.items():
            self._client.send_message(f"/petals/token/{key}", float(val))

    def send_flock_state(self, *, iteration: int, num_paths: int):
        if not self._enabled:
            return
        self._client.send_message("/petals/flock/iteration", iteration)
        self._client.send_message("/petals/flock/num_paths", num_paths)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Linguistic Topographer — explore embedding space as text is generated"
    )
    p.add_argument("--model", default="gpt2", help="HuggingFace model name (default: gpt2)")
    p.add_argument("--prompt", default="The nature of light is", help="Generation prompt")
    p.add_argument("--prompts", nargs="+", help="Multiple prompts for flock mode")
    p.add_argument("--max-tokens", type=int, default=40, help="Max new tokens to generate")
    p.add_argument("--flock", action="store_true", help="Run in flock/murmuration mode")
    p.add_argument("--osc", action="store_true", help="Enable OSC output to Max/MSP")
    p.add_argument("--osc-host", default="127.0.0.1")
    p.add_argument("--osc-port", type=int, default=7400)
    p.add_argument("--device", default=None, help="Force device (cpu/cuda/mps)")
    p.add_argument("--visualize", action="store_true", help="Launch Pyglet visualization window")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


async def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
        stream=sys.stderr,
    )

    # Device selection
    if args.device:
        device = args.device
    elif torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    logger.info("Device: %s", device)

    model, tokenizer = load_model(args.model, device)

    osc = OSCEmitter(args.osc_host, args.osc_port) if args.osc else None

    if args.visualize:
        # Launch Pyglet in a background thread; it needs the main thread on some platforms
        import threading, importlib
        vignettes = importlib.import_module("swarm_vignettes")
        t = threading.Thread(target=vignettes.run_visualization, daemon=True)
        t.start()

    if args.flock:
        prompts = args.prompts or [
            args.prompt,
            "In the beginning there was",
            "Language is the house of",
            "Between signal and noise",
        ]
        await run_flock(model, tokenizer, prompts, args.max_tokens, device, osc)
    else:
        await run_single(model, tokenizer, args.prompt, args.max_tokens, device, osc)


if __name__ == "__main__":
    asyncio.run(main())
