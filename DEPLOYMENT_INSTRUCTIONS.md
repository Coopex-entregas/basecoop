# Instruções de Implantação no PythonAnywhere

Este documento detalha os passos para implantar o sistema de entregas no PythonAnywhere.

## 1. Preparação dos Arquivos

Certifique-se de que os seguintes arquivos estão na pasta `coopex-sistema-entregas`:

- `app.py`
- `models.py`
- `requirements.txt`
- `Procfile`
- Pasta `templates/` (com todos os arquivos HTML)
- Pasta `static/` (com arquivos CSS e JS)

## 2. Upload dos Arquivos para o PythonAnywhere

1.  Faça login na sua conta PythonAnywhere (ou crie uma conta gratuita).
2.  Vá para a aba "Files".
3.  Crie uma nova pasta para o seu projeto (ex: `coopex-sistema-entregas`).
4.  Faça o upload de todos os arquivos e pastas listados acima para esta nova pasta.

## 3. Configuração do Banco de Dados SQLite

O PythonAnywhere suporta SQLite nativamente. O banco de dados `entregas.db` será criado automaticamente na primeira execução da aplicação, no mesmo diretório de `app.py`.

## 4. Configuração da Aplicação Web

1.  Vá para a aba "Web".
2.  Clique em "Add a new web app".
3.  Escolha "Flask" como framework.
4.  Selecione a versão do Python (recomenda-se Python 3.9 ou superior).
5.  No campo "Code path", insira o caminho para a pasta do seu projeto (ex: `/home/seu_usuario/coopex-sistema-entregas`).
6.  No campo "WSGI configuration file", edite o arquivo e certifique-se de que ele aponta para a sua aplicação. O conteúdo deve ser algo como:

    ```python
    import sys
    from os.path import dirname, join

    # Adicione o diretório do seu projeto ao sys.path
    project_folder = join(dirname(__file__), 'coopex-sistema-entregas')
    sys.path.insert(0, project_folder)

    from app import app as application  # 'application' é o nome que o PythonAnywhere espera
    ```

    **Importante:** Substitua `coopex-sistema-entregas` pelo nome da pasta que você criou e `seu_usuario` pelo seu nome de usuário no PythonAnywhere.

7.  Clique em "Save" e depois em "Reload your web app".

## 5. Acessando a Aplicação

Após recarregar a aplicação, você poderá acessá-la através do URL fornecido na aba "Web" (ex: `seu_usuario.pythonanywhere.com`).

## 6. Acesso ao Console para Migração Inicial (Opcional)

Se o banco de dados não for criado automaticamente ou se você precisar executar comandos específicos:

1.  Vá para a aba "Consoles".
2.  Abra um "Bash console".
3.  Navegue até o diretório do seu projeto:
    `cd /home/seu_usuario/coopex-sistema-entregas`
4.  Execute o `app.py` uma vez para criar o banco de dados e o usuário admin:
    `python app.py`
    Você pode precisar parar o processo com `Ctrl+C` após ver a mensagem de inicialização.

Com esses passos, seu sistema de entregas estará online no PythonAnywhere.

