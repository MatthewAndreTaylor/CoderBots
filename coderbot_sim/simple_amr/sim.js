const keys = { forward: false, backward: false, left: false, right: false };

class ray {
  constructor(start, end) {
    this.start = start;
    this.end = end;
  }

  yValueAt(x) {
    return this.offsetY + this.slope * x;
  }
  xValueAt(y) {
    return (y - this.offsetY) / this.slope;
  }

  pointInBounds(point) {
    var minX = Math.min(this.start.x, this.end.x);
    var maxX = Math.max(this.start.x, this.end.x);
    var minY = Math.min(this.start.y, this.end.y);
    var maxY = Math.max(this.start.y, this.end.y);
    return (
      point.x >= minX && point.x <= maxX && point.y >= minY && point.y <= maxY
    );
  }

  get slope() {
    var dif = this.end.minus(this.start);
    return dif.y / dif.x;
  }
  get offsetY() {
    return this.start.y - this.slope * this.start.x;
  }
  get isHorizontal() {
    return compareNum(this.start.y, this.end.y);
  }
  get isVertical() {
    return compareNum(this.start.x, this.end.x);
  }

  static intersect(rayA, rayB) {
    if (rayA.isVertical && rayB.isVertical) return null;
    if (rayA.isVertical)
      return new vec2(rayA.start.x, rayB.yValueAt(rayA.start.x));
    if (rayB.isVertical)
      return new vec2(rayB.start.x, rayA.yValueAt(rayB.start.x));
    if (compareNum(rayA.slope, rayB.slope)) return null;
    if (rayA.isHorizontal)
      return new vec2(rayB.xValueAt(rayA.start.y), rayA.start.y);
    if (rayB.isHorizontal)
      return new vec2(rayA.xValueAt(rayB.start.y), rayB.start.y);
    var x = (rayB.offsetY - rayA.offsetY) / (rayA.slope - rayB.slope);
    return new vec2(x, rayA.yValueAt(x));
  }
  static collisionPoint(rayA, rayB) {
    var intersection = ray.intersect(rayA, rayB);
    if (!intersection) return null;
    if (!rayA.pointInBounds(intersection)) return null;
    if (!rayB.pointInBounds(intersection)) return null;
    return intersection;
  }
  static bodyEdges(body) {
    var r = [];
    for (var i = body.parts.length - 1; i >= 0; i--) {
      for (var k = body.parts[i].vertices.length - 1; k >= 0; k--) {
        var k2 = k + 1;
        if (k2 >= body.parts[i].vertices.length) k2 = 0;
        var tray = new ray(
          vec2.fromOther(body.parts[i].vertices[k]),
          vec2.fromOther(body.parts[i].vertices[k2])
        );
        tray.verts = [body.parts[i].vertices[k], body.parts[i].vertices[k2]];

        r.push(tray);
      }
    }
    return r;
  }
  static bodyCollisions(rayA, body) {
    const r = [];
    const edges = ray.bodyEdges(body);
    for (let i = edges.length - 1; i >= 0; i--) {
      const colpoint = ray.collisionPoint(rayA, edges[i]);
      if (!colpoint) continue;
      r.push({ body: body, point: colpoint });
    }

    return r;
  }
}

function compareNum(a, b, eps = 0.00001) {
  return Math.abs(b - a) <= eps;
}

class vec2 {
  constructor(x = 0, y = x) {
    this.x = x;
    this.y = y;
  }
  normalized(magnitude = 1) {
    return this.multiply(magnitude / this.distance());
  }
  multiply(factor) {
    return new vec2(this.x * factor, this.y * factor);
  }
  plus(vec) {
    return new vec2(this.x + vec.x, this.y + vec.y);
  }
  minus(vec) {
    return this.plus(vec.multiply(-1));
  }
  rotate(rot) {
    var ang = this.direction;
    var mag = this.distance();
    ang += rot;
    return vec2.fromAng(ang, mag);
  }
  get direction() {
    return Math.atan2(this.y, this.x);
  }
  distance(vec = new vec2()) {
    var d = Math.sqrt(
      Math.pow(this.x - vec.x, 2) + Math.pow(this.y - vec.y, 2)
    );
    return d;
  }
  static fromAng(angle, magnitude = 1) {
    return new vec2(Math.cos(angle) * magnitude, Math.sin(angle) * magnitude);
  }
  static fromOther(vector) {
    return new vec2(vector.x, vector.y);
  }
}

