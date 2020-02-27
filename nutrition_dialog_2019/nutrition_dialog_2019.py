# import datetime
# from functools import partial
# import json
# from botocore.vendored import requests
# import standard_responses
from yandex_types import transform_event_dict_to_yandex_request_object, \
    transform_yandex_response_to_output_result_dict, log_hash
from decorators import timeit
import datetime
import typing
import standard_responses
import mockers
import dynamodb_functions
from delete_response import respond_delete

# from responses_constructors import \
#     construct_yandex_response_from_yandex_request, \
#     construct_food_yandex_response_from_food_dict
# from mockers import mock_incoming_event
# from dynamodb_functions import update_user_table,
# clear_session, save_session, \
#     write_to_cache_table, get_from_cache_table, get_boto3_client, \
#     fetch_context_from_dynamo_database
# from russian_language import russian_replacements_in_original_utterance
# from translation_functions import translate_request
# import dateutil
# from dates_transformations import transform_yandex_datetime_value_to_datetime
# from delete_response import remove_tokens_from_specific_intervals, \
#     respond_delete


# @timeit
# def respond_yes_in_request(
#         *,
#         request: YandexRequest,
#         context: dict,
#         database_client
# ):
#     # Save to database
#     # Clear context
#     # Say Сохранено
#
#     update_user_table(
#             database_client=database_client,
#             event_time=dateutil.parser.parse(context['time']),
#             foods_dict=context['foods'],
#             user_id=request.user_guid,
#             utterance=context['utterance'])
#
#     return construct_yandex_response_from_yandex_request(
#             yandex_request=request,
#             text='Сохранено. Чтобы посмотреть список сохраненной '
#                  'еды, спросите "Что я ел сегодня?',
#             tts='Сохранено',
#             end_session=False,
#             buttons=[],
#     )


# @timeit
# def respond_date_in_request(
#         *,
#         request: YandexRequest,
#         context: dict,
#         date: datetime,
#         database_client
# ):
#     # Save to database for specified time
#     # Clear context
#     # Say Сохранено
#
#     update_user_table(
#             database_client=database_client,
#             event_time=date.replace(
#                     tzinfo=dateutil.tz.gettz(request.timezone)
#             ).astimezone(dateutil.tz.gettz('UTC')),
#             foods_dict=context['foods'],
#             user_id=request.user_guid,
#             utterance=context['utterance'])
#
#     return construct_yandex_response_from_yandex_request(
#             yandex_request=request,
#             text=f'Сохранено за {date.date()}. Чтобы посмотреть список '
#             f'сохраненной еды, спросите меня что Вы ели',
#             tts='Сохранено',
#             end_session=False,
#             buttons=[],
#     )


# @timeit
# def respond_no_in_request(
#         *,
#         request: YandexRequest,
#         database_client,
#         context: dict,
# ):
#     # Clear context
#     # Say Забыли
#     if not context:
#         return standard_responses.respond_i_dont_know(request=request)
#
#     clear_session(database_client=database_client,
#                   session_id=request.session_id)
#
#     return construct_yandex_response_from_yandex_request(
#             yandex_request=request,
#             text='Забыли',
#             tts='Забыли',
#             end_session=False,
#             buttons=[],
#     )

#
# @timeit
# def check_if_yes_in_request(*, request: YandexRequest) \
#         -> typing.Optional[typing.Callable]:
#     tokens = request.tokens
#     full_phrase = request.original_utterance.lower().strip()
#     if ('хранить' in tokens or
#             'сохранить' in tokens or
#             'сохраняй' in tokens or
#             'сохрани' in tokens or
#             'храни' in tokens or
#             'сохранить' in tokens or
#             'да' in tokens or full_phrase in (
#                     'ну давай',
#                     'давай',
#                     'давай сохраняй',
#             )):
#         return respond_yes_in_request
#
#     return None


