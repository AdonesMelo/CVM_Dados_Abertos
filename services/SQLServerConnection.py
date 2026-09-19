import pyodbc
import logging

# configuração do log para o monitoramento de conexão
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SQLServerConnection:
    '''
    Gerenciamento de conexão com o banco de dados SQL Server usando o Context Manager
    '''
    def __init__(self, server: str, database: str, user: str, password: str, driver: str = '{ODBC Driver 17 for SQL Server}'):
        self.server = server
        self.database = database
        self.user = user
        self.password = password
        self.driver = driver
        self.connection = None

        # Montar uma string de conexão com o formato esperado pelo pyodbc
        self.conn_str = (
            f'DRIVER={self.driver};'
            f'SERVER={self.server};'
            f'DATABASE={self.database};'
            f'UID={self.user};'
            f'PWD={self.password};'
        )

    def __enter__(self):
        '''
        Metodo chamado ao entrar no bloco 'with'. Abre a conexão com o banco de dados
        '''
        try:
            self.connection = pyodbc.connect(self.conn_str)
            logging.info(f'Conexão aberta com sucesso com o servidor {self.database}')
            return self.connection
        except pyodbc.Error as erro:
            logging.error(f'Erro ao conectar ao banco de dados: {erro}')
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        '''
        Metodo chamado ao sair do bloco 'with'. Fecha a conexão com o banco de dados
        Faz o commit  se deu todo certo e rollback caso de erro, e fecha a conexão
        '''
        try:
            if self.connection:
                if exc_type is not None:
                    # Ocorreu uma erro no bloco 'with', faz o rollback
                    self.connection.rollback()
                    logging.warning(f'Erro detectado. Rollback realizado com sucesso.')
                else:
                    # Sem erros, faz o commit
                    self.connection.commit()

                self.connection.close()
                logging.info(f'Conexão fechada com sucesso.')
        except pyodbc.Error as erro:
            logging.error(f'Erro ao fechar a conexão: {erro}')
            raise
