import os
import logging
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GoogleDriveUploader:
    '''
    Serviço de automação web utilizando a biblioteca Playwright para
    fazer upload do arquivo limpo para o Google Drive (equipe da Controladoria).
    Utiliza o perfil do Google Chrome do sistema para reaproveitar a sessão logada do usuário.
    '''

    def __init__(self, url_drive: str = 'https://drive.google.com', headless: bool = False, user_data_dir: Optional[str] = None, use_system_chrome: bool = True):
        self.url_drive = url_drive
        self.headless = headless
        self.use_system_chrome = use_system_chrome

        if user_data_dir:
            self.user_data_dir = user_data_dir
        else:
            # Perfil padrão do Google Chrome no Windows
            chrome_user_data = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data')
            if use_system_chrome and Path(chrome_user_data).exists():
                self.user_data_dir = chrome_user_data
            else:
                self.user_data_dir = str(Path(r'.\Temp_File\browser_profile').resolve())

    def upload_arquivo(self, caminho_arquivo: str) -> bool:
        '''
        Abre o navegador Google Chrome via Playwright utilizando o perfil de usuário existente.
        '''
        arquivo = Path(caminho_arquivo).resolve()
        if not arquivo.exists():
            raise FileNotFoundError(f"Arquivo para upload não encontrado: {arquivo}")

        logging.info(f'Iniciando automação Playwright para upload do arquivo {arquivo.name} no Google Drive...')
        logging.info(f'Perfil do Chrome utilizado: {self.user_data_dir}')

        args_anti_bot = [
            '--disable-blink-features=AutomationControlled',
            '--start-maximized'
        ]

        with sync_playwright() as p:
            try:
                if self.use_system_chrome:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=self.user_data_dir,
                        channel='chrome',
                        headless=self.headless,
                        ignore_default_args=['--enable-automation'],
                        args=args_anti_bot
                    )
                else:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=self.user_data_dir,
                        headless=self.headless,
                        ignore_default_args=['--enable-automation'],
                        args=args_anti_bot
                    )
            except Exception as e_launch:
                logging.warning(f'O perfil principal do Chrome pode estar em uso ({e_launch}).')
                logging.info('Utilizando perfil de navegador dedicado em Temp_File/browser_profile...')
                fallback_dir = str(Path(r'.\Temp_File\browser_profile').resolve())
                context = p.chromium.launch_persistent_context(
                    user_data_dir=fallback_dir,
                    channel='chrome',
                    headless=self.headless,
                    ignore_default_args=['--enable-automation'],
                    args=args_anti_bot
                )


            page = context.pages[0] if context.pages else context.new_page()

            try:
                logging.info(f'Navegando para a pasta do Google Drive: {self.url_drive}')
                page.goto(self.url_drive, timeout=60000, wait_until='domcontentloaded')
                page.wait_for_timeout(4000)

                # Se redirecionou para login, aguarda o usuário logar/validar PIN se necessário
                if 'accounts.google.com' in page.url or page.query_selector('input[type="email"]'):
                    logging.info('--> TELA DE LOGIN / PIN DETECTADA <--')
                    logging.info('Por favor, conclua o login/PIN na janela do navegador para acessar a pasta...')
                    try:
                        page.wait_for_url(lambda u: 'accounts.google.com' not in u, timeout=120000)
                        logging.info('Login realizado! Navegando para a pasta...')
                        page.goto(self.url_drive, timeout=60000, wait_until='domcontentloaded')
                        page.wait_for_timeout(4000)
                    except Exception:
                        logging.warning('Tempo limite de login expirou.')

                logging.info(f'Iniciando o upload do arquivo {arquivo.name} ({arquivo.stat().st_size / (1024*1024):.2f} MB)...')

                # Método 1: Tentar injetar diretamente nos inputs do tipo file do Google Drive
                upload_sucesso = False
                inputs_file = page.query_selector_all('input[type="file"]')
                if inputs_file:
                    for input_elem in inputs_file:
                        try:
                            input_elem.set_input_files(str(arquivo))
                            upload_sucesso = True
                            logging.info(f'Arquivo anexado com sucesso via seletor de arquivo do Google Drive!')
                            break
                        except Exception:
                            continue

                # Método 2: Se o método 1 não funcionou, usar o menu "Novo" -> "Upload de arquivo"
                if not upload_sucesso:
                    logging.info("Buscando botão 'Novo' ou menu de upload da pasta...")
                    botao_novo = page.query_selector("button:has-text('Novo'), button:has-text('New'), [aria-label*='Novo'], [aria-label*='New']")
                    if botao_novo:
                        try:
                            with page.expect_file_chooser(timeout=10000) as fc_info:
                                botao_novo.click()
                                page.wait_for_timeout(1000)
                                page.click('text=/Upload de arquivo|File upload/i')
                            file_chooser = fc_info.value
                            file_chooser.set_files(str(arquivo))
                            upload_sucesso = True
                            logging.info("Arquivo anexado com sucesso via FileChooser do botão 'Novo'!")
                        except Exception as e_fc:
                            logging.warning(f'Não foi possível abrir o FileChooser: {e_fc}')

                if upload_sucesso:
                    logging.info('Aguardando o término do envio (upload) do arquivo para o Google Drive...')
                    # Aguardar o upload do arquivo (15MB leva alguns segundos)
                    page.wait_for_timeout(15000)
                    logging.info(f'Upload do arquivo {arquivo.name} para a pasta {self.url_drive} CONCLUÍDO com sucesso!')
                    return True
                else:
                    logging.warning('Não foi possível localizar o seletor de upload na página do Google Drive.')
                    return False

            except Exception as erro:
                logging.warning(f'Ocorreu uma falha no Playwright durante o upload: {erro}')
                return False
            finally:
                context.close()




