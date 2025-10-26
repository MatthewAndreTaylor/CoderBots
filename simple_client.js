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
  let projectileCircles = [];
  let twoUpdateBound = false;

  function ensureTwo() {
    if (two) return two;
    two = new Two({ width: SVG_W, height: SVG_H }).appendTo(canvasContainer);
    const bg = two.makeRectangle(SVG_W / 2, SVG_H / 2, SVG_W, SVG_H);
    bg.fill = "#fafafa";
    bg.noStroke();
    if (typeof two.play === "function") {
      try { two.play(); } catch (e) {}
    }
    two.update();
    return two;
  }

  function drawMap(map) {
    if (!map) return;
    PPM = map.ppm;
    const t = ensureTwo();
    t.clear();
    const bg = t.makeRectangle(SVG_W / 2, SVG_H / 2, SVG_W, SVG_H);
    bg.fill = "#fafafa";
    bg.noStroke();

    map.shapes.forEach((shape) => {
      if (shape.type === "rectangle") {
        const rect = t.makeRectangle(shape.x, shape.y, shape.width, shape.height);
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
        const goal = t.makeRectangle(shape.x, shape.y, shape.width, shape.height);
        goal.fill = "#0f0";
        goal.stroke = "#333";
        goal.linewidth = 1;
      }
    });

    two.update();
  }

  function drawPlayer(player) {
    if (!player) return;

    const pos = player.pos;
    let targetX = Array.isArray(pos) ? pos[0] * PPM : pos.x * PPM;
    let targetY = Array.isArray(pos) ? pos[1] * PPM : pos.y * PPM;

    const t = ensureTwo();

    if (!playerCircle) {
      playerCircle = t.makeCircle(targetX, targetY, 10);
      playerCircle.fill = "#e44";
      playerCircle.noStroke();
      playerCircle.current = { x: targetX, y: targetY };
    } else {
      playerCircle.target = { x: targetX, y: targetY };
    }

    if (!playerCircle.updateBound) {
      playerCircle.updateBound = true;
      t.bind("update", function (frameCount, timeDelta) {
        if (!playerCircle || !playerCircle.target) return;
        const dt = typeof timeDelta === "number" ? timeDelta / 1000 : 0.016;
        const speed = 2.0;
        const lerp = (a, b, f) => a + (b - a) * f;
        const alpha = Math.min(speed * dt, 1.0);

        playerCircle.current.x = lerp(playerCircle.current.x, playerCircle.target.x, alpha);
        playerCircle.current.y = lerp(playerCircle.current.y, playerCircle.target.y, alpha);

        playerCircle.translation.set(playerCircle.current.x, playerCircle.current.y);
      });
    }

    two.update();
  }

  function drawSensorHits(points) {
    if (!two) ensureTwo();
    sensorDots.forEach((d) => two.remove(d));
    sensorDots = [];

    if (!Array.isArray(points)) return;
    points.forEach((pt) => {
      let x = Array.isArray(pt) ? pt[0] : pt.x;
      let y = Array.isArray(pt) ? pt[1] : pt.y;
      const cx = x * PPM;
      const cy = y * PPM;
      createDot(cx, cy);
    });

    if (!twoUpdateBound) {
      two.bind("update", function (frameCount, timeDelta) {
        const dt = typeof timeDelta === "number" ? timeDelta / 1000 : 0.016;
        sensorDots.forEach((dot) => {
          if (dot.opacity > 0) {
            dot.elapsed += dt;
            dot.opacity = Math.max(1 - dot.elapsed / dot.fadeDuration, 0);
          }
        });
      });
      twoUpdateBound = true;
    }

    two.update();
  }

  function createDot(cx, cy) {
    const dot = two.makeCircle(cx, cy, 3);
    dot.fill = "#ff00ffff";
    dot.noStroke();
    dot.opacity = 1;
    dot.fadeDuration = 0.5;
    dot.elapsed = 0;
    sensorDots.push(dot);
  }

  function drawProjectiles(projectiles) {
    if (!two) ensureTwo();
    projectileCircles.forEach((d) => {
      setTimeout(() => two.remove(d), 100);
    });
    projectileCircles = [];

    if (!Array.isArray(projectiles)) return;
    projectiles.forEach((proj) => {
      const x = Array.isArray(proj) ? proj[0] * PPM : proj.x * PPM;
      const y = Array.isArray(proj) ? proj[1] * PPM : proj.y * PPM;
      const circle = two.makeCircle(x, y, 4);
      circle.fill = "#00f";
      circle.noStroke();
      projectileCircles.push(circle);
    });

    two.update();
  }

  model.on("change:result", async () => {
    const newValue = model.get("result");

    if (newValue.type === "sensor") {
      const hits = newValue.data?.hit_points || [];
      drawSensorHits(hits);
    } else if (newValue.type === "step") {
      drawPlayer(newValue.data.robot);
      drawProjectiles(newValue.data.projectiles || []);
    } else if (newValue.type === "fire") {
      // Optional: instant projectile flash on fire
      drawProjectiles(newValue.data ? [newValue.data.pos] : []);
    } else {
      console.warn("Unknown result type:", newValue.type);
    }
  });

  drawMap(model.get("env_map"));
  drawPlayer(model.get("player_data"));
}
