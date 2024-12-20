import os
import logging
from openai import OpenAI
from typing import List, Dict, Optional
from app.services.news_creator.tools.request import request_to_link
from pathlib import Path
import json
import time

class NewsCreatorAgent:
    def __init__(self, api_key: str):
        """Initialize the NewsCreatorAgent with OpenAI API credentials."""

        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Create console handler with formatting
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(console_handler)

        self.client = OpenAI(api_key=api_key)
        self.assistant = None
        self.thread = None
        self.uploaded_files = []
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
    
    def create_assistant(self):
        """Create and configure the OpenAI Assistant with file handling capabilities."""
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

    def create_thread(self):
        """Create a new conversation thread."""
        self.thread = self.client.beta.threads.create()
        return self.thread

    def upload_file(self, file_path: str) -> str:
        """Upload a single file to OpenAI and return its file ID."""
        try:
            with open(file_path, 'rb') as file:
                uploaded_file = self.client.files.create(
                    file=file,
                    purpose='assistants'
                )
                self.uploaded_files.append(uploaded_file)
                return uploaded_file.id
        except Exception as e:
            print(f"Error uploading {file_path}: {str(e)}")
            return None

    def process_file(self, file_path: str):
        """Process a single file and create a message with its attachment."""
        file_id = self.upload_file(file_path)
        if not file_id:
            return False

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
        
        # Create message with single file attachment
        try:
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=message_content,
                attachments=[{
                    "file_id": file_id,
                    "tools": ["file_search", "code_interpreter"]
                }]
            )
            return True
        except Exception as e:
            print(f"Error creating message with attachment {file_id}: {str(e)}")
            return False

    def create_news_story(
        self, 
        initial_story: Optional[str] = None, 
        file_paths: Optional[List[str]] = None,
        max_retries: int = 2
    ) -> str:
        """
        Create a news story from either provided documents or an initial story.
        
        Args:
            initial_story: Optional initial story text or URL to expand upon
            file_paths: Optional list of file paths to process
            max_retries: Maximum number of retry attempts for tool execution
                
        Returns:
            str: Generated news story
                
        Raises:
            ValueError: If neither file_paths nor initial_story is provided
        """
        self.logger.info("Starting news story creation")
            
        # Input validation
        if not file_paths and not initial_story:
            self.logger.error("No input provided: both file_paths and initial_story are empty")
            raise ValueError("Either file_paths or initial_story must be provided")
        
        try:
            # Initialize assistant and thread if needed
            if not self.assistant:
                self.logger.info("Creating new assistant")
                self.create_assistant()
            if not self.thread:
                self.logger.info("Creating new thread")
                self.create_thread()
            
            # Process files if provided
            if file_paths:
                self.logger.info(f"Processing {len(file_paths)} files")
                for file_path in file_paths:
                    success = self.process_file(file_path)
                    if not success:
                        self.logger.error(f"Failed to process file: {file_path}")
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
            prompt = self._create_story_prompt(file_paths, initial_story)
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
                # Get the current run status
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
                    self.cleanup_files()
                    return messages.data[0].content[0].text.value
                    
                elif run.status == "requires_action":
                    retry_count += 1
                    if retry_count > max_retries:
                        self.logger.error(f"Maximum retries ({max_retries}) exceeded")
                        self.cleanup_files()
                        return None
                    
                    self.logger.info(f"Processing required actions (Attempt {retry_count}/{max_retries})")
                    tool_outputs = []
                    
                    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                        try:
                            if tool_call.function.name == "request_to_link":
                                self.logger.info(f"Executing request_to_link")
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
                    
                    if tool_outputs:
                        try:
                            self.logger.info("Submitting tool outputs")
                            run = self.client.beta.threads.runs.submit_tool_outputs(
                                thread_id=self.thread.id,
                                run_id=run.id,
                                tool_outputs=tool_outputs
                            )
                        except Exception as e:
                            self.logger.error(f"Failed to submit tool outputs: {str(e)}")
                            self.cleanup_files()
                            return None
                    
                elif run.status in ["failed", "expired", "cancelled"]:
                    self.logger.error(f"Run failed with status: {run.status}")
                    self.cleanup_files()
                    return None
                
                time.sleep(2)  # Wait before checking status again
                
        except Exception as e:
            self.logger.error(f"Error in create_news_story: {str(e)}")
            self.cleanup_files()
            raise
 
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

# def main():
#     """Example usage of the NewsCreatorAgent."""
#     agent = NewsCreatorAgent(api_key)
    
#     # Example 1: Using files only
#     # files = ["news_source1.pdf", "news_source2.docx"]
#     # try:
#     #     story1 = agent.create_news_story(file_paths=files)
#     #     print("Story from files:", story1)
#     # except Exception as e:
#     #     print(f"Error creating story from files: {str(e)}")
    
#     # Example 2: Using initial story only
#     initial_story = """
#     go to this link https://finance.yahoo.com/news/bitcoin-selloff-overdone-why-grayscale-175954860.html and create a news story about it.
#     """
#     try:
#         story2 = agent.create_news_story(initial_story=initial_story)
#         print("Story from initial text:", story2)
#     except Exception as e:
#         print(f"Error creating story from initial text: {str(e)}")
    
#     # Example 3: Using both files and initial story
#     # try:
#     #     story3 = agent.create_news_story(file_paths=files, initial_story=initial_story)
#     #     print("Combined story:", story3)
#     # except Exception as e:
#     #     print(f"Error creating combined story: {str(e)}")

# if __name__ == "__main__":
#     main()