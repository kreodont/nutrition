class DialogContext:
    """
    For saving dialog context into database
    """
    food_dict: dict  # Food nutrition data
    intent_originator_name: str  # name of the intent who asked the
    # specifying question
    user_initial_phrase: str  # initial user request that lead to context saving
    specifying_question: str  # the question that was asked
    matching_intents_names: tuple  # List of intents names that fit as answers

    def __init__(self,
                 *,
                 food_dict=None,
                 intent_originator_name: str,
                 user_initial_phrase: str,
                 specifying_question: str,
                 matching_intents_names: tuple
                 ):
        if food_dict is None:
            food_dict = {}
        self.food_dict = food_dict
        self.intent_originator_name = intent_originator_name
        self.user_initial_phrase = user_initial_phrase
        self.specifying_question = specifying_question
        self.matching_intents_names = matching_intents_names

    def __repr__(self):
        return f'В ответ на фразу пользователя "{self.user_initial_phrase}" ' \
               f'интент "{self.intent_originator_name}" задал уточняющий ' \
               f'вопрос "{self.specifying_question}". Предполагаемые ' \
               f'допустимые ответные интенты: {self.matching_intents_names}'

    @staticmethod
    def empty_context():
        """
        To have the possibility to have empty context and not try to load it
        again
        :return:
        """
        return DialogContext(
                food_dict={},
                intent_originator_name='Empty context',
                user_initial_phrase='Empty context',
                matching_intents_names=(),
                specifying_question='Empty context',
        )
