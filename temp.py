import boto3
import json
import datetime

session = boto3.Session(profile_name='kreodont')
client = session.client('dynamodb')


def save_session(*, session_id: str, time: str, foods_dict: dict, utterance, database_client) -> None:
    database_client.put_item(TableName='nutrition_sessions',
                             Item={
                                 'id': {
                                     'S': session_id,
                                 },
                                 'value': {
                                     'S': json.dumps({'time': time, 'foods': foods_dict, 'utterance': utterance}),
                                 }})


def check_session(*, session_id: str, database_client) -> dict:
    result = database_client.get_item(
            TableName='nutrition_sessions', Key={'id': {'S': session_id}})
    if 'Item' not in result:
        return {}
    else:
        return json.loads(result['Item']['value']['S'])


def update_user_table(*, database_client, time: datetime.datetime, foods_dict: dict, utterance: str, user_id: str):
    result = database_client.get_item(
            TableName='nutrition_users',
            Key={'id': {'S': user_id}, 'date': {'S': str(time.date())}})
    item_to_save = []
    if 'Item' in result:
        item_to_save = json.loads(result['Item']['value']['S'])
    item_to_save.append({'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'foods': foods_dict, 'utterance': utterance})
    database_client.put_item(TableName='nutrition_users',
                             Item={
                                 'id': {
                                     'S': user_id,
                                 },
                                 'date': {'S': str(time.date())},
                                 'value': {
                                     'S': json.dumps(item_to_save),
                                 }})


# save_session(
#         session_id='e0b39c4e-aea82aa7-f4046f03-3173ae15',
#         time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#         foods_dict={},
#         utterance='2 сосиски',
#         database_client=client)
# print(check_session(session_id='e0b39c4e-aea82aa7-f4046f03-3173ae15', database_client=client))

update_user_table(
        database_client=client,
        time=datetime.datetime.now(),
        foods_dict={'food1': 'hahaa'},
        utterance='Привет',
        user_id='574027C0C2A1FEA0E65694182E19C8AB69A56FC404B938928EF74415CF05137E')
