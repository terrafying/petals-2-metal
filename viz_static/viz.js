(function () {
  'use strict';

  const container = document.getElementById('canvas-container');
  const promptInput = document.getElementById('prompt');
  const runBtn = document.getElementById('run');
  const maxTokensInput = document.getElementById('max-tokens');
  const layerSlider = document.getElementById('layer-slider');
  const layerRiverCheckbox = document.getElementById('layer-river');
  const allLayersCheckbox = document.getElementById('all-layers');
  const statusEl = document.getElementById('status');

  let scene, camera, renderer, pointsMesh, lineMesh, layerRiverMeshes = [];
  let currentData = { layers: [], tokens: [], mode: 'mock' };
  let streamPoints = [];
  let streamTokens = [];
  let streamMode = null;
  let ws = null;
  let rafId = null;
  const SCALE = 2.0;
  let cameraOrbit = { theta: 0.4, phi: 0.4, radius: 8 };
  let orbitCenter = { x: 0, y: 0, z: 0 };
  let updateCameraFromOrbit = null;

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function initThree() {
    var placeholder = document.getElementById('canvas-placeholder');
    if (typeof THREE === 'undefined') {
      setStatus('Error: Three.js did not load. Check the console or try another network.');
      if (placeholder) placeholder.textContent = 'Three.js failed to load (check Network tab for cdnjs).';
      return;
    }
    try {
      if (placeholder) placeholder.remove();
    } catch (e) { /* ignore */ }
    try {
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0d0d0f);
      camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
      camera.position.set(4, 2, 6);
      camera.lookAt(0, 0, 0);

      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      var w = container.clientWidth || window.innerWidth || 800;
      var h = container.clientHeight || window.innerHeight || 600;
      if (w <= 0 || h <= 0) {
        w = 800;
        h = 600;
      }
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.domElement.style.display = 'block';
      renderer.domElement.style.width = '100%';
      renderer.domElement.style.height = '100%';
      container.appendChild(renderer.domElement);

      var grid = new THREE.GridHelper(8, 8, 0x555555, 0x444444);
      grid.position.set(0, 0, 0);
      scene.add(grid);

      window.addEventListener('resize', function () {
        var cw = container.clientWidth || window.innerWidth;
        var ch = container.clientHeight || window.innerHeight;
        if (cw > 0 && ch > 0) {
          camera.aspect = cw / ch;
          camera.updateProjectionMatrix();
          renderer.setSize(cw, ch);
        }
      });
      renderer.render(scene, camera);
      if (placeholder && placeholder.parentNode) placeholder.remove();
    } catch (err) {
      var msg = (err && err.message) ? err.message : String(err);
      setStatus('Error: ' + msg);
      if (placeholder) {
        placeholder.textContent = 'Canvas error: ' + msg;
        placeholder.style.color = '#c55';
      }
      return;
    }

    // Simple orbit: mouse drag to rotate, scroll to zoom
    let isDown = false, prevX = 0, prevY = 0;
    const origin = new THREE.Vector3(0, 0, 0);

    function updateCamera() {
      var r = cameraOrbit.radius, th = cameraOrbit.theta, ph = cameraOrbit.phi;
      var cx = orbitCenter.x, cy = orbitCenter.y, cz = orbitCenter.z;
      camera.position.x = cx + r * Math.cos(ph) * Math.sin(th);
      camera.position.y = cy + r * Math.sin(ph);
      camera.position.z = cz + r * Math.cos(ph) * Math.cos(th);
      camera.lookAt(cx, cy, cz);
      camera.updateProjectionMatrix();
    }
    updateCameraFromOrbit = updateCamera;

    renderer.domElement.addEventListener('mousedown', function (e) {
      if (e.button === 0) { isDown = true; prevX = e.clientX; prevY = e.clientY; }
    });
    renderer.domElement.addEventListener('mouseup', function () { isDown = false; });
    renderer.domElement.addEventListener('mouseleave', function () { isDown = false; });
    renderer.domElement.addEventListener('mousemove', function (e) {
      if (!isDown) return;
      cameraOrbit.theta += (e.clientX - prevX) * 0.005;
      cameraOrbit.phi += (e.clientY - prevY) * 0.005;
      cameraOrbit.phi = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, cameraOrbit.phi));
      prevX = e.clientX;
      prevY = e.clientY;
      updateCamera();
    });
    renderer.domElement.addEventListener('wheel', function (e) {
      e.preventDefault();
      cameraOrbit.radius = Math.max(2, Math.min(80, cameraOrbit.radius + e.deltaY * 0.05));
      updateCamera();
    }, { passive: false });
  }

  function boundingSphereFromPoints(points) {
    if (!points || points.length === 0) return null;
    var minx = Infinity, miny = Infinity, minz = Infinity;
    var maxx = -Infinity, maxy = -Infinity, maxz = -Infinity;
    for (var i = 0; i < points.length; i++) {
      var p = points[i];
      var x = (p[0] || 0) * SCALE, y = (p[1] || 0) * SCALE, z = (p[2] || 0) * SCALE;
      if (x < minx) minx = x; if (x > maxx) maxx = x;
      if (y < miny) miny = y; if (y > maxy) maxy = y;
      if (z < minz) minz = z; if (z > maxz) maxz = z;
    }
    var cx = (minx + maxx) / 2, cy = (miny + maxy) / 2, cz = (minz + maxz) / 2;
    var r = 0;
    for (var j = 0; j < points.length; j++) {
      var q = points[j];
      var dx = (q[0] || 0) * SCALE - cx, dy = (q[1] || 0) * SCALE - cy, dz = (q[2] || 0) * SCALE - cz;
      var d = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (d > r) r = d;
    }
    if (r < 0.5) r = 2;
    return { center: new THREE.Vector3(cx, cy, cz), radius: r };
  }

  function fitCameraToContent(pointsOrLayers) {
    if (!camera || !updateCameraFromOrbit) return;
    var points = [];
    if (Array.isArray(pointsOrLayers) && pointsOrLayers.length > 0) {
      if (Array.isArray(pointsOrLayers[0]) && pointsOrLayers[0].length > 0 && typeof pointsOrLayers[0][0] === 'object') {
        for (var L = 0; L < pointsOrLayers.length; L++)
          for (var k = 0; k < (pointsOrLayers[L] || []).length; k++) points.push(pointsOrLayers[L][k]);
      } else {
        points = pointsOrLayers;
      }
    }
    var sphere = boundingSphereFromPoints(points);
    if (!sphere) return;
    var dist = sphere.radius * 2.2;
    orbitCenter.x = sphere.center.x; orbitCenter.y = sphere.center.y; orbitCenter.z = sphere.center.z;
    camera.position.copy(sphere.center).add(new THREE.Vector3(1, 0.5, 1).normalize().multiplyScalar(dist));
    camera.lookAt(sphere.center);
    camera.updateProjectionMatrix();
    cameraOrbit.radius = dist;
    var pos = camera.position;
    cameraOrbit.theta = Math.atan2(pos.x - sphere.center.x, pos.z - sphere.center.z);
    cameraOrbit.phi = Math.asin((pos.y - sphere.center.y) / dist);
  }

  function updateStreamGeometry(points) {
    if (!scene) return;
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
    if (!scene) return;
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
    if (!scene) return;
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
        fitCameraToContent(streamPoints);
        return;
      }
      if (msg.cmd === 'states') {
        streamPoints = [];
        streamTokens = [];
        currentData = { layers: msg.layers || [], tokens: msg.tokens || [], mode: msg.mode || 'mock' };
        setStatus('Loaded ' + (currentData.layers[0]?.length || 0) + ' points, ' + (currentData.layers.length || 0) + ' layers (mode: ' + currentData.mode + ')');
        if (currentData.layers.length >= 2) {
          if (layerRiverCheckbox) layerRiverCheckbox.checked = true;
          showLayerRiver();
        } else {
          showLayer(parseInt(layerSlider.value, 10));
        }
        fitCameraToContent(currentData.layers);
        return;
      }
      if (msg.cmd === 'error') {
        setStatus('Error: ' + (msg.message || 'Unknown'));
      }
    };
  }

  function run() {
    const prompt = promptInput.value.trim() || 'Hello, world.';
    const maxTokens = Math.max(8, Math.min(256, parseInt(maxTokensInput && maxTokensInput.value, 10) || 96));
    const stream = !(allLayersCheckbox && allLayersCheckbox.checked);
    setStatus(stream ? 'Sending prompt (stream)…' : 'Sending prompt (all layers)…');
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setStatus('Reconnecting…');
      connect();
      setTimeout(function () {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ cmd: 'prompt', prompt: prompt, max_tokens: maxTokens, stream: stream }));
        } else {
          setStatus('Not connected. Start the server (uvicorn viz_server:app).');
        }
      }, 500);
      return;
    }
    ws.send(JSON.stringify({ cmd: 'prompt', prompt: prompt, max_tokens: maxTokens, stream: stream }));
  }

  function animate() {
    rafId = requestAnimationFrame(animate);
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
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

  function start() {
    initThree();
    connect();
    animate();
  }
  if (document.readyState === 'complete') {
    start();
  } else {
    window.addEventListener('load', start);
  }
})();
