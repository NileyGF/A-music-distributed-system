import sqlite3
import os
import shutil
from pydub import AudioSegment
from mutagen.mp3 import MP3  
from mutagen.easyid3 import EasyID3  
import glob 
import random
from pydub.utils import make_chunks

SPLIT_SIZE = 10

def create_db(data_base_file_path:str):
    """ Creates a sqlite database with especified name. The name should have a full existing path
    to where the database must be constructed, including the file name. The extension '.db' is not necessary
    
    Examples:

    'data/sqlite_database.db'

    'data/sqlite_database'

    'sqlite_database'
    """
    connection = None
    try:
        if data_base_file_path[len(data_base_file_path)-3:] != '.db':
            data_base_file_path += '.db'
        connection = sqlite3.connect(data_base_file_path)
        # cursor = connection.cursor()
        print("Database created and Successfully Connected to SQLite")

        # sqlite_select_Query = "select sqlite_version();"
        # cursor.execute(sqlite_select_Query)
        # record = cursor.fetchall()
        # print("SQLite Database Version is:", record)
        connection.commit()
        # cursor.close()

    except sqlite3.Error as error:
        print("Error while connecting to sqlite:", error)
    finally:
        if connection:
            connection.close()
            print("The SQLite connection is closed")

def create_table(data_base_file_path:str, table_name:str, columns_list:list):
    """Createss an sqlite table in the file especified and with the name especified in 'table_name'.
    If 'columns_list' has 0 elements the table won't be created.

    The format for columns_list is:

    A list of strings where every string is 'column_name type_in_sqlite rest_of_params_to espicify_separated_by_spaces'
    
    Example:
            [
            'id_S INTEGER PRIMARY KEY',
            'title TEXT NOT NULL',
            'artists TEXT NOT NULL',
            'genre TEXT NOT NULL'
            ]
    """
    connection = None
    if len(columns_list) == 0:
        return False
    try:
        connection = sqlite3.connect(data_base_file_path)
        create_table_query = "CREATE TABLE if not exists " + table_name + ' ( ' 
        for i in range(len(columns_list)):
            column = columns_list[i]
            create_table_query = create_table_query + column
            if i != len(columns_list) -1:
                create_table_query = create_table_query + ', '
        create_table_query = create_table_query + ');'

        cursor = connection.cursor()
        print("Successfully Connected to SQLite")
        cursor.execute(create_table_query)
        connection.commit()
        print(f"table {table_name} in database OK")
        cursor.close()

    except sqlite3.Error as error:
        print("Error while creating a sqlite table:", error)
    finally:
        if connection:
            connection.close()
            print("sqlite connection is closed")

def insert_rows(data_base_file_path:str,table_name:str,columns_names:str,row_tuples_tuple:tuple):
    """ Insert one or more rows in the specified table, of the specified database.
    'columns_names' is a string of the name of the columns in the table, comma separated.
    'row_tuples_tuple' is a tuple with one or more elements, where each element is a tuple 
    with the values to insert to the row. Must be ordered in the same fashion as 'colummns_names'.

    Example:

        data_base_file_path = 'spotify_db.db'

        table_name = 'songs'

        columns = 'id_S, title, artists, genre'

        rows = ((0, 'This Is Halloween', 'Marilyn Manson', 'Soundtrack'),

                (6, 'Extraordinary Girl', 'Green Day', 'Punk Rock'),

                (11, 'House of the Rising Sun', 'Five Finger Death Punch', 'Rock'))

        insert_rows(data_base_file_path, table_name, columns, rows)
    """
    if len(row_tuples_tuple) == 0:
        return False

    try:
        connection = sqlite3.connect(data_base_file_path)
        cursor = connection.cursor()
        print("Connected to SQLite")

        sqlite_query = "INSERT OR REPLACE INTO " + table_name + " ( " + columns_names + " ) VALUES "
        # for row in row_tuples_tuple:
        value = '(' + ('?,'*(len(row_tuples_tuple[0])-1)) + '?);'
        insert = sqlite_query + value
        cursor.executemany(insert,row_tuples_tuple)        
        connection.commit()
        print("Values inserted successfully into the table")
        cursor.close()
 
    except sqlite3.Error as error:
        print("Failed to insert data into sqlite table:",error)
    finally:
        if connection:
            connection.close()
            print("The sqlite connection is closed")

def read_data(data_base_file_path:str, query:str="SELECT * from songs"):
    """ Given the path of the database file and a sqlite query, returns all rows corresponding to the query
        
        Examples:
                
                # get all data from 'songs' table:
                
                song_list = read_data('spotify_db.db', "SELECT * from songs")s
                
                
                # get a chunk of song which id is '11_dice_003' :
                
                query = "SELECT * from chunks where id_Chunk = '11_dice_003'"
                
                chunk = read_data('spotify_db.db', query)
    """
    try:
        connection = sqlite3.connect(data_base_file_path)
        cursor = connection.cursor()
        print("Connected to SQLite")

        cursor.execute(query)
        record = cursor.fetchall()
        cursor.close()
        return record
 
    except sqlite3.Error as error:
        print("Failed to read data from sqlite table:", error)
    finally:
        if connection:
            connection.close()
            print("sqlite connection is closed")


