import random
import typing
from yandex_types import YandexRequest, YandexResponse
from responses_constructors import \
    construct_yandex_response_from_yandex_request, respond_request
from delete_response import respond_delete
import datetime
from dates_transformations import transform_yandex_datetime_value_to_datetime
from dynamodb_functions import get_boto3_client, find_all_food_names_for_day
import dateutil
from russian_language import choose_case


def respond_one_of_predefined_phrases(
        request: YandexRequest,
) -> typing.Optional[YandexResponse]:
    # Delete request must be checked first since it can be longer and that is OK
    if is_delete_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_delete)

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

    if is_ping_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_ping)

    if is_launch_again_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_launch_again)

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

    if is_smart_calories_counter_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_smart_calories_countere)

    if is_where_is_saved_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_where_is_saved)

    if is_angry_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_angry)

    if is_not_implemented_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_not_implemented)

    if is_launch_another_skill_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_launch_another_skill)

    if is_what_i_have_eaten_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_what_i_have_eaten)

    if is_shut_up_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_shut_up_request)


def is_launch_again_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase.lower().strip() in (
            'запусти навык умный счетчик калорий',
            'алиса запусти умный счетчик калорий',
            'запустить умный счетчик калорий',
    ):
        return True
    return False


def respond_launch_again(request: YandexRequest) -> YandexResponse:
    help_text = 'Какую еду записать?'

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=help_text,
            tts=help_text,
            end_session=False,
            buttons=[],
    )


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


def is_delete_request(request: YandexRequest):
    tokens = request.tokens
    if (
            'удалить' in tokens or
            'удали' in tokens or
            'убери' in tokens or
            'убрать' in tokens):
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
    if full_phrase.lower().strip() in (
            'спасибо', 'молодец', 'отлично', 'ты классная', 'классная штука',
            'классно', 'ты молодец', 'круто', 'обалдеть', 'прикольно',
            'клево', 'ништяк', 'класс'):
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
    respond_string = 'Здравствуйте. А теперь расскажите что вы съели, ' \
                     'а я скажу сколько там было калорий и питательных веществ.'
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
                       'что-то мало', 'так много', 'а почему так много'):
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
    tokens = request.tokens
    if 'как' in tokens and ('зовут' in tokens or 'имя' in tokens):
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


def is_smart_calories_counter_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('умный счетчик калорий', ):
        return True
    return False


def respond_smart_calories_countere(request: YandexRequest) -> YandexResponse:
    respond_string = 'Да, я слушаю'

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_where_is_saved_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('а где сохраняются', 'где сохраняются',
                       'где сохранить', 'а зачем сохранять', 'зачем сохранять'):
        return True
    return False


def respond_where_is_saved(request: YandexRequest) -> YandexResponse:
    respond_string = 'Приемы пищи сохраняются в моей базе данных. ' \
                     'Ваши приемы пищи будут доступны только Вам. ' \
                     'Я могу быть Вашим личным дневником калорий'

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_angry_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('дура', 'дурочка', 'иди на хер', 'пошла нахер', 'тупица',
                       'идиотка', 'тупорылая', 'тупая', 'ты дура'):
        return True
    return False


def respond_angry(request: YandexRequest) -> YandexResponse:
    respond_string = 'Все мы можем ошибаться. Напишите моему разработчику, ' \
                     'а он меня накажет и научит больше не ошибаться.'

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_not_implemented_request(request: YandexRequest):
    full_phrase = request.original_utterance
    tokens = request.tokens
    if full_phrase in ('норма калорий',
                       'сколько я набрала калорий',
                       'сколько я набрал калорий',
                       'сколько в день нужно калорий',
                       'норма потребления',
                       'сколько нужно съесть калорий в день',
                       'дневная норма калорий',
                       ) or 'норма' in tokens:
        return True
    return False


