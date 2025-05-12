# --- agent.py (Modified for OpenAI) ---

import json
import os
from openai import OpenAI # Import the OpenAI library
from agent_tools import search_federal_documents # Your existing tool function

# Configure the OpenAI client
# This relies on OPENAI_API_KEY being set in the environment (loaded by main.py)
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

client = OpenAI(api_key=API_KEY)

# Choose an OpenAI model that supports function calling
# "gpt-3.5-turbo" is a good and cost-effective choice for testing.
# "gpt-4-turbo-preview" or "gpt-4" are more capable but more expensive.
MODEL_NAME = "gpt-3.5-turbo" # Or "gpt-4-turbo-preview"

# --- Define the schema for your tools (functions) in OpenAI format ---
# This tells the LLM about the available functions it can call.
tools_schema_openai = [
    {
        "type": "function",
        "function": {
            "name": "search_federal_documents",
            "description": "Search federal documents based on keywords, agency, or publication dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to search for in the document title or content.",
                    },
                    "agency": {
                        "type": "string",
                        "description": "Filter documents by the publishing agency name.",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date for publication date filter (YYYY-MM-DD format).",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for publication date filter (YYYY-MM-DD format).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return. Defaults to 10.",
                    },
                },
                "required": [], # OpenAI expects a list of required parameter names
                                 # e.g., ["query"] if 'query' is always required.
                                 # For now, making all optional as in your original Gemini schema.
            },
        },
    }
    # Add other tools here, each as a new dictionary in the list
]

# --- Store conversation history ---
# OpenAI's API is stateless for chat completions by default,
# so we need to manage the history if we want follow-up conversations.
# For a single turn RAG, this might be simpler. Let's start with a simpler approach
# and build up if multi-turn is needed.
# For now, we will send the history in each call for simplicity.

def run_conversation(user_query, conversation_history=None):
    """
    Sends user query to the OpenAI LLM, handles tool calls, and returns the final response.
    """
    if conversation_history is None:
        # Initialize with a system message (optional, but can guide the AI)
        conversation_history = [
            {"role": "system", "content": "You are a helpful assistant that can search federal documents."}
        ]

    # Add user's query to the history
    conversation_history.append({"role": "user", "content": user_query})

    print(f"Sending to OpenAI: {conversation_history}")

    try:
        # First call to OpenAI
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=conversation_history,
            tools=tools_schema_openai,
            tool_choice="auto",  # "auto" lets the model decide, or specify {"type": "function", "function": {"name": "my_function"}}
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # --- Step 2: Check if the model wants to call a tool ---
        if tool_calls:
            print(f"OpenAI wants to call tools: {tool_calls}")
            # Add the assistant's response (requesting tool call) to history
            conversation_history.append(response_message)

            available_functions = {
                "search_federal_documents": search_federal_documents,
            }
            
            # --- Step 3: Execute tool calls ---
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions.get(function_name)
                
                if function_to_call:
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                        print(f"Executing tool: {function_name} with args: {function_args}")
                        function_response = function_to_call(**function_args)
                        
                        # Add the tool's response to history
                        conversation_history.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": json.dumps(function_response), # Ensure content is a JSON string
                            }
                        )
                    except Exception as e:
                        print(f"Error executing tool {function_name}: {e}")
                        conversation_history.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": json.dumps({"error": f"Error executing function {function_name}: {str(e)}"}),
                            }
                        )
                else:
                    print(f"Error: Function '{function_name}' not found.")
                    # Potentially add an error message back to the model for this tool call
                    conversation_history.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps({"error": f"Function {function_name} not found."}),
                        }
                    )

            # --- Step 4: Send the tool responses back to the model ---
            print("Sending tool outputs back to OpenAI for summarization...")
            print(f"History before second call: {conversation_history}")
            
            second_response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=conversation_history,
            )
            final_response_message = second_response.choices[0].message.content
            # Add final assistant response to history for future turns (if any)
            conversation_history.append({"role": "assistant", "content": final_response_message})
            return final_response_message
        else:
            # --- If no tool call was requested, LLM provided a direct answer ---
            final_response_message = response_message.content
            # Add assistant's direct response to history
            conversation_history.append({"role": "assistant", "content": final_response_message})
            return final_response_message

    except Exception as e:
        print(f"An unexpected error occurred during OpenAI conversation: {e}")
        return f"An internal error occurred during the conversation: {str(e)}"

# Example of how to run the agent function (for testing)
if __name__ == "__main__":
    # This block allows you to test the agent.py file directly
    # Ensure your OPENAI_API_KEY environment variable is set.
    # If you are running this standalone and haven't loaded .env in main.py or similar:
    from dotenv import load_dotenv
    load_dotenv() # Load .env file if running agent.py directly

    # Check if API key is loaded (it would have raised an error earlier if not)
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not found. Please set it in your .env file.")
        exit()
        
    print(f"Agent initialized using OpenAI model: {MODEL_NAME}. Enter queries to test (type 'quit' to exit).")
    print("Make sure OPENAI_API_KEY is set and MySQL is running with data if your tool needs it.")

    # For multi-turn conversation in this test script, we'll manage history here
    current_conversation_history = []

    while True:
        user_input = input("\nYour Query: ")
        if user_input.lower() == 'quit':
            break

        print("Processing...")
        # Pass and update the history for each turn
        agent_response = run_conversation(user_input, current_conversation_history)
        print("\nAgent Response:")
        print(agent_response)
        # The run_conversation function now appends to the history it was given
        # so current_conversation_history is updated by reference.

    print("Agent stopped.")