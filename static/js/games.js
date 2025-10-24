// Tic Tac Toe
let board = Array(9).fill(null);
let player = 'X';
let ai = 'O';

function renderBoard() {
    document.querySelectorAll('.cell').forEach((cell, i) => {
        cell.textContent = board[i];
    });
}

function checkWinner() {
    const wins = [[0,1,2], [3,4,5], [6,7,8], [0,3,6], [1,4,7], [2,5,8], [0,4,8], [2,4,6]];
    for (let w of wins) {
        if (board[w[0]] && board[w[0]] === board[w[1]] && board[w[0]] === board[w[2]]) return board[w[0]];
    }
    return board.every(cell => cell) ? 'Tie' : null;
}

function minimax(newBoard, isMax) {
    let winner = checkWinner();
    if (winner === ai) return 10;
    if (winner === player) return -10;
    if (winner === 'Tie') return 0;
    let best = isMax ? -Infinity : Infinity;
    for (let i = 0; i < 9; i++) {
        if (!newBoard[i]) {
            newBoard[i] = isMax ? ai : player;
            let score = minimax(newBoard, !isMax);
            newBoard[i] = null;
            best = isMax ? Math.max(best, score) : Math.min(best, score);
        }
    }
    return best;
}

function aiMove() {
    let bestScore = -Infinity;
    let move;
    for (let i = 0; i < 9; i++) {
        if (!board[i]) {
            board[i] = ai;
            let score = minimax(board, false);
            board[i] = null;
            if (score > bestScore) {
                bestScore = score;
                move = i;
            }
        }
    }
    board[move] = ai;
}

function playerMove(index) {
    if (board[index] || checkWinner()) return;
    board[index] = player;
    renderBoard();
    if (!checkWinner()) {
        aiMove();
        renderBoard();
    }
    let winner = checkWinner();
    if (winner) {
        fetch('/game/win', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({game: 'tictactoe', win: winner === player})
        }).then(res => res.json()).then(data => {
            alert(`You ${winner === player ? 'Win' : 'Lose'}! Balance: ${data.balance}`);
            board = Array(9).fill(null);
            renderBoard();
        });
    }
}

// Spin and Win
function spinWheel() {
    document.getElementById('wheel').innerText = 'Spinning...';
    setTimeout(() => {
        let prize = Math.random() > 0.5 ? 20 : -10;
        fetch('/game/win', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({game: 'spin', win: prize > 0})
        }).then(res => res.json()).then(data => {
            document.getElementById('wheel').innerText = 'Spin Again!';
            alert(`You won ${prize} coins! New Balance: ${data.balance}`);
        });
    }, 1000);
}
