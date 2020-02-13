from DialogContext import DialogContext
from yandex_types import YandexRequest, \
    YandexResponse, construct_yandex_response_from_yandex_request
import sys
import inspect
import random
from dynamodb_functions import fetch_context_from_dynamo_database, \
    get_dynamo_client, get_from_cache_table
import typing


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
    should_save_context: bool = False  # Whether we need to save
    # context for future use. Costs 10 units (database WRITE operation)
    should_clear_context: bool = False  # Whether clear previous context.
    # Costs 10 units (database DELETE operation)
    should_read_context: bool = False  # Whether read context

    # from database. Costs 100 units (database READ)

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        raise NotImplemented

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        raise NotImplemented


class Intent00001StartingMessage(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Clear context
    should_clear_context = True
    name = 'Первое сообщение'
    description = 'Когда пользователь только открывает навык, ' \
                  'ему следует написать приветственное сообщение'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        if request.is_new_session:
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, request: YandexRequest, **kwargs) -> YandexResponse:
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

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance
        if full_phrase.lower() in ('ping', 'пинг'):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
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

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        if (len(request.original_utterance) >= 100 and
                'удали' not in request.original_utterance):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
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

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        tokens = request.tokens
        if ('помощь' in tokens or
                'справка' in tokens or
                'хелп' in tokens or
                'информация' in tokens or
                'умеешь' in tokens or
                ('что' in tokens and [t for t in tokens if 'делать' in t]) or
                ('что' in tokens and [t for t in tokens if 'умеешь' in t]) or
                ('как' in tokens and [t for t in tokens if 'польз' in t]) or
                'скучно' in tokens or 'help' in tokens):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
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


class Intent00005ThankYou(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Ответ на благодарность'
    should_clear_context = True
    description = 'Если пользователь похвалил навык, надо сказать ему спасибо'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        if request.original_utterance.lower().strip() in (
                'спасибо', 'молодец', 'отлично', 'ты классная',
                'классная штука',
                'классно', 'ты молодец', 'круто', 'обалдеть', 'прикольно',
                'клево', 'ништяк', 'класс'):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        answers = [
            'Спасибо, я стараюсь',
            'Спасибо за комплимент',
            'Приятно быть полезной',
            'Доброе слово и боту приятно']
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=random.choice(answers),
        )


class Intent00006Hello(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Ответ на приветствие'
    should_clear_context = True
    description = 'Если пользователь сказал Привет, надо ' \
                  'сказать ему привет в ответ'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        if request.original_utterance.lower().strip() in (
                'привет', 'здравствуй', 'здравствуйте', 'хелло',
                'приветик', 'hello',):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Здравствуйте. А теперь '
                     'расскажите что вы съели, а я '
                     'скажу сколько там было калорий и питательных веществ.',
        )


class Intent00007HumanMeat(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Ответ на человечину'
    should_clear_context = True
    description = 'Если пользователь сказал что он поел ' \
                  'человечины, надо спросить его не доктор ли он Лектер'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        tokens = request.tokens
        full_phrase = request.original_utterance
        if [t for t in tokens if 'человеч' in t] or \
                tokens == ['мясо', 'человека'] or \
                full_phrase.lower() in ('человек',):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Доктор Лектер, это вы?',
        )


class Intent00008Goodbye(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'До свидания'
    should_clear_context = True
    description = 'Если пользователь попрощался, надо сказать ему до ' \
                  'свидания и закрыть навык'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        tokens = request.tokens
        full_phrase = request.original_utterance
        if (
                'выход' in tokens or
                'выйти' in tokens or
                'выйди' in tokens or
                'до свидания' in full_phrase.lower() or
                'всего доброго' in full_phrase.lower() or
                full_phrase in ('иди на хуй', 'стоп', 'пока', 'алиса')

        ):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='До свидания',
                end_session=True,
        )


class Intent00009EatCat(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Съел кота'
    should_clear_context = True
    description = 'Если пользователь говорит что съел кота, ' \
                  'надо предложить ему падумоть'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance
        if full_phrase in ('кошка', 'кошку', 'кот',
                           'кота', 'котенок', 'котенка'):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Нееш, падумой',
        )


class Intent00010LaunchAgain(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Повторный запуск'
    should_clear_context = True
    description = 'Если пользователь уже в навыке, но ' \
                  'просит Алису его запустить'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance
        if full_phrase.lower().strip() in (
                'запусти навык умный счетчик калорий',
                'запустить навык умный счетчик калорий',
                'алиса запусти умный счетчик калорий',
                'запустить умный счетчик калорий',
                'запусти умный счетчик калорий',
                '',
        ):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Какую еду записать?',
        )


