import requests
import aiofiles
import json
import os
from functools import wraps
from playwright.sync_api import sync_playwright
import time


# Takes a string and change to lowercase and join with _
def transform_string(input_string):
    if not isinstance(input_string, str):
        return None
    # Convert the string to lowercase
    lower_string = input_string.lower()
    # Split the string into words
    words = lower_string.split()
    # Double each word and join them with underscores
    doubled_words = '_'.join(word + '_' + word for word in words)
    return doubled_words

# Recursive function that aims to resolve redirects URLs
def resolve_redirects(url):
    try:
        response = requests.get(url, allow_redirects=False)
        if response.status_code in (300, 301, 302, 303):
            redirect_url = response.headers['location']
            return resolve_redirects(redirect_url)
        else:
            return response.url
    except Exception as e:
        print(f"Error while resolving redirect: {e}")
        return None
    

def resolve_redirects_playwright(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Puedes usar p.firefox o p.webkit si prefieres otro navegador
        page = browser.new_page()
        page.goto(url)
        time.sleep(4)

        page.evaluate("""
            navigator.clipboard.writeText(window.location.href).then(function() {
                console.log('URL ok');
            }, function(err) {
                console.error('Error: ', err);
            });
        """)

        time.sleep(1)

        # Obtener la URL actual
        final_url = page.url

        browser.close()
        return final_url


def resolve_redirects_v2(url, timeout=100, max_redirects=100):
    try:
        visited_urls = set()
        current_url = url

        for _ in range(max_redirects):
            if current_url in visited_urls:
                print(f"Detected loop in redirects at {current_url}")
                return None
            visited_urls.add(current_url)

            response = requests.get(current_url, allow_redirects=False, timeout=timeout)
            
            if response.status_code in (300, 301, 302, 303):
                current_url = response.headers.get('location')
                if not current_url:
                    print("Redirect location header missing.")
                    return None
            else:
                print("response redir: ", response.url)
                return response.url

        print(f"Max redirects ({max_redirects}) exceeded.")
        return None

    except requests.exceptions.ConnectTimeout:
        print(f"Connection to {url} timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error while resolving redirect: {e}")
        return None

# Saves a Dict of elements into a JSON file
async def save_dict_to_json(data_dict, filename='data.json'):
    try:
        if os.path.exists(filename):
            # If the file already exists, generate a new filename with a numeric suffix
            index = 1
            while True:
                new_filename = f"{os.path.splitext(filename)[0]}_{index}.json"
                if not os.path.exists(new_filename):
                    filename = new_filename
                    break
                index += 1

        async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(data_dict, indent=4))
        print("Data saved to", filename)
    except Exception as e:
        print("Error:", e)


# Saves a long string to a TXT file
async def save_string_to_txt(string, filename='news.txt'):
    try:
        async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
            await file.write(string)
        print("News saved to", filename)
    except Exception as e:
        print("Error:", e)


# # Saves a list of elements into a JSON file
# async def save_list_to_json(data_list, filename='data.json'):
#     try:
#         if os.path.exists(filename):
#             count = 1
#             while True:
#                 new_filename = f"{os.path.splitext(filename)[0]}_{count}.json"
#                 if not os.path.exists(new_filename):
#                     break
#                 count += 1
#             filename = new_filename

#         async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
#             await file.write(json.dumps(data_list, ensure_ascii=False, indent=4))
#         print("Data saved to", filename)
#     except Exception as e:
#         print("Error:", e)




def measure_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time for {func.__name__}: {execution_time} seconds")
        return result
    return wrapper
