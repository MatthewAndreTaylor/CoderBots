const width = 800;
const height = 1000;
const two = new Two({
  width: width,
  height: height,
  autostart: true
}).appendTo(document.body);

// Define a function to create a circle shape in Two.js
function createCircle(x, y, radius, color) {
  const circle = two.makeCircle(x, y, radius);
  circle.fill = color;
  circle.noStroke();
  return circle;
}

// Track player circle
let playerCircle;

let balls = {};

function tweenPlayerCircle(x, y) {
  new TWEEN.Tween(playerCircle.translation)
    .to({ x, y }, 1) // Adjust the duration as needed
    .start();
}

// Update other circles (balls) with tween animation
function tweenBall(ball, x, y) {
  new TWEEN.Tween(ball.translation)
    .to({ x, y }, 1) // Adjust the duration as needed
    .start();
}

// Connect to the WebSocket for receiving game state
const socket = new WebSocket(`ws://${location.host}/echo`);

socket.addEventListener("open", (event) => {
    console.log("Connected to server: ", event);
});

socket.addEventListener("message", (event) => {
  try {
    const data = JSON.parse(event.data);
    
    // Update player circle position
    if (data.player) {
      if (!playerCircle) {
        playerCircle = createCircle(data.player.x, data.player.y, 20, 'blue');
      } else {
        tweenPlayerCircle(data.player.x, data.player.y);
      }
    }

    // Update other circles (balls)
    data.balls.forEach(ballData => {
      let ball = balls[ballData.id];
      if (!ball) {
        ball = createCircle(ballData.x, ballData.y, 20, 'red');
        balls[ballData.id] = ball;
      } else {
        tweenBall(ball, ballData.x, ballData.y);
      }
    });

  } catch (error) {
    console.error('Error parsing JSON:', error);
    console.error('Raw data:', event.data);
  }
});

socket.addEventListener("close", (event) => {
    console.log("Connection closed:", event);
});

// Send user input via WebSocket
const inputSocket = new WebSocket(`ws://${location.host}/input`);

document.addEventListener("keydown", (event) => {
  const impulse = { x: 0, y: 0 };

    switch (event.key) {
        case "ArrowUp":
            impulse.y = -50;
            break;
        case "ArrowDown":
            impulse.y = 50;
            break;
        case "ArrowLeft":
            impulse.x = -50;
            break;
        case "ArrowRight":
            impulse.x = 50;
            break;
    }

    inputSocket.send(JSON.stringify(impulse));
});

function animate() {
  requestAnimationFrame(animate);
  TWEEN.update();
}

animate();