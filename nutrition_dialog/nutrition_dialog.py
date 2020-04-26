from DialogIntents import intents, DialogIntent, Intent99999Default
from yandex_types import YandexRequest, \
    transform_event_dict_to_yandex_request_object, \
    transform_yandex_response_to_output_result_dict
# import mockers
import typing
from dynamodb_functions import clear_context, save_context, write_to_cache_table
import datetime
from dataclasses import replace
from decorators import timeit


@timeit
def nutrition_dialog(event, context):
    print(f'Request: {event}')
    request: YandexRequest = transform_event_dict_to_yandex_request_object(
        event_dict=event,
        aws_lambda_mode=bool(context),
    )
    if (request.user.id ==
            'BC8947C16A1442363544358F1761EA15BD1C81EF522C43D9CE69B9B874DC86D5'):
        request.user.log_hash = 'ME'
    request_str = f'ЮЗЕР_{request.user.log_hash}_Реплика_{request.message_id}'
    if request.user.authentificated:
        request_str += ' (auth)'
    request_str += f': {request.original_utterance}'
    print(request_str)
    available_intents: typing.List[DialogIntent] = intents()
    request = choose_the_best_intent(available_intents, request)
    if not request.chosen_intent:
        print('ERROR! No intent was chosen! Setting to default not to crash')
        request = replace(request, chosen_intent=Intent99999Default)

    print(f'{request.chosen_intent.__name__} has been chosen')
    response = request.chosen_intent.respond(request=request)

    if response.should_clear_context:
        print('Clearing previous context from database')
        clear_context(
            session_id=request.session_id,
            lambda_mode=request.aws_lambda_mode,
        )

    if response.context_to_write:
        print(f'Saving new context to database: {response.context_to_write}')
        save_context(
            response=response,
            event_time=datetime.datetime.now(),
        )

    if response.initial_request.food_dict and \
            response.initial_request.write_to_food_cache and not \
            response.initial_request.food_already_in_cache:
        write_to_cache_table(yandex_response=response)

    print(f'НАВЫК_{response.initial_request.user.log_hash}_Ответ_'
          f'{response.initial_request.message_id}'
          f':____________________'
          f' {response.response_text}')
    return transform_yandex_response_to_output_result_dict(
        yandex_response=response)


def choose_the_best_intent(
        intents_list: typing.List[DialogIntent],
        request: YandexRequest,
) -> YandexRequest:
    if len(intents_list) < 1:
        raise Exception('No intents defined in DialogIntents.py '
                        'Please add at least one')

    intents_sorted_by_time_to_evaluate = sorted(
        intents_list,
        key=lambda x: x.time_to_evaluate,
    )  # it is always better to evaluate the quickest intents first

    for intent in intents_sorted_by_time_to_evaluate:
        request = intent.evaluate(request=request)
        if intent in request.intents_matching_dict and \
                request.intents_matching_dict[intent] >= 100:
            request = replace(request, chosen_intent=intent)
            break

    return request


# def log_hash(request: YandexRequest) -> str:
#     """
#     Generates a random 3 digits number for one dialog
#     :param request:
#     :return: "589" for example
#     """
#     session_id = request.session_id
#     message_id = str(request.message_id)
#     return str(int(hashlib.sha1(session_id.encode()).hexdigest(),
#                    16) % (10 ** 3)) + '_Реплика ' + message_id


if __name__ == '__main__':
    """
    To test locally
    """

    # result = nutrition_dialog(
    #         event=mockers.mock_incoming_event(
    #             phrase='удали лисичку',
    #             timezone='UTC+3',
    #             write_to_food_cache=False,
    #
    #         ),
    #         context={})
    false = False
    true = True
    result = nutrition_dialog({
        "meta":    {
            "locale":     "ru-RU",
            "timezone":   "UTC",
            "client_id":  "ru.yandex.searchplugin/7.16 (none none; android 4.4.2)",
            "interfaces": {
                "screen":          {},
                "payments":        {},
                "account_linking": {}
            }
        },
        "session": {
            "message_id":  2,
            "session_id":  "a3fedb22-0e5d-4836-8ca9-3b047b7a343e",
            "skill_id":    "2142c27e-6062-4899-a43b-806f2eddeb27",
            "user_id":     "E401738E621D9AAC04AB162E44F39B3ABDA23A5CB2FF19E394C1915ED45CF467",
            "application": {
                "application_id": "E401738E621D9AAC04AB162E44F39B3ABDA23A5CB2FF19E394C1915ED45CF467"
            },
            "new":         false
        },
        "request": {
            "command":            "морковь 200 грамм",
            "original_utterance": "морковь 200 грамм",
            "nlu":                {
                "tokens":   [
                    "морковь",
                    "200",
                    "грамм"
                ],
                "entities": [
                    {
                        "type":   "YANDEX.NUMBER",
                        "tokens": {
                            "start": 1,
                            "end":   2
                        },
                        "value":  200
                    }
                ],
                "intents":  {}
            },
            "markup":             {
                "dangerous_context": false
            },
            "type":               "SimpleUtterance"
        },
        "state":   {
            "session": {}
        },
        "version": "1.0"
    }, {})

    print(f'Response: {result}')
