import os


def criar_estrutura_projeto():
    # Definindo a estrutura de pastas e arquivos
    estrutura = {
        'templates': [
            'base.html',
            'index.html',
            'cardapio.html',
            'admin_pedidos.html',
            'admin_caixa.html',
            'financeiro.html',
        ],
        'static': {'css': ['style.css'], 'js': ['script.js']},
    }

    print('🚀 Iniciando a criação da estrutura do Lanchefy...\n')

    # Criando arquivos principais na raiz
    arquivos_raiz = {
        'database.py': """from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
""",
        'whatsapp.py': """import urllib.parse

def gerar_mensagem_whatsapp(pedido):
    status_emojis = {
        'Recebido': '📥', 'Em Preparo': '👨‍🍳', 'Saiu para Entrega': '🛵',
        'Pronto para Retirada': '🛍️', 'Concluido': '✅', 'Cancelado': '❌'
    }
    emoji = status_emojis.get(pedido.status, '🔔')

    msg = f"{emoji} *{pedido.estabelecimento.nome} - Pedido #{pedido.id}*\\n\\n"
    msg += f"Olá, *{pedido.cliente_nome}*!\\n"
    msg += f"Status do seu pedido: *{pedido.status.upper()}*\\n\\n"

    msg += "📋 *Itens:* \\n"
    for item in pedido.itens:
        obs = f" (_Obs: {item.observacao}_)" if item.observacao else ""
        msg += f"• {item.quantidade}x {item.produto_nome} - R$ {item.preco_unitario:.2f}{obs}\\n"

    msg += f"\\n💰 *Total:* R$ {pedido.total:.2f}\\n"
    msg += f"💳 *Forma de Pagamento:* {pedido.forma_pagamento}\\n"

    if pedido.precisa_troco and pedido.troco_para:
        troco_calculado = pedido.troco_para - pedido.total
        msg += f"💵 Troco para R$ {pedido.troco_para:.2f} (Troco: R$ {troco_calculado:.2f})\\n"

    msg += f"\\n📅 _Atualizado em: {pedido.data_inicio.strftime('%d/%m/%Y às %H:%M')}_"
    return msg

def gerar_link_whatsapp(telefone, mensagem):
    num_limpo = ''.join(filter(str.isdigit, telefone))
    if not num_limpo.startswith('55') and len(num_limpo) in [10, 11]:
        num_limpo = f"55{num_limpo}"
    texto_encoded = urllib.parse.quote(mensagem)
    return f"https://api.whatsapp.com/send?phone={num_limpo}&text={texto_encoded}"
""",
        'models.py': """from datetime import datetime
from database import db

class Estabelecimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    telefone_whatsapp = db.Column(db.String(20), nullable=False)
    cor_primaria = db.Column(db.String(7), default='#FF5722')
    cor_secundaria = db.Column(db.String(7), default='#212121')
    cor_fundo = db.Column(db.String(7), default='#F8F9FA')

    produtos = db.relationship('Produto', backref='estabelecimento', lazy=True)
    pedidos = db.relationship('Pedido', backref='estabelecimento', lazy=True)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=False)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=False)
    cliente_nome = db.Column(db.String(100), nullable=False)
    cliente_telefone = db.Column(db.String(20), nullable=False)
    tipo_pedido = db.Column(db.String(20), default='Delivery')
    forma_pagamento = db.Column(db.String(50), nullable=False)
    precisa_troco = db.Column(db.Boolean, default=False)
    troco_para = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(30), default='Recebido')
    data_inicio = db.Column(db.DateTime, default=datetime.now)
    data_fim = db.Column(db.DateTime, nullable=True)
    total = db.Column(db.Float, nullable=False)
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True)

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    produto_nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    observacao = db.Column(db.String(255), nullable=True)
""",
        'app.py': """from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from database import db
from models import Estabelecimento, Produto, Pedido, ItemPedido
from whatsapp import gerar_mensagem_whatsapp, gerar_link_whatsapp
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lanchefy_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lanchefy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def landing_page():
    return render_template('index.html')

@app.route('/cadastrar-lanchonete', methods=['POST'])
def cadastrar_lanchonete():
    nome = request.form.get('nome')
    slug = request.form.get('slug').lower().replace(' ', '-')
    telefone = request.form.get('telefone')
    cor_primaria = request.form.get('cor_primaria', '#FF5722')
    cor_secundaria = request.form.get('cor_secundaria', '#212121')
    cor_fundo = request.form.get('cor_fundo', '#F8F9FA')

    if Estabelecimento.query.filter_by(slug=slug).first():
        flash('Este slug já está em uso!')
        return redirect(url_for('landing_page'))

    nova_lanchonete = Estabelecimento(
        nome=nome, slug=slug, telefone_whatsapp=telefone,
        cor_primaria=cor_primaria, cor_secundaria=cor_secundaria, cor_fundo=cor_fundo
    )
    db.session.add(nova_lanchonete)
    db.session.commit()
    return redirect(url_for('admin_pedidos', slug=slug))

@app.route('/lanchonete/<slug>')
def cardapio_publico(slug):
    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    produtos = Produto.query.filter_by(estabelecimento_id=estabelecimento.id).all()
    return render_template('cardapio.html', est=estabelecimento, produtos=produtos)

@app.route('/admin/<slug>/pedidos')
def admin_pedidos(slug):
    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    pedidos = Pedido.query.filter_by(estabelecimento_id=estabelecimento.id).order_by(Pedido.id.desc()).all()
    return render_template('admin_pedidos.html', est=estabelecimento, pedidos=pedidos)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
""",
    }

    for nome_arq, conteudo in arquivos_raiz.items():
        with open(nome_arq, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        print(f'📄 Criado arquivo raiz: {nome_arq}')

    # Criando pastas e subpastas
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

    # Criando arquivos dentro de templates e static vazios ou com estrutura básica
    for pasta, arquivos in estrutura.items():
        if isinstance(arquivos, list):
            for arq in arquivos:
                caminho = os.path.join(pasta, arq)
                if not os.path.exists(caminho):
                    with open(caminho, 'w', encoding='utf-8') as f:
                        f.write(
                            f'<!-- Arquivo {arq} gerado automaticamente pelo Lanchefy -->'
                        )
                    print(f'📁 Criado arquivo: {caminho}')
        elif isinstance(arquivos, dict):
            for subpasta, subarquivos in arquivos.items():
                caminho_sub = os.path.join(pasta, subpasta)
                os.makedirs(caminho_sub, exist_ok=True)
                for arq in subarquivos:
                    caminho = os.path.join(caminho_sub, arq)
                    if not os.path.exists(caminho):
                        with open(caminho, 'w', encoding='utf-8') as f:
                            f.write(f'/* {arq} */')
                        print(f'📁 Criado arquivo: {caminho}')

    print(
        '\n✨ Sucesso! Toda a estrutura do Lanchefy foi criada automaticamente'
        ' com os códigos base!'
    )


if __name__ == '__main__':
    criar_estrutura_projeto()