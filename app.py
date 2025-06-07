from flask import (
    Flask, render_template, request, redirect, url_for,
    abort, jsonify, session, flash
)
import os
import time
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from mongo_utils import (
    buscar_usuario, verificar_contrasena,
    get_peliculas, get_peliculas_vistas, anhadir_pelicula_vista
)

from cassandra_utils import (get_cassandra_predictions)

import random

import joblib
import numpy as np

# ─── CONFIGURACIÓN GENERAL ─────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necesaria para sesiones

df_movies = pd.read_csv('./Data/transformed/movies_cleaned.csv')

# ─── CARGAR MODELOS ────────────────────────────────────────────────────────────

pca = joblib.load('./notebooks/modelos_entrenados/pca_model.pkl')
similarity_matrix = np.load('./notebooks/modelos_entrenados/similarity_matrix.npy')

# ─── CONFIGURACIÓN DE KAFKA ────────────────────────────────────────────────────

KAFKA_BROKER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = 'info'

producer = None
timeout = 300  # 5 minutos
start_time = time.time()

while producer is None:
    try:
        producer = KafkaProducer(bootstrap_servers=KAFKA_BROKER)
        print("✅ Conectado a Kafka.")
    except NoBrokersAvailable:
        if (time.time() - start_time) > timeout:
            raise Exception("❌ Kafka no está disponible tras 5 minutos.")
        print("⏳ Kafka no disponible. Reintentando en 5 segundos...")
        time.sleep(5)

# ─── DATOS DE PELÍCULAS ────────────────────────────────────────────────────────

peliculas = get_peliculas()

def get_peliculas_no_vistas():
    numero = session.get('usuario_numero')
    predicciones = get_cassandra_predictions(userId=int(numero))
    vistas = get_peliculas_vistas(userId=numero)

    movie_ids_vistos = set()
    if vistas:
        if isinstance(vistas[0], dict):
            movie_ids_vistos = {str(p['movieId']) for p in vistas}
        elif isinstance(vistas[0], (int, str)):
            movie_ids_vistos = {str(p) for p in vistas}

    # Filtrar predicciones no vistas
    pred_no_vistas = [p for p in predicciones if str(p.movieid) not in movie_ids_vistos]

    # Seleccionar 5 random (o menos si no hay suficientes)
    seleccion = random.sample(pred_no_vistas, min(5, len(pred_no_vistas)))

    # Si quieres devolver los objetos de 'peliculas' correspondientes, puedes hacer:
    movie_ids_seleccion = {str(p.movieid) for p in seleccion}
    peliculas_seleccionadas = [p for p in peliculas if str(p['movieId']) in movie_ids_seleccion]

    return peliculas_seleccionadas


def get_generos():
    generos_unicos = {g for p in peliculas for g in p['generos']}
    return sorted(generos_unicos)

# ─── FUNCIONES AUXILIARES ──────────────────────────────────────────────────────

def mas_info_kafka(movie_id):
    peli = next((p for p in peliculas if p['movieId'] == movie_id), None)
    if peli:
        numero = session.get('usuario_numero')
        if numero:
            try:
                mensaje = f"ID: {movie_id} / Película: {peli['title']}"
                producer.send(KAFKA_TOPIC, value=mensaje.encode('utf-8'))
                flash(f"🔍 Más info para '{peli['title']}' enviada a Kafka", 'success')
            except Exception as e:
                flash(f"Kafka error: {e}", 'error')
        else:
            flash("⚠️ Usuario no logueado", 'warning')
    else:
        flash("Película no encontrada", 'error')

def recommend_movies(movie_id, df, similarity_matrix, top_n=20):
    try:
        idx = df[df['movieId'] == movie_id].index[0]
    except IndexError:
        return []

    sim_scores = list(enumerate(similarity_matrix[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:top_n+1]
    recommended_indices = [i[0] for i in sim_scores]
    return df.loc[recommended_indices]

def mas_info_mostrar_recomendaciones(movie_id):
    recomendaciones = recommend_movies(movie_id, df_movies, similarity_matrix).sample(n=5, random_state=None)
    return recomendaciones.to_dict(orient='records')

# ─── RUTAS ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    genero = request.args.get('genero')
    generos = get_generos()
    peliculas_no_vistas = get_peliculas_no_vistas()

    return render_template(
        'index.html',
        peliculas=peliculas_no_vistas,
        generos=generos,
        seleccionado=genero
    )


@app.route('/pelicula/<int:id>')
def detalle_pelicula(id):
    peli = next((p for p in peliculas if p['movieId'] == str(id)), None)
    if not peli:
        abort(404)
    
    peliculas_similares = mas_info_mostrar_recomendaciones(id)
    mas_info_kafka(id)

    pelis_no_vistas = get_peliculas_no_vistas()
    

    return render_template(
        'detalle.html',
        pelicula=peli,
        recomendaciones=peliculas_similares
    )


@app.route('/marcar_vista/<int:id>', methods=['POST'])
def marcar_vista(id):
    valoracion = request.form.get('valoracion')
    print(peliculas)

    # Buscar película por movieId (no id)
    peli = next((p for p in peliculas if str(p['movieId']) == str(id)), None)

    if peli:
        flash(f"✅ Marcaste '{peli['title']}' como vista con valoración {valoracion}.", 'success')
        numero = session.get('usuario_numero')
        if numero:
            try:
                # Si rating no viene o no es válido, poner un valor por defecto, ej 0
                rating_val = float(valoracion) if valoracion else 0
                anhadir_pelicula_vista(userId=numero, movieId=id, rating=rating_val)

                # Opcional: actualizar la sesión para que la película quede marcada como vista sin recargar DB
                vistas = set(session.get('vistas', []))
                vistas.add(str(id))
                session['vistas'] = list(vistas)

            except Exception as e:
                flash(f"❌ Error guardando en MongoDB: {e}", 'error')

    else:
        flash("Película no encontrada.", "error")

    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        numero = request.form['numero']
        contrasena = request.form['contrasena']
        usuario = buscar_usuario(numero)

        if usuario and verificar_contrasena(usuario, contrasena):
            session['usuario_numero'] = str(numero)
            session['logged_in'] = True
            flash('✅ ¡Bienvenido!', 'success')
            return redirect(url_for('index'))
        else:
            error = '❌ Número o contraseña incorrectos.'

    return render_template('login.html', error=error)


# ─── MANEJO DE ERRORES ─────────────────────────────────────────────────────────

@app.errorhandler(404)
def pagina_no_encontrada(error):
    return render_template('error.html', error=error), 404


# ─── EJECUCIÓN ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)