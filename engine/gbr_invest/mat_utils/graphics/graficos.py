import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
# from settings import plt
class Graficos:
    def __init__(self):
        self.figs = {}

    def start_fig(self, id, size):
        if id not in self.figs:
            fig, ax = plt.subplots(figsize=size)
            self.figs[id] = (fig, ax)
        return self.figs[id]

    def DFC(self, tempo:list[int], fluxo:list[int]):
        fig, ax = self.start_fig("DFC", size=(8, 8))
        ax.axhline(0)
        # Linha do tempo
        # Setas dos fluxos
        for t, cf in zip(tempo, fluxo):
            ax.arrow(
                t, 0,
                0, cf,
                length_includes_head=True,
                head_width=15,
                head_length=80,
                linewidth=2
            )
        ax.set_xlabel("Tempo (dias)")
        ax.set_ylabel("Fluxo de Caixa (R$)")
        ax.set_title("Diagrama de Fluxo de Caixa – CDB")
        ax.set_xticks(tempo)
        ax.grid(True, axis="x", linestyle="--", alpha=0.6)
        
        fig.tight_layout()
        self.show()
        
    def save(self, fig, nome):
        fig.savefig(nome, dpi=150, bbox_inches="tight")
    
    def show(self):
        plt.show()

    def close(self, id=None):
        if id and id in self.figs:
            plt.close(self.figs[id][0])
            del self.figs[id]
        else:
            plt.close('all')
            self.figs.clear()


