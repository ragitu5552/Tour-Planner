import json
from groq import Groq
import re

client = Groq(api_key="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")

def user_info_agent(user_message: str, message_history: list) -> str:
    """
    Specialized agent for travel itinerary planning that maintains context
    and collects user preferences systematically
    """

    system_prompt = """
    You are a specialized travel planning assistant focused on creating one-day city tours.
    Your role is to:
  Instructions for generating response:  
    1. Analyze the user's last message  
    2. Update any provided preferences  
    3. Keep existing preferences if not mentioned  
    4. Ask for the next missing information  
    5. Set complete to true only if all preferences are filled  
    6. Once you have all information, say "Thanks, I will be now developing an optimize tour plan for you."

    Missing information priority:  
    1. City (if empty)  
    2. Timings (if empty)  
    3. Budget (if empty)  
    4. Interests (if empty)  
    5. Starting point (if empty)  

    """

    # Format message history for the API
    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # Add conversation history
    for msg in message_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.7,
            max_tokens=2048  # Increased for longer itineraries
        )

        return completion.choices[0].message.content
    except Exception as e:
        return f"Error processing request: {str(e)}"

def extract_preferences(user_message: str) -> dict:
    """
    Helper function to extract and maintain user preferences from a single user message.
    Adds robust JSON parsing and error handling.
    """
    # Comprehensive system prompt for JSON extraction
    system_prompt = """
    You are a JSON extraction assistant. Extract user preferences with the following rules:
    1. Use this exact JSON structure
    2. Only fill in fields with explicit user mentions
    3. Use null for unknown fields
    4. Normalize data (e.g., lowercase interests)
    5. Be precise in extracting information

    JSON Schema:
    {
        "city": "string or null",
        "time_range": "string or null (format: 'HH:MM AM/PM - HH:MM AM/PM')",
        "budget": "string or null (options: 'low', 'medium', 'high')",
        "interests": ["list of lowercase strings or empty list"],
        "starting_point": "string or null"
    }
    """

    # Messages for the model
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    try:
        # API call to extract preferences
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.01,
            max_tokens=512,
            response_format={"type": "json_object"}
        )

        # Extract response content
        response_content = completion.choices[0].message.content

        # Robust JSON parsing with multiple techniques
        try:
            # First, try direct JSON parsing
            preferences = json.loads(response_content)
            return preferences
        except json.JSONDecodeError:
            # If direct parsing fails, try extracting JSON from markdown code block
            json_match = re.search(r'```json\n(.*?)```', response_content, re.DOTALL)
            if json_match:
                preferences = json.loads(json_match.group(1))
                return preferences
            
            # If code block parsing fails, try extracting JSON from text
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                preferences = json.loads(json_match.group(0))
                return preferences

            # If all parsing methods fail
            raise ValueError("Could not extract valid JSON")

    except Exception as e:
        # Comprehensive error handling
        return {
            "error": f"Extraction error: {str(e)}",
            # "raw_response": response_content
        }

# Example usage
message_history = [
    {"role": "user", "content": "I want to plan a day in Paris."},
    {"role": "assistant", "content": "Great! What time will you be available?"},
    {"role": "user", "content": "From 10 AM to 6 PM. My budget is medium, and I love food and history."},
    {"role": "assistant", "content": "Got it! Where will you be starting from?"},
    {"role": "user", "content": "I'll be starting from my hotel near the Eiffel Tower."}
]

# Combine the history into a single message for extraction
# combined_message = " ".join([msg['content'] for msg in message_history if msg['role'] == 'user'])
# print(extract_preferences(combined_message))