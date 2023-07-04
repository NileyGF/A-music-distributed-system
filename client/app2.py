from flask import Flask, render_template, request
from pydub import AudioSegment
from pydub.playback import play
import math
import os
import client_class
from multiprocessing import Process
from flask import jsonify

IMG_FOLDER=os.path.join('static','IMG')
app = Flask(__name__)
app.config['UPLOAD_FOLDER']=IMG_FOLDER
client=client_class.Client()
process=None

@app.route('/')
def index():
    Flask_Logo=os.path.join(app.config['UPLOAD_FOLDER'],'logo.png')
    songs= []
    return render_template('index.html',user_image=Flask_Logo,songs=songs)

@app.route('/on_download_click', methods=['POST'])
def on_download_click():
        # selected_song = list_box.curselection()
        # duration_sec = selected_song[4] / 1000 
        # number_of_chunks:float = duration_sec / selected_song[5]
        # number_of_chunks = math.ceil(number_of_chunks)
        # download_song(selected_song[0], number_of_chunks)
        return

@app.route('/on_play_click', methods=['POST'])    
def on_play_click():
        # selected_song = list_box.curselection()
        # duration_sec = selected_song[4] / 1000 
        # number_of_chunks:float = duration_sec / selected_song[5]
        # number_of_chunks = math.ceil(number_of_chunks)
        # play_song(selected_song[0], number_of_chunks)
        play_song()
        return

@app.route('/on_stop_click', methods=['POST'])
def on_stop_click():
        process.terminate()

@app.route('/on_load_click', methods=['POST'])
def on_load_click():
        # self.list_box.delete(0,tk.END)
        client.refresh_song_list()
        song_list = client.song_list
        songs=[]
        for i, sl in enumerate(song_list):
            songs.insert(i,sl)
        return jsonify(songs=songs)
        
# def play_song(song_id, number_of_chunks):
def play_song():
    wave=None
    # for i in range(number_of_chunks):
    #     if i < 10:
    #         cs = '00'+ str(i)
    #     elif i < 100:
    #         cs = '0' + str(i)
    #     try: 
    #         wave=AudioSegment.from_file(f'{song_id}_dice_{cs}.mp3')
    #         process=Process(target=play, args=wave, )
    #     except:
    #         chunk = client.request_song_from(song_id, i*10*1000)
    #         wave=AudioSegment.from_file(f'{song_id}_dice_{cs}.mp3')
    #         process=Process(target=play, args=wave, )
    #     process.start()
    wave=AudioSegment.from_file('/Users/josue/Documents/Ciencias_de_la_Computación/4to/Distributed_Spotify/SD_Spotify_Niley_Josue/A-music-distributed-system/client/cache/Impulso.mp3')
    process=Process(target=play, args=wave, )
    process.start()
    return
    # Puedes agregar un bucle para detener la reproducción después de un tiempo específico
    # while pygame.mixer.music.get_busy():
    #     time.sleep(1)
    
    
def download_song(song_id, number_of_chunks):
    if not client.request_song(song_id, number_of_chunks):
        # messagebox.showerror('Error', 'No se pudo descargar la canción')
        return
    

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True,port=8000)