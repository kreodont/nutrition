class DialogContext:
    """
    For saving dialog context into database
    """
    data_dict: dict
    is_empty: bool
    contains_food: bool
    dialog_intent_name: str  # Intent that saved the context

    def __init__(self,
                 *,
                 data=None,
                 is_empty: bool = True,
                 contains_food: bool = False):
        if data is None:
            data = {}
        self.data_dict = data
        self.is_empty = is_empty
        self.contains_food = contains_food
