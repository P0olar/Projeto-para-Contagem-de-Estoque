from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import csv
from collections import defaultdict
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Substitua por uma chave secreta segura

# Função para carregar os usuários do arquivo CSV
def carregar_usuarios(nome_arquivo):
    usuarios = {}
    with open(nome_arquivo, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            user = row['user']
            senha = row['senha']
            nome = row['nome']
            usuarios[user] = {'senha': generate_password_hash(senha), 'nome': nome}
    return usuarios

users = carregar_usuarios('logins.csv')

# Função para salvar os dados em um arquivo CSV
def salvar_em_csv(dados, nome_arquivo):
    with open(nome_arquivo, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        for linha in dados:
            writer.writerow(linha)

# Função para registrar no log
def registrar_log(acao, produto, usuario):
    with open('change-log.txt', 'a') as logfile:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logfile.write(f'[{timestamp}] {acao}: {produto} Pelo Usuario: {usuario}\n')

# Função para ler dados do arquivo CSV e contar a ocorrência de cada produto
def contar_produtos(nome_arquivo):
    contagem_produtos = defaultdict(int)
    nome_sku_dict = {}

    # Ler dados do arquivo "bd-produtos.csv" e criar um dicionário com nome e SKU
    with open('Cadastros_dos_Produtos.csv', 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            nome_sku_dict[row['Produto']] = {'nome': row['Nome'], 'sku': row['SKU']}

    # Ler dados do arquivo CSV "Produtos_Registrados.csv" e contar os produtos
    with open(nome_arquivo, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            # Ignorar a primeira coluna (etiqueta) e contar os produtos
            for produto in row[1:]:
                if produto:  # Contar apenas se o produto não estiver vazio
                    contagem_produtos[produto] += 1

    # Combinar dados de contagem de produtos com nome e SKU
    contagem_produtos_com_info = {}
    for produto, contagem in contagem_produtos.items():
        if produto in nome_sku_dict:
            nome = nome_sku_dict[produto]['nome']
            sku = nome_sku_dict[produto]['sku']
        else:
            nome = ''
            sku = ''
        contagem_produtos_com_info[produto] = {'nome': nome, 'sku': sku, 'contagem': contagem}

    return contagem_produtos_com_info

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and check_password_hash(users[username]['senha'], password):
            session['username'] = username
            session['nome'] = users[username]['nome']
            return redirect(url_for('index'))
        return "Login inválido"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('nome', None)
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
def add():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Usuário não autenticado'})
    produtos = request.json.get('produtos', [])
    usuario = session['username']
    dados = [[''] + produtos]  # Usar uma string vazia para a etiqueta
    salvar_em_csv(dados, 'Produtos_Registrados.csv')
    for produto in produtos:
        registrar_log('Adicionado', produto, usuario)
    return jsonify({'status': 'success'})

@app.route('/remove', methods=['POST'])
def remove():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Usuário não autenticado'})
    produto = request.json.get('produto', '')
    usuario = session['username']
    if produto:
        with open('Produtos_Registrados.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            linhas = list(reader)

        # Remover uma unidade do produto no arquivo CSV
        for linha in linhas:
            if produto in linha:
                linha.remove(produto)
                registrar_log('Removido', produto, usuario)
                break

        # Reescrever o arquivo CSV sem a unidade removida
        with open('Produtos_Registrados.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerows(linhas)

        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Produto não especificado'})

@app.route('/report')
def report():
    if 'username' not in session:
        return redirect(url_for('login'))
    contagem_produtos = contar_produtos('Produtos_Registrados.csv')
    return render_template('report.html', contagem_produtos=contagem_produtos)

if __name__ == '__main__':
    app.run(debug=True)
