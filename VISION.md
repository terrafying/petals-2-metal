# Vision: LLM Internal State as High-Dimensional Geometry

**Product in one line:** The clearest way to see an LLM’s hidden state as fluid 3D geometry in the browser — prompt in, trajectory out, token-by-token.

## Original intent

This repo was conceived to **explore, via high-dimensional geometric visualization, the internal state of an LLM as it interprets and responds to text**. The goal is to make the “thought process” of a language model visible: how representations evolve across layers, how tokens relate in hidden space, and how generation traces a path through that space.

## Current state (brief)

- **Petals** (distributed LLM) is integrated for text generation; the distributed forward path does **not** expose hidden states or attention to the client.
- **Local path**: `FlockGenerator` + `PatternManager` use a local `transformers` model with `output_hidden_states=True`, and apply “flocking” and resonant patterns to hidden state vectors. This is the only path that actually uses LLM internal state.
- **Visualization** is split between:
  - **Desktop**: Pyglet (quantum gravity metaphor, mandalas, shapes). Functional but not embeddable and not tuned for smooth, simulation-style rendering.
  - **Browser**: Templates use Three.js and TensorFlow.js but rely on **static** JSON (`pattern_explorer_data.json`); there is no live pipeline from LLM → backend → browser.
- **PatternManager** is a rich system (resonant modes, security, recursion) that maps model embedding dimension to structured tensors; it is not yet wired to a **direct** “hidden state → 3D/2D geometry” visualization.

So: the **intent** (LLM state → geometry) exists; the **implementation** is partially there (local hidden states, patterns) and partially disconnected (no fluid browser experience, no real-time streaming of true internal state).

## New direction: browser-first, fluid, simulation-grade

- **Rendering**: Target a **highly efficient, fluid graphical experience** in the **browser**: WebGL (e.g. Three.js) or WebGPU for advanced simulation-style visuals. **No matplotlib** for the primary experience; desktop Pyglet can remain for legacy or offline use.
- **Data pipeline**: A small **backend** (Python) that:
  - Runs or connects to an LLM and extracts **hidden states** (and optionally **attention**) per token/layer.
  - Reduces dimension (PCA, UMAP, or similar) to 2D/3D for visualization.
  - **Streams** state to the frontend in real time (e.g. WebSocket or SSE).
- **Frontend**: A single-page **WebGL app** that:
  - Receives state updates (points, trajectories, optional attention edges).
  - Renders point clouds, lines, and trajectories at 60fps with minimal round-trips (prefer “stream once, animate on GPU”).
- **Embeddability**: Everything should be runnable locally and viewable in a normal browser (and later embeddable in docs, notebooks, or dashboards).

## Fruitful avenues of exploration

1. **Token trajectories** ✅ *Implemented*  
   As the model generates, each new token corresponds to a point in hidden space. The **streaming path** sends `stream_start` → one `stream_token` per token (point + token string) → `stream_end`. The frontend appends each point and redraws so the 3D trajectory grows in real time. PCA (or random projection) is fit on the prompt’s last-layer hidden states so the same 3D space is used for the whole run. See **docs/STREAMING_API.md**.

2. **Layer river** ✅ *Implemented*  
   For batch mode (`stream: false`), the server returns **all layers** (one list of 3D points per layer). The frontend has a **Layer river** checkbox: when enabled, it draws every layer as a separate line in the same 3D view (different color/opacity per layer), giving a “braid” of representation through the stack. The layer slider still selects a single layer when Layer river is off.

3. **Attention as structure** *Not yet*  
   If attention weights are available, show them as **edges** (token ↔ token) or as **heat** on a 2D layout of tokens. This can be combined with hidden-state positions (e.g. tokens laid out by reduced hidden state, edges by attention).

4. **Embedding space neighborhoods** *Not yet*  
   Use the **embedding layer** (and optionally later layers) to place tokens in 2D/3D (PCA/UMAP). Explore how prompt and completion tokens cluster or separate.

5. **Small local models for real-time viz** ✅ *In use*  
   The server uses a small model (configurable, default TinyLlama) **locally** with `output_hidden_states=True` for the streaming and batch paths. No Petals required. Optional `stream_mock: true` forces mock data for testing without a model.

6. **Bridging existing work** *Not yet*  
   Reuse **PatternManager** and **FlockGenerator** as optional “filters” or “modulations” on hidden state (e.g. drive mandala or flock visuals from the same state that feeds the new WebGL viz). Keep the quantum/mandala metaphor as one possible **mapping** from state to geometry, not the only one.

## Out of scope for the first iteration

- Full Petals integration for hidden states (Petals currently does not expose them in the client API).
- Production-grade security, auth, or multi-user hosting (focus on local, single-user exploration).

## Success criteria

- User can type (or paste) a prompt and see the **internal state** of an LLM (hidden states, and optionally attention) visualized as **fluid, high-framerate geometry** in the browser.
- Visualization is **clearly tied to the model’s actual computations** (same data that the model uses), not only to hand-crafted “quantum” or pattern outputs.
- Codebase is structured so that new views (e.g. “layer river”, “attention graph”) can be added without rewriting the entire stack.
