from io import BytesIO
import mysqlx
import pandas as pd
import urllib, urllib.request
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request, redirect, send_file, session, url_for
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

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = db.database.cursor()
    cursor.execute("SELECT email, password FROM usuarios WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        new_email = request.form['email']
        new_password = request.form['password']
        cursor.execute("UPDATE usuarios SET email=%s, password=%s WHERE id=%s", (new_email, new_password, user_id))
        db.database.commit()  # Deberías confirmar los cambios en la base de datos aquí
        return redirect(url_for('perfil'))

    return render_template('perfil.html', email=user[0], password=user[1])



@app.route('/search', methods=['POST'])
def search():
    num_habitaciones = request.form.get('num-habitaciones')
    superficie = request.form.get('superficie')
    caracteristicas = request.form.getlist('caracteristicas[]')
    page = request.form.get('page', 1)  # Obtener el número de página, por defecto es 1

    # Construir la URL de búsqueda con los filtros
    url = "https://www.pisos.com/venta/pisos-sevilla_capital/"
    if num_habitaciones and num_habitaciones != "todas":
        url += f"con-{num_habitaciones}-habitaciones/"
    if superficie and superficie != "todas":
        url += f"desde-{superficie}-m2/"
    if caracteristicas:
        for caracteristica in caracteristicas:
            url += f"{caracteristica}/"
    url += f"{page}/"

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
            image_urls = []
            picture_elements = listing.find_all('picture')
            for picture_element in picture_elements:
                img_element = picture_element.find('img')
                if img_element and 'src' in img_element.attrs:
                    image_urls.append(img_element['src'])

            # Join image URLs into a single string separated by commas
            image_urls_str = ', '.join(image_urls)

            # Find price element
            price_element = listing.find('span', class_='ad-preview__price')
            price_text = price_element.text.strip() if price_element else "Precio no disponible"

            # Extract additional information: rooms, bathrooms, size, floor
            rooms_text = "N/A"
            bathrooms_text = "N/A"
            size_text = "N/A"
            floor_text = "N/A"

            details = listing.find_all('p', class_='ad-preview__char')
            for detail in details:
                text = detail.text.strip()
                if 'habs.' in text:
                    rooms_text = text.split()[0]
                elif 'baños' in text:
                    bathrooms_text = text.split()[0]
                elif 'm²' in text:
                    size_text = text.split()[0]
                elif 'planta' in text:
                    floor_text = text.split()[0]

            results.append({
                "url": complete_url,
                "description": description_text,
                "image_urls": image_urls_str,
                "price": price_text,
                "rooms": rooms_text,
                "bathrooms": bathrooms_text,
                "size": size_text,
                "floor": floor_text
            })

    return results




@app.route('/export', methods=['POST'])
def export():
    try:
        # Obtener los resultados de la búsqueda desde el JSON de la solicitud
        search_results = request.json.get('results', [])

        if not search_results:
            raise ValueError("No se encontraron resultados de búsqueda para exportar.")

        # Crear un DataFrame con los resultados de la búsqueda
        df = pd.DataFrame(search_results)
        print("Datos del DataFrame:", df)

        # Crear un buffer para guardar el Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Resultados')
        output.seek(0)

        print("Archivo Excel generado exitosamente.")
        
        # Enviar el archivo Excel
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name='resultados_busqueda.xlsx')
    except Exception as e:
        print(f"Error al exportar a Excel: {e}")
        return jsonify({"error": "No se pudo exportar a Excel"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)