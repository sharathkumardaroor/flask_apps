from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nickname = request.form['nickname']
        room = request.form['room']
        if not nickname or not room:
            return render_template('index.html', error='Nickname and room are required.')
        session['nickname'] = nickname
        session['room'] = room
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/chat')
def chat():
    if 'nickname' not in session or 'room' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', nickname=session['nickname'], room=session['room'])

@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)
    send({'msg': f"{data['nickname']} has joined the room."}, room=room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    msg = data['msg']
    nickname = data['nickname']
    send({'msg': f"{nickname}: {msg}"}, room=room)

@socketio.on('leave')
def handle_leave(data):
    room = data['room']
    leave_room(room)
    send({'msg': f"{data['nickname']} has left the room."}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True) 