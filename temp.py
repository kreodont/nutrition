import boto3
import json
import datetime
import dateutil

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


def report(
        *,
        database_client,
        date_from: datetime.date,
        date_to: datetime.date,
        user_id: str,
        current_timezone: str) -> str:
    if date_to < date_from:
        return 'Дата начала должна быть меньше или равна дате окончания'
    if (date_to - date_from).days > 31:
        return 'Максимальный размер отчета один месяц'
    week_days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье', ]
    impacted_days = [str(d) for d in [date_from + datetime.timedelta(days=i) for
                                      i in range((date_to-date_from).days + 1)]]

    total_calories = 0
    total_fat = 0.0
    total_carbohydrates = 0.0
    total_protein = 0.0
    total_sugar = 0.0

    items = database_client.batch_get_item(
            RequestItems={
                'nutrition_users': {
                    'Keys': [{'id': {'S': user_id}, 'date': {'S': d}} for d in impacted_days]}})
    for item in sorted(items['Responses']['nutrition_users'], key=lambda x: x['date']['S']):
        date = dateutil.parser.parse(item['date']['S']).date()
        print(f'\n{date} ({week_days[date.isoweekday() - 1]})')
        food_list = json.loads(item['value']['S'])
        day_calories = 0
        day_protein = 0
        day_fat = 0
        day_sugar = 0
        day_carbohydrates = 0
        for food in food_list:
            nutrition_dict = food['foods']
            food_calories = 0
            food_protein = 0
            food_fat = 0
            food_carbohydrates = 0
            food_sugar = 0
            food_time = dateutil.parser.parse(food['time'])
            food_time = food_time.replace(tzinfo=dateutil.tz.gettz('UTC')).\
                astimezone(dateutil.tz.gettz(current_timezone))
            # food_time = food_time.astimezone(dateutil.tz.gettz(current_timezone))
            for f in nutrition_dict['foods']:
                calories = f.get("nf_calories", 0) or 0
                food_calories += calories
                total_calories += calories
                day_calories += calories
                protein = f.get("nf_protein", 0) or 0
                total_protein += protein
                food_protein += protein
                day_protein += protein
                fat = f.get("nf_total_fat", 0) or 0
                total_fat += fat
                food_fat += fat
                day_fat += fat
                carbohydrates = f.get("nf_total_carbohydrate", 0) or 0
                total_carbohydrates += carbohydrates
                food_carbohydrates += carbohydrates
                day_carbohydrates += carbohydrates
                sugar = f.get("nf_sugars", 0) or 0
                total_sugar += sugar
                food_sugar += sugar
                day_sugar += sugar
            food_total_nutritions = food_protein + food_fat + food_carbohydrates
            food_protein_percent = int((food_protein / food_total_nutritions) * 100) if food_total_nutritions > 0 else 0
            food_fat_percent = int((food_fat / food_total_nutritions) * 100) if food_total_nutritions > 0 else 0
            food_carbohydrates_percent = int((food_carbohydrates / food_total_nutritions) * 100) if \
                food_total_nutritions > 0 else 0
            print(food_time.strftime('%H:%M'), food['utterance'], int(food_protein), str(food_protein_percent) + '%',
                  int(food_fat), str(food_fat_percent) + '%', int(food_carbohydrates),
                  str(food_carbohydrates_percent) + '%', food_calories)
        day_total_nutritions = day_protein + day_fat + day_carbohydrates
        day_protein_percent = int((day_protein / day_total_nutritions) * 100) if day_total_nutritions > 0 else 0
        day_fat_percent = int((day_fat / day_total_nutritions) * 100) if day_total_nutritions > 0 else 0
        day_carbohydrates_percent = int((day_carbohydrates / day_total_nutritions) * 100) if \
            day_total_nutritions > 0 else 0
        print(f'Итого за день: \t{int(day_protein)}({day_protein_percent}%)\t{int(day_fat)}({day_fat_percent}%)'
              f'\t{int(day_carbohydrates)}({day_carbohydrates_percent}%)\t{int(day_sugar)}\t{int(day_calories)}')
    total_nutritions = total_protein + total_fat + total_carbohydrates
    total_protein_percent = int((total_protein / total_nutritions) * 100) if total_nutritions > 0 else 0
    total_fat_percent = int((total_fat / total_nutritions) * 100) if total_nutritions > 0 else 0
    total_carbohydrates_percent = int((total_carbohydrates / total_nutritions) * 100) if \
        total_nutritions > 0 else 0
    print(f'\nИтого за период: \t{int(total_protein)}({total_protein_percent}%)\t{int(total_fat)}({total_fat_percent}%)'
          f'\t{int(total_carbohydrates)}({total_carbohydrates_percent}%)\t{int(total_sugar)}'
          f'\t{int(total_calories)}')
    return 'OI'


if __name__ == '__main__':
    print(
            report(
                    database_client=client,
                    date_from=datetime.date.today() - datetime.timedelta(days=7),
                    date_to=datetime.date.today(),
                    user_id='C7661DB7B22C25BC151DBC1DB202B5624348B30B4325F2A67BB0721648216065',
                    current_timezone='Europe/Moscow'))

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
