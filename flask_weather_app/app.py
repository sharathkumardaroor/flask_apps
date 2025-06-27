import os
from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
API_KEY = os.getenv('OPENWEATHER_API_KEY')
BASE_URL = 'https://api.openweathermap.org/data/2.5/'

def get_weather(city):
    url = f"{BASE_URL}weather?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def get_forecast(city):
    url = f"{BASE_URL}forecast?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    weather = None
    forecast = None
    city = ''
    if request.method == 'POST':
        city = request.form['city']
        weather = get_weather(city)
        forecast = get_forecast(city)
        if not weather:
            flash('City not found or API error.')
    return render_template('index.html', weather=weather, forecast=forecast, city=city)

if __name__ == '__main__':
    app.run(debug=True) 