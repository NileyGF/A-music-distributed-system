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
    def __init__(self) -> None:
        self.providers_by_song = dict()  # update by time or by event
        self.songs_tags_list = list()     # update by time or by event

    
    def __get_songs_tags_list(self):
        # fix to connect to a reader node and ask for it
        self.songs_tags_list = database_controller.get_aviable_songs()
        return self.songs_tags_list
    
    def send_songs_tags_list(self,connection:socket.socket):
        header = pickle.dumps('SSList')
        data = self.__get_songs_tags_list()
        tail = pickle.dumps(TAIL)
        pickled_data = pickle.dumps(data)
        result = core.send_data_to((header,pickled_data,tail),connection,True)
        print(result)
        # connection.send(header)
        
        # i = 0
        # connection.send(pickled_data)
        # # while (i <= len(pickled_data)-1):
        # #     line = pickled_data[i:min(i+1024, len(pickled_data)-1)]
        # #     i += 1025
        # #     connection.send(line)
        # connection.send(tail)
    
        


    headers = {'SSList':0, # Send Songs List 
               'RSList':send_songs_tags_list, # Request Songs List
               'Rsong': 0, # Request song
               'SPList':0, # Send Providers List
               'Rchunk':0, # Request chunk
               'Schunk':0, # Send chunk
               }
