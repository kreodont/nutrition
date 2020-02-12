class DialogContext:
    """
    For saving dialog context into database
    """
    data_dict: dict
    is_empty: bool
    contains_food: bool  # if it is food context
    intent_originator: object  # one of the intents classes

    def __init__(self,
                 *,
                 data=None,
                 is_empty: bool = True,
                 contains_food: bool = False,
                 intent_originator: object = None,
                 ):
        if data is None:
            data = {}
        self.data_dict = data
        self.is_empty = is_empty
        self.contains_food = contains_food
        self.intent_originator = intent_originator
