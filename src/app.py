import urllib, urllib.request
from xml.dom.minidom import Document
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, session, url_for
from flask_mail import Mail, Message
import os

import requests
import database as db


template_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
template_dir = os.path.join(template_dir, 'src', 'templates')

app = Flask(__name__, template_folder = template_dir)

# Configuración para Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Servidor SMTP de Gmail
app.config['MAIL_PORT'] = 465  # Puerto SMTP de Gmail
app.config['MAIL_USERNAME'] = 'pruebasmail.alvaro@gmail.com'  # Correo electrónico desde el que se enviarán los mensajes
app.config['MAIL_PASSWORD'] = os.environ.get('PASSWORD')  # Contraseña del correo electrónico
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

@app.route('/')
def home():
    cursor = db.database.cursor()
    cursor.execute("SELECT * FROM usuarios")
    myresult = cursor.fetchall()
    #Convertir los datos a diccionario
    insertObject = []
    columnNames = [column[0] for column in cursor.description]
    for record in myresult:
        insertObject.append(dict(zip(columnNames, record)))
    cursor.close()
    return render_template('index.html', data=insertObject)

    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Verificar las credenciales en la base de datos
        cursor = db.database.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            # Si las credenciales son correctas, redirige a la página principal
            return render_template('busqueda.html')
        else:
            # Si las credenciales son incorrectas, puedes renderizar nuevamente el formulario de inicio de sesión con un mensaje de error
            return render_template('login.html', error="Credenciales incorrectas. Inténtalo de nuevo.")
    else:
        # Si la solicitud es GET, muestra el formulario de inicio de sesión
        return render_template('login.html')


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    # Aquí puedes agregar cualquier lógica necesaria para cerrar la sesión
    # Por ejemplo, eliminar la sesión actual del usuario
    # session.pop('user_id', None)

    # Luego, redirige al usuario a la página de inicio
    return render_template('index.html')

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        mensaje = request.form['mensaje']

        # Crear un objeto Message para el correo electrónico
        msg = Message(subject='Mensaje de contacto desde HogarData',
                      recipients=['alvaromartinsalazar@gmail.com'],  # Dirección de correo electrónico de destino
                      body=f'Nombre: {nombre}\nEmail: {email}\nMensaje: {mensaje}')

        # Enviar el correo electrónico
        try:
            mail.send(msg)
            return redirect(url_for('contacto_exitoso'))
        except Exception as e:
            # Manejar el error si ocurre algún problema al enviar el correo electrónico
            print('Error al enviar el correo electrónico:', e)
            return 'Error al enviar el correo electrónico. Inténtalo de nuevo más tarde.'
    else:
        return render_template('contacto.html')


@app.route('/perfil')
def perfil():
    # Verificar si el usuario está autenticado
    if 'user_id' in session:
        # Si el usuario está autenticado, renderiza la plantilla de perfil con los datos del usuario
        return render_template('perfil.html')
    # Si el usuario no está autenticado, redirige al usuario a la página de inicio de sesión
    return redirect(url_for('login'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' in session:
        user_id = session['user_id']
        email = request.form['email']
        password = request.form['password']
        # Actualizar el correo electrónico y la contraseña del usuario en la base de datos
        cursor = db.database.cursor()
        cursor.execute("UPDATE usuarios SET email = %s, password = %s WHERE id = %s", (email, password, user_id))
        db.database.commit()
        cursor.close()
        # Redirigir al usuario a la página de perfil después de la actualización
        return redirect(url_for('perfil'))
    # Si el usuario no está autenticado, redirigirlo a la página de inicio de sesión
    return redirect(url_for('login'))

#AQUI EMPIEZA EL SCRAPING
@app.route('/index', methods=['GET', 'POST'])
def web():
    enlaces_principales = []
    enlaces_secundarios = []
    resultados = []

    if request.method == 'POST':
        ciudad = request.form['ciudad']
        tipo_propiedad = request.form['tipo_propiedad']

        # Construir la URL de búsqueda en Fotocasa
        url = f"https://www.fotocasa.es/es/comprar/viviendas/{ciudad}?maxPrice=100000"
        if tipo_propiedad != 'Todos':
            url += f"&propertySubtypeId={tipo_propiedad.lower()}"

        # Realizar la solicitud GET a la URL de Fotocasa
        response = requests.get(url)

        # Parsear el contenido HTML de la respuesta
        soup = BeautifulSoup(response.content, 'html.parser')

        # Encontrar todos los elementos de anuncios de propiedades
        anuncios = soup.find_all('div', class_='re-Card')

        # Extraer información relevante de cada anuncio
        # Dentro del bucle que recorre los anuncios
        for anuncio in anuncios:
            titulo = anuncio.find('a', class_='re-Card-titleLink').text.strip()
            precio = anuncio.find('span', class_='re-Card-price').text.strip()
            descripcion = anuncio.find('div', class_='re-Card-description').text.strip()
            imagen_url = anuncio.find('img')['src']
            link = anuncio.find('a', class_='re-Card-titleLink')['href']
            
            # Imprimir los datos de cada anuncio para depuración
            print(f'Título: {titulo}')
            print(f'Precio: {precio}')
            print(f'Descripción: {descripcion}')
            print(f'URL de la imagen: {imagen_url}')
            print(f'Enlace: {link}')

    return render_template('fotocasa.html', resultados=resultados)





if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
