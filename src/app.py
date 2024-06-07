import urllib, urllib.request
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request, redirect, session, url_for
from flask_mail import Mail, Message
import os
import requests
import database as db

template_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
template_dir = os.path.join(template_dir, 'src', 'templates')

app = Flask(__name__, template_folder=template_dir)

# Configuración para Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'pruebasmail.alvaro@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('PASSWORD')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

@app.route('/')
def home():
    cursor = db.database.cursor()
    cursor.execute("SELECT * FROM usuarios")
    myresult = cursor.fetchall()
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
        cursor = db.database.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        if user:
            return render_template('busqueda.html')
        else:
            return render_template('login.html', error="Credenciales incorrectas. Inténtalo de nuevo.")
    else:
        return render_template('login.html')

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    return render_template('index.html')

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == ['POST']:
        nombre = request.form['nombre']
        email = request.form['email']
        mensaje = request.form['mensaje']
        msg = Message(subject='Mensaje de contacto desde HogarData',
                      recipients=['alvaromartinsalazar@gmail.com'],
                      body=f'Nombre: {nombre}\nEmail: {email}\nMensaje: {mensaje}')
        try:
            mail.send(msg)
            return redirect(url_for('contacto_exitoso'))
        except Exception as e:
            print('Error al enviar el correo electrónico:', e)
            return 'Error al enviar el correo electrónico. Inténtalo de nuevo más tarde.'
    else:
        return render_template('contacto.html')

@app.route('/perfil')
def perfil():
    if 'user_id' in session:
        return render_template('perfil.html')
    return redirect(url_for('login'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' in session:
        user_id = session['user_id']
        email = request.form['email']
        password = request.form['password']
        cursor = db.database.cursor()
        cursor.execute("UPDATE usuarios SET email = %s, password = %s WHERE id = %s", (email, password, user_id))
        db.database.commit()
        cursor.close()
        return redirect(url_for('perfil'))
    return redirect(url_for('login'))

@app.route('/search', methods=['POST'])
def search():
    num_habitaciones = request.form.get('num-habitaciones')
    url = "https://www.pisos.com/venta/pisos-sevilla_capital/"
    pisos_data = scrape_pisos(url)
    return jsonify(pisos_data)

def scrape_pisos(url):
    """Scrapes pisos.com for apartment listings and descriptions.

    Args:
        url (str): The URL of the pisos.com listings page.

    Returns:
        list: A list of dictionaries containing scraped URLs, descriptions, image URLs, and prices.
    """
    results = []
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html5lib')

    # Find all listings
    listings = soup.find_all('div', class_='ad-preview')  # Adjust class if necessary

    for listing in listings:
        link = listing.find('a', class_='ad-preview__title')
        if link:
            href = link['href']
            complete_url = "https://www.pisos.com" + href

            description_element = listing.find('p', class_='ad-preview__description')
            if description_element:
                description_text = description_element.text.strip()
            else:
                description_text = "Descripción no disponible."

            # Truncate description if it's too long
            max_length = 100  # You can set this to the desired length
            if len(description_text) > max_length:
                description_text = description_text[:max_length] + "..."

            # Handle the image extraction more robustly
            image_url = ""
            picture_element = listing.find('picture')
            if picture_element:
                img_element = picture_element.find('img')
                if img_element and 'src' in img_element.attrs:
                    image_url = img_element['src']

            # Find price element
            price_element = listing.find('span', class_='ad-preview__price')
            price_text = price_element.text.strip() if price_element else "Precio no disponible"

            results.append({
                "url": complete_url,
                "description": description_text,
                "image_url": image_url,
                "price": price_text
            })

    return results






if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
