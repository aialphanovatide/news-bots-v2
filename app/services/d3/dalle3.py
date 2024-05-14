from openai import OpenAI
import requests
import json
import os
import base64
from PIL import Image
import boto3
from io import BytesIO
from dotenv import load_dotenv
#from routes.slack.templates.news_message import send_INFO_message_to_slack_channel

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')




client = OpenAI(
    api_key=OPENAI_API_KEY,
)

def resize_image(image_data, target_size=(500, 500)): 
    image_binary = base64.b64decode(image_data)
    image = Image.open(BytesIO(image_binary))
    resized_image = image.resize(target_size)
    resized_image_data = base64.b64encode(
        resized_image.tobytes()).decode('utf-8')
    return resized_image_data

def generate_poster_prompt(article):
    prompt = f'Generate a DALL-E prompt related to this {article}. It should be 400 characters or less and avoid specific names focused on abstract image without mention letters, numbers or words..'
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt},
                  {"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=1024,
    )
    final_prompt = response.choices[0].message.content[:450] 
    api_url = 'https://api.openai.com/v1/images/generations'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }
    data = {
        "model": "dall-e-3",
        "prompt": f'{final_prompt} - depicting an anime style.', 
        "n": 1,
        "size": "1024x1024"
    }
    

    response = requests.post(api_url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        result = response.json()
        image_url = result['data'][0]['url']
        return image_url  # Retorna solo la URL de la imagen
    else:
        print("Error:", response.status_code, response.text)
        #send_INFO_message_to_slack_channel(title_message="Error generating DALL-E image", sub_title="Response", message=str(response.text))
        return None



def resize_and_upload_image_to_s3(image_data, bucket_name, image_filename, target_size=(512, 512)):
    try:
        response = requests.get(image_data)
        if response.status_code == 200:
            image_binary = response.content
            image = Image.open(BytesIO(image_binary))
            image_key = image_filename
            
            s3 = boto3.client(
                's3',
                region_name='us-east-2',
                aws_access_key_id=AWS_ACCESS,
                aws_secret_access_key=AWS_SECRET_KEY
            )
            
            s3.upload_fileobj(BytesIO(image_binary), 'mktnewsposters', image_key)

            resized_image = image.resize(target_size)
            
            with BytesIO() as output:
                resized_image.save(output, format="JPEG")
                output.seek(0)
                s3.upload_fileobj(output, bucket_name, image_key)

            image_url = f"https://{bucket_name}.s3.amazonaws.com/{image_key}"
            return image_url
        else:
            print("Error:", response.status_code)
            return None
    except Exception as e:
        print("Error:", str(e)) 
        return None
