from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from asistente import clase_virtual
from flask_login import LoginManager, login_required, login_user, current_user, UserMixin , logout_user
from dialogo import dialogo
from flask_cors import CORS
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import abort
from datetime import datetime



app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clases.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'inicio_sesion'

# Modelo Curso
class Curso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    clases = db.relationship('Clase', backref='curso', lazy=True)

class Clase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'), nullable=False)
    secciones = db.relationship('Seccion', backref='clase', lazy=True)

class Seccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    dialogo = db.Column(db.Text, nullable=True)
    clase_id = db.Column(db.Integer, db.ForeignKey('clase.id'), nullable=False)
    
class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    contraseña_hash = db.Column(db.String(128), nullable=False)
    tipo_usuario = db.Column(db.String(20), nullable=False)  # Puede ser 'admin', 'profesor' o 'alumno'

    def set_contraseña(self, contraseña):
        self.contraseña_hash = generate_password_hash(contraseña)

    def verificar_contraseña(self, contraseña):
        return check_password_hash(self.contraseña_hash, contraseña)
    
class RegistroAccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(100), nullable=False)
    email_usuario = db.Column(db.String(100), nullable=False)
    tipo_usuario = db.Column(db.String(20), nullable=False)
    accion = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

def registrar_accion(nombre_usuario, email_usuario, tipo_usuario, accion):
    nuevo_registro = RegistroAccion(nombre_usuario=nombre_usuario, email_usuario=email_usuario, tipo_usuario=tipo_usuario, accion=accion)
    db.session.add(nuevo_registro)
    db.session.commit()

# Crear la base de datos y las tablas
with app.app_context():
    db.create_all()
    
    




def separar_secciones(texto):
    secciones = {
        "Introduction to the Class": {"contenido": "", "dialogo": ""},
        "Objectives of the Class": {"contenido": "", "dialogo": ""},
        "Teaching Content of the Class": {"contenido": "", "dialogo": ""},
        "Exercises": {"contenido": "", "dialogo": ""},
        "Closing": {"contenido": "", "dialogo": ""}
    }
    
    nombres_secciones = list(secciones.keys())
    seccion_actual = None
    
    for linea in texto.split('\n'):
        linea = linea.strip()
        if linea.startswith('**') and linea.endswith('**'):
            nombre_seccion = linea.strip('**').strip()
            if nombre_seccion in nombres_secciones:
                seccion_actual = nombre_seccion
        elif seccion_actual:
            secciones[seccion_actual]["contenido"] += linea + "\n"
    
    for seccion in secciones:
        secciones[seccion]["contenido"] = secciones[seccion]["contenido"].strip()
    
    return secciones

@app.route('/api/cursos', methods=['GET'])
def get_cursos():
    cursos = Curso.query.all()
    return jsonify([{
        'id': curso.id,
        'nombre': curso.nombre,
        'clases': [{'id': clase.id, 'nombre': clase.nombre} for clase in curso.clases]
    } for curso in cursos])

@app.route('/cursos', methods=['POST'])
def crear_curso():
    data = request.form
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'error': 'Nombre is required'}), 400

    nuevo_curso = Curso(nombre=nombre)
    db.session.add(nuevo_curso)
    db.session.commit()
    registrar_accion(current_user.nombre_usuario, current_user.email, current_user.tipo_usuario, 'Crear curso')
    return redirect(url_for('profesor_dashboard'))


@app.route('/api/cursos/<int:curso_id>/clases', methods=['POST'])
def create_clase_in_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    data = request.json
    material = data.get('material')
    if not material:
        return jsonify({'error': 'Material is required'}), 400
    
    resultado = clase_virtual(material)
    fragmentos = separar_secciones(resultado)
    
    nueva_clase = Clase(nombre='Clase', curso_id=curso.id)
    db.session.add(nueva_clase)
    db.session.commit()
    nueva_clase.nombre = f'Clase {nueva_clase.id}'
    db.session.commit()
    
    for nombre, datos in fragmentos.items():
        contenido = datos["contenido"]
        dialogo_profesor = dialogo(contenido)
        fragmentos[nombre]["dialogo"] = dialogo_profesor
        
        nueva_seccion = Seccion(nombre=nombre, contenido=contenido, dialogo=dialogo_profesor, clase_id=nueva_clase.id)
        db.session.add(nueva_seccion)
        db.session.commit()
    
    return jsonify({'message': 'Clase creada', 'clase': {'id': nueva_clase.id, 'nombre': nueva_clase.nombre}}), 201

@app.route('/api/cursos/<int:curso_id>', methods=['DELETE'])
def delete_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    
    for clase in curso.clases:
        for seccion in clase.secciones:
            db.session.delete(seccion)
        db.session.delete(clase)
    
    db.session.delete(curso)
    db.session.commit()
    registrar_accion(current_user.nombre_usuario, current_user.email, current_user.tipo_usuario, 'Eliminar curso')
    return jsonify({'message': 'Curso eliminado'}), 200

