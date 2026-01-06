from settings import datetime, pd, du

class DataHandler:
    def __init__(self, app):
        self.app = app

        
    def _limit_to_today(self, date_str):
        hoje = datetime.datetime.now().date()
        d = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
        return min(d, hoje).strftime("%d/%m/%Y")
    
    
    def inicio_saida(self, dias):
        data_fim = pd.Timestamp(du.last_du())
        data_inicio = data_fim - pd.Timedelta(days=dias)
        return data_inicio, data_fim


    def contar_dias_uteis(self, data_inicio, data_fim):
        dias = pd.date_range(data_inicio, data_fim, freq="D")
        return sum(1 for d in dias if du.is_du(d.date()))