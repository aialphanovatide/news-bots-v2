import os
import json
import boto3
import requests
from PIL import Image
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

client = OpenAI(
    api_key=OPENAI_API_KEY,
)


def generate_poster_prompt(article, bot_id):
    
    prompt = f'Generate a DALL-E prompt related to this {article}. It should be 400 characters or less and avoid specific names focused on abstract image without mention letters, numbers or words.'
    api_url = 'https://api.openai.com/v1/images/generations'
    
    poster_response_prompt = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt},
                  {"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=1024,
    )

    if not poster_response_prompt:
        return {'error': 'No poster prompt given', 'success': False}
    
    final_prompt = poster_response_prompt.choices[0].message.content[:450]
    
    print("prompt generado por GPT 0: " + final_prompt)
    
    if 1 <= bot_id <= 39:
        postfinalprompt = 'depicting an anime style.'
    else:
        postfinalprompt = 'Generate realistic, photograph-style images, using natural lighting and a professional color palette to convey credibility and authority.'

   

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
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
        return {'response': image_url, 'success': True}  # It only returns the image URL
    else:
        return {'error': response.text, 'success': False}


# Resize the image and uploads to two different Buckets, one for the MKT sites and other for the App
def resize_and_upload_image_to_s3(image_data, bucket_name, image_filename, target_size=(512, 512)):
    try:
        response = requests.get(image_data)

        if response.status_code != 200:
            return {'error': response.text, 'success': False}
        
        image_binary = response.content
        image = Image.open(BytesIO(image_binary))
        image_key = image_filename
        
        # connection to AWS
        s3 = boto3.client(
            's3',
            region_name='us-east-2',
            aws_access_key_id=AWS_ACCESS,
            aws_secret_access_key=AWS_SECRET_KEY
        )

        # Uploads the same image to the sitesnewsposters AWS Bucket for the Marketing sites
        s3.upload_fileobj(BytesIO(image_binary), 'sitesnewsposters', image_key)
        print("Mkt sites image generated and saved")

        # Uploads the same image to the specified Bucket for the APP
        resized_image = image.resize(target_size)
        with BytesIO() as output:
            resized_image.save(output, format="JPEG")
            output.seek(0)
            s3.upload_fileobj(output, bucket_name, image_key)

        image_url = f"https://{bucket_name}.s3.amazonaws.com/{image_key}"
        return {'response': image_url, 'success': True}
    
    except Exception as e:
        return {'error': f'Error while uploading Image to AWS: {str(e)}', 'success': False}
    










# Example usage
# print(generate_poster_prompt(article="""
# - Grayscale, a leading crypto asset manager, has made strategic changes to its Digital Large Cap Fund (GDLC) and Smart Contract Platform Ex-Ethereum Fund.
# - The firm has removed Cardano (ADA) from its GDLC and Cosmos (ATOM) from its Ex-Ethereum Smart Contract Platform Fund.
# - This rebalancing is designed to optimize the portfolio according to current market dynamics and the funds' strategic objectives.
# - Post-rebalancing, the GDLC primarily holds Bitcoin (BTC), Ethereum (ETH), Solana (SOL), Ripple (XRP), and Avalanche (AVAX).
# - Grayscale has also converted its Bitcoin Trust (GBTC) into a spot Bitcoin Exchange-Traded Fund (ETF), which started trading on January 11.
# - However, the fund has experienced significant outflows since its conversion, reflecting the challenging market conditions for crypto investments.
# - In addition, Grayscale has applied to the U.S. SEC to launch a spot Ether ETF in its effort to expand its ETF offerings.
# - These changes highlight the dynamic nature of the crypto asset management sector and Grayscale's commitment to adapt and innovate in the rapidly evolving cryptocurrency market.
# """))