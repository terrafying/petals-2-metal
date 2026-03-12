"""
vector_space_explorer.py
────────────────────────
Tracks how text generation traces a path through a model's embedding space,
computes geometric and fractal properties of that trajectory, and exposes
resonant probes for perturbation experiments.

Core ideas (from gripcorduroyred.txt):
  - Each generated token is a point in R^d (last hidden state, mean-pooled)
  - The sequence of points forms a *trajectory*
  - Fractal dimension of that trajectory measures how "expansive" or "focused"
    the linguistic motion is at any moment
  - Resonant probes nudge the trajectory along specific frequency axes to
    explore the surrounding manifold

Mathematical toolkit:
  - Correlation dimension (Grassberger-Procaccia) for fractal estimation
  - Finite-difference velocity (step-to-step Euclidean distance)
  - Cosine curvature (angle between successive displacement vectors)
  - PCA for reduced-dimension projection (for visualization export)
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import AsyncGenerator, Callable, Optional

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class Waypoint:
    """A single step in the trajectory through embedding space."""
    token: str
    hidden_state: torch.Tensor      # [1, seq_len, hidden_dim]
    point: np.ndarray               # mean-pooled, shape [hidden_dim]
    step: int
    fractal_dim: float = 0.0
    speed: float = 0.0             # Euclidean distance from previous point
    curvature: float = 0.0         # Cosine of angle between successive steps
    valence: float = 0.0           # Emotional valence proxy (from storyteller logic)


@dataclass
class Trajectory:
    """Full trajectory produced by a single generation run."""
    prompt: str
    generated_text: str
    waypoints: list[tuple[str, torch.Tensor, dict]]  # (token, hidden, metrics)
    points: np.ndarray              # [n_steps, hidden_dim]  mean-pooled per step
    fractal_dims: list[float]
    speeds: list[float]
    curvatures: list[float]


# ─── Fractal dimension ────────────────────────────────────────────────────────

def correlation_dimension(points: np.ndarray, n_scales: int = 8) -> float:
    """
    Estimate the correlation dimension of a point cloud via the
    Grassberger-Procaccia algorithm.

    points: [N, D]  — trajectory points in embedding space
    Returns a float (the estimated dimension).

    For a 1-D curve in 3-D space the result is ≈ 1.
    For a space-filling fractal it approaches the ambient dimension.
    """
    n = len(points)
    if n < 8:
        return 0.0

    # Work in a reduced subspace (first 32 PCA dims) for computational efficiency
    if points.shape[1] > 32:
        try:
            from sklearn.decomposition import PCA
            pca = PCA(n_components=32)
            pts = pca.fit_transform(points)
        except Exception:
            pts = points[:, :32]
    else:
        pts = points

    # Pairwise distances (upper triangle only)
    dists = []
    for i in range(n):
        for j in range(i + 1, n):
            d = np.linalg.norm(pts[i] - pts[j])
            if d > 0:
                dists.append(d)

    if not dists:
        return 0.0

    dists = np.array(dists)
    r_min, r_max = dists.min(), dists.max()
    if r_min >= r_max:
        return 0.0

    radii = np.logspace(np.log10(r_min), np.log10(r_max), n_scales)
    C = []
    for r in radii:
        count = np.sum(dists < r)
        C.append(count / len(dists) if len(dists) > 0 else 0.0)

    # Slope of log C(r) vs log r
    log_r = np.log(radii + 1e-12)
    log_C = np.log(np.array(C) + 1e-12)

    # Robust linear fit (ignore saturated tails)
    mask = (log_C > log_C.min() + 0.1) & (log_C < log_C.max() - 0.1)
    if mask.sum() < 2:
        mask = np.ones(len(log_r), dtype=bool)

    coeffs = np.polyfit(log_r[mask], log_C[mask], 1)
    return float(max(0.0, coeffs[0]))


def _rolling_fractal_dim(points: np.ndarray, window: int = 16) -> float:
    """Fractal dimension of the last `window` steps."""
    if len(points) < 4:
        return 0.0
    return correlation_dimension(points[-window:])


# ─── Explorer ─────────────────────────────────────────────────────────────────

class VectorSpaceExplorer:
    """
    Wraps a local HuggingFace model and generates text token-by-token,
    capturing the full hidden-state trajectory and computing geometric metrics.
    """

    def __init__(
        self,
        model: AutoModelForCausalLM,
        tokenizer: AutoTokenizer,
        device: str = "cpu",
        fractal_window: int = 16,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.fractal_window = fractal_window

    # ── mean-pool a hidden state to a single point ────────────────────────────
    @staticmethod
    def _pool(hidden_state: torch.Tensor) -> np.ndarray:
        """hidden_state: [1, seq_len, hidden_dim] → [hidden_dim] numpy array."""
        return hidden_state.squeeze(0).mean(dim=0).float().cpu().numpy()

    # ── emotional valence proxy (mirrors storyteller._calculate_emotional_valence) ─
    @staticmethod
    def _valence(point: np.ndarray) -> float:
        """Map the first 5 dims of the mean-pooled point to a [-1, 1] valence."""
        weights = np.array([1.0, 0.9, 0.8, 0.7, 0.6])
        vals = np.tanh(point[:5]) if len(point) >= 5 else np.tanh(point)
        w = weights[: len(vals)]
        return float(np.dot(vals, w) / w.sum())

    # ── step-by-step generation ───────────────────────────────────────────────
    async def trace_generation(
        self,
        prompt: str,
        max_new_tokens: int = 40,
        temperature: float = 0.8,
        top_p: float = 0.9,
        on_token: Optional[Callable] = None,
    ) -> Trajectory:
        """
        Generate `max_new_tokens` tokens one at a time, capturing the
        hidden-state trajectory at each step.

        on_token(step, token_str, hidden_state, metrics) is called per token.
        """
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        input_ids = inputs["input_ids"]

        waypoints: list[tuple[str, torch.Tensor, dict]] = []
        all_points: list[np.ndarray] = []
        speeds: list[float] = []
        curvatures: list[float] = []
        fractal_dims: list[float] = []
        prev_point: Optional[np.ndarray] = None
        prev_disp: Optional[np.ndarray] = None
        generated_text = ""

        for step in range(max_new_tokens):
            with torch.no_grad():
                out = self.model(
                    input_ids,
                    output_hidden_states=True,
                    return_dict=True,
                )

            # Last-layer hidden states: [1, seq_len, hidden_dim]
            hidden = out.hidden_states[-1]
            point = self._pool(hidden)
            all_points.append(point)

            # Geometric metrics
            speed = float(np.linalg.norm(point - prev_point)) if prev_point is not None else 0.0
            speeds.append(speed)

            curvature = 0.0
            if prev_point is not None and prev_disp is not None:
                disp = point - prev_point
                norm_prev = np.linalg.norm(prev_disp)
                norm_curr = np.linalg.norm(disp)
                if norm_prev > 1e-9 and norm_curr > 1e-9:
                    cos = np.dot(prev_disp, disp) / (norm_prev * norm_curr)
                    curvature = float(np.clip(cos, -1.0, 1.0))
                prev_disp = disp
            elif prev_point is not None:
                prev_disp = point - prev_point

            curvatures.append(curvature)

            frac_dim = _rolling_fractal_dim(
                np.array(all_points), window=self.fractal_window
            )
            fractal_dims.append(frac_dim)

            valence = self._valence(point)

            # Sample next token from logits
            logits = out.logits[:, -1, :]  # [1, vocab]
            # Temperature + top-p sampling
            next_token_id = _sample_token(logits, temperature=temperature, top_p=top_p)

            token_str = self.tokenizer.decode(
                [next_token_id.item()], skip_special_tokens=True
            )
            generated_text += token_str

            metrics = {
                "fractal_dim": frac_dim,
                "speed": speed,
                "curvature": curvature,
                "valence": valence,
            }

            waypoints.append((token_str, hidden.detach().cpu(), metrics))

            if on_token:
                on_token(step, token_str, hidden, metrics)

            # Append token and continue
            input_ids = torch.cat(
                [input_ids, next_token_id.unsqueeze(0)], dim=-1
            )
            prev_point = point

            # Yield to event loop
            await asyncio.sleep(0)

            # Stop on EOS
            if next_token_id.item() == self.tokenizer.eos_token_id:
                break

        return Trajectory(
            prompt=prompt,
            generated_text=generated_text,
            waypoints=waypoints,
            points=np.array(all_points),
            fractal_dims=fractal_dims,
            speeds=speeds,
            curvatures=curvatures,
        )

    # ── summary stats for a completed trajectory ──────────────────────────────
    @staticmethod
    def trajectory_stats(traj: Trajectory) -> dict:
        """Return a dict of scalar summary statistics for the trajectory."""
        pts = traj.points
        stats: dict = {}

        stats["n_steps"] = len(pts)

        if len(pts) > 1:
            stats["path_length"] = float(np.sum(traj.speeds))
            stats["mean_speed"] = float(np.mean(traj.speeds))
            stats["max_speed"] = float(np.max(traj.speeds))
            stats["mean_curvature"] = float(np.mean(traj.curvatures))

            # Net displacement (first → last)
            stats["net_displacement"] = float(np.linalg.norm(pts[-1] - pts[0]))

            # Tortuosity: path length / net displacement
            nd = stats["net_displacement"]
            stats["tortuosity"] = (
                stats["path_length"] / nd if nd > 1e-9 else float("inf")
            )
        else:
            stats.update(
                path_length=0.0,
                mean_speed=0.0,
                max_speed=0.0,
                mean_curvature=0.0,
                net_displacement=0.0,
                tortuosity=1.0,
            )

        # Fractal dimension (global, over full trajectory)
        stats["fractal_dim_global"] = correlation_dimension(pts)
        stats["fractal_dim_final"] = (
            traj.fractal_dims[-1] if traj.fractal_dims else 0.0
        )

        # Spread in embedding space (mean pairwise distance, sampled)
        if len(pts) >= 4:
            sample = pts[:: max(1, len(pts) // 20)]  # up to 20 points
            dists = [
                np.linalg.norm(sample[i] - sample[j])
                for i in range(len(sample))
                for j in range(i + 1, len(sample))
            ]
            stats["embedding_spread"] = float(np.mean(dists)) if dists else 0.0
        else:
            stats["embedding_spread"] = 0.0

        return stats

    # ── resonant probe ────────────────────────────────────────────────────────
    def resonant_probe(
        self,
        hidden_state: torch.Tensor,
        frequency: float = 0.1,
        amplitude: float = 0.05,
        phase: float = 0.0,
        step: int = 0,
    ) -> torch.Tensor:
        """
        Perturb `hidden_state` with a sinusoidal resonant mode.

        This is the core of the resonant-mode concept from pattern_manager.py,
        extracted here as a standalone probe for exploration experiments.

        Returns the perturbed tensor with the same shape.
        """
        dim = hidden_state.shape[-1]
        t = step * frequency + phase
        indices = torch.arange(dim, dtype=torch.float32, device=hidden_state.device)
        wave = amplitude * torch.sin(2 * math.pi * t + indices / dim * 2 * math.pi)
        return hidden_state + wave.reshape(1, 1, -1)

    # ── PCA projection for visualization ──────────────────────────────────────
    @staticmethod
    def project_trajectory(traj: Trajectory, n_components: int = 3) -> np.ndarray:
        """
        Project the trajectory points to n_components dimensions via PCA.
        Returns [n_steps, n_components].
        """
        pts = traj.points
        if pts.shape[0] < 2 or pts.shape[1] <= n_components:
            return pts[:, :n_components]

        try:
            from sklearn.decomposition import PCA
            pca = PCA(n_components=n_components)
            return pca.fit_transform(pts)
        except Exception as e:
            logger.warning("PCA failed: %s", e)
            return pts[:, :n_components]


# ─── Token sampling ───────────────────────────────────────────────────────────

def _sample_token(
    logits: torch.Tensor,
    temperature: float = 0.8,
    top_p: float = 0.9,
) -> torch.Tensor:
    """Sample a single next token with temperature + top-p (nucleus) filtering."""
    logits = logits / max(temperature, 1e-6)

    # Top-p filtering
    sorted_logits, sorted_indices = torch.sort(logits, descending=True, dim=-1)
    cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)

    # Remove tokens that push cumulative prob above top_p
    sorted_indices_to_remove = cumulative_probs - torch.softmax(sorted_logits, dim=-1) > top_p
    sorted_logits[sorted_indices_to_remove] = float("-inf")

    # Scatter back to original ordering
    logits = sorted_logits.scatter(1, sorted_indices, sorted_logits)
    probs = torch.softmax(logits, dim=-1)
    return torch.multinomial(probs, num_samples=1).squeeze(-1)
