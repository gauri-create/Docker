const socket = io();

let mode = "";
let room = "";

const boardDiv = document.getElementById("board");
const multiplayerDiv = document.getElementById("multiplayer");

// ----------- UI CONTROL -----------

function startSingle() {
    mode = "single";
    resetLocal();
}

function showMultiplayer() {
    multiplayerDiv.style.display = "block";
}

function joinRoom() {
    mode = "multi";
    room = document.getElementById("roomInput").value;
    socket.emit("join", {room});
}

// ----------- DRAW BOARD -----------

function drawBoard(board) {
    boardDiv.innerHTML = "";
    board.forEach((val, i) => {
        let cell = document.createElement("div");
        cell.className = "cell";
        cell.innerText = val;
        cell.onclick = () => move(i);
        boardDiv.appendChild(cell);
    });
}

// ----------- MOVES -----------

function move(i) {
    if (mode === "single") {
        fetch("/move", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({index: i})
        })
        .then(res => res.json())
        .then(data => {
            drawBoard(data.board);
            if (data.status !== "continue") alert(data.status);
        });
    } else {
        socket.emit("move", {room, index: i});
    }
}

// ----------- RESET -----------

function reset() {
    if (mode === "single") {
        resetLocal();
    } else {
        socket.emit("reset", {room});
    }
}

function resetLocal() {
    fetch("/reset")
    .then(res => res.json())
    .then(data => drawBoard(data.board));
}

// ----------- SOCKET EVENTS -----------

socket.on("update", data => {
    drawBoard(data.board);
});

socket.on("game_over", msg => {
    alert(msg);
});