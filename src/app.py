from io import BytesIO
import pandas as pd
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request, redirect, send_file, url_for
import os
import requests
import database as db
from sparkpost import SparkPost

template_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
template_dir = os.path.join(template_dir, 'src', 'templates')

app = Flask(__name__, template_folder=template_dir)

SPARKPOST_API_KEY = '450dc7ec7fbc0ec5b1c1d9c9dd9b6d2e7ffa5ce7'  # Reemplazar con tu clave de API de SparkPost

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        asunto = request.form['asunto']  # Obtener el asunto del formulario
        mensaje = request.form['mensaje']
        
        try:
            # Crear un objeto SparkPost para enviar el correo electrónico
            sparkpost = SparkPost(SPARKPOST_API_KEY)

            # Enviar el correo electrónico utilizando la API de SparkPost
            response = sparkpost.transmissions.send(
                recipients=[{'address': 'alvaro.martin.salazar@iesciudadjardin.com'}],  # Cambia la dirección de correo
                content={
                    'from': email,
                    'subject': asunto,  # Utilizar el asunto proporcionado por el usuario
                    'text': f'Nombre: {nombre}\nEmail: {email}\nMensaje: {mensaje}'
                }
            )
            return redirect(url_for('contacto_exitoso'))  # Redirigir a una página de éxito
        except Exception as e:
            print('Error al enviar el correo electrónico:', e)
            return render_template('error_contacto.html')
    else:
        return render_template('contacto.html')

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

    # Pasar las URL de las imágenes a la plantilla
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

@app.route('/search', methods=['POST'])
def search():
    num_habitaciones = request.form.get('num-habitaciones')
    superficie = request.form.get('superficie')
    caracteristicas = request.form.getlist('caracteristicas[]')
    precio_min = request.form.get('precioMin')
    precio_max = request.form.get('precioMax')
    page = request.form.get('page', 1)

    # Construir la URL de búsqueda con los filtros
    base_url = "https://www.pisos.com/venta/pisos-sevilla_capital/"
    if "terraza" in caracteristicas:
        url = f"{base_url}terraza/"
        caracteristicas.remove("terraza")
    else:
        url = base_url

    if num_habitaciones and num_habitaciones != "todas":
        url += f"con-{num_habitaciones}-habitaciones/"
    if superficie and superficie != "todas":
        url += f"desde-{superficie}-m2/"
    if precio_min:
        url += f"desde-{precio_min}/"
    if precio_max:
        url += f"hasta-{precio_max}/"
    if caracteristicas:
        for caracteristica in caracteristicas:
            url += f"{caracteristica}/"
    url += f"{page}/"

    pisos_data = scrape_pisos(url)
    
    return jsonify(pisos_data)

def scrape_pisos(url):
    results = []
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')

    listings = soup.find_all('div', class_='ad-preview')

    for listing in listings:
        link = listing.find('a', class_='ad-preview__title')
        if link:
            href = link['href']
            complete_url = "https://www.pisos.com" + href

            description_element = listing.find('p', class_='ad-preview__description')
            description_text = description_element.text.strip() if description_element else "Descripción no disponible."

            max_length = 100
            if len(description_text) > max_length:
                description_text = description_text[:max_length] + "..."

            image_urls = []
            carousel_slides = listing.find_all('div', class_='carousel__main-photo carousel__main-photo--as-img')
            for slide in carousel_slides:
                picture_elements = slide.find_all('picture')
                for picture_element in picture_elements:
                    img_element = picture_element.find('img')
                    if img_element and 'data-src' in img_element.attrs:
                        image_urls.append(img_element['data-src'])

            image_urls_str = ', '.join(image_urls)

            price_element = listing.find('span', class_='ad-preview__price')
            price_text = price_element.text.strip() if price_element else "Precio no disponible"

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

            # Extraer la ubicación
            location_element = listing.find('p', class_='p-sm ad-preview__subtitle')
            location_text = location_element.text.strip() if location_element else "Ubicación no disponible"

            result = {
                'url': complete_url,
                'description': description_text,
                'image_urls': image_urls_str,
                'price': price_text,
                'rooms': rooms_text,
                'bathrooms': bathrooms_text,
                'size': size_text,
                'floor': floor_text,
                'location': location_text
            }
            results.append(result)

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

