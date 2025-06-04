from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

# Cambia la URI según tu configuración de MongoDB
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'recomendador'
COLLECTION = 'usuarios'

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
usuarios_col = db[COLLECTION]

def insertar_usuario(numero, contrasena):
    # Guarda la contraseña hasheada por seguridad
    usuario = {
        'numero': numero,
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
