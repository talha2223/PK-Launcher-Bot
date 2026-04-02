from dataclasses import dataclass

@dataclass
class SharedState:
    users: int = 0

    def __init__(self, default_users: int = 0):
        self.users = default_users
