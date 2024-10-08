import os
import json
import boto3
from flask import session
import requests
from PIL import Image
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv
from config import Bot

load_dotenv()

class ImageGenerator:
    def __init__(self):
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.AWS_ACCESS = os.getenv('AWS_ACCESS')
        self.AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
        self.client = OpenAI(api_key=self.OPENAI_API_KEY)
        self.s3 = boto3.client(
            's3',
            region_name='us-east-2',
            aws_access_key_id=self.AWS_ACCESS,
            aws_secret_access_key=self.AWS_SECRET_KEY
        )

    def generate_poster_prompt(self, article, bot_id):
        prompt = f'Generate a DALL-E prompt related to this {article}. It should be 400 characters or less and avoid specific names focused on abstract image without mention letters, numbers or words.'
        api_url = 'https://api.openai.com/v1/images/generations'
        
        poster_response_prompt = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt},
                      {"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=1024,
        )

        if not poster_response_prompt:
            return {'error': 'No poster prompt given', 'success': False}
        
        final_prompt = poster_response_prompt.choices[0].message.content[:450]
        
        bot_record = Bot.query.filter_by(id=bot_id).first()
        
        postfinalprompt = bot_record.dalle_prompt if bot_record else 'Generate realistic, photograph-style images, using natural lighting and a professional color palette to convey credibility and authority.'

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.OPENAI_API_KEY}'
        }
        data = {
            "model": "dall-e-3",
            "prompt": f'{final_prompt} - {postfinalprompt}', 
            "n": 1,
            "size": "1024x1024"
        }
        
        response = requests.post(api_url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            result = response.json()
            image_url = result['data'][0]['url']
            return {'response': image_url, 'success': True}
        else:
            return {'error': response.text, 'success': False}

    def resize_and_upload_image_to_s3(self, image_data, bucket_name, image_filename, target_size=(512, 512)):
        try:
            response = requests.get(image_data)

            if response.status_code != 200:
                return {'error': response.text, 'success': False}
            
            image_binary = response.content
            image = Image.open(BytesIO(image_binary))
            image_key = image_filename
            
            # Uploads the same image to the sitesnewsposters AWS Bucket for the Marketing sites
            self.s3.upload_fileobj(BytesIO(image_binary), 'sitesnewsposters', image_key)

            # Uploads the same image to the specified Bucket for the APP
            resized_image = image.resize(target_size)
            with BytesIO() as output:
                resized_image.save(output, format="JPEG")
                output.seek(0)
                self.s3.upload_fileobj(output, bucket_name, image_key)

            image_url = f"https://{bucket_name}.s3.amazonaws.com/{image_key}"
            return {'response': image_url, 'success': True}
        
        except Exception as e:
            return {'error': f'Error while uploading Image to AWS: {str(e)}', 'success': False}