# def check_if_date_in_request(
#         *, request: YandexRequest) -> typing.Optional[typing.Callable]:
#     all_datetime_entries = [entity for entity in request.entities if
#                             entity['type'] == "YANDEX.DATETIME"]
#
#     if len(all_datetime_entries) == 0:
#         return None
#
#     tokens_without_dates_tokens = remove_tokens_from_specific_intervals(
#             tokens_list=request.tokens,
#             intervals_dicts_list=all_datetime_entries)
#
#     tokens_without_common_words = [t for t in tokens_without_dates_tokens if
#                                    t not in ('да', 'за',
#                                              'сохрани', 'сохранить')]
#
#     # all other words were removed, so only date left in request
#     if len(tokens_without_common_words) == 0:
#         last_date_mentioned_dict = all_datetime_entries[-1]
#         last_date_mentioned = transform_yandex_datetime_value_to_datetime(
#                 yandex_datetime_value_dict=last_date_mentioned_dict)
#         return partial(respond_date_in_request, date=last_date_mentioned)
#
#     return None


# @timeit
# def check_if_no_in_request(*, request: YandexRequest) \
#         -> typing.Optional[typing.Callable]:
#     tokens = request.tokens
#     if (
#             'не' in tokens or
#             'нет' in tokens or
#             'забудь' in tokens or
#             'забыть' in tokens or
#             'удалить' in tokens):
#         return respond_no_in_request
#
#     return None


# @timeit
# def respond_with_context(
#         *,
#         request: YandexRequest,
#         context: dict,
#         database_client
# ) -> YandexResponse:
#     if check_if_date_in_request(request=request):
#         last_datetime_entity = [entity for entity in request.entities if
#                                 entity['type'] == "YANDEX.DATETIME"][-1]
#         absolute_date = transform_yandex_datetime_value_to_datetime(
#                 yandex_datetime_value_dict=last_datetime_entity['value'])
#
#         # sometimes yandex sets YANDEX.DATETIME object where it shouldn't be
#         if absolute_date.year > 2000:
#             return response_with_context_when_date_in_request(
#                     request=request,
#                     context=context,
#                     database_client=database_client,
#                     date=absolute_date,
#
#             )
#
#     if check_if_no_in_request(request=request):
#         return response_with_context_when_no_in_request(
#                 request=request,
#                 database_client=database_client,
#         )
#
#     if check_if_yes_in_request(request=request):
#         return response_with_context_when_yes_in_request(
#                 request=request,
#                 context=context,
#                 database_client=database_client,
#         )
#
#     # We checked all possible context reaction, nothing fits,
#     # so act as we don't have context at all
#     return respond_without_context(request=request)


# @timeit
# def query_endpoint(*, link, login, password, phrase, debug=False) -> dict:
#     if debug:
#         print(f'Login: {login} Password: {password} Phrase: {phrase}')
#     try:
#         response = requests.post(link,
#                                  data=json.dumps({'query': phrase}),
#                                  headers={'content-type': 'application/json',
#                                           'x-app-id': login,
#                                           'x-app-key': password},
#                                  timeout=0.5,
#                                  )
#     except Exception as e:
#         return {'fatal': str(e)}
#
#     if response.status_code != 200:
#         return {'error': response.text}
#
#     try:
#         nutrition_dict = json.loads(response.text)
#     except Exception as e:
#         return {'fatal': f'Failed to parse food json: {e}'}
#
#     if 'foods' not in nutrition_dict or not nutrition_dict['foods']:
#         return {'fatal': f'Tag foods not found or empty: {nutrition_dict}'}
#
#     return nutrition_dict


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


