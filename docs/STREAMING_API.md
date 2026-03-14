# LLM State Viz — WebSocket API

The backend (`viz_server`) exposes a WebSocket at `/ws` for streaming or batch visualization.

## Commands (client → server)

- **`ping`** — Server replies with `pong` (keepalive).
- **`prompt`** — Run the model (or mock) on a prompt and send state back.

### `prompt` payload

| Field         | Type    | Default       | Description |
|---------------|---------|---------------|-------------|
| `prompt`      | string  | `"Hello, world."` | Input text. |
| `max_tokens`  | int     | `48`          | Max new tokens to generate (stream) or approximate length (batch). |
| `stream`      | bool    | `true`        | If `true`, stream token-by-token (`stream_start` → `stream_token`* → `stream_end`). If `false`, send one `states` message with all layers. |
| `stream_mock` | bool    | `false`       | If `true`, use mock trajectory even when a real model is available (for testing). |

## Messages (server → client)

- **`status`** — `{ "cmd": "status", "status": "computing" }` (or similar).
- **`stream_start`** — Start of a trajectory stream. `mode`: `"real"` or `"mock"`.
- **`stream_token`** — One point on the trajectory: `{ "cmd": "stream_token", "point": [x,y,z], "token": "...", "index": n }`. The frontend appends to the current trajectory and redraws.
- **`stream_end`** — End of stream. `mode`: `"real"` or `"mock"`.
- **`states`** — Batch result: `{ "cmd": "states", "layers": [[[x,y,z], ...], ...], "tokens": ["...", ...], "mode": "real"|"mock" }`. `layers[layer_index]` is the list of 3D points for that layer (one per token).
- **`error`** — `{ "cmd": "error", "message": "..." }`.

## Streaming (token-by-token)

1. Client sends `{ "cmd": "prompt", "prompt": "...", "max_tokens": 48, "stream": true }`.
2. Server sends `stream_start`, then one `stream_token` per token (prompt tokens first, then generated tokens), then `stream_end`.
3. Each `stream_token` contains a single 3D point (last-layer hidden state reduced via PCA or random projection) and the token string. The frontend grows the trajectory in real time.

## Batch (all layers)

1. Client sends `{ "cmd": "prompt", "prompt": "...", "max_tokens": 48, "stream": false }`.
2. Server runs the model (or mock) once and sends one `states` message with `layers` (one array of 3D points per layer) and `tokens`.
3. The frontend can show a single layer (slider) or **Layer river** (all layers as separate lines in 3D).

## Layer river

When the frontend has batch data (`states` with multiple layers), the **Layer river** checkbox draws every layer as its own line in the same 3D space (different color/opacity per layer). This shows how the same sequence is represented at each layer — a “braid” or “river” of representations through the stack.

## Testing

With the repo root as cwd, run the server’s HTTP and WebSocket behavior via FastAPI’s TestClient (stream and batch with `stream_mock: true` so no model is loaded):

```bash
python -c "
from fastapi.testclient import TestClient
from viz_server import app
client = TestClient(app)
assert client.get('/').status_code == 200
with client.websocket_connect('/ws') as ws:
    ws.send_json({'cmd': 'prompt', 'prompt': 'x', 'max_tokens': 3, 'stream': True, 'stream_mock': True})
    cmds = [ws.receive_json().get('cmd') for _ in range(6)]
    assert 'stream_end' in cmds
print('OK')
"
```
