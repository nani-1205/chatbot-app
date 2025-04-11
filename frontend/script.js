document.addEventListener('DOMContentLoaded', function() {
    const chatLog = document.getElementById('chat-log');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = userInput.value;
        if (message.trim() !== '') {
            appendMessage('user-message', message);
            userInput.value = '';
            // Send message to backend API
            fetch('/chat', { // Adjust URL if your backend is deployed on a different domain/port
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            })
            .then(response => response.json())
            .then(data => {
                if (data.response) {
                    appendMessage('bot-message', data.response);
                } else if (data.error) {
                    appendMessage('bot-message error', 'Error: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error communicating with backend:', error);
                appendMessage('bot-message error', 'Error communicating with backend.');
            });
        }
    }

    function appendMessage(senderClass, text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', senderClass);
        messageDiv.textContent = text;
        chatLog.appendChild(messageDiv);
        chatLog.scrollTop = chatLog.scrollHeight; // Scroll to bottom of chat log
    }
});