import urllib, urllib.request
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for
import os
import database as db

template_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
template_dir = os.path.join(template_dir, 'src', 'templates')

app = Flask(__name__, template_folder = template_dir)

"""url = 'https://www.pisos.com/viviendas/sevilla/'
html = urllib.request.urlopen(url)
soup = BeautifulSoup(html)
url_principal='https://www.pisos.com'

tags=soup('div')
zonas = soup.find(class_='zoneList')

for tag in tags:
    tags2=zonas('a')
    for tag2 in tags2:
        enlaces_zonas=tag2.get('href')
        urls=url_principal+enlaces_zonas
        print(urls)"""


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
    return render_template('login.html', data=insertObject)

    
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
            return render_template('index.html')
        else:
            # Si las credenciales son incorrectas, puedes renderizar nuevamente el formulario de inicio de sesión con un mensaje de error
            return render_template('login.html', error="Credenciales incorrectas. Inténtalo de nuevo.")
    else:
        # Si la solicitud es GET, muestra el formulario de inicio de sesión
        return render_template('login.html')
    

if __name__ == '__main__':
    app.run(debug=True, port=5000)