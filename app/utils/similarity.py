import os
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

OPENAI_API_KEY = os.getenv('NEWS_BOT_OPENAI_API_KEY')
api_key = OPENAI_API_KEY

def cosine_similarity_modified(content_1, content_2):
    try:
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([content_1, content_2]).toarray()

        cosine_sim = cosine_similarity(vectors)

        similarity_threshold = 0.85
        similarity_score = cosine_sim[0][1] 
        if similarity_score >= similarity_threshold:
            print(f"Content similar, score: {similarity_score}")
        else:
            print(f"Content not similar, score: {similarity_score}")
    
    except Exception as e:
        print(f"Exception occurred in cosine_similarity_modified: {str(e)}")


def cosine_similarity_with_openai_classification(content_1: str, content_2: str) -> float:
    """
    Calculate the cosine similarity between two text contents using OpenAI's text embeddings.

    This function generates embeddings for the input texts using OpenAI's API and then
    computes their cosine similarity.

    Args:
        content_1 (str): The first text content to compare.
        content_2 (str): The second text content to compare.

    Returns:
        float: The cosine similarity score between the two text contents.

    Raises:
        ValueError: If the input contents are empty or the API key is not available.
        Exception: If any error occurs during the embedding or similarity calculation process.
    """
    if not content_1 or not content_2:
        raise ValueError("Both content_1 and content_2 must be non-empty strings.")
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key is not available in the environment.")

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Generate embeddings for both contents
        embeddings = client.embeddings.create(
            input=[content_1, content_2],
            model="text-embedding-3-small"
        )
        
        # Extract embedding vectors
        embedding_1 = embeddings.data[0].embedding
        embedding_2 = embeddings.data[1].embedding

        # Calculate cosine similarity
        similarity_score = cosine_similarity([embedding_1], [embedding_2])[0][0]
        
        return similarity_score

    except Exception as e:
        raise Exception(f"Error in cosine similarity calculation: {str(e)}") from e
    
