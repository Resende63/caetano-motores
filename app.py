import io
import json
import sqlite3
from flask import Flask, flash, redirect, render_template, request, send_file, url_for

app = Flask(__name__)
app.secret_key = "caetanos_motores_chave_secreta"

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
    
    clientes = cursor.execute("SELECT * FROM clientes ORDER BY id DESC").fetchall()
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
        conn.cursor().execute(
            "INSERT INTO clientes (nome, telefone, equipamento) VALUES (?, ?, ?)",
            (nome, telefone, equipamento)
        )
        conn.commit()
        
    flash("Cliente cadastrado com sucesso!")
    return redirect(url_for("painel"))

@app.route("/excluir_cliente/<int:id>")
def excluir_cliente(id):
    with conectar_banco() as conn:
        conn.cursor().execute("DELETE FROM clientes WHERE id = ?", (id,))
        conn.commit()
    flash("Cliente removido.")
    return redirect(url_for("painel"))

@app.route("/agendar_servico", methods=["POST"])
def agendar_servico():
    cliente_id = request.form.get("cliente_id")
    data = request.form.get("data")
    servico = request.form.get("servico")
    
    with conectar_banco() as conn:
        conn.cursor().execute(
            "INSERT INTO agendamentos (cliente_id, data, servico) VALUES (?, ?, ?)",
            (cliente_id, data, servico)
        )
        conn.commit()
        
    flash("Agendamento realizado!")
    return redirect(url_for("painel"))

@app.route("/concluir_agendamento/<int:id>")
def concluir_agendamento(id):
    with conectar_banco() as conn:
        conn.cursor().execute("UPDATE agendamentos SET status = 'Concluído' WHERE id = ?", (id,))
        conn.commit()
    flash("Serviço marcado como concluído!")
    return redirect(url_for("painel"))

@app.route("/excluir_agendamento/<int:id>")
def excluir_agendamento(id):
    with conectar_banco() as conn:
        conn.cursor().execute("DELETE FROM agendamentos WHERE id = ?", (id,))
        conn.commit()
    flash("Agendamento excluído.")
    return redirect(url_for("painel"))

@app.route("/lancar_caixa", methods=["POST"])
def lancar_caixa():
    tipo = request.form.get("tipo")
    descricao = request.form.get("descricao")
    valor_str = request.form.get("valor", "").replace(",", ".")
    valor = float(valor_str) if valor_str else 0.0
    data = request.form.get("data")
    
    with conectar_banco() as conn:
        conn.cursor().execute(
            "INSERT INTO caixa (tipo, descricao, valor, data) VALUES (?, ?, ?, ?)",
            (tipo, descricao, valor, data)
        )
        conn.commit()
        
    flash("Lançamento financeiro realizado!")
    return redirect(url_for("painel"))

@app.route("/excluir_caixa/<int:id>")
def excluir_caixa(id):
    with conectar_banco() as conn:
        conn.cursor().execute("DELETE FROM caixa WHERE id = ?", (id,))
        conn.commit()
    flash("Lançamento removido do caixa.")
    return redirect(url_for("painel"))

@app.route("/backup")
def fazer_backup():
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
