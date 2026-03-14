# Petal 2 Metal — LLM internal state as geometry

This repo explores **high-dimensional geometric visualization of an LLM’s internal state** as it interprets and responds to text: hidden states, layer-by-layer representation, and (where available) attention. The goal is a **fluid, simulation-style visual experience** in the **browser** (WebGL), plus optional desktop (Pyglet) and integration with the Petals distributed LLM stack.

See **[VISION.md](VISION.md)** for the full intent, current state, and planned directions.

---

## Quick start: browser visualization

The main visualization is a **browser-based WebGL app** backed by a small Python server that can use a real LLM (with hidden states) or mock data.

1. **Install** (from repo root):

   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server**:

   ```bash
   uvicorn viz_server:app --reload --host 0.0.0.0
   ```

3. **Open** [http://localhost:8000](http://localhost:8000) in a browser.

4. Enter a prompt and click **Run**. The server **streams** token-by-token: the 3D trajectory (point cloud + line) grows in real time as the model generates. Each point is the last-layer hidden state for that token, reduced to 3D (PCA or random projection). Drag to rotate, scroll to zoom.

- **Streaming** (default): one `stream_token` per token so the trajectory grows live. **Layer** slider is for batch mode only.
- **Batch mode**: send `stream: false` (e.g. from a custom client) to get all layers at once; then use the **Layer** slider or the **Layer river** checkbox to see one layer or all layers as a braid in 3D.
- **Without** a local LLM: the server uses **mock** trajectory (deterministic from the prompt). Use `stream_mock: true` in the WebSocket payload to force mock when a model is available.
- **With** `transformers` and `torch`: a small model (default TinyLlama) is loaded on first use for real hidden-state streaming. See **docs/STREAMING_API.md** for the WebSocket protocol.

---

## Repo layout (high level)

| Path | Purpose |
|------|--------|
| **VISION.md** | Intent, current state, and fruitful avenues (token trajectories, layer river, attention, etc.). |
| **viz_server.py** | FastAPI + WebSocket server: optional LLM, hidden-state extraction, dimension reduction, stream to frontend. |
| **viz_static/** | Browser frontend: single-page WebGL (Three.js); streaming trajectory (grows token-by-token) and Layer river (all layers as braid). |
| **docs/STREAMING_API.md** | WebSocket protocol: `prompt`, `stream` / batch, `stream_start` / `stream_token` / `stream_end`, `states`. |
| **launch_visualizer.py** | Desktop Pyglet launcher (quantum gravity / mandala style). |
| **visualization_manager.py** | Pyglet + pattern/lattice logic and legacy browser templates. |
| **pattern_manager.py** | Resonant modes, pattern tensors, security; used by flock/swarm and can drive geometry. |
| **flock_generator.py** | Uses a **local** transformers model with `output_hidden_states=True`, applies flocking and PatternManager; the existing “LLM state → geometry” path. |
| **swarm_vignettes.py** | Vignettes, storytelling, Pyglet/matplotlib visuals. |
| **connect_client.py** / **client.py** | Petals/local client and pattern generation. |
| **git_petals/** | Petals distributed LLM (submodule). |

---

## Other ways to run

- **Desktop (Pyglet)**  
  ```bash
  python launch_visualizer.py
  ```  
  Quantum gravity / mandala style; see `--help` for options.

- **Petals + local discovery**  
  See **DEMO_INSTRUCTIONS.md** for running a Petals server and client. Note: the current Petals client API does not expose hidden states for visualization; the browser viz uses a **local** model or mock data.

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
