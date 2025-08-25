import requests

def validate_email(email, token):
    """
    Validate an email address using Clearout.io API.
    
    Args:
        email (str): The email address to validate.
        token (str): Your Clearout.io API token.
    
    Returns:
        dict: The API response in JSON format.
    """
    url = "https://api.clearout.io/v2/email_verify/instant"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {
        "email": email
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx, 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Replace with your Clearout.io API token and the email to test
API_TOKEN = "a4f6a382794e46adf8c03c69b2177883:809b4198d27ef739ca0597d8756bafc72af52f273d05198d07e5bf3bde35a09e"
EMAIL_TO_TEST = "painful_knees@nerves.sa.com"
EMAIL_TO_TEST = "phil@your.it"

# Call the function
result = validate_email(EMAIL_TO_TEST, API_TOKEN)

# Print the result
print(result)
