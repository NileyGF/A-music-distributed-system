from customtkinter import CTk, CTkFrame, CTkEntry, CTkButton, CTkCheckBox,CTkLabel

import tkinter as tk
from tkinter import *
import tkinter.ttk as ttk
import os
import requests
import json
import pygame

class ScrolledListbox(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent)
        self.listbox = tk.Listbox(self, *args, **kwargs)
        self.listbox_scrollbar = tk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=self.listbox_scrollbar.set)
        self.listbox_scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind('<Enter>', self.enter)
        self.listbox.bind('<Leave>', self.leave)
        self.listvariable(kwargs.get('listvariable',None))
        

    def configure(self, **kwargs):
        self.listvariable(kwargs.get('listvariable',None))
        self.setbackground(kwargs.get('bg',None))
        self.setforeground(kwargs.get('fg',None))
        self.sethighlight(kwargs.get('highlightcolor',None))
        self.setselectbackground(kwargs.get('selectbackground',None))
        self.setexportselection(kwargs.get('exportselection',1))
        

    def listvariable(self, item_list):
        if item_list != None:
            for item in item_list:
                self.listbox.insert(tk.END, item)

    def setexportselection(self, exportselection):
        self.listbox.configure(exportselection = exportselection)

    def setbackground(self, bg):
        if bg != None:
            self.listbox.configure(bg = bg)
        
    def setforeground(self, fg):
        if fg != None:
            self.listbox.configure(fg = fg)
            
    def sethighlight(self, highlightcolor):
        if highlightcolor != None:
            self.listbox.configure(highlightcolor = highlightcolor)

    def setselectbackground(self, selectbackground):
        if selectbackground != None:
            self.listbox.configure(selectbackground = selectbackground)

    def enter(self, event):
        self.listbox.config(cursor="hand2")

    def leave(self, event):
        self.listbox.config(cursor="")

    def insert(self, location, item):
        self.listbox.insert(location, item)

    def curselection(self):
        return self.listbox.curselection()
        
    def delete(self, first, last=None):
        self.listbox.delete(first, last)

    def delete_selected(self):
        selected_item = self.listbox.curselection()
        idx_count = 0
        for item in selected_item:
            self.listbox.delete(item - idx_count)
            idx_count += 1

    def delete_unselected(self):
        selected_item = self.listbox.curselection()
        idx_count = 0
        for i, listbox_entry in enumerate(self.listbox.get(0, tk.END)):
            if not listbox_entry in selected_item:
                self.listbox.delete(i - idx_count)
                idx_count += 1

