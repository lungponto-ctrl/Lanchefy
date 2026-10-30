import urllib.parse

def gerar_mensagem_whatsapp(pedido):
    status_emojis = {
        'Recebido': '📥', 'Em Preparo': '👨‍🍳', 'Saiu para Entrega': '🛵',
        'Pronto para Retirada': '🛍️', 'Concluido': '✅', 'Cancelado': '❌'
    }
    emoji = status_emojis.get(pedido.status, '🔔')

    msg = f"{emoji} *{pedido.estabelecimento.nome} - Pedido #{pedido.id}*\n\n"
    msg += f"Olá, *{pedido.cliente_nome}*!\n"
    msg += f"Status do seu pedido: *{pedido.status.upper()}*\n\n"

    msg += "📋 *Itens:* \n"
    for item in pedido.itens:
        obs = f" (_Obs: {item.observacao}_)" if item.observacao else ""
        msg += f"• {item.quantidade}x {item.produto_nome} - R$ {item.preco_unitario:.2f}{obs}\n"

    msg += f"\n💰 *Total:* R$ {pedido.total:.2f}\n"
    msg += f"💳 *Forma de Pagamento:* {pedido.forma_pagamento}\n"

    if pedido.precisa_troco and pedido.troco_para:
        troco_calculado = pedido.troco_para - pedido.total
        msg += f"💵 Troco para R$ {pedido.troco_para:.2f} (Troco: R$ {troco_calculado:.2f})\n"

    msg += f"\n📅 _Atualizado em: {pedido.data_inicio.strftime('%d/%m/%Y às %H:%M')}_"
    return msg

def gerar_link_whatsapp(telefone, mensagem):
    num_limpo = ''.join(filter(str.isdigit, telefone))
    if not num_limpo.startswith('55') and len(num_limpo) in [10, 11]:
        num_limpo = f"55{num_limpo}"
    texto_encoded = urllib.parse.quote(mensagem)
    return f"https://api.whatsapp.com/send?phone={num_limpo}&text={texto_encoded}"
