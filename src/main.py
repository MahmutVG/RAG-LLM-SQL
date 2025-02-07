import json
from embedding_manager import EmbeddingManager
from sql_expert import SQLExpert
from chat_history import ChatHistory
from database_assistant import DatabaseAssistant
import time

def handle_user_input(user_input: str, sql_expert: SQLExpert, chat: ChatHistory, db_assistant: DatabaseAssistant):
    """
    Handles user input: refines the query, generates SQL, and updates chat history.
    """
    if not user_input.strip():
        return "Input cannot be empty.", ""

    db_assistant.update_schema()
    chat.update_message(0, "system", f"You are an SQL expert and this is postgresql database schema: {json.dumps(db_assistant.schema, indent=2)}. Always remember to check the schema before generating SQL queries.")
    # Refine and generate SQL query
    reasoning, sql_query = sql_expert.refine_and_generate_sql(user_input)
    
    chat.add_message("assistant", f"Reasoning: {reasoning} SQL Query: {sql_query}")
    print(f"\nSQL Query: {sql_query}")

    execute = input("Do you want me to execute the query? (yes/no): ").strip().lower()
    if execute == "yes":
        result = db_assistant.execute_query(sql_query)  # Pass params if applicable
        print(f"\nExecution Result: {result}")

    return sql_query


def main():
    """
    Main function for running the Database Assistant application.
    """
    api_key = "not_needed"  # Replace with your OpenAI API key
    embedding_manager = EmbeddingManager()
    db_assistant = DatabaseAssistant()
    chat = ChatHistory()
    sql_expert = SQLExpert(embedding_manager=embedding_manager, database_assistant=db_assistant, api_key=api_key, chat_history=chat)

    print("Welcome to the Database Assistant!\n")

    # Ask if user wants to extend knowledge base
    extend_prompt = input("Do you want to extend the knowledge base? (yes/no): ").strip().lower()
    if extend_prompt == "yes":
        embedding_manager.extend_knowledge_base()

    # Connect to the database
    retry_interval = 5
    max_retries = 12
    retries = 0

    while retries < max_retries:
        db_params = {
            "host": "localhost",
            "dbname": "deprem",
            "user": "postgres",
            "password": "bilgem",
            "port": 5433
        }
        connection_message = db_assistant.connect(db_params)
        print(connection_message)
        
        if connection_message == "Connection successful!":
            break
        
        retries += 1
        print(f"Retrying in {retry_interval} seconds... ({retries}/{max_retries})")
        time.sleep(retry_interval)
    else:
        print("Failed to connect to the database after multiple attempts.")
        return

    # Main interaction loop
    while True:
        user_input = input("Enter your SQL problem or type 'exit' to quit: ")
        if user_input.lower() in ["exit", "quit"]:
            db_assistant.close_connection()
            print("Goodbye!")
            break

        handle_user_input(user_input, sql_expert, chat, db_assistant)

        print("\nChat History:")
        print(chat.get_formatted_history())
        print("\n" + "=" * 50)

if __name__ == "__main__":
    main()