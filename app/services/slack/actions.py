from app.services.slack.index import client
from slack_sdk.errors import SlackApiError


# Send news to the specified Slack Channel
def send_NEWS_message_to_slack_channel(channel_id: str, title: str, 
                                       article_url: str, content: str, 
                                       used_keywords: list[str], image: str):
   
    trimmed_title = title[:1800]
    last_period_index = content.rfind('.', 0, 1970)
    if last_period_index == -1:
        last_period_index = content.find('.', 1970)
        if last_period_index == -1:
            last_period_index = 1970
    trimmed_content = content[:last_period_index + 1]
    trimmed_content = trimmed_content.replace('**', '*')
    
    formatted_keywords = ', '.join(used_keywords)
 
    # print('trimmed_content: ', trimmed_content)
    # print('trimmed_title: ', trimmed_title)
    # print('used_keywords: ', used_keywords)
    # print('image: ', image)
    # print('article_url: ', article_url)
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{trimmed_title}",
                "emoji": True
            }
        },
        {
			"type": "image",
			"image_url": f"{image}",
			"alt_text": f"{title}"
		},
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"{article_url}"
                }
            ]
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"{trimmed_content}"
                }
            ]
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Used Keywords:* {formatted_keywords}"
                }
            ]
        },
        {
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*Send to AI Alpha App*"
			},
			"accessory": {
				"type": "button",
				"text": {
					"type": "plain_text",
					"text": "ADD AS TOP STORY",
					"emoji": True
				},
				"value": f"link_to_article: {article_url}",
				"action_id": "add_to_top_story"
			}
		},
        {
            "dispatch_action": True,
			"type": "input",
			"element": {
				"type": "plain_text_input",
				"action_id": "green"
			},
			"label": {
				"type": "plain_text",
				"text": "GREEN",
				"emoji": True
			}
		},
        {
            "dispatch_action": True,
			"type": "input",
			"element": {
				"type": "plain_text_input",
				"action_id": "red"
			},
			"label": {
				"type": "plain_text",
				"text": "RED",
				"emoji": True
			}
		},
        {
            "dispatch_action": True,
			"type": "input",
			"element": {
				"type": "plain_text_input",
				"action_id": "yellow"
			},
			"label": {
				"type": "plain_text",
				"text": "YELLOW",
				"emoji": True
			}
		},
        {
            "type": "divider"
        }
    ]

    try:
        result = client.chat_postMessage(
            channel=channel_id,
            text=title,
            blocks=blocks
        )

        response = result['ok']
        ts = result['ts']
        print(f'Slack message timestamp:', ts)

        if response:
            return {'response': f'Message sent successfully to Slack channel {channel_id}', 'success': True}
        return {'error': 'Response error from slack API', 'success': False}

    except SlackApiError as e:
        return {'error': f'Slack API Error: {str(e)}', 'success': False}
    except Exception as e:
        return {'error': f'Error while sending message to slack: {str(e)}', 'success': False}



# Deletes a message in Slack
def delete_messages_in_channel(ts_messages_list, channel_id="C071142J72R"):
    try:
        for message in ts_messages_list:
            response = client.chat_delete(
                channel=channel_id,
                ts=message
            )
            if not response["ok"]:
                print(f"---Failed to delete message with timestamp {message}. Error: {response['error']}---")
            else:
                print(f"---Deleted message with timestamp {message}---")

        return 'All messages deleted in Slack'
    except Exception as e:
        print(f'---Error while deleting messages in Slack: {str(e)}---')
        return f'Error while deleting messages in Slack: {str(e)}'



# Sends a message to a Slack channel
def send_WARNING_message_to_slack_channel(channel_id, title_message, sub_title, message):
        
        blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title_message}*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*{sub_title}:*\n{message}"
                        }
                    ]
                },
                {
                "type": "divider"
                }
            ]
    
        try:
            result = client.chat_postMessage(
                channel=channel_id,
                text=title_message, 
                blocks=blocks
            )

            response = result['ok']
            ts = result['ts']
            print(f'Slack message timestamp:', ts)
           
            if response:
                return {'response': f'Message sent successfully to Slack channel {channel_id}', 'success': True}
            else:
                return {'error': response, 'success': False}

        except SlackApiError as e:
            return {'error': f'Slack API error: {str(e)}', 'success': False }
        except Exception as e:
            return {'error': f'Error sending message to slack: {str(e)}', 'success': False}
        














# send_NEWS_message_to_slack_channel(channel_id='C071142J72R',
#                                    title='Gold rally continues with buyers eyeing $2,400 as inflation recedes',
#                                    article_url='https://www.fxstreet.com/news/gold-price-soars-to-three-week-high-amid-easing-inflation-rate-cut-hopes-202405151942',
#                                    content="""
# Introduction
# Gold prices surged to a three-week high of $2,390, reflecting a 1% gain. This increase is set against a backdrop of declining US Treasury bond yields and a weakening US Dollar Index (DXY), which fell to a five-week low. Key economic indicators, including April's stagnant Retail Sales and signals from the Federal Reserve, have influenced market movements, suggesting potential shifts in monetary policy. This analysis explores the multifaceted reasons behind the gold price surge, the implications of the current economic data, and the broader economic landscape.

