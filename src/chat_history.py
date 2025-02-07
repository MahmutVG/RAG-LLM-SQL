class ChatHistory:
    """
    Manages the chat history for interaction between the user and the system.
    """

    def __init__(self):
        self._history = ["placeholder"]

    def add_message(self, role, content):
        """
        Adds a message to the chat history.
        """
        self._history.append({"role": role, "content": content})
    
    def update_message(self, index, role, content):
        """
        Updates a message in the chat history.
        """
        self._history[index] = {"role": role, "content": content}

    def get_formatted_history(self):
        """
        Returns a formatted string of the chat history for better readability, excluding system messages.
        """
        return "\n".join(f"{item['role'].upper()}: {item['content']}" for item in self.get_history() if item['role'] != 'system')

    def get_history(self):
        """
        Returns a copy of the chat history.
        """
        return self._history.copy()