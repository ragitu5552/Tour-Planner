# One-Day Tour Planning Assistant

This project implements an intelligent one-day tour planning assistant that dynamically adjusts to user preferences through a chat-based interface. It personalizes itinerary suggestions based on user inputs, remembers preferences across conversations, and adapts seamlessly to evolving requirements.

## Features
- Personalized itinerary suggestions tailored to user preferences.
- Memory management using **LLM-generated triplets** stored in a **Neo4j graph database**.
- Real-time dynamic updates to the itinerary based on user feedback.
- Supports at least three distinct user personas with unique preferences.

## How to Run

### 1. Install Dependencies
Ensure you have Python installed. Create a virtual environment and install the required dependencies:

```bash
pip install -r requirements.txt

