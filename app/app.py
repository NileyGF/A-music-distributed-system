from tkinter import *
from tkinter import ttk
import os

class Form(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.config(bg = 'white')

        self.btn_download = None
        self.btn_play = None
        self.btn_load = None

        self.list_box = None

        self.set_size()
        self.create_widgets()


    def set_size(self, sheight:int = 610, swidth:int = 800):
        self.geometry(str(swidth) + 'x' + str(sheight))

    def create_widgets(self):
        self.btn_download = Button(self, text = 'Download', padx = 15, pady = 5, bg = 'gray')
        self.btn_download.grid(row = 4, column = 5)

        v_separator1 = Frame(self)
        v_separator1.grid(row = 4, column = 4)
        v_separator1.config(width = 20, height = 10, bg = 'white')
        
        self.btn_play = Button(self, text='Play', padx = 15, pady = 5, bg = 'gray')
        self.btn_play.grid(row = 4, column = 3)

        v_separator2 = Frame(self)
        v_separator2.grid(row = 4, column = 2)
        v_separator2.config(width = 220, height = 10, bg = 'white')

        self.btn_load = Button(self, text = 'Load', padx = 15, pady = 5, bg = 'gray')
        self.btn_load.grid(row = 4, column = 1)
        
        v_separator3 = Frame(self)
        v_separator3.grid(row = 0, column = 0)
        v_separator3.config(width = 100, height = 10, bg = 'white')

        self.list_box = Listbox(self, height = 35, width = 50, bg = 'gray')
        self.list_box.grid(row = 1, column = 1)

        box = Frame(self)
        box.grid(row = 1, column = 2)
        box.place(x = 410, y = 10)
        box.config(width = 220, height = 70, bg = 'gray')

        scroll =  ttk.Scrollbar(self.list_box, orient = VERTICAL)
        scroll.set(0.2, 0.5)
        scroll.place(x = 283, y = 0, height = 560)

        txt_entry = ttk.Entry(box)
        txt_entry.place(x = 10, y = 0, width = 200, height = 30)

        btn_filter = Button(box, text = 'Filter')
        btn_filter.place(x = 130, y = 35, width = 80, height = 30)

    def btn_download_config(self):
        pass
    
    def btn_play_config(self):
        pass

    def btn_load_config(self):
        pass

    def listbox_config(self):
        pass


if __name__ == '__main__':
    root = Form()
    root.wm_title('Music')

    root.mainloop()