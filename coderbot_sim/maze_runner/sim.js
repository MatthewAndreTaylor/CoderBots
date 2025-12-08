let simState = {};

export default {
  initialize({ model }) {
    model.on("change:sim_state", () => {
      simState = model.get("sim_state") || {};
    });
  },

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

    function draw() {
      const state = simState || {};
      const maze = state.maze || [];
      const agent = state.agent || { r: 1, c: 1 };
      const goal = state.goal || { r: maze.length - 2, c: (maze[0] || []).length - 2 };
      const rows = state.rows || maze.length || 1;
      const cols = state.cols || (maze[0] || []).length || 1;

      ctx.clearRect(0, 0, width, height);

      // Background
      ctx.fillStyle = "#111827";
      ctx.fillRect(0, 0, width, height);

      const cellW = width / cols;
      const cellH = height / rows;

      // Draw maze walls
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          if ((maze[r] && maze[r][c]) === 1) {
            ctx.fillStyle = "#4B5563"; // wall
            ctx.fillRect(c * cellW, r * cellH, cellW, cellH);
          }
        }
      }

      // Goal
      ctx.fillStyle = "#22C55E";
      ctx.fillRect(
        goal.c * cellW + cellW * 0.15,
        goal.r * cellH + cellH * 0.15,
        cellW * 0.7,
        cellH * 0.7
      );

      // Agent
      ctx.fillStyle = "#FACC15";
      const ax = agent.c * cellW + cellW * 0.15;
      const ay = agent.r * cellH + cellH * 0.15;
      ctx.beginPath();
      ctx.arc(
        ax + cellW * 0.35,
        ay + cellH * 0.35,
        Math.min(cellW, cellH) * 0.3,
        0,
        Math.PI * 2
      );
      ctx.fill();

      // Steps text
      ctx.fillStyle = "#FFFFFF";
      ctx.font = "16px Arial";
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText(`Steps: ${state.steps ?? 0}`, 10, 10);

      requestAnimationFrame(draw);
    }

    draw();

    model.set("_view_ready", true);
    model.save_changes();
  }
};
