(function () {
  'use strict';

  const container = document.getElementById('canvas-container');
  const promptInput = document.getElementById('prompt');
  const runBtn = document.getElementById('run');
  const layerSlider = document.getElementById('layer-slider');
  const layerRiverCheckbox = document.getElementById('layer-river');
  const statusEl = document.getElementById('status');

  let scene, camera, renderer, pointsMesh, lineMesh, layerRiverMeshes = [];
  let currentData = { layers: [], tokens: [], mode: 'mock' };
  let streamPoints = [];
  let streamTokens = [];
  let streamMode = null;
  let ws = null;
  const SCALE = 2.0;

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function initThree() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0d0d0f);
    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(4, 2, 6);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    window.addEventListener('resize', function () {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

    // Simple orbit: mouse drag to rotate, scroll to zoom
    let isDown = false, prevX = 0, prevY = 0;
    const origin = new THREE.Vector3(0, 0, 0);
    let theta = 0.4, phi = 0.4, radius = 8;

    renderer.domElement.addEventListener('mousedown', function (e) {
      if (e.button === 0) { isDown = true; prevX = e.clientX; prevY = e.clientY; }
    });
    renderer.domElement.addEventListener('mouseup', function () { isDown = false; });
    renderer.domElement.addEventListener('mouseleave', function () { isDown = false; });
    renderer.domElement.addEventListener('mousemove', function (e) {
      if (!isDown) return;
      theta += (e.clientX - prevX) * 0.005;
      phi += (e.clientY - prevY) * 0.005;
      phi = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, phi));
      prevX = e.clientX;
      prevY = e.clientY;
      updateCamera();
    });
    renderer.domElement.addEventListener('wheel', function (e) {
      e.preventDefault();
      radius = Math.max(2, Math.min(40, radius + e.deltaY * 0.05));
      updateCamera();
    }, { passive: false });

    function updateCamera() {
      camera.position.x = radius * Math.cos(phi) * Math.sin(theta);
      camera.position.y = radius * Math.sin(phi);
      camera.position.z = radius * Math.cos(phi) * Math.cos(theta);
      camera.lookAt(origin);
      camera.updateProjectionMatrix();
    }
  }

  function updateStreamGeometry(points) {
    if (pointsMesh) {
      scene.remove(pointsMesh);
      pointsMesh.geometry.dispose();
      pointsMesh.material.dispose();
    }
    if (lineMesh) {
      scene.remove(lineMesh);
      lineMesh.geometry.dispose();
      lineMesh.material.dispose();
      lineMesh = null;
    }
    if (!points.length) return;
    const n = points.length;
    const positions = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const p = points[i];
      positions[i * 3]     = (p[0] || 0) * SCALE;
      positions[i * 3 + 1] = (p[1] || 0) * SCALE;
      positions[i * 3 + 2] = (p[2] || 0) * SCALE;
    }
    const pointsGeo = new THREE.BufferGeometry();
    pointsGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    pointsGeo.computeBoundingSphere();
    const pointsMat = new THREE.PointsMaterial({
      size: 0.08,
      color: 0x5c7cfa,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.9,
    });
    pointsMesh = new THREE.Points(pointsGeo, pointsMat);
    scene.add(pointsMesh);
    if (n >= 2) {
      const lineGeo = new THREE.BufferGeometry();
      lineGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x5c7cfa,
        transparent: true,
        opacity: 0.4,
      });
      lineMesh = new THREE.Line(lineGeo, lineMat);
      scene.add(lineMesh);
    }
  }

  function buildGeometryFromLayer(layerPoints, drawTrajectory) {
    const scale = SCALE;
    const n = layerPoints.length;
    const positions = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const p = layerPoints[i];
      positions[i * 3]     = (p[0] || 0) * scale;
      positions[i * 3 + 1] = (p[1] || 0) * scale;
      positions[i * 3 + 2] = (p[2] || 0) * scale;
    }

    const pointsGeo = new THREE.BufferGeometry();
    pointsGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    pointsGeo.computeBoundingSphere();

    const pointsMat = new THREE.PointsMaterial({
      size: 0.08,
      color: 0x5c7cfa,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.9,
    });

    const points = new THREE.Points(pointsGeo, pointsMat);

    if (!drawTrajectory || n < 2) return { points, line: null };

    const lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const lineMat = new THREE.LineBasicMaterial({
      color: 0x5c7cfa,
      transparent: true,
      opacity: 0.4,
    });
    const line = new THREE.Line(lineGeo, lineMat);
    return { points, line };
  }

  function clearRiverMeshes() {
    layerRiverMeshes.forEach(function (m) {
      scene.remove(m);
      if (m.geometry) m.geometry.dispose();
      if (m.material) m.material.dispose();
    });
    layerRiverMeshes = [];
  }

  function showLayerRiver() {
    if (pointsMesh) { scene.remove(pointsMesh); pointsMesh.geometry.dispose(); pointsMesh.material.dispose(); pointsMesh = null; }
    if (lineMesh) { scene.remove(lineMesh); lineMesh.geometry.dispose(); lineMesh.material.dispose(); lineMesh = null; }
    clearRiverMeshes();
    const layers = currentData.layers;
    if (!layers.length || layers.length < 2) return;
    for (var L = 0; L < layers.length; L++) {
      var pts = layers[L];
      if (!pts || pts.length < 2) continue;
      var positions = new Float32Array(pts.length * 3);
      for (var i = 0; i < pts.length; i++) {
        positions[i * 3]     = (pts[i][0] || 0) * SCALE;
        positions[i * 3 + 1] = (pts[i][1] || 0) * SCALE;
        positions[i * 3 + 2] = (pts[i][2] || 0) * SCALE;
      }
      var hue = 0.6 - (L / layers.length) * 0.5;
      var color = new THREE.Color().setHSL(hue, 0.7, 0.6);
      var lineGeo = new THREE.BufferGeometry();
      lineGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      var lineMat = new THREE.LineBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.4 + (L / layers.length) * 0.4,
      });
      var line = new THREE.Line(lineGeo, lineMat);
      scene.add(line);
      layerRiverMeshes.push(line);
    }
    layerSlider.max = Math.max(0, layers.length - 1);
  }

  function showLayer(layerIndex) {
    clearRiverMeshes();
    if (pointsMesh) { scene.remove(pointsMesh); pointsMesh.geometry.dispose(); pointsMesh.material.dispose(); }
    if (lineMesh) { scene.remove(lineMesh); lineMesh.geometry.dispose(); lineMesh.material.dispose(); lineMesh = null; }

    const layers = currentData.layers;
    if (!layers.length) return;
    const idx = Math.max(0, Math.min(layerIndex, layers.length - 1));
    const layerPoints = layers[idx];
    if (!layerPoints || !layerPoints.length) return;

    const { points, line } = buildGeometryFromLayer(layerPoints, true);
    pointsMesh = points;
    scene.add(pointsMesh);
    if (line) {
      lineMesh = line;
      scene.add(lineMesh);
    }

    layerSlider.max = Math.max(0, layers.length - 1);
    layerSlider.value = idx;
  }

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = protocol + '//' + window.location.host + '/ws';
    ws = new WebSocket(url);
    ws.onopen = function () { setStatus('Connected'); };
    ws.onclose = function () { setStatus('Disconnected'); };
    ws.onerror = function () { setStatus('Connection error'); };
    ws.onmessage = function (ev) {
      const msg = JSON.parse(ev.data);
      if (msg.cmd === 'pong') return;
      if (msg.cmd === 'status') {
        setStatus(msg.status || '');
        return;
      }
      if (msg.cmd === 'stream_start') {
        streamPoints = [];
        streamTokens = [];
        streamMode = msg.mode || 'mock';
        setStatus('Streaming trajectory (' + streamMode + ')…');
        return;
      }
      if (msg.cmd === 'stream_token') {
        streamPoints.push(msg.point || [0, 0, 0]);
        streamTokens.push(msg.token != null ? msg.token : '');
        updateStreamGeometry(streamPoints);
        setStatus(streamPoints.length + ' tokens (' + streamMode + ')');
        return;
      }
      if (msg.cmd === 'stream_end') {
        setStatus('Done: ' + streamPoints.length + ' points (mode: ' + (msg.mode || streamMode) + ')');
        streamMode = null;
        return;
      }
      if (msg.cmd === 'states') {
        streamPoints = [];
        streamTokens = [];
        currentData = { layers: msg.layers || [], tokens: msg.tokens || [], mode: msg.mode || 'mock' };
        setStatus('Loaded ' + (currentData.layers[0]?.length || 0) + ' points (mode: ' + currentData.mode + ')');
        if (layerRiverCheckbox && layerRiverCheckbox.checked && currentData.layers.length >= 2) {
          showLayerRiver();
        } else {
          showLayer(parseInt(layerSlider.value, 10));
        }
        return;
      }
      if (msg.cmd === 'error') {
        setStatus('Error: ' + (msg.message || 'Unknown'));
      }
    };
  }

  function run() {
    const prompt = promptInput.value.trim() || 'Hello, world.';
    setStatus('Sending prompt…');
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setStatus('Reconnecting…');
      connect();
      setTimeout(function () {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ cmd: 'prompt', prompt: prompt, max_tokens: 48 }));
        } else {
          setStatus('Not connected. Start the server (uvicorn viz_server:app).');
        }
      }, 500);
      return;
    }
    ws.send(JSON.stringify({ cmd: 'prompt', prompt: prompt, max_tokens: 48 }));
  }

  function animate() {
    rafId = requestAnimationFrame(animate);
    renderer.render(scene, camera);
  }

  runBtn.addEventListener('click', run);
  layerSlider.addEventListener('input', function () {
    if (layerRiverCheckbox && layerRiverCheckbox.checked) {
      showLayerRiver();
    } else {
      showLayer(parseInt(layerSlider.value, 10));
    }
  });
  if (layerRiverCheckbox) {
    layerRiverCheckbox.addEventListener('change', function () {
      if (!currentData.layers.length) return;
      if (layerRiverCheckbox.checked && currentData.layers.length >= 2) {
        showLayerRiver();
      } else {
        showLayer(parseInt(layerSlider.value, 10));
      }
    });
  }

  initThree();
  connect();
  animate();
})();
