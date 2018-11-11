import sys
import zipfile
import os
import boto3
import glob

profiles_dictionary = {
    'kreodont':
        {
            'bucket_name': 'kreodont-lambda-virginia',
            'role': 'arn:aws:iam::704400236483:role/lambda_basic_execution',
        },
    '':
        {
            'bucket_name': 'kreodont-lambda-virginia',
            'role': 'arn:aws:iam::704400236483:role/lambda_basic_execution',
        },
}


def print_info(info_str):
    print(info_str)


def print_error(error_str):
    print_info("\n%s\n" % error_str)


def zipdir(path, ziph, exceptions=()):
    for root, dirs, files in os.walk(path):
        for f in files:
            full_path = os.path.join(root, f).replace('\\', '/')
            if full_path in exceptions:
                continue
            full_path_without_folder_name = '/'.join(full_path.split('/')[1:])
            if full_path_without_folder_name in exceptions:
                continue
            ziph.write(full_path, full_path_without_folder_name)


def create_zipfile_from_folder(folder_name):
    zipfile_name = folder_name + '/%s.zip' % folder_name
    zip_file = zipfile.ZipFile(zipfile_name, 'w', zipfile.ZIP_DEFLATED)
    exception_extentions = ('*.zip', '*.csv', '*.json')
    exception_filenames = [os.path.basename(f) for f_ in
                           [glob.glob('%s/%s' % (folder_name, e)) for e in exception_extentions] for f in f_]
    zipdir(folder_name, zip_file, exceptions=exception_filenames)
    return zipfile_name


def upload_to_s3(filename, s3_name, session, bucket_name):
    s3 = session.resource('s3')
    data = open(filename, 'rb')
    s3.Bucket(bucket_name).put_object(Key=s3_name, Body=data)
    object_acl = s3.ObjectAcl(bucket_name, s3_name)
    response = object_acl.put(ACL='public-read')
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        print_error('Cannot upload %s' % filename)
        print_error(response)
        exit(1)


def deploy_lambda_from_s3(function_name, session, bucket_name, role_name):
    client = session.client('lambda')
    first_response = client.list_functions()
    existing_functions_names = [c['FunctionName'] for c in first_response['Functions']]
    next_marker = first_response.get('NextMarker')

    while next_marker:
        response = client.list_functions(Marker=next_marker)
        existing_functions_names.extend([c['FunctionName'] for c in response['Functions']])
        next_marker = response.get('NextMarker')

    if function_name in existing_functions_names:
        client.update_function_code(FunctionName=function_name, S3Bucket=bucket_name, S3Key='%s.zip' % function_name,
                                    Publish=True)
    else:
        client.create_function(FunctionName=function_name,
                               Code={
                                   'S3Bucket': bucket_name,
                                   'S3Key': '%s.zip' % function_name,
                               },
                               Runtime='python3.6',
                               Timeout=30,
                               MemorySize=128,
                               Role=role_name,
                               Handler='%s.%s' % (function_name, function_name),
                               Publish=True)


if len(sys.argv) < 2:
    print_error('Usage: python %s lambda_function_folder' % sys.argv[0])
    exit(1)

working_folder = sys.argv[1]
if not os.path.isdir(working_folder):
    print_error('Cannot find folder %s' % working_folder)
    exit(1)

aws_profile_name = ''
if len(sys.argv) > 2:
    aws_profile_name = sys.argv[2]
aws_bucket_name = profiles_dictionary[aws_profile_name]['bucket_name']
lambda_execution_role_name = profiles_dictionary[aws_profile_name]['role']
created_zipfile_name = create_zipfile_from_folder(working_folder)
aws_session = boto3.Session(profile_name=aws_profile_name)
upload_to_s3(created_zipfile_name, '%s.zip' % working_folder, aws_session, aws_bucket_name)
deploy_lambda_from_s3(working_folder, aws_session, aws_bucket_name, lambda_execution_role_name)
print_info('%s succesfully uploaded\n' % working_folder)
