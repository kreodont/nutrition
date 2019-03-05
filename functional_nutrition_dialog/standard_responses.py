import random
import typing
from yandex_types import YandexRequest, YandexResponse
from responses_constructors import \
    construct_yandex_response_from_yandex_request, respond_request


def is_help_request(request: YandexRequest):
    tokens = request.tokens
    if (
            'помощь' in tokens or
            'справка' in tokens or
            'хелп' in tokens or
            'информация' in tokens or
            'ping' in tokens or
            'пинг' in tokens or
            'умеешь' in tokens or
            ('что' in tokens and [t for t in tokens if 'делать' in t]) or
            ('что' in tokens and [t for t in tokens if 'умеешь' in t]) or
            ('как' in tokens and [t for t in tokens if 'польз' in t]) or
            'скучно' in tokens or
            'help' in tokens):
        return True
    return False


def respond_help(request: YandexRequest) -> YandexResponse:
    help_text = 'Я считаю калории. Просто скажите что вы съели, а я скажу ' \
                'сколько в этом было калорий. Например: соевое молоко с ' \
                'хлебом. Потом я спрошу надо ли сохранить этот прием пищи, и ' \
                'если вы скажете да, я запишу его в свою базу данных. Можно ' \
                'сказать не просто да, а указать время приема пищи, ' \
                'например: да, вчера в 9 часов 30 минут. После того, как ' \
                'прием пищи сохранен, вы сможете узнать свое суточное ' \
                'потребление калорий с помощью команды "что я ел(а)?". ' \
                'При этом также можно указать время, например: "Что я ел ' \
                'вчера?" или "Что я ела неделю назад?". Если какая-то еда ' \
                'была внесена ошибочно, можно сказать "Удалить соевое ' \
                'молоко с хлебом".  Прием пищи "Соевое молоко с хлебом" ' \
                'будет удален'

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=help_text,
            tts=help_text,
            end_session=False,
            buttons=[],
    )


def is_thanks_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in (
            'спасибо', 'молодец', 'отлично', 'ты классная', 'классная штука',
            'классно', 'ты молодец', 'круто', 'обалдеть', 'прикольно',
            'клево', 'ништяк'):
        return True
    return False


def respond_thanks(request: YandexRequest) -> YandexResponse:
    welcome_phrases = [
        'Спасибо, я стараюсь',
        'Спасибо за комплимент',
        'Приятно быть полезной',
        'Доброе слово и боту приятно']
    chosen_welcome_phrase = random.choice(welcome_phrases)
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=chosen_welcome_phrase,
            tts=chosen_welcome_phrase,
            end_session=False,
            buttons=[],
    )


def is_hello_request(request: YandexRequest):
    tokens = request.tokens
    if (
            'привет' in tokens or
            'здравствуй' in tokens or
            'здравствуйте' in tokens or
            'хелло' in tokens or
            'hello' in tokens or
            'приветик' in tokens
    ):
        return True
    return False


def is_human_meat_request(request: YandexRequest):
    tokens = request.tokens
    full_phrase = request.original_utterance
    if [t for t in tokens if 'человеч' in t] or \
            tokens == ['мясо', 'человека'] or \
            full_phrase in ('человек',):
        return True
    return False


def respond_human_meat(request: YandexRequest) -> YandexResponse:
    respond_string = 'Доктор Лектер, это вы?'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def respond_hello(request: YandexRequest) -> YandexResponse:
    respond_string = 'Здравствуйте. А теперь расскажите что вы съели, а я ' \
                     'скажу сколько там было калорий и питательных веществ.'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_goodbye_request(request: YandexRequest):
    tokens = request.tokens
    full_phrase = request.original_utterance
    if (
            'выход' in tokens or
            'выйти' in tokens or
            'пока' in tokens or
            'выйди' in tokens or
            'до свидания' in full_phrase.lower() or
            'всего доброго' in full_phrase.lower() or
            tokens == ['алиса', ] or
            full_phrase in ('иди на хуй', 'стоп')

    ):
        return True
    return False


def respond_goodbye(request: YandexRequest) -> YandexResponse:
    respond_string = 'До свидания'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=True,
            buttons=[],
    )


def is_eat_cat_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('кошка', 'кошку', 'кот', 'кота', 'котенок', 'котенка'):
        return True
    return False


def respond_eat_cat(request: YandexRequest) -> YandexResponse:
    respond_string = 'Нееш, падумой'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_eat_poop_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('говно', 'какашка', 'кака', 'дерьмо',
                       'фекалии', 'какахе', 'какахи'):
        return True
    return False


def respond_eat_poop(request: YandexRequest) -> YandexResponse:
    respond_string = 'Вы имели в виду "Сладкий хлеб"?'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_i_think_too_much_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('это много', 'это мало', 'что-то много',
                       'что-то мало', 'так много'):
        return True
    return False


def respond_i_think_too_much(request: YandexRequest) -> YandexResponse:
    respond_string = 'Если вы нашли ошибку, напишите моему разработчику, ' \
                     'и он объяснит мне, как правильно'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_dick_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('хуй', 'моржовый хуй', 'хер'):
        return True
    return False


def respond_dick(request: YandexRequest) -> YandexResponse:
    respond_string = 'С солью или без соли?'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_nothing_to_add_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('никакую', 'ничего', 'никакой'):
        return True
    return False


def respond_nothing_to_add(request: YandexRequest) -> YandexResponse:
    respond_string = 'Хорошо, дайте знать, когда что-то появится'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_what_is_your_name_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('как тебя зовут', 'как вас зовут',
                       'а как тебя зовут', 'а как твое имя'):
        return True
    return False


def respond_what_is_your_name(request: YandexRequest) -> YandexResponse:
    respond_string = 'Я умный счетчик калорий, а имя мне пока не придумали. ' \
                     'Может, Вы придумаете?'

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def check_if_help_in_request(*, request: YandexRequest) -> bool:
    tokens = request.tokens
    if (
            'помощь' in tokens or
            'справка' in tokens or
            'хелп' in tokens or
            'информация' in tokens or
            'ping' in tokens or
            'пинг' in tokens or
            'умеешь' in tokens or
            ('что' in tokens and [t for t in tokens if 'делать' in t]) or
            ('что' in tokens and [t for t in tokens if 'умеешь' in t]) or
            ('как' in tokens and [t for t in tokens if 'польз' in t]) or
            'скучно' in tokens or
            'help' in tokens):
        return True

    return False


def respond_one_of_predefined_phrases(
        request: YandexRequest) -> typing.Optional[YandexResponse]:
    # Respond long phrases
    if len(request.original_utterance) >= 100:
        return respond_request(
                request=request,
                responding_function=respond_text_too_long)

    # Respond help requests
    if check_if_help_in_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_help)

    if is_thanks_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_thanks)

    if is_hello_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_hello)

    if is_goodbye_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_goodbye)

    if is_human_meat_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_human_meat)

    if is_eat_cat_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_eat_cat)

    if is_eat_poop_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_eat_poop)

    if is_i_think_too_much_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_i_think_too_much)

    if is_dick_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_dick)

    if is_nothing_to_add_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_nothing_to_add)

    if is_what_is_your_name_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_what_is_your_name)


def respond_text_too_long(request: YandexRequest) -> YandexResponse:
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Ой, текст слишком длинный. Давайте попробуем частями?',
            tts='Ой, текст слишком длинный. Давайте попробуем частями?',
            end_session=False,
            buttons=[],
    )
