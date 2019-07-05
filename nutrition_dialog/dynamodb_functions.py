import datetime
import json
from decorators import timeit
from botocore.vendored.requests.exceptions import ReadTimeout, ConnectTimeout
import botocore.client
import boto3
import typing


# This cache is useful because AWS lambda can keep it's state, so no
# need to restantiate connections again. It is used in get_boto3_client
# function, I know it is a mess, but 100 ms are 100 ms
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
            return new_client, False

        # saving to cache to to spend time to create it next time
        client = new_client
        return client

    return closure()


@timeit
def get_boto3_client(
        *,
        aws_lambda_mode: bool,
        service_name: str,
        profile_name: str = 'kreodont',
        connect_timeout: float = 0.2,
        read_timeout: float = 0.4,
) -> typing.Tuple[typing.Optional[boto3.client], bool]:
    """
    Dirty function to fetch s3_clients
    :param connect_timeout:
    :param read_timeout:
    :param aws_lambda_mode:
    :param service_name:
    :param profile_name:
    :return:
    """
    known_services = ['translate', 'dynamodb', 's3']
    if service_name in global_cached_boto3_clients:
        print(f'{service_name} client taken from cache!')
        return global_cached_boto3_clients[service_name], True

    if service_name not in known_services:
        raise Exception(
                f'Not known service '
                f'name {service_name}. The following '
                f'service names known: {", ".join(known_services)}')

    if aws_lambda_mode:
        client = boto3.client(
                service_name,
                config=botocore.client.Config(
                        connect_timeout=connect_timeout,
                        read_timeout=read_timeout,
                        parameter_validation=False,
                        retries={'max_attempts': 0},
                ),
        )
    else:
        client = boto3.Session(profile_name=profile_name).client(service_name)
        return client, False

    # saving to cache to to spend time to create it next time
    global_cached_boto3_clients[service_name] = client
    return client, False


@timeit
def update_user_table(
        *,
        database_client,
        event_time: datetime.datetime,
        foods_dict: dict,
        utterance: str,
        user_id: str):
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
def clear_session(
        *,
        session_id: str,
        database_client) -> None:
    try:
        database_client.delete_item(TableName='nutrition_sessions',
                                    Key={
                                        'id': {
                                            'S': session_id,
                                        }, })
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
        initial_phrase: str,
        nutrition_dict: dict,
        database_client,
        keys_dict: dict) -> None:
    database_client.put_item(TableName='nutrition_cache',
                             Item={
                                 'initial_phrase': {
                                     'S': initial_phrase,
                                 },
                                 'response': {
                                     'S': json.dumps(nutrition_dict),
                                 }})
    database_client.put_item(TableName='nutrition_cache',
                             Item={
                                 'initial_phrase': {
                                     'S': '_key',
                                 },
                                 'response': {
                                     'S': json.dumps(keys_dict),
                                 }})


@timeit
def get_from_cache_table(
        *,
        request_text: str,
        database_client: boto3.client) -> typing.Tuple[dict, dict]:
    keys_dict = {}
    food_dict = {}
    try:
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
                                    'S': request_text},
                            }
                        ]}})
    except (ConnectTimeout, ReadTimeout):
        return {'error': 'timeout'}, {'error': 'timeout'}

    for item in items['Responses']['nutrition_cache']:
        if item['initial_phrase']['S'] == '_key':
            keys_dict = json.loads(item['response']['S'])
        if item['initial_phrase']['S'] == request_text:
            food_dict = json.loads(item['response']['S'])

    return keys_dict, food_dict


@timeit
def fetch_context_from_dynamo_database(
        *,
        session_id: str,
        database_client: boto3.client
) -> dict:
    try:
        result = database_client.get_item(
                TableName='nutrition_sessions',
                Key={'id': {'S': session_id}})

    except (ConnectTimeout, ReadTimeout):
        return {}

    if 'Item' not in result:
        return {}
    else:
        try:
            return json.loads(result['Item']['value']['S'])
        except json.decoder.JSONDecodeError:
            return {}


@timeit
def delete_food(*,
                database_client: boto3.client,
                date: datetime.date,
                list_of_food_to_delete_dicts: typing.List[dict],
                list_of_all_food_dicts: typing.List[dict],
                user_id: str,
                ) -> str:
    result_list = [d for d in list_of_all_food_dicts if
                   d not in list_of_food_to_delete_dicts]

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
        database_client: boto3.client,
        date: datetime.date,
        food_name_to_find: str,
        user_id: str,
) -> typing.List[dict]:
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
        database_client: boto3.client,
        date: datetime.date,
        user_id: str,
) -> typing.List[dict]:
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
