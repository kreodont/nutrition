from functools import partial
import boto3
# from botocore.vendored import requests
import json
import random
import time


def construct_response(*,
                       text,
                       end_session=False,
                       tts=None,
                       session='',
                       message_id='',
                       user_id='',
                       verions='1.0',
                       debug=False,
                       ) -> dict:
    if tts is None:
        tts = text

    response = {
        "response": {
            "text": text,
            "tts": tts,
            "end_session": end_session
        },
        "session": {
            "session_id": session,
            "message_id": message_id,
            "user_id": user_id
        },
        "version": verions
    }

    if debug:
        print(response)

    return response


def nutrition_dialog(event: dict, context: dict) -> dict:
    """
    Parses request from yandex and returns response
    Example 1 - First response
    >>> nutrition_dialog({
    ...    'meta': {
    ...       'client_id': 'ru.yandex.searchplugin/7.16 (none none; android 4.4.2)',
    ...        'interfaces': {
    ...            'screen': {},
    ...        },
    ...        'locale': 'ru-RU',
    ...        'timezone': 'UTC',
    ...    },
    ...    'request': {
    ...        'command': 'Ghb',
    ...        'nlu': {
    ...            'entities': [],
    ...            'tokens': ['ghb'],
    ...        },
    ...        'original_utterance': 'Ghb',
    ...        'type': 'SimpleUtterance',
    ...    },
    ...    'session':
    ...        {
    ...            'message_id': 1,
    ...            'new': False,
    ...            'session_id': 'f12a4adc-ca1988d-1978333d-3ffd2ca6',
    ...            'skill_id': '5799f33a-f13b-459f-b7ff-3039666f2b8b',
    ...            'user_id': '574027C0C2A1FEA0E65694182E19C8AB69A56FC404B938928EF74415CF05137E',
    ...        },
    ...    'version': '1.0',
    ... },
    ...        {})
    {'response': {'text': 'Это не похоже на название еды. Попробуйте сформулировать иначе',
    'tts': 'Это не похоже на название еды. Попробуйте сформулировать иначе', 'end_session': False},
    'session': {'session_id': 'f12a4adc-ca1988d-1978333d-3ffd2ca6', 'message_id': 1,
    'user_id': '574027C0C2A1FEA0E65694182E19C8AB69A56FC404B938928EF74415CF05137E'}, 'version': '1.0'}


    :param event:
    :param context:
    :return:
    """
    start_time = time.time()
    default_texts = ['Это не похоже на название еды. Попробуйте сформулировать иначе',
                     'Хм. Не могу понять что это',
                     'Что, простите?',
                     ]
    event.setdefault('debug', bool(context))

    request = event.get('request')
    if not request:
        return construct_response(text='Неверный запрос, нет поля request')

    session = event.get('session')  # type: dict
    if not session:
        return construct_response(text='Неверный запрос, нет поля session')

    construct_response_with_session = partial(construct_response,
                                              session=session['session_id'],
                                              user_id=session['user_id'],
                                              message_id=session.get('message_id'),
                                              debug=event['debug'],
                                              )

    is_new_session = session.get('new')
    help_text = 'Скажите мне сколько и чего вы съели, а я скажу сколько это калорий. ' \
                'Например: картофельное пюре, 300 грамм'
    if is_new_session:
        return construct_response_with_session(text=help_text)

    tokens = request.get('nlu').get('tokens')  # type: list
    if context:
        lambda_client = boto3.client('lambda')
        translation_client = boto3.client('translate')
    else:
        aws_session = boto3.Session(profile_name='kreodont')
        lambda_client = aws_session.client('lambda')
        translation_client = boto3.Session(profile_name='kreodont').client('translate')

    if 'помощь' in tokens or 'справка' in tokens:
        return construct_response_with_session(text=help_text)

    full_phrase = request.get('original_utterance')
    # full_phrase_translated = lambda_client.invoke(
    #         FunctionName='translation_lambda',
    #         InvocationType='RequestResponse',
    #         Payload=json.dumps({'phrase_to_translate': full_phrase},
    #                            ))['Payload'].read().decode('utf-8')
    full_phrase_translated = translation_client.translate_text(Text=full_phrase,
                                                               SourceLanguageCode='ru',
                                                               TargetLanguageCode='en'
                                                               ).get('TranslatedText')

    if event['debug']:
        print(f'Translated: {full_phrase_translated}')

    nutrionix_dict_str = lambda_client.invoke(
            FunctionName='nutritionix_lambda',
            InvocationType='RequestResponse',
            Payload=json.dumps({'phrase': full_phrase_translated}))['Payload'].read().decode('utf-8')

    nutrionix_dict = json.loads(nutrionix_dict_str)

    # if event['debug']:
    #     print(f'Response from Nuntionix: {nutrionix_dict}')

    if 'foods' not in nutrionix_dict or not nutrionix_dict['foods']:
        if event['debug']:
            print(f'Tag foods not found or empty')
        return construct_response_with_session(text=random.choice(default_texts))

    response_text = ''  # type: str
    total_calories = 0.0  # type: float

    if len(nutrionix_dict['foods']) == 1:
        if event['debug']:
            end_time = time.time()
            print(f'{(end_time - start_time) * 1000} ms')
            print(response_text)

        return construct_response_with_session(text=f'{nutrionix_dict["foods"][0]["nf_calories"]} калорий')

    for number, food_name in enumerate(nutrionix_dict['foods']):
        total_calories += nutrionix_dict["foods"][number]["nf_calories"]
        response_text += f'{number + 1}. {int(nutrionix_dict["foods"][number]["nf_calories"])} калорий\n'

    if len(nutrionix_dict["foods"]) > 1:
        response_text += f'Итого: {int(total_calories)} калорий'

    if event['debug']:
        end_time = time.time()
        print(f'{(end_time - start_time) * 1000} ms')
        print(response_text)

    return construct_response_with_session(text=response_text)


if __name__ == '__main__':
    nutrition_dialog({
        'meta': {
            'client_id': 'ru.yandex.searchplugin/7.16 (none none; android 4.4.2)',
            'interfaces': {
                'screen': {},
            },
            'locale': 'ru-RU',
            'timezone': 'UTC',
        },
        'request': {
            'command': 'Картофельное пюре, 300 г',
            'nlu': {
                'entities': [],
                'tokens': ['ghb'],
            },
            'original_utterance': 'Картофельное пюре, 300 г',
            'type': 'SimpleUtterance',
        },
        'session':
            {
                'message_id': 1,
                'new': False,
                'session_id': 'f12a4adc-ca1988d-1978333d-3ffd2ca6',
                'skill_id': '5799f33a-f13b-459f-b7ff-3039666f2b8b',
                'user_id': '574027C0C2A1FEA0E65694182E19C8AB69A56FC404B938928EF74415CF05137E',
            },
        'version': '1.0',
        'debug': True,
    },
            {})
    # import doctest
    # doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE, verbose=False)
