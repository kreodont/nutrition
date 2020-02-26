import json
import os
import re
import datetime
from decorators import timeit
import dateutil
import functools
from DialogContext import DialogContext
from yandex_types import YandexRequest, \
    YandexResponse, construct_yandex_response_from_yandex_request
import sys
import inspect
import random
from dynamodb_functions import fetch_context_from_dynamo_database, \
    get_dynamo_client, get_from_cache_table, update_user_table, \
    find_all_food_names_for_day, delete_food, write_keys_to_cache_table
import typing
import requests
from dates_transformations import transform_yandex_datetime_value_to_datetime


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
    should_save_context = True
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
        if 'answer' in kwargs and kwargs['answer'] == 'Intent00022Agree':
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text='Что ж, доктор, приятно познакомиться',
                    should_clear_context=True)

        if 'answer' in kwargs and kwargs['answer'] == 'Intent00023Disagree':
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text='Простите, обозналась',
                    should_clear_context=True)
        specifying_question = 'Доктор Лектер, это вы?'
        context = DialogContext(
                intent_originator_name=cls.__name__,
                matching_intents_names=('Intent00022Agree',
                                        'Intent00023Disagree'),
                specifying_question=specifying_question,
                user_initial_phrase=request.original_utterance)
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=specifying_question,
                new_context_to_write=context,
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


class Intent00025DoNotSaveFood(DialogIntent):
    time_to_evaluate = 100  # Need to check context
    time_to_respond = 0  # Need to clear context
    name = 'Нет, не надо сохранять еду'
    should_clear_context = True
    description = 'У пользователя в контексте есть еда, но он говорит что не ' \
                  'надо записывать ее в базу данных'

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
        if (
                'не' in tokens or
                'нет' in tokens or
                'забудь' in tokens or
                'забыть' in tokens or
                'удалить' in tokens
        ):
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


class Intent00026WhatIAte(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 110  # Read user database and clear context
    name = 'Что я ел?'
    should_clear_context = True
    description = 'Пользователь просит вспомнить что он ел'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        tokens = request.tokens
        full_phrase = request.original_utterance

        if (('что' in tokens or 'сколько' in tokens) and (
                'ел' in full_phrase or 'хран' in full_phrase)) or \
                full_phrase in ('покажи результат',
                                'открыть список сохранения',
                                'скажи результат',
                                'общий результат',
                                'общий итог',
                                'какой итог',
                                'сколько всего',
                                'сколько калорий',
                                'какой результат',
                                'сколько в общем калорий',
                                'сколько всего калорий',
                                'сколько калорий в общей сумме',
                                'сколько я съел калорий',
                                'сколько я съела калорий',
                                'покажи сохраненную',
                                'покажи сколько калорий',
                                'сколько я съел',
                                'сколько всего калорий было',
                                'сколько всего калорий было в день',
                                'список сохраненные еды',
                                'список сохраненной еды',
                                'общая сумма калорий за день',
                                'посчитай все калории за сегодня',
                                'сколько все вместе за весь день',
                                'ну посчитай сколько всего калорий',
                                'посчитай сколько всего калорий',
                                'подсчитать калории',
                                'сколько калорий у меня сегодня',
                                'подсчитать все',
                                'сколько всего получилось',
                                'сколько за день',
                                'сколько калорий за день',
                                'сколько сегодня калорий',
                                'сколько было сегодня калорий',
                                'сколько сегодня калорий было',
                                'общее количество',
                                'посчитай калории',
                                'итог',
                                'наели калорий за сегодня',
                                'итого'
                                ):
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0
        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        all_datetime_entries = [entity for entity in request.entities if
                                entity['type'] == "YANDEX.DATETIME"]
        if len(all_datetime_entries) == 0:
            target_date = datetime.date.today()
        else:
            # last detected date
            last_detected_date = all_datetime_entries[-1]
            target_date = transform_yandex_datetime_value_to_datetime(
                    yandex_datetime_value_dict=last_detected_date,
            ).date()

        all_food_for_date = find_all_food_names_for_day(
                lambda_mode=request.aws_lambda_mode,
                date=target_date,
                user_id=request.user_guid,
        )
        if len(all_food_for_date) == 0:
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Не могу ничего найти за {target_date}. '
                         f'Чтобы еда сохранялась в мою базу, не забывайте '
                         f'говорить "Сохранить", после того, как я посчитаю '
                         f'калории.',
                    tts='Ничего не найдено',
                    should_clear_context=True
            )

        food_total_text, food_total_tts = total_calories_text(
                food_dicts_list=all_food_for_date,
                target_date=target_date,
                timezone=request.timezone)

        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=food_total_text,
                tts=food_total_tts,
                should_clear_context=True
        )


