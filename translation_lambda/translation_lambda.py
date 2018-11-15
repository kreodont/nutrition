import boto3
import time


def translation_lambda(event: dict, context: dict) -> str:
    """
    Translates phrase using AWS translate service
    :param event: input parameters, dict of strings
    :param context: indicates if it runs in AWS environment
    :return: string translation

    Example 1 (Standard case):
    >>> translation_lambda({'phrase_to_translate': 'булка'}, {})
    {'phrase_to_translate': 'булка', 'target_language': 'en', 'source_language': 'ru'}
    'A bun'

    Example 2 (Empty phrase):
    >>> translation_lambda({'phrase_to_translate': ''}, {})
    {'phrase_to_translate': '', 'target_language': 'en', 'source_language': 'ru'}
    ''

    Example 3 (Unable to translate):
    >>> translation_lambda({'phrase_to_translate': 'гыбламфмя'}, {})
    {'phrase_to_translate': 'гыбламфмя', 'target_language': 'en', 'source_language': 'ru'}
    'Gyblamfma'

    """
    lambda_mode = bool(context)  # type: bool
    event.setdefault('phrase_to_translate', '')
    event.setdefault('target_language', 'en')
    event.setdefault('source_language', 'ru')
    event.setdefault('debug', bool(context))
    if event['debug']:
        print(event)

    if event['phrase_to_translate'] == '':
        return ''

    if lambda_mode:
        translation_client = boto3.client('translate')
    else:
        translation_client = boto3.Session(profile_name='kreodont').client('translate')

    start_time = time.time()
    response = translation_client.translate_text(Text=event['phrase_to_translate'],
                                                 SourceLanguageCode=event['source_language'],
                                                 TargetLanguageCode=event['target_language']
                                                 ).get('TranslatedText')
    end_time = time.time()

    if event['debug']:
        print(f'{(end_time - start_time) * 1000} ms')
        print(response)

    return response


if __name__ == '__main__':
    translation_lambda({'phrase_to_translate': 'слово', 'debug': True}, {})
    # import doctest
    # doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE, verbose=False)
