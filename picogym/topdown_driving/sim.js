export default {
  async render({ model, el }) {
    const [CANVAS_W, CANVAS_H] = model.get("_viewport_size") || [800, 600];

    const container = document.createElement("div");
    container.style.position = "relative";
    el.appendChild(container);

    const canvas = document.createElement("canvas");
    canvas.width = CANVAS_W;
    canvas.height = CANVAS_H;
    container.appendChild(canvas);

    const ctx = canvas.getContext("2d");

    const walls = model.get("wall_positions") || [];
    let sim_state = model.get("sim_state") || {};

    model.on("change:sim_state", () => {
      sim_state = model.get("sim_state") || {};
    });
    const xs = [];
    const ys = [];

    for (const [x, y, w, h] of walls) {
      const r = Math.hypot(w, h) * 0.5;
      xs.push(x - r, x + r);
      ys.push(y - r, y + r);
    }

    const min_x = Math.min(...xs);
    const max_x = Math.max(...xs);
    const min_y = Math.min(...ys);
    const max_y = Math.max(...ys);

    const scale = Math.min(
      (CANVAS_W - 2) / (max_x - min_x),
      (CANVAS_H - 2) / (max_y - min_y)
    );

    const offset_x = -min_x * scale;
    const offset_y = max_y * scale;

    const worldToScreen = (x, y) => {
      return [
        x * scale + offset_x,
        -y * scale + offset_y,
      ];
    };

    const drawWalls = () => {
      ctx.fillStyle = "#cccccc";
      ctx.strokeStyle = "#000";

      for (const [x, y, w, h, rot] of walls) {
        const [sx, sy] = worldToScreen(x, y);

        ctx.save();
        ctx.translate(sx, sy);
        const rad = (rot * Math.PI) / 180;
        ctx.rotate(-rad);

        ctx.beginPath();
        ctx.rect(
          (-w * scale) / 2,
          (-h * scale) / 2,
          w * scale,
          h * scale
        );
        ctx.fill();
        ctx.stroke();

        ctx.restore();
      }
    };

    const drawCars = () => {
      if (!sim_state.x) return;

      const xs = sim_state.x;
      const ys = sim_state.y;
      const angles = sim_state.angle;
      const CAR_LENGTH = 1.0;
      const CAR_WIDTH = 0.5;
      const COLORS = [
        "red",
        "orange",
        "yellow",
        "green",
        "blue",
        "indigo",
        "violet",
      ];

      for (let i = 0; i < xs.length; i++) {
        const [sx, sy] = worldToScreen(xs[i], ys[i]);

        ctx.save();
        ctx.translate(sx, sy);
        ctx.rotate(angles[i]);

        ctx.fillStyle = COLORS[i % COLORS.length];
        ctx.strokeStyle = "black";

        ctx.beginPath();
        ctx.rect(
          (-CAR_LENGTH * scale) / 2,
          (-CAR_WIDTH * scale) / 2,
          CAR_LENGTH * scale,
          CAR_WIDTH * scale
        );
        ctx.fill();
        ctx.stroke();

        ctx.restore();
      }
    };

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      drawWalls();
      drawCars();

      requestAnimationFrame(draw);
    };

    draw();

    model.set("_view_ready", true);
    model.save_changes();
  }
};
