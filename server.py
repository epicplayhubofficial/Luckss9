from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
suits = ["H","D","C","S"]

rooms = {}

def value(rank):
    if rank == "A": return 1
    if rank in ["10","J","Q","K"]: return 0
    return int(rank)

def draw():
    rank = random.choice(ranks)
    suit = random.choice(suits)
    code = ("0" if rank == "10" else rank) + suit
    return {"rank": rank, "code": code}

def score(cards):
    return sum(value(c["rank"]) for c in cards) % 10

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("join")
def join(data):
    room = data["room"]
    join_room(room)

    if room not in rooms:
        rooms[room] = {"players": [], "game": {}}

    if request.sid not in rooms[room]["players"]:
        rooms[room]["players"].append(request.sid)

    if len(rooms[room]["players"]) > 2:
        emit("full")
        return

    if len(rooms[room]["players"]) == 2:
        p1, p2 = rooms[room]["players"]

        rooms[room]["game"] = {
            p1: {"cards": [draw(), draw()], "done": False},
            p2: {"cards": [draw(), draw()], "done": False}
        }

        socketio.emit("start", {"players": rooms[room]["players"]}, room=room)
    else:
        emit("waiting")

@socketio.on("hit")
def hit(data):
    room = data["room"]
    game = rooms[room]["game"]

    if len(game[request.sid]["cards"]) < 3:
        game[request.sid]["cards"].append(draw())

    emit("update", game, room=room)

@socketio.on("fight")
def fight(data):
    room = data["room"]
    game = rooms[room]["game"]

    game[request.sid]["done"] = True

    if all(p["done"] for p in game.values()):
        players = list(game.keys())
        p1, p2 = players

        s1 = score(game[p1]["cards"])
        s2 = score(game[p2]["cards"])

        if s1 > s2:
            winner = "Player 1 Wins"
        elif s2 > s1:
            winner = "Player 2 Wins"
        else:
            winner = "Tie"

        socketio.emit("end", {
            "game": game,
            "winner": winner,
            "scores": {p1: s1, p2: s2}
        }, room=room)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
