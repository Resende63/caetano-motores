from flask import Flask, request, jsonify, render_template
from werkzeug.security import generate_password_hash
import re
import os  # Permite verificar as pastas do sistema

# Identifica automaticamente se a pasta é 'Modelos' ou 'templates'
pasta_visual = 'Modelos' if os.path.exists('Modelos') else 'templates'

# Se você já tiver uma linha "app = Flask..." mais abaixo, substitua por esta:
app = Flask(__name__, template_folder=pasta_visual)

DATABASE = "oficina.db"

def conectar_banco():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_banco():
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL,
                equipamento TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                data TEXT NOT NULL,
                servico TEXT NOT NULL,
                status TEXT DEFAULT 'Pendente',
                FOREIGN KEY(cliente_id) REFERENCES clientes(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS caixa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                data TEXT NOT NULL
            )
        """)
        conn.commit()

inicializar_banco()

@app.route("/")
def painel():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    clientes = cursor.execute("SELECT * FROM clientes").fetchall()
    caixa = cursor.execute("SELECT * FROM caixa ORDER BY id DESC").fetchall()
    
    agendamentos = cursor.execute("""
        SELECT agendamentos.*, clientes.nome as nome_cliente 
        FROM agendamentos 
        LEFT JOIN clientes ON agendamentos.cliente_id = clientes.id
        ORDER BY data ASC
    """).fetchall()
    
    entradas_req = cursor.execute("SELECT SUM(valor) FROM caixa WHERE tipo='Entrada'").fetchone()
    entradas = entradas_req[0] if entradas_req[0] is not None else 0
    
    saidas_req = cursor.execute("SELECT SUM(valor) FROM caixa WHERE tipo='Saida'").fetchone()
    saidas = saidas_req[0] if saidas_req[0] is not None else 0
    
    saldo = entradas - saidas
    conn.close()
    
    return render_template("painel.html", clientes=clientes, agendamentos=agendamentos, caixa=caixa, saldo=saldo)

@app.route("/cadastrar_cliente", methods=["POST"])
def cadastrar_cliente():
    nome = request.form.get("nome")
    telefone = request.form.get("telefone")
    equipamento = request.form.get("equipamento")
    
    with conectar_banco() as conn:
        conn.cursor().execute("INSERT INTO clientes (nome, telefone, equipamento) VALUES (?, ?, ?)", (nome, telefone, equipamento))
        conn.commit()
        
    flash("Cliente cadastrado com sucesso!")
    return redirect(url_for("painel"))

@app.route("/agendar_servico", methods=["POST"])
def agendar_servico():
    cliente_id = request.form.get("cliente_id")
    data = request.form.get("data")
    servico = request.form.get("servico")
    
    with conectar_banco() as conn:
        conn.cursor().execute("INSERT INTO agendamentos (cliente_id, data, servico) VALUES (?, ?, ?)", (cliente_id, data, servico))
        conn.commit()
        
    flash("Agendamento realizado!")
    return redirect(url_for("painel"))

@app.route("/lancar_caixa", methods=["POST"])
def lancar_caixa():
    tipo = request.form.get("tipo")
    descricao = request.form.get("descricao")
    valor = float(request.form.get("valor", 0))
    data = request.form.get("data")
    
    with conectar_banco() as conn:
        conn.cursor().execute("INSERT INTO caixa (tipo, descricao, valor, data) VALUES (?, ?, ?, ?)", (tipo, descricao, valor, data))
        conn.commit()
        
    flash("Lançamento financeiro realizado!")
    return redirect(url_for("painel"))

@app.route("/backup")
def fazer_backup():
    import io
    import json
    from flask import send_file
    
    conn = conectar_banco()
    cursor = conn.cursor()
    
    backup_data = {
        "clientes": [dict(r) for r in cursor.execute("SELECT * FROM clientes").fetchall()],
        "agendamentos": [dict(r) for r in cursor.execute("SELECT * FROM agendamentos").fetchall()],
        "caixa": [dict(r) for r in cursor.execute("SELECT * FROM caixa").fetchall()]
    }
    conn.close()
    
    json_str = json.dumps(backup_data, ensure_ascii=False, indent=4)
    file_object = io.BytesIO(json_str.encode('utf-8'))
    
    return send_file(
        file_object,
        mimetype='application/json',
        as_attachment=True,
        download_name='backup_caetano_motores.json'
    )


class Port:
    def __init__(self, host="127.0.0.1", port=0, timeout=3.0, buffer_size=4096):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.buffer_size = buffer_size
        self._socket = None
        self._connected = False

    def open(self):
        if self._socket is not None:
            return self

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.timeout)
        if self.port:
            self._socket.bind((self.host, self.port))
        return self

    def connect(self, host=None, port=None):
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port

        if self._socket is None:
            self.open()

        self._socket.connect((self.host, self.port))
        self._connected = True
        return self

    def listen(self, host=None, port=None, backlog=5):
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port

        if self._socket is None:
            self.open()

        self._socket.bind((self.host, self.port))
        self._socket.listen(backlog)
        self._connected = True
        return self

    def accept(self):
        if self._socket is None:
            raise ConnectionError("Port not opened.")

        client_socket, address = self._socket.accept()
        return client_socket, address

    def write(self, data):
        if self._socket is None:
            raise ConnectionError("Port not opened.")

        if isinstance(data, str):
            data = data.encode("utf-8")

        if not data:
            return 0

        return self._socket.sendall(data)

    def read(self, size=None):
        if self._socket is None:
            raise ConnectionError("Port not opened.")

        if size is None:
            size = self.buffer_size

        return self._socket.recv(size)

    def readline(self, size=None):
        if self._socket is None:
            raise ConnectionError("Port not opened.")

        if size is None:
            size = self.buffer_size

        buffer = bytearray()
        while True:
            chunk = self._socket.recv(1)
            if not chunk:
                break
            buffer.extend(chunk)
            if chunk == b"\n" or len(buffer) >= size:
                break
        return bytes(buffer)

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._connected = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __repr__(self):
        return f"Port(host={self.host!r}, port={self.port!r}, connected={self._connected})"


import socket

if __name__ == "__main__":
    # Corrigido de 'porr' para 'port' com apenas um r
    app.run(host='0.0.0.0', port=5000, debug=False)
