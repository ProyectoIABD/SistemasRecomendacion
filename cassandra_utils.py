from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import json
import pandas as pd

cloud_config = {
    'secure_connect_bundle': './cassandra/secure-connect-test-cassandra.zip'
}

with open("./cassandra/cassandra-token.json") as f:
    secrets = json.load(f)

CLIENT_ID = secrets["clientId"]
CLIENT_SECRET = secrets["secret"]
TOKEN = secrets["token"]
KEYSPACE = "proyecto_recomendaciones"

auth_provider = PlainTextAuthProvider(CLIENT_ID, CLIENT_SECRET)
cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
session = cluster.connect()
session.set_keyspace(KEYSPACE)

# Crear keyspace si no existe
def crear_keyspace():
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}}
    """)
    session.set_keyspace(KEYSPACE)


def get_cassandra_predictions(userId):
    result = session.execute(
        "SELECT * FROM recomendaciones_ALS WHERE userId=%s", (userId,)
    )
    return list(sorted(result, key=lambda r: r.prediction, reverse=True)[:20])

# Inicialización
#crear_keyspace()