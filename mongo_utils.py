from pymongo import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash

# Cambia la URI según tu configuración de MongoDB
DB_NAME = 'Recomendaciones'
COLLECTION = 'usuarios'

DB_peliculas = 'Recomendaciones'
COLLECTION_peliculas = 'movie_data'


uri = "mongodb+srv://AlumnoLinkia:holi1234@sistemarecomendacion.wqyrle5.mongodb.net/?retryWrites=true&w=majority&appName=SistemaRecomendacion"

client = MongoClient(uri, server_api=ServerApi('1'))
db = client[DB_NAME]
usuarios_col = db[COLLECTION]

def insertar_usuario(numero, contrasena):
    # Guarda la contraseña hasheada por seguridad
    usuario = {
        'numero': str(numero),
        'contrasena': generate_password_hash(contrasena)
    }
    usuarios_col.insert_one(usuario)
    return usuario

def buscar_usuario(numero):
    return usuarios_col.find_one({'numero': numero})

def verificar_contrasena(usuario, contrasena):
    if not usuario:
        return False
    return check_password_hash(usuario['contrasena'], contrasena)