def get_song_tags(file_path:str):
    """ Given an .mp3 file path tries to get 'artist', 'title', 'genre' and 'duration' tags.
        If the .mp3 file does not have all the tags, it will be returned 'Unknown'

        Returns 4 strings values, one for each tag.

        return title, artist, genre, duration
    """
    

    filez = glob.glob(file_path) 
    audiofile = MP3(filez[0], ID3=EasyID3) 
   
    duration = int(audiofile.info.length*1000)
    
    try:
        authors = audiofile['artist'][0]
    except:
        authors = 'Unknown artist'
    try:
        title =  audiofile['title'][0]
    except:
        title = 'Unknown title'
    try:
        genre =  audiofile['genre'][0]
    except:
        genre = 'Unknown genre'
    
    return title, authors, genre, duration


def Create_Songs_Chunks_tables(data_base_file_path:str='spotify_db.db'):
    """ Create the tables for songs and chunks in the specified sqlite database file"""
    Song_table = ['id_S INTEGER PRIMARY KEY',
                  'title TEXT NOT NULL',
                  'artists TEXT NOT NULL',
                  'genre TEXT NOT NULL',
                  'duration_ms INTEGER NOT NULL',
                  'chunk_slice INTEGER NOT NULL'
                ]

    Chunk_table = ['id_Chunk TEXT PRIMARY KEY',
                   'chunk BLOB NOT NULL',
                   'id_S INTEGER NOT NULL',
                   'FOREIGN KEY (id_S) REFERENCES songs (id_S) '
              ]           

    create_table(data_base_file_path, 'songs', Song_table)
    create_table(data_base_file_path, 'chunks', Chunk_table) 

def Insert_songs(songs_list:list,data_base_file_path:str='spotify_db.db'):
    """ Given a list of .mp3 files paths, and a sqlite database file:
        Get the tags of each file and introduce it to the 'songs' table.
        Also split the song in chunks with the same size, except perhaps, the last one.
        These chunks are stored in the 'chunks' table. 
    """
    next_id = -1
    try:
        connection = sqlite3.connect(data_base_file_path)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM songs ORDER BY id_S DESC LIMIT 1")
        result = cursor.fetchall()
        if result != None and len(result) > 0:
            print('last rowid',result)
            next_id = result[0][0] + 1
        cursor.close()
    except sqlite3.Error as error:
        print(f"Failed to get last rowid in sqlite table {error}")
    if connection:
        connection.close()
        print("The sqlite connection is closed")
    
    if next_id < 0:
        next_id = 0
    list_tags = []
    for i in range(len(songs_list)):
        title, authors, genre, duration = get_song_tags(songs_list[i])
        list_tags.append((next_id,title,authors,genre,duration, SPLIT_SIZE))
        next_id += 1
    tuple_tags = tuple(list_tags)
    # remove the songs that are already in the table
    tuple_tags,songs_list = not_in_db(data_base_file_path, tuple_tags,songs_list)
    print('inserting ',tuple_tags)
    tuple_chunks = split_songs(songs_list,tuple_tags,True)
    insert_rows(data_base_file_path, 'songs', 'id_S, title, artists, genre, duration_ms, chunk_slice', tuple_tags)
    insert_rows(data_base_file_path, 'chunks', 'id_Chunk, chunk, id_S', tuple_chunks)

def split_songs(songs_list:list, songs_tags:list, reesplit:bool = True):
    """ Given a list of .mp3 files paths, and for each song, it's tags (id_S,title,artist,genre);
        for every song, split it in SPLIT_SIZE seconds pieces, and for each piece make a tuple (id_chunk, chunk, id_S),
        that belongs in the returned tuple of tuples.
    """
    if not os.path.exists('chunk'):
            os.makedirs('chunk')

    if reesplit:        
        chunks = []
        for i in range(len(songs_list)):
            path = songs_list[i]
            song = AudioSegment.from_mp3(path)
            song_diced = make_chunks(song, 1000 * SPLIT_SIZE)
            c = 0
            for chunk in song_diced:
                id_S = songs_tags[i][0]
                if c < 10:
                    cs = '00'+ str(c)
                elif c < 100:
                    cs = '0' + str(c)
                id_chunk = str(id_S) + '_dice_' + cs
                c+=1
                chunk.export("chunk/"+id_chunk+".mp3", format='mp3')
                with open("chunk/"+id_chunk+".mp3", 'rb') as file:
                    chunk = file.read()
                chunks.append((id_chunk, chunk, id_S))
                os.remove("chunk/"+id_chunk+".mp3")
    else:
        chunks = []
        chunks_paths = songs_list_from_directory('chunk')
        for chunk_f in chunks_paths:
            # song = AudioSegment.from_mp3(chunk_f)
            with open(chunk_f, 'rb') as file:
                song = file.read()
            id_chunk:str = chunk_f [6:-4]
            id_S = int(id_chunk.split('_')[0])
            chunks.append((id_chunk, song, id_S))

    return tuple(chunks)

