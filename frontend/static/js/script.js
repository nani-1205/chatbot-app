// frontend/static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatHistory = document.getElementById('chat-history');
    const userQueryInput = document.getElementById('user-query');

    chatForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const userQuery = userQueryInput.value;
        if (!userQuery.trim()) return;

        // Add user message to chat history
        const userMessageDiv = document.createElement('div');
        userMessageDiv.classList.add('chat-message', 'user-message');
        userMessageDiv.innerHTML = `<p class="message-text"><strong>You:</strong> ${userQuery}</p>`;
        chatHistory.appendChild(userMessageDiv);

        userQueryInput.value = ''; // Clear input

        // Send query to backend
        fetch('/get_response', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `user_query=${encodeURIComponent(userQuery)}`
        })
        .then(response => response.json())
        .then(data => {
            const botResponse = data.response;
            const botMessageDiv = document.createElement('div');
            botMessageDiv.classList.add('chat-message', 'bot-message');
            botMessageDiv.innerHTML = `<p class="message-text"><strong>Bot:</strong> ${botResponse}</p>`;
            chatHistory.appendChild(botMessageDiv);

            // Scroll to bottom of chat history
            chatHistory.scrollTop = chatHistory.scrollHeight;
        });
    });
});