# Gold Price Dynamics
# Gold's Appeal Amid Economic Uncertainty
# Gold, often viewed as a safe-haven asset, tends to attract investors during periods of economic uncertainty. The recent increase in gold prices can be attributed to several factors:

# Inflation Data: The US Bureau of Labor Statistics (BLS) reported that inflation is showing signs of easing, which raises expectations for a potential Federal Reserve rate cut in 2024. This has made gold more attractive as lower interest rates reduce the opportunity cost of holding non-yielding assets like gold.

# US Dollar Weakness: The US Dollar Index (DXY) dropped to its lowest level in five weeks. A weaker dollar makes gold cheaper for holders of other currencies, thereby boosting demand.

# Declining Treasury Yields: US Treasury bond yields, particularly along the short and long ends of the curve, have plunged between 8 and 10 basis points. Lower yields diminish the attractiveness of fixed-income securities relative to gold.

# Economic Indicators and Their Implications
# Inflation Trends
# The BLS data revealed a slowing in consumer inflation, which has significant implications:

# Consumer Price Index (CPI): April’s CPI rose by 0.3% month-over-month (MoM), below both the estimates and the previous month's 0.4% increase. The core CPI, which excludes volatile food and energy prices, also rose by 0.3% MoM, again below the prior reading of 0.4%.

# Inflation Expectations: Despite the current easing, inflation expectations for the coming year have increased. The New York Federal Reserve’s monthly Survey of Consumer Expectations showed a rise in inflation expectations to 3.3% from 3% in March.

# These mixed signals reflect ongoing uncertainty about the inflation trajectory and the Fed’s monetary policy responses.

# Retail Sales and Consumer Spending
# April’s Retail Sales data showed stagnation with a 0% change month-over-month, significantly below the expected 0.4% increase. This stagnation indicates weaker consumer spending, which is a critical driver of economic growth. The data highlights several points:

# Economic Slowdown: The stagnation in retail sales suggests that consumers are becoming more cautious amid economic uncertainty, possibly due to inflationary pressures and higher interest rates.

# Impact on Monetary Policy: Weaker consumer spending might prompt the Federal Reserve to reconsider its restrictive monetary policy stance. Lower interest rates could stimulate spending and investment, providing a boost to the economy.

# Federal Reserve's Stance and Market Expectations
# Fed Officials' Comments
# Federal Reserve officials have provided mixed signals regarding future monetary policy:

# Neel Kashkari: The Minneapolis Fed President mentioned that higher government debt might necessitate higher borrowing costs in the short term to achieve the Fed’s 2% inflation target. His comments reflect a cautious stance towards easing monetary policy prematurely.

# Jerome Powell: The Fed Chair expressed expectations for continued disinflation but noted less confidence in the disinflation outlook than before. This suggests a wait-and-see approach, balancing between combating inflation and supporting economic growth.

# Market Expectations
# Market expectations for interest rate cuts have increased. Data from the Chicago Board of Trade indicated that expectations for a rate cut towards the end of the year rose from 35 basis points to 42 basis points. This shift is driven by:

# Economic Data: The recent economic indicators, including inflation and retail sales data, suggest that the economy might need monetary easing sooner than previously anticipated.

# Investor Sentiment: Lower Treasury yields and a weaker dollar indicate that investors are positioning for a potential easing of monetary policy.

# Broader Economic Context
# Global Economic Environment
# The US economic indicators are also influenced by global factors:

# Geopolitical Uncertainty: Ongoing geopolitical tensions and trade uncertainties can drive investors towards safe-haven assets like gold.

# Global Economic Slowdown: Signs of a slowdown in major economies, including China and the Eurozone, can impact US economic growth and monetary policy decisions.

# Commodity Markets
# Gold’s price movements are also affected by developments in other commodity markets:

# Oil Prices: Changes in oil prices can influence inflation expectations and, consequently, monetary policy decisions. A significant rise in oil prices could reignite inflationary pressures, affecting gold prices.

# Commodity Demand: Broader trends in commodity demand, influenced by industrial activity and economic growth prospects, also play a role.

# Conclusion
# The recent surge in gold prices to a three-week high of $2,390 reflects a complex interplay of factors, including declining US Treasury bond yields, a weaker US Dollar, and evolving expectations around Federal Reserve monetary policy. Key economic indicators, such as slowing inflation and stagnant retail sales, have significant implications for future interest rate decisions. Fed officials' comments and market expectations suggest a cautious but growing sentiment towards potential rate cuts in 2024. This analysis underscores the importance of monitoring economic data and central bank communications to understand the drivers of gold prices and broader market trends.
# """,
#                                    used_keywords=['Gold', 'Federal Reserve'],
#                                    image='https://apparticleimages.s3.us-east-2.amazonaws.com/Crypto Market Outlook for 2024: Trends and Predictions.jpg'
#                                    )

# Example usage
# ts_list = ['1715877213.683879']
# delete_messages_in_channel(ts_messages_list=ts_list)


# Example usage
# send_WARNING_message_to_slack_channel(channel_id='C071142J72R', 
#                                       title_message='Warning test message',
#                                       sub_title='reason',
#                                       message='test message'
#                                       )