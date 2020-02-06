from yandex_types import YandexRequest, \
    YandexResponse, construct_yandex_response_from_yandex_request
import sys
import inspect
import random


class DialogIntent:
    """
    Represents users intention. Whether he wants to add food or delete it or
    to learn what he ate
    """
    time_to_evaluate: int  # How many units is needed to
    # check if user's request fits this intent. (Query database, check context,
    # etc)
    time_to_respond: int  # How many units is needed to respond (clear
    # context, write context, query database, etc)
    name: str  # Intent name
    description: str  # Intent description

    @staticmethod
    def evaluate(*, request: YandexRequest, **kwargs) -> int:
        raise NotImplemented

    @staticmethod
    def respond(request: YandexRequest, **kwargs) -> YandexResponse:
        raise NotImplemented


class IntentStartingMessage(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 0
    name = 'Первое сообщение'
    description = 'Когда пользователь только открывает навык, ' \
                  'ему следует написать приветственное сообщение'

    @staticmethod
    def evaluate(*, request: YandexRequest, **kwargs) -> int:
        if request.is_new_session:
            return 100
        else:
            return 0

    @staticmethod
    def respond(request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Привет. Скажите что вы съели, '
                     'а я скажу сколько там калорий',
        )


class IntentDefault(DialogIntent):
    """
    WARNING! This class should always be the last in the file
    This a default response in none of above fit
    """
    time_to_evaluate = 0
    time_to_respond = 0
    name = 'Дефолтный ответ'
    description = 'Если ничего не подошло, ' \
                  'отвечаем пользователю что не знаем такой еды'

    @staticmethod
    def evaluate(*, request: YandexRequest, **kwargs) -> int:
        return 100

    @staticmethod
    def respond(request: YandexRequest, **kwargs) -> YandexResponse:
        first_parts_list = [
            'Это не похоже на название еды. Попробуйте сформулировать иначе',
            'Хм. Не могу понять что это. Попробуйте сказать иначе',
            'Такой еды я пока не знаю. Попробуйте сказать иначе',
        ]

        food_examples_list = ['Бочка варенья и коробка печенья',
                              'Литр молока и килограмм селедки',
                              '2 куска пиццы с ананасом',
                              '200 грамм брокколи и 100 грамм шпината',
                              'ананас и рябчик',
                              '2 блина со сгущенкой',
                              'тарелка риса, котлета и стакан апельсинового '
                              'сока',
                              'банан, апельсин и манго',
                              'черная икра, красная икра, баклажанная икра',
                              'каша из топора и свежевыжатый березовый сок',
                              ]

        full_generated_text = f"{random.choice(first_parts_list)}, " \
                              f"например: " \
                              f"{random.choice(food_examples_list)}. " \
                              f"Чтобы выйти, скажите Выход"

        if request.has_screen:
            tts = "Попробуйте сказать иначе"
        else:
            tts = full_generated_text

        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=full_generated_text,
                tts=tts,
                buttons=[],
                end_session=False,
                should_clear_context=False
        )


def intents() -> list:
    intents_to_return = []
    for class_name, cl in inspect.getmembers(
            sys.modules[__name__],
            inspect.isclass):
        if class_name in ('DialogIntent', 'YandexRequest', 'YandexResponse'):
            continue
        intents_to_return.append(cl)
    return intents_to_return


if __name__ == '__main__':
    print(intents())
