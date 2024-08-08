from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = '/Users/agustinbustamante/news-bots-v2/app/services/google_drive/animated-bay-419919-a83a8335f711.json'

def authenticate():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

def get_folder_id(service, folder_name, parent_id=None):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        pageSize=10
    ).execute()
    
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    return None

def create_folder(service, folder_name, parent_id=None):
    folder_id = get_folder_id(service, folder_name, parent_id)
    if folder_id:
        return folder_id
    
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id] if parent_id else []
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_file(folder_name, file_name, file_path):
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)
    
    # ID de la carpeta padre NewsCreatorFiles
    parent_folder_id = '1dGoWDtM3QR-Yi8qEBroxesTDdF3E5sZW'
    
    # Crea la carpeta dentro de NewsCreatorFiles si no existe
    folder_id = create_folder(service, folder_name, parent_folder_id)
    
    if not folder_id:
        print(f"Folder '{folder_name}' not found or could not be created.")
        return
    
    print(f"Uploading to folder ID: {folder_id}")
    
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"File ID: {file.get('id')}")
    
    except Exception as e:
        print(f"Failed to upload file to Google Drive: {e}")


