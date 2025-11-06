from .provider import TrafegabilidadeProviderPlugin

def classFactory(iface):
    return TrafegabilidadeProviderPlugin(iface)
