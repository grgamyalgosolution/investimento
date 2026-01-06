from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import pandas as pd
import requests
import datetime 
import calendar 
import dias_uteis as du



class GabrielInvestimentos:
    def __init__(self, url):
        self.path = f'{os.path.dirname(__file__) }/dados.pkl'
        self.url = url
        self.data = self.get_data()
        self.N = 1
        self.dias_atrasados = 10
        ini, fim = self.inicio_saida(300)
        self.cdi_d = self.get_bcb_series(12, ini, fim)
        self.selic = self.get_bcb_series(11) #diária
        self.selic_meta = self.get_bcb_series(432) #meta
        self._ipca_focus_cache = None
        self._ipca_mes_cache = None




    def get_data(self):
        if os.path.exists(self.path):
            return pd.read_pickle(self.path)


        options = Options()
        options.add_argument("--start-maximized")
        # options.add_argument("--headless")  # se quiser rodar sem abrir o navegador

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 20)

        
        driver.get(self.url)

        # Aguarda os cards carregarem (Angular)
        dados = []
        while True:
            cards = wait.until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "mat-card"))
            )

            # espera os cards da página atual


            for card in cards:
                try:
                    # Nome do banco
                    banco = card.find_element(By.TAG_NAME, "mat-card-subtitle").text.strip()
                    tipo_contrato = card.find_element(By.TAG_NAME, "mat-card-title").text.strip()


                    vencimento = card.find_element(
                        By.XPATH,
                        ".//label[contains(text(),'Vencimento')]/following-sibling::span"
                    ).text
                    vencimento = int(vencimento.replace(" dias", ""))

                    taxa = card.find_element( By.XPATH, ".//span[contains(text(),'Taxa')]/following::p[1]/span[1]" ).text.strip()
                    taxa, tipo_taxa = self.solve_taxa(taxa)
                    dados.append([banco, tipo_contrato, vencimento, taxa, tipo_taxa])

                except Exception:
                    # ignora cards incompletos
                    pass
            # 🔽 tentar ir para próxima página
            try:
                next_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button[aria-label='próxima página']")
                    )
                )

                # se estiver desabilitado, acabou
                if (
                    next_button.get_attribute("disabled") is not None
                    or "mat-button-disabled" in next_button.get_attribute("class")
                ):
                    break

                next_button.click()

                # espera a página trocar (cards antigos sumirem)
                wait.until(EC.staleness_of(cards[0]))

            except Exception:
                break
        driver.quit()
        columns = ["Banco", "Tipo_contrato", "Vencimento", "Taxa%", "Taxa_tipo"]
        
        # Convert to DataFrame 
        df = pd.DataFrame(dados, columns=columns) 

        df.to_pickle(self.path) 
        self.data = df
        return df

        
    
    def solve_taxa(self, taxa):
        taxa = taxa.split()
        first_val = taxa[0]
        tax_val = None
        tax_tipo = None

        if '%' in first_val:
            
            tax_val = float(first_val.replace('%', "").replace(',', '.'))

            if len(taxa) == 1:
                tax_tipo = 'PRE'
            else:
                tax_tipo = 'CDI_PCT'
        elif first_val == 'IPCA':
            tax_val = float(taxa[1].replace('%', "").replace(',', '.').replace('+', ''))
            tax_tipo = first_val
        elif first_val == 'CDI':
            # raise Exception('entrou')
            tax_val = float(taxa[2].replace('%', "").replace(',', '.'))
            tax_tipo = 'CDI_SPREAD'
        else:
            raise Exception('Something went wrong!')
        return tax_val, tax_tipo

        


    def ir_cdb(self,dias):
        if dias <= 180:
            return 0.225
        elif dias <= 360:
            return 0.20
        elif dias <= 720:
            return 0.175
        return 0.15
    

    def get_cdi_diario(self, start, end):
        df = self.cdi_d.copy()
        df["valor"] = df["valor"].astype(float) / 100
    
        mask = (df["data"] >= start) & (df["data"] <= end)
        df = df.loc[mask]

        if df.empty:
            raise ValueError(
                f"CDI diário inexistente no intervalo {start.date()} → {end.date()}"
            )
        return df.sort_values("data").reset_index(drop=True)

    
    def rendimento_cdi_pct_real(self, valor, pct_cdi, dias):
        data_inicio, data_fim = self.inicio_saida(dias)
        df = self.get_cdi_diario(data_inicio, data_fim)

        # CDI já é diário (% a.d.)
        cdi_dia = df["valor"] 

        # percentual do CDI
        cdi_ativo = cdi_dia * (pct_cdi / 100)

        fator = (1 + cdi_ativo).prod()
        return valor * fator


    def rendimento_pre(self, valor, taxa_aa, dias):
        taxa = taxa_aa / 100
        return valor * (1 + taxa) ** (dias / 365)
    
    def rendimento_cdi_spread_real(self, valor, spread_aa, dias):
        data_inicio, data_fim = self.inicio_saida(dias)
        df = self.get_cdi_diario(data_inicio, data_fim)

        spread_dia = (1 + spread_aa / 100) ** (1 / 252) - 1
        fator = ((1 + df["valor"]) * (1 + spread_dia)).prod()
        return valor * fator

        
    def rendimento_ipca_real(self, valor, spread_aa, dias):
        data_inicio, data_fim = self.inicio_saida(dias)

        fator_ipca = self.ipca_fator_periodo(data_inicio, data_fim)

        dias_uteis = self.contar_dias_uteis(data_inicio, data_fim)
        fator_real = (1 + spread_aa / 100) ** (dias_uteis / 252)

        return valor * fator_ipca * fator_real


        
    
    def contar_dias_uteis(self, data_inicio, data_fim):
        dias = pd.date_range(data_inicio, data_fim, freq="D")
        return sum(1 for d in dias if du.is_du(d.date()))


    def ipca_fator_periodo(self, data_inicio, data_fim):
        

        ipca_hist = self.get_ipca_mensal().copy()

        # IPCA implícito (Focus + prêmio de mercado)
        ipca_proj_aa = self.get_ipca_focus_12m()
        ipca_proj_m = (1 + ipca_proj_aa) ** (1 / 12) - 1

        fator = 1.0
        meses = pd.period_range(data_inicio, data_fim, freq="M")

        for mes in meses[:-1]:
            mes_ref = mes - 2
            val = ipca_hist.loc[ipca_hist["mes"] == mes_ref, "valor"]

            if not val.empty:
                fator *= (1 + val.iloc[0])
            else:
                fator *= (1 + ipca_proj_m)

        # 🔥 pró-rata do último mês
        ultimo_mes = meses[-1]
        mes_ref = ultimo_mes - 2
        dias_mes = calendar.monthrange(data_fim.year, data_fim.month)[1]
        proporcao = data_fim.day / dias_mes

        val = ipca_hist.loc[ipca_hist["mes"] == mes_ref, "valor"]
        ipca_ultimo = val.iloc[0] if not val.empty else ipca_proj_m

        fator *= (1 + ipca_ultimo * proporcao)

        return fator


    def fator_juros_reais(self, spread_aa, data_inicio, data_fim):
        dias_corridos = (data_fim - data_inicio).days
        return (1 + spread_aa / 100) ** (dias_corridos / 365)


    
    def get_ipca_mensal(self):
        if self._ipca_mes_cache is not None:
            return self._ipca_mes_cache
        df = self.get_bcb_series(433)
        df["valor"] = df["valor"] / 100
        df["mes"] = df["data"].dt.to_period("M")
        self._ipca_mes_cache = df[["mes", "valor"]]
        return df[["mes", "valor"]]

    def get_ipca_focus_12m(self):
        if self._ipca_focus_cache is not None:
            return self._ipca_focus_cache

        df = self.get_bcb_series(10844)
        df["valor"] = df["valor"] / 100

        ipca_aa = df.iloc[-1]["valor"]
        self._ipca_focus_cache = ipca_aa

        return ipca_aa


    
    def _limit_to_today(self, date_str):
        hoje = datetime.datetime.now().date()
        d = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
        return min(d, hoje).strftime("%d/%m/%Y")
    
    


    def reset_data(self, url=None):
        os.remove(self.path)
        if url is not None:
            self.url = url
        self.get_data()


    def calcular_rendimentos(self, valor_inicial=1.0):
        valor_inicial *= 1000
        resultados = []

        for _, row in self.data.iterrows():
            banco = row["Banco"]
            tipo = row["Tipo_contrato"]
            dias = row["Vencimento"]
            taxa = row["Taxa%"]
            taxa_tipo = row["Taxa_tipo"]

            # 🔢 valor bruto
            if taxa_tipo == "PRE":
                bruto = self.rendimento_pre(valor_inicial, taxa, dias)

            elif taxa_tipo == "CDI_PCT":
                bruto = self.rendimento_cdi_pct_real(valor_inicial, taxa, dias)

            elif taxa_tipo == "CDI_SPREAD":
                bruto = self.rendimento_cdi_spread_real(valor_inicial, taxa, dias)

            elif taxa_tipo == "IPCA":
                if dias <= 90:
                    continue  # ou lançar warning
                bruto = self.rendimento_ipca_real(valor_inicial, taxa, dias)

            else:
                continue  # segurança

            # 💸 IR
            aliquota_ir = self.ir_cdb(dias)
            lucro = bruto - valor_inicial
            ir = lucro * aliquota_ir
            liquido = bruto - ir

            resultados.append({
                "Banco": banco,
                "Tipo_contrato": tipo,
                "Taxa_tipo": taxa_tipo,
                "Taxa%": taxa,
                "Vencimento (dias)": dias,
                "Valor inicial": valor_inicial,
                "Valor bruto": round(bruto, 2),
                "IR": round(ir, 2),
                "Valor líquido": round(liquido, 2),
                "Rentabilidade líquida (%)": round((liquido / valor_inicial - 1) * 100, 2)
            })

        df_result = pd.DataFrame(resultados)

        # ranking
        df_result.sort_values("Rentabilidade líquida (%)", ascending=False, inplace=True)

        return df_result

    def inicio_saida(self, dias):
        data_fim = pd.Timestamp(du.last_du())
        data_inicio = data_fim - pd.Timedelta(days=dias)
        return data_inicio, data_fim



    def get_bcb_series(self, code, start=None, end=None):
        if start:
            start = self._limit_to_today(start.strftime("%d/%m/%Y"))
        if end:
            end = self._limit_to_today(end.strftime("%d/%m/%Y"))

        if start:
            url = (
                f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
                f"?formato=json&dataInicial={start}&dataFinal={end}"
            )
        else:
            url = (
                f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{self.N}"
                f"?formato=json"
            )

        r = requests.get(url)

        if r.status_code == 404:
            raise ValueError("BCB: intervalo futuro ou inexistente")

        r.raise_for_status()

        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("BCB retornou série vazia")

        df = pd.DataFrame(data)

        if "data" not in df or "valor" not in df:
            raise ValueError(f"Formato inesperado do BCB: {df.columns}")

        df["data"] = pd.to_datetime(df["data"], dayfirst=True)
        df["valor"] = df["valor"].astype(float)

        return df

    def exportar(self, format, data=None):
        if format == 'xlsx':
            if data is not None:
                data.to_excel(f"dados.{format}", index=False)
            else:
                self.data.to_excel(f"dados.{format}", index=False)
        elif format == 'csv':
            if data is not None:
                data.to_csv(f"dados.{format}", index=False)
            else:
                self.data.to_csv(f"dados.{format}", index=False)



# url = 'https://apprendafixa.com.br/app/investimentos/rendafixa?tipo=ALL&fgc=true&vencimentoInicio=1&vencimentoFim=180&irInicio=0&irFim=0.225&riscoInicio=0&riscoFim=1'

# gbr_invest = GabrielInvestimentos(url)
# result = gbr_invest.calcular_rendimentos(200)