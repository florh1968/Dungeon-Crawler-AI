import math
from flask import Flask, redirect, render_template, request, url_for, session, request, jsonify, flash
from flask_socketio import SocketIO, send, emit
from flask_migrate import Migrate
import numpy as np
from database.models import db, User, MazeBd
from sqlalchemy import or_
import json
import threading
import time
import bcrypt
from functools import wraps
from environment import maze

app = Flask(__name__)

# Configuración de la base de datos (en este caso SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mysecretkey'  # Necesario para usar sesiones

# Inicializar la base de datos con la aplicación
db.init_app(app)
socketio = SocketIO(app)

# Inicializar Flask-Migrate
migrate = Migrate(app, db)

# Crear la base de datos y las tablas si no existen
with app.app_context():
    db.create_all()

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))  # Redirigir al login si no está autenticado
        return f(*args, **kwargs)
    return decorated_function

def get_all_users():
    users = User.query.all()
    users_list = [{'username': user.username, 'completed_dungeons': user.completed_dungeons} for user in users]
    
    # Imprime los datos para depuración
    print(users_list)
    
    return users_list

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        # Buscar el usuario en la base de datos
        user = User.query.filter(or_(User.username == username, User.email == username)).first()

        # Verificar si el usuario existe y la contraseña es correcta
        if user and bcrypt.checkpw(password, user.password):
            session['user_id'] = user.id  # Guardar el ID del usuario en la sesión
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Credenciales incorrectas')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Eliminar la sesión del usuario
    return redirect(url_for('login'))

# Ruta protegida, solo accesible si se ha iniciado sesión
@app.route('/home')
@login_required
def home():
    if 'user_id' in session:
        return "Bienvenido al Home!"
    else:
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        email = request.form['email']

        # Comprobar si ya existe un usuario con ese nombre o correo
        existing_user = User.query.filter(or_(User.username == username, User.email == email)).first()

        if existing_user:
            # Si el usuario ya existe, devolver un mensaje de error
            return render_template('register.html', error="Usuario ya registrado")

        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

        new_user = User(username=username, password=hashed_password, email=email,)
        
        # Añadir el nuevo usuario a la base de datos
        db.session.add(new_user)
        db.session.commit()

        # Guardar el ID del nuevo usuario en la sesión
        session['user_id'] = new_user.id
        
        # Redirigir al home o a la página que prefieras después del registro
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/leaderboard')
def leaderboard():
    users = get_all_users()
    
    # Asegúrate de que todos los valores sean numéricos y no None
    for user in users:
        if user['completed_dungeons'] is None:
            user['completed_dungeons'] = 0  # O asigna un valor predeterminado
    
    # Ordena la lista de usuarios
    users_sorted = sorted(users, key=lambda user: user['completed_dungeons'], reverse=True)
    
    return render_template('leaderboard.html', users=users_sorted)

@app.route('/mode_creative', methods=['GET','POST'])
def mode_creative():
    if request.method == 'POST':
        try:
            cantRow = int(request.form.get('rows', 0))
            print (1)
            cantColumn = int(request.form.get('columns', 0))
            print (2)
            entradaX = int(request.form.get('entradaX', 0))
            print (3)
            entradaY = int(request.form.get('entradaY', 0))
            print (4)
            salidaX = int(request.form.get('salidaX', 0))
            print (5)
            salidaY = int(request.form.get('salidaY', 0))
            print (6)

            if cantRow < 5 or cantColumn < 5:
                print (7)
                return render_template('mode_creative.html', error="Mapa muy pequeño")

            if entradaX >= cantRow or entradaY >= cantColumn or entradaX < 0 or entradaY < 0:
                print (8)
                return render_template('mode_creative.html', error="Entrada del maze inválida")

            if salidaX >= cantRow or salidaY >= cantColumn or salidaX < 0 or salidaY < 0:
                print (9)
                return render_template('mode_creative.html', error="Salida del maze inválida")
            print (10)
            grid = np.zeros((cantRow, cantColumn))
            grid[entradaX][entradaY] = 2
            grid[salidaX][salidaY] = 3

            for i in range(cantRow):
                for j in range(cantColumn):
                    try:
                        cell_value = int(request.form.get(f'cell_{i}_{j}', 0))
                        print (11)
                        if cell_value in [1, 4]:
                            print (12)
                            grid[i][j] = cell_value
                        else:
                            print (13)
                            return render_template('mode_creative.html', error="Número desconocido")
                    except ValueError:
                        print (14)
                        return render_template('mode_creative.html', error="Entrada inválida")

            # Aquí puedes agregar la lógica para verificar el laberinto y guardarlo en la base de datos
            print (15)
            json_str = json.dumps(grid.tolist())  # Convertir el array a lista para JSON
            print (16)
            new_maze = MazeBd(grid=json_str, entradaX=entradaX, entradaY=entradaY, salidaX=salidaX, salidaY=salidaY)
            # Si el laberinto es válido, guardar en la base de datos
            print (17)
            return render_template('mode_creative.html', success="Mapa creado exitosamente")

        except Exception as e:
            print (18)
            return render_template('mode_creative.html', error=f"Ocurrió un error: {str(e)}")

    # Si el método es GET, simplemente devuelve el formulario
    return render_template('mode_creative.html')

