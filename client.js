export async function render({ model, el }) {
  el.innerHTML = "";

  const endpoint = model.get("endpoint");

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

  const messageEl = document.createElement("p");
  messageEl.textContent = "Loading map...";
  el.appendChild(messageEl);

  const canvasContainer = document.createElement("div");
  canvasContainer.style.border = "2px solid #444";
  canvasContainer.style.borderRadius = "8px";
  canvasContainer.style.boxShadow = "0 2px 6px rgba(0,0,0,0.1)";
  el.appendChild(canvasContainer);

  const SVG_W = 800;
  const SVG_H = 600;
  canvasContainer.style.width = SVG_W + "px";
  canvasContainer.style.height = SVG_H + "px";

  // Data display
  const dataPre = document.createElement("pre");
  dataPre.style.maxHeight = "180px";
  dataPre.style.overflow = "auto";
  dataPre.style.background = "#fff";
  dataPre.style.width = SVG_W + "px";
  dataPre.style.padding = "6px";
  dataPre.style.border = "1px solid #ccc";
  dataPre.style.borderRadius = "6px";
  el.appendChild(dataPre);

  const controls = document.createElement("div");
  controls.style.display = "flex";
  controls.style.gap = "0.5em";
  el.appendChild(controls);

  function makeButton(text, onClick) {
    const b = document.createElement("button");
    b.textContent = text;
    b.style.padding = "6px 10px";
    b.onclick = onClick;
    return b;
  }

  function makeFormButton(text, onClick, fields) {
    const form = document.createElement("form");

    // When the form is submitted, collect the numeric inputs and pass
    // them as an object to the provided onClick handler.
    form.onsubmit = (e) => {
      e.preventDefault();
      const values = {};
      const inputs = form.querySelectorAll("input");
      inputs.forEach((input, idx) => {
        const name = input.name || input.dataset.name || `field${idx}`;
        let val = input.value;
        // Parse numeric inputs to numbers where applicable
        if (input.type === "number") {
          // use parseFloat to allow non-integer steps
          const parsed = parseFloat(val);
          val = Number.isNaN(parsed) ? null : parsed;
        }
        values[name] = val;
      });
      // Call handler with collected values
      onClick(values);
    };

    const b = document.createElement("button");
    b.textContent = text;
    b.style.padding = "6px 10px";
    b.type = "submit"; // ensure it triggers the form's submit handler
    form.appendChild(b);

    fields.forEach((field, idx) => {
      const input = document.createElement("input");
      input.type = "number";
      input.placeholder = field.placeholder;
      input.value = field.placeholder;
      if (field.step) {
        input.step = field.step;
      }
      const name = field.name || field.label || `field${idx}`;
      input.name = name;
      // Add a label for each input
      const label = document.createElement("label");
      label.textContent = field.label;
      label.style.marginRight = "6px";
      form.appendChild(label);
      form.appendChild(input);
    });

    return form;
  }

  const up = makeButton("↑", () => sendMove(0, -1));
  const down = makeButton("↓", () => sendMove(0, 1));
  const left = makeButton("←", () => sendMove(-1, 0));
  const right = makeButton("→", () => sendMove(1, 0));
  const sensorBtn = makeFormButton("Sensor", sendSensor, [
    { label: "num_beams", placeholder: 60 },
    { label: "max_range", placeholder: 1000.0, step: "any" },
    { label: "noise_std", placeholder: 0, step: "any" },
    { label: "fov", placeholder: 6.28, step: "any" }
  ]);
  const stepBtn = makeButton("Step", sendStep);

  controls.append(left, up, down, right, sensorBtn, stepBtn);

  let PPM = 10;
  let two = null;
  let playerCircle = null;
  let sensorDots = [];

  async function fetchEnv() {
    try {
      const res = await fetch(`http://${endpoint}/robot_scenario_env`);
      const data = await res.json();
      drawMap(data.map);
      drawPlayer(data.player);
      messageEl.textContent = "Map loaded.";
    } catch (err) {
      messageEl.textContent = "Failed to load environment.";
      console.error(err);
    }
  }

  function ensureTwo() {
    if (two) return two;
    two = new Two({ width: SVG_W, height: SVG_H }).appendTo(canvasContainer);
    // light background rectangle so canvas looks similar to previous SVG
    const bg = two.makeRectangle(SVG_W / 2, SVG_H / 2, SVG_W, SVG_H);
    bg.fill = "#fafafa";
    bg.noStroke();
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
      }
    });

    t.update();
  }

  function drawPlayer(player) {
    if (!player) return;
    const pos = player.position;
    let px = 0,
      py = 0;
    if (Array.isArray(pos)) {
      px = pos[0] * PPM;
      py = pos[1] * PPM;
    } else if (pos && typeof pos.x === "number") {
      px = pos.x * PPM;
      py = pos.y * PPM;
    } else if (player.position && player.position.x !== undefined) {
      px = player.position.x * PPM;
      py = player.position.y * PPM;
    } else {
      // unknown format; bail
      return;
    }

    const t = ensureTwo();
    if (!playerCircle) {
      playerCircle = t.makeCircle(px, py, 10); // player_radius_px
      playerCircle.fill = "#e44";
      playerCircle.noStroke();
    } else {
      playerCircle.translation.set(px, py);
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
      const dot = two.makeCircle(cx, cy, 2);
      dot.fill = "#08f";
      dot.noStroke();
      sensorDots.push(dot);
    });
    two.update();
  }

  async function sendMove(x, y, rotation = 0) {
    try {
      await fetch(`http://${endpoint}/robot_scenario_move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ x, y, rotation }),
      });
      messageEl.textContent = `Moved (${x}, ${y})`;
    } catch (err) {
      messageEl.textContent = `Move failed: ${err.message}`;
    }
  }

  async function sendSensor(params = {}) {
    try {
      const res = await fetch(`http://${endpoint}/robot_scenario_sensor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params || {}),
      });
      const data = await res.json();
      // server returns { "hit_points": [[x,y], ...] }
      const hits = data.hit_points || data.hitPoints || [];
      drawSensorHits(hits);
      dataPre.textContent = JSON.stringify(data, null, 2);
      messageEl.textContent = "Sensor data received.";
    } catch (err) {
      messageEl.textContent = `Sensor failed: ${err.message}`;
    }
  }

  async function sendStep() {
    try {
      const res = await fetch(`http://${endpoint}/robot_scenario_step`, {
        method: "GET",
      });
      const data = await res.json();
      const player = data.player || data;
      drawPlayer(player);
      dataPre.textContent = JSON.stringify(player, null, 2);
      messageEl.textContent = "Stepped.";
    } catch (err) {
      messageEl.textContent = "Step failed.";
      console.error(err);
    }
  }

  await fetchEnv();
}
