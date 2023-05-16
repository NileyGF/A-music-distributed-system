import sqlite3
import os
from pydub import AudioSegment
import io

SPLIT_SIZE = 10

def create_db(data_base_file_path:str):
    """ Creates a sqlite database with especified name. The name should have a full existing path
    to where the DB must be constructed, and the name as well
    Examples:
    'data/sqlite_database.db'
    'data/sqlite_database'
    'sqlite_database'
    """
    try:
        if data_base_file_path[len(data_base_file_path)-3:] != '.db':
            data_base_file_path += '.db'
        connection = sqlite3.connect(data_base_file_path)
        cursor = connection.cursor()
        print("Database created and Successfully Connected to SQLite")

        sqlite_select_Query = "select sqlite_version();"
        cursor.execute(sqlite_select_Query)
        record = cursor.fetchall()
        print("SQLite Database Version is:", record)
        connection.commit()
        cursor.close()

    except sqlite3.Error as error:
        print("Error while connecting to sqlite:", error)
    finally:
        if connection:
            connection.close()
            print("The SQLite connection is closed")

def create_table(data_base_file_path:str,table_name:str,columns_list:list):
    """Create an sqlite table in the file especified and with the name especified.
    If columns_list has 0 elements the table won't be created.
    The format for columns_list is:
    a list of strings where every string is 'column_name type_in_sqlite rest_of_params_to espicify_separated_by_spaces'
    Example:
        [
        'id INTEGER PRIMARY KEY',
        'title TEXT NOT NULL',
        'authors TEXT NOT NULL',
        'genre TEXT NOT NULL'
        ]
    """
    try:
        connection = sqlite3.connect(data_base_file_path)
        create_table_query = "CREATE TABLE " + table_name + ' ( ' 
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
        print("SQLite table created")

        cursor.close()

    except sqlite3.Error as error:
        print("Error while creating a sqlite table:", error)
    finally:
        if connection:
            connection.close()
            print("sqlite connection is closed")

def insert_rows(data_base_file_path:str,table_name:str,columns_names:str,row_tuples_tuple:tuple):
    """ Insert one or more rows in the especified table, of the especfied database.
    columns_names is a string of the columns in the table, comma separated
    row_tuples_tuple is a tuple with one or more elements, where each element is a tuple 
    with the values to insert to the row. Must be ordered in the same fashion as colummns_names
    Example:

    """
    if len(row_tuples_tuple) == 0:
        return False

    try:
        connection = sqlite3.connect(data_base_file_path)
        cursor = connection.cursor()
        print("Connected to SQLite")

        sqlite_query = "INSERT INTO " + table_name + " ( " + columns_names + " ) VALUES "
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
    from mutagen.mp3 import MP3  
    from mutagen.easyid3 import EasyID3  
    import glob 
    filez = glob.glob(file_path) 
    audiofile = MP3(filez[0], ID3=EasyID3) 
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
    
    return title, authors, genre

def file_to_binary(file_path:str):
    '''Convert data to binary format'''
    with open(file_path, 'rb') as file:
        blob_data = file.read()
    return blob_data

def Create_Songs_Chunks_tables(data_base_file_path:str='spotify_db.db'):

    Song_table = ['id_S INTEGER PRIMARY KEY',
                  'title TEXT NOT NULL',
                  'artists TEXT NOT NULL',
                  'genre TEXT NOT NULL'
              ]

    Chunk_table = ['id_Chunk TEXT PRIMARY KEY',
                   'chunk BLOB NOT NULL',
                   'id_S INTEGER NOT NULL',
                   'FOREIGN KEY (id_S) REFERENCES songs (id_S) '
              ]           

    create_table(data_base_file_path, 'songs', Song_table)
    create_table(data_base_file_path, 'chunks', Chunk_table) 

def Insert_songs(songs_list:list,data_base_file_path:str='spotify_db.db'):
    next_id = -1
    try:
        connection = sqlite3.connect(data_base_file_path)
        cursor = connection.cursor()
        if cursor.lastrowid:
            next_id = cursor.lastrowid + 1
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
        title, authors, genre = get_song_tags(songs_list[i])
        list_tags.append((next_id,title,authors,genre))
        next_id += 1
    tuple_tags = tuple(list_tags)
    tuple_chunks = split_songs(songs_list,list_tags,False)
    insert_rows(data_base_file_path, 'songs', 'id_S, title, artists, genre', tuple_tags)
    insert_rows(data_base_file_path, 'chunks', 'id_Chunk, chunk, id_S', tuple_chunks)

def split_songs(songs_list:list, songs_tags:list, reesplit:bool = False):
    
    if reesplit:
        from pydub.utils import make_chunks
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
    songs_list = []
    for path in os.listdir(dir_path):
        # check if current path is a file
        if os.path.isfile(os.path.join(dir_path, path)):
            songs_list.append(os.path.join(dir_path, path))
    return songs_list

def get_a_chunk(start_time_ms:int, id_S:int ):
    c = int((start_time_ms / 1000) // 10)
    if c < 10:
        cs = '00'+ str(c)
    elif c < 100:
        cs = '0' + str(c)
    id_chunk = str(id_S) + '_dice_' + cs

    query = "SELECT * from chunks where id_Chunk = '" + id_chunk + "'"

    chunk = read_data('spotify_db.db',query)
    if isinstance(chunk,list):
        if len(chunk) > 0:
            chunk = chunk[0]   
    chunk = chunk[1]
    sound = AudioSegment.from_mp3(io.BytesIO(chunk))

    return sound
    

def get_n_chunks(start_time_ms:int, id_S:int, n:int):
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

        chunk = read_data('spotify_db.db',query)
        if isinstance(chunk,list):
            if len(chunk) > 0:
                chunk = chunk[0]   
        chunk = chunk[1]
        sound = AudioSegment.from_mp3(io.BytesIO(chunk))
        audios.append(sound)
    return audios


# Use cursor.fetchall() or fetchone() or fetchmany() to read query result.

create_db('spotify_db.db')
Create_Songs_Chunks_tables()
songs_list = songs_list_from_directory('songs')
Insert_songs(songs_list)
chunk = get_a_chunk(22000,11)
chunk.export("from_db/11_dice_002.mp3", format='mp3')

chunks = get_n_chunks(32000,11,6)
for i in range(6):
    chunks[i].export("from_db/11_dice_00"+str(i+3)+".mp3", format='mp3')

