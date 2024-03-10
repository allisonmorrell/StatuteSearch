

settings = {
    "model": "gpt-3.5-turbo",
    "temperature": .7
}


class Conversation():
    def __init__(self, settings=settings):
        self.messages = []
        self.settings = settings

    def add_message(self, role, content, name=None):
        message = {"role": role, "content": content}
        if name:
            message["name"] = name
        self.messages.append(message)

    def delete_last(self):
        self.messages.pop()

    def display_all(self):
        for message in self.messages:
            print(f"{message['role']}:  {message['content']}\n")

    def display_latest(self):
        message = self.messages[-1]
        print(f"{message['role']}:  {message['content']}\n")

