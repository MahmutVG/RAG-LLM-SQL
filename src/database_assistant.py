from typing import Dict, Any
import psycopg2
from psycopg2 import sql
import logging
from command_classifier import CommandClassifier

class DatabaseAssistant:
    """
    DatabaseAssistant handles the connection to the PostgreSQL database and executes queries.
    """

    def __init__(self):
        self.conn = None
        self.cursor = None
        self.schema = {}

    def connect(self, db_params):
        """
        Connects to the PostgreSQL database using the provided parameters.
        """
        try:
            self.conn = psycopg2.connect(**db_params)
            self.cursor = self.conn.cursor()
            self.update_schema()
            return "Connection successful!"
        except Exception as e:
            logging.error("Error connecting to the database: %s", e)
            return "Failed to connect to the database. Please check the parameters and try again."

    def update_schema(self):
        """
        Retrieves and updates the database schema information.
        """
        try:
            self.cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            tables = self.cursor.fetchall()
            schema = {}
            for table in tables:
                table_name = table[0]
                self.cursor.execute(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                """)
                columns = self.cursor.fetchall()
                schema[table_name] = {col[0]: col[1] for col in columns}

                self.cursor.execute(f"""
                    SELECT
                        tc.constraint_name, 
                        kcu.column_name, 
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name 
                    FROM 
                        information_schema.table_constraints AS tc 
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                    WHERE constraint_type = 'FOREIGN KEY' AND tc.table_name='{table_name}';
                """)
                foreign_keys = self.cursor.fetchall()
                schema[table_name]['foreign_keys'] = [
                    {
                        'column': fk[1],
                        'foreign_table': fk[2],
                        'foreign_column': fk[3]
                    } for fk in foreign_keys
                ]
            self.schema = schema
        except Exception as e:
            logging.error("Error retrieving schema information: %s", e)

    def execute_query(self, sql_query: str, params: Dict = None):
        """
        Executes the given SQL query on the connected database using psycopg2.sql for safety.
        """
        try:
            if CommandClassifier.is_destructive(sql_query):
                confirmation = input("This is a destructive operation. Are you sure you want to proceed? (yes/no): ").strip().lower()
                if confirmation != "yes":
                    return "Query execution aborted by the user."

            # Use psycopg2.sql for safe query execution
            if params:
                query = sql.SQL(sql_query).format(**{
                    key: sql.Identifier(value) if isinstance(value, str) else sql.Literal(value)
                    for key, value in params.items()
                })
                self.cursor.execute(query)
            else:
                self.cursor.execute(sql.SQL(sql_query))

            self.conn.commit()

            # Fetch and print the results if the query has output
            if self.cursor.description:
                rows = self.cursor.fetchall()
                for row in rows:
                    print(row)

            return "Query executed successfully."
        except Exception as e:
            logging.error("Error executing query: %s", e)
            return "Failed to execute query."

    def close_connection(self):
        """
        Closes the database connection.
        """
        if self.conn:
            self.cursor.close()
            self.conn.close()