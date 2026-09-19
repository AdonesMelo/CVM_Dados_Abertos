from services.SQLServerConnection import SQLServerConnection

import logging
import os
from dotenv import load_dotenv

# configuração do log para o monitoramento de conexão
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info('Iniciando o sistama de automação do CVM')

    # Carregando as variáveis de ambiente do Banco de Dados
    load_dotenv()

    # validando as variáveis de ambiente do Banco de Dados
    if not os.getenv('DB_SERVER'):
        logging.error('Erro ao carregar as variáveis de ambiente do Banco de Dados')
        return # Encerrando o programa antes de tentar conectar

    # Configuração das variáveis de ambiente do Banco de Dados
    db_config = {
        'server': os.getenv('DB_SERVER'),
        'database': os.getenv('DB_DATABASE'),
        'user': os.getenv('DB_USERNAME'),
        'password': os.getenv('DB_PASSWORD'),
        'driver': os.getenv('DB_DRIVER')
    }

    # Espaço reservado para o download dos dados futuros
    logging.info('Iniciando o download da fonte de dados...')

    #dados = DownloadService.obter_dados()

    # Conexão com o Banco de Dados
    logging.info('Iniciando a conexão com o Banco de Dados...')
    try:
        with SQLServerConnection(**db_config) as conn:
            cursor = conn.cursor()

            # Aqui tera a logica de inserir os dados no BD

            #cursor.execute('INSERT INTO...'...)

            logging.info('Dados inseridos com sucesso.')

    except Exception as e:
        # Se ocorrer um erro no banco de dados (ou no download), nós capturamos aqui
        logging.error(f"O processo foi interrompido devido a um erro: {e}")



    

if __name__ == "__main__":
    main()