class Intent00027DeleteSavedFood(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 120  # Read user database, write to user database
    # and clear context
    name = 'Удалить сохраненную еду по названию'
    should_clear_context = True
    description = 'Пользователь просит удалить еду, которую он сохранял ' \
                  'до этого'

    @staticmethod
    def define_deletion_date(request: YandexRequest) -> datetime.date:
        all_datetime_entries = [entity for entity in request.entities if
                                entity['type'] == "YANDEX.DATETIME"]
        # if no dates found in request, assuming deletion for today was
        # requested
        if len(all_datetime_entries) == 0:
            target_date = datetime.date.today()
        else:
            # last detected date
            last_detected_date = all_datetime_entries[-1]
            target_date = transform_yandex_datetime_value_to_datetime(
                    yandex_datetime_value_dict=last_detected_date,
            ).date()
        return target_date

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        for t in ['удалить',
                  'удали',
                  'удалите',
                  'убери',
                  'убрать',
                  ]:
            if t in request.tokens:
                # if number speficied, then
                # Intent00028DeleteSavedFoodByNumber fits better
                request.intents_matching_dict[cls] = 90
        if cls not in request.intents_matching_dict:
            request.intents_matching_dict[cls] = 0

        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        target_date = cls.define_deletion_date(request)
        all_datetime_entries = [entity for entity in request.entities if
                                entity['type'] == "YANDEX.DATETIME"]
        tokens_without_dates_tokens = remove_tokens_from_specific_intervals(
                tokens_list=request.original_utterance.split(),
                intervals_dicts_list=all_datetime_entries)

        # deleting extra words, so for now we should only have a
        # product name to delete
        tokens_without_delete_words = [t for t in tokens_without_dates_tokens if
                                       t.lower() not in (
                                           'удалить',
                                           'еду',
                                           'удали',
                                           'удалите'
                                           'убери',
                                           'убрать')]

        if len(tokens_without_delete_words) == 0:
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Если вы хотите очистить историю за сегодня, '
                         f'скажите "удалить всё"',
                    should_clear_context=True
            )
        elif (len(tokens_without_delete_words) == 1
              and tokens_without_delete_words[0].lower() in ('все', 'всё')):
            # deleting all food from database
            delete_food(
                    date=target_date,
                    list_of_food_to_delete_dicts=[],
                    list_of_all_food_dicts=[],
                    user_id=request.user_guid,
                    lambda_mode=request.aws_lambda_mode,
            )
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    should_clear_context=True,
                    text=f'Вся еда за {target_date} удалена')

        # Now rejoin all the tokens left back into the phrase
        food_to_delete = ' '.join(tokens_without_delete_words)
        all_food_for_date = find_all_food_names_for_day(
                lambda_mode=request.aws_lambda_mode,
                date=target_date,
                user_id=request.user_guid,
        )
        today_names_list = [food['utterance'] for food in all_food_for_date]
        if len(all_food_for_date) == 0:
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Не могу ничего найти за {target_date}. '
                         f'Чтобы еда сохранялась в мою базу, не забывайте '
                         f'говорить "Сохранить", после того, как я посчитаю '
                         f'калории.',
                    tts='Ничего не найдено',
                    should_clear_context=True
            )

        # Check if the food exists
        if food_to_delete not in today_names_list:
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Еды {food_to_delete} за {target_date} не найдено. '
                         f'Есть следующее: {today_names_list}',
                    tts='Такой еды не найдено',
                    should_clear_context=True,
            )
        else:
            delete_food(
                    date=target_date,
                    list_of_food_to_delete_dicts=[],
                    list_of_all_food_dicts=[],
                    user_id=request.user_guid,
                    lambda_mode=request.aws_lambda_mode,
            )
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Еды {food_to_delete} за {target_date} удалена.',
                    tts='Удалено',
                    should_clear_context=True,
            )


