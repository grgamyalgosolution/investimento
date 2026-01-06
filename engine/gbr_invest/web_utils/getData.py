from settings import Options, webdriver, WebDriverWait, pd, By, EC, os
class GetData:
    def __init__(self, app):
        self.app = app
        self.path =  f'{os.path.dirname(os.path.dirname(__file__)) }/exports/dados.pkl'
        self.url = app.url
        self.data = self.get_data()

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
            tax_val = float(taxa[2].replace('%', "").replace(',', '.'))
            tax_tipo = 'CDI_SPREAD'
        else:
            raise Exception('Something went wrong!')
        return tax_val, tax_tipo

        
    def reset_data(self, url=None):
        os.remove(self.path)
        if url is not None:
            self.url = url
        self.data = self.get_data()
    

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