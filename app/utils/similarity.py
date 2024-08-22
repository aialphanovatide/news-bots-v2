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



# article1="""
# Despite having a massive head start on the Bitcoin exchange-traded fund (ETF) market when Bitcoin ETFs were approved in January, Grayscale has seen its first-mover advantage evaporate.

# The firm is a leading fund manager within the crypto space, and last year won its appeal against the U.S. Securities and Exchange Commission (SEC) to convert its Grayscale Bitcoin Trust (GBTC) into a spot Bitcoin ETF. The trust previously operated like a closed-end fund but was effectively the only such investment product on the market.

# When its converted fund was among several Bitcoin ETFs approved by the regulator on Jan. 10, Grayscale held most of the cards.

# “Grayscale was the first in the space to offer an ‘ETF-type product,’” Tom Cohen, head trader at crypto asset manager Algoz Technologies, told Decrypt. “Grayscale was always going to lose market share for their BTC and ETH product against the huge marketing budgets and customer bases of these [other] providers.”
# """

# article2="""
# Bitcoin (BTC) price is inching closer to reclaiming its post-halving reaccumulation range, setting the market abuzz with anticipation. Amid critical weekly close, traders and investors are keenly watching the $60,600 level. As of now, BTC price is slightly above this threshold at $60,700.

# Stock Market Rally To Fuel Bitcoin Price Surge

# Crypto analyst Rekt Capital expects BTC to enter the post-Halving reaccumulation phase if it closes above $60,600 this week. Bitcoin price is currently well above $60,600. However, since there are six days left for the week to end, the uncertainty remains.
# Nonetheless, one of the significant factors catalyzing Bitcoin’s upward momentum is the ongoing stock market rally. According to QCP Capital’s analysis released today, momentum traders and trend-followers are re-leveraging their positions.

# This activity has been amplified by August’s lower liquidity, which typically sees reduced trading volumes as major financial institutions and traders take summer vacations. Adding fuel to this rally, corporate share buybacks have surged. Companies buying back a staggering $1.15 trillion worth of shares this year.

# This trend has been particularly pronounced among clients of Goldman Sachs’ trading unit. It has reported record demand for buying dips in the market. Hence, QCP Capital noted this surge in share buybacks reflects corporate confidence and could have a spillover effect on other risk assets, including Bitcoin.

# The risk-on sentiment evident in the equities market could extend to cryptocurrencies and precious metals like gold. Bitcoin, in particular, stands to benefit from this environment as demand for topside call options on BTC increases. This growing interest in bullish options suggests that traders are betting on further Bitcoin price appreciation.

# U.S. Election Dynamics

# However, the upcoming U.S. 2024 elections remain a critical focal point for market participants. QCP Capital notes a skew in Bitcoin options favoring puts ahead of the election, indicating some caution among traders. There is a significant six-point volatility spread between pre and post-election expiries. This reflects uncertainty about the election’s outcome and its potential impact on Bitcoin price.
# Meanwhile, Democrats are losing the crypto community’s support as the Democratic platform shunned crypto. Whilst, the Republicans have pledged to end what they describe as an “unlawful and un-American crypto crackdown.”

# Zach Pandl, Grayscale Investments’ Managing Director of Research, recently expressed a bullish outlook on Bitcoin’s near-term prospects. In a recent interview, Pandl suggested that BTC is poised to rally, regardless of the outcome of the upcoming U.S. election. Furthermore, the Grayscale exec emphasized Bitcoin’s long-term potential, particularly as a hedge against looming depreciation of the U.S. dollar.

# Short Liquidations & ETF Flows Impact On BTC Price

# Another key factor contributing to recent Bitcoin price movements is the liquidation of short positions. According to data from Coinglass, Bitcoin short liquidations totaled $25.90 million, significantly outpacing the $5.23 million in long liquidations.

# When short positions are liquidated, traders are forced to buy back Bitcoin to minimize their losses, which can drive the price higher. In addition to short liquidations, spot Bitcoin ETF flows have been positive, further supporting the price recovery.
# """

# cosine_similarity_with_openai_classification(article1, article2)