def songs_list_from_directory(dir_path:str):
    """ Given a directory(folder), get all files paths from it (ignoring folder in directory)"""
    songs_list = []
    for path in os.listdir(dir_path):
        # check if current path is a file
        if os.path.isfile(os.path.join(dir_path, path)):
            songs_list.append(os.path.join(dir_path, path))
    return songs_list

def not_in_db(data_base_file_path, tuple_tags,songs_list):
    result = []
    songs = []
    for i in range(len(tuple_tags)):
        s = tuple_tags[i]
        query = f"SELECT * FROM songs WHERE title = \"{s[1]}\" AND artists = \"{s[2]}\" "
        s_list = read_data(data_base_file_path, query)
        if s_list != None and len(s_list) > 0:
            print(f"Repeated insertion {s} ignored.")
            continue
        result.append(s)
        songs.append(songs_list[i])
    return tuple(result), songs

def insert_song_from_bytes(song, tags, data_base_file_path:str='spotify_db.db'):
    temp_f = 'songs/temp'+ str(random.randint(1000,9999)) + '.mp3'
    with open(temp_f,'wb') as f:
        f.write(song)
    auto_tags = get_song_tags(temp_f)
    if tags != None and len(tags) == 3:
        for i,t in enumerate(auto_tags):
            try:
                if 'Unknown' in t and tags[i] != None:
                    auto_tags[i] = tags[i]
            except: pass
    Insert_songs([temp_f],data_base_file_path)
    # os.remove(temp_f)

def insert_rows_into_songs(songs_tags_list:list,data_base_file_path:str='spotify_db.db'):
    tuple_tags = tuple(songs_tags_list)
    insert_rows(data_base_file_path, 'songs', 'id_S, title, artists, genre, duration_ms, chunk_slice', tuple_tags)
    
def insert_rows_into_chunks(chunks_list:list,data_base_file_path:str='spotify_db.db'):
    tuple_chunks = tuple(chunks_list)
    insert_rows(data_base_file_path, 'chunks', 'id_Chunk, chunk, id_S', tuple_chunks)

def get_a_chunk(start_time_ms:int, id_S:int,data_base_file_path:str='spotify_db.db'):
    """ Returns the chunk containing start_time_ms millisecond of the song with id = id_S"""
    c = int((start_time_ms / 1000) // 10)
    if c < 10:
        cs = '00'+ str(c)
    elif c < 100:
        cs = '0' + str(c)
    id_chunk = str(id_S) + '_dice_' + cs

    query = "SELECT * from chunks where id_Chunk = '" + id_chunk + "'"

    chunk = read_data(data_base_file_path,query)
    if isinstance(chunk,list):
        if len(chunk) > 0:
            chunk = chunk[0]   
    chunk = chunk[1]
    # sound = AudioSegment.from_mp3(io.BytesIO(chunk))

    return chunk
    
def get_n_chunks(start_time_ms:int, id_S:int, n:int,data_base_file_path:str='spotify_db.db'):
    """ Returns n chunks, beginning in the one containing start_time_ms millisecond of the song with id = id_S"""
    ids = []
    audios = []
    st = start_time_ms
    for i in range(n):
        c = int((st/ 1000) // SPLIT_SIZE)
        st = c*SPLIT_SIZE * 1000 + SPLIT_SIZE * 1000
        if c < 10:
            cs = '00'+ str(c)
        elif c < 100:
            cs = '0' + str(c)
        id_chunk = str(id_S) + '_dice_' + cs
        ids.append(id_chunk)
        query = "SELECT * from chunks where id_Chunk = '" + id_chunk + "'"

        chunk = read_data(data_base_file_path,query)
        if isinstance(chunk,list):
            if len(chunk) > 0:
                chunk = chunk[0]   
        chunk = chunk[1]
        # sound = AudioSegment.from_mp3(io.BytesIO(chunk))
        audios.append(chunk)
    return audios

def get_aviable_songs(data_base_file_path:str='spotify_db.db'):
    """ List all songs' tags  in the specified database"""
    s_list = read_data(data_base_file_path, "SELECT * from songs")
    return s_list

def get_chunks_rows_for_song(id_S:int,data_base_file_path:str='spotify_db.db') -> list:
    query = "SELECT * from chunks where id_S = " + str(id_S)

    chunks_row = read_data(data_base_file_path,query)

    return chunks_row
# shutil.rmtree('/home/akeso/Documents/VSCode/A-music-distributed-system/server/chunk')
# os.listdir('/home/akeso/Documents/VSCode/database_all/03 A Reason to Fight.mp3')

# db = '/home/akeso/Documents/VSCode/A-music-distributed-system/server/data_nodes/spotify_53.db'
# song_to_add = "/home/akeso/Documents/VSCode/A-music-distributed-system/client/database_all/11 - Lonely Day.mp3"
# with open(song_to_add,'rb') as f:
#     song_bytes = f.read()
# insert_song_from_bytes(song_bytes,[None,None,None],db)