const sensorData = {};

export default {
  initialize({ model }) {
    model.on("change:controls", () => {
      const controls = model.get("controls");

      if (controls.data) {
        for (const [key, value] of Object.entries(controls.data)) {
          keys[key] = value;
        }
      }

      model.set("sensorData", {
        angles: sensorData.angles || [],
        hitPoints: sensorData.hitPoints || [],
        labels: sensorData.labels || [],
        scanId: controls.num_scans || 0,
      });
      model.save_changes();
    });
  },

  async render({ model, el }) {
    const { default: Matter } = await import(
      "https://cdn.jsdelivr.net/npm/matter-js/+esm"
    );
    const {
      Engine,
      Render,
      Runner,
      World,
      Bodies,
      Body,
      Events,
      Query,
      Vector,
      Composite,
    } = Matter;

    const dimensions = model.get("_viewport_size") || [800, 600];
    const width = dimensions[0];
    const height = dimensions[1];
    const engine = Engine.create();
    engine.gravity.y = 0;

    const container = document.createElement("div");
    container.className = "sim-container";
    el.appendChild(container);

    const renderArea = document.createElement("div");
    renderArea.className = "render-area";
    container.appendChild(renderArea);

    const renderInstance = Render.create({
      element: renderArea,
      engine,
      options: {
        width,
        height,
        wireframes: false,
        background: "#0b1220",
      },
    });

    Render.run(renderInstance);
    const runner = Runner.create();
    Runner.run(runner, engine);

    const mapData = model.get("mapData") || {
      map: [],
      robot: { pos: [200, 200], angle: 0, speed: 0.01, turn_speed: 0.03 },
    };
    

    model.on("change:_reset_state", () => {
      if (model.get("_reset_state")) {
        World.clear(engine.world);
        Engine.clear(engine);
        buildWorld();
        model.set("_reset_state", false);
      }
    });

    let robot;
    let headingIndicator;
    const robotWidth = 54;
    const robotHeight = 44;

    function buildWorld() {
      const bodies = [];
      mapData.map.forEach((item) => {
        if (item.type === "rectangle") {
          item.bodyInfo.isStatic = item.bodyInfo.isStatic ?? true;
          const rect = Bodies.rectangle(
            item.x,
            item.y,
            item.width,
            item.height,
            item.bodyInfo
          );
          bodies.push(rect);
        }
      });
      World.add(engine.world, bodies);

      robot = Bodies.rectangle(
        mapData.robot.pos[0],
        mapData.robot.pos[1],
        robotWidth,
        robotHeight,
        {
          frictionAir: 0.12,
          friction: 0,
          restitution: 0.1,
          inertia: Infinity,
          angle: mapData.robot.angle,
          render: { fillStyle: "#f0c808" },
        }
      );

      // Add heading
      headingIndicator = Bodies.polygon(
        robot.position.x + 30,
        robot.position.y,
        3,
        16,
        {
          isSensor: true,
          render: {
            fillStyle: "rgba(209,73,91,0.75)",
            strokeStyle: "rgba(209,73,91,0.9)",
            lineWidth: 1,
          },
        }
      );
      headingIndicator.isStatic = true;
      World.add(engine.world, [robot, headingIndicator]);
    }

    buildWorld();

    Events.on(engine, "beforeUpdate", () => {
      Body.setPosition(headingIndicator, {
        x: robot.position.x + Math.cos(robot.angle) * (robotWidth / 2 + 6),
        y: robot.position.y + Math.sin(robot.angle) * (robotWidth / 2 + 6),
      });
      Body.setAngle(headingIndicator, robot.angle);
    });

    if (model.get("show_controls")) {
      const controls = document.createElement("div");
      controls.className = "controls";
      controls.innerHTML = `
        <button id="forward">↑</button>
        <button id="left">←</button>
        <button id="right">→</button>
        <button id="backward">↓</button>
      `;
      container.appendChild(controls);

      controls.addEventListener("mousedown", (event) => {
        const dir = event.target.id;
        if (dir) keys[dir] = true;
      });
      controls.addEventListener("mouseup", (event) => {
        const dir = event.target.id;
        if (dir) keys[dir] = false;
      });
    }

    function applyControls() {
      const thrust = mapData.robot.speed || 0.01;
      const turn = mapData.robot.turn_speed || 0.04;

      if (keys.forward) {
        Body.applyForce(robot, robot.position, {
          x: Math.cos(robot.angle) * thrust,
          y: Math.sin(robot.angle) * thrust,
        });
      }
      if (keys.backward) {
        Body.applyForce(robot, robot.position, {
          x: -Math.cos(robot.angle) * thrust * 0.6,
          y: -Math.sin(robot.angle) * thrust * 0.6,
        });
      }

      if (keys.left && !keys.right) {
        Body.setAngularVelocity(robot, -turn);
      } else if (keys.right && !keys.left) {
        Body.setAngularVelocity(robot, turn);
      } else {
        Body.setAngularVelocity(robot, robot.angularVelocity * 0.9);
      }

      const maxSpeed = 8;
      const v = robot.velocity;
      const speed = Math.hypot(v.x, v.y);
      if (speed > maxSpeed) {
        Body.setVelocity(robot, {
          x: (v.x * maxSpeed) / speed,
          y: (v.y * maxSpeed) / speed,
        });
      }
    }

    function lidarScan(engine, origin, yaw, numBeams, fov, maxRange) {
      const allBodies = Composite.allBodies(engine.world);
      const bodies = allBodies.filter(
        (b) => b !== robot && b !== headingIndicator
      );

      const angles = [];
      const hitPoints = [];
      const hitBodies = [];

      for (let i = 0; i < numBeams; i++) {
        const angle = yaw - fov / 2 + (fov * i) / (numBeams - 1);
        const dir = { x: Math.cos(angle), y: Math.sin(angle) };

        let start = Vector.clone(origin);
        let end = {
          x: origin.x + dir.x * maxRange,
          y: origin.y + dir.y * maxRange,
        };

        start = vec2.fromOther(start);
        end = vec2.fromOther(end);
        var query = Query.ray(bodies, start, end);
        var cols = [];

        var raytest = new ray(start, end);
        for (let i = query.length - 1; i >= 0; i--) {
          var bcols = ray.bodyCollisions(raytest, query[i].body);
          for (let k = bcols.length - 1; k >= 0; k--) {
            cols.push(bcols[k]);
          }
        }

        cols.sort(function (a, b) {
          return a.point.distance(start) - b.point.distance(start);
        });

        if (cols.length > 0) {
          hitPoints.push(cols[0].point);
          hitBodies.push(cols[0].body);
          angles.push(angle);
        }
      }

      return { angles, hitPoints, hitBodies };
    }

    const {
      numBeams = 30,
      fov = 2 * Math.PI,
      maxRange = 1000,
    } = mapData.robot.lidar ?? {};

    Events.on(engine, "afterUpdate", () => {
      applyControls();

      const origin = robot.position;
      const yaw = robot.angle;
      const scan = lidarScan(engine, origin, yaw, numBeams, fov, maxRange);

      sensorData.angles = scan.angles;
      sensorData.hitPoints = scan.hitPoints;
      sensorData.labels = scan.hitBodies.map((body) => body.label);
      sensorData.scanTime = Date.now();

      if (model.get("debugDraw")) {
        const ctx = renderInstance.context;
        ctx.save();
        ctx.strokeStyle = "rgba(255, 0, 0, 1)";
        ctx.lineWidth = 1;

        for (let i = 0; i < scan.hitPoints.length; i++) {
          const p = scan.hitPoints[i];
          ctx.beginPath();
          ctx.moveTo(origin.x, origin.y);
          ctx.lineTo(p.x, p.y);
          ctx.stroke();
        }

        ctx.restore();
      }
    });

    Render.lookAt(renderInstance, {
      min: { x: 0, y: 0 },
      max: { x: width, y: height },
    });
  },
};