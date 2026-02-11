# Vizinho de Aluguel 🏠

Projeto desenvolvido para facilitar a conexão entre prestadores de serviços e clientes.

## 🛠 Tecnologias
* **Framework:** Django 6.0
* **Banco de Dados:** PostgreSQL
* **Linguagem:** Python 3.12+
* **Estilização:** Tailwind CSS (Planejado)

## 🚀 Como rodar o projeto localmente

### 1. Clonar o repositório
```bash
git clone https://github.com/AutojunUFSC/Vizinho-de-alugel
cd vizinho_de_aluguel
2. Configurar o Ambiente Virtual
Bash

python -m venv venv
# No Windows (CMD):
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate
3. Instalar as dependências
Bash

pip install -r requirements.txt
4. Configurar o Banco de Dados
Certifique-se de que o PostgreSQL está rodando e crie um banco chamado vizinho_db. Configure as credenciais no arquivo core/settings.py (ou use um arquivo .env).

5. Rodar as Migrações e o Servidor
Bash

python manage.py migrate
python manage.py runserver
👥 Equipe
Artur Tomaz
Bernardo Nunes
Gabriel Madeira
Gustavo Borget
Rafael Mussi



Este projeto faz parte do desenvolvimento da AutoJun/UFSC.