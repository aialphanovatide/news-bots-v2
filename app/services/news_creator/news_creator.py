import os
from openai import OpenAI
from typing import List, Dict, Optional
from pathlib import Path
import time

class NewsCreatorAgent:
    def __init__(self, api_key: str):
        """Initialize the NewsCreatorAgent with OpenAI API credentials."""
        self.client = OpenAI(api_key=api_key)
        self.assistant = None
        self.thread = None
        self.uploaded_files = []
    
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
            tools=[
                {"type": "file_search"},
                {"type": "code_interpreter"}
            ]
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
        file_paths: Optional[List[str]] = None, 
        initial_story: Optional[str] = None
    ) -> str:
        """
        Create a news story from either provided documents or an initial story.
        
        Args:
            file_paths: Optional list of file paths to process
            initial_story: Optional initial story text to expand upon
            
        Returns:
            str: Generated news story
            
        Raises:
            ValueError: If neither file_paths nor initial_story is provided
        """
          
        # Input validation
        if not file_paths and not initial_story:
            raise ValueError("Either file_paths or initial_story must be provided")
        
        if not self.assistant:
            self.create_assistant()
        if not self.thread:
            self.create_thread()
        
        # Process files if provided
        if file_paths:
            for file_path in file_paths:
                success = self.process_file(file_path)
                if not success:
                    print(f"Failed to process {file_path}")

        # Process initial story if provided
        if initial_story:
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=f"Here's the initial story to work with:\n\n{initial_story}"
            )
        
        # Create a comprehensive prompt for news story generation
        base_content = "Based on {} provided, please create a comprehensive news story following these detailed steps:"
        source_text = "the documents" if file_paths and not initial_story else \
                    "the initial story" if initial_story and not file_paths else \
                    "both the documents and initial story"
        
        prompt = f"""{base_content.format(source_text)}

        1. RESEARCH & ANALYSIS
        - Extract key facts, dates, and events
        - Identify main stakeholders and their roles
        - Note significant quotes and statements
        - Verify any statistical data or figures
        - Identify potential gaps in information

        2. STORY STRUCTURE
        - Create an attention-grabbing headline
        - Write a compelling lead paragraph that answers the 5 W's (Who, What, Where, When, Why)
        - Develop a clear narrative arc
        - Organize information in order of importance (inverted pyramid style)
        - Include relevant subheadings to break up the text

        3. CONTENT DEVELOPMENT
        - Provide necessary background context
        - Include supporting evidence and examples
        - Integrate quotes naturally into the narrative
        - Present balanced viewpoints when applicable
        - Address potential counterarguments or alternative perspectives
        - Add relevant statistical data or research findings

        4. WRITING STYLE
        - Use clear, concise language
        - Maintain an objective tone
        - Avoid jargon unless necessary (with explanations if used)
        - Use active voice predominantly
        - Vary sentence structure for better readability

        5. STORY ELEMENTS
        - Include relevant human interest elements
        - Highlight impact on stakeholders or community
        - Provide future implications or next steps
        - Add context about broader trends or related events
        - Include expert perspectives when available

        6. FINAL POLISH
        - Ensure proper attribution for all sources
        - Verify accuracy of all facts and figures
        - Check for logical flow and transitions
        - Review for clarity and coherence
        - Add any necessary disclaimers or notes

        Please format the story professionally with:
        - A clear headline
        - Subheadings where appropriate
        - Properly formatted paragraphs
        - Clear attribution for quotes and sources
        - A strong concluding paragraph

        Remember to maintain journalistic integrity and focus on factual, unbiased reporting."""

        # Send the comprehensive prompt
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=prompt
        )
        
        # Run the assistant
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
        )
        
        # Wait for completion
        while True:
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=run.id
            )
            if run_status.status == 'completed':
                break
            elif run_status.status == 'failed':
                raise Exception("Assistant run failed: ", run_status.last_error)
            elif run_status.status == 'requires_action':
                # Handle any required actions (if implementing function calling)
                pass
            time.sleep(1)
        
        # Get the response
        messages = self.client.beta.threads.messages.list(
            thread_id=self.thread.id
        )
        
        # Clean up - delete uploaded files
        self.cleanup_files()
        
        # Return the assistant's response
        return messages.data[0].content[0].text.value
    
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