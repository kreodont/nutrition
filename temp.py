import boto3
import json
import datetime
import dateutil.parser

session = boto3.Session(profile_name='kreodont')
dynamo = session.client('dynamodb')
bulb = dynamo.get_item(
        TableName='nutrition_cache',
        Key={'initial_phrase': {'S': '_key'}})['Item']['response']['S']

keys_dict = json.loads(bulb)
min_usage_value = 200
min_usage_key = None
min_usage_key_num = 0
for k in keys_dict['keys']:
    k['dates'] = [d for d in k['dates'] if
                  dateutil.parser.parse(d) > datetime.datetime.now() - datetime.timedelta(hours=24)]
    if min_usage_key is None:
        min_usage_key = k
    if min_usage_value > len(k['dates']):
        min_usage_key = k
        min_usage_value = len(k['dates'])

min_usage_key['dates'].append(str(datetime.datetime.now()))
print(min_usage_key['name'])
print(min_usage_key['pass'])

# New keys addition
# keys_dict['keys'].append({'name': '1fe9d120', 'pass': '0a333def74c56d8870ccf8d0855427e5', 'dates': []})
###
dynamo.put_item(TableName='nutrition_cache',
                Item={
                    'initial_phrase': {
                        'S': '_key',
                    },
                    'response': {
                        'S': json.dumps(keys_dict),
                    }})


# response = dynamo.get_item(TableName='nutrition_cache', Key={'initial_phrase': {'S': phrase}})
# response_text = response['Item']['response']['S'] if 'Item' in response and \
#                                                      'response' in response['Item'] and \
#                                                      'S' in response['Item']['response'] else None
# if not response_text:
#     response_text = phrase.upper()
#     dynamo.put_item(TableName='nutrition_cache',
#                     Item={
#                         'initial_phrase': {
#                             'S': phrase,
#                         },
#                         'response': {
#                             'S': response_text,
#                         }})


