from services.SQLServerConnection import SQLServerConnection
from services.DownloadCVM import DownloadCVM
from services.ProcessadorCVM import ProcessadorCVM
from services.CVMRepository import CVMRepository

import logging
import os
from dotenv import load_dotenv

# configuração do log para o monitoramento de conexão
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info('Iniciando o sistema de automação do CVM')

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
        'username': os.getenv('DB_USERNAME'),
        'password': os.getenv('DB_PASSWORD'),
        'driver': os.getenv('DB_DRIVER')
    }

    # Configurando a URL da API(CVM) e a pasta de destino
    url_cvm = os.getenv('URL_CVM')
    pasta_dados = os.getenv('DADOS_BRUTOS')
    pasta_dados_tratados = os.getenv('DADOS_TRATADOS', r'.\Temp_File\Dados_tratados')


    try:
        # Faz o download dos dados
        logging.info('Iniciando o download da fonte de dados...')
        download = DownloadCVM(url=url_cvm, pasta_destino=pasta_dados)
        caminho_csv = download.baixar_arquivo()

        if not caminho_csv:
            logging.error('Nenhum dado retornado! Encerrando o processo.')
            return

        # Processamento e tratamento dos dados baixados
        logging.info('Iniciando o tratamento dos dados...')
        processador = ProcessadorCVM(caminho_csv=caminho_csv)
        df_tratado = processador.processar()
        
        # Salvando a base de dados limpa no diretório de dados tratados
        processador.salvar_csv(df_tratado, pasta_destino=pasta_dados_tratados, nome_arquivo='cad_fi_tratado.csv')
        
        logging.info(f'Tratamento e salvamento concluídos. {len(df_tratado)} registros salvos em {pasta_dados_tratados}.')


        # Conexão com o Banco de Dados e Carga
        logging.info('Iniciando a conexão com o Banco de Dados para inserção...')

        with SQLServerConnection(**db_config) as conn:
            repo = CVMRepository()
            total_inserido = repo.inserir_dados(conn, df_tratado, truncar=True, tamanho_lote=5000)
            logging.info(f'Carga no banco finalizada com sucesso! Total de registros salvos na tabela Carteira.CVM_FI: {total_inserido}')


    except Exception as e:
        # Se ocorrer um erro no banco de dados (ou no download/tratamento), nós capturamos aqui
        logging.error(f"O processo foi interrompido devido a um erro: {e}")

if __name__ == "__main__":
    main()