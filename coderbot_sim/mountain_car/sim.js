export default {
  async render({ model, el }) {
    const [width, height] = model.get("_viewport_size") || [600, 400];
    const container = document.createElement("div");
    container.style.position = "relative";
    el.appendChild(container);

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    container.appendChild(canvas);
    const ctx = canvas.getContext("2d");

    const sim_state = model.get("sim_state") || {};
    const minPosition = -1.2;
    const maxPosition = 0.6;
    const maxSpeed = 0.07;
    const force = 0.001;
    const gravity = 0.0025;
    let position = sim_state.position || -0.5;
    let velocity = sim_state.velocity || 0.0;

    if (model.get("_manual_control")) {
      const controls = document.createElement("div");
      controls.className = "controls";
      controls.innerHTML = `
        <button id="left">←</button>
        <button id="right">→</button>
      `;

      const controlsObj = { action: 1 }; // 0=left, 1=idle, 2=right
      container.appendChild(controls);

      controls.addEventListener("mousedown", (e) => {
        const id = e.target.id;
        if (id === "left") {
          controlsObj.action = 0;
        } else if (id === "right") {
          controlsObj.action = 2;
        }
      });

      controls.addEventListener("mouseup", (e) => {
        const id = e.target.id;
        if (id === "left" || id === "right") {
          controlsObj.action = 1;
        }
      });

      let lastTime = new Date();
      const step = () => {
        let ms = new Date();
        if (ms - lastTime < 20) { 
          requestAnimationFrame(step);
          return;
        }
        lastTime = ms;

        const action = controlsObj.action; // 0=left, 1=idle, 2=right
        const forceTerm = (action - 1) * force;
        velocity += forceTerm + Math.cos(3 * position) * -gravity;
        velocity = Math.max(Math.min(velocity, maxSpeed), -maxSpeed);
        position += velocity;
        position = Math.max(Math.min(position, maxPosition), minPosition);
        if (position === minPosition && velocity < 0) velocity = 0;
        requestAnimationFrame(step);
      };

      step();
    }

    const goalPosition = 0.5;
    const worldWidth = maxPosition - minPosition;
    const scale = width / worldWidth;
    const heightFn = (x) => Math.sin(3 * x) * 0.45 + 0.55;

    const terrain = [];
    for (let i = 0; i < 200; i++) {
      const t = i / 199;
      const xWorld = minPosition + t * worldWidth;
      const yWorld = heightFn(xWorld);
      terrain.push({
        x: (xWorld - minPosition) * scale,
        y: height - yWorld * scale
      });
    }

    const carWidth = 40;
    const carHeight = 20;
    const clearance = 10;

    model.on("change:sim_state", () => {
      const newState = model.get("sim_state") || {};
      position = newState.position;
      velocity = newState.velocity;
    });

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#eeeeee";
      ctx.beginPath();
      ctx.moveTo(terrain[0].x, terrain[0].y);
      for (const p of terrain) ctx.lineTo(p.x, p.y);
      ctx.lineTo(width, height);
      ctx.lineTo(0, height);
      ctx.closePath();
      ctx.fill();

      ctx.strokeStyle = "#444";
      ctx.lineWidth = 2;
      ctx.stroke();
      const xScreen = (position - minPosition) * scale;
      const yScreen = height - heightFn(position) * scale - clearance;
      const slope = Math.cos(3 * position);
      const angle = Math.atan(slope);

      ctx.save();
      ctx.translate(xScreen, yScreen);
      ctx.rotate(-angle);

      ctx.fillStyle = "#000";
      ctx.fillRect(-carWidth / 2, -carHeight, carWidth, carHeight);

      ctx.fillStyle = "#777";
      const wheelR = carHeight * 0.4;
      ctx.beginPath();
      ctx.arc(carWidth / 3, 0, wheelR, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(-carWidth / 3, 0, wheelR, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      const fx = (goalPosition - minPosition) * scale;
      const fy = height - heightFn(goalPosition) * scale;
      ctx.strokeStyle = "#000";
      ctx.beginPath();
      ctx.moveTo(fx, fy);
      ctx.lineTo(fx, fy - 40);
      ctx.stroke();

      ctx.fillStyle = "#ff0";
      ctx.beginPath();
      ctx.moveTo(fx, fy - 40);
      ctx.lineTo(fx + 25, fy - 35);
      ctx.lineTo(fx, fy - 30);
      ctx.closePath();
      ctx.fill();

      requestAnimationFrame(draw);
    };

    draw();

    model.set("_view_ready", true);
    model.save_changes();
  }
};
