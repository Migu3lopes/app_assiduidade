from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

# Configuração do Flask
app = Flask(__name__)
app.secret_key = "chave_secreta"  # Necessário para gerenciar sessões de usuário

# Caminho do banco de dados
DB_PATH = "assiduidade.db"

# Criar o banco de dados e tabelas se não existirem
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Criar tabela de atletas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )
    """)

    # Criar tabela de sessões de treino
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessoes_treino (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT UNIQUE NOT NULL
        )
    """)

    # Criar tabela de assiduidade
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assiduidade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            atleta_id INTEGER,
            sessao_id INTEGER,
            status TEXT CHECK(status IN ('Presente', 'Falta I.', 'Falta J.')),
            FOREIGN KEY(atleta_id) REFERENCES atletas(id),
            FOREIGN KEY(sessao_id) REFERENCES sessoes_treino(id),
            UNIQUE(atleta_id, sessao_id)
        )
    """)

    conn.commit()
    conn.close()

# Inicializar banco de dados na primeira execução
init_db()

# Página de Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        if usuario == "admin" and senha == "1234":
            session["user"] = usuario
            return redirect(url_for("index"))  # Redireciona para a página principal

        return render_template("login.html", erro="Usuário ou senha inválidos.")

    return render_template("login.html")

# Logout (Sair)
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# Página Principal (Protegida)
@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))  # Se não estiver logado, vai para login

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM atletas")
    atletas = cursor.fetchall()

    conn.close()
    return render_template("index.html", atletas=atletas)


# Registrar Assiduidade
@app.route("/registrar", methods=["POST"])
def registrar():
    if "user" not in session:
        return redirect(url_for("login"))  # Proteção extra

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    data_treino = request.form.get("data_treino")

    # Criar sessão de treino com a data selecionada se não existir
    cursor.execute("SELECT id FROM sessoes_treino WHERE data = ?", (data_treino,))
    sessao = cursor.fetchone()

    if not sessao:
        cursor.execute("INSERT INTO sessoes_treino (data) VALUES (?)", (data_treino,))
        conn.commit()
        sessao_id = cursor.lastrowid
    else:
        sessao_id = sessao[0]

    # Registrar assiduidade dos atletas
    for key, value in request.form.items():
        if key.startswith("assiduidade_"):
            atleta_id = key.split("_")[1]

            cursor.execute("""
                INSERT OR REPLACE INTO assiduidade (atleta_id, sessao_id, status)
                VALUES (?, ?, ?)
            """, (atleta_id, sessao_id, value))

    conn.commit()
    conn.close()

    return redirect(url_for("index"))

# Página do Histórico
@app.route("/historico")
def historico():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.nome, 
               SUM(CASE WHEN ass.status = 'Presente' THEN 1 ELSE 0 END) AS presencas,
               SUM(CASE WHEN ass.status = 'Falta I.' THEN 1 ELSE 0 END) AS faltas_injustificadas,
               SUM(CASE WHEN ass.status = 'Falta J.' THEN 1 ELSE 0 END) AS faltas_justificadas,
               COUNT(DISTINCT ass.sessao_id) AS total_treinos
        FROM atletas a
        LEFT JOIN assiduidade ass ON a.id = ass.atleta_id
        GROUP BY a.nome
    """)

    historico_registros = []
    for row in cursor.fetchall():
        nome = row["nome"]
        presencas = row["presencas"] if row["presencas"] else 0
        faltas_injustificadas = row["faltas_injustificadas"] if row["faltas_injustificadas"] else 0
        faltas_justificadas = row["faltas_justificadas"] if row["faltas_justificadas"] else 0
        total_treinos = row["total_treinos"] if row["total_treinos"] else 0

        pontos = presencas + (faltas_justificadas * 0.50)
        minutos = presencas * 60
        percentagem = (pontos / total_treinos * 100) if total_treinos > 0 else 0

        historico_registros.append({
            "nome": nome,
            "presencas": presencas,
            "faltas_injustificadas": faltas_injustificadas,
            "faltas_justificadas": faltas_justificadas,
            "total_treinos": total_treinos,
            "minutos": minutos,
            "percentagem": round(percentagem, 2)
        })

    conn.close()
    return render_template("historico.html", historico_registros=historico_registros)

# Iniciar o servidor Flask
if __name__ == "__main__":
    app.run(debug=True)