# print(json.dumps(response, indent=4))
# import json
# dict_= {"foods": [{"food_name": "potato",
# "brand_name": "puree", "serving_qty": 300,
# "serving_unit": "g", "serving_weight_grams": 300,
# "nf_calories": 279, "nf_total_fat": 0.39, "nf_saturated_fat": 0.1,
# "nf_cholesterol": 0, "nf_sodium": 30, "nf_total_carbohydrate": 63.45,
# "nf_dietary_fiber": 6.6, "nf_sugars": 3.54, "nf_protein": 7.5, "nf_potassium": 1605,
# "nf_p": 210, "full_nutrients": [{"attr_id": 203, "value": 7.5}, {"attr_id": 204, "value": 0.39},
# {"attr_id": 205, "value": 63.45}, {"attr_id": 207, "value": 3.99}, {"attr_id": 208, "value": 279},
# {"attr_id": 209, "value": 51.81}, {"attr_id": 210, "value": 1.2}, {"attr_id": 211, "value": 1.32},
# {"attr_id": 212, "value": 1.02}, {"attr_id": 213, "value": 0}, {"attr_id": 214, "value": 0},
# {"attr_id": 221, "value": 0}, {"attr_id": 255, "value": 224.67}, {"attr_id": 262, "value": 0},
# {"attr_id": 263, "value": 0}, {"attr_id": 268, "value": 1170}, {"attr_id": 269, "value": 3.54},
# {"attr_id": 287, "value": 0}, {"attr_id": 291, "value": 6.6}, {"attr_id": 301, "value": 45},
# {"attr_id": 303, "value": 3.24}, {"attr_id": 304, "value": 84}, {"attr_id": 305, "value": 210},
# {"attr_id": 306, "value": 1605}, {"attr_id": 307, "value": 30}, {"attr_id": 309, "value": 1.08},
# {"attr_id": 312, "value": 0.354}, {"attr_id": 315, "value": 0.657}, {"attr_id": 317, "value": 1.2},
# {"attr_id": 318, "value": 30}, {"attr_id": 319, "value": 0}, {"attr_id": 320, "value": 3},
# {"attr_id": 321, "value": 18}, {"attr_id": 322, "value": 0}, {"attr_id": 323, "value": 0.12},
# {"attr_id": 324, "value": 0}, {"attr_id": 328, "value": 0}, {"attr_id": 334, "value": 0},
# {"attr_id": 337, "value": 0}, {"attr_id": 338, "value": 90}, {"attr_id": 341, "value": 0},
# {"attr_id": 342, "value": 0}, {"attr_id": 343, "value": 0}, {"attr_id": 401, "value": 28.8},
# {"attr_id": 404, "value": 0.192}, {"attr_id": 405, "value": 0.144}, {"attr_id": 406, "value": 4.23},
# {"attr_id": 410, "value": 1.128}, {"attr_id": 415, "value": 0.933}, {"attr_id": 417, "value": 84},
# {"attr_id": 418, "value": 0}, {"attr_id": 421, "value": 44.4}, {"attr_id": 429, "value": 0},
# {"attr_id": 430, "value": 6}, {"attr_id": 431, "value": 0}, {"attr_id": 432, "value": 84},
# {"attr_id": 435, "value": 84}, {"attr_id": 454, "value": 0.6}, {"attr_id": 501, "value": 0.075},
# {"attr_id": 502, "value": 0.243}, {"attr_id": 503, "value": 0.24}, {"attr_id": 504, "value": 0.357},
# {"attr_id": 505, "value": 0.39}, {"attr_id": 506, "value": 0.114}, {"attr_id": 507, "value": 0.087},
# {"attr_id": 508, "value": 0.297}, {"attr_id": 509, "value": 0.174}, {"attr_id": 510, "value": 0.375},
# {"attr_id": 511, "value": 0.369}, {"attr_id": 512, "value": 0.126}, {"attr_id": 513, "value": 0.228},
# {"attr_id": 514, "value": 1.749}, {"attr_id": 515, "value": 1.281}, {"attr_id": 516, "value": 0.207},
# {"attr_id": 517, "value": 0.228}, {"attr_id": 518, "value": 0.273}, {"attr_id": 601, "value": 0},
# {"attr_id": 605, "value": 0}, {"attr_id": 606, "value": 0.102}, {"attr_id": 607, "value": 0},
# {"attr_id": 608, "value": 0}, {"attr_id": 609, "value": 0}, {"attr_id": 610, "value": 0.003},
# {"attr_id": 611, "value": 0.012}, {"attr_id": 612, "value": 0.003}, {"attr_id": 613, "value": 0.066},
# {"attr_id": 614, "value": 0.015}, {"attr_id": 617, "value": 0.003}, {"attr_id": 618, "value": 0.129},
# {"attr_id": 619, "value": 0.039}, {"attr_id": 620, "value": 0}, {"attr_id": 621, "value": 0},
# {"attr_id": 626, "value": 0.003}, {"attr_id": 627, "value": 0}, {"attr_id": 628, "value": 0},
# {"attr_id": 629, "value": 0}, {"attr_id": 630, "value": 0}, {"attr_id": 631, "value": 0},
# {"attr_id": 645, "value": 0.009}, {"attr_id": 646, "value": 0.171}], "nix_brand_name": None,
# "nix_brand_id": None, "nix_item_name": None, "nix_item_id": None, "upc": None,
# "consumed_at": "2018-11-14T16:24:06+00:00", "metadata": {"is_raw_food": False},
# "source": 1, "ndb_no": 11674, "tags": {"item": "potato", "measure": "g", "quantity": "300.0",
# "food_group": 4, "tag_id": 752}, "alt_measures": [{"serving_weight": 148, "measure": "NLEA serving",
# "seq": 1, "qty": 1}, {"serving_weight": 138, "measure": "potato small", "seq": 4, "qty": 1},
# {"serving_weight": 173, "measure": "potato medium", "seq": 3, "qty": 1}, {"serving_weight": 299,
# "measure": "potato large", "seq": 2, "qty": 1}, {"serving_weight": 122, "measure": "cup", "seq": 80, "qty": 1},
# {"serving_weight": 210, "measure": "cup, mashed", "seq": 81, "qty": 1}, {"serving_weight": 25,
# "measure": "baby potato", "seq": 82, "qty": 1}, {"serving_weight": 100, "measure": "g", "seq": None,
# "qty": 100}], "lat": None, "lng": None, "meal_type": 3,
# "photo": {"thumb": "https://d2xdmhkmkbyw75.cloudfront.net/752_thumb.jpg",
# "highres": "https://d2xdmhkmkbyw75.cloudfront.net/752_highres.jpg", "is_user_uploaded": False},
# "sub_recipe": None}]}
#
# print(json.dumps(dict_, sort_keys=True, indent=4, separators=(',', ': ')))

# from botocore.vendored import requests
# import json
# # response = requests.post('https://omertu-googlehomekodi-60.glitch.me/stop',
# #                          data=json.dumps({'token': 'kreodont09'}),
# #                          headers={'content-type': 'application/json'})
#
# response = requests.post('https://xggk60khe2.execute-api.us-east-1.amazonaws.com/test/dialogs',
#                          headers={'content-type': 'application/json'},
#                          data=json.dumps({'token': 'kreodont09'}))
#
# print(response.text)
