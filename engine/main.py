
from settings import os, DataHandler, GetData, BCB_Series, Rendimentos



class GabrielInvestimentos:
    def __init__(self, url = None):
        self.url = url if url is not None else 'https://apprendafixa.com.br/app/investimentos/rendafixa?tipo=ALL&fgc=true&vencimentoInicio=1&vencimentoFim=180&irInicio=0&irFim=0.225&riscoInicio=0&riscoFim=1'
        self.on_init()
    
    def on_init(self):
        self.data_handler = DataHandler(self)
        self.get_data = GetData(self)
        self.data = self.get_data.data
        self.bcb_api = BCB_Series(self)
        self.rendimentos = Rendimentos(self)




# url = 'https://apprendafixa.com.br/app/investimentos/rendafixa?tipo=ALL&fgc=true&vencimentoInicio=1&vencimentoFim=180&irInicio=0&irFim=0.225&riscoInicio=0&riscoFim=1'

# gbr_invest = GabrielInvestimentos(url)
# gbr_invest.rendimentos.calcular_rendimentos(200)