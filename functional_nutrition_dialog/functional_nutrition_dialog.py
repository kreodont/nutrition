import datetime
import typing
from functools import partial
import boto3
import botocore.client
import json
from botocore.vendored import requests
from standard_responses import respond_i_dont_know, \
    respond_one_of_predefined_phrases, respond_greeting_phrase
from yandex_types import YandexResponse, YandexRequest, \
    transform_event_dict_to_yandex_request_object, \
    transform_yandex_response_to_output_result_dict
from decorators import timeit
from responses_constructors import respond_request, \
    construct_yandex_response_from_yandex_request, \
    construct_food_yandex_response_from_food_dict
# from mockers import mock_incoming_event
from dynamodb_functions import update_user_table, clear_session, save_session, \
    write_to_cache_table, get_from_cache_table, \
    fetch_context_from_dynamo_database
from russian_language import russian_replacements_in_original_utterance
from translation_functions import translate_request
import dateutil
from dates_transformations import transform_yandex_datetime_value_to_datetime

# This cache is useful because AWS lambda can keep it's state, so no
# need to restantiate connections again. It is used in get_boto3_client
# function, I know it is mess, but 100 ms are 100 ms
global_cached_boto3_clients = {}


@timeit
def get_boto3_client(
        *,
        aws_lambda_mode: bool,
        service_name: str,
        profile_name: str = 'kreodont',
        connect_timeout: float = 0.2,
        read_timeout: float = 0.4,
) -> typing.Optional[boto3.client]:
    """
    Dirty function to fetch s3_clients
    :param connect_timeout:
    :param read_timeout:
    :param aws_lambda_mode:
    :param service_name:
    :param profile_name:
    :return:
    """
    known_services = ['translate', 'dynamodb', 's3']
    if service_name in global_cached_boto3_clients:
        print(f'{service_name} client taken from cache!')
        return global_cached_boto3_clients[service_name]

    if service_name not in known_services:
        raise Exception(
                f'Not known service '
                f'name {service_name}. The following '
                f'service names known: {", ".join(known_services)}')

    if aws_lambda_mode:
        client = boto3.client(
                service_name,
                config=botocore.client.Config(
                        connect_timeout=connect_timeout,
                        read_timeout=read_timeout,
                        parameter_validation=False,
                        retries={'max_attempts': 0},
                ),
        )
    else:
        client = boto3.Session(profile_name=profile_name).client(service_name)

    # saving to cache to to spend time to create it next time
    global_cached_boto3_clients[service_name] = client
    return client


@timeit
def response_with_context_when_yes_in_request(
        *,
        request: YandexRequest,
        context: dict,
        database_client
):
    # Save to database
    # Clear context
    # Say Сохранено
    update_user_table(
            database_client=database_client,
            event_time=dateutil.parser.parse(context['time']),
            foods_dict=context['foods'],
            user_id=request.user_guid,
            utterance=context['utterance'])

    clear_session(database_client=database_client,
                  session_id=request.session_id)

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Сохранено',
            tts='Сохранено',
            end_session=False,
            buttons=[],
    )


@timeit
def response_with_context_when_date_in_request(
        *,
        request: YandexRequest,
        context: dict,
        date: datetime,
        database_client
):
    # Save to database for specified time
    # Clear context
    # Say Сохранено
    update_user_table(
            database_client=database_client,
            event_time=date.replace(
                    tzinfo=dateutil.tz.gettz(request.timezone)
            ).astimezone(dateutil.tz.gettz('UTC')),
            foods_dict=context['foods'],
            user_id=request.user_guid,
            utterance=context['utterance'])

    clear_session(database_client=database_client,
                  session_id=request.session_id)

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=f'Сохранено за {date.date()}. Чтобы посмотреть список '
            f'сохраненной еды, спросите меня что Вы ели',
            tts='Сохранено',
            end_session=False,
            buttons=[],
    )


@timeit
def response_with_context_when_no_in_request(
        *,
        request: YandexRequest,
        database_client
):
    # Clear context
    # Say Забыли

    clear_session(database_client=database_client,
                  session_id=request.session_id)

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Забыли',
            tts='Забыли',
            end_session=False,
            buttons=[],
    )


@timeit
def check_if_yes_in_request(*, request: YandexRequest) -> bool:
    tokens = request.tokens
    if (
            'да' in tokens or
            'ага' in tokens or
            'конечно' in tokens or
            'хорошо' in tokens or
            'хранить' in tokens or
            'сохраняй' in tokens or
            'давай' in tokens or
            'можно' in tokens or
            'сохрани' in tokens or
            'храни' in tokens):
        return True

    return False


