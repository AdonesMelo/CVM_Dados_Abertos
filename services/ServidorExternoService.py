import shutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ServidorExternoService:
    '''
    Serviço responsável por simular a transferência do arquivo limpo
    para um servidor/diretório externo compartilhado.
    '''

    def __init__(self, diretorio_destino: str):
        self.diretorio_destino = Path(diretorio_destino)

    def enviar_arquivo(self, caminho_arquivo_origem: str, nome_destino: str = None) -> str:
        '''
        Copia o arquivo de origem para o diretório de destino do servidor externo.
        '''
        origem = Path(caminho_arquivo_origem)
        if not origem.exists():
            raise FileNotFoundError(f"Arquivo de origem não encontrado: {origem}")

        # Garantir que a pasta de destino exista no servidor externo
        self.diretorio_destino.mkdir(parents=True, exist_ok=True)

        nome_final = nome_destino if nome_destino else origem.name
        caminho_destino_completo = self.diretorio_destino / nome_final

        logging.info(f'Simulando envio do arquivo {origem.name} para o Servidor Externo: {caminho_destino_completo}')
        shutil.copy2(origem, caminho_destino_completo)
        logging.info(f'Arquivo enviado com sucesso para o Servidor Externo.')
        return str(caminho_destino_completo)
