# LLM State Viz — See the model think in 3D

**One line:** Type a prompt and watch an LLM’s hidden state as a fluid 3D trajectory in the browser. High-dimensional geometry, token-by-token streaming, layer river — all in one place.

See **[VISION.md](VISION.md)** for intent and roadmap.

---

## Run it (primary)

```bash
pip install -r requirements.txt
uvicorn viz_server:app --reload --host 0.0.0.0
```

Open [http://localhost:8000](http://localhost:8000), enter a prompt, click **Run**. The 3D trajectory (point cloud + line) grows in real time as the model generates. Each point is last-layer hidden state reduced to 3D (PCA or random projection). Drag to rotate, scroll to zoom.

- **Streaming** (default): trajectory grows live. **Layer** slider and **Layer river** (all layers as braid) apply in batch mode (`stream: false`).
- **No local model:** server uses **mock** trajectory. Use `stream_mock: true` in the WebSocket payload to force mock when a model is available.
- **With** `transformers` + `torch`: a small model (e.g. TinyLlama) loads on first use. See **docs/STREAMING_API.md** for the WebSocket protocol.

---

## Repo layout

| Path | Purpose |
|------|--------|
| **viz_server.py** | FastAPI + WebSocket: LLM hidden-state extraction, dimension reduction, stream to frontend. |
| **viz_static/** | Browser frontend: WebGL (Three.js), streaming trajectory + Layer river. |
| **VISION.md** | Intent, current state, and roadmap. |
| **docs/STREAMING_API.md** | WebSocket protocol. |
| **docs/PLAN_CEO_REVIEW.md** | Focus and cleanup rationale. |
| *Legacy / optional* | **launch_visualizer.py**, **visualization_manager.py**, **pattern_manager.py**, **flock_generator.py**, **swarm_vignettes.py** — Pyglet, swarm, mandala experiments. **connect_client.py**, **client.py**, **git_petals/** — Petals distributed demo (no hidden-state viz). |

---

## Optional: other ways to run

- **Desktop (Pyglet)** — `python launch_visualizer.py`. Legacy quantum gravity / mandala style; see `--help`.
- **Petals distributed demo** — See **DEMO_INSTRUCTIONS.md** for running a Petals server and client. Petals does not expose hidden states; the main browser viz uses a **local** model or mock data.

---

## Dependencies

- **Core**: `torch`, `numpy`, `pyglet`, `matplotlib`, `pillow` (see `requirements.txt`).
- **Browser viz**: `fastapi`, `uvicorn`, `scikit-learn` (optional; used for PCA in `viz_server.py`; falls back to random projection if missing).

---

## Development and next steps

- **Streaming** ✅ Token-by-token generation streams one 3D point per token; the frontend grows the trajectory in real time. **Layer river** ✅ Batch mode can show all layers as separate lines (braid) via the Layer river checkbox.
- **New views**: Add attention edges (when the model exposes attention), token labels on hover, or embedding-space neighborhoods (PCA/UMAP) without rewriting the whole stack.
- **Bridging**: Reuse **PatternManager** / **FlockGenerator** to drive alternative geometries (mandala, flock) from the same hidden state that feeds the WebGL viz.

---

## License

MIT (see LICENSE).