def respond_not_implemented(request: YandexRequest) -> YandexResponse:
    respond_string = 'Этого я пока не умею, но планирую скоро научиться. ' \
                     'Следите за обновлениями'

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_launch_another_skill_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if 'запусти' in full_phrase or 'поиграем' in full_phrase:
        return True
    return False


def respond_launch_another_skill(request: YandexRequest) -> YandexResponse:
    respond_string = 'Я навык Умный Счетчик Калорий. Чтобы вернуться в Алису ' \
                     'и запустить другой навык, скажите Выход'

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
            'умеешь' in tokens or
            ('что' in tokens and [t for t in tokens if 'делать' in t]) or
            ('что' in tokens and [t for t in tokens if 'умеешь' in t]) or
            ('как' in tokens and [t for t in tokens if 'польз' in t]) or
            'скучно' in tokens or
            'help' in tokens):
        return True

    return False


def is_ping_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('ping', 'пинг'):
        return True
    return False


def respond_ping(request: YandexRequest) -> YandexResponse:
    respond_string = 'pong'

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def respond_text_too_long(request: YandexRequest) -> YandexResponse:
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Ой, текст слишком длинный. Давайте попробуем частями?',
            tts='Ой, текст слишком длинный. Давайте попробуем частями?',
            end_session=False,
            buttons=[],
    )


def respond_i_dont_know(request: YandexRequest) -> YandexResponse:
    first_parts_list = [
        'Это не похоже на название еды. Попробуйте сформулировать иначе',
        'Хм. Не могу понять что это. Попробуйте сказать иначе',
        'Такой еды я пока не знаю. Попробуйте сказать иначе'
    ]

    food_examples_list = ['Бочка варенья и коробка печенья',
                          'Литр молока и килограмм селедки',
                          '2 куска пиццы с ананасом',
                          '200 грамм брокколи и 100 грамм шпината',
                          'ананас и рябчик',
                          '2 блина со сгущенкой',
                          'тарелка риса, котлета и стакан апельсинового сока',
                          'банан, апельсин и манго',
                          'черная икра, красная икра, баклажанная икра',
                          'каша из топора и свежевыжатый березовый сок',
                          ]

    full_generated_text = f"{random.choice(first_parts_list)}, " \
        f"например: {random.choice(food_examples_list)}. " \
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
    )


def respond_greeting_phrase(request: YandexRequest) -> YandexResponse:
    greeting_text = 'Какую еду записать?'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=greeting_text,
            tts=greeting_text,
            end_session=False,
            buttons=[],
    )


def is_what_i_have_eaten_request(request: YandexRequest):
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
                            ):
        return True
    return False


def respond_what_i_have_eaten(request: YandexRequest) -> YandexResponse:
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
            database_client=get_boto3_client(
                    aws_lambda_mode=request.aws_lambda_mode,
                    service_name='dynamodb'),
            date=target_date,
            user_id=request.user_guid,
    )
    if len(all_food_for_date) == 0:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=f'Не могу ничего найти за {target_date}. '
                f'Чтобы еда сохранялась в мою базу, не забывайте '
                f'говорить "Сохранить", после того, как я посчитаю калории.',
                tts='Ничего не найдено',
                end_session=False,
                buttons=[],
        )

    food_total_text, food_total_tts = total_calories_text(
                    food_dicts_list=all_food_for_date,
                    target_date=target_date,
                    timezone=request.timezone)
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=food_total_text,
            tts=food_total_tts,
            end_session=False,
            buttons=[],
    )


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
        f'жир. {round(total_carbohydrates)} ({percent_carbohydrates}%) ' \
        f'угл. {round(total_sugar)} ' \
        f'сах.\n_\n{choose_case(amount=round(total_calories, 2))}'

    tts = choose_case(amount=total_calories, tts_mode=True, round_to_int=True)
    return full_text, tts


def is_shut_up_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('заткнись', 'замолчи', 'молчи', 'молчать'):
        return True
    return False


def respond_shut_up_request(request: YandexRequest) -> YandexResponse:
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Молчу',
            tts='Молчу',
            end_session=False,
            buttons=[],
    )