# @timeit
# def respond_food_in_request(
#         *,
#         request: YandexRequest,
#         use_cache_result: bool,
# ) -> typing.Optional[YandexResponse]:
#     something
#
#
#
# @timeit
# def respond_without_context(request: YandexRequest) -> YandexResponse:
#     database_client = get_boto3_client(
#             aws_lambda_mode=request.aws_lambda_mode,
#             service_name='dynamodb',
#     )[0]
#
#     keys_dict, cached_dict = get_from_cache_table(
#             request_text=request.original_utterance,
#             database_client=database_client)
#
#     # if failed to get data from dynamodb
#     if 'error' in keys_dict:
#         return standard_responses.respond_i_dont_know(request=request)
#
#     if cached_dict:
#         if 'foods' in cached_dict and 'error' not in cached_dict['foods']:
#             save_session(
#                     session_id=request.session_id,
#                     database_client=database_client,
#                     event_time=datetime.datetime.now(),
#                     foods_dict=cached_dict,
#                     utterance=request.original_utterance)
#
#         return construct_food_yandex_response_from_food_dict(
#                 yandex_request=request,
#                 cached_dict=cached_dict)
#
#     request_with_replacements = russian_replacements_in_original_utterance(
#             yandex_request=request)
#
#     translation_client = get_boto3_client(
#             aws_lambda_mode=request.aws_lambda_mode,
#             service_name='translate',
#     )[0]
#
#     translated_request = translate_request(
#             yandex_request=request_with_replacements,
#             translate_client=translation_client,
#     )
#
#     if translated_request.error:
#         return standard_responses.respond_i_dont_know(
#                 request=translated_request)
#
#     login, password, keys_dict = choose_key(keys_dict)
#     nutrition_dict = query_endpoint(
#             link=keys_dict['link'],
#             login=login,
#             password=password,
#             phrase=translated_request.original_utterance,
#             debug=True
#     )
#
#     # if we recevied negative response,
#     if 'fatal' in nutrition_dict:
#         return standard_responses.respond_i_dont_know(
#                 request=translated_request)
#
#     write_to_cache_table(
#             initial_phrase=request.original_utterance,
#             nutrition_dict=nutrition_dict,
#             database_client=database_client,
#             keys_dict=keys_dict)
#
#     if 'error' in nutrition_dict:
#         return standard_responses.respond_i_dont_know(
#                 request=translated_request)
#
#     # Saving context
#     save_session(
#             session_id=translated_request.session_id,
#             database_client=database_client,
#             event_time=datetime.datetime.now(),
#             foods_dict=nutrition_dict,
#             utterance=request.original_utterance)
#
#     return construct_food_yandex_response_from_food_dict(
#             yandex_request=request,
#             cached_dict=nutrition_dict,
#     )
#

# def respond_existing_session(yandex_request: YandexRequest):
#     database_client = get_boto3_client(
#             aws_lambda_mode=yandex_request.aws_lambda_mode,
#             service_name='dynamodb')[0]
#
#     context = fetch_context_from_dynamo_database(
#             database_client=database_client,
#             session_id=yandex_request.session_id,
#     )
#
#     if context:
#         return partial(
#                 respond_with_context,
#                 context=context,
#                 database_client=database_client)(request=yandex_request)
#     else:
#         return respond_without_context(request=yandex_request)


# def respond_request_contains_error(
#         *,
#         request: typing.Optional[YandexRequest],
# ) -> typing.Optional[YandexResponse]:
#     if not requests:
#         return None
#     if request.error:
#         return construct_yandex_response_from_yandex_request(
#                 yandex_request=request,
#                 text=request.error,
#                 tts=request.error,
#                 buttons=[],
#                 end_session=True,
#         )
#     return None
def return_the_first_result_from_the_list_of_functions(
        *,
        functions_list: typing.Tuple[typing.Callable, ...],
        debug_mode: bool = False,
        **parameters):

    for f in functions_list:
        result = f(**parameters)
        if result:
            if debug_mode:
                print(f'Function {f.__name__} returned result the first')
            return result

        if debug_mode:
            print(f'Function {f.__name__} did not return result')


