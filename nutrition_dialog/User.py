from dataclasses import dataclass
from typing import Optional


@dataclass()
class User:
    """
    This class will store all user data like weigt, age, kalories limit etc.
    Information to be stored withing Alice sessions
    """
    id: str  # Mandatory id got from Yandex request
    authentificated: bool  # is authentificated with Yandex passport. If
    # there is session -> user -> user_id in request, that means that user
    # authentificated and we can save data for him.
    log_hash: str  # temporary number to use with logs
    name: Optional[str] = None  # User's name, maybe will be filled later
    time_saw_link_to_vote: Optional[str] = None  # last time user was
    # prompted to vote for the skill
    kalories_limit: Optional[float] = None  # how many calories are allowed
