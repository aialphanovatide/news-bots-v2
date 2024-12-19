import os
import boto3
import requests
import re
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

# Constants for the article creation process
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
UPLOAD_FOLDER = 'static/temp_uploads'

def allowed_file(filename):
   return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_article_creation(data):
    """
    Validate article creation payload with comprehensive checks.
    
    Args:
        data (dict): Incoming request payload
    
    Returns:
        dict: Validation result with 'valid' boolean and 'errors' list
    """
    errors = []
    
    # Required field validation
    required_fields = ['title', 'content', 'image_url']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"'{field}' is required and cannot be empty")
    
    # Title validation
    if 'title' in data:
        if not isinstance(data['title'], str):
            errors.append("Title must be a string")
        elif len(data['title'].strip()) < 5:
            errors.append("Title must be at least 5 characters long")


    # Image URL validation
    if 'image_url' in data:
        if not isinstance(data['image_url'], str):
            errors.append("Image URL must be a string")

    # is_top_story param boolean validation
    if 'is_top_story' in data:
        if not isinstance(data['is_top_story'], bool):
            errors.append("is_top_story must be a true or false value")
    
    # Content validation
    if 'content' in data:
        if not isinstance(data['content'], str):
            errors.append("Content must be a string")
        elif len(data['content'].strip()) < 20:
            errors.append("Content must be at least 20 characters long")
    
    # Optional field type checks
    optional_list_fields = ['used_keywords']
    for field in optional_list_fields:
        if field in data and not isinstance(data[field], list):
            errors.append(f"'{field}' must be a list")
    
    # Optional string field checks
    optional_string_fields = ['comment']
    for field in optional_string_fields:
        if field in data and not isinstance(data[field], str):
            errors.append(f"'{field}' must be a string")
    
    # ID validations
    id_fields = ['bot_id', 'category_id']
    for field in id_fields:
        if field in data and not isinstance(data[field], int):
            errors.append(f"'{field}' must be an integer")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }
    
    
def download_and_process_image(image_url, title):
    """
    Download, process, and upload image to S3.
    
    Args:
        image_url (str): URL of the image to download
        title (str): Title to use for image filename
    
    Returns:
        str: Filename of the uploaded image
    """
    # Download image
    try:
        image_response = requests.get(image_url)
        image_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f'Failed to download image: {str(e)}')
    
    # Sanitize filename
    image_filename = re.sub(r'[^a-zA-Z0-9_]', '', title.replace(" ", "_"))
    image_filename = f"{image_filename}.jpg"
    
    # S3 configuration
    s3 = boto3.client('s3', 
        region_name='us-east-2', 
        aws_access_key_id=AWS_ACCESS, 
        aws_secret_access_key=AWS_SECRET_KEY
    )
    
    s3_bucket_names = {
        'original': 'sitesnewsposters',
        'processed': 'appnewsposters'
    }
    
    # Image processing
    image_data = image_response.content
    image = Image.open(BytesIO(image_data))
    resized_image = image.resize((512, 512))
    
    # Upload original image
    try:
        s3.upload_fileobj(
            BytesIO(image_data), 
            s3_bucket_names['original'], 
            image_filename
        )
    except Exception as e:
        raise ValueError(f'Original image upload failed: {str(e)}')
    
    # Upload resized image
    try:
        with BytesIO() as output:
            resized_image.save(output, format="JPEG")
            output.seek(0)
            s3.upload_fileobj(
                output, 
                s3_bucket_names['processed'], 
                image_filename
            )
    except Exception as e:
        raise ValueError(f'Resized image upload failed: {str(e)}')
    
    return image_filename