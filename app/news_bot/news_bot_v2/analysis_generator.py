from typing import Dict, Any, Optional, Tuple, Literal
from dataclasses import dataclass
from openai import OpenAI
from config import Bot
import requests
import base64
import dotenv
import json
import os

dotenv.load_dotenv()

@dataclass
class AnalysisConfig:
    """
    Configuration settings for the OpenAI-powered AnalysisGenerator.
    
    Attributes:
        model (str): OpenAI model identifier. Default is 'gpt-4-turbo-preview' for
            optimal performance and cost balance.
        max_tokens (int): Maximum tokens in generated response. Default 4000
            ensures comprehensive analysis while managing costs.
        temperature (float): Controls randomness in generation (0.0-1.0).
            Lower values (0.3) for more focused, deterministic outputs.
        top_p (float): Nucleus sampling parameter. Default 0.9 provides good
            balance between creativity and coherence.
        frequency_penalty (float): Prevents repetition (-2.0 to 2.0).
            Default 1.0 reduces repetitive text.
        presence_penalty (float): Encourages new topics (-2.0 to 2.0).
            Default 0.0 maintains focus on the input content.
        seed (int): Seed for reproducible outputs. Default 42.
        timeout_seconds (int): API request timeout. Default 30 seconds.
        api_url (str): OpenAI API endpoint for chat completions.
        response_schema (Dict): JSON schema defining expected response structure.
    """
    model: str = "gpt-4o"
    max_tokens: int = 4000
    temperature: float = 0.3
    frequency_penalty: float = 1.0
    presence_penalty: float = 0.0
    seed: int = 42
    timeout_seconds: int = 30

@dataclass
class AudioConfig:
    """
    Configuration settings for the OpenAI-powered AudioGenerator.
    Attributes:
        voice (str): Default voice option for the audio generation. Available options are: alloy, echo, fable, onyx, nova, shimmer.
        audio_model (str): Audio model option for the generation. Default is 'tts-1'.
        audio_response_format (str): Audio response format option. Default is 'mp3'.
        audio_speed (float): Audio speed option. Default is 1.0.
    """
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "fable"  # Default voice option. Available options are: alloy, echo, fable, onyx, nova, shimmer.
    audio_model: str = "gpt-4o-audio-preview"
    audio_response_format: str = "mp3"  # Options: mp3, opus, aac, flac
    audio_speed: float = 1.0  # Range: 0.25 to 4.0


