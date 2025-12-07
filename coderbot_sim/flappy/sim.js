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

    const WORLD_WIDTH = 800;
    const WORLD_HEIGHT = 600;
    const BIRD_X = 200;
    const BIRD_SIZE = 35;
    const PIPE_WIDTH = 80;
    const PIPE_HEIGHT = 320;
    const GROUND_HEIGHT = 80;

    // Scale world to canvas (in case viewport differs from 800×600)
    const scaleX = width / WORLD_WIDTH;
    const scaleY = height / WORLD_HEIGHT;

    function draw() {
      const state = simState || {};
      const birdY = state.bird_y ?? WORLD_HEIGHT / 2;
      const pipes = state.pipes || [];

      ctx.clearRect(0, 0, width, height);

      // Background sky
      ctx.fillStyle = "#70C5CE";
      ctx.fillRect(0, 0, width, height);

      // Ground
      const groundH = GROUND_HEIGHT * scaleY;
      ctx.fillStyle = "#DED895";
      ctx.fillRect(0, height - groundH, width, groundH);

      // Bird
      const birdScreenX = BIRD_X * scaleX;
      const birdScreenY = birdY * scaleY;
      const birdSizeX = BIRD_SIZE * scaleX;
      const birdSizeY = BIRD_SIZE * scaleY;

      ctx.fillStyle = "#FFD700";
      ctx.strokeStyle = "#000000";
      ctx.lineWidth = 2 * ((scaleX + scaleY) / 2);

      ctx.beginPath();
      ctx.ellipse(
        birdScreenX + birdSizeX / 2,
        birdScreenY + birdSizeY / 2,
        birdSizeX / 2,
        birdSizeY / 2,
        0,
        0,
        Math.PI * 2
      );
      ctx.fill();
      ctx.stroke();

      // Pipes
      ctx.fillStyle = "#7EC850";
      ctx.strokeStyle = "#4a8d34";
      ctx.lineWidth = 2 * ((scaleX + scaleY) / 2);

      for (const pair of pipes) {
        const upper = pair[0];
        const lower = pair[1];

        const ux = (upper.x || 0) * scaleX;
        const uy = (upper.y || 0) * scaleY;
        const lx = (lower.x || 0) * scaleX;
        const ly = (lower.y || 0) * scaleY;

        const pw = PIPE_WIDTH * scaleX;
        const ph = PIPE_HEIGHT * scaleY;

        // Upper pipe
        ctx.beginPath();
        ctx.rect(ux, uy, pw, ph);
        ctx.fill();
        ctx.stroke();

        // Lower pipe
        ctx.beginPath();
        ctx.rect(lx, ly, pw, ph);
        ctx.fill();
        ctx.stroke();
      }

      requestAnimationFrame(draw);
    }

    draw();

    model.set("_view_ready", true);
    model.save_changes();
  }
};
