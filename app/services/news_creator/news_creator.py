import os
import sys
import json
from pathlib import Path

# Add project root to PYTHONPATH
root_dir = Path(__file__).resolve().parents[3]  # Go up 3 levels to project root
sys.path.append(str(root_dir))

import io
import logging
from openai import OpenAI
from typing import List, Dict, Optional, Any, Union
from werkzeug.datastructures import FileStorage
from app.services.news_creator.tools.request import request_to_link
from app.services.news_creator.tools.docx_extracter import extract_docx_content
from app.services.news_creator.tools.pdf_extracter import extract_pdf_content
from pathlib import Path
import json
import time

class NewsCreatorAgent:
    def __init__(self, api_key: str, verbose: bool = True):
        """Initialize the NewsCreatorAgent with OpenAI API credentials."""
        self._setup_logger(verbose)
        
        self.client = OpenAI(api_key=api_key)
        self.assistant = None
        self.thread = None
        self.uploaded_files = []
        
        # Define supported file types and limits
        self.supported_extensions = ['pdf', 'doc', 'docx', 'txt']
        self.supported_mime_types = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        }
        self.MAX_FILE_SIZE_MB = 512
        self.tools = [
            {"type": "file_search"},
            {"type": "code_interpreter"},
            {
                "type": "function",
                "function": {
                    "name": "request_to_link",
                    "description": "Request to a link or URL and return the article text content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "link": {
                                "type": "string",
                                "description": "The URL to request"
                            }
                        },
                        "required": ["link"]
                    }
                }
            }
        ]

    def _setup_logger(self, verbose: bool):
        """Set up logging configuration based on verbose flag."""
        self.logger = logging.getLogger(__name__)
        
        if verbose:
            self.logger.setLevel(logging.INFO)
            # Create console handler with formatting
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            
            # Add handler to logger if it doesn't already exist
            if not self.logger.handlers:
                self.logger.addHandler(console_handler)
        else:
            self.logger.setLevel(logging.WARNING)

    def list_assistants(self):
        """List all available OpenAI assistants."""
        try:
            assistants = self.client.beta.assistants.list()
            self.logger.info(f"Found {len(assistants.data)} assistants")
            return [model.model_dump() for model in assistants.data]

        except Exception as e:
            self.logger.error(f"Error listing assistants: {str(e)}")
            return []
    
    def create_assistant(self):
        """Create and configure the OpenAI Assistant with file handling capabilities."""
        try:
            # List existing assistants and check for one with our name
            assistants = self.client.beta.assistants.list(
                order="desc",
                limit=100  # Adjust based on your needs
            )
            
            # Look for existing assistant with the same name
            for assistant in assistants.data:
                if assistant.name == "News Story Creator":
                    self.logger.info("Found existing assistant")
                    self.assistant = assistant
                    return assistant
                # If no existing assistant found, create a new one
            self.logger.info("Creating new assistant")
            self.assistant = self.client.beta.assistants.create(
                name="News Story Creator",
                instructions="""You are a professional news writer. Your task is to:
                1. Analyze provided documents for key information
                2. Create comprehensive news stories that are accurate and engaging
                3. Follow journalistic best practices
                4. Include relevant quotes from the source material
                5. Structure stories with headlines, subheadings, and proper formatting
                6. Synthesize information from multiple sources when available""",
                model="gpt-4o",
                tools=self.tools
            )
            return self.assistant
        except Exception as e:
            self.logger.error(f"Error creating/retrieving assistant: {str(e)}")
            raise

    def delete_assistant(self, assistant_id: str) -> bool:
        """
        Delete an OpenAI assistant by ID.

        Args:
            assistant_id (str): The ID of the assistant to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            self.logger.info(f"Attempting to delete assistant: {assistant_id}")
            response = self.client.beta.assistants.delete(assistant_id=assistant_id)
            
            # Check if deletion was successful
            if response.deleted:
                self.logger.info(f"Successfully deleted assistant: {assistant_id}")
                # If this was our current assistant, clear it
                if self.assistant and self.assistant.id == assistant_id:
                    self.assistant = None
                return True
            else:
                self.logger.warning(f"Deletion response indicated failure for assistant: {assistant_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting assistant {assistant_id}: {str(e)}")
            return False

    def retrieve_assistant(self, assistant_id: str):
        """
        Retrieve an existing assistant by ID.

        Args:
            assistant_id (str): The ID of the assistant to retrieve

        Returns:
            The assistant object if found, None if not found or error occurs

        Raises:
            Exception: If there's an error retrieving the assistant
        """
        try:
            self.logger.info(f"Retrieving assistant with ID: {assistant_id}")
            assistant = self.client.beta.assistants.retrieve(assistant_id=assistant_id)
            self.assistant = assistant
            return assistant
        except Exception as e:
            self.logger.error(f"Error retrieving assistant: {str(e)}")
            raise

    def update_assistant(
        self,
        assistant_id: str,
        name: str = None,
        instructions: str = None,
        model: str = None,
        tools: list = None,
        description: str = None,
        metadata: dict = None,
        temperature: float = None,
        top_p: float = None,
        response_format: Union[str, dict] = None
    ) -> Optional[Any]:
        """
        Update an existing assistant's properties.

        Args:
            assistant_id (str): The ID of the assistant to modify
            name (str, optional): New name for the assistant (max 256 chars)
            instructions (str, optional): New system instructions (max 256k chars)
            model (str, optional): New model ID to use
            tools (list, optional): New list of tools (max 128 tools)
            description (str, optional): New description (max 512 chars)
            metadata (dict, optional): New metadata key-value pairs
            temperature (float, optional): New sampling temperature (0 to 2)
            top_p (float, optional): New nucleus sampling value (0 to 1)
            response_format (Union[str, dict], optional): New response format specification

        Returns:
            The modified assistant object if successful, None if error occurs

        Raises:
            Exception: If there's an error updating the assistant
        """
        try:
            self.logger.info(f"Updating assistant with ID: {assistant_id}")
            
            # Build update parameters (only include non-None values)
            update_params = {}
            if name is not None:
                update_params['name'] = name
            if instructions is not None:
                update_params['instructions'] = instructions
            if model is not None:
                update_params['model'] = model
            if tools is not None:
                update_params['tools'] = tools
            if description is not None:
                update_params['description'] = description
            if metadata is not None:
                update_params['metadata'] = metadata
            if temperature is not None:
                update_params['temperature'] = temperature
            if top_p is not None:
                update_params['top_p'] = top_p
            if response_format is not None:
                update_params['response_format'] = response_format

            # Update the assistant
            updated_assistant = self.client.beta.assistants.update(
                assistant_id=assistant_id,
                **update_params
            )
            
            # Update the instance's assistant if it's the same one
            if self.assistant and self.assistant.id == assistant_id:
                self.assistant = updated_assistant
                
            return updated_assistant

        except Exception as e:
            self.logger.error(f"Error updating assistant: {str(e)}")
            raise

    def create_thread(self):
        """Create a new conversation thread."""
        self.thread = self.client.beta.threads.create()
        return self.thread

    def handle_file_upload(self, file: FileStorage) -> Optional[str]:
        """
        Handle a single file upload to OpenAI.
        
        Args:
            file (FileStorage): The file to upload
            
        Returns:
            Optional[str]: The OpenAI file ID if successful, None otherwise
        """
        try:
            self.logger.debug(f"Starting file upload for {file.filename}")
            
            # Validate file extension
            file_extension = file.filename.split('.')[-1].lower()
            self.logger.debug(f"File extension: {file_extension}")
            if file_extension not in self.supported_extensions:
                self.logger.error(f"Unsupported file type: {file.filename}")
                return None
            
            # Validate MIME type
            if hasattr(file, 'content_type'):
                self.logger.debug(f"MIME type: {file.content_type}")
                if file.content_type not in self.supported_mime_types:
                    self.logger.error(f"Unsupported MIME type: {file.content_type}")
                    return None
            else:
                self.logger.debug("No content_type attribute found")
            
            # Check file size
            file.seek(0, os.SEEK_END)
            size_mb = file.tell() / (1024 * 1024)
            file.seek(0)
            self.logger.debug(f"File size: {size_mb:.2f} MB")
            
            if size_mb > self.MAX_FILE_SIZE_MB:
                self.logger.error(f"File too large: {file.filename} ({size_mb:.2f} MB)")
                return None
            
            # Upload to OpenAI
            self.logger.debug("Attempting OpenAI file upload")
            file_response = self.client.files.create(
                file=file.stream,
                purpose='assistants'
            )
            
            if hasattr(file_response, 'id'):
                self.logger.debug(f"File response ID: {file_response.id}")
                self.uploaded_files.append(file_response)
                self.logger.info(f"File uploaded successfully: {file.filename}")
                return file_response.id
            else:
                self.logger.error(f"File upload failed: {file.filename}, Response: {file_response}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error uploading file {file.filename}: {str(e)}")
            self.logger.debug(f"Exception details:", exc_info=True)
            return None

    def process_file(self, file: FileStorage) -> bool:
        """
        Process a single file and create a message with its attachment.
        
        Args:
            file (FileStorage): The file to process
            
        Returns:
            bool: True if processing successful, False otherwise
        """
        file_id = self.handle_file_upload(file)
        if not file_id:
            return False
        
        self.logger.info(f"File ID: {file_id}")
        
        message_content = f"""Please conduct a thorough analysis of this document as a professional researcher:
            1. Identify and extract key facts, figures, and statistical data
        2. Note significant quotes and statements from credible sources
        3. Analyze the methodology and validity of any research presented
        4. Identify the main arguments, findings, and conclusions
        5. Evaluate the credibility and potential biases of the sources
        6. Highlight any limitations or gaps in the information provided
        7. Note relationships to broader context and related research
        8. Extract any relevant dates, locations, and key stakeholders
            Please organize your findings systematically and highlight any particularly noteworthy or unique insights."""
        
        try:
            # Create message with file attachment
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=message_content,
                 attachments=[{
                    "file_id": file_id,
                    "tools": [{"type": "code_interpreter"}]
                }]
            )
            
            # Update thread with file
            self.client.beta.threads.update(
                thread_id=self.thread.id,
                tool_resources= {"code_interpreter": {"file_ids": [file_id]}}
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing file attachment: {str(e)}")
            return False
     
    def create_news_story(
        self, 
        initial_story: Optional[str] = None, 
        files: Optional[List[FileStorage]] = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Create a news story from either provided files or an initial story.
        
        Args:
            initial_story: Optional initial story text or URL
            files: Optional list of FileStorage objects to process
            max_retries: Maximum number of retry attempts for tool execution
            
        Returns:
            Optional[str]: Generated news story or None if failed
            
        Raises:
            ValueError: If neither files nor initial_story is provided
        """
        self.logger.info("Starting news story creation")
        
        if not files and not initial_story:
            self.logger.error("No input provided")
            raise ValueError("Either files or initial_story must be provided")
        
        try:
            # Initialize assistant and thread if needed
            if not self.assistant:
                self.logger.info("Creating new assistant")
                self.create_assistant()
            if not self.thread:
                self.logger.info("Creating new thread")
                self.create_thread()
            
            # Process files if provided
            processed_files = False
            if files:
                self.logger.info(f"Processing {len(files)} files")
                for file in files:
                    if self.process_file(file):
                        processed_files = True
                    else:
                        self.logger.warning(f"Failed to process file: {file.filename}")
                
                if not processed_files and not initial_story:
                    self.logger.error("No files were successfully processed")
                    return None
            
            # Process initial story if provided
            if initial_story:
                self.logger.info("Processing initial story")
                self.client.beta.threads.messages.create(
                    thread_id=self.thread.id,
                    role="user",
                    content=f"Here's the initial story to work with:\n\n{initial_story}"
                )
            
            # Send the story generation prompt
            self.logger.info("Sending story generation prompt")
            prompt = self._create_story_prompt(processed_files, bool(initial_story))
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=prompt
            )
            
            # Start the run
            self.logger.info("Starting assistant run")
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id
            )
            
            retry_count = 0
            while True:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id,
                    run_id=run.id
                )
                
                self.logger.info(f"Run status: {run.status}")
                
                if run.status == "completed":
                    self.logger.info("Run completed successfully")
                    messages = self.client.beta.threads.messages.list(
                        thread_id=self.thread.id
                    )
                    return messages.data[0].content[0].text.value
                    
                elif run.status == "requires_action":
                    retry_count += 1
                    if retry_count > max_retries:
                        self.logger.error(f"Maximum retries ({max_retries}) exceeded")
                        break
                    
                    self.logger.info(f"Tool calls: {run.required_action.submit_tool_outputs.tool_calls}")
                    tool_outputs = self._handle_tool_calls(run.required_action.submit_tool_outputs.tool_calls)
                    
                    if tool_outputs:
                        try:
                            run = self.client.beta.threads.runs.submit_tool_outputs(
                                thread_id=self.thread.id,
                                run_id=run.id,
                                tool_outputs=tool_outputs
                            )
                        except Exception as e:
                            self.logger.error(f"Failed to submit tool outputs: {str(e)}")
                            break
                
                elif run.status in ["failed", "expired", "cancelled"]:
                    self.logger.error(f"Run failed with status: {run.status}")
                    break
                
                time.sleep(2)
        
        except Exception as e:
            self.logger.error(f"Error in create_news_story: {str(e)}")
            raise
        finally:
            self.cleanup_files()

    def _handle_tool_calls(self, tool_calls) -> List[Dict[str, str]]:
        """
        Handle tool calls from the assistant.
        
        Args:
            tool_calls: The tool calls to process
            
        Returns:
            List[Dict[str, str]]: List of tool outputs
        """
        tool_outputs = []
        for tool_call in tool_calls:
            try:
                if tool_call.function.name == "request_to_link":
                    self.logger.info("Executing request_to_link")
                    args = json.loads(tool_call.function.arguments)
                    result = request_to_link(args["link"])
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })

            except Exception as e:
                self.logger.error(f"Tool execution error: {str(e)}")
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": f"Error: {str(e)}"
                })
        
        return tool_outputs
 
    def _create_story_prompt(self, file_paths, initial_story) -> str:
        """Create the comprehensive prompt for story generation."""
        base_content = "Based on {} provided, please create a comprehensive news story following these detailed steps:"
        source_text = "the documents" if file_paths and not initial_story else \
                    "the initial story" if initial_story and not file_paths else \
                    "both the documents and initial story"
        
        return f"""{base_content.format(source_text)}
            1. RESEARCH & ANALYSIS
        - Extract key facts, dates, and events
        - Identify main stakeholders and their roles
        - Note significant quotes and statements
        - Verify any statistical data or figures
        - Identify potential gaps in information
            2. STORY STRUCTURE
        - Create an attention-grabbing headline
        - Write a compelling lead paragraph that answers the 5 W's
        - Develop a clear narrative arc
        - Organize information in order of importance
        - Include relevant subheadings
            3. CONTENT DEVELOPMENT
        - Provide necessary background context
        - Include supporting evidence and examples
        - Integrate quotes naturally into the narrative
        - Present balanced viewpoints
        - Add relevant statistical data
            4. WRITING STYLE
        - Use clear, concise language
        - Maintain an objective tone
        - Avoid unnecessary jargon
        - Use active voice
        - Vary sentence structure
        Please format the story professionally with clear sections and proper attribution."""

    def cleanup_files(self):
        """Delete uploaded files to free up resources."""
        for file in self.uploaded_files:
            try:
                self.client.files.delete(file.id)
            except Exception as e:
                print(f"Error deleting file {file.id}: {str(e)}")
        self.uploaded_files = []