@timeit
def nutrition_dialog_2019(event: dict, context: dict) -> dict:
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
    print(f'ЮЗЕР_{log_hash(yandex_request)}: '
          f'{yandex_request.original_utterance}')

    # Functions that don't need any other actions, just return
    # the answer, like ping or error
    response_from_simple = return_the_first_result_from_the_list_of_functions(
            functions_list=standard_responses.simple_functions_list(),
            request=yandex_request,
    )
    if response_from_simple:
        return transform_yandex_response_to_output_result_dict(
                yandex_response=response_from_simple)

    # also simple functions, but context clear is required before
    # returning the result
    func_list = standard_responses.simple_functions_with_context_clear_list()
    response_from_clearing_context = \
        return_the_first_result_from_the_list_of_functions(
                functions_list=func_list,
                request=yandex_request,
        )

    if response_from_clearing_context:
        dynamodb_functions.clear_session(
                session_id=yandex_request.session_id,
                database_client=dynamodb_functions.get_dynamo_client(
                        lambda_mode=yandex_request.aws_lambda_mode))
        return transform_yandex_response_to_output_result_dict(
                yandex_response=response_from_clearing_context)

    # Check if "Удалить" in incoming request
    response_from_delete_function = \
        return_the_first_result_from_the_list_of_functions(
                functions_list=(respond_delete, ),
                request=yandex_request,
        )
    if response_from_delete_function:
        return transform_yandex_response_to_output_result_dict(
                yandex_response=response_from_delete_function)

    # Check if response for previous question in request. Context must exist
    context_dict = dynamodb_functions.fetch_context_from_dynamo_database(
            yandex_request.session_id,
            database_client=dynamodb_functions.get_dynamo_client(
                    lambda_mode=yandex_request.aws_lambda_mode,
            ))

    if context_dict:
        matching_functions = standard_responses.\
            functions_that_respond_to_context_list()
        first_match = return_the_first_result_from_the_list_of_functions(
                functions_list=matching_functions,
                request=yandex_request,
                context=context_dict,
        )
        if first_match:
            return transform_yandex_response_to_output_result_dict(
                    yandex_response=first_match(yandex_request))

    # Check if user statistics is asked


    # Previous functions didn't return result, returning default.
    # Context clearing not needed here, since the user can just make a
    # mistake saying Yes
    print('DEFAULT RESPONSE')
    return transform_yandex_response_to_output_result_dict(
            yandex_response=standard_responses.respond_i_dont_know(
                    request=yandex_request))

    # # Requests that don't require anything
    # for function_without_clearing_context in (
    #         respond_request_contains_error,
    #         standard_responses.respond_ping,
    #         standard_responses.respond_greeting_phrase,
    #         standard_responses.respond_text_too_long,
    # ):
    #     response = function_without_clearing_context(request=yandex_request)
    #     if response:
    #         return transform_yandex_response_to_output_result_dict(
    #                 yandex_response=response)
    #
    # # Requests that require clearing session after finish
    # for function_clearing_session in (
    #         standard_responses.respond_help,
    #         standard_responses.respond_thanks,
    #         standard_responses.respond_hello,
    #         standard_responses.respond_human_meat,
    #         standard_responses.respond_goodbye,
    #         standard_responses.respond_eat_cat,
    #         standard_responses.respond_launch_again,
    #         standard_responses.respond_eat_poop,
    #         standard_responses.respond_think_too_much,
    #         standard_responses.respond_dick,
    #         standard_responses.respond_nothing_to_add,
    #         standard_responses.respond_what_your_name,
    #         standard_responses.respond_smart_ccr,
    #         standard_responses.respond_where_is_saved,
    #         standard_responses.respond_angry,
    #         standard_responses.respond_not_implemented,
    #         standard_responses.respond_launch_another,
    #         standard_responses.respond_shut_up,
    # ):
    #     response = function_clearing_session(request=yandex_request)
    #     if response:
    #         database_client, is_cached = get_boto3_client(
    #                 aws_lambda_mode=bool(context),
    #                 service_name='dynamodb',
    #         )
    #         clear_session(
    #                 session_id=yandex_request.session_id,
    #                 database_client=,
    #         )
    #         return transform_yandex_response_to_output_result_dict(
    #                 yandex_response=response)
    #
    # for function_needed_context in (
    #         check_if_date_in_request,
    #         check_if_yes_in_request,
    #         check_if_no_in_request,
    # ):
    #     chosen_function = function_needed_context(request=yandex_request)
    #     if chosen_function:
    #         database_client = get_boto3_client(
    #                 aws_lambda_mode=bool(context),
    #                 service_name='dynamodb',
    #         )[0]
    #         context = fetch_context_from_dynamo_database(
    #                 database_client=database_client,
    #                 session_id=yandex_request.session_id,
    #         )
    #         if not context:
    #             return transform_yandex_response_to_output_result_dict(
    #                     yandex_response=standard_responses.respond_i_dont_know(
    #                             request=yandex_request))
    #         return chosen_function(
    #                 request=yandex_request,
    #                 context=context,
    #                 database_client=database_client)
    #
    # for functions_that_require_access_to_food_database in (respond_delete, ):
    #     response = functions_that_require_access_to_food_database(
    #             request=yandex_request)
    #
    #     if response:
    #         return transform_yandex_response_to_output_result_dict(
    #                 yandex_response=response)
    #
    # # Here all other variants are checked, now need to try food in request
    #
    # # if no suitable function is added, respond "I don't know"
    # print('DEFAULT RESPONSE')
    # return transform_yandex_response_to_output_result_dict(
    #         yandex_response=standard_responses.respond_i_dont_know(
    #                 request=yandex_request))

    # if yandex_request.error:
    #     # Exit immediatelly in case of mailformed request
    #     return transform_yandex_response_to_output_result_dict(
    #             yandex_response=construct_yandex_response_from_yandex_request(
    #                     yandex_request=yandex_request,
    #                     text=yandex_request.error,
    #                     tts=yandex_request.error,
    #                     buttons=[],
    #                     end_session=True,
    #             ))
    #
    # # Check if boto3 clients are cached, return if not
    # database_client, is_cached = get_boto3_client(
    #                     aws_lambda_mode=yandex_request.aws_lambda_mode,
    #                     service_name='dynamodb',
    #             )
    # if not is_cached and context:
    #     error_text = 'Ой, я кажется не расслышала. ' \
    #                  'Повторите, пожалуйста еще раз?'
    #     return transform_yandex_response_to_output_result_dict(
    #             yandex_response=construct_yandex_response_from_yandex_request(
    #                     yandex_request=yandex_request,
    #                     text=error_text,
    #                     tts=error_text,
    #                     buttons=[],
    #                     end_session=True,
    #             ))
    #
    # # there can be many hardcoded responses, need to check all of them before
    # # querying any databases. This includes DELETE request and "What I
    # # have eaten request"
    # any_predifined_response = respond_one_of_predefined_phrases(
    #         request=yandex_request)
    #
    # if any_predifined_response:
    #     # If predefined answer given, forget all previous food, since
    #     # conversation topic has been already changed
    #     clear_session(
    #             session_id=yandex_request.session_id,
    #             database_client=get_boto3_client(
    #                     aws_lambda_mode=yandex_request.aws_lambda_mode,
    #                     service_name='dynamodb',
    #             )[0]
    #     )
    #     return transform_yandex_response_to_output_result_dict(
    #             yandex_response=any_predifined_response)
    #
    # if yandex_request.is_new_session:
    #     return transform_yandex_response_to_output_result_dict(
    #             yandex_response=respond_request(
    #                     request=yandex_request,
    #                     responding_function=respond_greeting_phrase,
    #             ))
    #
    # return transform_yandex_response_to_output_result_dict(
    #         yandex_response=respond_request(
    #                 request=yandex_request,
    #                 responding_function=respond_existing_session,
    #         )
    # )