class Intent00011EatPoop(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Съел какаху'
    should_clear_context = True
    should_save_context = True
    description = 'Почему-то пользователи иногда любят заявлять что съели ' \
                  'говно. Что ж, сделаем отсылку к Зеленому Слонику'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance.lower()
        if full_phrase in ('говно', 'какашка', 'кака', 'дерьмо',
                           'фекалии', 'какахе', 'какахи', 'какаха', 'какаху'):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        if 'answer' in kwargs and kwargs['answer'] == 'Intent00022Agree':
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text='Извини, братишка, сегодня не принес покушать',
                    should_clear_context=True)

        specifying_question = 'Вы имели в виду "Сладкий хлеб"?'
        context = DialogContext(
                intent_originator_name=cls.__name__,
                matching_intents_names=('Intent00022Agree',),
                specifying_question=specifying_question,
                user_initial_phrase=request.original_utterance)

        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=specifying_question,
                new_context_to_write=context,
        )


class Intent00012ThinkTooMuch(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Кажется, слишком много'
    should_clear_context = True
    description = 'Пользователь думает что навык насчитал слишком много ' \
                  'калорий. Попросим его написать мне'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance.lower()
        if full_phrase in ('это много', 'это мало', 'что-то много',
                           'что-то мало', 'так много', 'а почему так много',
                           'неправильно', 'мало', "маловато",):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Если вы нашли ошибку, напишите моему разработчику, '
                     'и он объяснит мне, как правильно',
        )


class Intent00013Dick(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Съел МПХ'
    should_clear_context = True
    description = 'Пользователь говорит что съел член. Спросим, с солью или без'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance.lower()
        if full_phrase in ('хуй', 'моржовый хуй', 'хер', 'хуй моржовый'):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='С солью или без соли?',
        )


class Intent00014NothingToAdd(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Не надо мне никакой еды'
    should_clear_context = True
    description = 'На вопрос какую еду записать, пользователь отвечает что ' \
                  'никакой не надо'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance.lower()
        if full_phrase in ('никакую', 'ничего', 'никакой'):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Хорошо, дайте знать, когда что-то появится',
        )


class Intent00015WhatIsYourName(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Как тебя зовут?'
    should_clear_context = True
    description = 'Пользователь спрашивает как зовут счетчика'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        tokens = request.tokens
        if 'как' in tokens and ('зовут' in tokens or 'имя' in tokens):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Я умный счетчик калорий, а имя мне пока не придумали. '
                     'Может, Вы придумаете?',
        )


class Intent00016CalledAgain(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Обращение к навыку из навыка'
    should_clear_context = True
    description = 'Пользователь внутри навыка снова говорит "Умный счетчик ' \
                  'калорий". Нужно дать ему знать, что мы его все еще слушаем'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance
        if full_phrase in ('умный счетчик калорий',):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Да, я слушаю',
        )


class Intent00017WhereIsSaved(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Куда ты сохраняешь?'
    should_clear_context = True
    description = 'Пользователь может спросить куда сохраняются данные'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance
        if full_phrase in ('а где сохраняются', 'где сохраняются',
                           'где сохранить', 'а зачем сохранять',
                           'зачем сохранять', 'куда', 'а куда сохранила'):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Приемы пищи сохраняются в моей базе данных. Ваши приемы '
                     'пищи будут доступны только Вам. Я могу быть Вашим личным '
                     'дневником калорий',
        )


class Intent00018Angry(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Пользователь злится'
    should_clear_context = True
    description = 'Пользователь ругает навык'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance
        if full_phrase in (
                'дура', 'дурочка', 'иди на хер', 'пошла нахер', 'тупица',
                'идиотка', 'тупорылая', 'тупая', 'ты дура', 'плохо'):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Все мы можем ошибаться. Напишите моему разработчику, '
                     'а он '
                     'меня накажет и научит больше не ошибаться.',
        )


class Intent00019NotImplemented(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Эта функция пока не реализована'
    should_clear_context = True
    description = 'Пользователь запросил функцию, которая пока не ' \
                  'реализована, но у меня в планах она есть'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance.lower()
        tokens = request.tokens
        if full_phrase in ('норма калорий',
                           'сколько я набрала калорий',
                           'сколько я набрал калорий',
                           'сколько в день нужно калорий',
                           'норма потребления',
                           'сколько нужно съесть калорий в день',
                           'дневная норма калорий',
                           'сколько калорий можно употреблять в сутки',
                           'сколько калорий в день можно'
                           ) or 'норма' in tokens:
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Этого я пока не умею, но планирую скоро научиться. '
                     'Следите за обновлениями',
        )


