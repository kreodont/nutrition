import boto3
import json

session = boto3.Session(profile_name='kreodont')
dynamo = session.client('dynamodb')


def save_session(*, session_id: str, time, foods_dict) -> None:
    pass
