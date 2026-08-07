export default {
  async render({ model, el }) {
    const [width, height] = model.get("_viewport_size") || [800, 600];

    const container = document.createElement("div");
    container.style.position = "relative";
    container.style.width = width + "px";
    container.style.height = height + "px";
    el.appendChild(container);

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    container.appendChild(canvas);
    const ctx = canvas.getContext("2d");

    // Current sim state
    let simState = model.get("sim_state") || {};
    let frogPos = simState.frog_pos || [0, 0];  // grid coords
    let score = simState.score || 0;
    let carRects = model.get("car_positions") || []; // pixel absolute coords

    // Watch sim_state and car_positions
    model.on("change:sim_state", () => {
      simState = model.get("sim_state") || {};
      frogPos = simState.frog_pos || frogPos;
      score = simState.score ?? score;
    });

    model.on("change:car_positions", () => {
      carRects = model.get("car_positions") || carRects;
    });

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Background
      ctx.fillStyle = "#101010";
      ctx.fillRect(0, 0, width, height);

      // The frog is still grid-based
      const grid = simState.grid || [];
      const rows = grid.length || 15;
      const cols = (grid[0] && grid[0].length) || 20;

      const cellW = width / cols;
      const cellH = height / rows;

      // Safe zones
      ctx.fillStyle = "#000050";
      ctx.fillRect(0, 0, width, cellH);
      ctx.fillStyle = "#004000";
      ctx.fillRect(0, (rows - 1) * cellH, width, cellH);

      // Road tint
      for (let r = 1; r < rows - 1; r++) {
        ctx.fillStyle = "#202020";
        ctx.fillRect(0, r * cellH, width, cellH);
      }

      ctx.fillStyle = "#B43232";
      for (let i = 0; i < carRects.length; i += 4) {
          ctx.fillRect(carRects[i], carRects[i + 1], carRects[i + 2], carRects[i + 3]);
      }

      const [frogCol, frogRow] = frogPos;
      const fx = frogCol * cellW;
      const fy = frogRow * cellH;
      const radius = Math.min(cellW, cellH) * 0.4;

      ctx.fillStyle = "#32DC32";
      ctx.beginPath();
      ctx.arc(fx + cellW / 2, fy + cellH / 2, radius, 0, Math.PI * 2);
      ctx.fill();

      // Grid lines
      ctx.strokeStyle = "#282828";
      ctx.lineWidth = 1;

      for (let r = 0; r <= rows; r++) {
        const y = r * cellH;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      for (let c = 0; c <= cols; c++) {
        const x = c * cellW;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }

      // Score
      ctx.fillStyle = "#FFFFFF";
      ctx.font = "16px Arial";
      ctx.textBaseline = "top";
      ctx.fillText(`Score: ${score.toFixed(2)}`, 10, 10);

      requestAnimationFrame(draw);
    };

    draw();

    model.set("_view_ready", true);
    model.save_changes();
  },
};
