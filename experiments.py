import boto3
import typing
from botocore.client import Config


def get_boto3_client(
        *,
        aws_lambda_mode: bool,
        service_name: str,
        profile_name: str = 'kreodont',
) -> typing.Optional[boto3.client]:

    known_services = ['translate', 'dynamodb', 's3']
    if service_name not in known_services:
        raise Exception(
                f'Not known service '
                f'name {service_name}. The following '
                f'service names known: {", ".join(known_services)}')

    # if aws_lambda_mode:
    return boto3.client(service_name, config=Config(signature_version='s3v4'))

    # return boto3.Session(profile_name=profile_name).client(service_name)


def generate_presigned_url(
        *,
        s3_client: boto3.client,
        bucket_name: str,
        file_name: str,
) -> str:
    return s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_name
            }
    )


if __name__ == '__main__':
    client = get_boto3_client(
            aws_lambda_mode=False,
            service_name='s3',
    )
    print(generate_presigned_url(
            s3_client=client,
            bucket_name='nutrition-dialog-reports',
            file_name='test.pdf'))


def handler(event, context):
    client = get_boto3_client(
            aws_lambda_mode=False,
            service_name='s3',
    )
    print(generate_presigned_url(
            s3_client=client,
            bucket_name='nutrition-dialog-reports',
            file_name='test.pdf'))