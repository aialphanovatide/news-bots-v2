


import requests

headers = {
    "Content-Type": "application/json",
    "x-api-key": "4ee02f03d6e44d46b964d4ff7505bb28"
}

data = {
    "replica_id": "r79e1c033f",
    "script": """Bitcoin experienced a sharp market correction, with its price dropping by $2,000 in just a few hours, falling back to $64,200. This came after briefly surpassing $66,000 over the weekend.

Despite this short-term dip, Bitcoin's long-term performance continues to impress. Over the past year, the cryptocurrency has surged by 136.2%.

One Bitcoin trader recently sold 265.89 BTC for $17.5 million, realizing a profit of $11.28 million after holding for two years. This sale followed Bitcoin's sharp decline, showing a strategic move to capitalize on earlier gains.

According to analysis by IntoTheBlock, a significant portion of Bitcoin holders are still in profit. Most addresses acquired Bitcoin at prices below its current level of $63,318.82.

The recent market drop is attributed to global factors, such as ongoing conflict in the Middle East and anticipation of key U.S. economic data releases.

Looking ahead, experts believe that seasonality, coupled with the potential for a global central bank easing cycle, could boost Bitcoin’s future gains. Additionally, the upcoming U.S. Presidential election may further influence market sentiment."""
}

response = requests.post(
  'https://tavusapi.com/v2/videos', 
  headers=headers, 
  json=data
)

print(response.json())


# Creatify

import requests
import time

# API credentials
API_ID = "YOUR_API_ID"
API_KEY = "YOUR_API_KEY"

# API endpoints
PREVIEW_URL = "https://api.creatify.ai/api/ai_shorts/preview/"
STATUS_URL = "https://api.creatify.ai/api/ai_shorts/{id}/"
RENDER_URL = "https://api.creatify.ai/api/ai_shorts/{id}/render/"

# Headers
headers = {
    "X-API-ID": API_ID,
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def generate_preview(script, aspect_ratio="9x16", style="4K realistic"):
    payload = {
        "script": script,
        "aspect_ratio": aspect_ratio,
        "style": style
    }
    
    response = requests.post(PREVIEW_URL, json=payload, headers=headers)
    return response.json()["id"]

def check_status(video_id):
    url = STATUS_URL.format(id=video_id)
    response = requests.get(url, headers=headers)
    return response.json()

def render_video(video_id):
    url = RENDER_URL.format(id=video_id)
    response = requests.post(url, headers=headers)
    return response.json()

def create_viral_video(script):
    # Generate preview
    video_id = generate_preview(script)
    print(f"Preview generation started. Video ID: {video_id}")

    # Check preview status
    while True:
        status = check_status(video_id)
        if "preview" in status and status["preview"]:
            print("Preview generated successfully.")
            break
        print("Waiting for preview generation...")
        time.sleep(10)

    # Render video
    render_response = render_video(video_id)
    print("Video rendering started.")

    # Check render status
    while True:
        status = check_status(video_id)
        if status["status"] == "done":
            print("Video rendering completed.")
            print(f"Video output URL: {status['video_output']}")
            break
        print("Waiting for video rendering...")
        time.sleep(10)

# Example usage
script = "Meet the Tesla Model X, where cutting-edge technology meets unparalleled performance. Designed with luxury and comfort in mind, the Model X offers a driving experience like no other."
create_viral_video(script)