class Form(CTk):
    
    def __init__(self):
        CTk.__init__(self)
        
        self.purple='#7f5af0'
        self.green='#2cb67d'
        self.black='#010101'
        self.white='#ffffff'
        self.config(bg='white')
        
        frame=CTkFrame(self,fg_color=self.white)
        frame.grid(column=0,row=0,sticky='nsew',padx=50,pady=50)

        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        
        frame.columnconfigure([0,1],weight=1)
        frame.rowconfigure([0,1,2,3,4,5],weight=1)
            
        logo=PhotoImage(file='/Users/josue/Downloads/Dist/d_system/A-music-distributed-system/app/images/logo.png')
        
        CTkLabel(self,image=logo,text="").grid(columnspan=2,row=0,column=0,padx=12,pady=10,sticky='N')
    
    # root.call('wm','iconphoto',root._w,logo)

        self.btn_download = None
        self.btn_play = None
        self.btn_stop=None
        self.btn_load = None

        self.list_box = None
        
        self.set_size(frame)
        
        self.create_widgets(frame)
        
        self.set_widgets_actions()

    def set_size(frame, sheight: int = 610, swidth: int = 800):
        frame.geometry('500x600+350+20')
        frame.minsize(650,700)
    
        # self.list_box.grid(row = 1, column = 1)
        # self.search_box.place(x = 10, y = 0, width = 200, height = 30)

    
    def create_widgets(self, frame):
        # Botón para cargar una canción
        self.btn_load = CTkButton(frame, border_color=self.green, fg_color=self.black, hover_color=self.green, corner_radius=12, border_width=2, text='Cargar', height=40)
        self.btn_load.grid(columnspan=2, row=4, pady=4, padx=4, sticky="s")
    
        # Listbox para mostrar las canciones disponibles
        self.list_box = ScrolledListbox(frame, selectmode=MULTIPLE)
        self.list_box.grid(columnspan=2, row=2, padx=4, pady=4, sticky="nsew")
    
        # Cuadro de texto para buscar canciones
        self.search_box = CTkEntry(frame, placeholder_text='Escriba el nombre de la canción que desea', border_color=self.black, fg_color=self.white, width=1000, height=40)
        self.search_box.grid(columnspan=2, row=3, sticky="s")
    
        # Frame para los botones de descarga, reproducción y parada
        button_frame = CTkFrame(frame, bg_color=self.white)
        button_frame.grid(columnspan=2, row=6, pady=4, padx=4, sticky="s")
    
        # Botón para descargar una canción
        self.btn_download = CTkButton(button_frame, border_color=self.green, fg_color=self.black, hover_color=self.green, corner_radius=12, border_width=2, text='Descargar', height=40)
        self.btn_download.pack(side="left", padx=4, pady=4)
    
        # Botón para reproducir una canción
        self.btn_play = CTkButton(button_frame, border_color=self.green, fg_color=self.black, hover_color=self.green, corner_radius=12, border_width=2, text='Reproducir', height=40)
        self.btn_play.pack(side="left", padx=4, pady=4)
    
        # Botón para parar una canción
        self.btn_stop = CTkButton(button_frame, border_color=self.green, fg_color=self.black, hover_color=self.green, corner_radius=12, border_width=2, text='Parar', height=40)
        self.btn_stop.pack(side="left", padx=4, pady=4)
    
        # Configuración de la fila y la columna central
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(2, weight=1)
    
        # # Configuración de la ventana principal
        # self.pack(fill="both", expand=True)
   
    def set_widgets_actions(self):
        self.btn_download  # Acción para descargar una canción
        self.btn_play       # Acción para reproducir una canción
        self.btn_load       # Acción para cargar una canción

        self.list_box.bind('<<ListboxSelect>>', self.on_listbox_select)
        self.btn_download.bind('<Button>', self.on_download_click)
        self.btn_play.bind('<Button>', self.on_play_click)

    def on_listbox_select(self, event):
        song_id = self.list_box.item[0, 'song_id']
        self.play_song(song_id)
    
    def on_download_click(self, event):
        song_id = self.list_box.item[0, 'song_id']
        self.download_song(song_id)
    
    def on_play_click(self, event):
        song_id = self.list_box.item[0, 'song_id']
        self.play_song(song_id)
    
    def search_songs(query):
        response = requests.get(f'http://localhost:3001/api/search?q={query}') #que tenga como entrada el ip.... NILEY
        return response.json()
    
    
    
    def play_song(song_id):
        # Reemplaza 'song_id' con el ID de la canción que deseas reproducir
        song_id = 1
    
        pygame.mixer.init()
        pygame.mixer.music.load('ruta/al/archivo/de/la/cancion.mp3')
        pygame.mixer.music.play()
    
        # Puedes agregar un bucle para detener la reproducción después de un tiempo específico
        # while pygame.mixer.music.get_busy():
        #     time.sleep(1)
        
    def get_song_info(song_id):
        response = requests.get(f'http://localhost:3001/api/songs/{song_id}')
        return response.json()
    
    def download_song(song_id):
        song_info = self.get_song_info(song_id)
        song_url = song_info['url']
    
        if song_url:
            response = requests.get(song_url)
            with open(f'{song_id}.mp3', 'wb') as f:
                f.write(response.content)
            print(f'Cancion {song_id} descargada y guardada en {song_id}.mp3')
        else:
            print(f'No se encontró la URL de la cancion {song_id}')
    



if __name__ == '__main__':
    # root = Form()
    # root.wm_title('Music')
    
    root=Form()
    
    root.title('Distributed Spotify')

    root.mainloop()
