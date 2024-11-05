import os
import requests
from dotenv import load_dotenv 

load_dotenv()
PERPLEXITY_API = os.getenv("PERPLEXITY_API")

def perplexity_api_request(content, prompt):
    url = "https://api.perplexity.ai/chat/completions"

    if not content or not prompt:
        return {'response': 'content and prompt are required', 'success': False}
    
    model='llama-3.1-sonar-huge-128k-online'
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ]
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {PERPLEXITY_API}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()  # Convierte la respuesta en JSON

        if response_data.get('choices'):
            first_choice = response_data['choices'][0]
            if 'message' in first_choice:
                content_response = first_choice['message']['content']
                
                unwanted_phrases = [
                    "Here is the rewritten headline and summary:",
                    "Here is a rewritten headline and summary of the article:",
                    "Here is the rewritten headline and summary of the article:",
                    "Headline:", "Summary:"
                ]
                for phrase in unwanted_phrases:
                    content_response = content_response.replace(phrase, "").strip()
                
                return {'response': content_response, 'success': True}
            else:
                return {'response': "No 'message' key found in choices", 'success': False}

        else:
            return {'response': "No 'choices' key in the response or 'choices' is empty", 'success': False}

    except requests.exceptions.RequestException as e:
        return {'response': f'Perplexity API request failed: {str(e)}', 'success': False}
    
    except Exception as e:
        return {'response': f'Perplexity failed: {str(e)}', 'success': False}



# Usage Example
# content = (
#     "German Sale, Mt. Gox Repayments Impact Bitcoin • The German government's sale of over 25,000 BTC to exchanges "
#     "led to a significant price surge, but the impact on 24-hour market activity was limited. • The government still "
#     "holds around 16,000 BTC, worth approximately $823 million, after the sale. • Mt. Gox creditors' repayments also "
#     "contributed to the decline in Bitcoin price, which fell below $55,000. • Positive developments in US jobs data "
#     "and predictions of interest rate cuts have led to a rebound in the market. • Institutional inflows into spot Bitcoin "
#     "ETFs and new Ethereum products are expected to support the market recovery. • The global crypto market capitalization "
#     "fell 0.56% to $2.12 trillion, with total crypto market volume reaching $63.61 billion. • Some altcoins, such as XRP, "
#     "Stacks, and Lido DAO, are trading in the green zone, while others, like Notcoin and Flare, are declining."
# )

# prompt = (
#     "Imagine that you are one of the world's foremost experts on Bitcoin and also a globally renowned journalist skilled at summarizing articles about Bitcoin. "
#     "Your job involves two steps.\n"
#     "Step One: Rewrite the headline of the article you are summarizing. Follow these rules for the headline:\n"
#     "(i) The headline should never exceed seven words. It can be shorter, but never longer.\n"
#     "(ii) The headline should avoid sounding like clickbait. It should read like something from the Financial Times or Bloomberg rather than The Daily Mail.\n"
#     "(iii) The headline needs to be as factual as possible. If the headline discusses an opinion, the people or person sharing the opinion should be mentioned in the headline.\n"
#     "Step Two: Summarize the article in bullet points. Follow these rules for the article:\n"
#     "(i) The summary must be concise, focusing only on the most important points in the article.\n"
#     "(ii) If there are secondary points that you think should still be included, create a second summary.\n"
#     "(iii) Remove any content from the article that you consider unnecessary.\n"
#     "(iv) The bullet points should be structured, and the summaries should have a beginning, middle, and end.\n"
#     "(v) If summarizing a longer article (over 1000 words), it's acceptable to use subheadings for the summary.\n"
#     "(vi) Highlight the most important words without using any symbols."
# )

# response = perplexity_api_request(content, prompt)

