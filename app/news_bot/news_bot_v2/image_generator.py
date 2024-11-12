from botocore.exceptions import BotoCoreError, ClientError
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from io import BytesIO
from openai import OpenAI
from config import Bot
from PIL import Image
import requests
import dotenv
import boto3
import os
import re

dotenv.load_dotenv()

@dataclass
class ImageConfig:
    """Configuration settings for the ImageGenerator."""
    dalle_model: str = "dall-e-3"
    image_size_spec: str = "1024x1024"
    app_image_size: Tuple[int, int] = (512, 512)
    max_prompt_length: int = 3500
    s3_region: str = "us-east-2"
    s3_app_bucket: str = "appnewsposters"
    s3_site_bucket: str = "sitesnewsposters"
    image_style: str = "natural"
    image_quality: str = "hd"
    timeout_seconds: int = 30

class ImageGenerator:
    # Default prompt for generating DALL-E prompts when none exists in database
    DEFAULT_IMAGE_GENERATION_PROMPT = (
        "Generate a DALL-E prompt related to this {article}. It should be 400 characters or less and avoid specific names focused on abstract image without mention letters, numbers or words."
    )

    # Default style preferences for all generated images
    DEFAULT_IMAGE_PROMPT = (
        "Generate realistic, photograph-style images, using natural lighting and a professional color palette to convey credibility and authority, avoid letters, numbers or words."
    )

    def __init__(
        self,
        openai_key: Optional[str] = None,
        config: Optional[ImageConfig] = None
    ):
        """Initialize the ImageGenerator with API keys and configuration."""
        self.openai_key = openai_key or os.getenv('NEWS_BOT_OPENAI_API_KEY')
        if not self.openai_key:
            raise ValueError("OpenAI API key is required")
            
        self.config = config or ImageConfig()
        self.openai_client = OpenAI(api_key=self.openai_key)
        self._init_s3_client()

    def _init_s3_client(self):
        """Initialize AWS S3 client with credentials."""
        self.s3_client = boto3.client(
            's3',
            region_name=self.config.s3_region,
            aws_access_key_id=os.getenv('AWS_ACCESS'),
            aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
        )

    def generate_image(
        self, 
        article_text: str, 
        bot_id: int
    ) -> Dict[str, Any]:
        """
        Generate an AI image based on article content using bot-specific settings.

        Args:
            article_text (str): Article text to base image on
            bot_id (int): Database ID of the bot requesting the image

        Returns:
            Dict[str, Any]: Result containing generated image URL
        """
        try:
            if not article_text or not bot_id:
                raise ValueError("Article text and bot_id are required")

            # Get the bot's DALL-E prompt from database or generate one
            dalle_prompt = self._get_bot_prompt(bot_id)
            
            # If we got a stored DALL-E prompt, use it directly
            if dalle_prompt:
                prompt = dalle_prompt
            else:
                # Generate a new prompt using GPT
                initial_prompt = self.DEFAULT_IMAGE_GENERATION_PROMPT.format(
                    article=article_text.strip().lower()
                )
                prompt = self.generate_prompt(initial_prompt)
                prompt = f"{prompt} {self.DEFAULT_IMAGE_PROMPT}"
                
            if len(prompt) > self.config.max_prompt_length:
                prompt = prompt[:self.config.max_prompt_length].strip()
           
            image_url = self._generate_dalle_image(prompt)
            return image_url
            
        except Exception as e:
            raise Exception(f"{str(e)}")

    def _get_bot_prompt(self, bot_id: int) -> Optional[str]:
        """
        Retrieve bot-specific DALL-E prompt from database.

        Args:
            bot_id (int): Database ID of the bot

        Returns:
            Optional[str]: Bot's custom DALL-E prompt if exists, None otherwise
        """
        try:
            bot = Bot.query.get(bot_id)
            if bot and bot.dalle_prompt:
                return bot.dalle_prompt
            return None
            
        except Exception as e:
            raise Exception(f"Failed to get bot prompt: {str(e)}")

    def generate_prompt(self, initial_prompt: str) -> str:
        """
        Generate a DALL-E optimized prompt using GPT.

        Args:
            initial_prompt (str): Base prompt to enhance

        Returns:
            str: Generated DALL-E optimized prompt
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": initial_prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Failed to generate prompt: {str(e)}")

    def _generate_dalle_image(self, prompt: str) -> str:
        """
        Generate image using DALL-E with the final prompt.

        Args:
            prompt (str): Final prompt (either from database or generated)

        Returns:
            str: URL of the generated image
        """
        try:
            response = self.openai_client.images.generate(
                model=self.config.dalle_model,
                prompt=prompt,
                style=self.config.image_style,
                quality=self.config.image_quality,
                n=1,
                size=self.config.image_size_spec
            )
            return response.data[0].url
            
        except Exception as e:
            raise Exception(f"DALL-E image generation failed: {str(e)}")

    def upload_image(self, image_url: str, title: str) -> str:
        """
        Download, resize and upload image to S3 buckets.

        Args:
            image_url (str): URL of the generated image
            title (str): Title to use for filename

        Returns:
            str: Public URL of the uploaded image
        """
        try:
            # Sanitize filename
            filename = self._sanitize_filename(title) + ".jpg"
            
            # Download image
            response = self._download_image(image_url)
            image = Image.open(BytesIO(response.content))
            
            # Upload original to sites bucket
            self._upload_to_s3(
                image, 
                self.config.s3_site_bucket, 
                filename
            )
            
            # Resize and upload to app bucket
            resized_image = image.resize(self.config.app_image_size)
            url = self._upload_to_s3(
                resized_image, 
                self.config.s3_app_bucket, 
                filename
            )
            
            return url
            
        except Exception as e:
            raise Exception(f"Image upload failed: {str(e)}")

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to be safe across different operating systems.
        
        Args:
            filename (str): Original filename

        Returns:
            str: Sanitized filename
        """
        # Remove or replace invalid filename characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace spaces and other characters with underscores
        filename = re.sub(r'[\s\-]+', '_', filename)
        # Remove dots and underscores from start/end
        filename = filename.strip('._')
        # Limit length (Windows has 255 char limit)
        max_length = 200  # Leave room for path and extension
        if len(filename) > max_length:
            filename = filename[:max_length]
        return filename.lower()

    def _download_image(self, image_url: str) -> requests.Response:
        """Download image from URL."""
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            return response
        except Exception as e:
            raise Exception(f"Failed to download image: {str(e)}")

    def _upload_to_s3(
        self, 
        image: Image, 
        bucket: str, 
        filename: str
    ) -> str:
        """Upload image to S3 bucket."""
        try:
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            buffer.seek(0)
            
            self.s3_client.upload_fileobj(
                buffer,
                bucket,
                filename,
                ExtraArgs={'ContentType': 'image/jpeg'}
            )
            
            return f"https://{bucket}.s3.amazonaws.com/{filename}"
            
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"S3 upload failed: {str(e)}")