@timeit
def check_if_date_in_request(*, request: YandexRequest) -> bool:
    if any([entity for entity in request.entities if
            entity['type'] == "YANDEX.DATETIME"]):
        return True

    return False


@timeit
def check_if_no_in_request(*, request: YandexRequest) -> bool:
    tokens = request.tokens
    if (
            'не' in tokens or
            'нет' in tokens or
            'забудь' in tokens or
            'забыть' in tokens or
            'удалить' in tokens):
        return True

    return False


@timeit
def respond_with_context(
        *,
        request: YandexRequest,
        context: dict,
        database_client
) -> YandexResponse:
    if check_if_no_in_request(request=request):
        return response_with_context_when_no_in_request(
                request=request,
                database_client=database_client,
        )

    if check_if_yes_in_request(request=request):
        return response_with_context_when_yes_in_request(
                request=request,
                context=context,
                database_client=database_client,
        )

    if check_if_date_in_request(request=request):
        last_datetime_entity = [entity for entity in request.entities if
                                entity['type'] == "YANDEX.DATETIME"][-1]
        absolute_date = transform_yandex_datetime_value_to_datetime(
                yandex_datetime_value_dict=last_datetime_entity['value'])

        return response_with_context_when_date_in_request(
                request=request,
                context=context,
                database_client=database_client,
                date=absolute_date,

        )

    # We checked all possible context reaction, nothing fits,
    # so act as we don't have context at all
    return respond_without_context(request=request)


@timeit
def query_endpoint(*, link, login, password, phrase) -> dict:
    try:
        response = requests.post(link,
                                 data=json.dumps({'query': phrase}),
                                 headers={'content-type': 'application/json',
                                          'x-app-id': login,
                                          'x-app-key': password},
                                 timeout=0.5,
                                 )
    except Exception as e:
        return {'fatal': str(e)}

    if response.status_code != 200:
        return {'error': response.text}

    try:
        nutrition_dict = json.loads(response.text)
    except Exception as e:
        return {'fatal': f'Failed to parse food json: {e}'}

    if 'foods' not in nutrition_dict or not nutrition_dict['foods']:
        return {'fatal': f'Tag foods not found or empty: {nutrition_dict}'}

    return nutrition_dict


@timeit
def choose_key(keys_dict):
    min_usage_value = 90000
    min_usage_key = None
    limit_date = str(datetime.datetime.now() - datetime.timedelta(hours=24))
    for k in keys_dict['keys']:
        # deleting keys usages if they are older than 24 hours
        k['dates'] = [d for d in k['dates'] if d > limit_date]
        if min_usage_key is None:
            min_usage_key = k
        if min_usage_value > len(k['dates']):
            min_usage_key = k
            min_usage_value = len(k['dates'])

    min_usage_key['dates'].append(str(datetime.datetime.now()))
    return min_usage_key['name'], min_usage_key['pass'], keys_dict


@timeit
def respond_without_context(request: YandexRequest) -> YandexResponse:
    database_client = get_boto3_client(
            aws_lambda_mode=request.aws_lambda_mode,
            service_name='dynamodb',
    )

    keys_dict, cached_dict = get_from_cache_table(
            request_text=request.original_utterance,
            database_client=database_client)

    # if failed to get data from dynamodb
    if 'error' in keys_dict:
        return respond_i_dont_know(request=request)

    if cached_dict:
        return construct_food_yandex_response_from_food_dict(
                yandex_request=request,
                cached_dict=cached_dict)

    request_with_replacements = russian_replacements_in_original_utterance(
            yandex_request=request)

    translation_client = get_boto3_client(
            aws_lambda_mode=request.aws_lambda_mode,
            service_name='translate',
    )

    translated_request = translate_request(
            yandex_request=request_with_replacements,
            translate_client=translation_client,
    )

    if translated_request.error:
        return respond_i_dont_know(request=translated_request)

    login, password, keys_dict = choose_key(keys_dict)
    nutrition_dict = query_endpoint(
            link=keys_dict['link'],
            login=login,
            password=password,
            phrase=translated_request.original_utterance)

    # if we recevied negative response,
    if 'fatal' in nutrition_dict:
        return respond_i_dont_know(request=translated_request)

    write_to_cache_table(
            initial_phrase=request.original_utterance,
            nutrition_dict=nutrition_dict,
            database_client=database_client,
            keys_dict=keys_dict)

    if 'error' in nutrition_dict:
        return respond_i_dont_know(request=translated_request)

    save_session(
            session_id=translated_request.session_id,
            database_client=database_client,
            event_time=datetime.datetime.now(),
            foods_dict=nutrition_dict,
            utterance=request.original_utterance)

    return construct_food_yandex_response_from_food_dict(
            yandex_request=request,
            cached_dict=nutrition_dict,
    )


