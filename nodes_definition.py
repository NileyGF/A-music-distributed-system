"""Here goes the definions of the types of nodes and their role, according to the orientation.
An unique host can have more than one node, allowing it to have more than one role.
For instance, we must define a "data_base node", "order router"(presumibly the one waiting for orders to redirect them), 
and others.
"""
import database_controller
import socket
import pickle
import core
TAIL = '!END!'

class Router_node:
    def __init__(self, router_group_addr:str, reading_group_addr:str) -> None:
        self.providers_by_song = dict()  # update by time or by event
        self.songs_tags_list = list()     # update by time or by event

        self.__get_songs_tags_list()

    
    def __get_songs_tags_list(self):
        # fix to connect to a reader node and ask for it

        # change to conect to a reading node and ask for the list 
        self.songs_tags_list = database_controller.get_aviable_songs()
        return self.songs_tags_list
    
    def send_songs_tags_list(self,connection:socket.socket):
        data = database_controller.get_aviable_songs()
        h_d_t_list = tuple(["SSList",data,"!END!"])
        pickled_data = pickle.dumps(h_d_t_list)

        result = core.sender_3th(pickled_data,connection)
        print("Songs Tags Sended: ",result)
    
        


    headers = {'SSList':0, # Send Songs List 
               'RSList':send_songs_tags_list, # Request Songs List
               'Rsong': 0, # Request song
               'SPList':0, # Send Providers List
               'Rchunk':0, # Request chunk
               'Schunk':0, # Send chunk
               }
