export async function render({ model, el }) {
  el.innerHTML = "";

  await new Promise((resolve) => {
    if (window.Two) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src =
      "https://cdnjs.cloudflare.com/ajax/libs/two.js/0.8.12/two.min.js";
    script.onload = resolve;
    document.head.appendChild(script);
  });

  el.style.display = "flex";
  el.style.flexDirection = "column";
  el.style.alignItems = "center";
  el.style.gap = "1em";

  const title = document.createElement("h3");
  title.textContent = model.get("title");
  el.appendChild(title);

  const canvasContainer = document.createElement("div");
  canvasContainer.style.border = "2px solid #444";
  canvasContainer.style.borderRadius = "8px";
  canvasContainer.style.boxShadow = "0 2px 6px rgba(0,0,0,0.1)";
  el.appendChild(canvasContainer);

  const SVG_W = 800;
  const SVG_H = 600;
  canvasContainer.style.width = SVG_W + "px";
  canvasContainer.style.height = SVG_H + "px";

  let PPM = 10;
  let two = null;
  let playerCircle = null;
  let sensorDots = [];
  let twoUpdateBound = false;

  function ensureTwo() {
    if (two) return two;
    two = new Two({ width: SVG_W, height: SVG_H }).appendTo(canvasContainer);
    // light background rectangle so canvas looks similar to previous SVG
    const bg = two.makeRectangle(SVG_W / 2, SVG_H / 2, SVG_W, SVG_H);
    bg.fill = "#fafafa";
    bg.noStroke();
    // Start the animation loop so any bound update handlers run
    if (typeof two.play === "function") {
      try {
        two.play();
      } catch (e) {
        // ignore if play is unavailable for some reason
      }
    }
    two.update();
    return two;
  }

  function drawMap(map) {
    if (!map) return;
    // Shapes in the map JSON are in pixels. ppm is pixels-per-meter and is
    // used to convert physics (meters) -> pixels for the player only.
    PPM = map.ppm;

    const t = ensureTwo();
    // clear scene and add background
    t.clear();
    const bg = t.makeRectangle(SVG_W / 2, SVG_H / 2, SVG_W, SVG_H);
    bg.fill = "#fafafa";
    bg.noStroke();

    map.shapes.forEach((shape) => {
      if (shape.type === "rectangle") {
        // map rectangle x,y are center coords in pixels
        const rx = shape.x;
        const ry = shape.y;
        const rw = shape.width;
        const rh = shape.height;
        const rect = t.makeRectangle(rx, ry, rw, rh);
        rect.fill = "#ccc";
        rect.stroke = "#333";
        rect.linewidth = 1;
      } else if (shape.type === "triangle" || shape.type === "polygon") {
        const anchors = shape.vertices.map((v) => new Two.Anchor(v[0], v[1]));
        const tri = t.makePath(anchors, true);
        tri.fill = "#ddd";
        tri.stroke = "#333";
        tri.linewidth = 1;
      } else if (shape.type === "goal") {
        const gx = shape.x;
        const gy = shape.y;
        const gw = shape.width;
        const gh = shape.height;
        const goal = t.makeRectangle(gx, gy, gw, gh);
        goal.fill = "#0f0";
        goal.stroke = "#333";
        goal.linewidth = 1;
      }
    });

    t.update();
  }

  function drawPlayer(player) {
  if (!player) return;

  const pos = player.pos;
  let targetX = 0, targetY = 0;
  if (Array.isArray(pos)) {
    targetX = pos[0] * PPM;
    targetY = pos[1] * PPM;
  } else if (pos && typeof pos.x === "number") {
    targetX = pos.x * PPM;
    targetY = pos.y * PPM;
  } else {
    return; // unknown format
  }

  const t = ensureTwo();

  if (!playerCircle) {
    // create player circle
    playerCircle = t.makeCircle(targetX, targetY, 10);
    playerCircle.fill = "#e44";
    playerCircle.noStroke();
    playerCircle.current = { x: targetX, y: targetY };
  } else {
    // set the target for lerping
    playerCircle.target = { x: targetX, y: targetY };
  }

  // only bind the update handler once
  if (!playerCircle.updateBound) {
    playerCircle.updateBound = true;

    t.bind("update", function (frameCount, timeDelta) {
      if (!playerCircle || !playerCircle.target) return;

      const dt = typeof timeDelta === "number" ? timeDelta / 1000 : 0.016;
      const speed = 2.0; // higher = faster interpolation

      const cx = playerCircle.current.x;
      const cy = playerCircle.current.y;
      const tx = playerCircle.target.x;
      const ty = playerCircle.target.y;

      // linear interpolation
      const lerp = (a, b, f) => a + (b - a) * f;
      const alpha = Math.min(speed * dt, 1.0);

      playerCircle.current.x = lerp(cx, tx, alpha);
      playerCircle.current.y = lerp(cy, ty, alpha);

      playerCircle.translation.set(playerCircle.current.x, playerCircle.current.y);
    });
  }

  t.update();
}

  function drawSensorHits(points) {
    // points: array of [x,y] in meters or objects {x,y}. Convert by PPM.
    if (!two) ensureTwo();
    // remove previous dots
    try {
      sensorDots.forEach((d) => two.remove(d));
    } catch (e) {
      // ignore if removal fails
    }
    sensorDots = [];
    if (!Array.isArray(points)) return;
    points.forEach((pt) => {
      let x = 0,
        y = 0;
      if (Array.isArray(pt)) {
        x = pt[0];
        y = pt[1];
      } else if (pt && typeof pt.x === "number") {
        x = pt.x;
        y = pt.y;
      } else {
        return;
      }
      const cx = x * PPM;
      const cy = y * PPM;
      createDot(cx, cy);
    });

    // Bind the update handler only once so we don't accumulate handlers on
    // repeated sensor calls. This will progressively fade the dots.
    if (!twoUpdateBound) {
      two.bind("update", function (frameCount, timeDelta) {
        // timeDelta may be provided in ms depending on Two.js; convert to seconds
        const dt = typeof timeDelta === "number" ? timeDelta / 1000 : 0.016;
        for (const dot of sensorDots) {
          if (dot.opacity > 0) {
            dot.elapsed += dt;
            dot.opacity = Math.max(1 - dot.elapsed / dot.fadeDuration, 0);
          }
        }
      });
      twoUpdateBound = true;
    }

    // Ensure the scene renders immediately with the new dots
    two.update();
  }

  function createDot(cx, cy) {
    const dot = two.makeCircle(cx, cy, 3);
    dot.fill = "#ff00ffff";
    dot.noStroke();
    dot.opacity = 1;
    dot.fadeDuration = 0.5; // seconds
    dot.elapsed = 0;
    sensorDots.push(dot);
  }

  model.on("change:result", async () => {
    const newValue = model.get("result");

    if (newValue.type === "sensor") {
      const hits = newValue.data?.hit_points || [];
      drawSensorHits(hits);
      dataPre.textContent = JSON.stringify(newValue.data, null, 2);
    } else if (newValue.type === "step") {
      drawPlayer(newValue.data);
      dataPre.textContent = JSON.stringify(newValue.data, null, 2);
    } else {
      console.warn("Unknown result type:", newValue.type);
    }
  });

  drawMap(model.get("env_map"));
  drawPlayer(model.get("player_data"));
}
