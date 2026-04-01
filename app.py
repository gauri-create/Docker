from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = {}  # room_name -> {players: {sid: 'X'/'O'}, board: [...], turn: 'X', vs_computer: bool, computer_player: 'X'/'O'}

@app.route("/")
def index():
    return render_template("index.html")

def check_win(board, p):
    wins = [
        (0,1,2),(3,4,5),(6,7,8),
        (0,3,6),(1,4,7),(2,5,8),
        (0,4,8),(2,4,6)
    ]
    return any(board[a]==board[b]==board[c]==p for a,b,c in wins)

def minimax(board, player, computer, human, alpha, beta):
    # Base case
    if check_win(board, computer):
        return 10, None
    elif check_win(board, human):
        return -10, None
    elif " " not in board:
        return 0, None

    if player == computer:
        max_eval = -float('inf')
        best_move = None
        for i, cell in enumerate(board):
            if cell == " ":
                board[i] = player
                eval, _ = minimax(board, human, computer, human, alpha, beta)
                board[i] = " "
                if eval > max_eval:
                    max_eval = eval
                    best_move = i
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        best_move = None
        for i, cell in enumerate(board):
            if cell == " ":
                board[i] = player
                eval, _ = minimax(board, computer, computer, human, alpha, beta)
                board[i] = " "
                if eval < min_eval:
                    min_eval = eval
                    best_move = i
                beta = min(beta, eval)
                if beta <= alpha:
                    break
        return min_eval, best_move

def computer_move(room):
    game = rooms[room]
    empty_cells = [i for i, v in enumerate(game["board"]) if v==" "]
    if not empty_cells:
        return
    # Use minimax with alpha-beta pruning
    _, idx = minimax(game["board"], game["computer_player"], game["computer_player"], "X", -float('inf'), float('inf'))
    if idx is None:
        idx = empty_cells[0]  # fallback
    game["board"][idx] = game["computer_player"]

    emit("update", {"board": game["board"], "turn": "X"}, to=room)

    if check_win(game["board"], game["computer_player"]):
        emit("game_over", f"{game['computer_player']} wins!", to=room)
        return
    if " " not in game["board"]:
        emit("game_over", "Draw!", to=room)
        return

    game["turn"] = "X"

@socketio.on("join")
def on_join(data):
    room = data["room"]
    vs_computer = data.get("vs_computer", False)
    sid = request.sid
    join_room(room)

    if room not in rooms:
        rooms[room] = {"players": {}, "board": [" "]*9, "turn": "X", "vs_computer": vs_computer, "computer_player": None}

    game = rooms[room]

    if vs_computer:
        game["computer_player"] = "O"  # Human is X
        game["players"][sid] = "X"
        emit("update", {"board": game["board"], "turn": "X", "player": "X"}, to=sid)
        emit("info", f"Game vs Computer started. You are X.", to=sid)
    else:
        # Multiplayer
        if sid not in game["players"]:
            if "X" not in game["players"].values():
                game["players"][sid] = "X"
            elif "O" not in game["players"].values():
                game["players"][sid] = "O"
            else:
                emit("full", "Room is full", to=sid)
                return
        player = game["players"][sid]
        emit("update", {"board": game["board"], "turn": game["turn"], "player": player}, to=sid)
        emit("info", f"Player {player} joined", to=room)

@socketio.on("move")
def on_move(data):
    room = data["room"]
    idx = data["index"]
    sid = request.sid
    game = rooms.get(room)
    if not game:
        return

    if game["vs_computer"]:
        if idx<0 or game["board"][idx]!=" ":
            return
        game["board"][idx] = "X"
        emit("update", {"board": game["board"], "turn": "O"}, to=room)

        if check_win(game["board"], "X"):
            emit("game_over", "X wins!", to=room)
            return
        if " " not in game["board"]:
            emit("game_over", "Draw!", to=room)
            return

        # Computer move
        computer_move(room)
    else:
        sid_player = game["players"].get(sid)
        if not sid_player or game["board"][idx]!=" " or game["turn"] != sid_player:
            return
        game["board"][idx] = sid_player
        next_turn = "O" if sid_player=="X" else "X"
        emit("update", {"board": game["board"], "turn": next_turn}, to=room)
        if check_win(game["board"], sid_player):
            emit("game_over", f"{sid_player} wins!", to=room)
            return
        if " " not in game["board"]:
            emit("game_over", "Draw!", to=room)
            return
        game["turn"] = next_turn

@socketio.on("reset")
def on_reset(data):
    room = data["room"]
    game = rooms.get(room)
    if not game:
        return
    game["board"] = [" "]*9
    game["turn"] = "X"
    emit("update", {"board": game["board"], "turn": "X"}, to=room)

@socketio.on("leave")
def on_leave(data):
    room = data["room"]
    sid = request.sid
    leave_room(room)
    game = rooms.get(room)
    if game and sid in game["players"]:
        del game["players"][sid]
        emit("info", "A player has left the game", to=room)
        if not game["players"]:
            del rooms[room]

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)