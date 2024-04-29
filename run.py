from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
app.name = 'news_bot'
CORS(app, origins=['http://example.com'])

if __name__ == '__main__':
    app.run(debug=True, user_reloader=True)