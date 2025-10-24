const socket = io();

socket.on('connect', () => {
    socket.emit('join', {from: currentUserId, to: toUserId});  // Define in HTML script
});

function sendMessage() {
    const text = document.getElementById('message').value;
    socket.emit('send_message', {from: currentUserId, to: toUserId, text});
    document.getElementById('message').value = '';
}

socket.on('new_message', (data) => {
    const chatDiv = document.getElementById('chat');
    chatDiv.innerHTML += `<p>${data.from}: ${data.text}</p>`;
    chatDiv.scrollTop = chatDiv.scrollHeight;
});

// For media upload
function uploadMedia() {
    const formData = new FormData();
    formData.append('file', document.getElementById('media').files[0]);
    fetch('/upload', {method: 'POST', body: formData})
        .then(res => res.json())
        .then(data => {
            socket.emit('send_message', {from: currentUserId, to: toUserId, media: data.url});
        });
}
