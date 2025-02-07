import json
from pydantic import BaseModel
import openai
import logging
from embedding_manager import EmbeddingManager

from database_assistant import DatabaseAssistant
from chat_history import ChatHistory

sql_response_schema = {
    "type": "object",
    "properties": {
        "sql_command": {
            "type": "string",
            "description": "The SQL query generated based on the user request and context."
        },
        "reasoning": {
            "type": "string",
            "description": "The reasoning behind the SQL query design, explaining how it satisfies the user request."
        }
    },
    "required": ["sql_command", "reasoning"]
}
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "sql_generation_response",
        "description": "Response format for SQL query generation with reasoning.",
        "schema": sql_response_schema,
        "strict": True  # Ensures strict adherence to the schema
    }
}
class SQLExpert:
    """
    SQLExpert handles query refinement, context retrieval, and SQL query generation.
    """

    def __init__(
            self,
            embedding_manager: EmbeddingManager,
            database_assistant: DatabaseAssistant,
            chat_history: ChatHistory,
            model="llama-3-sqlcoder-8b",
            api_key="not-needed"):
        self.client = openai.OpenAI(base_url="http://localhost:1234/v1", api_key=api_key)
        self.model = model
        self.embedding_manager = embedding_manager
        self.database_assistant = database_assistant
        self.chat_history = chat_history
        self.context = None

    def refine_and_generate_sql(self, user_query: str) -> str:
        """
        Refines the user query, retrieves relevant context, and generates an SQL query.
        """
        try:
            context_changed = False
            if self.context is None:
                self.context, distances = self.embedding_manager.search(user_query, top_k=3)
                context_changed = True
            else:
                change_context = input("Do you want to change the context? (yes/no): ").strip().lower()
                if change_context == "yes":
                    self.context,distances = self.embedding_manager.search(user_query, top_k=3)
                    context_changed = True
                else:
                    self.chat_history.add_message(
                        "system",
                        "The user indicated that the last assistant response was incorrect, requires adjustments, or needs to address a related request. Please generate a new response, ensuring the user's suggestions or subsequent requests are incorporated."
                    )

            sql_prompt = user_query

            if context_changed:
                context_texts = []
                for ctx in self.context:
                    context_texts.append(f"{ctx['query']} {ctx['answer']} {ctx['question']}")
                context_text = "\n".join(context_texts)
                sql_prompt = (
                    f"Write an SQL query based on the context and schema provided. Ensure accuracy with table and column names.\n\n"
                    f"Context:\n{context_text}\n\n"
                    f"Request:\n{sql_prompt}\n\n"
                    f"Notes:\n"
                    f"- Verify the schema before generating the query.\n"
                    f"- Use proper joins, filters, and aggregations if required.\n"
                    f"- Ensure the output is valid JSON.\n"
                    f"- JSON Format:\n"
                    f"{{\n"
                    f'  "sql_command": "<SQL query>",\n'
                    f'  "reasoning": "<Reason for the SQL query design>"\n'
                    f"}}\n"
                    f"- Reasoning should explain how the query satisfies the user request.\n"
                )


            messages = self.chat_history.get_history()
            self.chat_history.add_message("user", user_query)
            messages.append({"role": "user", "content":sql_prompt}) # this is for seperating extended context and user query
            sql_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.4,
                max_tokens=400,
                top_p=0.9,
                response_format=response_format
            )
            sql_dict = json.loads(sql_response.choices[0].message.content)
            

            sql_query = sql_dict.get("sql_command")
            reasoning = sql_dict.get("reasoning")
            return reasoning, sql_query

        except Exception as e:
            logging.error("Error during query processing: %s", e)
            return "Could not process the query. Please try again."