# Example of usage:
# if __name__ == "__main__":
#     article_text = """
#     Algorand Foundation and T-Hub have teamed up to supercharge Web3 startups, rolling out their first batch of investments through the Start-up Lab program. This collaboration is all about turbocharging innovation in blockchain applications across industries like supply chain, trade, and finance.\n\nAnil Kakani from Algorand Foundation is excited about these trailblazers making waves with solutions for everything from supply chain traceability to film finance. The program's secret sauce? A blend of mentorship, technical prowess, and a network that opens doors to funding and partnerships.\n\nMeet the five startups shaking things up:\n\n- **LW3**: Revolutionizing supply chains by tokenizing products with tamper-proof QR codes for real-time tracking. Think sustainability meets anti-counterfeiting.\n- **FilmFinance**: Bridging filmmakers with investors via blockchain-based fractional tokenization of film assets. It's transparency meets efficiency in movie financing.\n- **Automaxis/FDP Connect**: Modernizing global trade with digitized documentation using blockchain—streamlining freight payments and paperwork like never before.\n- **Astrix**: Elevating fan experiences at live events with secure ticketing and digital collectibles while tackling fraud head-on.\n- **ARVO**: Combining AI, IoT, and blockchain for advanced traceability solutions in automotive and pharma sectors—fighting counterfeits one product at a time.\n\nSujit Jagirdar from T-Hub highlights how this partnership accelerates startup success by refining their tech for real-world markets. Algorand’s commitment doesn’t stop here; they’re also helping these innovators scale up by securing more institutional capital.
#     """
#     bot_id = 1

#     image_generator = ImageGenerator()
#     image_url = image_generator.generate_image(article_text, bot_id)
#     print(image_url)