class Intent00020UseAsAlice(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Обращение к Алисе'
    should_clear_context = True
    description = 'Пользователь думает что говорит с Алисой и пытается ' \
                  'вызвать ее функции. Нужно сказать ему, что это Счетчик ' \
                  'и научить как выйти в Алису'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance.lower()
        if 'запусти' in full_phrase or 'поиграем' in full_phrase:
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Я навык Умный Счетчик Калорий. Чтобы вернуться в Алису '
                     'и запустить другой навык, скажите Выход'
        )


class Intent00021ShutUp(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 10  # Need to clear context
    name = 'Заткнись'
    should_clear_context = True
    description = 'Пользователь говорит навыку заткнуться.'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        full_phrase = request.original_utterance
        if full_phrase in ('заткнись', 'замолчи', 'молчи', 'молчать'):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Молчу',
                end_session=True,
        )


class Intent00022Agree(DialogIntent):
    time_to_evaluate = 100  # Need to check context
    time_to_respond = 0  # Need to clear context
    name = 'Ответ ДА'
    should_clear_context = True
    description = 'Пользователь отвечает согласием. Нужно посмотреть в ' \
                  'контексте, на что было дано согласие и передать ' \
                  'управление этому интенту'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        r = request
        if not request.context:
            r = r.set_context(
                    fetch_context_from_dynamo_database(
                            session_id=r.session_id,
                            database_client=get_dynamo_client(
                                    lambda_mode=r.aws_lambda_mode)))

        # tokens = request.tokens
        full_phrase = request.original_utterance.lower().strip()
        if full_phrase in ('да', 'ну да', 'ага', 'конечно'):
            r.intents_matching_dict[cls] = 100
            r = r.set_chosen_intent(cls)
        else:
            r.intents_matching_dict[cls] = 0
        return r

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        if request.context \
                and cls.__name__ in request.context.matching_intents_names:
            print(f'Getting answer from originating '
                  f'intent {request.context.intent_originator_name}')
            return globals()[request.context.intent_originator_name].respond(
                    request=request,
                    answer=cls.__name__)

        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Что да?',
        )


class Intent00023Disagree(DialogIntent):
    time_to_evaluate = 100  # Need to check context
    time_to_respond = 0  # Need to clear context
    name = 'Ответ НЕТ'
    should_clear_context = True
    description = 'Пользователь отвечает отказом. Нужно посмотреть в ' \
                  'контексте, на что было дан отказ и передать ' \
                  'управление этому интенту'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        r = request
        if not request.context:
            r = r.set_context(
                    fetch_context_from_dynamo_database(
                            session_id=r.session_id,
                            database_client=get_dynamo_client(
                                    lambda_mode=r.aws_lambda_mode)))

        # tokens = request.tokens
        full_phrase = request.original_utterance.lower().strip()
        if full_phrase in ('нет', 'ну нет', 'неа', 'ни за что'):
            r.intents_matching_dict[cls] = 100
            r = r.set_chosen_intent(cls)
        else:
            r.intents_matching_dict[cls] = 0
        return r

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        if request.context \
                and cls.__name__ in request.context.matching_intents_names:
            print(f'Getting answer from originating '
                  f'intent {request.context.intent_originator_name}')
            return globals()[request.context.intent_originator_name].respond(
                    request=request,
                    answer=cls.__name__)

        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Что нет?',
                should_clear_context=cls.should_clear_context
        )


class Intent00024SaveFood(DialogIntent):
    time_to_evaluate = 100  # Need to check context
    time_to_respond = 0  # Need to clear context
    name = 'Да, сохранить еду'
    should_clear_context = True
    description = 'У пользователя в контексте есть еда, и он подтверждает ' \
                  'свое согласие записать ее в базу данных'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        r = request
        if not request.context:
            r = r.set_context(
                    fetch_context_from_dynamo_database(
                            session_id=r.session_id,
                            database_client=get_dynamo_client(
                                    lambda_mode=r.aws_lambda_mode)))

        tokens = request.tokens
        full_phrase = request.original_utterance.lower().strip()
        if ('хранить' in tokens or
                'сохранить' in tokens or
                'сохраняй' in tokens or
                'сохрани' in tokens or
                'храни' in tokens or
                'сохранить' in tokens or
                'да' in tokens or full_phrase in (
                        'ну давай',
                        'давай',
                        'давай сохраняй',
                )):
            r.intents_matching_dict[cls] = 100
            r = r.set_chosen_intent(cls)
        else:
            r.intents_matching_dict[cls] = 0
        return r

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        if request.context \
                and cls.__name__ in request.context.matching_intents_names:
            print(f'Getting answer from originating '
                  f'intent {request.context.intent_originator_name}')
            return globals()[request.context.intent_originator_name].respond(
                    request=request,
                    answer=cls.__name__)

        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text='Пока нечего сохранять. Сначала скажите что вы съели.',
                should_clear_context=cls.should_clear_context
        )


