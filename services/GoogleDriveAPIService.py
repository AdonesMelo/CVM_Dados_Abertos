import os
import logging
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GoogleDriveAPIService:
    '''
    Serviço oficial da API do Google Drive para upload direto de arquivos via chamadas REST (sem navegador).
    '''

    SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']

    def __init__(self, folder_id: str = '1arQKhL1WPDMNAjPM6PW7ob4ab6PL8JNu', credentials_path: str = 'credentials.json'):
        self.folder_id = folder_id
        self.credentials_path = Path(credentials_path)
        self.token_path = Path('token.json')

    def _obter_servico_drive(self):
        '''
        Autentica na API do Google Drive utilizando Service Account ou fluxo OAuth2.
        '''
        creds = None

        # 1. Tenta autenticar via arquivo de Service Account (Chave JSON de Conta de Serviço)
        if self.credentials_path.exists():
            try:
                creds = service_account.Credentials.from_service_account_file(
                    str(self.credentials_path), scopes=self.SCOPES
                )
                logging.info(f'Autenticado via Conta de Serviço Google: {self.credentials_path}')
                return build('drive', 'v3', credentials=creds)
            except Exception as e:
                logging.debug(f'Arquivo credentials.json não é uma Service Account: {e}')

        # 2. Tenta autenticar via fluxo OAuth2 (Token gerado ou credentials.json OAuth)
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), self.SCOPES)
            except Exception as e_tok:
                logging.warning(f'Erro ao carregar token.json: {e_tok}')

        # Se as credenciais não existirem ou forem inválidas, tenta atualizar ou gerar novo token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logging.info('Token de acesso renovado com sucesso.')
                except Exception:
                    creds = None

            if not creds:
                if self.credentials_path.exists():
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    # Salva o token para as próximas execuções
                    with open(self.token_path, 'w') as token_file:
                        token_file.write(creds.to_json())
                    logging.info('Novo token OAuth2 gerado e salvo em token.json.')
                else:
                    logging.warning(f'Arquivo de credenciais do Google ({self.credentials_path}) não encontrado.')
                    logging.info('Para usar a API oficial do Google Drive, coloque o arquivo credentials.json na raiz do projeto.')
                    return None

        return build('drive', 'v3', credentials=creds)

    def upload_arquivo(self, caminho_arquivo: str, nome_destino: Optional[str] = None) -> Optional[str]:
        '''
        Realiza o upload direto do arquivo para a pasta especificada no Google Drive.
        '''
        arquivo = Path(caminho_arquivo).resolve()
        if not arquivo.exists():
            raise FileNotFoundError(f'Arquivo para upload não encontrado: {arquivo}')

        service = self._obter_servico_drive()
        if not service:
            logging.error('Serviço do Google Drive não foi inicializado (credenciais ausentes).')
            return None

        nome_arquivo = nome_destino if nome_destino else arquivo.name
        logging.info(f'Iniciando upload via API do Google Drive do arquivo {nome_arquivo} ({arquivo.stat().st_size / (1024*1024):.2f} MB)...')

        file_metadata = {
            'name': nome_arquivo,
            'parents': [self.folder_id]
        }

        media = MediaFileUpload(str(arquivo), mimetype='text/csv', resumable=True)

        try:
            # Habilita suporte a pastas compartilhadas e Drives compartilhados (supportsAllDrives=True)
            file_obj = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()

            file_id = file_obj.get('id')
            link = file_obj.get('webViewLink')
            logging.info(f'Upload via API Oficial do Google Drive CONCLUÍDO com sucesso! ID do arquivo: {file_id}')
            if link:
                logging.info(f'Link do arquivo no Google Drive: {link}')
            return file_id

        except Exception as erro:
            logging.error(f'Erro ao realizar upload via API do Google Drive: {erro}')
            str_erro = str(erro)
            if 'storageQuotaExceeded' in str_erro or 'Service Accounts do not have storage quota' in str_erro:
                logging.warning('--> MOTIVO DO ERRO 403 (storageQuotaExceeded) <--')
                logging.warning('Contas de Serviço (Service Accounts) não possuem cota de armazenamento própria para criar arquivos em pastas do Google Drive pessoal (@gmail.com).')
                logging.info(" --> SOLUÇÃO: Crie uma credencial 'OAuth 2.0 Client ID' (Tipo: Aplicativo de Desktop) no Google Cloud Console:")
                logging.info('   1. Acesse o Google Cloud Console -> APIs e Serviços -> Credenciais.')
                logging.info("   2. Clique em 'Criar Credenciais' -> 'ID do cliente OAuth'.")
                logging.info("   3. Selecione o tipo 'Aplicativo de Desktop' e faça o download do novo 'credentials.json'.")
                logging.info('   4. Substitua o credentials.json na raiz do projeto e rode o script novamente.')
            elif '404' in str_erro or 'notFound' in str_erro:
                logging.warning('--> MOTIVO DO ERRO 404 <--')
                logging.warning(f"A pasta com ID '{self.folder_id}' não foi encontrada ou a credencial do Google não tem permissão de acesso.")
                try:
                    import json
                    if self.credentials_path.exists():
                        with open(self.credentials_path, 'r') as f:
                            dados = json.load(f)
                            email_servico = dados.get('client_email')
                            if email_servico:
                                logging.info(f'SOLUÇÃO: Abra a pasta no Google Drive (https://drive.google.com/drive/folders/{self.folder_id})')
                                logging.info(f"   Clique em 'Compartilhar' e adicione o e-mail abaixo com permissão de EDITOR:")
                                logging.info(f' --> {email_servico}')
                except Exception:
                    pass
            return None
