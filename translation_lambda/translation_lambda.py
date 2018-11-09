import boto3


def translation_lambda(event: dict, context: dict) -> str:
    lambda_mode = bool(context)  # type: bool
    event.setdefault('phrase_to_translate', '')
    event.setdefault('target_language', 'en')
    event.setdefault('source_language', 'ru')
    if event['phrase_to_translate'] == '':
        return ''

    if lambda_mode:
        translation_client = boto3.client('translate')
    else:
        translation_client = boto3.Session(profile_name='kreodont').client('translate')

    return translation_client.translate_text(Text=event['phrase_to_translate'],
                                             SourceLanguageCode=event['source_language'],
                                             TargetLanguageCode=event['target_language']).get('TranslatedText')


if __name__ == '__main__':
    print(translation_lambda({'phrase_to_translate': 'булка'}, {}))