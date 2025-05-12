# --- main.py ---

# Ensure this is at the very top to load environment variables first
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn # Keep uvicorn import if you plan to run from here, though running via terminal is standard

# Import the run_conversation function from your separate agent.py file
from agent import run_conversation

# Create the FastAPI application instance
# This must be at the top level of the script for Uvicorn to find it
app = FastAPI()

# --- Basic HTML for the UI ---
# This multi-line string contains the HTML, CSS, and JavaScript for the chat interface.
# Keep this exactly as it was provided in the previous step.
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Chat with RAG Agent</title>
    <h2>By Adya Tiwari<h2>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }
        h1 { color: #333; }
        #chatbox {
            border: 1px solid #ccc;
            height: 400px; /* Adjusted height for better viewing */
            overflow-y: scroll;
            padding: 15px; /* Adjusted padding */
            margin-bottom: 10px;
            background-color: #f9f9f9; /* Light background */
            border-radius: 8px;
        }
        .message {
            margin-bottom: 15px; /* Increased spacing between messages */
            padding: 10px; /* Added padding within message */
            border-radius: 5px;
        }
        .user {
            background-color: #e9e9eb; /* Light grey background for user */
            text-align: right; /* Align user messages to the right */
            margin-left: 20%; /* Keep user messages from spanning full width */
        }
        .agent {
            background-color: #d4edda; /* Light green background for agent */
            text-align: left; /* Align agent messages to the left */
            margin-right: 20%; /* Keep agent messages from spanning full width */
        }
        .input-area {
            display: flex; /* Use flexbox for input and button */
        }
        #user_input {
            flex-grow: 1; /* Allow input field to take available space */
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-right: 5px; /* Space between input and button */
        }
        button {
            padding: 10px 15px;
            background-color: #007bff; /* Blue button */
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <h1>Chat with your RAG Agent</h1>
    <div id="chatbox">
        <div class="message agent">Agent: Hello! How can I help you today?</div>
    </div>
    <div class="input-area">
        <input type="text" id="user_input" placeholder="Enter your query here...">
        <button onclick="sendMessage()">Send</button>
    </div>

    <script>
        async function sendMessage() {
            const userInput = document.getElementById('user_input');
            const chatbox = document.getElementById('chatbox');
            const query = userInput.value;

            if (query.trim() === "") return; // Don't send empty messages

            // Display user message
            const userMessageDiv = document.createElement('div');
            userMessageDiv.classList.add('message', 'user');
            userMessageDiv.textContent = 'You: ' + query;
            chatbox.appendChild(userMessageDiv);

            userInput.value = ''; // Clear input field
            chatbox.scrollTop = chatbox.scrollHeight; // Scroll to the bottom

            // Display a "Thinking..." message from the Agent
            const thinkingMessageDiv = document.createElement('div');
            thinkingMessageDiv.classList.add('message', 'agent', 'thinking');
            thinkingMessageDiv.textContent = 'Agent: Thinking...';
            chatbox.appendChild(thinkingMessageDiv);
            chatbox.scrollTop = chatbox.scrollHeight; // Scroll to the bottom


            // Send query to FastAPI backend using the /chat endpoint
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded', // Form data format
                    },
                    body: new URLSearchParams({ 'query': query }) // Send query as form data
                });

                // Remove the "Thinking..." message
                chatbox.removeChild(thinkingMessageDiv);


                if (!response.ok) {
                     throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json(); // Assuming backend returns JSON like {"response": "..."}

                // Display agent response
                const agentMessageDiv = document.createElement('div');
                agentMessageDiv.classList.add('message', 'agent');
                agentMessageDiv.textContent = 'Agent: ' + data.response; // Access the response field
                chatbox.appendChild(agentMessageDiv);

            } catch (error) {
                // Remove the "Thinking..." message if it's still there
                const thinkingMessage = chatbox.querySelector('.message.thinking');
                if (thinkingMessage) {
                     chatbox.removeChild(thinkingMessage);
                }
                const errorMessageDiv = document.createElement('div');
                errorMessageDiv.classList.add('message', 'error'); // You might want to add styling for errors
                errorMessageDiv.textContent = 'Error: Could not get response from agent. ' + error.message;
                chatbox.appendChild(errorMessageDiv);
                console.error('Error:', error);
            } finally {
               chatbox.scrollTop = chatbox.scrollHeight; // Ensure scroll to bottom after response or error
            }
        }

        // Allow sending message by pressing Enter key in the input field
        document.getElementById('user_input').addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                sendMessage();
                event.preventDefault(); // Prevent default form submission if inside a form
            }
        });
    </script>
</body>
</html>
"""

# --- FastAPI Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    """Serves the basic HTML chat interface."""
    return html_content

@app.post("/chat")
async def chat_with_agent(query: str = Form(...)):
    """
    Receives user query via POST request and sends it to the agent.
    Returns the agent's response.
    """
    print(f"Received query: {query}") # Optional: Log received query

    # Call the run_conversation function from your agent.py
    # This is where the user query is passed to the LLM and tools are used.
    agent_response = run_conversation(query)

    print(f"Agent response: {agent_response}") # Optional: Log agent response

    # Return the agent's response as JSON
    return {"response": agent_response}

# --- How to Run the FastAPI App ---
# To run this application, save the code as main.py and run the command:
# uvicorn main:app --reload
# (Ensure your virtual environment is activated and GOOGLE_API_KEY is set in .env)