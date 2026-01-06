from settings import requests, pd

class BCB_Series:
    def __init__(self, app):
        self.app = app
        self.data_handler = app.data_handler
        self.N = 1
        self.dias_atrasados = 10
        self.ipca_focus = self.get_ipca_focus_12m()
        self.ipca_mes = self.get_ipca_mensal()
        ini, fim = app.data_handler.inicio_saida(300)
        self.cdi_d = self.get_bcb_series(12, ini, fim)
        self.selic = self.get_bcb_series(11) #diária
        self.selic_meta = self.get_bcb_series(432) #meta
    
    def get_bcb_series(self, code, start=None, end=None):
        if start:
            start = self.data_handler._limit_to_today(start.strftime("%d/%m/%Y"))
        if end:
            end = self.data_handler._limit_to_today(end.strftime("%d/%m/%Y"))

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
    
    def get_ipca_mensal(self):
        df = self.get_bcb_series(433)
        df["valor"] = df["valor"] / 100
        df["mes"] = df["data"].dt.to_period("M")
        self.ipca_mes = df[["mes", "valor"]]
        return df[["mes", "valor"]]

    def get_ipca_focus_12m(self):

        df = self.get_bcb_series(10844)
        df["valor"] = df["valor"] / 100

        ipca_aa = df.iloc[-1]["valor"]
        self.ipca_focus = ipca_aa

        return ipca_aa

