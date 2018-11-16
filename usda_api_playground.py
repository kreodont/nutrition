import os
from botocore.vendored import requests

key = os.environ['usda_key']
string_to_search = 'light beer'.replace(' ', '%20')
print(requests.get(f'https://api.nal.usda.gov/ndb/search/?format=json&q={string_to_search}'
                   f'&sort=n&max=10&offset=0&api_key={key}').text)