class AnalysisGenerator:
    """
    Generates refined content analysis using OpenAI's GPT models with structured output.
    
    Features:
        - Enforced JSON schema for consistent response structure
        - Configurable model parameters for output control
        - Robust error handling and validation
        - Optimized prompts for financial content analysis
    """
    
    DEFAULT_SYSTEM_PROMPT = (
        "You are a financial analyst that creates analysis that adopt a tone that is conversational, engaging, and accessible, while still retaining the depth of the financial insights. The tone should reflect the style of Matt Levine, famous columnist, known for making complex financial topics understandable and entertaining. Please respect the brevity of the original analysis. You should also edit the titles of the analysis, which should be short and appealing to X's audience."
    )

    PROMPT_SUFFIX = (
        " Please ensure the following: "
        "1) NEVER include introductory phrases at the start. "
        "2) Start directly with the content. "
        "3) Maintain a professional tone for a knowledgeable audience. "
        "4) Always return your response as a JSON object with 'new_title' and 'new_content' fields"
    )
    
    USER_PROMPT_TEMPLATE = (
        "Rewrite this financial analysis in {max_tokens} tokens or less:\n"
        "Title: {title}\n"
        "Content: {content}\n\n"
        "Requirements:\n"
        "1. Make it engaging and accessible\n"
        "2. Maintain analytical depth\n"
        "3. Keep the core insights\n"
    )

    def __init__(self, config: Optional[AnalysisConfig] = None, audio_config: Optional[AudioConfig] = None):
        """
        Initialize the generator with configuration settings.
        
        Args:
            config: Optional configuration override. If None, uses defaults.
        
        Raises:
            ValueError: If OpenAI API key is not set in environment.
        """
        self.api_key = os.getenv('NEWS_BOT_OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.openai_client = OpenAI(api_key=self.api_key)
        self.config = config or AnalysisConfig()
        self.audio_config = audio_config or AudioConfig()
    
    async def generate_analysis(
        self, 
        content: str, 
        title: str,
        bot_id: int
    ) -> Dict[str, Any]:
        """
        Generate refined analysis from input content.
        
        Args:
            content: Source content to analyze
            title: Original title
            bot_id: Identifier for bot-specific customization
        
        Returns:
            Dict containing new_title, new_content, and success status
        """
        try:
            if not content or not bot_id:
                raise ValueError("Content and bot_id are required")

            system_prompt = await self._get_bot_prompt(bot_id)
            if not system_prompt:
                system_prompt = f"{self.DEFAULT_SYSTEM_PROMPT}{self.PROMPT_SUFFIX}"

            new_title, new_content = await self._process_with_openai(
                content, title, system_prompt
            )
            
            return {
                'new_title': new_title,
                'new_content': new_content,
                'success': True
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _get_bot_prompt(self, bot_id: int) -> str:
        """Get bot-specific prompt or default."""
        try:
            bot = Bot.query.get(bot_id)
            if bot and bot.prompt:
                return f"{bot.prompt}{self.PROMPT_SUFFIX}"
            return None
            
        except Exception as e:
            raise Exception(f"Failed to get bot prompt: {str(e)}")

    async def _process_with_openai(
        self, 
        content: str,
        title: str,
        prompt: str
    ) -> Tuple[str, str]:
        """
        Process content using OpenAI's API with structured output.
        
        Args:
            content: Source content
            title: Original title
            prompt: System prompt for generation
        
        Returns:
            Tuple of (new_title, new_content)
            
        Raises:
            Exception: For API or processing failures
        """
        try:
            messages = [
                {"role": "system", "content": prompt},
                {
                    "role": "user", 
                    "content": self.USER_PROMPT_TEMPLATE.format(
                        max_tokens=self.config.max_tokens,
                        content=content.strip(),
                        title=title.strip()
                    )
                }
            ]
            

            response = self.openai_client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                response_format={"type": "json_object"},
                timeout=self.config.timeout_seconds,
                seed=self.config.seed,
                max_tokens=self.config.max_tokens,
                frequency_penalty=self.config.frequency_penalty,
                presence_penalty=self.config.presence_penalty
            )
            completion = response.choices[0].message.content
            content_dict = json.loads(completion)
           
            # Validate against schema
            if not all(k in content_dict for k in ['new_title', 'new_content']):
                raise ValueError("Invalid response structure")
            
            return content_dict['new_title'], content_dict['new_content']

        except requests.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Content processing failed: {str(e)}")
        
    async def generate_audio(
        self,
        title: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        Generate audio from the analysis title and content.
        
        Args:
            title: The article title
            content: The article content
            output_path: Path where the audio file should be saved
        
        Returns:
            Dict containing:
                success: bool indicating if generation was successful
                file_path: str path to the generated audio file
                duration: float duration of the audio in seconds
                metadata: Dict containing audio metadata
                data: bytes of the audio file
                error: str error message if any
        
        Example:
            result = await generator.generate_audio(
                title="Market Analysis",
                content="The market showed strong gains...",
                output_path="./output/analysis.mp3"
            )
        """
        try:
            audio_prompt = f"""
            Create a podcast script in the style of Matt Levine, the renowned Bloomberg writer, based on the following financial article title and text. The script should:
            - Start with a catchy, witty introduction that relates the topic to everyday life or current events.
            - Break down complex financial concepts into digestible, entertaining explanations.
            - Use a conversational tone with occasional dry humor and clever asides.
            - Incorporate analogies or metaphors to illustrate financial ideas.
            - Include rhetorical questions or hypothetical scenarios to engage the listener.
            - Maintain a slightly skeptical or ironic perspective on financial news and trends.
            - Conclude with a thought-provoking observation or a humorous final remark.
            - Keep the total length between 800-1200 words.
            Title: {title}
            Article text: {content}
            Begin the script with "Welcome to [Podcast Name], I'm your host Penelope. Today, we're diving into {title}..."
            """

            response = self.openai_client.chat.completions.create(
                model=self.audio_config.audio_model,
                modalities=["text", "audio"],
                audio= { "voice": self.audio_config.voice, "format": self.audio_config.audio_response_format },
                messages=[
                    {
                    "role": "user",
                    "content": audio_prompt
                    }
                ]
            );


            output_path = f"./app/news_bot/news_bot_v2/audios/{title.lower().replace(' ', '_')}.{self.audio_config.audio_response_format}"
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save the audio file
            audio_bytes = base64.b64decode(response.choices[0].message.audio.data)
            with open(output_path, 'wb') as audio_file:
                audio_file.write(audio_bytes)


            # Calculate audio duration in seconds (mp3 format)
            # MP3 bitrate is typically 32 kbps for speech
            bitrate = 32000  # bits per second
            duration_seconds = (len(audio_bytes) * 8) / bitrate
            
            return {
                'success': True,
                'file_path': output_path,
                'metadata': {
                    'duration': duration_seconds,
                    'format': self.audio_config.audio_response_format,
                    'voice': self.audio_config.voice,
                    'speed': self.audio_config.audio_speed,
                    'file_size_bytes': len(audio_bytes),
                    'file_size_mb': round(len(audio_bytes) / (1024 * 1024), 2),
                    'model': self.audio_config.audio_model,
                    'transcript': response.choices[0].message.audio.transcript,
                },
                'data': audio_bytes
            }

        except requests.RequestException as e:
            raise Exception(f"Audio API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Audio generation failed: {str(e)}")
            
        

# Example of usage:
# if __name__ == "__main__":
#     content = """
#     he Algorand Foundation, in collaboration with T-Hub, has announced the first set of companies to receive investment through the inaugural Start-up Lab program at T-Hub.
#     This strategic partnership aims to accelerate the growth of Web3 startups by providing them with technical support, business mentorship, and access to funding, fostering innovation across various industries through blockchain technology.
#     The selected startups are focused on creating cutting-edge blockchain solutions for sectors such as supply chain management, product authenticity, traceability, cross-border trade, and project finance.
#     Anil Kakani, Vice President and India Country Head at Algorand Foundation, said, "At Algorand, beyond sparking innovation, we aim to cultivate entrepreneurs and support their efforts to deliver impactful and scalable Web3 solutions. We're thrilled to see the first set of companies from our inaugural Start-up Lab program already achieving critical milestones, with solutions spanning from supply chain traceability to trade finance, live event ticketing, and film finance."
#     The Start-up Lab program is designed to fast-track the path to market readiness for emerging startups by combining mentorship from industry veterans with technical expertise. Participating startups benefit from Algorand's blockchain technology, enabling them to build scalable, secure, and efficient solutions with instant finality. Additionally, the program connects them with T-Hub's extensive network of entrepreneurs, investors, and business leaders, facilitating access to crucial funding and partnerships.
#     The five companies selected for this inaugural cohort include:
#     LW3: A platform that enhances supply chain traceability by tokenizing products using a tamper-proof QR code. The solution enables real-time tracking of product movements, improving sustainability and reducing counterfeiting risks.
#     FilmFinance: A blockchain-based platform that connects filmmakers with global investors through fractional tokenization of film assets, offering transparency and efficiency in film financing.
#     Automaxis/FDP Connect: A digitized trade documentation solution that uses blockchain to modernize the bill of lading and automate freight, payments, and documentation, improving global trade efficiency.
#     Astrix: A blockchain-powered fan engagement platform that provides secure ticketing, digital collectibles, and enhanced community experiences for live events, combating fraud and counterfeit tickets.
#     ARVO: An advanced traceability solution combining AI, IoT, and blockchain to combat counterfeiting and improve transparency in industries like automotive and pharmaceuticals.
#     Sujit Jagirdar, Interim CEO at T-Hub, emphasized the importance of the partnership, stating, "The collaboration with Algorand Foundation exemplifies how the T-Hub Start-up Lab propels startups toward success. This investment not only supports these startups in refining their solutions but accelerates their integration into real-world markets."
#     As part of its commitment to driving growth and innovation in the blockchain space, the Algorand Foundation will also help these startups raise further institutional capital to scale their operations and refine their product offerings.
#     """
#     title = "Five Startups Selected for Algorand Foundation and T-Hub's Start-up Lab to Transform Blockchain Applications in Key Sectors"
#     bot_id = 1
#     import asyncio

#     analysis_generator = AnalysisGenerator()

#     # Generate analysis
#     analysis = asyncio.run(analysis_generator.generate_analysis(content, title, bot_id))
#     print(analysis['new_content'])

    # Generate audio
    # audio = asyncio.run(analysis_generator.generate_audio(title, content))
    # print(audio)
