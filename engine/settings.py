import subprocess, sys, os, calendar, datetime, requests, importlib

modulos = [["numpy", None], ["pandas", None], ["dias_uteis", None], ["selenium", None], ["selenium.webdriver", "webdriver-manager"]]
def search_modules(pacote, pip_name=None, obj=None): 
    
    pip_name = pip_name if pip_name is not None else pacote
    try:
        mod = importlib.import_module(pacote)
        if obj is not None:
            getattr(mod, obj)

    except ImportError: 
        print(f"Pacote {pacote} não encontrado. Instalando...") 
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])  
for pct_name, pip_name in modulos:
    search_modules(pct_name, pip_name)
import pandas as pd
import numpy as np
import dias_uteis as du
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from gbr_invest.web_utils.getData import GetData
from gbr_invest.mat_utils.data_handler import DataHandler
from gbr_invest.mat_utils.rendimentos import Rendimentos
from gbr_invest.API.bcb_series import BCB_Series