mapa_original = [
    -1, 0, 0, 0, 0, 0, 0,
    1, 1, 1, 0, 1, 1 , 0, 
    0, 1, 0, 0, 1, 0, 0,
    0, 1, 0, 0, 1, 0, 1,
    0, 0, 0, 0, 0, 0, 1,
    0, 1, 0, 0, 1, 0, 1,
    0, 0, 0, 1, 1, 0,3,
]

map_size = 7

def find_player_position():
    return mapa_original.index(-1)
@app.route('/map')
def map():
    return render_template('map.html', mapa_original=mapa_original)

@socketio.on('connect')
def handle_connect():
    emit('map', mapa_original)

@socketio.on('move')
def handle_move(direction):
    global mapa_original 
    print(f'Movimiento recibido: {direction}')

    player_pos = find_player_position()

    if direction == 'ArrowUp':
        new_pos = player_pos - map_size if player_pos >= map_size else player_pos
    elif direction == 'ArrowDown':
        new_pos = player_pos + map_size if player_pos < len(mapa_original) - map_size else player_pos
    elif direction == 'ArrowLeft':
        new_pos = player_pos - 1 if player_pos % map_size != 0 else player_pos
    elif direction == 'ArrowRight':
        new_pos = player_pos + 1 if (player_pos + 1) % map_size != 0 else player_pos
    else:
        new_pos = player_pos  

    if mapa_original[new_pos] == 0:
        mapa_original[player_pos] = 0
        mapa_original[new_pos] = -1  

    if mapa_original[new_pos] == 3:
        mapa_original[player_pos] = 0
        mapa_original [new_pos] = -2
        emit('finish_map', 'You Win!')
              
    emit('map', mapa_original)

@socketio.on('restart_pos')
def restart_position(position):
    global mapa_original 
    mapa_original[mapa_original.index(-2)] = 3
    mapa_original[position] = -1
    emit('map', mapa_original)
    
@app.route('/map_creator')
def map_creator():
    return render_template('map_creator.html')
    
@app.route('/validate_map', methods=['POST'])
def validate_map():
    data = request.get_json()
    map_grid = data.get('map')  # El mapa que enviaste desde el frontend
    size = int(len(map_grid) ** 0.5)  # Suponiendo que el mapa es cuadrado

    # Buscar el punto de inicio y de salida en el mapa
    start_point = None
    exit_point = None

    # Convertir el arreglo plano en una matriz
    grid = [map_grid[i:i + size] for i in range(0, len(map_grid), size)]

    # Identificar el punto de inicio (2) y de salida (3)
    for row in range(size):
        for col in range(size):
            if grid[row][col] == 2:
                start_point = (row, col)
            if grid[row][col] == 3:
                exit_point = (row, col)

    if start_point is None or exit_point is None:
        return jsonify({'valid': False, 'error': 'No se encontró el punto de inicio o salida'}), 400

    # Crear la instancia del laberinto
    new_maze = maze.Maze(grid, size, start_point, exit_point)

    # Validar si el laberinto es resoluble
    if new_maze.is_winneable():
        return jsonify({'valid': True})
    else:
        return jsonify({'valid': False})


if __name__ == '__main__':
    socketio.run(app, debug=True)
