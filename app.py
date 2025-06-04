from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session, flash
from mongo_utils import insertar_usuario, buscar_usuario, verificar_contrasena
from cassandra_utils import guardar_visto

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necesario para usar sesiones

# Datos de ejemplo: películas
peliculas = [
    {"id": 1, "titulo": "Inception", "genero": "Ciencia Ficción", "puntuacion": 8.8, "descripcion": "Un ladrón que roba secretos a través de sueños."},
    {"id": 2, "titulo": "Titanic", "genero": "Romance", "puntuacion": 7.8, "descripcion": "Una historia de amor en el fatídico viaje del Titanic."},
    {"id": 3, "titulo": "Interstellar", "genero": "Ciencia Ficción", "puntuacion": 8.6, "descripcion": "Exploradores viajan a través de un agujero de gusano en el espacio."},
    {"id": 4, "titulo": "La La Land", "genero": "Musical", "puntuacion": 8.0, "descripcion": "Un pianista y una actriz persiguen sus sueños en Los Ángeles."},
    {"id": 5, "titulo": "El Padrino", "genero": "Crimen", "puntuacion": 9.2, "descripcion": "La historia de una familia mafiosa en EE.UU."}
]

def get_peliculas_no_vistas():
    vistas = session.get('vistas', set())
    return [p for p in peliculas if str(p['id']) not in vistas]

def get_generos():
    return sorted(list(set(p['genero'] for p in peliculas)))

# 1. Ruta básica
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('registro'))
    genero = request.args.get('genero')
    pelis = get_peliculas_no_vistas()
    if genero:
        pelis = [p for p in pelis if p['genero'] == genero]
    generos = get_generos()
    return render_template('index.html', peliculas=pelis, generos=generos, seleccionado=genero)

# 2. Ruta con parámetros
@app.route('/pelicula/<int:id>')
def detalle_pelicula(id):
    peli = next((p for p in peliculas if p['id'] == id), None)
    if not peli:
        abort(404)
    # Recomendaciones: mismas género y buena puntuación, que no estén vistas
    pelis_no_vistas = get_peliculas_no_vistas()
    recomendaciones = [p for p in pelis_no_vistas if p['genero'] == peli['genero'] and p['id'] != id and p['puntuacion'] >= 7.5]
    return render_template('detalle.html', pelicula=peli, recomendaciones=recomendaciones)

# 3. Manejo de formularios (GET/POST)
@app.route('/formulario', methods=['GET', 'POST'])
def mostrar_formulario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        # Aquí normalmente procesaríamos los datos
        return redirect(url_for('resultado', nombre=nombre, email=email))
    return render_template('formulario.html')

# 4. Redirección y resultado
@app.route('/resultado')
def resultado():
    nombre = request.args.get('nombre', 'Invitado')
    email = request.args.get('email', '')
    return render_template('resultado.html', nombre=nombre, email=email)

@app.route('/marcar_vista/<int:id>', methods=['POST'])
def marcar_vista(id):
    vistas = set(session.get('vistas', set()))
    vistas.add(str(id))
    session['vistas'] = list(vistas)
    valoracion = request.form.get('valoracion')
    peli = next((p for p in peliculas if p['id'] == id), None)
    if peli:
        flash(f"Has marcado '{peli['titulo']}' como vista con valoración {valoracion}.", 'success')
        # Guardar en Cassandra si el usuario está logueado
        numero = session.get('usuario_numero')
        if numero:
            try:
                guardar_visto(numero, id, float(valoracion))
            except Exception as e:
                flash(f"Error al guardar en Cassandra: {e}", 'error')
    return redirect(url_for('index'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        numero = request.form['numero']
        contrasena = request.form['contrasena']
        if buscar_usuario(numero):
            flash('El número de usuario ya está registrado.', 'error')
            return render_template('registro.html')
        insertar_usuario(numero, contrasena)
        session['usuario_numero'] = numero
        session['usuario_contrasena'] = contrasena
        session['logged_in'] = True
        return redirect(url_for('seleccionar_generos'))
    return render_template('registro.html')

@app.route('/seleccionar_generos', methods=['GET', 'POST'])
def seleccionar_generos():
    generos = get_generos()
    if request.method == 'POST':
        favoritos = request.form.getlist('generos')
        if len(favoritos) != 3:
            flash('Debes seleccionar exactamente 3 géneros favoritos.', 'error')
            return render_template('seleccionar_generos.html', generos=generos, seleccionados=favoritos)
        session['generos_favoritos'] = favoritos
        # Aquí se podría guardar en MongoDB más adelante
        flash('¡Registro completado! Tus géneros favoritos han sido guardados.', 'success')
        return redirect(url_for('resultado'))  # Cambia esto por resultado
    return render_template('seleccionar_generos.html', generos=generos, seleccionados=[])

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        numero = request.form['numero']
        contrasena = request.form['contrasena']
        usuario = buscar_usuario(numero)
        if usuario and verificar_contrasena(usuario, contrasena):
            session['usuario_numero'] = numero
            session['logged_in'] = True
            flash('¡Bienvenido de nuevo!', 'success')
            return redirect(url_for('index'))
        else:
            error = 'Número o contraseña incorrectos.'
    return render_template('login.html', error=error)

# 6. Manejo de errores
@app.errorhandler(404)
def pagina_no_encontrada(error):
    return render_template('error.html', error=error), 404

if __name__ == '__main__':
    app.run(debug=True)
