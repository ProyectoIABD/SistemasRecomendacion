from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import json
import pandas as pd

# Configuración de conexión (ajusta los valores según tu entorno)
CASSANDRA_HOSTS = ['127.0.0.1']  # Cambia por la IP de tu clúster si es necesario
CASSANDRA_KEYSPACE = 'recomendador'
CASSANDRA_USER = 'cassandra'      # Cambia por tu usuario si tienes autenticación
CASSANDRA_PASS = 'cassandra'      # Cambia por tu contraseña si tienes autenticación

# Si tu clúster no requiere autenticación, puedes omitir auth_provider
# auth_provider = PlainTextAuthProvider(username=CASSANDRA_USER, password=CASSANDRA_PASS)
# cluster = Cluster(CASSANDRA_HOSTS, auth_provider=auth_provider)
#cluster = Cluster(CASSANDRA_HOSTS)
#session = cluster.connect()

cloud_config = {
    'secure_connect_bundle': 'cassandra/secure-connect-test-cassandra.zip'
}

with open("cassandra/cassandra-token.json") as f:
    secrets = json.load(f)

CLIENT_ID = secrets["clientId"]
CLIENT_SECRET = secrets["secret"]
TOKEN = secrets["token"]

KEYSPACE = "proyecto_recomendaciones"

# Crear keyspace si no existe
def crear_keyspace():
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {CASSANDRA_KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}}
    """)
    session.set_keyspace(CASSANDRA_KEYSPACE)


# Insertar usuario
def insertar_usuario(numero, contrasena):
    session.execute(
        "INSERT INTO usuarios (numero, contrasena) VALUES (%s, %s)",
        (numero, contrasena)
    )

# Buscar usuario por número
def buscar_usuario(numero):
    result = session.execute(
        "SELECT * FROM usuarios WHERE numero=%s", (numero,)
    )
    return result.one()


# Obtener registros de vistas de un usuario
def obtener_vistos_usuario(numero):
    result = session.execute(
        "SELECT pelicula_id, rating FROM vistos WHERE numero=%s", (numero,)
    )
    return list(result)


def get_cassandra_predictions(userId):
    result = session.execute(
        "SELECT * FROM recomendaciones_ALS WHERE userId=%s", (userId,)
    )
    return list(sorted(result, key=lambda r: r.prediction, reverse=True)[:20])

# Inicialización
#crear_keyspace()
