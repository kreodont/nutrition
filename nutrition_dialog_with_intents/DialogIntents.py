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
    should_save_context: bool  # Whether we need to save context for future
    # use. Costs 10 units (database write operation)
    should_clear_context: bool  # Whether clear previous context. Costs 10

    # units (database write operation)

    @staticmethod
    def evaluate(*, request: YandexRequest, **kwargs) -> int:
        raise NotImplemented

    @staticmethod
    def respond(request: YandexRequest, **kwargs) -> YandexResponse:
        raise NotImplemented


class Intent00001StartingMessage(DialogIntent):
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


class Intent00002Ping(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 0
    name = 'Ответ на пинг'
    description = 'Яндекс пингует навык каждую минуту. Отвечаем понг'

    @staticmethod
    def evaluate(*, request: YandexRequest, **kwargs) -> int:
        full_phrase = request.original_utterance
        if full_phrase.lower() in ('ping', 'пинг'):
            return 100
        return 0

    @staticmethod
    def respond(request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='pong',
        )


class Intent00003TextTooLong(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 0
    name = 'Текст слишком длинный'
    description = 'Мы будем отбрасывать длинные запросы, ' \
                  'потому что не хватит времени найти на них ответ. ' \
                  'Слово удали - исключение, потому что пользователь может ' \
                  'захотеть удалить длинную предыдущую фразу'

    @staticmethod
    def evaluate(*, request: YandexRequest, **kwargs) -> int:
        if (len(request.original_utterance) >= 100 and
                'удали' not in request.original_utterance):
            return 100
        return 0

    @staticmethod
    def respond(request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Ой, текст слишком длинный. Давайте попробуем частями?',
        )


class Intent00004Help(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Текст помощи'
    should_clear_context = True
    description = 'Объясняем пользователю как работает навык'

    @staticmethod
    def evaluate(*, request: YandexRequest, **kwargs) -> int:
        tokens = request.tokens
        if ('помощь' in tokens or
                'справка' in tokens or
                'хелп' in tokens or
                'информация' in tokens or
                'ping' in tokens or
                'пинг' in tokens or
                'умеешь' in tokens or
                ('что' in tokens and [t for t in tokens if 'делать' in t]) or
                ('что' in tokens and [t for t in tokens if 'умеешь' in t]) or
                ('как' in tokens and [t for t in tokens if 'польз' in t]) or
                'скучно' in tokens or 'help' in tokens):
            return 100
        return 0

    @staticmethod
    def respond(request: YandexRequest, **kwargs) -> YandexResponse:
        help_text = '''Я считаю калории. Просто скажите что вы съели, 
        а я скажу сколько в этом было калорий. Например: соевое молоко с 
        хлебом. Потом я спрошу надо ли сохранить этот прием пищи, и если вы 
        скажете да, я запишу его в свою базу данных. Можно сказать не просто 
        да, а указать время приема пищи, например: да, вчера в 9 часов 
        30 минут. После того, как прием пищи сохранен, вы сможете узнать свое 
        суточное потребление калорий с помощью команды "что я ела?". При этом 
        также можно указать время, например: "Что я ел вчера?" или "Что я ела 
        неделю назад?". Если какая-то еда была внесена ошибочно, 
        можно сказать "Удалить соевое молоко с хлебом".  Прием пищи 
        "Соевое молоко с хлебом" будет удален'''
        return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=help_text,
        )


class Intent99999Default(DialogIntent):
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
    print(sys.modules[__name__])
    print(intents())
