# /plan-ceo-review: Clean up and focus this repo

## What is this product actually for?

**The 10-star product:** *The clearest, fastest way to see an LLM’s hidden state as fluid 3D geometry in the browser.*

Not “Petals on Metal.” Not “quantum gravity visualizer.” Not “swarm of models.” The one thing that makes this repo worth opening is: **prompt → model runs → you see the thought trajectory in 3D, live.** One entry point. One mental model. Optional depth (layer river, attention) for power users.

---

## What’s in the way

1. **Identity confusion**  
   Repo name and layout suggest “Petals + Metal.” DEMO_INSTRUCTIONS is entirely “run Petals server + client” (no viz, no hidden states). The *working* path is local model + `viz_server` + `viz_static`. Petals doesn’t expose hidden states. Two unrelated stories dilute focus.

2. **Multiple “main” experiences**  
   README presents Pyglet launcher, swarm vignettes, Petals demo, and browser viz as peers. A new user doesn’t know which one is the app. The only path that delivers the core promise (see the model think) is: **browser viz**.

3. **Heavy legacy**  
   `pattern_manager` (1200+ lines), `flock_generator`, `swarm_vignettes` (1500+), `visualization_manager` (1100+), `shape_visualizer`, `storyteller`, `connect_client`, `client`, `model_manager`, `distributed_swarm`, etc. Many were for the old “quantum / swarm / Petals” vision. The new north star is: one server, one frontend, real hidden states, browser.

4. **Docs spread**  
   README, VISION, DEMO_INSTRUCTIONS, AGENTS, STREAMING_API. DEMO_INSTRUCTIONS is a different product (distributed inference demo). It should be clearly “optional: Petals demo” so the primary story is obvious.

---

## Recommendations

| Action | Why |
|--------|-----|
| **Name the product in one line** | “LLM State Viz” or “Hidden State Explorer” — browser-first, see the model think. Add that sentence at the top of README and VISION. |
| **One way to run (primary)** | `pip install -r requirements.txt && uvicorn viz_server:app --reload` → open localhost:8000. First 5 lines of README. |
| **Mark Petals as optional** | Short section or `docs/petals-demo.md`: “Optional: run distributed Petals (no hidden-state viz).” DEMO_INSTRUCTIONS refocused or moved so it doesn’t compete with the main product. |
| **Mark legacy as legacy** | Pyglet, swarm_vignettes, pattern_manager/flock — one short “Legacy / optional experiments” paragraph; or move to `legacy/` / `experiments/` so root = viz_server + viz_static + clear README. |
| **Don’t delete code yet** | Just stop presenting everything as equal. Primary: browser viz. Optional: desktop (Pyglet), Petals demo, swarm/pattern experiments. |

---

## Outcome

A newcomer lands on the repo and immediately knows: *This is the app where you type a prompt and watch the model’s internal state as a 3D trajectory.* Everything else is “also here” but not the main offer.
