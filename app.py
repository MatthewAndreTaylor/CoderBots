from flask import Flask, render_template
from Box2D import b2World, b2Vec2, b2EdgeShape, b2FixtureDef, b2CircleShape
import pygame
from coderbot_package.maps.loader import load_map

# Server should send player physics data
# when the server starts send a list 


app = Flask(__name__)

WIDTH, HEIGHT = 800, 1000
world = b2World(gravity=(0, 0), doSleep=True)

# Load a map from a JSON file (shapes defined in pixels). The loader converts
# pixels -> meters using the ppm (pixels per meter) value.
load_map(world, "coderbot_package/maps/rect_triangle_map.json", ppm=10)

# create player after map is loaded
player_body = world.CreateDynamicBody(
    position=(WIDTH / 2 / 10, 5),
    shapes=b2CircleShape(radius=2),
    linearDamping=0.5,
    angularDamping=0.5
)

pygame.init()
clock = pygame.time.Clock()


@app.route('/', methods=['GET',"POST"])
def home():
    return render_template("index.html")

@app.route('/geometry', methods=['GET'])


if __name__ == "__main__":
    app.run(debug=True)