class Intent00028DeleteSavedFoodByNumber(DialogIntent):
    time_to_evaluate = 0
    time_to_respond = 120  # Read user database, write to user database
    # and clear context
    name = 'Удалить сохраненную еду по номеру в списку'
    should_clear_context = True
    description = 'Пользователь просит удалить еду, которую он сохранял ' \
                  'до этого, называя ее по номеру'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        request.intents_matching_dict[cls] = 0
        for t in ['удалить',
                  'удали',
                  'удалите',
                  'убери',
                  'убрать',
                  ]:
            if t in request.tokens:
                request.intents_matching_dict[cls] += 80
                break

        for t in ['номер', ]:
            if t in request.tokens:
                request.intents_matching_dict[cls] += 20
                break

        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        target_date = Intent00027DeleteSavedFood.define_deletion_date(request)
        all_food_for_date = find_all_food_names_for_day(
                lambda_mode=request.aws_lambda_mode,
                date=target_date,
                user_id=request.user_guid,
        )
        if len(all_food_for_date) == 0:
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Не могу ничего найти за {target_date}. '
                         f'Чтобы еда сохранялась в мою базу, не забывайте '
                         f'говорить "Сохранить", после того, как я посчитаю '
                         f'калории.',
                    tts='Ничего не найдено',
                    should_clear_context=True
            )

        search = re.search(r'номер (\d+)', request.original_utterance)
        if search:
            food_number = int(float(search.groups()[0]))
        else:
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Не поняла, какой номер удалить?',
                    tts='Удалено',
                    should_clear_context=True,
            )

        if food_number == 0:
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Не поняла, какой номер удалить?',
                    tts='Удалено',
                    should_clear_context=True,
            )

        if food_number > len(all_food_for_date):
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Нет еды с таким номером. Максимальный номер за '
                         f'{target_date}: {len(all_food_for_date)}',
                    should_clear_context=True,
            )

        delete_food(
                date=target_date,
                list_of_all_food_dicts=all_food_for_date,
                list_of_food_to_delete_dicts=[
                    all_food_for_date[food_number-1],
                ],
                lambda_mode=request.aws_lambda_mode,
                user_id=request.user_guid,
        )

        return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Еда с номером {food_number} '
                         f'({all_food_for_date[food_number-1]}) за '
                         f'{target_date} удалена.',
                    tts='Удалено',
                    should_clear_context=True,
            )


class Intent01000SearchForFood(DialogIntent):
    time_to_evaluate = 500  # Check cache, translate request, query API
    time_to_respond = 10  # Save food context
    name = 'Найти еду'
    should_clear_context = False
    description = 'Пользователь сказал что он съел. Нужно посчитать калории'

    @classmethod
    def evaluate(cls, *, request: YandexRequest, **kwargs) -> YandexRequest:
        # trying to look in cache first (and also load API keys in the same
        # request)
        request = get_from_cache_table(yandex_requext=request)
        if request.food_dict:
            request.intents_matching_dict[cls] = 100
            return request

        request = translate_into_english(yandex_request=request)
        if not request.translated_phrase:
            request.intents_matching_dict[cls] = 0
            return request

        request = query_api(yandex_request=request)
        write_keys_to_cache_table(
                keys_dict=request.api_keys,
                lambda_mode=request.aws_lambda_mode)

        if request.food_dict:
            request.intents_matching_dict[cls] = 100
        else:
            request.intents_matching_dict[cls] = 0

        return request

    @classmethod
    def respond(cls, *, request: YandexRequest, **kwargs) -> YandexResponse:
        if 'answer' in kwargs and kwargs['answer'] in (
                'Intent00022Agree', 'Intent00024SaveFood'):
            update_user_table(
                    database_client=get_dynamo_client(
                            lambda_mode=request.aws_lambda_mode),
                    event_time=datetime.datetime.now(),
                    foods_dict=request.context.food_dict,
                    utterance=request.context.user_initial_phrase,
                    user_id=request.user_guid,
            )

            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text='Сохранено',
                    should_clear_context=True)

        if 'answer' in kwargs and kwargs['answer'] in (
                'Intent00025DoNotSaveFood', 'Intent00023Disagree'):
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text='Забыто',
                    should_clear_context=True)
        context = DialogContext(
                intent_originator_name=cls.__name__,
                matching_intents_names=('Intent00022Agree',
                                        'Intent00025DoNotSaveFood',
                                        'Intent00024SaveFood',
                                        'Intent00023Disagree'),
                specifying_question='Сохранить?',
                user_initial_phrase=request.original_utterance,
                food_dict=request.food_dict,
        )
        response_text, total_calories = make_final_text(
                nutrition_dict=request.food_dict)
        response_text += '\nСкажите "да" или "сохранить", если хотите ' \
                         'записать этот прием пищи.'
        if request.has_screen:
            tts = choose_case(
                    amount=total_calories,
                    tts_mode=True,
                    round_to_int=True) + '. Сохранить?'
        else:
            tts = response_text
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=response_text,
                tts=tts,
                end_session=False,
                new_context_to_write=context
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


