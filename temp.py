import typing
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


def clear_session(
        *,
        session_id: str,
        database_client) -> None:
    database_client.delete_item(TableName='nutrition_sessions',
                                Key={
                                    'id': {
                                        'S': session_id,
                                    }, })


def what_i_have_eaten(*,
                      date: datetime.date,
                      user_id: str,
                      database_client) -> typing.Tuple[str, float]:
    result = database_client.get_item(
            TableName='nutrition_users',
            Key={'id': {'S': user_id}, 'date': {'S': str(date)}})
    if 'Item' not in result:
        return f'Не могу ничего найти за {date}', 0

    total_calories = 0
    full_text = ''
    items_list = json.loads(result['Item']['value']['S'])
    for food_number, food in enumerate(items_list, 1):
        nutrition_dict = food['foods']
        this_food_calories = 0
        for f in nutrition_dict['foods']:
            calories = f.get("nf_calories", 0) or 0
            this_food_calories += calories
            total_calories += calories
        full_text += f'{food_number}. {food["utterance"]} ({this_food_calories})\n'

    full_text += f'Всего: {total_calories} калорий'
    return full_text, total_calories


def delete_food(*,
                database_client,
                date: datetime.date,
                utterance_to_delete: str,
                user_id: str) -> str:
    result = database_client.get_item(
            TableName='nutrition_users',
            Key={'id': {'S': user_id}, 'date': {'S': str(date)}})

    if 'Item' not in result:
        return f'Никакой еды не найдено за {date}'

    items = json.loads(result['Item']['value']['S'])
    items_to_delete = []
    for item in items:
        if item['utterance'] and utterance_to_delete in item['utterance']:
            items_to_delete.append(item)
    if not items_to_delete:
        return f'"{utterance_to_delete}" не найдено за {date}. Найдено: {[i["utterance"] for i in items]}'
    elif len(items_to_delete) > 1:
        return f'Несколько значений подходят: {[i["utterance"] for i in items_to_delete]}. Уточните, какое удалить?'
    items.remove(items_to_delete[0])
    database_client.put_item(TableName='nutrition_users',
                             Item={
                                 'id': {
                                     'S': user_id,
                                 },
                                 'date': {'S': str(date)},
                                 'value': {
                                     'S': json.dumps(items),
                                 }})
    return f'"{utterance_to_delete}" удалено'


def report(*, database_client, date_from: datetime.date, date_to: datetime.date, user_id: str) -> str:
    if date_to < date_from:
        return 'Дата начала должна быть меньше или равна дате окончания'
    if (date_to - date_from).days > 31:
        return 'Максимальный размер отчета один месяц'
    impacted_days = [str(d) for d in [date_from + datetime.timedelta(days=i) for
                                      i in range((date_to-date_from).days + 1)]]

    items = database_client.batch_get_item(
            RequestItems={
                'nutrition_users': {
                    'Keys': [{'id': {'S': user_id}, 'date': {'S': d}} for d in impacted_days]}})
    for item in sorted(items['Responses']['nutrition_users'], key=lambda x: x['date']['S']):
        print('\n' + item['date']['S'])
        food_list = json.loads(item['value']['S'])
        for food in food_list:
            print(food['utterance'])
    return 'OI'


if __name__ == '__main__':
    print(
            report(
                    database_client=client,
                    date_from=datetime.date.today() - datetime.timedelta(days=4),
                    date_to=datetime.date.today(),
                    user_id='C7661DB7B22C25BC151DBC1DB202B5624348B30B4325F2A67BB0721648216065'))

# r = transform_yandex_entities_into_dates([
#     {
#         "tokens": {
#             "end": 4,
#             "start": 3
#         },
#         "type": "YANDEX.NUMBER",
#         "value": 20
#     },
#     {
#         "tokens": {
#             "end": 6,
#             "start": 3
#         },
#         "type": "YANDEX.DATETIME",
#         "value": {
#             "day": 20,
#             "day_is_relative": False,
#             "month": 4,
#             "month_is_relative": False,
#             "year": 2016,
#             "year_is_relative": False
#         }
#     },
#     {
#         "tokens": {
#             "end": 6,
#             "start": 5
#         },
#         "type": "YANDEX.NUMBER",
#         "value": 2016
#     }
# ])
# print(r)
# print(delete_food(
#         database_client=client,
#         date=datetime.date.today(),
#         utterance_to_delete='2000 килограммов блинов',
#         user_id='C7661DB7B22C25BC151DBC1DB202B5624348B30B4325F2A67BB0721648216065'))
# text, c = what_i_have_eaten(
#         date=datetime.date.today() - datetime.timedelta(days=0),
#         user_id='C7661DB7B22C25BC151DBC1DB202B5624348B30B4325F2A67BB0721648216065',
#         database_client=client)
# print(c)
# save_session(
#         session_id='e0b39c4e-aea82aa7-f4046f03-3173ae15',
#         time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#         foods_dict={},
#         utterance='2 сосиски',
#         database_client=client)
# print(check_session(session_id='e0b39c4e-aea82aa7-f4046f03-3173ae15', database_client=client))
