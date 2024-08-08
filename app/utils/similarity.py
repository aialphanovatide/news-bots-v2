import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

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
        print(f"Exception occurred: {str(e)}")


def cosine_similarity_with_openai_classification(content_1, content_2):
    try:
        client = openai.OpenAI(api_key=api_key)
        response_1 = client.embeddings.create(
            input=content_1,
            model="text-embedding-ada-002"
        )
        response_2 = client.embeddings.create(
            input=content_2,
            model="text-embedding-ada-002"
        )
        
        embedding_1 = response_1.data[0].embedding
        embedding_2 = response_2.data[0].embedding

        vectors = [embedding_1, embedding_2]
        cosine_sim = cosine_similarity(vectors)
        
        similarity_score = cosine_sim[0][1]
        
        similarity_threshold = 0.9
        if similarity_score >= similarity_threshold:
            print(f"Content similar, score: {similarity_score}")
            return similarity_score 
        else:
            print(f"Content not similar, score: {similarity_score}")
            return similarity_score  
    
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None  # Devuelve None en caso de excepción


