from llm import user_info_agent, extract_preferences  

def process_message(user_message: str, message_history: list) -> str:  
    """  
    Process user messages using the user_info_agent to maintain natural conversation flow.  
    Also checks if all preferences have been collected.  

    Args:  
        user_message (str): The current user message  
        message_history (list): List of previous messages in the conversation  

    Returns:  
        str: Assistant's response  
    """  

    # Get response from user_info_agent  
    response = user_info_agent(user_message, message_history)  

    # Combine all user messages for preference extraction  
    combined_messages = " ".join([msg['content'] for msg in message_history + [{"role": "user", "content": user_message}] if msg['role'] == "user"])  

    # Extract preferences  
    preferences = extract_preferences(combined_messages)  

    # Check if all preferences are collected and have values  
    if isinstance(preferences, dict) and "error" not in preferences:  
        all_fields_present = all([  
            preferences.get("city"),  
            preferences.get("time_range"),  
            preferences.get("budget"),  
            preferences.get("interests") and len(preferences["interests"]) > 0,  
            preferences.get("starting_point")  
        ])  

        if all_fields_present:  
            print("completed")  
            print("Collected preferences:", preferences)  

    return response  