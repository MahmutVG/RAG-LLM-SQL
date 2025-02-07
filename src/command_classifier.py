class CommandClassifier:
    """
    Classifies SQL commands as destructive or non-destructive for PostgreSQL.
    """

    DESTRUCTIVE_COMMANDS = [
        "DROP TABLE", "DROP INDEX", "DROP SEQUENCE", "DROP VIEW",
        "DROP MATERIALIZED VIEW", "DROP DATABASE", "DROP FUNCTION",
        "TRUNCATE", "DELETE", "UPDATE", "ALTER TABLE", "ALTER SYSTEM",
        "REINDEX", "REFRESH MATERIALIZED VIEW", "VACUUM FULL",
        "RESET", "SET", "CREATE MATERIALIZED VIEW"
    ]

    NON_DESTRUCTIVE_COMMANDS = [
        "SELECT", "WITH", "EXPLAIN", "ANALYZE", "SHOW", "LISTEN",
        "NOTIFY", "SELECT INTO", "SET LOCAL", "ROLLBACK", "SAVEPOINT",
        "BEGIN", "COMMIT", "COPY", "CREATE INDEX", "CREATE FUNCTION",
        "CREATE SEQUENCE", "CREATE TABLE", "CREATE VIEW", "CREATE DATABASE"
    ]

    @staticmethod
    def is_destructive(command: str) -> bool:
        """
        Determines if a given SQL command is destructive.
        """
        command_upper = command.strip().upper()
        for destructive_cmd in CommandClassifier.DESTRUCTIVE_COMMANDS:
            if command_upper.startswith(destructive_cmd):
                return True
        return False
