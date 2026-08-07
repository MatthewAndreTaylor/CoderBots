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
    const PIPE_GAP = 200;
    const GROUND_HEIGHT = 80;

    // Scale world to canvas (in case viewport differs from 800×600)
    const scaleX = width / WORLD_WIDTH;
    const scaleY = height / WORLD_HEIGHT;

    function draw() {
      const state = simState || {};
      const birdY = state.bird_y ?? WORLD_HEIGHT / 2;
      const pipes_x = state.pipes_x || [];
      const pipes_y = state.pipes_y || [];
      const done = state.done || false;

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
      ctx.lineWidth = 1;

      if (!done) {
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
      }

      // Pipes
      ctx.fillStyle = "#228B22";
      ctx.strokeStyle = "#4a8d34";
      ctx.lineWidth = 2 * ((scaleX + scaleY) / 2);

      for (let i = 0; i < pipes_x.length; i++) {
        const pipeX = pipes_x[i];
        const pipeY = pipes_y[i];

        const pw = PIPE_WIDTH * scaleX;
        const ux = pipeX * scaleX;
        const uy = 0; // Upper pipe starts at top of screen
        const uh = pipeY * scaleY; // Upper pipe height extends down to pipeY
        const lx = pipeX * scaleX;
        const ly = (pipeY + PIPE_GAP) * scaleY; // Lower pipe starts after gap
        const lh = (WORLD_HEIGHT - (pipeY + PIPE_GAP)) * scaleY; // Lower pipe extends to bottom

        // Upper pipe
        ctx.beginPath();
        ctx.rect(ux, uy, pw, uh);
        ctx.fill();
        ctx.stroke();

        // Lower pipe
        ctx.beginPath();
        ctx.rect(lx, ly, pw, lh);
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
