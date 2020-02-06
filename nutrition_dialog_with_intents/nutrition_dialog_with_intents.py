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
    if len(available_intents) < 1:
        raise Exception('No intents defined in DialogIntents.py')

    intents_sorted_by_time_to_evaluate = sorted(
            available_intents,
            key=lambda x: x.time_to_evaluate,
    )  # it is always better to evaluate the quickest intents first

    chosen_intent = available_intents[-1]  # last one, hope it's default
    for intent in intents_sorted_by_time_to_evaluate:
        evaluation_percent = intent.evaluate(request=request)
        if evaluation_percent == 100:  # first that fits
            chosen_intent = intent
            print(f'Intent "{chosen_intent.name}" has been chosen')
            break

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
    nutrition_dialog_with_intents(
            event=mockers.mock_incoming_event(
                    phrase='помощь',

            ),
            context={})