@timeit
def translate_into_english(*, yandex_request: YandexRequest) -> YandexRequest:
    russian_phrase = yandex_request.command
    if yandex_request.aws_lambda_mode:
        timeout = 0.5
    else:
        timeout = 10
    print(f'Translating "{russian_phrase}" into English')
    response = requests.get(
            'https://translate.yandex.net/api/v1.5/tr.json/translate',
            params={
                'key': os.getenv('YandexTranslate'),
                'text': russian_phrase,
                'lang': 'ru-en'
            },
            timeout=timeout,
    )

    if not response:
        print(f'Response not received from Yandex Translate: {response.text}')
        return yandex_request

    try:
        json_dict = json.loads(response.text)
    except Exception as e:
        print(f'Cannot parse response from yandex translate: {e}')
        return yandex_request

    if 'text' not in json_dict or len(json_dict['text']) < 1:
        print(f'Cannot parse response from yandex translate: {json_dict}')
        return yandex_request

    translated_text = json_dict['text'][0].lower(). \
        replace('bisque', 'soup')
    translated_text = re.sub(r'without (\w+)', '', translated_text)
    print(f'Translated: "{translated_text}"')

    yandex_request = yandex_request.set_translated_phrase(translated_text)
    return yandex_request


@timeit
def query_api(*, yandex_request: YandexRequest) -> YandexRequest:
    login, password, keys_dict = choose_key(yandex_request.api_keys)
    yandex_request = yandex_request.set_api_keys(api_keys=keys_dict)
    link = yandex_request.api_keys['link']
    if not yandex_request.aws_lambda_mode:  # while testing locally it
        # doesn't matter how long the script executed
        timeout = 10
    else:
        timeout = 0.5
    try:
        response = requests.post(link,
                                 data=json.dumps({
                                     'query':
                                         yandex_request.translated_phrase}),
                                 headers={'content-type': 'application/json',
                                          'x-app-id': login,
                                          'x-app-key': password},
                                 timeout=timeout,
                                 )
    except Exception as e:
        print(f'Exception when querying API: {e}')
        return yandex_request

    if response.status_code != 200:
        print(f'Failed to get nutrients for '
              f'"{yandex_request.translated_phrase}": {response.reason}')
        return yandex_request

    try:
        nutrition_dict = json.loads(response.text)
    except Exception as e:
        print(f'Cannot parse API respond: "{response.text}". Exception: {e}')
        return yandex_request

    if 'foods' not in nutrition_dict or not nutrition_dict['foods']:
        print(f'Tag foods not found or empty: {nutrition_dict}')
        return yandex_request

    yandex_request = yandex_request.set_food_dict(food_dict=nutrition_dict)

    return yandex_request