if __name__ == '__main__':
    print(nutrition_dialog_2019(
            event=mockers.mock_incoming_event(
                    phrase='Забавная мордаша',
                    has_screen=True),
            context={}))

    # print(nutrition_dialog(
    #         event={
    #             "meta": {
    #                 "client_id": "ru.yandex.searchplugin/7.16 (none none; "
    #                              "android 4.4.2)",
    #                 "interfaces": {
    #                     "account_linking": {},
    #                     "payments": {},
    #                     "screen": {}
    #                 },
    #                 "locale": "ru-RU",
    #                 "timezone": "UTC"
    #             },
    #             "request": {
    #                 "command": "шесть часов сорок пять минут",
    #                 "nlu": {
    #                     "entities": [
    #                         {
    #                             "tokens": {
    #                                 "end": 2,
    #                                 "start": 0
    #                             },
    #                             "type": "YANDEX.DATETIME",
    #                             "value": {
    #                                 "hour": 6,
    #                                 "hour_is_relative": False,
    #                                 "minute": 45,
    #                                 "minute_is_relative": False
    #                             }
    #                         }
    #                     ],
    #                     "tokens": [
    #                         "6",
    #                         "45"
    #                     ]
    #                 },
    #                 "original_utterance": "шесть часов сорок пять минут",
    #                 "type": "SimpleUtterance"
    #             },
    #             "session": {
    #                 "message_id": 33,
    #                 "new": False,
    #                 "session_id": "a34a1050-764ec46f-58b1be34-712df3c0",
    #                 "skill_id": "2142c27e-6062-4899-a43b-806f2eddeb27",
    #                 "user_id": "E401738E621D9AAC04AB162E44F39"
    #                            "B3ABDA23A5CB2FF19E394C1915ED45CF467"
    #             },
    #             "version": "1.0"
    #         },
    #         context={},
    # ))
