from DialogIntents import intents, DialogIntent
from yandex_types import YandexRequest, \
    transform_event_dict_to_yandex_request_object, \
    transform_yandex_response_to_output_result_dict
import mockers
import typing
import hashlib
from dynamodb_functions import clear_context, get_dynamo_client


def nutrition_dialog_with_intents(event, context):
    request: YandexRequest = transform_event_dict_to_yandex_request_object(
            event_dict=event,
            aws_lambda_mode=bool(context),
    )
    print(f'ЮЗЕР_{log_hash(request)}: {request.original_utterance}')
    available_intents: typing.List[DialogIntent] = intents()
    chosen_intent = choose_the_best_intent(available_intents, request)
    print(f'Intent "{chosen_intent.name}" has been chosen')

    response = chosen_intent.respond(request)

    if chosen_intent.should_clear_context:
        print('Clearing previous context from database')
        clear_context(
            session_id=request.session_id,
            database_client=get_dynamo_client(lambda_mode=bool(context)))

    print(f'НАВЫК_{log_hash(response.initial_request)}:'
          f' {response.response_text}')
    return transform_yandex_response_to_output_result_dict(
            yandex_response=response)


def choose_the_best_intent(
        intents_list: typing.List[DialogIntent],
        request: YandexRequest,
) -> DialogIntent:
    if len(intents_list) < 1:
        raise Exception('No intents defined in DialogIntents.py '
                        'Please add at least one')

    intents_sorted_by_time_to_evaluate = sorted(
            intents_list,
            key=lambda x: x.time_to_evaluate,
    )  # it is always better to evaluate the quickest intents first

    chosen_intent = intents_list[-1]  # last one, hope it's default
    for intent in intents_sorted_by_time_to_evaluate:
        evaluation_percent = intent.evaluate(request=request)
        if evaluation_percent == 100:  # first that fits
            chosen_intent = intent
            break

    return chosen_intent


def log_hash(request: YandexRequest) -> str:
    """
    Generates a random 3 digits number for one dialog
    :param request:
    :return:
    """
    session_id = request.session_id
    message_id = str(request.message_id)
    return str(int(hashlib.sha1(session_id.encode()).hexdigest(),
                   16) % (10 ** 3)) + '_' + message_id


if __name__ == '__main__':
    """
    To test locally
    """
    result = nutrition_dialog_with_intents(
            event=mockers.mock_incoming_event(
                    phrase='выход',

            ),
            context={})

    print(result)