def respond_existing_session(yandex_request: YandexRequest):
    database_client = get_boto3_client(
            aws_lambda_mode=yandex_request.aws_lambda_mode,
            service_name='dynamodb')

    context = fetch_context_from_dynamo_database(
            database_client=database_client,
            session_id=yandex_request.session_id,
    )

    if context:
        return partial(
                respond_with_context,
                context=context,
                database_client=database_client)(request=yandex_request)
    else:
        return respond_without_context(request=yandex_request)


@timeit
def functional_nutrition_dialog(event: dict, context: dict) -> dict:
    """
    Main lambda entry point
    # event:dict ->
    # YandexRequest:YandexRequest ->
    # YandexResponse:YandexResponse ->
    # response:dict
    """
    yandex_request = transform_event_dict_to_yandex_request_object(
            event_dict=event,
            aws_lambda_mode=bool(context),
    )

    if yandex_request.error:
        # Exit immediatelly in case of mailformed request
        return transform_yandex_response_to_output_result_dict(
                yandex_response=construct_yandex_response_from_yandex_request(
                        yandex_request=yandex_request,
                        text=yandex_request.error,
                        tts=yandex_request.error,
                        buttons=[],
                        end_session=True,
                ))

    # there can be many hardcoded responses, need to check all of them before
    # querying any databases
    any_predifined_response = respond_one_of_predefined_phrases(
            request=yandex_request)

    if any_predifined_response:
        # If predefined answer given, forget all previous food, since
        # conversation topic has been already changed
        clear_session(
                session_id=yandex_request.session_id,
                database_client=get_boto3_client(
                        aws_lambda_mode=yandex_request.aws_lambda_mode,
                        service_name='dynamodb',
                )
        )
        return transform_yandex_response_to_output_result_dict(
                yandex_response=any_predifined_response)

    if yandex_request.is_new_session:
        responding_function = respond_greeting_phrase
    else:
        responding_function = respond_existing_session

    return transform_yandex_response_to_output_result_dict(
            yandex_response=respond_request(
                    request=yandex_request,
                    responding_function=responding_function,
            )
    )


if __name__ == '__main__':
    # print(functional_nutrition_dialog(
    #         event=mock_incoming_event(
    #                 phrase='удалить',
    #                 has_screen=True),
    #         context={}))
    print(functional_nutrition_dialog(
            event={
                "meta": {
                    "client_id": "ru.yandex.searchplugin/7.16 (none none; "
                                 "android 4.4.2)",
                    "interfaces": {
                        "account_linking": {},
                        "payments": {},
                        "screen": {}
                    },
                    "locale": "ru-RU",
                    "timezone": "UTC"
                },
                "request": {
                    "command": "удалить 4 января и 5 января в 13:00 банан",
                    "nlu": {
                        "entities": [
                            {
                                "tokens": {
                                    "end": 2,
                                    "start": 1
                                },
                                "type": "YANDEX.NUMBER",
                                "value": 4
                            },
                            {
                                "tokens": {
                                    "end": 3,
                                    "start": 1
                                },
                                "type": "YANDEX.DATETIME",
                                "value": {
                                    "day": 4,
                                    "day_is_relative": False,
                                    "month": 1,
                                    "month_is_relative": False
                                }
                            },
                            {
                                "tokens": {
                                    "end": 5,
                                    "start": 4
                                },
                                "type": "YANDEX.NUMBER",
                                "value": 5
                            },
                            {
                                "tokens": {
                                    "end": 9,
                                    "start": 4
                                },
                                "type": "YANDEX.DATETIME",
                                "value": {
                                    "day": 5,
                                    "day_is_relative": False,
                                    "hour": 13,
                                    "hour_is_relative": False,
                                    "minute": 0,
                                    "minute_is_relative": False,
                                    "month": 1,
                                    "month_is_relative": False
                                }
                            }
                        ],
                        "tokens": [
                            "удалить",
                            "4",
                            "января",
                            "и",
                            "5",
                            "января",
                            "в",
                            "13",
                            "00",
                            "банан"
                        ]
                    },
                    "original_utterance": "удалить 4 января и 5 "
                                          "января в 13:00 банан",
                    "type": "SimpleUtterance"
                },
                "session": {
                    "message_id": 1,
                    "new": False,
                    "session_id": "18418e00-26deac36-8386cc00-680a52be",
                    "skill_id": "2142c27e-6062-4899-a43b-806f2eddeb27",
                    "user_id": "E401738E621D9AAC04AB162E44F39"
                               "B3ABDA23A5CB2FF19E394C1915ED45CF467"
                },
                "version": "1.0"
            },
            context={},
    ))
