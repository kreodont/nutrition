import datetime
import json
from decorators import timeit
from botocore.vendored.requests.exceptions import ReadTimeout, ConnectTimeout
import botocore.client
import boto3
import typing
from DialogContext import DialogContext


# This cache is useful because AWS lambda can keep it's state, so no
# need to restantiate connections again. It is used in get_boto3_client
# function, I know it is a mess, but 100 ms are 100 ms
from yandex_types import YandexResponse, YandexRequest

global_cached_boto3_clients = {}


def get_dynamo_client(
        *,
        lambda_mode: bool,
        profile_name: str = 'kreodont',
        connect_timeout: float = 0.2,
        read_timeout: float = 0.4,
) -> boto3.client:
    client = None

    def closure():
        nonlocal client
        if client:
            print('Dynamo client fetched from CACHE!')
            return client
        if lambda_mode:
            new_client = boto3.client(
                    'dynamodb',
                    config=botocore.client.Config(
                            connect_timeout=connect_timeout,
                            read_timeout=read_timeout,
                            parameter_validation=False,
                            retries={'max_attempts': 0},
                    ),
            )
        else:
            new_client = boto3.Session(profile_name=profile_name).client(
                'dynamodb')
            return new_client

        # saving to cache to to spend time to create it next time
        client = new_client
        return client

    return closure()


@timeit
def update_user_table(
        *,
        database_client,
        event_time: datetime.datetime,
        foods_dict: dict,
        utterance: str,
        user_id: str):
    print(f'Saving food for user: "{utterance}"')
    result = database_client.get_item(
            TableName='nutrition_users',
            Key={'id': {'S': user_id}, 'date': {'S': str(event_time.date())}})
    item_to_save = []
    if 'Item' in result:
        item_to_save = json.loads(result['Item']['value']['S'])
    item_to_save.append({
        'time': event_time.strftime('%Y-%m-%d %H:%M:%S'),
        'foods': foods_dict,
        'utterance': utterance})
    try:
        database_client.put_item(TableName='nutrition_users',
                                 Item={
                                     'id': {
                                         'S': user_id,
                                     },
                                     'date': {'S': str(event_time.date())},
                                     'value': {
                                         'S': json.dumps(item_to_save),
                                     }})

    except (ReadTimeout, ConnectTimeout):
        pass


@timeit
def save_session(
        *,
        session_id: str,
        event_time: datetime.datetime,
        foods_dict: dict,
        utterance: str,
        database_client) -> None:
    database_client.put_item(
            TableName='nutrition_sessions',
            Item={
                'id': {
                    'S': session_id,
                },
                'value': {
                    'S': json.dumps({
                        'time': event_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'foods': foods_dict,
                        'utterance': utterance}),
                }})


@timeit
def write_to_cache_table(
        *,
        yandex_response: YandexResponse) -> None:
    database_client = get_dynamo_client(
        lambda_mode=yandex_response.initial_request.aws_lambda_mode)
    initial_phrase = yandex_response.initial_request.original_utterance
    nutrition_dict = yandex_response.initial_request.food_dict
    keys_dict = yandex_response.initial_request.api_keys
    print(f'Saving into cache table nutrients for the following: '
          f'{initial_phrase}')
    database_client.put_item(TableName='nutrition_cache',
                             Item={
                                 'initial_phrase': {
                                     'S': initial_phrase,
                                 },
                                 'response': {
                                     'S': json.dumps(nutrition_dict),
                                 }})
    if keys_dict:  # Only if we have updated key dict. NOT to overwrite with
        # empty dict
        database_client.put_item(TableName='nutrition_cache',
                                 Item={
                                     'initial_phrase': {
                                         'S': '_key',
                                     },
                                     'response': {
                                         'S': json.dumps(keys_dict),
                                     }})


def write_keys_to_cache_table(*, keys_dict: dict, lambda_mode: bool):
    if not keys_dict:
        return
    database_client = get_dynamo_client(lambda_mode=lambda_mode)
    database_client.put_item(TableName='nutrition_cache',
                             Item={
                                 'initial_phrase': {
                                     'S': '_key',
                                 },
                                 'response': {
                                     'S': json.dumps(keys_dict),
                                 }})


@timeit
def get_from_cache_table(*, yandex_requext: YandexRequest) -> YandexRequest:
    keys_dict = {}
    food_dict = {}
    try:
        print(f'Searching for "{yandex_requext.command}" in cache table')
        database_client = get_dynamo_client(
                lambda_mode=yandex_requext.aws_lambda_mode)
        items = database_client.batch_get_item(
                RequestItems={
                    'nutrition_cache': {
                        'Keys': [
                            {
                                'initial_phrase': {
                                    'S': '_key'},
                            },
                            {
                                'initial_phrase': {
                                    'S': yandex_requext.command},
                            }
                        ]}})
    except (ConnectTimeout, ReadTimeout):
        print('Timeout during Food Cache table request')
        return yandex_requext

    for item in items['Responses']['nutrition_cache']:
        if item['initial_phrase']['S'] == '_key':
            keys_dict = json.loads(item['response']['S'])
        if item['initial_phrase']['S'] == yandex_requext.command:
            food_dict = json.loads(item['response']['S'])
    if food_dict and 'foods' in food_dict:
        print(f'"{yandex_requext.command}" found in cache!')
        yandex_requext = yandex_requext.set_food_dict(food_dict=food_dict)
        yandex_requext = yandex_requext.set_food_already_in_cache()
    else:
        yandex_requext = yandex_requext.set_api_keys(keys_dict)

    return yandex_requext


