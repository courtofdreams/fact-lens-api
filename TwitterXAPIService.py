
import requests


class TwitterXAPIService:
    def __init__(self, api_key, api_secret_key, access_token, access_token_secret, bearer_token):
        self.api_key = api_key
        self.api_secret_key = api_secret_key
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.bearer_token = bearer_token

    def get_tweet(self, tweet_id) -> str:
        """
        Fetch a tweet by its ID.
        """
        url = f"https://api.twitter.com/2/tweets?ids={tweet_id}"
        headers = {
        "Authorization": f"Bearer {self.bearer_token}",
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return {"error": f"HTTP error occurred: {http_err}"}
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
            return {"error": f"Request error occurred: {req_err}"}
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return {"error": f"An unexpected error occurred: {e}"}