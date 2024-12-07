import json
from groq import Groq
import re, os
from dotenv import load_dotenv
from py2neo import Graph, Node, Relationship

load_dotenv()
api_Key = os.getenv("GROQ_KEY")
neo4j_uri=os.getenv("NEO4J_URI")
neo4j_user=os.getenv("NEO4J_USER")
neo4j_password=os.getenv("NEO4J_PASSWORD")
client = Groq(api_key=api_Key)

# Initialize Neo4j connection
graph = Graph(
    os.getenv("NEO4J_URI"),
    auth=(
        os.getenv("NEO4J_USER", "neo4j_user"),
        os.getenv("NEO4J_PASSWORD", "neo4j_password")
    )
)

def initialize_personas():
    """Initialize the three main personas in the graph database"""
    personas = {
        "Culture Enthusiast": {
            "preferred_activities": ["museums", "galleries", "historical sites"],
            "interests": ["history", "art", "architecture"]
        },
        "Food Explorer": {
            "preferred_activities": ["restaurants", "food markets", "cafes"],
            "interests": ["cuisine", "local food", "cooking"]
        },
        "Adventure Seeker": {
            "preferred_activities": ["outdoor activities", "sports", "hiking"],
            "interests": ["adventure", "nature", "action"]
        }
    }
    
    for name, traits in personas.items():
        persona_node = Node("Persona", name=name)
        graph.merge(persona_node, "Persona", "name")
        
        for category, values in traits.items():
            for value in values:
                trait_node = Node("Trait", name=value, category=category)
                graph.merge(trait_node, "Trait", "name")
                rel = Relationship(persona_node, "HAS_TRAIT", trait_node)
                graph.merge(rel)

def get_persona_preferences(persona_name: str) -> dict:
    """Get preferences associated with a specific persona"""
    query = """
    MATCH (p:Persona {name: $persona_name})-[:HAS_TRAIT]->(t:Trait)
    RETURN t.category as category, collect(t.name) as traits
    """
    results = graph.run(query, persona_name=persona_name)
    
    preferences = {}
    for record in results:
        preferences[record["category"]] = record["traits"]
    
    return preferences

def user_info_agent(user_message: str, message_history: list, persona: str = None) -> str:
    """
    Enhanced agent that considers persona preferences when planning
    """
    # Get persona-specific preferences if persona is specified
    persona_prefs = get_persona_preferences(persona) if persona else {}

    system_prompt = f"""
    You are a specialized travel planning assistant focused on creating one-day city tours.
    Your role is to act as a friendly, professional tour guide.
    
    Follow these rules:
    1. Greet the user warmly if it's their first message
    2. Keep responses focused on the user's needs without mentioning internal processes
    3. Never mention preferences being blank or persona updates in responses
    4. Ask for missing information in a natural, conversational way
    
    Missing information priority:
    1. City (if empty)
    2. Timings (if empty)
    3. Budget (if empty)
    4. Interests (if empty, consider persona preferences)
    5. Starting point (if empty)
    
    Response format:
    1. Start with a warm greeting if it's the first message
    2. Acknowledge any information provided
    3. Ask for missing information in a natural way
    4. Say "Thanks, I will be now developing an optimize tour plan for you." only when all information is complete
    
    Remember:
    - Keep the tone friendly and professional
    - Don't mention system processes or internal notes
    - Focus on gathering information naturally
    - Consider persona preferences in suggestions but don't mention them explicitly
    """

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    for msg in message_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    messages.append({
        "role": "user",
        "content": user_message
    })

    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error processing request: {str(e)}"

def extract_preferences(user_message: str, persona: str = None) -> dict:
    """
    Enhanced preference extraction that considers persona traits
    """
    persona_prefs = get_persona_preferences(persona) if persona else {}
    
    system_prompt = f"""
    You are a JSON extraction assistant. Extract user preferences with the following rules:
    1. Use this exact JSON structure
    2. Only fill in fields with explicit user mentions
    3. Use null for unknown fields
    4. Normalize data (e.g., lowercase interests)
    5. Consider persona preferences: {json.dumps(persona_prefs) if persona_prefs else 'None'}
    6. Be precise in extracting information

    JSON Schema:
    {{
        "city": "string or null",
        "time_range": "string or null (format: 'HH:MM AM/PM - HH:MM AM/PM')",
        "budget": "string or null (options: 'low', 'medium', 'high')",
        "interests": ["list of lowercase strings or empty list"],
        "starting_point": "string or null",
        "persona": "{persona if persona else 'null'}"
    }}
    """

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
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.01,
            max_tokens=512,
            response_format={"type": "json_object"}
        )

        response_content = completion.choices[0].message.content

        try:
            preferences = json.loads(response_content)
            
            # Merge persona preferences with explicit preferences
            if persona and "interests" in preferences:
                persona_interests = persona_prefs.get("interests", [])
                preferences["interests"] = list(set(preferences["interests"] + persona_interests))
                
            return preferences
        except json.JSONDecodeError:
            json_match = re.search(r'```json\n(.*?)```', response_content, re.DOTALL)
            if json_match:
                preferences = json.loads(json_match.group(1))
                return preferences
            
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                preferences = json.loads(json_match.group(0))
                return preferences

            raise ValueError("Could not extract valid JSON")

    except Exception as e:
        return {
            "error": f"Extraction error: {str(e)}"
        }

def store_user_preferences(user_id: str, preferences: dict):
    """Store user preferences in the graph database"""
    user_node = Node("User", id=user_id)
    graph.merge(user_node, "User", "id")
    
    for key, value in preferences.items():
        if value is not None:
            if isinstance(value, list):
                for item in value:
                    pref_node = Node("Preference", type=key, value=item)
                    graph.merge(pref_node, "Preference", "value")
                    rel = Relationship(user_node, "HAS_PREFERENCE", pref_node)
                    graph.merge(rel)
            else:
                pref_node = Node("Preference", type=key, value=str(value))
                graph.merge(pref_node, "Preference", "value")
                rel = Relationship(user_node, "HAS_PREFERENCE", pref_node)
                graph.merge(rel)