class Intent01000SearchForFood(DialogIntent):
    time_to_evaluate = 500  # Check cache, translate request, query API
    time_to_respond = 10  # Save food context
    name = 'Найти еду'
    should_clear_context = False
    description = 'Пользователь сказал что он съел. Нужно посчитать калории'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        request = get_from_cache_table(yandex_requext=request)
        if request.food_dict:
            request.intents_matching_dict[cls] = 100

        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        response_text, total_calories = make_final_text(
            nutrition_dict=request.food_dict)
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=response_text,
                end_session=True,
        )


class Intent99999Default(DialogIntent):
    """
    WARNING! This class should always be the last in the file
    This a default response in none of above fit
    """
    time_to_evaluate = 99999
    time_to_respond = 0
    name = 'Дефолтный ответ'
    should_clear_context = False
    description = 'Если ничего не подошло, ' \
                  'отвечаем пользователю что не знаем такой еды'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        request.intents_matching_dict[cls] = 100
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
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
        # Excluding auxiliary classes
        if class_name in ('DialogIntent', 'YandexRequest', 'YandexResponse',
                          'DialogContext'):
            continue
        intents_to_return.append(cl)
    return intents_to_return


def make_final_text(*, nutrition_dict) -> typing.Tuple[str, float]:
    response_text = ''  # type: str
    total_calories = 0.0  # type: float
    total_fat = 0.0
    total_carbohydrates = 0.0
    total_protein = 0.0
    total_sugar = 0.0

    for number, food_name in enumerate(nutrition_dict['foods']):
        calories = nutrition_dict["foods"][number].get("nf_calories", 0) or 0
        total_calories += calories
        weight = nutrition_dict['foods'][number].get(
                'serving_weight_grams', 0) or 0
        protein = nutrition_dict["foods"][number].get("nf_protein", 0) or 0
        total_protein += protein
        fat = nutrition_dict["foods"][number].get("nf_total_fat", 0) or 0
        total_fat += fat
        carbohydrates = nutrition_dict["foods"][number].get(
                "nf_total_carbohydrate", 0) or 0
        total_carbohydrates += carbohydrates
        sugar = nutrition_dict["foods"][number].get("nf_sugars", 0) or 0
        total_sugar += sugar
        number_string = ''
        if len(nutrition_dict["foods"]) > 1:
            number_string = f'{number + 1}. '
        response_text += f'{number_string}{choose_case(amount=calories)} ' \
                         f'в {weight} гр.\n' \
            f'({round(protein, 1)} бел. ' \
            f'{round(fat, 1)} жир. ' \
            f'{round(carbohydrates, 1)} угл. ' \
            f'{round(sugar, 1)} сах.)\n'

    if len(nutrition_dict["foods"]) > 1:
        response_text += f'Итого: ({round(total_protein, 1)} бел. ' \
            f'{round(total_fat, 1)} жир. ' \
            f'{round(total_carbohydrates, 1)} угл. ' \
                         f'{round(total_sugar, 1)} сах.' \
            f')\n_\n{choose_case(amount=total_calories)}\n_\n'

    return response_text, total_calories


def choose_case(*, amount: float, round_to_int=False, tts_mode=False) -> str:
    if round_to_int:
        str_amount = str(int(amount))
    else:
        # Leaving only 2 digits after comma (12.03 for example)
        str_amount = str(round(amount, 2))
        if int(amount) == amount:
            str_amount = str(int(amount))

    last_digit_str = str_amount[-1]

    if not round_to_int and '.' in str_amount:  # 12.04 калории
        return f'{str_amount} калории'
    # below amount is integer for sure
    if last_digit_str == '1':  # 21 калория (20 одна калория in tts mode)
        if len(str_amount) > 1 and str_amount[-2] == '1':  # 11 калорий
            return f'{str_amount} калорий'
        if tts_mode:
            if len(str_amount) > 1:
                first_part = str(int(str_amount[:-1]) * 10)
            else:
                first_part = ''
            str_amount = f'{first_part} одна'
        return f'{str_amount} калория'
    elif last_digit_str in ('2', '3', '4'):
        if len(str_amount) > 1 and str_amount[-2] == '1':  # 11 калорий
            return f'{str_amount} калорий'
        if tts_mode:
            if len(str_amount) > 1:
                first_part = str(int(str_amount[:-1]) * 10)
            else:
                first_part = ''
            if last_digit_str == '2':
                str_amount = f'{first_part} две'
        return f'{str_amount} калории'  # 22 калории
    else:
        return f'{str_amount} калорий'  # 35 калорий


if __name__ == '__main__':
    print(sys.modules[__name__])
    print(intents())
