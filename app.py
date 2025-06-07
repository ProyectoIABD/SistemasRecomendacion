from flask import (
    Flask, render_template, request, redirect, url_for,
    abort, jsonify, session, flash
)
import os
import time
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from mongo_utils import (
    insertar_usuario, buscar_usuario, verificar_contrasena,
    get_peliculas, get_peliculas_vistas, anhadir_pelicula_vista
)


# ─── CONFIGURACIÓN GENERAL ─────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necesaria para sesiones

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
    vistas = get_peliculas_vistas(userId=numero)

    movie_ids_vistos = set()
    if vistas:
        if isinstance(vistas[0], dict):
            movie_ids_vistos = {str(p['movieId']) for p in vistas}
        elif isinstance(vistas[0], (int, str)):
            movie_ids_vistos = {str(p) for p in vistas}

    return [p for p in peliculas if str(p['movieId']) not in movie_ids_vistos]


def get_generos():
    generos_unicos = {g for p in peliculas for g in p['generos']}
    return sorted(generos_unicos)

# ─── FUNCIONES AUXILIARES ──────────────────────────────────────────────────────

def mas_info_kafka(movie_id):
    peli = next((p for p in peliculas if p['id'] == movie_id), None)
    if peli:
        numero = session.get('usuario_numero')
        if numero:
            try:
                mensaje = f"ID: {movie_id} / Película: {peli['titulo']}"
                producer.send(KAFKA_TOPIC, value=mensaje.encode('utf-8'))
                flash(f"🔍 Más info para '{peli['titulo']}' enviada a Kafka", 'success')
            except Exception as e:
                flash(f"Kafka error: {e}", 'error')
        else:
            flash("⚠️ Usuario no logueado", 'warning')
    else:
        flash("Película no encontrada", 'error')

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
    peli = next((p for p in peliculas if p['id'] == id), None)
    if not peli:
        abort(404)

    mas_info_kafka(id)

    pelis_no_vistas = get_peliculas_no_vistas()
    recomendaciones = [
        p for p in pelis_no_vistas
        if p['genero'] == peli['genero'] and p['id'] != id and p['puntuacion'] >= 7.5
    ]

    return render_template(
        'detalle.html',
        pelicula=peli,
        recomendaciones=recomendaciones
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