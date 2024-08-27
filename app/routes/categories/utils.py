import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
load_dotenv()

AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')


s3_client = boto3.client(
    's3',
    region_name='us-east-2',
    aws_access_key_id=AWS_ACCESS,
    aws_secret_access_key=AWS_SECRET_KEY
)

def upload_file_to_s3(file, bucket_name, object_name=None, extra_args=None):
    """
    Upload a file to an S3 bucket

    :param file: File to upload
    :param bucket_name: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :param extra_args: Optional, additional arguments to pass to boto3 client
    :return: True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file.filename

    # If extra_args was not specified, initialize it
    if extra_args is None:
        extra_args = {}

    # Upload the file
    try:
        s3_client.upload_fileobj(file, bucket_name, object_name, ExtraArgs=extra_args)
    except ClientError as e:
        print(f"Error uploading file to S3: {e}")
        return False
    return True

def get_s3_url(bucket_name, object_name):
    """
    Get the URL of an object in an S3 bucket

    :param bucket_name: Name of the S3 bucket
    :param object_name: Name of the object in the bucket
    :return: URL of the object
    """
    return f"https://{bucket_name}.s3.amazonaws.com/{object_name}"