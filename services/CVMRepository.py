import pyodbc
import pandas as pd
import logging
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CVMRepository:
    '''
    Classe responsável pelas operações de persistência e carga no banco SQL Server.
    '''

    COLUNAS_TABELA = [
        'TP_FUNDO', 'CNPJ_FUNDO', 'DENOM_SOCIAL', 'DT_REG', 'DT_CONST', 'CD_CVM',
        'DT_CANCEL', 'SIT', 'DT_INI_SIT', 'DT_INI_ATIV', 'DT_INI_EXERC', 'DT_FIM_EXERC',
        'CLASSE', 'DT_INI_CLASSE', 'RENTAB_FUNDO', 'CONDOM', 'FUNDO_COTAS', 'FUNDO_EXCLUSIVO',
        'TRIB_LPRAZO', 'PUBLICO_ALVO', 'ENTID_INVEST', 'TAXA_PERFM', 'INF_TAXA_PERFM',
        'TAXA_ADM', 'INF_TAXA_ADM', 'VL_PATRIM_LIQ', 'DT_PATRIM_LIQ', 'DIRETOR',
        'CNPJ_ADMIN', 'ADMIN', 'PF_PJ_GESTOR', 'CPF_CNPJ_GESTOR', 'GESTOR',
        'CNPJ_AUDITOR', 'AUDITOR', 'CNPJ_CUSTODIANTE', 'CUSTODIANTE',
        'CNPJ_CONTROLADOR', 'CONTROLADOR', 'INVEST_CEMPR_EXTER', 'CLASSE_ANBIMA'
    ]

    def __init__(self, tabela: str = 'Carteira.CVM_FI'):
        self.tabela = tabela

    def limpar_tabela(self, cursor: pyodbc.Cursor) -> None:
        '''
        Executa TRUNCATE TABLE para garantir carga limpa e atualizada dos dados.
        '''
        logging.info(f"Limpando registros antigos da tabela {self.tabela} (TRUNCATE)...")
        cursor.execute(f"TRUNCATE TABLE {self.tabela}")
        logging.info("Tabela limpa com sucesso.")

    def inserir_dados(self, conn: pyodbc.Connection, df: pd.DataFrame, truncar: bool = True, tamanho_lote: int = 5000) -> int:
        '''
        Insere o DataFrame em lotes (chunks) no SQL Server utilizando fast_executemany para controle de memória e log de progresso.
        '''
        cursor = conn.cursor()

        if truncar:
            self.limpar_tabela(cursor)

        # Garantir que todas as colunas necessárias existam no DataFrame (preencher ausentes com None)
        df_para_inserir = df.copy()
        for col in self.COLUNAS_TABELA:
            if col not in df_para_inserir.columns:
                df_para_inserir[col] = None

        # Reordenar colunas exatamente conforme a definição da tabela
        df_para_inserir = df_para_inserir[self.COLUNAS_TABELA]

        # Converter valores para tipos nativos do Python que o pyodbc manipula sem erros
        def para_tipo_nativo(val):
            if val is None or pd.isna(val) or val == 'NaT' or str(val).lower() in ('nan', 'none'):
                return None
            if hasattr(val, 'item'):
                val = val.item()
            if isinstance(val, (int, float, str)):
                return val
            return str(val)

        registros_tuplas = [
            tuple(para_tipo_nativo(val) for val in row)
            for row in df_para_inserir.itertuples(index=False)
        ]

        # Montar a instrução SQL parametrizada
        colunas_sql = ", ".join(self.COLUNAS_TABELA)
        placeholders = ", ".join(["?"] * len(self.COLUNAS_TABELA))
        sql = f"INSERT INTO {self.tabela} ({colunas_sql}) VALUES ({placeholders})"

        total_registros = len(registros_tuplas)
        logging.info(f"Iniciando a inserção dividida em lotes de {tamanho_lote} registros (Total: {total_registros})...")
        
        # Habilitar inserção em alta velocidade do pyodbc
        cursor.fast_executemany = True

        # Processar a inserção dividida em lotes (chunks)
        registros_inseridos = 0
        for i in range(0, total_registros, tamanho_lote):
            lote = registros_tuplas[i:i + tamanho_lote]
            cursor.executemany(sql, lote)
            registros_inseridos += len(lote)
            num_lote = (i // tamanho_lote) + 1
            logging.info(f"Lote {num_lote}: {registros_inseridos}/{total_registros} registros inseridos...")

        logging.info(f"Carga concluída com sucesso! Total de {registros_inseridos} registros inseridos na tabela {self.tabela}.")
        return registros_inseridos


