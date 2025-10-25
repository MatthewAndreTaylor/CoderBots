from flask import Flask, render_template
from Box2D import b2World, b2Vec2, b2EdgeShape, b2FixtureDef, b2CircleShape
import pygame

# Server should send player physics data

# when the server starts send a list 


app = Flask(__name__)

WIDTH, HEIGHT = 800, 1000
world = b2World(gravity=(0, 0), doSleep=True)

player_body = world.CreateDynamicBody(
    position=(WIDTH / 2 / 10, 5),
    shapes=b2CircleShape(radius=2),
    linearDamping=0.5,
    angularDamping=0.5
)

wall_top = world.CreateStaticBody(
    position=(0, HEIGHT / 10),
    fixtures=b2FixtureDef(
        shape=b2EdgeShape(vertices=[(0, 0), (WIDTH / 10, 0)]),
        restitution=1.0
    )
)

wall_bottom = world.CreateStaticBody(
    position=(0, 0),
    fixtures=b2FixtureDef(
        shape=b2EdgeShape(vertices=[(0, 0), (WIDTH / 10, 0)]),
        restitution=1.0
    )
)

wall_left = world.CreateStaticBody(
    position=(0, 0),
    fixtures=b2FixtureDef(
        shape=b2EdgeShape(vertices=[(0, 0), (0, HEIGHT / 10)]),
        restitution=1.0
    )
)

wall_right = world.CreateStaticBody(
    position=(WIDTH / 10, 0),
    fixtures=b2FixtureDef(
        shape=b2EdgeShape(vertices=[(0, 0), (0, HEIGHT / 10)]),
        restitution=1.0
    )
)

pygame.init()
clock = pygame.time.Clock()


@app.route('/', methods=['GET',"POST"])
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)