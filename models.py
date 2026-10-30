from datetime import datetime
from database import db
from argon2 import PasswordHasher

ph = PasswordHasher()


class Estabelecimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    telefone_whatsapp = db.Column(db.String(20), nullable=False)
    endereco = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Ativa')
    vencimento_plano = db.Column(db.DateTime, nullable=True)  # <-- Adicionado para o teste grátis de 10 dias
    senha = db.Column(db.String(255), nullable=False, default='123456')
    cor_primaria = db.Column(db.String(20), default='#FF5722')
    cor_secundaria = db.Column(db.String(20), default='#212121')
    cor_fundo = db.Column(db.String(20), default='#F8F9FA')
    impressora_automatica = db.Column(db.Boolean, default=False)

    def set_senha(self, senha_texto):
        self.senha = ph.hash(senha_texto)

    def verificar_senha(self, senha_texto):
        try:
            return ph.verify(self.senha, senha_texto)
        except Exception:
            return self.senha == senha_texto


class Produto(db.Model):
    __tablename__ = 'produto'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    foto = db.Column(db.String(255), nullable=True)
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=False)


class Pedido(db.Model):
    __tablename__ = 'pedido'
    id = db.Column(db.Integer, primary_key=True)
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=False)
    cliente_nome = db.Column(db.String(100), nullable=False)
    cliente_telefone = db.Column(db.String(20), nullable=False)
    cliente_endereco = db.Column(db.Text, nullable=True)
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
    __tablename__ = 'item_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    produto_nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    observacao = db.Column(db.String(255), nullable=True)