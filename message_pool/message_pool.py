import json

from agentverse.agents import BaseAgent
from agentverse.message import Message, CriticMessage, ExecutorMessage
from pydantic import BaseModel, Field
from typing import List, Tuple, Set, Union, Any, Dict


class MessagePool(BaseModel):
    messages: Dict[str, list[Message]] = Field(default={})
    count: int = Field(default=0)

    def add_messages(self, messages: list[Message]):
        self.count += len(messages)
        for message in messages:
            for receiver in message.receiver:
                if self.messages.get(receiver):
                    self.messages[receiver].extend(messages)
                else:
                    self.messages[receiver] = messages

    def delete_message_by_sender(self, sender: str):
        self.messages = {
            key: [message for message in message_list if message.sender != sender]
            for key, message_list in self.messages.items()
        }

    def delete_message_by_receiver(self, receiver: str):
        self.messages[receiver] = []

    def delete_message_by_id(self, id: int):
        self.messages = {
            key: [message for message in message_list if message.id != id]
            for key, message_list in self.messages.items()
        }

    def get_messages(self, receiver: str):
        available_messages = []
        if self.messages.get("all"):
            available_messages.extend(self.messages["all"])
        if self.messages.get(receiver):
            available_messages.extend(self.messages[receiver])
        return available_messages

    def to_messages(self, receiver: str = "", start_index: int = 0) -> List[dict]:
        messages = []
        for message in self.get_messages(receiver):
            if message.sender == receiver:
                if isinstance(message, ExecutorMessage):
                    if message.tool_name != "":
                        messages.append(
                            {
                                "role": "assistant",
                                "content": f"[{message.sender}]: {message.content}"
                                if message.content != ""
                                else "",
                                "function_call": {
                                    "name": message.tool_name,
                                    "arguments": json.dumps(message.tool_input),
                                },
                            }
                        )
                        continue
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"[{message.sender}]: {message.content}",
                    }
                )
                continue
            if message.sender == "function":
                messages.append(
                    {
                        "role": "function",
                        "content": message.content,
                        "name": message.tool_name,
                    }
                )
                continue
            messages.append(
                {
                    "role": "assistant",
                    "content": f"[{message.sender}]: {message.content}",
                }
            )
        return messages

    def to_string(self, receiver: str, add_sender_prefix: bool = False):
        messages = self.messages[receiver]
        if add_sender_prefix:
            return "\n".join(
                [
                    f"[{message.sender}]: {message.content}"
                    if message.sender != ""
                    else message.content
                    for message in messages
                ]
            )
        else:
            return "\n".join([message.content for message in messages])


messagePool = MessagePool()
