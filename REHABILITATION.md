# Rehabilitation Notes: petals-2-metal → Linguistic Topographer

## Original Vision

`petals-2-metal` was conceived as three interlocking layers:

1. **Infrastructure** — Apple Silicon–optimised fork of the [Petals](https://github.com/bigscience-workshop/petals)
   distributed-inference framework ("petals-2-metal" = flower petals → Metal Performance Shaders).
   Multiple Macs would share transformer blocks over a local network.

2. **Creative computation** — the genuinely novel part. Hidden states were treated as points in a
   high-dimensional *linguistic vector space*:
   - **Resonant modes** — harmonic oscillators (`frequency`, `amplitude`, `phase`, `decay`) applied to
     model activations, drawn from physics metaphors for attention and resonance in language
   - **Fractal dimensionality** — measuring how "expansive" or "focused" a generation trajectory is
     (described in `gripcorduroyred.txt`, a design conversation with an AI assistant)
   - **Murmuration / flock dynamics** — multiple generation paths as a boid swarm with
     cohesion / separation / alignment forces on embedding tensors
   - **Narrative threads** — thematic and emotional metadata extracted from activation statistics

3. **Artistic output** — Max/MSP via OSC, Pyglet mandalas, "EntendreGlyphs" (ambiguous words
   rendered as visual glyphs), spherical-harmonic visualisation.

## What Went Wrong

The creative computation layer (the interesting part) was wired exclusively to the infrastructure
layer (Petals P2P), which was never stable. Missing modules (`unified_discovery`), broken Ray
actors, and unconditional heavy imports caused the whole thing to fail to import, leaving
`storyteller.py`, `flock_generator.py`, and the resonant-mode math stranded inside broken plumbing.

## New Direction

Strip the distributed Petals infrastructure. Rehabilitate the creative layer around **local models**
(any HuggingFace model via `transformers`, no distributed dependency).

### New modules

| File | Role |
|------|------|
| `linguistic_topographer.py` | Main entry point — CLI, model loading, single/flock dispatch |
| `vector_space_explorer.py` | Token-by-token trajectory tracking, fractal dimension (Grassberger-Procaccia), resonant probes, PCA projection |

### Rehabilitated existing modules

| File | Status | Notes |
|------|--------|-------|
| `pattern_manager.py` | Used | `ResonantMode`, `PatternManager` — core resonant-mode math |
| `storyteller.py` | Used | `NarrativeThread` weaving from activation statistics |
| `flock_generator.py` | Used | Boid dynamics on embedding tensors |
| `swarm_vignettes.py` | Fixed imports | Optional deps (`ray`, `matplotlib`, `pythonosc`) guarded; `run_visualization()` entry point added |

### Removed dependency

- `unified_discovery` (never existed) — replaced by `local_discovery.py` for peer discovery when needed
- Unconditional `ray`, `seaborn`, `matplotlib`, `pythonosc` top-level imports — all now guarded with `try/except`

## Running It

```bash
# Zero-dependency demo (gpt2 downloads automatically, ~500 MB)
python linguistic_topographer.py --prompt "The nature of light is"

# Flock mode: four simultaneous generation paths
python linguistic_topographer.py --flock --model distilgpt2

# With Pyglet mandala visualization
python linguistic_topographer.py --visualize --prompt "In the beginning"

# With OSC output to Max/MSP (port 7400)
python linguistic_topographer.py --osc --prompt "Language is the house of being"
```

## Key Ideas Still to Implement

- **Spherical-harmonic mandala** driven by linguistic-vector components (sketched in `gripcorduroyred.txt`)
- **Live OSC address space** fully mapped to Max patch (`/petals/token/fractal_dim`, `/petals/flock/cohesion`, etc.)
- **Trajectory replay** — load a saved trajectory and re-explore it with different resonant probes
- **Cross-lingual murmuration** — same prompt in multiple languages, watch the flock converge/diverge
- **Hausdorff dimension** as an alternative to correlation dimension for sparse trajectories
