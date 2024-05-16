from .index import client
from slack_sdk.errors import SlackApiError




def send_INFO_message_to_slack_channel(channel_id, title, content, used_keywords, image):
    trimmed_title = title[:1800]
    last_period_index = content.rfind('.', 0, 1970)
    if last_period_index == -1:
        last_period_index = content.find('.', 1970)
        if last_period_index == -1:
            last_period_index = 1970
    trimmed_content = content[:last_period_index + 1]
    trimmed_content = trimmed_content.replace('**', '*')
    formatted_keywords = ', '.join(used_keywords)
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{trimmed_title}*"
            },
            "accessory": {
                "type": "image",
                "image_url": f"{image}",
                "alt_text": f"News Image"
            }
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
                    "text": f"*Used Keywords: {formatted_keywords}*"
                }
            ]
        },
        {
            "type": "actions",
            "block_id": "button_actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "RED"},
                    "style": "primary",
                    "action_id": "red_button"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "YELLOW"},
                    "style": "primary",
                    "action_id": "yellow_button"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "GREEN"},
                    "style": "primary",
                    "action_id": "green_button"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "ADD AS A TOP STORY"},
                    "style": "primary",
                    "action_id": "toystory"
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
            text=title,
            blocks=blocks
        )
        response = result['ok']
        if response == True:
            return f'Message sent successfully to Slack channel {channel_id}'
        return None

    except SlackApiError as e:
        print(
            f'Error sending this message: "{title}" to Slack channel, Reason:\n{str(e)}')
        return None


# send_INFO_message_to_slack_channel(channel_id='C070SM07NGL',
#                                    title_message='test title',
#                                    sub_title='test subtitle',
#                                    message='message'
#                                    )
