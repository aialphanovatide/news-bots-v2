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

        similarity_threshold = 0.8
        similarity_score = cosine_sim[0][1] 
        if similarity_score >= similarity_threshold:
            print(f"Content similar, score: {similarity_score}")
        else:
            print(f"Content not similar, score: {similarity_score}")
    
    except Exception as e:
        print(f"Exception occurred: {str(e)}")



def cosine_similarity_with_openai(content_1, content_2):
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

        similarity_threshold = 0.8
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
        
        similarity_threshold = 0.8
        similarity_score = cosine_sim[0][1]
        

        if similarity_score >= similarity_threshold:
            print(f"Content similar, score: {similarity_score}")
        else:
            print(f"Content not similar, score: {similarity_score}")
    
    except Exception as e:
        print(f"Exception occurred: {str(e)}")


content_1 = """Gold Price Under Pressure Ahead of US Nonfarm Payrolls
- Gold price (XAU/USD) trades negatively, retracing from two-week highs
- Investors await US Nonfarm Payrolls (NFP) report, influencing Federal Reserve policy
- Rising bets for September interest rate cut and dovish Fed expectations support gold
- Geopolitical tensions in the Middle East also favor gold's upside
- Technical resistance near $2,400, support at $2,060
- China's pause in gold reserves accumulation weighs on gold price"""

content_2 = """ Gold Price Forecast: Stability Expected Ahead of FOMC Meeting
- Gold price expected to remain stable until FOMC meeting and CPI data
- Downward trend continues, with support at $2,300 and resistance at $2,355
- Market awaits hints on first-rate cut and inflation figures
- US dollar index at highest level in a month, benefiting from flight to safety
- Stock indexes fell ahead of CPI report and FOMC meeting
"""


cosine_similarity_modified(content_1, content_2)
cosine_similarity_with_openai(content_1, content_2)
cosine_similarity_with_openai_classification(content_1, content_2)



# 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


