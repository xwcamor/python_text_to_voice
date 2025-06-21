from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_mysqldb import MySQL
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from gtts import gTTS
from datetime import timedelta
import os
import uuid
import threading
import time
import config

app = Flask(__name__)
app.config.from_object(config)

# Expiración automática: 10 minutos
app.permanent_session_lifetime = timedelta(minutes=10)

# Configurar sesión
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Configurar conexión MySQL
mysql = MySQL(app)

AUDIO_FOLDER = "static"

# ============ UTILIDAD ============
def eliminar_archivo_despues(filename, segundos):
    time.sleep(segundos)
    if os.path.exists(filename):
        os.remove(filename)
        print(f"🗑️ Archivo eliminado: {filename}")

# ============ RUTAS ============

@app.route("/")
def home():
    if "usuario" in session:
        return render_template("index.html", usuario=session["usuario"])
    else:
        flash("Tu sesión ha expirado. Inicia sesión nuevamente.", "warning")
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        contraseña = request.form["contraseña"]

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        usuario = cur.fetchone()

        if usuario:
            if check_password_hash(usuario[3], contraseña):
                if usuario[4]:  # Campo "activo"
                    flash("Tu cuenta ya está en uso en otro dispositivo.", "danger")
                    return redirect(url_for("login"))

                # Marcar como activo
                cur.execute("UPDATE usuarios SET activo = 1 WHERE email = %s", (email,))
                mysql.connection.commit()
                cur.close()

                session.permanent = True
                session["usuario"] = usuario[1]
                session["email"] = usuario[2]
                flash("Inicio de sesión exitoso", "success")
                return redirect(url_for("home"))
            else:
                flash("Contraseña incorrecta", "danger")
        else:
            flash("Correo no registrado", "warning")
        cur.close()

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        contraseña = generate_password_hash(request.form["contraseña"])

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        existe = cur.fetchone()

        if existe:
            flash("Este email ya está registrado", "warning")
            return redirect(url_for("register"))

        cur.execute("INSERT INTO usuarios (nombre, email, contraseña, activo) VALUES (%s, %s, %s, 0)",
                    (nombre, email, contraseña))
        mysql.connection.commit()
        cur.close()
        flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/logout")
def logout():
    if "email" in session:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE usuarios SET activo = 0 WHERE email = %s", (session["email"],))
        mysql.connection.commit()
        cur.close()

    session.clear()
    flash("Sesión cerrada", "info")
    return redirect(url_for("login"))

# ============ VOZ (gTTS) ============

@app.route("/speak", methods=["POST"])
def speak():
    if "usuario" not in session:
        return jsonify({"error": "No autorizado"}), 403

    text = request.form.get("text")
    lang = request.form.get("lang", "es")

    if not text:
        return jsonify({"error": "Texto vacío"}), 400

    filename = f"{AUDIO_FOLDER}/audio_{uuid.uuid4().hex}.mp3"

    try:
        tts = gTTS(text=text, lang=lang)
        tts.save(filename)
        threading.Thread(target=eliminar_archivo_despues, args=(filename, 30)).start()
        return jsonify({"url": "/" + filename})
    except Exception as e:
        print("❌ Error al generar audio:", e)
        return jsonify({"error": "Error interno"}), 500

@app.route("/descargar")
def descargar():
    ruta = request.args.get("archivo")
    if ruta and os.path.exists(ruta):
        return send_file(ruta, as_attachment=True)
    return "Archivo no encontrado", 404

# ============ INICIO ============

if __name__ == "__main__":
    app.run(debug=True)





