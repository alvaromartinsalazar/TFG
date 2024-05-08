import urllib, urllib.request
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, session, url_for
from flask_mail import Mail, Message
import os
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
    
@app.route('/index', methods=['GET', 'POST'])
def web():
    enlaces_principales=[]
    enlaces_secundarios=[]
    if request.method == 'POST':

        url = request.form['web']

        # Verificar si la URL tiene el esquema (http:// o https://)
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url  # Agregar el esquema http:// si no está presente

        try:
            html = urllib.request.urlopen(url)
            soup = BeautifulSoup(html, 'html.parser')

            tags = soup.find_all('a')

            print('Enlaces en la página principal: \r\n')

            for tag in tags:
                enlaces_principales.append({'texto': tag.contents[0], 'url': tag.get('href')})

            print('\r\n Enlaces en las páginas secundarias: \r\n')

            for tag in tags:
                enlaces_secundarios.append({'url': newtag.get('href')})
                print('Accediendo a las páginas de la web', enlaces_secundarios)
                try:
                    if enlaces_secundarios and (enlaces_secundarios.startswith('http://') or enlaces_secundarios.startswith('https://')):
                        html2 = urllib.request.urlopen(enlaces_secundarios)
                    else:
                        if enlaces_secundarios:
                            html2 = urllib.request.urlopen(url + enlaces_secundarios)
                        else:
                            continue  # Ignorar enlaces nulos
                    soup2 = BeautifulSoup(html2, 'html.parser')
                    newtags = soup2.find_all('a')
                    if len(newtags) > 0:
                        print(len(newtags), 'enlaces: ')
                        for newtag in newtags:
                            print(newtag.get('href'))
                    else:
                        print('No hay más enlaces')
                except Exception as e:
                    print('Algo ha fallado:', e)

        except Exception as e:
            print('Error al abrir la URL:', e)

    return render_template('index.html', titulo1="Enlaces principales:", enlaces_principales=enlaces_principales, titulo2="Enlaces secundarios:", enlaces_secundarios=enlaces_secundarios)


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

if __name__ == '__main__':
    app.run(debug=True, port=5000)