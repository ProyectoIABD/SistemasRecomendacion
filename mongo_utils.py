from pymongo import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash

# Cambia la URI según tu configuración de MongoDB
DB_NAME = 'Recomendaciones'
COLLECTION = 'usuarios'
COLLECTION_peliculas = 'peliculas'


uri = "mongodb+srv://AlumnoLinkia:holi1234@sistemarecomendacion.wqyrle5.mongodb.net/?retryWrites=true&w=majority&appName=SistemaRecomendacion"

client = MongoClient(uri, server_api=ServerApi('1'))
db = client[DB_NAME]
usuarios_col = db[COLLECTION]
peliculas_col = db[COLLECTION_peliculas]

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

def get_peliculas():
    return list(peliculas_col.find())

def get_peliculas_vistas(userId):
    return usuarios_col.find_one({'numero': userId}).get('peliculas', [])

def anhadir_pelicula_vista(userId, movieId, rating):
    try:
        catalogo_peliculas = get_peliculas()
        usuario = usuarios_col.find_one({'numero': str(userId)})
        if not usuario:
            return False  # Usuario no existe

        # Buscar la película en el catálogo
        pelicula_info = next((p for p in catalogo_peliculas if str(p['movieId']) == str(movieId)), None)
        if not pelicula_info:
            return False  # Película no encontrada

        # Formatear la entrada a guardar
        nueva_pelicula = {
            "movieId": str(pelicula_info['movieId']),
            "pelicula": str(pelicula_info['title']),
            "rating": float(rating),
            "generos": pelicula_info.get('generos', []),
            "year": pelicula_info.get('year')
        }

        # Verificar si ya está en la lista
        ya_vista = any(str(p['movieId']) == str(movieId) for p in usuario.get('peliculas', []))
        if ya_vista:
            return True  # Ya registrada, no repetir

        # Añadir al array
        usuarios_col.update_one(
            {'numero': str(userId)},
            {'$push': {'peliculas': nueva_pelicula}}
        )
        return True

    except Exception as e:
        print(f"❌ Error al añadir película vista: {e}")
        return False