def choose_key(keys_dict):
    min_usage_value = 90000
    key_with_minimal_usages = None
    limit_date = str(datetime.datetime.now() - datetime.timedelta(hours=24))
    for k in keys_dict['keys']:
        # deleting keys usages if they are older than 24 hours
        # k = {'name': 'xxxx', 'pass': 'xxxx', 'dates': [list of strings]}
        k['dates'] = [d for d in k['dates'] if d > limit_date]
        if key_with_minimal_usages is None:
            key_with_minimal_usages = k
        if min_usage_value > len(k['dates']):
            key_with_minimal_usages = k
            min_usage_value = len(k['dates'])

    key_with_minimal_usages['dates'].append(str(datetime.datetime.now()))
    print(f"Key {key_with_minimal_usages['name']} with "
          f"{len(key_with_minimal_usages['dates'])} usages for last 24 hours")

    return \
        key_with_minimal_usages['name'], \
        key_with_minimal_usages['pass'], \
        keys_dict


def total_calories_text(
        *,
        food_dicts_list: typing.List[dict],
        target_date: datetime.date,
        timezone: str) -> typing.Tuple[str, str]:
    total_calories = 0
    total_fat = 0.0
    total_carbohydrates = 0.0
    total_protein = 0.0
    total_sugar = 0.0

    full_text = ''

    for food_number, food in enumerate(food_dicts_list, 1):
        nutrition_dict = food['foods']
        this_food_calories = 0
        food_time = dateutil.parser.parse(food['time'])
        food_time = food_time.astimezone(dateutil.tz.gettz(timezone))
        if 'foods' not in nutrition_dict:
            continue

        for f in nutrition_dict['foods']:
            calories = f.get("nf_calories", 0) or 0
            this_food_calories += calories
            total_calories += calories
            protein = f.get("nf_protein", 0) or 0
            total_protein += protein
            fat = f.get("nf_total_fat", 0) or 0
            total_fat += fat
            carbohydrates = f.get("nf_total_carbohydrate", 0) or 0
            total_carbohydrates += carbohydrates
            sugar = f.get("nf_sugars", 0) or 0
            total_sugar += sugar
        full_text += f'[{food_time.strftime("%H:%M")}] ' \
                     f'{food["utterance"]} ({round(this_food_calories, 2)})\n'

    all_total = total_protein + total_fat + total_carbohydrates
    if all_total == 0:
        return f'Не могу ничего найти за {target_date}. Я сохраняю еду в ' \
               f'свою базу, только если вы скажете Сохранить после ' \
               f'того, как я спрошу.', 'Ничего не найдено'
    percent_protein = round((total_protein / all_total) * 100)
    percent_fat = round((total_fat / all_total) * 100)
    percent_carbohydrates = round((total_carbohydrates / all_total) * 100)
    full_text += f'\n' \
                 f'Всего: \n{round(total_protein)} ({percent_protein}%) ' \
                 f'бел. {round(total_fat)} ({percent_fat}%) ' \
                 f'жир. {round(total_carbohydrates)} (' \
                 f'{percent_carbohydrates}%) ' \
                 f'угл. {round(total_sugar)} ' \
                 f'сах.\n_\n{choose_case(amount=round(total_calories, 2))}'

    tts = choose_case(amount=total_calories, tts_mode=True, round_to_int=True)
    return full_text, tts


def remove_tokens_from_specific_intervals(
        *,
        tokens_list: list,
        intervals_dicts_list: typing.Iterable,
) -> list:
    """
    If we have list of tokens like ["Token 1", "2", "Banana", "Egg"] and
    we want to remove specific numbers, we can call this function with
    the following intervals dict list: [{"start": 1, "end": 2}], and the
    result will be: ["Token 1", "Egg"]
    :param tokens_list:
    :param intervals_dicts_list:
    :return:
    """

    def if_token_number_in_interval(yandex_entity_dict: dict, *,
                                    number: int):
        if 'tokens' not in yandex_entity_dict:
            return False
        if 'start' not in yandex_entity_dict['tokens']:
            return False
        if 'end' not in yandex_entity_dict['tokens']:
            return False
        if yandex_entity_dict['tokens']['start'] <= number < \
                yandex_entity_dict['tokens']['end']:
            return True
        return False

    result_list = []
    for token_number, token in enumerate(tokens_list):
        partial_function = functools.partial(
                if_token_number_in_interval,
                token_number=token_number)
        result = list(map(partial_function, intervals_dicts_list))
        if any(result):
            continue
        result_list.append(token)

    return result_list


if __name__ == '__main__':
    print(sys.modules[__name__])
    print(intents())
