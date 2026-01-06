
from settings import pd, calendar

class Rendimentos:
    def __init__(self, app):
        self.app = app
        self.data = app.data
        self.bcb_api = app.bcb_api
        self.data_handler = app.data_handler


    def rendimento_cdi_pct_real(self, valor, pct_cdi, dias):
        data_inicio, data_fim = self.data_handler.inicio_saida(dias)
        df = self.bcb_api.get_cdi_diario(data_inicio, data_fim)

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
        data_inicio, data_fim = self.data_handler.inicio_saida(dias)
        df = self.bcb_api.get_cdi_diario(data_inicio, data_fim)

        spread_dia = (1 + spread_aa / 100) ** (1 / 252) - 1
        fator = ((1 + df["valor"]) * (1 + spread_dia)).prod()
        return valor * fator

        
    def rendimento_ipca_real(self, valor, spread_aa, dias):
        data_inicio, data_fim = self.data_handler.inicio_saida(dias)

        fator_ipca = self.ipca_fator_periodo(data_inicio, data_fim)

        dias_uteis = self.data_handler.contar_dias_uteis(data_inicio, data_fim)
        fator_real = (1 + spread_aa / 100) ** (dias_uteis / 252)

        return valor * fator_ipca * fator_real


        
    

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
            rent = round((liquido / valor_inicial - 1) * 100, 3)
            taxa_eq_aa = (liquido / valor_inicial) ** (365 / dias) - 1

            resultados.append({
                "Banco": banco,
                "Tipo_contrato": tipo,
                "Taxa_tipo": taxa_tipo,
                "Taxa%": taxa,
                "Vencimento": dias,
                "Valor_inicial": valor_inicial,
                "Valor_bruto": round(bruto, 2),
                "IR": round(ir, 2),
                "Valor_liquido": round(liquido, 2),
                "Rentabilidade_liquida%": rent,
                "Rentabilidade/Vencimento": taxa_eq_aa
            })

        df_result = pd.DataFrame(resultados)

        # ranking
        df_result.sort_values("Rentabilidade/Vencimento", ascending=False, inplace=True)

        return df_result

    def ir_cdb(self, dias):
        if dias <= 180:
            return 0.225
        elif dias <= 360:
            return 0.20
        elif dias <= 720:
            return 0.175
        return 0.15
    
    def ipca_fator_periodo(self, data_inicio, data_fim):
    

        ipca_hist = self.bcb_api.ipca_mes.copy()

        # IPCA implícito (Focus + prêmio de mercado)
        ipca_proj_aa = self.bcb_api.ipca_focus
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