@timeit
def fetch_context_from_dynamo_database(
        *,
        session_id: str,
        database_client: boto3.client
) -> typing.Optional[DialogContext]:
    try:
        result = database_client.get_item(
                TableName='nutrition_sessions',
                Key={'id': {'S': session_id}})

    except (ConnectTimeout, ReadTimeout):
        print('Timeout when tried to load context')
        return None

    if 'Item' not in result:
        print('No context found')
        return DialogContext.empty_context()
    else:
        try:
            json_dict = json.loads(result['Item']['value']['S'])
            food_data = json_dict.get('foods', {})
            intent_originator_name = json_dict.get(
                    'intent_originator_name',
                    'Intent originator not defined')

            matching_intents_names = json_dict.get('matching_intents_names', ())
            specifying_question = json_dict.get(
                    'specifying_question',
                    'Specifying question not defined')

            user_initial_phrase = json_dict.get(
                    'user_initial_phrase',
                    'Initial phase not defined')

            context = DialogContext(
                    food_dict=food_data,
                    intent_originator_name=intent_originator_name,
                    matching_intents_names=matching_intents_names,
                    specifying_question=specifying_question,
                    user_initial_phrase=user_initial_phrase,
            )
            print(f'Loaded context: {context}')
            return context
        except json.decoder.JSONDecodeError:
            return DialogContext.empty_context()


@timeit
def save_context(
        *,
        response: YandexResponse,
        table_name: str = 'nutrition_sessions',
        event_time: datetime.datetime = datetime.datetime.now()
) -> YandexResponse:
    client = get_dynamo_client(
        lambda_mode=response.initial_request.aws_lambda_mode)
    client.put_item(
            TableName=table_name,
            Item={
                'id': {
                    'S': response.initial_request.session_id,
                },
                'value': {
                    'S': json.dumps({
                        'time': event_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'foods': response.context_to_write.food_dict,
                        'intent_originator_name':
                            response.context_to_write.intent_originator_name,
                        'user_initial_phrase':
                            response.context_to_write.user_initial_phrase,
                        'specifying_question':
                            response.context_to_write.specifying_question,
                        'matching_intents_names':
                            response.context_to_write.matching_intents_names,
                    }),
                }})
    return response


@timeit
def clear_context(
        *,
        session_id: str,
        database_client,
) -> None:
    try:
        database_client.delete_item(TableName='nutrition_sessions',
                                    Key={
                                        'id': {
                                            'S': session_id,
                                        }, })
    except (ReadTimeout, ConnectTimeout):
        pass


@timeit
def delete_food(*,
                date: datetime.date,
                list_of_food_to_delete_dicts: typing.List[dict],  # list of
                # foods that should be deleted
                list_of_all_food_dicts: typing.List[dict],  # list of food
                # that exist in database
                user_id: str,
                lambda_mode: bool,
                ) -> str:

    database_client = get_dynamo_client(lambda_mode=lambda_mode)
    # Filtering list of existing food leaving only food that NOT
    # specified in list_of_food_to_delete_dicts
    result_list = [d for d in list_of_all_food_dicts if
                   d not in list_of_food_to_delete_dicts]

    # Saving new food list
    result = database_client.put_item(TableName='nutrition_users',
                                      Item={
                                          'id': {
                                              'S': user_id,
                                          },
                                          'date': {'S': str(date)},
                                          'value': {
                                              'S': json.dumps(result_list),
                                          }})
    return result


def find_food_by_name_and_day(
        *,
        date: datetime.date,
        food_name_to_find: str,
        user_id: str,
        lambda_mode: bool,
) -> typing.List[dict]:
    database_client = get_dynamo_client(lambda_mode=lambda_mode)
    result = database_client.get_item(
            TableName='nutrition_users',
            Key={
                'id': {'S': user_id},
                'date': {'S': str(date)},
            })

    if 'Item' not in result:
        return []

    items: typing.List[dict] = json.loads(result['Item']['value']['S'])
    found_items = []

    for item in items:
        if (item['utterance'] and food_name_to_find.strip() ==
                item['utterance'].replace(',', '').strip()):
            found_items.append(item)

    return found_items


def find_all_food_names_for_day(
        *,
        date: datetime.date,
        user_id: str,
        lambda_mode: bool,
) -> typing.List[dict]:
    database_client = get_dynamo_client(lambda_mode=lambda_mode)
    result = database_client.get_item(
            TableName='nutrition_users',
            Key={
                'id': {'S': user_id},
                'date': {'S': str(date)},
            })

    if 'Item' not in result:
        return []

    items: typing.List[dict] = json.loads(result['Item']['value']['S'])
    return [i for i in items if 'foods' in i and 'error' not in i['foods']]
    # found_items = []
    #
    # for item in items:
    #     if (item['utterance'] and food_name.strip() ==
    #             item['utterance'].replace(',', '').strip()):
    #         found_items.append(item)
    #
    # return found_items
