from functools import partial
from botocore.vendored import requests
import json
import random


def construct_response(*,
                       text,
                       end_session=False,
                       tts=None,
                       session='',
                       message_id='',
                       user_id='',
                       verions='1.0',
                       debug=False,
                       ):
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


def _make_request_to_kodi(*, endpoint: str, simulate: bool = False) -> None:
    if simulate:
        return

    try:
        requests.post('https://omertu-googlehomekodi-60.glitch.me/' + endpoint,
                      data=json.dumps({'token': ''}),
                      headers={'content-type': 'application/json'},
                      timeout=0.1)
    except requests.exceptions.ReadTimeout:
        pass


def yandex_request(event: dict, context: dict) -> dict:
    """
    Parses request from yandex and returns response
    Example 1 - First response
    >>> yandex_request({
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
    {'response': {'text': 'Ну, пока я умею только управлять Kodi. Скажи запустить, остановить или пауза.',
    'tts': 'Ну, пока я умею только управлять Kodi. Скажи запустить, остановить или пауза.',
    'end_session': False}, 'session': {'session_id': 'f12a4adc-ca1988d-1978333d-3ffd2ca6', 'message_id': 1,
    'user_id': '574027C0C2A1FEA0E65694182E19C8AB69A56FC404B938928EF74415CF05137E'}, 'version': '1.0'}


    :param event:
    :param context:
    :return:
    """
    make_request_to_kodi = partial(_make_request_to_kodi, simulate=True)  # change to False for real work

    debug = bool(context)
    if debug:
        print(event)

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
                                              debug=debug,
                                              )

    is_new_session = session.get('new')
    help_text = 'Я могу запустить видео, остановить его, или поставить на паузу. В данный ' \
                'момент навык является приватным. Чтобы выйти из навыка, скажите Выход.'
    short_help_texts = ['Скажите Запустить, Остановить, или Пауза',
                        'Запустить, Остановить, или поставить на Паузу - вот что я умею',
                        'Прекрасно, но я умею только запускать, останавливать и ставить на паузу видео',
                        'А попробуйте лучше сказать Запустить, Остановить или Пауза. С этим я прекрасно справляюсь'
                        ]
    if is_new_session:
        return construct_response_with_session(text=help_text)

    tokens = request.get('nlu').get('tokens')  # type: list
    if ('запустить' in tokens or
            'запуск' in tokens or
            'выбрать' in tokens or
            'выбор' in tokens or
            'выбрать' in tokens or
            'запусти' in tokens):
        make_request_to_kodi(endpoint='navselect')
        return construct_response_with_session(text='Запускаю')

    if ('остановить' in tokens or
            'стоп' in tokens or
            'остановись' in tokens or
            'останови' in tokens):
        make_request_to_kodi(endpoint='stop')
        return construct_response_with_session(text='Останавливаю')

    if [t for t in tokens if 'пауз' in t]:
        make_request_to_kodi(endpoint='playpause')
        return construct_response_with_session(text='Выполняю')

    if ('помощь' in tokens or
            'справка' in tokens or
            'хелп' in tokens or
            'информация' in tokens or
            '?' in tokens or
            'help' in tokens):
        return construct_response_with_session(text=help_text)

    if ('выход' in tokens or
            'выйти' in tokens or
            'пока' in tokens or
            'выйди' in tokens or
            'до свидания' in tokens):
        return construct_response_with_session(text='До свидания', end_session=True)

    return construct_response_with_session(text=random.choice(short_help_texts))


if __name__ == '__main__':
    import doctest

    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE, verbose=False)