@app.route('/api/clases', methods=['GET'])
def get_clases():
    clases = Clase.query.all()
    return jsonify([{
        'id': clase.id,
        'nombre': clase.nombre,
        'secciones': [{'id': seccion.id, 'nombre': seccion.nombre, 'contenido': seccion.contenido, 'dialogo': seccion.dialogo} for seccion in clase.secciones]
    } for clase in clases])

@app.route('/asistente', methods=['POST'])
def asistente2():
    data = request.form
    material = data.get('material')
    curso_id = data.get('curso_id')
    if not material:
        return jsonify({'error': 'Material is required'}), 400
    if not curso_id:
        return jsonify({'error': 'Curso ID is required'}), 400

    resultado = clase_virtual(material)
    fragmentos = separar_secciones(resultado)

    nueva_clase = Clase(nombre='Clase', curso_id=curso_id)
    db.session.add(nueva_clase)
    db.session.commit()
    nueva_clase.nombre = f'Clase {nueva_clase.id}'
    db.session.commit()

    for nombre, datos in fragmentos.items():
        contenido = datos["contenido"]
        dialogo_profesor = dialogo(contenido)
        fragmentos[nombre]["dialogo"] = dialogo_profesor

        nueva_seccion = Seccion(nombre=nombre, contenido=contenido, dialogo=dialogo_profesor, clase_id=nueva_clase.id)
        db.session.add(nueva_seccion)
        db.session.commit()

    return redirect(url_for('profesor_dashboard'))

@app.route('/clases/<int:id>')
def ver_clase(id):
    clase = Clase.query.get_or_404(id)
    secciones = Seccion.query.filter_by(clase_id=id).all()
    return render_template('ver_clase.html', clase=clase, secciones=secciones)

@app.route('/clases/editar/<int:clase_id>/<int:seccion_id>', methods=['GET', 'POST'])
def editar_seccion(clase_id, seccion_id):
    seccion = Seccion.query.get_or_404(seccion_id)

    if request.method == 'POST':
        seccion.nombre = request.form['nombre']
        seccion.contenido = request.form['contenido']
        seccion.dialogo = request.form['dialogo']

        db.session.commit()
        return redirect(url_for('ver_clase', id=clase_id))

    return render_template('editar_seccion.html', seccion=seccion, clase_id=clase_id)

@app.route('/clases/eliminar/<int:clase_id>/<int:seccion_id>')
def eliminar_seccion(clase_id, seccion_id):
    seccion = Seccion.query.get_or_404(seccion_id)
    db.session.delete(seccion)
    db.session.commit()
    return redirect(url_for('ver_clase', id=clase_id))

@app.route('/clases/eliminar/<int:clase_id>')
def eliminar_clase(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    for seccion in clase.secciones:
        db.session.delete(seccion)
    db.session.delete(clase)
    db.session.commit()
    return redirect(url_for('profesor_dashboard'))


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        email = request.form['email']
        contraseña = request.form['contraseña']
        tipo_usuario = request.form['tipo_usuario']
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('El correo electrónico ya está registrado.')
            return redirect(url_for('registro'))
        nuevo_usuario = Usuario(nombre_usuario=nombre_usuario, email=email, tipo_usuario=tipo_usuario)
        nuevo_usuario.set_contraseña(contraseña)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('¡Registro exitoso! Por favor inicia sesión.')
        if tipo_usuario == 'profesor':
            return redirect(url_for('profesor_dashboard'))
        elif tipo_usuario == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif tipo_usuario == 'alumno':
            return redirect(url_for('alumno_dashboard'))
    return render_template('registro.html')

@app.route('/inicio_sesion', methods=['GET', 'POST'])
def inicio_sesion():
    if request.method == 'POST':
        email = request.form['email']
        contraseña = request.form['contraseña']
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is None or not usuario.verificar_contraseña(contraseña):
            flash('Credenciales inválidas. Por favor inténtalo de nuevo.')
            return redirect(url_for('inicio_sesion'))
        login_user(usuario)
        if usuario.tipo_usuario == 'profesor':
            return redirect(url_for('profesor_dashboard'))
        elif usuario.tipo_usuario == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif usuario.tipo_usuario == 'alumno':
            return redirect(url_for('alumno_dashboard'))
    return render_template('inicio_sesion.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('inicio_sesion'))


def requiere_roles(*roles):
    def decorador(f):
        @wraps(f)
        def decorado_funcion(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('inicio_sesion'))
            if current_user.tipo_usuario not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorado_funcion
    return decorador

@app.route('/admin_dashboard')
@login_required
@requiere_roles('admin')
def admin_dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('inicio_sesion'))
    
    acciones=RegistroAccion.query.all()
    return render_template('admin.html' , aciones=acciones)

@app.route('/profesor_dashboard')
@login_required
@requiere_roles('profesor', 'admin')
def profesor_dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('inicio_sesion'))
    clases = Clase.query.all()
    cursos = Curso.query.all()
    return render_template('index.html', clases=clases, cursos=cursos)

@app.route('/alumno_dashboard')
@login_required
@requiere_roles('alumno', 'admin')
def alumno_dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('inicio_sesion'))
    return render_template('alumno.html')




if __name__ == '__main__':
    app.run(debug=True)