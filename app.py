from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
import sqlite3
import smtplib
from email.mime.text import MIMEText
import os
import random
import time
import json
import requests  # для обратного геокодирования
from threading import Thread
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message


SMTP_EMAIL = "bot51384@gmail.com"
SMTP_PASSWORD = "kkyv asku gvvm eyrb"

app = Flask(__name__)
app.secret_key = "очень_секретный_ключ_сюда"

def send_confirmation_code(to_email, code):
    msg = MIMEText(f"Ваш код подтверждения: {code}")
    msg['Subject'] = 'Код подтверждения'
    msg['From'] = SMTP_EMAIL
    msg['To'] = to_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Ошибка отправки письма: {e}")

def delete_if_unverified(email):
    time.sleep(480)
    conn = sqlite3.connect("login.db")
    c = conn.cursor()
    c.execute("SELECT code FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    if result and result[0] != '0':
        c.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
    conn.close()

def init_db():
    conn = sqlite3.connect('login.db')
    c = conn.cursor()

    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        code TEXT DEFAULT '0'
    )''')

    # 🔐 Таблица карт
    c.execute('''CREATE TABLE IF NOT EXISTS calc (
        email TEXT PRIMARY KEY,
        card_number TEXT,
        card_cvv TEXT,
        card_expiry TEXT,
        confirm_code TEXT DEFAULT '0'
    )''')


    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template("raboty.html")

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['user']
    cart_key = f"cart_{email}"
    cart = session.get(cart_key, [])

    if not cart:
        return "Корзина пуста", 400

    all_items = load_items()
    cart_items = []
    total = 0

    for entry in cart:
        index = entry['index']
        quantity = entry['quantity']
        if isinstance(index, int) and 0 <= index < len(all_items):
            item = all_items[index]
            subtotal = item['price'] * quantity
            total += subtotal
            cart_items.append({
                'name': item['name'],
                'price': item['price'],
                'quantity': quantity,
                'subtotal': subtotal
            })

    # Получаем адрес из координат
    address_data = session.get(f"address_{email}")
    address_str = "Адрес не указан"
    if address_data:
        lat = address_data.get("lat")
        lng = address_data.get("lng")
        try:
            res = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"format": "json", "lat": lat, "lon": lng},
                headers={"User-Agent": "my-app"}
            )
            data = res.json()
            address_str = data.get("display_name", address_str)
        except Exception:
            address_str = "Не удалось определить адрес"

    # Формируем HTML-письмо
    email_body = "<h2>🛍️ Новый заказ</h2><ul style='font-size:16px;'>"
    for item in cart_items:
        email_body += f"<li><b>{item['name']}</b>: {item['price']} ₸ × {item['quantity']} = {item['subtotal']} ₸</li>"
    email_body += "</ul>"
    email_body += f"<p style='font-size:18px;'><b>Итог:</b> {total} ₸</p>"
    email_body += f"<p style='font-size:16px;'><b>Адрес доставки:</b> {address_str}</p>"

    # Настройки почты
    sender_email = "alenapodoinikova05@gmail.com"
    sender_password = "puyu pdue pjar jtyk"
    recipient_email = "alenapodoinikova05@gmail.com"

    msg = MIMEText(email_body, 'html', 'utf-8')
    msg['Subject'] = '🛒 Новый заказ с сайта'
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        session[cart_key] = []  # очищаем корзину
        return redirect(url_for('masterclass'))  # возвращаем на корзину
    except Exception as e:
        return f"Ошибка при отправке письма: {str(e)}", 500











@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = sqlite3.connect("login.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        if user:
            code = str(random.randint(100000, 999999))
            c.execute("UPDATE users SET code = ? WHERE email = ?", (code, email))
            conn.commit()
            conn.close()
            send_confirmation_code(email, code)
            return render_template("reset_confirm.html", email=email)
        conn.close()
        return "Пользователь не найден"
    return render_template("forgot_password.html")


@app.route('/reset_confirm', methods=['POST'])
def reset_confirm():
    email = request.form['email']
    code = request.form['code']
    conn = sqlite3.connect("login.db")
    c = conn.cursor()
    c.execute("SELECT code FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    if result and result[0] == code:
        conn.close()
        return render_template("reset_password.html", email=email)
    conn.close()
    return "Неверный код подтверждения"


@app.route('/reset_password', methods=['POST'])
def reset_password():
    email = request.form['email']
    password1 = request.form['password1']
    password2 = request.form['password2']
    if password1 != password2:
        return "Пароли не совпадают"

    conn = sqlite3.connect("login.db")
    c = conn.cursor()
    c.execute("UPDATE users SET password = ?, code = '0' WHERE email = ?", (password1, email))
    conn.commit()
    conn.close()
    return redirect(url_for('login'))










@app.route('/raboty')
def raboty():
    all_items = []
    if os.path.exists("Price.txt"):
        with open("Price.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            visible_lines = [line for line in lines if line.strip() and not line.startswith("=")]
            for visible_idx, line in enumerate(visible_lines):
                parts = line.strip().strip(";").split("-+")
                if len(parts) == 8:
                    name, size, material, price, image, timestamp, description, category = parts
                    all_items.append({
                        'index': visible_idx,
                        'name': name,
                        'size': size,
                        'material': material,
                        'price': price,
                        'image': image,
                        'description': description,
                        'timestamp': timestamp,
                        'category': category
                    })

    sorted_items = sorted(all_items, key=lambda x: x['timestamp'], reverse=True)
    newest_items = sorted_items[:4]
    return render_template("raboty.html", items=sorted_items, newest=newest_items)




@app.route('/primery')
def primery():
    return render_template("primery.html")


def load_items():
    items = []
    if os.path.exists("Price.txt"):
        with open("Price.txt", "r", encoding="utf-8") as f:
            visible_lines = [line for line in f if line.strip() and not line.startswith("=")]
            for idx, line in enumerate(visible_lines):
                parts = line.strip().strip(";").split("-+")
                if len(parts) == 8:
                    name, size, material, price, image, timestamp, description, category = parts
                    items.append({
                        'index': idx,
                        'name': name,
                        'size': size,
                        'material': material,
                        'price': int(price),
                        'image': image,
                        'timestamp': timestamp,
                        'description': description,
                        'category': category
                    })
    return items











@app.route('/masterclass')
def masterclass():
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['user']
    cart_key = f"cart_{email}"
    cart_data = session.get(cart_key, [])

    if not isinstance(cart_data, list):
        cart_data = []

    all_items = load_items()
    cart_items = []
    total = 0

    for entry in cart_data:
        if isinstance(entry, int):
            entry = {'index': entry, 'quantity': 1}
        elif not (isinstance(entry, dict) and 'index' in entry and 'quantity' in entry):
            continue

        index = entry['index']
        quantity = entry['quantity']
        if isinstance(index, int) and 0 <= index < len(all_items):
            item = all_items[index].copy()
            item['quantity'] = quantity
            item['index'] = index
            total += item['price'] * quantity
            cart_items.append(item)

    return render_template("masterclass.html", cart_items=cart_items, total=total)


@app.route('/reset_cart')
def reset_cart():
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['user']
    cart_key = f"cart_{email}"
    session[cart_key] = []
    return redirect(url_for('masterclass'))



@app.route('/add_to_cart/<int:index>', methods=['POST'])
def add_to_cart(index):
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['user']
    cart_key = f"cart_{email}"

    visible_items = [line for line in open("Price.txt", encoding="utf-8") if line.strip() and not line.startswith("=")]

    if 0 <= index < len(visible_items):
        cart = session.get(cart_key, [])

        # преобразуем все старые записи в словари
        new_cart = []
        found = False
        for entry in cart:
            if isinstance(entry, int):
                entry = {'index': entry, 'quantity': 1}
            if entry['index'] == index:
                entry['quantity'] += 1
                found = True
            new_cart.append(entry)

        if not found:
            new_cart.append({'index': index, 'quantity': 1})

        session[cart_key] = new_cart
        session.modified = True

    return redirect(url_for('raboty'))



@app.route('/change_quantity/<int:index>', methods=['POST'])
def change_quantity(index):
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['user']
    cart_key = f"cart_{email}"

    action = request.form['action']
    cart = session.get(cart_key, [])

    for entry in cart:
        if isinstance(entry, int):
            entry = {'index': entry, 'quantity': 1}
        if entry['index'] == index:
            if action == 'increase':
                entry['quantity'] += 1
            elif action == 'decrease' and entry['quantity'] > 1:
                entry['quantity'] -= 1
            break

    session[cart_key] = cart
    session.modified = True
    return redirect(url_for('masterclass'))


@app.route('/remove_from_cart/<int:index>', methods=['POST'])
def remove_from_cart(index):
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['user']
    cart_key = f"cart_{email}"

    cart = session.get(cart_key, [])
    new_cart = [entry for entry in cart if not (isinstance(entry, dict) and entry.get('index') == index)]
    session[cart_key] = new_cart
    session.modified = True
    return redirect(url_for('masterclass'))










@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == 'siteadministrator@gmail.com' and password == 'sitebot12345':
            session['user'] = email
            session['admin'] = True
            return redirect(url_for('admin'))

        conn = sqlite3.connect("login.db")
        c = conn.cursor()
        c.execute("SELECT password, code FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user:
            stored_password, code = user
            if stored_password == password:
                if code == '0':
                    session['user'] = email
                    session['admin'] = False
                    return redirect(url_for('index'))
                else:
                    return "Подтвердите аккаунт через код"
            else:
                return "Неверный пароль"
        return "Такого аккаунта не существует"
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        code = str(random.randint(100000, 999999))
        conn = sqlite3.connect("login.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password, code) VALUES (?, ?, ?)", (email, password, code))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Пользователь с таким email уже существует"
        finally:
            conn.close()

        send_confirmation_code(email, code)
        Thread(target=delete_if_unverified, args=(email,)).start()
        return render_template("confirm.html", email=email)
    return render_template("register.html")

@app.route('/confirm', methods=['POST'])
def confirm():
    email = request.form['email']
    input_code = request.form['code']
    conn = sqlite3.connect("login.db")
    c = conn.cursor()
    c.execute("SELECT code FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    if result and result[0] == input_code:
        c.execute("UPDATE users SET code = '0' WHERE email = ?", (email,))
        conn.commit()
        session['user'] = email
        session['admin'] = False
        conn.close()
        return redirect(url_for('index'))
    else:
        conn.close()
        return "Неверный код или аккаунт был удалён"

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('admin'):
        return redirect(url_for('admin'))

    email = session['user']

    # Получаем данные карты
    conn = sqlite3.connect("login.db")
    c = conn.cursor()
    c.execute("SELECT card_number, card_cvv, card_expiry FROM calc WHERE email = ?", (email,))
    card_row = c.fetchone()
    conn.close()

    card_data = None
    if card_row:
        card_data = {
            'card_number': card_row[0],
            'card_cvv': card_row[1],
            'card_expiry': card_row[2]
        }

    # Получаем координаты из сессии
    address_data = session.get(f"address_{email}")
    address_str = None

    if address_data:
        lat = address_data.get("lat")
        lng = address_data.get("lng")

        try:
            res = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"format": "json", "lat": lat, "lon": lng},
                headers={"User-Agent": "my-app"}
            )
            data = res.json()
            address_str = data.get("display_name")
        except Exception as e:
            address_str = "Не удалось определить адрес"

    return render_template("profile.html", email=email, card_data=card_data, address_str=address_str)




@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))

    items = []
    if os.path.exists("Price.txt"):
        with open("Price.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            for idx, line in enumerate(lines):
                if line.strip():
                    inactive = line.startswith("=")
                    clean_line = line[1:] if inactive else line
                    parts = clean_line.strip().strip(";").split("-+")
                    
                    if len(parts) == 8:
                        name, size, material, price, image, timestamp, description, category = parts
                        items.append({
                            'name': name,
                            'size': size,
                            'material': material,
                            'price': price,
                            'image': image,
                            'inactive': inactive,
                            'index': idx,
                            'description': description,
                            'timestamp': timestamp,
                            'category': category  # ⬅️ новая строка
                        })

    return render_template("admin.html", items=items)


@app.route('/toggleitem', methods=['POST'])
def toggleitem():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    index = data.get('index')

    if index is None:
        return jsonify({'error': 'Missing index'}), 400

    try:
        index = int(index)
    except ValueError:
        return jsonify({'error': 'Invalid index'}), 400

    if os.path.exists("Price.txt"):
        with open("Price.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()

        if 0 <= index < len(lines):
            line = lines[index].lstrip('=')
            if lines[index].startswith('='):
                lines[index] = line
            else:
                lines[index] = '=' + line

            with open("Price.txt", "w", encoding="utf-8") as f:
                f.writelines(lines)

            return jsonify({'success': True})

    return jsonify({'error': 'Item not found'}), 404

@app.route('/deleteitem', methods=['POST'])
def deleteitem():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    index = data.get('index')

    try:
        index = int(index)
    except:
        return jsonify({'error': 'Invalid index'}), 400

    if os.path.exists("Price.txt"):
        with open("Price.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()

        if 0 <= index < len(lines):
            del lines[index]
            with open("Price.txt", "w", encoding="utf-8") as f:
                f.writelines(lines)
            return jsonify({'success': True})

    return jsonify({'error': 'Not found'}), 404

@app.route('/additem', methods=['POST'])
def additem():
    if not session.get('admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    size = request.form['size']
    material = request.form['material']
    price = request.form['price']
    category = request.form.get('category', 'Без категории')  # ⬅️ новая строка
    image = request.files['image']

    if image and image.filename != '':
        filename = secure_filename(image.filename)
        img_path = os.path.join('static', 'img', filename)
        image.save(img_path)
    else:
        return "Ошибка загрузки изображения"

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    description = request.form.get('description', '').replace('\n', ' ').replace(';', '').strip()

    # Сохраняем с категорией
    entry = f"{name}-+{size}-+{material}-+{price}-+{filename}-+{timestamp}-+{description}-+{category};\n"

    with open("Price.txt", "a", encoding="utf-8") as f:
        f.write(entry)

    return redirect(url_for('admin'))


@app.route('/item/<int:index>')
def item_detail(index):
    if os.path.exists("Price.txt"):
        with open("Price.txt", "r", encoding="utf-8") as f:
            visible_lines = [line for line in f if line.strip() and not line.startswith("=")]

        if 0 <= index < len(visible_lines):
            parts = visible_lines[index].strip().strip(";").split("-+")
            if len(parts) == 8:
                name, size, material, price, image, timestamp, description, category = parts
                item = {
                    'index': index,
                    'name': name,
                    'size': size,
                    'material': material,
                    'price': price,
                    'image': image,
                    'description': description,
                    'timestamp': timestamp,
                    'category': category
                }
                return render_template("item.html", item=item)

    return "Товар не найден", 404



@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
