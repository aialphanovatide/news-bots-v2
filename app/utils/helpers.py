
import json
import os

from flask import app
import requests

from config import Bot

# async def save_dict_to_json(data_dict, filename='data.json'):
#     try:
#         if os.path.exists(filename):
#             # If the file already exists, generate a new filename with a numeric suffix
#             index = 1
#             while True:
#                 new_filename = f"{os.path.splitext(filename)[0]}_{index}.json"
#                 if not os.path.exists(new_filename):
#                     filename = new_filename
#                     break
#                 index += 1

#         async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
#             await file.write(json.dumps(data_dict, indent=4))
#         print("Data saved to", filename)
#     except Exception as e:
#         print("Error:", e)

def resolve_redirects(url):
    try:
        response = requests.get(url, allow_redirects=False)
        if response.status_code in (300, 301, 302, 303):
            redirect_url = response.headers['location']
            return resolve_redirects(redirect_url)
        else:
            return response.url
    except Exception as e:
        print(f"Error al resolver redireccionamientos: {e}")
        return None


# # Saves a long string to a TXT file
# async def save_string_to_txt(string, filename='news.txt'):
#     try:
#         async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
#             await file.write(string)
#         print("News saved to", filename)
#     except Exception as e:
#         print("Error:", e)


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