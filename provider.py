import os
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProcessingProvider, QgsApplication
from .algorithms.least_cost_route import LeastCostRouteAlgorithm

class TrafegabilidadeProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(LeastCostRouteAlgorithm())
    def id(self): return 'trafegabilidade_tools'
    def name(self): return 'Off-Road Explorer'
class TrafegabilidadeProviderPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None
        self.toolbar = None
    def initGui(self):
        # registra provider no Processing
        self.provider = TrafegabilidadeProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)
        # cria ação com ícone e adiciona na barra
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'icon_route.png')
        self.action = QAction(QIcon(icon_path), 'Off-Road Explorer', self.iface.mainWindow())
        self.action.triggered.connect(self.run_algorithm)
        self.toolbar = self.iface.addToolBar('Off-Road Explorer')
        self.toolbar.addAction(self.action)
        # também adiciona no menu Plugins
        try:
            self.iface.addPluginToMenu('&Off-Road Explorer', self.action)
        except Exception:
            pass
    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        if self.action:
            try:
                self.iface.removeToolBarIcon(self.action)
            except Exception:
                pass
            try:
                self.iface.removePluginMenu('&Off-Road Explorer', self.action)
            except Exception:
                pass
            self.action = None
        if self.toolbar:
            try:
                self.iface.mainWindow().removeToolBar(self.toolbar)
            except Exception:
                pass
            self.toolbar = None

    def run_algorithm(self):
        try:
            import processing
            # abre a caixa de parâmetros do algoritmo do Processing
            processing.execAlgorithmDialog('trafegabilidade_tools:least_cost_route_grass_plus_merge', {})
        except Exception as e:
            # Log seguro independente da UI
            try:
                from qgis.core import Qgis, QgsMessageLog
                QgsMessageLog.logMessage(str(e), 'Off-Road Explorer', Qgis.Critical)
            except Exception:
                pass
            try:
                self.iface.messageBar().pushWarning('Off-Road Explorer', str(e))
            except Exception:
                pass

