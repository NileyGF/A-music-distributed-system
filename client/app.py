from flask import Flask, render_template, request
from pydub import AudioSegment
from pydub.playback import play
import math
import os
from flask_bootstrap import Bootstrap
import client_class
from multiprocessing import Process
from flask import jsonify
from werkzeug.utils import secure_filename

IMG_FOLDER=os.path.join('static','IMG')
app = Flask(__name__)
app.config['UPLOAD_FOLDER']=IMG_FOLDER
app.config['UPLOAD_SONG_FOLDER']="uploads"
Bootstrap(app)
ALLOWED_EXTENSIONS=set(["mp3"])
client=client_class.Client()
process=None 
def allowed_file(file):
    file=file.split('.')
    if file[1] in ALLOWED_EXTENSIONS:
        return True
    return False

songs= []
Flask_Logo=os.path.join(app.config['UPLOAD_FOLDER'],'logo.png')
@app.route('/')
def index():
    
    
    return render_template('index.html',user_image=Flask_Logo,songs=songs)
@app.route('/upload_song', methods=['GET','POST'])
def upload():
    # file=request.files["uploadFile"]
    # filename=secure_filename(file.filename)
    
    # print(filename)
    # #if file and allowed_file(filename):
    #     #client.upload_song(file)
    # return render_template('index.html',user_image=Flask_Logo,songs=songs)
    if request.method == 'POST':
        title = request.form['title']
        gender = request.form['gender']
        author = request.form['author']
        song_file = request.files['songfile']

        client.upload_song(song_file.read(),[title,author,gender])

        return render_template('index.html',user_image=Flask_Logo,songs=songs)
    else:
        return render_template('upload_song.html')

@app.route('/on_download_click', methods=['POST'])
def on_download_click():
        selected_song = request.json.get("selectedValues")
        selected_song = tuple(map(str, str(selected_song).split(', ')))
        duration_sec = int(selected_song[4]) / 1000 
        number_of_chunks:float = duration_sec / int("".join(filter(str.isdigit,selected_song[5])))
        number_of_chunks = math.ceil(number_of_chunks)
        download_song(int("".join(filter(str.isdigit, selected_song[0]))), number_of_chunks)
        return render_template('index.html',user_image=Flask_Logo,songs=songs)

@app.route('/on_play_click', methods=['POST'])    
def on_play_click():
        selected_song = request.json.get("selectedValues")
        
        selected_song = tuple(map(str, str(selected_song).split(', ')))
        duration_sec = int(selected_song[4]) / 1000 
        number_of_chunks:float = duration_sec / int("".join(filter(str.isdigit,selected_song[5])))
        number_of_chunks = math.ceil(number_of_chunks)
        play_song(int("".join(filter(str.isdigit, selected_song[0]))), number_of_chunks)
       
        return render_template('index.html',user_image=Flask_Logo,songs=songs)

@app.route('/on_stop_click', methods=['POST'])
def on_stop_click():
    global process
    if process is not None:
        process.terminate()
    return render_template('index.html',user_image=Flask_Logo,songs=songs)

@app.route('/on_load_click', methods=['POST'])
def on_load_click():
    global songs
    # self.list_box.delete(0,tk.END)
    client.refresh_song_list()
    song_list = client.song_list
    print(song_list)
    for i, sl in enumerate(song_list):
        songs.insert(i,sl)
    return render_template('index.html',user_image=Flask_Logo,songs=songs)
        
def play_song(song_id, number_of_chunks):
    global process
    for i in range(number_of_chunks):
        if i < 10:
            cs = '00'+ str(i)
        elif i < 100:
            cs = '0' + str(i)
        try: 
            print(song_id)
            print(cs)
            wave=AudioSegment.from_mp3(f'cache/{song_id}_dice_{cs}.mp3')
            process=Process(target=play, args=(wave,) )
        except:
            chunk = client.request_song_from(song_id, i*10*1000,number_of_chunks)
            wave=AudioSegment.from_mp3(f'cache/{song_id}_dice_{cs}.mp3')
            process=Process(target=play, args=(wave,) )
        process.start()
    
def download_song(song_id, number_of_chunks):
    for i in range(number_of_chunks):
        if i < 10:
            cs = '00'+ str(i)
        elif i < 100:
            cs = '0' + str(i)
        try: 
            wave=AudioSegment.from_mp3(f'cache/{song_id}_dice_{cs}.mp3')
        except:
            chunk = client.request_song_from(song_id, i*10*1000,number_of_chunks)
    

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True,port=5000)
 