from datetime import datetime, timedelta
import os
import re
import urllib.parse
from database import db
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from models import Estabelecimento, ItemPedido, Pedido, Produto
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lanchefy_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lanchefy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def verificar_sessao_admin(slug):
    return session.get(f'admin_logado_{slug}') == True


def validar_senha_forte(senha):
    if len(senha) < 8: return False
    if not re.search(r'[A-Z]', senha): return False
    if not re.search(r'[a-z]', senha): return False
    if not re.search(r'[0-9]', senha): return False
    if not re.search(r'[\W_]', senha): return False
    return True


# ==========================================
# MIDDLEWARE: BLOQUEIO AUTOMÁTICO SE TESTE EXpirar
# ==========================================
@app.before_request
def verificar_vencimento_loja():
    if '/admin/' in request.path:
        partes = request.path.split('/')
        if len(partes) > 2:
            slug = partes[2]
            est = Estabelecimento.query.filter_by(slug=slug).first()
            if est and est.vencimento_plano:
                if datetime.now() > est.vencimento_plano:
                    return render_template('plano_expirado.html', est=est)


# ==========================================
# ROTAS DO SUPER ADMIN (GESTÃO GLOBAL SAAS)
# ==========================================

@app.route('/super-admin/login', methods=['GET', 'POST'])
def super_admin_login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        if usuario == 'admin' and senha == 'Lanchefy@2026!':
            session['super_admin_logado'] = True
            return redirect(url_for('painel_super_admin'))
        else:
            flash('Usuário ou senha inválidos. A senha de segurança exige maiúsculas, minúsculas, números e caracteres especiais.')
    return render_template('super_admin_login.html')


@app.route('/super-admin/logout')
def super_admin_logout():
    session.pop('super_admin_logado', None)
    return redirect(url_for('super_admin_login'))


