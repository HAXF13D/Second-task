from flask import Flask, jsonify, request, send_file
from flask_sqlalchemy import SQLAlchemy
from pydub import AudioSegment
from credits import USER_NAME, PASSWORD, DB_NAME
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{USER_NAME}:{PASSWORD}@localhost/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    access_token = db.Column(db.String(100), nullable=False)

    def __init__(self, name, access_token):
        self.name = name
        self.access_token = access_token


class AudioRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    audio_url = db.Column(db.String(200), nullable=False)

    def __init__(self, user_id, audio_url):
        self.user_id = user_id
        self.audio_url = audio_url


@app.route('/users', methods=['POST'])
def create_user():
    name = request.json.get('name')
    if name is None:
        return jsonify({'error': 'Missing name parameter'}), 400

    access_token = str(uuid.uuid4())
    user = User(name=name, access_token=access_token)
    db.session.add(user)
    db.session.commit()

    return jsonify({'user_id': user.id, 'access_token': user.access_token})


@app.route('/records', methods=['POST'])
def add_audio_record():
    user_id = request.json.get('user_id')
    access_token = request.json.get('access_token')
    audio_data = request.files.get('audio_data')

    if user_id is None or access_token is None or audio_data is None:
        return jsonify({'error': 'Missing parameters'}), 400

    user = User.query.get(user_id)
    if user is None or user.access_token != access_token:
        return jsonify({'error': 'Invalid user credentials'}), 401

    audio_id = str(uuid.uuid4())
    audio_filename = f'{audio_id}.mp3'
    audio_path = f'./audio_files/{audio_filename}'
    audio_data.save(audio_path)

    audio = AudioSegment.from_file(audio_path, format='wav')
    audio.export(audio_path, format='mp3')

    audio_record = AudioRecord(user_id=user.id, audio_url=audio_filename)
    db.session.add(audio_record)
    db.session.commit()

    return jsonify({'url': f'http://host:port/record?id={audio_id}&user={user.id}'})


@app.route('/record', methods=['GET'])
def get_audio_record():
    audio_id = request.args.get('id')
    user_id = request.args.get('user')

    if audio_id is None or user_id is None:
        return jsonify({'error': 'Missing parameters'}), 400

    audio_record = AudioRecord.query.get(audio_id)
    if audio_record is None or audio_record.user_id != user_id:
        return jsonify({'error': 'Invalid audio record or user'}), 404

    audio_path = f'./audio_files/{audio_record.audio_url}'

    return send_file(audio_path, mimetype='audio/mp3')


if __name__ == '__main__':
    app.run(debug=True)
