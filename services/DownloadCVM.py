import requests
import logging
from pathlib import Path

class DownloadCVM:
    '''
    Faz o download de arquivos pesados via streaming e salva diretamente em disco.
    '''
    
    def __init__(self, url: str, pasta_destino: str, timeout: int = 60):
        self.url = url
        self.pasta_destino = Path(pasta_destino)
        self.timeout = timeout

    def baixar_arquivo(self) -> str:
        '''
        Baixa o arquivo em pedaços e retorna o caminho completo de onde foi salvo.
        '''
        # Garante que a pasta existe (cria se não existir, sem dar erro)
        self.pasta_destino.mkdir(parents=True, exist_ok=True)

        # Pega o último pedaço da URL para usar como nome (ex: "cad_fi.csv")
        nome_arquivo = self.url.split('/')[-1]
        caminho_completo = self.pasta_destino / nome_arquivo

        logging.info(f'Iniciando o download do arquivo {nome_arquivo} via streaming...')

        try:
            # stream=True não carrega o arquivo inteiro na memória RAM
            # timeout protege contra travamentos de rede
            response = requests.get(self.url, stream=True, timeout=self.timeout)

            # Verifica se o servidor retornou sucesso (status 200)
            if response.status_code == 200:
                with open(caminho_completo, 'wb') as arquivo:
                    
                    # iter_content baixa o arquivo em pequenos pacotes de 8KB
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            arquivo.write(chunk)
                            
                logging.info(f'Arquivo {nome_arquivo} baixado com sucesso.')
                
                # Retornamos str() para garantir a compatibilidade com a assinatura da função -> str
                return str(caminho_completo) 
                
            else:
                logging.error(f'Erro ao baixar o arquivo {nome_arquivo}. Status HTTP: {response.status_code}')
                return None
                
        except requests.exceptions.RequestException as erro:
            logging.error(f'Erro de rede ao tentar baixar o arquivo {nome_arquivo}: {erro}')
            raise