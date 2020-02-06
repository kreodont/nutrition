from DialogIntents import intents, DialogIntent
from yandex_types import YandexRequest, \
    transform_event_dict_to_yandex_request_object, \
    transform_yandex_response_to_output_result_dict
import mockers
import typing


def nutrition_dialog_with_intents(event, context):
    request: YandexRequest = transform_event_dict_to_yandex_request_object(
            event_dict=event,
            aws_lambda_mode=bool(context),
    )
    print(request)
    available_intents: typing.List[DialogIntent] = intents()
    if len(available_intents) < 1:
        raise Exception('No intents defined in DialogIntents.py')

    intents_sorted_by_time_to_evaluate = sorted(
            available_intents,
            key=lambda x: x.time_to_evaluate,
    )  # it is always better to evaluate the quickest intents first

    chosen_intent = available_intents[-1]
    for intent in intents_sorted_by_time_to_evaluate:
        evaluation_percent = intent.evaluate(request=request)
        if evaluation_percent == 100:  # first that fits
            chosen_intent = intent
            print(f'Intent {chosen_intent.name} has been chosen')
            break

    response = chosen_intent.respond(request)
    print(response)
    return transform_yandex_response_to_output_result_dict(
            yandex_response=response)


if __name__ == '__main__':
    """
    To test locally
    """
    print(nutrition_dialog_with_intents(
            event=mockers.mock_incoming_event(
                    phrase='Забавная мордаша',
                    has_screen=True),
            context={}))