@app.route('/super-admin/dashboard', methods=['GET', 'POST'])
def painel_super_admin():
    if not session.get('super_admin_logado'):
        return redirect(url_for('super_admin_login'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        slug = request.form.get('slug').lower().replace(' ', '-')
        telefone = request.form.get('telefone')
        endereco = request.form.get('endereco', '')
        senha = request.form.get('senha', '')
        cor_primaria = request.form.get('cor_primaria', '#FF5722')

        if not validar_senha_forte(senha):
            flash('Erro: A senha da loja deve ter no mínimo 8 caracteres, incluindo letras maiúsculas, minúsculas, números e caracteres especiais (ex: @, #, $, !).')
            return redirect(url_for('painel_super_admin'))

        if Estabelecimento.query.filter_by(slug=slug).first():
            flash('Erro: Este identificador (slug) já está em uso por outra loja.')
            return redirect(url_for('painel_super_admin'))

        # Define 10 dias de teste para cadastros feitos pelo Super Admin também
        vencimento_teste = datetime.now() + timedelta(days=10)

        nova_loja = Estabelecimento(
            nome=nome,
            slug=slug,
            telefone_whatsapp=telefone,
            endereco=endereco,
            cor_primaria=cor_primaria,
            cor_secundaria='#212121',
            cor_fundo='#F8F9FA',
            status='Ativa',
            vencimento_plano=vencimento_teste
        )
        nova_loja.set_senha(senha)
        db.session.add(nova_loja)
        db.session.commit()
        flash('Loja parceira cadastrada com 10 dias de teste grátis!')
        return redirect(url_for('painel_super_admin'))

    lojas = Estabelecimento.query.all()
    return render_template('super_admin.html', lojas=lojas)


@app.route('/super-admin/loja/<int:id>/toggle-status', methods=['POST'])
def super_admin_toggle_status(id):
    if not session.get('super_admin_logado'):
        return redirect(url_for('super_admin_login'))
    loja = Estabelecimento.query.get_or_404(id)
    loja.status = 'Suspensa' if loja.status == 'Ativa' else 'Ativa'
    db.session.commit()
    return redirect(url_for('painel_super_admin'))


@app.route('/super-admin/loja/<int:id>/excluir', methods=['POST'])
def super_admin_excluir_loja(id):
    if not session.get('super_admin_logado'):
        return redirect(url_for('super_admin_login'))
    loja = Estabelecimento.query.get_or_404(id)
    db.session.delete(loja)
    db.session.commit()
    flash('Loja excluída com sucesso do sistema.')
    return redirect(url_for('painel_super_admin'))


# ==========================================
# ROTAS PÚBLICAS E DO CLIENTE (COM TESTE DE 10 DIAS + WHATSAPP)
# ==========================================

@app.route('/')
def landing_page():
    return render_template('index.html')


@app.route('/cadastrar-lanchonete', methods=['POST'])
def cadastrar_lanchonete():
    nome = request.form.get('nome')
    slug = request.form.get('slug').lower().replace(' ', '-')
    telefone = request.form.get('telefone')
    senha_pura = request.form.get('senha', '123')
    cor_primaria = request.form.get('cor_primaria', '#FF5722')
    cor_secundaria = request.form.get('cor_secundaria', '#212121')
    cor_fundo = request.form.get('cor_fundo', '#F8F9FA')

    if Estabelecimento.query.filter_by(slug=slug).first():
        flash('Este slug já está em uso!')
        return redirect(url_for('landing_page'))

    # Concede 10 dias de teste gratuito
    vencimento_teste = datetime.now() + timedelta(days=10)

    nova_lanchonete = Estabelecimento(
        nome=nome,
        slug=slug,
        telefone_whatsapp=telefone,
        cor_primaria=cor_primaria,
        cor_secundaria=cor_secundaria,
        cor_fundo=cor_fundo,
        status='Ativa',
        vencimento_plano=vencimento_teste
    )
    nova_lanchonete.set_senha(senha_pura)

    db.session.add(nova_lanchonete)
    db.session.commit()

    session[f'admin_logado_{slug}'] = True

    # Redireciona o navegador para o seu WhatsApp (31972148479) com a notificação
    meu_zap = '5531972148479'
    msg_zap = f'🚀 *NOVO CADASTRO NO LANCHEFY!*\n\nLoja: *{nome}*\nSlug: `{slug}`\nWhatsApp: {telefone}\nVencimento do Teste: {vencimento_teste.strftime("%d/%m/%Y")}'
    url_zap_admin = f'https://api.whatsapp.com/send?phone={meu_zap}&text={urllib.parse.quote(msg_zap)}'

    return redirect(url_zap_admin)


@app.route('/lanchonete/<slug>')
def cardapio_publico(slug):
    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    produtos = Produto.query.filter_by(estabelecimento_id=estabelecimento.id).all()
    return render_template('cardapio.html', est=estabelecimento, produtos=produtos)


@app.route('/lanchonete/<slug>/fazer-pedido', methods=['POST'])
def fazer_pedido_online(slug):
    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    dados = request.get_json() if request.is_json else request.form

    cliente_nome = dados.get('cliente_nome', 'Cliente Anônimo')
    cliente_telefone = dados.get('cliente_telefone', '')
    tipo_pedido = dados.get('tipo_pedido', 'Delivery')
    cliente_endereco = dados.get('cliente_endereco', '')
    forma_pagamento = dados.get('forma_pagamento', 'Pix')
    troco_para = dados.get('troco_para')
    total = float(dados.get('total', 0))

    if troco_para:
        forma_pagamento += f' (Troco para R$ {troco_para})'

    status_inicial = 'Em Preparo' if estabelecimento.impressora_automatica else 'Recebido'

    novo_pedido = Pedido(
        estabelecimento_id=estabelecimento.id,
        cliente_nome=cliente_nome,
        cliente_telefone=cliente_telefone,
        cliente_endereco=cliente_endereco,
        tipo_pedido=tipo_pedido,
        forma_pagamento=forma_pagamento,
        total=total,
        status=status_inicial,
        data_inicio=datetime.now(),
    )

    db.session.add(novo_pedido)
    db.session.commit()

    return jsonify({
        'status': 'sucesso',
        'pedido_id': novo_pedido.id,
        'mensagem': 'Pedido registrado com sucesso!',
    })


# ==========================================
# ROTAS DO PAINEL ADMINISTRATIVO DA LOJA
# ==========================================

@app.route('/admin/<slug>/login', methods=['GET', 'POST'])
def admin_login(slug):
    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        senha_digitada = request.form.get('senha')
        if estabelecimento.verificar_senha(senha_digitada):
            session[f'admin_logado_{slug}'] = True
            return redirect(url_for('admin_pedidos', slug=slug))
        else:
            flash('Senha incorreta. Tente novamente.')
    return render_template('login.html', slug=slug, est=estabelecimento)


@app.route('/admin/<slug>/logout')
def admin_logout(slug):
    session.pop(f'admin_logado_{slug}', None)
    flash('Você saiu do painel administrativo.')
    return redirect(url_for('admin_login', slug=slug))


@app.route('/admin/<slug>/verificar-novos-pedidos')
def verificar_novos_pedidos(slug):
    if not verificar_sessao_admin(slug):
        return jsonify({'error': 'Não autorizado'}), 401

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    ultimo_pedido = (
        Pedido.query.filter_by(estabelecimento_id=estabelecimento.id)
        .order_by(Pedido.id.desc())
        .first()
    )
    total_pedidos = Pedido.query.filter_by(estabelecimento_id=estabelecimento.id).count()
    ultimo_id = ultimo_pedido.id if ultimo_pedido else 0

    return jsonify({
        'total_pedidos': total_pedidos,
        'ultimo_pedido_id': ultimo_id,
        'impressora_automatica': estabelecimento.impressora_automatica
    })


@app.route('/admin/<slug>/toggle-impressora', methods=['POST'])
def toggle_impressora(slug):
    if not verificar_sessao_admin(slug):
        return jsonify({'error': 'Não autorizado'}), 401

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    estabelecimento.impressora_automatica = not estabelecimento.impressora_automatica
    db.session.commit()

    return jsonify({
        'status': 'sucesso',
        'impressora_automatica': estabelecimento.impressora_automatica
    })


@app.route('/admin/<slug>/pedidos')
def admin_pedidos(slug):
    if not verificar_sessao_admin(slug):
        return redirect(url_for('admin_login', slug=slug))

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    pedidos = Pedido.query.filter_by(estabelecimento_id=estabelecimento.id).order_by(Pedido.id.desc()).all()
    return render_template('admin_pedidos.html', est=estabelecimento, pedidos=pedidos)


@app.route('/admin/<slug>/pedido/<int:id>/status', methods=['POST'])
def atualizar_status_pedido(slug, id):
    if not verificar_sessao_admin(slug):
        return redirect(url_for('admin_login', slug=slug))

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    pedido = Pedido.query.filter_by(id=id, estabelecimento_id=estabelecimento.id).first_or_404()

    novo_status = request.form.get('status')
    pedido.status = novo_status
    db.session.commit()

    if novo_status in ['Pronto para Retirada', 'Enviado com Motoboy']:
        telefone_limpo = ''.join(filter(str.isdigit, pedido.cliente_telefone or ''))
        if telefone_limpo:
            if len(telefone_limpo) <= 11 and not telefone_limpo.startswith('55'):
                telefone_limpo = '55' + telefone_limpo

            if novo_status == 'Pronto para Retirada':
                msg = f'Olá *{pedido.cliente_nome}*! O seu pedido *#{pedido.id}* já está *PRONTO PARA RETIRADA* na *{estabelecimento.nome}*! 🏪🏃‍♂️'
            else:
                msg = f'Olá *{pedido.cliente_nome}*! O seu pedido *#{pedido.id}* acabou de sair para entrega com o nosso motoboy! 🛵💨'

            url_zap = f'https://api.whatsapp.com/send?phone={telefone_limpo}&text={urllib.parse.quote(msg)}'
            return redirect(url_zap)

    return redirect(url_for('admin_pedidos', slug=slug))


@app.route('/admin/<slug>/pedido/<int:id>/mudar-status-json', methods=['POST'])
def mudar_status_json(slug, id):
    if not verificar_sessao_admin(slug):
        return jsonify({'error': 'Não autorizado'}), 401

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    pedido = Pedido.query.filter_by(id=id, estabelecimento_id=estabelecimento.id).first_or_404()

    dados = request.get_json() if request.is_json else request.form
    novo_status = dados.get('status', 'Em Preparo')

    pedido.status = novo_status
    db.session.commit()

    return jsonify({'status': 'sucesso', 'novo_status': novo_status})


@app.route('/admin/<slug>/pedido/<int:id>/imprimir')
def imprimir_pedido(slug, id):
    if not verificar_sessao_admin(slug):
        return redirect(url_for('admin_login', slug=slug))

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    pedido = Pedido.query.filter_by(id=id, estabelecimento_id=estabelecimento.id).first_or_404()

    return render_template('imprimir_pedido.html', est=estabelecimento, pedido=pedido)


@app.route('/admin/<slug>/produtos', methods=['GET', 'POST'])
def admin_produtos(slug):
    if not verificar_sessao_admin(slug):
        return redirect(url_for('admin_login', slug=slug))

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()

    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = float(request.form.get('preco'))
        categoria = request.form.get('categoria')

        foto_filename = None
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                foto_filename = f'{timestamp}_{filename}'
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file.save(os.path.join(UPLOAD_FOLDER, foto_filename))

        novo_produto = Produto(
            nome=nome,
            descricao=descricao,
            preco=preco,
            categoria=categoria,
            foto=foto_filename,
            estabelecimento_id=estabelecimento.id,
        )
        db.session.add(novo_produto)
        db.session.commit()

        flash('Produto cadastrado com sucesso!')
        return redirect(url_for('admin_produtos', slug=slug))

    produtos = Produto.query.filter_by(estabelecimento_id=estabelecimento.id).all()
    return render_template('admin_produtos.html', est=estabelecimento, produtos=produtos)


@app.route('/admin/<slug>/produto/<int:id>/editar', methods=['GET', 'POST'])
def admin_editar_produto(slug, id):
    if not verificar_sessao_admin(slug):
        return redirect(url_for('admin_login', slug=slug))

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    produto = Produto.query.filter_by(id=id, estabelecimento_id=estabelecimento.id).first_or_404()

    if request.method == 'POST':
        produto.nome = request.form.get('nome')
        produto.descricao = request.form.get('descricao')
        produto.preco = float(request.form.get('preco'))
        produto.categoria = request.form.get('categoria')

        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                foto_filename = f'{timestamp}_{filename}'
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file.save(os.path.join(UPLOAD_FOLDER, foto_filename))
                produto.foto = foto_filename

        db.session.commit()
        flash('Produto atualizado com sucesso!')
        return redirect(url_for('admin_produtos', slug=slug))

    return render_template('admin_editar_produto.html', est=estabelecimento, produto=produto)


@app.route('/admin/<slug>/produto/<int:id>/excluir', methods=['POST'])
def admin_excluir_produto(slug, id):
    if not verificar_sessao_admin(slug):
        return redirect(url_for('admin_login', slug=slug))

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    produto = Produto.query.filter_by(id=id, estabelecimento_id=estabelecimento.id).first_or_404()

    db.session.delete(produto)
    db.session.commit()
    flash('Produto excluído com sucesso!')
    return redirect(url_for('admin_produtos', slug=slug))


@app.route('/admin/<slug>/qrcode')
def admin_qrcode(slug):
    if not verificar_sessao_admin(slug):
        return redirect(url_for('admin_login', slug=slug))

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    url_cardapio = request.host_url.rstrip('/') + url_for('cardapio_publico', slug=slug)
    return render_template('admin_qrcode.html', est=estabelecimento, url_cardapio=url_cardapio)


@app.route('/admin/<slug>/caixa-balcao', methods=['GET', 'POST'])
def admin_caixa(slug):
    if not verificar_sessao_admin(slug):
        return redirect(url_for('admin_login', slug=slug))

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()

    if request.method == 'POST':
        dados = request.get_json() if request.is_json else request.form
        cliente_nome = dados.get('cliente_nome', 'Cliente Balcão')
        cliente_telefone = dados.get('cliente_telefone', 'Balcão Presencial')
        forma_pagamento = dados.get('forma_pagamento', 'Dinheiro')
        total = float(dados.get('total', 0))
        troco_para = dados.get('troco_para')

        if troco_para:
            forma_pagamento += f' (Troco para R$ {troco_para})'

        novo_pedido = Pedido(
            cliente_nome=cliente_nome,
            cliente_telefone=cliente_telefone,
            tipo_pedido='Balcão',
            forma_pagamento=forma_pagamento,
            total=total,
            estabelecimento_id=estabelecimento.id,
            data_inicio=datetime.now(),
            data_fim=datetime.now(),
            status='Finalizado',
        )
        db.session.add(novo_pedido)
        db.session.commit()

        if request.is_json:
            return jsonify({'status': 'sucesso', 'mensagem': 'Venda registrada com sucesso!'})

        flash('Venda de balcão registrada com sucesso!')
        return redirect(url_for('admin_financeiro', slug=slug))

    produtos = Produto.query.filter_by(estabelecimento_id=estabelecimento.id).all()
    return render_template('admin_caixa.html', est=estabelecimento, produtos=produtos)


@app.route('/admin/<slug>/financeiro')
def admin_financeiro(slug):
    if not verificar_sessao_admin(slug):
        return redirect(url_for('admin_login', slug=slug))

    estabelecimento = Estabelecimento.query.filter_by(slug=slug).first_or_404()
    pedidos = Pedido.query.filter_by(estabelecimento_id=estabelecimento.id).all()
    total_faturado = sum(p.total for p in pedidos)
    qtd_pedidos = len(pedidos)

    return render_template(
        'financeiro.html',
        est=estabelecimento,
        pedidos=pedidos,
        total_faturado=total_faturado,
        qtd_pedidos=qtd_pedidos,
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)