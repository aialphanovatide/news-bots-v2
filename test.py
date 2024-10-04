


import requests

headers = {
    "Content-Type": "application/json",
    "x-api-key": "4ee02f03d6e44d46b964d4ff7505bb28"
}

data = {
    "replica_id": "r79e1c033f",
    "script": """"Bitcoin experienced a sharp market correction, with its price dropping by $2,000 in just a few hours, falling back to $64,200. This came after briefly surpassing $66,000 over the weekend.

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