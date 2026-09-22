import pandas as pd
import numpy as np
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProcessadorCVM:
    '''
    Classe responsável pela leitura, sanitização, limpeza e tipagem
    dos dados abertos de fundos de investimento da CVM.
    '''
    
    COLUNAS_CNPJ = [
        'CNPJ_FUNDO', 'CNPJ_ADMIN', 'CPF_CNPJ_GESTOR',
        'CNPJ_AUDITOR', 'CNPJ_CUSTODIANTE', 'CNPJ_CONTROLADOR'
    ]

    COLUNAS_DATAS = [
        'DT_REG', 'DT_CONST', 'DT_CANCEL', 'DT_INI_SIT',
        'DT_INI_ATIV', 'DT_INI_EXERC', 'DT_FIM_EXERC',
        'DT_INI_CLASSE', 'DT_PATRIM_LIQ'
    ]

    COLUNAS_NUMERICAS_FLOAT = [
        'TAXA_PERFM', 'TAXA_ADM', 'VL_PATRIM_LIQ'
    ]

    COLUNAS_NUMERICAS_INT = [
        'CD_CVM'
    ]

    def __init__(self, caminho_csv: str, encoding: str = 'latin1', sep: str = ';'):
        self.caminho_csv = Path(caminho_csv)
        self.encoding = encoding
        self.sep = sep

    def _limpar_cnpj(self, serie: pd.Series) -> pd.Series:
        '''
        Remove caracteres especiais (pontos, barras e traços) de colunas de CNPJ/CPF.
        '''
        return serie.astype(str).str.replace(r'[\.\/\-\s]', '', regex=True).replace({'nan': None, 'None': None, '': None})

    def processar(self) -> pd.DataFrame:
        '''
        Executa o pipeline completo de limpeza e tratamento dos dados.
        Retorna um DataFrame tratado e pronto para carga no banco de dados.
        '''
        if not self.caminho_csv.exists():
            raise FileNotFoundError(f"Arquivo CSV não encontrado em: {self.caminho_csv}")

        logging.info(f"Lendo o arquivo CSV: {self.caminho_csv}")
        # Carregamos como string por padrão para evitar interpretações incorretas de tipo durante a leitura inicial
        df = pd.read_csv(
            self.caminho_csv,
            sep=self.sep,
            encoding=self.encoding,
            dtype=str,
            low_memory=False
        )

        total_linhas_inicial = len(df)
        logging.info(f"Total de registros carregados do CSV: {total_linhas_inicial}")

        # 1. Limpeza de colunas CNPJ / CPF (remover pontos, barras e hífen)
        logging.info("Higienizando colunas de CNPJ / CPF...")
        for col in self.COLUNAS_CNPJ:
            if col in df.columns:
                df[col] = self._limpar_cnpj(df[col])

        # 2. Remoção de registros duplicados com base na Primary Key (CNPJ_FUNDO)
        if 'CNPJ_FUNDO' in df.columns:
            # Garante que registros com CNPJ nulo sejam removidos pois CNPJ_FUNDO é chave primária
            df = df.dropna(subset=['CNPJ_FUNDO'])
            df = df[df['CNPJ_FUNDO'].str.len() > 0]
            
            linhas_antes_dedup = len(df)
            df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')
            duplicadas_removidas = linhas_antes_dedup - len(df)
            if duplicadas_removidas > 0:
                logging.info(f"Removidos {duplicadas_removidas} registros duplicados de CNPJ_FUNDO.")

        # 3. Limpeza de espaços em branco em colunas do tipo texto e substituição de vazios/nan por None
        logging.info("Tratando valores nulos e limpando textos...")
        for col in df.columns:
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
            df[col] = df[col].replace({'': None, 'nan': None, 'None': None, np.nan: None})

        # 4. Tratamento e validação de datas (formato YYYY-MM-DD)
        logging.info("Convertendo e formatando colunas de datas...")
        for col in self.COLUNAS_DATAS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
                df[col] = df[col].replace({np.nan: None, 'NaT': None, '': None})

        # 5. Tratamento de colunas numéricas
        logging.info("Convertendo colunas numéricas...")
        for col in self.COLUNAS_NUMERICAS_FLOAT:
            if col in df.columns:
                # Substitui vírgula por ponto para conversão correta em float caso venha formatado no PT-BR
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].replace({np.nan: None})

        for col in self.COLUNAS_NUMERICAS_INT:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Converter para Int64 do pandas que aceita nulos antes do to_dict
                df[col] = df[col].astype('Int64')

        # Substituir quaisquer resíduos de NaN do pandas/numpy por None (SQL NULL)
        df = df.where(pd.notnull(df), None)

        logging.info(f"Tratamento finalizado. Registros válidos e tratados: {len(df)}")
        return df

    def salvar_csv(self, df: pd.DataFrame, pasta_destino: str, nome_arquivo: str = 'cad_fi_tratado.csv') -> str:
        '''
        Salva o DataFrame tratado em formato CSV na pasta de destino informada.
        '''
        caminho_dir = Path(pasta_destino)
        caminho_dir.mkdir(parents=True, exist_ok=True)
        caminho_completo = caminho_dir / nome_arquivo

        logging.info(f"Salvando dados tratados em: {caminho_completo}")
        df.to_csv(caminho_completo, sep=self.sep, index=False, encoding=self.encoding)
        logging.info(f"Arquivo limpo salvo com sucesso em: {caminho_completo}")
        return str(caminho_completo)

    def obter_registros_para_banco(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        '''
        Converte o DataFrame tratado em uma lista de dicionários pronta para inserção via pyodbc.
        '''
        # Substitui resíduos de float 'nan' ou 'None' por None nativo do Python
        registros = df.to_dict(orient='records')
        for reg in registros:
            for k, v in reg.items():
                if pd.isna(v) or v == 'NaT' or v == 'nan':
                    reg[k] = None
        return registros

