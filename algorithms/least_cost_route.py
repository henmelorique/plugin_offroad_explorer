import os
# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer, QgsProcessingParameterCrs,
    QgsProcessingParameterNumber, QgsProcessingParameterString,
    QgsProcessingParameterFolderDestination, QgsProcessingException,
    QgsVectorLayer, QgsRasterLayer, QgsProject,
    QgsVectorFileWriter, QgsCoordinateTransformContext, QgsFields,
    QgsProcessingParameterBoolean, QgsProcessingParameterDefinition)
import processing, os, uuid, datetime
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProcessingParameterPoint, QgsField, QgsFeature, QgsGeometry, QgsPointXY, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsWkbTypes


from qgis.core import (
    QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSvgMarkerSymbolLayer,
    QgsMarkerSymbol, QgsWkbTypes, QgsProject
)


def _persist_style_on_layer(layer, plugin_dir):
    try:
        from qgis.core import QgsMapLayerStyle
        style = QgsMapLayerStyle(); style.readFromLayer(layer)
        # Try save to database (GPKG) as default
        try:
            layer.saveStyleToDatabase('OffRoadExplorer Default','Auto-saved by plugin', True, '')
        except Exception:
            # Fallback: save .qml next to data source
            src = layer.source()
            import os
            if src and '.' in src:
                qml = os.path.splitext(src)[0] + '.qml'
                layer.saveNamedStyle(qml)
    except Exception:
        pass


def _apply_point_labels_pt(layer):
    """Ativa rótulos 'Origem' e 'Destino' baseados no campo 'role'."""
    try:
        if not layer:
            return
        from qgis.core import QgsTextFormat, QgsProperty, QgsVectorLayerSimpleLabeling, QgsPalLayerSettings
        fmt = QgsTextFormat()
        fmt.setSize(9)
        # buffer leve para legibilidade
        from qgis.core import QgsTextBufferSettings
        buf = QgsTextBufferSettings(); buf.setEnabled(True); buf.setSize(1)
        fmt.setBuffer(buf)
        s = QgsPalLayerSettings()
        s.enabled = True
        s.fieldName = 'label_pt'
        s.isExpression = False
        s.placement = QgsPalLayerSettings.OverPoint
        s.setFormat(fmt)
        labeling = QgsVectorLayerSimpleLabeling(s)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)
        layer.triggerRepaint()
    except Exception:
        pass

def _apply_point_svg_style(layer, plugin_dir):
    """Aplicar ícones branco/azul categorizando por 'role'."""
    try:
        if not layer or layer.wkbType() == QgsWkbTypes.NoGeometry:
            return
        svg_white = os.path.join(plugin_dir, 'icons', 'pin_white.svg')
        svg_blue  = os.path.join(plugin_dir, 'icons', 'pin_blue.svg')

        sym_start = QgsMarkerSymbol()
        sym_start.changeSymbolLayer(0, QgsSvgMarkerSymbolLayer(svg_white, 8.2, 0.0))
        try:
            sym_start.symbolLayer(0).setOffset(0, -2.5)
        except Exception:
            pass

        sym_end = QgsMarkerSymbol()
        sym_end.changeSymbolLayer(0, QgsSvgMarkerSymbolLayer(svg_blue, 8.2, 0.0))
        try:
            sym_end.symbolLayer(0).setOffset(0, -2.5)
        except Exception:
            pass

        renderer = QgsCategorizedSymbolRenderer('role', [
            QgsRendererCategory('start', sym_start, 'Origem'),
            QgsRendererCategory('end',   sym_end,   'Destino'),
        ])
        layer.setRenderer(renderer)
        layer.triggerRepaint()
    except Exception as e:
        try:
            from qgis.core import Qgis, QgsMessageLog
            QgsMessageLog.logMessage(str(e), 'Off-Road Explorer', Qgis.Warning)
        except Exception:
            pass

def _style_any_endpoint_layer_in_project(plugin_dir):
    """Se o plugin salvar/relê os pontos (ex.: GPKG), garante o estilo no layer final visível."""
    try:
        proj = QgsProject.instance()
        for lyr in proj.mapLayers().values():
            try:
                if getattr(lyr, 'geometryType', None) and lyr.geometryType() != 0:
                    continue
                # precisa ter campo 'role'
                if not hasattr(lyr, 'fields') or 'role' not in [f.name() for f in lyr.fields()]:
                    continue
                lname = (lyr.name() or '').lower()
                if 'pontos da rota' in lname or 'endpoint' in lname:
                    _apply_point_svg_style(lyr, plugin_dir); _apply_point_labels_pt(lyr); _persist_style_on_layer(lyr, plugin_dir)
            except Exception:
                continue
    except Exception:
        pass

from qgis.core import (
    QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSvgMarkerSymbolLayer,
    QgsMarkerSymbol, QgsWkbTypes, QgsProject, QgsPalLayerSettings, QgsTextFormat,
    QgsTextBufferSettings, QgsVectorLayerSimpleLabeling
)
from qgis.PyQt.QtGui import QColor, QFont

PIN_SIZE_MM = 8.2

def _apply_point_svg_style(layer, plugin_dir):
    try:
        if not layer or layer.wkbType() == QgsWkbTypes.NoGeometry:
            return
        svg_white = os.path.join(plugin_dir, 'icons', 'pin_white.svg')
        svg_blue  = os.path.join(plugin_dir, 'icons', 'pin_blue.svg')

        # start -> WHITE (Origem); end -> BLUE (Destino)
        sym_start = QgsMarkerSymbol()
        sym_start.changeSymbolLayer(0, QgsSvgMarkerSymbolLayer(svg_white, PIN_SIZE_MM, 0.0))
        try: sym_start.symbolLayer(0).setOffset(0, -2.5)
        except Exception: pass

        sym_end = QgsMarkerSymbol()
        sym_end.changeSymbolLayer(0, QgsSvgMarkerSymbolLayer(svg_blue, PIN_SIZE_MM, 0.0))
        try: sym_end.symbolLayer(0).setOffset(0, -2.5)
        except Exception: pass

        renderer = QgsCategorizedSymbolRenderer('role', [
            QgsRendererCategory('start', sym_start, 'Origem'),
            QgsRendererCategory('end',   sym_end,   'Destino'),
        ])
        layer.setRenderer(renderer)

        # Labels: preto com halo branco, Origem/Destino
        pal = QgsPalLayerSettings()
        pal.enabled = True
        pal.fieldName = "CASE WHEN \"role\"='start' THEN 'Origem' WHEN \"role\"='end' THEN 'Destino' END"
        pal.isExpression = True
        pal.placement = QgsPalLayerSettings.OverPoint

        fmt = QgsTextFormat()
        fmt.setFont(QFont('Arial', 10))
        fmt.setSize(10)
        fmt.setColor(QColor('black'))
        buf = QgsTextBufferSettings()
        buf.setEnabled(True)
        buf.setSize(1.2)
        buf.setColor(QColor('white'))
        fmt.setBuffer(buf)
        pal.setFormat(fmt)

        labeling = QgsVectorLayerSimpleLabeling(pal)
        layer.setLabelsEnabled(True)
        layer.setLabeling(labeling)

        layer.triggerRepaint()
    except Exception as e:
        try:
            from qgis.core import Qgis, QgsMessageLog
            QgsMessageLog.logMessage(str(e), 'Off-Road Explorer', Qgis.Warning)
        except Exception:
            pass

def _style_any_endpoint_layer_in_project(plugin_dir):
    try:
        proj = QgsProject.instance()
        for lyr in proj.mapLayers().values():
            try:
                if getattr(lyr, 'geometryType', None) and lyr.geometryType() != 0:
                    continue
                if not hasattr(lyr, 'fields') or 'role' not in [f.name() for f in lyr.fields()]:
                    continue
                lname = (lyr.name() or '').lower()
                if 'pontos da rota' in lname or 'endpoint' in lname:
                    _apply_point_svg_style(lyr, plugin_dir); _apply_point_labels_pt(lyr); _persist_style_on_layer(lyr, plugin_dir)
            except Exception:
                continue
    except Exception:
        pass

class LeastCostRouteAlgorithm(QgsProcessingAlgorithm):
    def _autoclean_selection_layers(self):
        """
        Remove lingering memory layers named with '_selecionadas' to keep UI clean.
        """
        try:
            prj = QgsProject.instance()
            keys = [k for k, v in prj.mapLayers().items() if "_selecionadas" in v.name().lower()]
            for k in keys:
                try:
                    prj.removeMapLayer(k)
                except Exception:
                    pass
        except Exception:
            pass


    P_ADEQ='ADEQ'; P_REST='REST'; P_IMPED='IMPED'
    # Removed vector layer fallbacks
    P_CRS='TARGET_CRS'; P_CELL='CELL'; P_OUTDIR='OUT_DIR'; P_BASE='BASENAME'
    P_ORIG_PT='ORIGIN_POINT'; P_DEST_PT='DEST_POINT'

    def tr(self,s): return QCoreApplication.translate('LeastCostRouteAlgorithm',s)
    def name(self): return 'least_cost_route_grass_plus_merge'
    def displayName(self): return self.tr('Off-Road Explorer – Rota de menor custo')
    def group(self): return 'Off-Road Explorer'
    def groupId(self): return 'trafegabilidade_tools'

    def shortHelpString(self):
        return self.tr("""
<p style="margin-top:8px;">
📘 <a href="file:///C:/Users/aluno/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/off_road_explorer/Manual_Usuario.pdf"> Abrir Manual de Uso (PDF)</a>
</p>
<b>Descrição geral</b><br>
Recebe as camadas de trafegabilidade <i>Adequado</i>, <i>Restritivo</i> e <i>Impeditivo</i> (polígonos), 
gera um raster de custo (1/50/9999), executa <code>r.cost</code> e <code>r.drain</code> (GRASS) e retorna a rota de menor custo.

<b>Como usar</b>
<ol>
<li>Informe as camadas de trafegabilidade: <b>Adequado</b>, <b>Restritivo</b>, <b>Impeditivo</b> (qualquer CRS). O algoritmo reprojeta tudo para o <b>CRS de interesse (m)</b>.</li>
<li>Defina os pontos a partir do click no mapa: <b>Mapa de coordenadas do ponto(s) de início (E,N)</b> e <b>Mapa de coordenadas do ponto(s) de destino (E,N)</b>. 
<u>Prioridade:</u> o valor da coordenada obtido a partir do click no mapa <b>prevalece</b> sobre as camadas <i>Origem (ponto)</i> e <i>Destino (ponto)</i> (alternativas opcionais).</li>
<li>Informações para possíveis ajustes: <b>CRS para reprojetar (m)</b>, <b>Tamanho do pixel (m)</b>, <b>Nome base</b> e <b>Pasta de saída</b>.</li>
<li>Clique em <b>Executar</b>.</li>
</ol>

<b>Saídas</b>
<ul>
<li><code>*_cost.tif</code>: Raster de custo (1/50/9999).</li>
<li><code>*_accum.tif</code>: Raster de custo acumulado (<code>r.cost</code>).</li>
<li><code>*_direction.tif</code>: Direção de movimento (<code>r.cost</code>).</li>
<li><code>*_route.gpkg</code>: Rota de menor custo (vetor) — adicionada ao projeto.</li>
<li><code>*_endpoints.gpkg</code>: Pontos de origem/destino (camada auxiliar).</li>
</ul>

<b>Observações</b>
<ul>
<li>É necessário ter o provedor GRASS habilitado.</li>
<li>O <b>pixel</b> define a resolução do custo; resoluções muito finas aumentam o tempo de processamento.</li>
<li>A extensão é derivada do mosaico de classes; garanta que os pontos estejam <b>dentro</b> dessa área.</li>
<li>Todos os insumos são reprojetados para o <b>CRS de interesse (m)</b> antes do processamento.</li>
</ul>
""")

    def initAlgorithm(self, config=None):
        # Auto-clean *_selecionadas layers that may linger in memory
        self._autoclean_selection_layers()
        # Polígonos
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.P_ADEQ,'Adequado (polígonos)',[QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.P_REST,'Restritivo (polígonos)',[QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.P_IMPED,'Impeditivo (polígonos)',[QgsProcessing.TypeVectorPolygon]))

        # Mapa de início (obrigatório) + tooltip
        p_orig = QgsProcessingParameterPoint(self.P_ORIG_PT, self.tr('Mapa de coordenadas do ponto(s) de início (E,N)'))
        p_orig.setFlags(p_orig.flags() & ~QgsProcessingParameterDefinition.FlagOptional)
        p_orig.setHelp(self.tr('Clique no alvo para capturar a coordenada no mapa. Prioridade: este campo > "Origem (ponto)". Se ambos existirem, o valor clicado prevalece.'))
        self.addParameter(p_orig)

        # Mapa de destino (obrigatório) + tooltip
        p_dest = QgsProcessingParameterPoint(self.P_DEST_PT, self.tr('Mapa de coordenadas do ponto(s) de destino (E,N)'))
        p_dest.setFlags(p_dest.flags() & ~QgsProcessingParameterDefinition.FlagOptional)
        p_dest.setHelp(self.tr('Clique no alvo para capturar a coordenada no mapa. Prioridade: este campo > "Destino (ponto)". Se ambos existirem, o valor clicado prevalece.'))
        self.addParameter(p_dest)

        # Camadas de ponto (opcionais) + tooltip

        # Parâmetros gerais
        self.addParameter(QgsProcessingParameterCrs(self.P_CRS,'CRS para reprojetar (metros)',defaultValue='EPSG:31983'))
        self.addParameter(QgsProcessingParameterNumber(self.P_CELL,'Tamanho do pixel (m)',
            type=QgsProcessingParameterNumber.Double,defaultValue=30.0,minValue=0.01))
        self.addParameter(QgsProcessingParameterString(self.P_BASE,'Nome base',defaultValue='lcp'))
        self.addParameter(QgsProcessingParameterFolderDestination(self.P_OUTDIR,'Pasta de saída'))

    def _resolve_points(self, parameters, context, feedback):
        # Captura obrigatória via clique no mapa (campo de ponto)
        origin_pt = self.parameterAsPoint(parameters, self.P_ORIG_PT, context)
        if origin_pt is None or (hasattr(origin_pt,'isEmpty') and getattr(origin_pt,'isEmpty')()):
            raise QgsProcessingException(self.tr('Informe a origem: clique no mapa (campo de ponto).'))
        dest_pt = self.parameterAsPoint(parameters, self.P_DEST_PT, context)
        if dest_pt is None or (hasattr(dest_pt,'isEmpty') and getattr(dest_pt,'isEmpty')()):
            raise QgsProcessingException(self.tr('Informe o destino: clique no mapa (campo de ponto).'))
        return origin_pt, dest_pt

    def checkParameterValues(self, parameters, context):
        # Garante coerência com rótulos/validação
        ok_orig = (parameters.get(self.P_ORIG_PT) is not None)
        ok_dest = (parameters.get(self.P_DEST_PT) is not None)
        errors = []
        if not ok_orig:
            errors.append((self.P_ORIG_PT, self.tr('Informe a origem: clique no mapa (campo de ponto).')))
        if not ok_dest:
            errors.append((self.P_DEST_PT, self.tr('Informe o destino: clique no mapa (campo de ponto).')))
        return (len(errors) == 0, errors)

    def createInstance(self): return LeastCostRouteAlgorithm()

    def _assert(self,path,label):
        if not os.path.exists(path) or os.path.getsize(path)==0:
            raise QgsProcessingException(f'Falha ao criar {label}: {path}')

    
    def _pretty_style(self, layer, flavor="accum"):
        try:
            from qgis.core import QgsRasterShader, QgsColorRampShader, QgsSingleBandPseudoColorRenderer, QgsRasterBandStats, QgsBilinearRasterResampler
            from PyQt5.QtGui import QColor
        except Exception:
            return
        # pyramids
        try:
            dp = layer.dataProvider()
            try:
                dp.buildPyramids([2,4,8,16,32,64], 'AVERAGE')
            except Exception:
                try: dp.buildPyramids('AVERAGE', [2,4,8,16,32,64])
                except Exception: pass
        except Exception:
            pass
        # bilinear
        try:
            rf = layer.resampleFilter()
            rf.setZoomedInResampler(QgsBilinearRasterResampler())
            rf.setZoomedOutResampler(QgsBilinearRasterResampler())
        except Exception:
            pass
        # color ramp
        try:
            stats = layer.dataProvider().bandStatistics(1, QgsRasterBandStats.All, layer.extent(), 0)
            mn = float(getattr(stats,'minimumValue',0.0)); mx = float(getattr(stats,'maximumValue',1.0))
            if not (mx>mn): mx = mn + 1.0
            shader = QgsRasterShader(); ramp = QgsColorRampShader()
            ramp.setColorRampType(QgsColorRampShader.Interpolated)
            cols=[(68,1,84),(59,82,139),(33,145,140),(253,231,37)]
            vals=[mn, mn+(mx-mn)*0.35, mn+(mx-mn)*0.7, mx]
            items=[QgsColorRampShader.ColorRampItem(v, QColor(*c), str(round(v,2))) for v,c in zip(vals,cols)]
            ramp.setColorRampItemList(items); shader.setRasterShaderFunction(ramp)
            renderer=QgsSingleBandPseudoColorRenderer(layer.dataProvider(),1,shader)
            layer.setRenderer(renderer); layer.triggerRepaint()
        except Exception:
            pass

    def _load_r(self,path,name):
        rl = QgsRasterLayer(path,name,'gdal')
        if not rl or not rl.isValid():
            return None
        # Não adicionar ao projeto aqui; quem adiciona é a rotina após aplicar estilo
        return rl


    
    
    
    def _apply_route_black_style_and_save(self, vlayer: QgsVectorLayer, gpkg_path: str):
        """Aplica estrada realista mais fina (sem seta) e salva como padrão."""
        try:
            if vlayer is None or not vlayer.isValid():
                return

            # Ombreira cinza claro
            shoulder = QgsSimpleLineSymbolLayer()
            shoulder.setColor(QColor(201,201,201))
            shoulder.setWidth(2.0)

            # Asfalto preto
            asphalt = QgsSimpleLineSymbolLayer()
            asphalt.setColor(QColor(26,26,26))
            asphalt.setWidth(1.6)

            # Faixa central tracejada branca
            dashed = QgsSimpleLineSymbolLayer()
            dashed.setColor(QColor(255,255,255))
            dashed.setWidth(0.4)
            try:
                dashed.setUseCustomDashPattern(True)
                dashed.setCustomDashVector([2.5, 2.0])
            except Exception:
                pass

            # Monta símbolo de linha
            line_symbol = QgsLineSymbol()
            try:
                line_symbol.deleteSymbolLayer(0)
            except Exception:
                pass
            line_symbol.appendSymbolLayer(shoulder)
            line_symbol.appendSymbolLayer(asphalt)
            line_symbol.appendSymbolLayer(dashed)

            vlayer.setRenderer(QgsSingleSymbolRenderer(line_symbol))
            vlayer.triggerRepaint()

            try:
                vlayer.saveStyleToDatabase('padrao_rota_realista_sem_seta', 'Estrada realista mais fina (sem seta)', True, '')
            except Exception:
                try:
                    vlayer.saveDefaultStyle()
                except Exception:
                    pass
        except Exception:
            pass

    
    
    
    
    def _write_to_gpkg_layer(self, vlayer, gpkg_path, layer_name, feedback):
        """Grava vlayer em gpkg_path com nome layer_name usando apenas native:package, e registra no log."""
        try:
            import processing, os
            # garante dir
            try:
                os.makedirs(os.path.dirname(gpkg_path), exist_ok=True)
            except Exception:
                pass
            # força o nome da camada
            try:
                vlayer.setName(layer_name)
            except Exception:
                pass
            # cria/sobrescreve arquivo .gpkg com a camada
            processing.run('native:package', {
                'LAYERS': [vlayer],
                'OUTPUT': gpkg_path,
                'OVERWRITE': True
            }, feedback=feedback)
            # log amigável
            try:
                feedback.pushInfo(f"✅ Rota salva em: {gpkg_path}")
            except Exception:
                pass
            return True
        except Exception as e:
            try:
                feedback.reportError(f"Falha ao gravar GPKG: {e}")
            except Exception:
                pass
            return False

    def _load_v(self,path,name):
        vl=QgsVectorLayer(path,name,'ogr')
        if vl.isValid(): QgsProject.instance().addMapLayer(vl)

    def _cleanup_temp(self, outdir, run_dir, feedback):
        import glob
        removed = 0
        patterns = [
            'drain_*', 'drain_*.*',
            'tmp_*', 'tmp_*.*',
            'rdout_*', 'rdout_*.*',
            'route_tmp.*', '*_path_tmp.*'
        ]
        for pat in patterns:
            try:
                for p in glob.glob(pat):
                    if os.path.isfile(p):
                        try:
                            os.remove(p); removed += 1
                        except Exception:
                            pass
            except Exception:
                pass
        try:
            feedback.pushInfo(f'Off-Road Explorer: temporários removidos: {removed}')
        except Exception:
            pass

    def processAlgorithm(self, parameters, context, feedback):
        # Garantir base_name vindo do parâmetro 'BASENAME'
        try:
            base_name = base_name  # se já existir, mantém
        except NameError:
            try:
                base_name = self.parameterAsString(parameters, 'BASENAME', context)
            except Exception:
                base_name = parameters.get('BASENAME') if isinstance(parameters, dict) else 'lcp'
            if not base_name:
                base_name = 'lcp'
        origin_pt, dest_pt = self._resolve_points(parameters, context, feedback)

        # Helpers
        def _mem_point_layer_from_xy(pt_xy, crs, name='pt'):
            vl=QgsVectorLayer(f'Point?crs={crs.authid()}',name,'memory')
            pr=vl.dataProvider()
            pr.addAttributes([QgsField('id', QVariant.Int)])
            vl.updateFields()
            f=QgsFeature(vl.fields()); f.setAttribute('id',1)
            f.setGeometry(QgsGeometry.fromPointXY(pt_xy)); pr.addFeatures([f])
            vl.updateExtents(); return vl

        def _reproject_if_needed(vlayer, target_crs, tmp_name):
            if vlayer is None or not vlayer.isValid(): return vlayer
            if not target_crs.isValid() or vlayer.crs()==target_crs: return vlayer
            out=QgsVectorLayer(f"{QgsWkbTypes.displayString(vlayer.wkbType())}?crs={target_crs.authid()}",tmp_name,'memory')
            out_dp=out.dataProvider(); out_dp.addAttributes(vlayer.fields()); out.updateFields()
            xform=QgsCoordinateTransform(vlayer.crs(),target_crs,QgsProject.instance())
            feats=[]
            for feat in vlayer.getFeatures():
                g=feat.geometry()
                if g and not g.isEmpty():
                    g=QgsGeometry(g); g.transform(xform)
                nf=QgsFeature(out.fields()); nf.setAttributes(feat.attributes()); nf.setGeometry(g); feats.append(nf)
            out_dp.addFeatures(feats); out.updateExtents(); return out

        self._mem_point_layer_from_xy=_mem_point_layer_from_xy
        self._reproject_if_needed=_reproject_if_needed

        adeq=self.parameterAsVectorLayer(parameters,self.P_ADEQ,context)
        rest=self.parameterAsVectorLayer(parameters,self.P_REST,context)
        imped=self.parameterAsVectorLayer(parameters,self.P_IMPED,context)
        target_crs=self.parameterAsCrs(parameters,self.P_CRS,context)
        if not target_crs.isValid():
            target_crs=QgsProject.instance().crs()

        # Criar camadas em memória a partir dos cliques (em CRS do projeto) e depois reprojetar
        project_crs = QgsProject.instance().crs()
        orig=self._mem_point_layer_from_xy(origin_pt, project_crs, 'origem_mem_proj')
        dest=self._mem_point_layer_from_xy(dest_pt,   project_crs, 'destino_mem_proj')

        # Reprojetar entradas
        crs=self.parameterAsCrs(parameters,self.P_CRS,context)
        def reproject(layer): 
            return processing.run('native:reprojectlayer',{'INPUT':layer,'TARGET_CRS':crs,'OUTPUT':'memory:'},context=context,feedback=feedback)['OUTPUT']
        adeq= reproject(adeq); rest=reproject(rest); imped=reproject(imped)
        orig= reproject(orig); dest=reproject(dest)

        # Adicionar campo 'classe' e mesclar
        def set_class(layer, value):
            processing.run('native:fieldcalculator',{
                'INPUT':layer,'FIELD_NAME':'classe','FIELD_TYPE':2,'FIELD_LENGTH':20,'NEW_FIELD':True,
                'FORMULA':f"'{value}'",'OUTPUT':'memory:'
            },context=context,feedback=feedback)['OUTPUT']
            return processing.run('native:fieldcalculator',{
                'INPUT':layer,'FIELD_NAME':'classe','FIELD_TYPE':2,'FIELD_LENGTH':20,'NEW_FIELD':False,
                'FORMULA':f"'{value}'",'OUTPUT':'memory:'
            },context=context,feedback=feedback)['OUTPUT']
        adeq=set_class(adeq,'Adequado'); rest=set_class(rest,'Restritivo'); imped=set_class(imped,'Impeditivo')

        merged=processing.run('native:mergevectorlayers',{'LAYERS':[adeq,rest,imped],'CRS':crs,'OUTPUT':'memory:'},context=context,feedback=feedback)['OUTPUT']

        merged=processing.run('native:fieldcalculator',{
            'INPUT':merged,'FIELD_NAME':'custo','FIELD_TYPE':1,'FIELD_LENGTH':10,'NEW_FIELD':True,
            'FORMULA':"CASE WHEN \"classe\"='Adequado' THEN 1 WHEN \"classe\"='Restritivo' THEN 50 WHEN \"classe\"='Impeditivo' THEN 9999 END",
            'OUTPUT':'memory:'
        },context=context,feedback=feedback)['OUTPUT']

        e=merged.extent(); ext=f"{e.xMinimum()},{e.xMaximum()},{e.yMinimum()},{e.yMaximum()} [{crs.authid()}]"
        cell=self.parameterAsDouble(parameters,self.P_CELL,context)
        outdir=self.parameterAsFile(parameters,self.P_OUTDIR,context)
        base=self.parameterAsString(parameters,self.P_BASE,context)

        stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        run_dir=os.path.join(outdir,f'{base}_run_{stamp}_{uuid.uuid4().hex[:6]}')
        os.makedirs(run_dir,exist_ok=True)

        cost=os.path.join(run_dir,f'{base}_cost.tif')
        accum=os.path.join(run_dir,f'{base}_accum.tif')
        direc=os.path.join(run_dir,f'{base}_direction.tif')
        route=os.path.join(run_dir,f'{base}_route.gpkg')
        route_layer = 'lcp_route'
        route_with_layer = f"{route}|layername={route_layer}"

        processing.run('gdal:rasterize',{
            'INPUT':merged,'FIELD':'custo','WIDTH':cell,'HEIGHT':cell,'UNITS':1,'EXTENT':ext,
            'NODATA':0,'DATA_TYPE':5,'OPTIONS':'COMPRESS=LZW','OUTPUT':cost
        },context=context,feedback=feedback)
        self._assert(cost,'Raster de Custo'); self._load_r(cost,'Raster de Custo')


                                        # Garantir que não haja NODATA/zeros no custo para evitar buracos
        cost_filled_tif = os.path.join(run_dir, f"{base}_cost_filled.tif")
        processing.run('gdal:rastercalculator', {
            'INPUT_A': cost,
            'BAND_A': 1,
            'INPUT_B': None, 'BAND_B': -1,
            'INPUT_C': None, 'BAND_C': -1,
            'INPUT_D': None, 'BAND_D': -1,
            'INPUT_E': None, 'BAND_E': -1,
            'INPUT_F': None, 'BAND_F': -1,
            'FORMULA': 'A*(A>0) + 50*(A<=0)',
            'NO_DATA': None,
            'RTYPE': 5,
            'OPTIONS': 'COMPRESS=LZW',
            'EXTRA': '',
            'OUTPUT': cost_filled_tif
        }, context=context, feedback=feedback)


        
        
        # Helper para recuperar uma camada IMPED funcional (evita 'wrapped C/C++ object ... deleted')
        def _get_imped_working(_imped, _merged):
            # 1) Tenta clonar a entrada (garantir nova instância em memória)
            try:
                if _imped is not None and _imped.isValid() and _imped.featureCount() > 0:
                    return processing.run('native:savefeatures', {
                        'INPUT': _imped, 'OUTPUT': 'memory:'
                    }, context=context, feedback=feedback)['OUTPUT']
            except Exception:
                pass
            # 2) Fallback: re-extrai do 'merged' pela coluna 'classe' == 'Impeditivo'
            try:
                return processing.run('native:extractbyattribute', {
                    'INPUT': _merged,
                    'FIELD': 'classe',
                    'OPERATOR': 0,  # '='
                    'VALUE': 'Impeditivo',
                    'OUTPUT': 'memory:'
                }, context=context, feedback=feedback)['OUTPUT']
            except Exception:
                return None
# === Impeditivo como BARREIRA ABSOLUTA (NULL) ===
        # Recupera IMPED garantido
        imped = _get_imped_working(imped, merged)

        # Proteção: inicializa variável e checa se camada IMPED é válida e tem feições
        buffered_vec = None
        if imped is not None and imped.isValid() and imped.featureCount() > 0:
            buffered_vec = imped
        else:
            feedback.pushWarning('Camada IMPED vazia/ inválida — barreira desativada para esta execução.')

        # Gera máscara do Impeditivo (1=impeditivo) alinhada ao grid do custo e aplica NULL nessas células.
        try:
            imped_mask_path = os.path.join(run_dir, f"{base}_imped_mask.tif")
            # Opcional: engrossa áreas impeditivas com buffer de 1/2 célula
            try:
                buf_dist = float(cell) / 2.0
            except Exception:
                buf_dist = 0.0
            # Buffer robusto em polígonos (área) usando 'native:buffer' e dissolvendo
            if buffered_vec is not None:
                buffered_vec = processing.run('native:buffer', {
                    'INPUT': buffered_vec,
                    'DISTANCE': buf_dist,
                    'SEGMENTS': 8,
                    'END_CAP_STYLE': 0,
                    'JOIN_STYLE': 0,
                    'MITER_LIMIT': 2,
                    'DISSOLVE': True,
                    'SEPARATE_DISJOINT': False,
                    'OUTPUT': 'memory:'
                }, context=context, feedback=feedback)['OUTPUT']
            else:
                feedback.pushWarning('Sem IMPED válido — barreira desativada nesta execução.')
                raise Exception('IMPED vazio')

            # Rasterizar a máscara 1=impeditivo alinhada ao grid do custo (gdal:rasterize)
            imped_mask = processing.run('gdal:rasterize', {
                'INPUT': buffered_vec,
                'FIELD': None,
                'BURN': 1,
                'UNITS': 1,             # pixel size em unidades do CRS
                'WIDTH': cell,
                'HEIGHT': cell,
                'EXTENT': ext,
                'NODATA': 0,
                'OPTIONS': 'COMPRESS=LZW',
                'DATA_TYPE': 5,         # Float32
                'INIT': 0,
                'INVERT': False,
                'EXTRA': '',
                'OUTPUT': os.path.join(run_dir, f"{base}_imped_mask.tif")
            }, context=context, feedback=feedback)['OUTPUT']
            imped_mask_filled = processing.run('grass7:r.mapcalc.simple', {
                'a': imped_mask,
                'expression': 'if(isnull(A), 0, A)',
                'output': os.path.join(run_dir, f"{base}_imped_mask_filled.tif"),
                'GRASS_REGION_PARAMETER': ext,
                'GRASS_REGION_CELLSIZE_PARAMETER': cell,
                'GRASS_RASTER_FORMAT_OPT': 'COMPRESS=LZW,TFW=YES',
                'GRASS_RASTER_FORMAT_META': ''
            }, context=context, feedback=feedback)['output']

            cost_barrier = os.path.join(run_dir, f"{base}_cost_barrier.tif")
            cost_barrier = processing.run('grass7:r.mapcalc.simple', {
                'a': cost_filled_tif,
                'b': imped_mask_filled,
                'expression': 'if(B == 1, null(), A)',
                'output': cost_barrier,
                'GRASS_REGION_PARAMETER': ext,
                'GRASS_REGION_CELLSIZE_PARAMETER': cell,
                'GRASS_RASTER_FORMAT_OPT':'COMPRESS=LZW,TFW=YES',
                'GRASS_RASTER_FORMAT_META':''
            }, context=context, feedback=feedback)['output']

            cost_for_routing = cost_barrier
        except Exception as _e_mask:  # barreira

            feedback.pushWarning(f'Falha ao aplicar barreira NULL no Impeditivo: {_e_mask}. Seguindo com raster de custo sem barreira.')
            cost_for_routing = cost_filled_tif
        # === fim barreira ===

        processing.run('grass7:r.cost',{
            'input': cost_for_routing,'start_points':dest,'max_cost':0,'memory':300,
            'output':accum,'outdir':direc,'GRASS_REGION_PARAMETER':ext,'GRASS_REGION_CELLSIZE_PARAMETER':cell,
            'GRASS_RASTER_FORMAT_OPT':'COMPRESS=LZW,TFW=YES','GRASS_RASTER_FORMAT_META':''
        },context=context,feedback=feedback)
        self._assert(accum,'Custo Acumulado'); self._assert(direc,'Direção de Movimento')
        self._load_r(accum,'Custo Acumulado'); self._load_r(direc,'Direção de Movimento')
        # Criar versão de visualização SEM BURACOS do acumulado (mantendo os NULLs somente no 'accum' original para análises)
        try:
            accum_filled = os.path.join(run_dir, f"{base}_accum_filled.tif")
            processing.run('grass7:r.mapcalc.simple', {
                'a': accum,
                'expression': 'if(isnull(A), 0, A)',
                'output': accum_filled,
                'GRASS_REGION_PARAMETER': ext,
                'GRASS_REGION_CELLSIZE_PARAMETER': cell,
                'GRASS_RASTER_FORMAT_OPT': 'COMPRESS=LZW,TFW=YES',
                'GRASS_RASTER_FORMAT_META': ''
            }, context=context, feedback=feedback)
        except Exception as e_accumfill:
            accum_filled = accum
            feedback.pushWarning(f"[Style] Falha ao gerar '_accum_filled.tif': {e_accumfill}. Usando acumulado original para visualização.")

        # Criar versão de visualização SEM BURACOS da direção (NULL -> 0)
        try:
            direction_filled = os.path.join(run_dir, f"{base}_direction_filled.tif")
            processing.run('grass7:r.mapcalc.simple', {
                'a': direc,
                'expression': 'if(isnull(A), 0, A)',
                'output': direction_filled,
                'GRASS_REGION_PARAMETER': ext,
                'GRASS_REGION_CELLSIZE_PARAMETER': cell,
                'GRASS_RASTER_FORMAT_OPT': 'COMPRESS=LZW,TFW=YES',
                'GRASS_RASTER_FORMAT_META': ''
            }, context=context, feedback=feedback)
        except Exception as e_dirfill:
            direction_filled = direc
            feedback.pushWarning(f"[Style] Falha ao gerar '_direction_filled.tif': {e_dirfill}. Usando direção original para visualização.")

            accum_filled = accum
            feedback.pushWarning(f"[Style] Falha ao gerar '_accum_filled.tif': {e_accumfill}. Usando acumulado original para visualização.")


        drain_name = f"drain_{uuid.uuid4().hex[:8]}"
        processing.run('grass7:r.drain', {'input':accum, 'direction':direc, 'start_points':orig, 'flags':'d', 'output': f"rdout_{uuid.uuid4().hex[:8]}", 'GRASS_REGION_PARAMETER':ext, 'GRASS_REGION_CELLSIZE_PARAMETER':cell, 'drain': os.path.join(run_dir, f'{drain_name}.shp')}, context=context, feedback=feedback)

        saved=False
        try:
            reproj=processing.run('native:reprojectlayer',{'INPUT': os.path.join(run_dir, f'{drain_name}.shp'),'TARGET_CRS':crs,'OUTPUT':'memory:'},context=context,feedback=feedback)['OUTPUT']
            self._write_to_gpkg_layer(reproj, route, route_layer, feedback)
            vl=QgsVectorLayer(route_with_layer,'Rota de Menor Custo','ogr')
            if vl.isValid() and vl.featureCount()>0:
                self._apply_route_black_style_and_save(vl, route)
                QgsProject.instance().addMapLayer(vl); saved=True
        except Exception as e:
            feedback.reportError(str(e))

        if not saved:
            # Fallback very conservador: se falhar reprojeção direta, tenta carregar o shapefile e salvar
            try:
                vl_tmp = QgsVectorLayer(os.path.join(run_dir, f'{drain_name}.shp'), 'drain_tmp', 'ogr')
                if vl_tmp and vl_tmp.isValid():
                    reproj=processing.run('native:reprojectlayer',{'INPUT':vl_tmp,'TARGET_CRS':crs,'OUTPUT':'memory:'},context=context,feedback=feedback)['OUTPUT']
                    self._write_to_gpkg_layer(reproj, route, route_layer, feedback)
                    self._load_v(route_with_layer,'Rota de Menor Custo')
                    saved=True
            except Exception as e:
                feedback.reportError(f'Fallback falhou: {e}')
# Endpoints
        try:
            route_vl = QgsVectorLayer(route, 'route', 'ogr')
            if route_vl and route_vl.isValid():
                crs_route = route_vl.crs()
                mem = QgsVectorLayer('Point?crs=' + crs_route.authid(), 'endpoints', 'memory')
                prov = mem.dataProvider()
                fields_ep = QgsFields(); fields_ep.append(QgsField('role', QVariant.String)); fields_ep.append(QgsField('label_pt', QVariant.String))
                prov.addAttributes(fields_ep); mem.updateFields()
                feats_add = []
                for _feat in route_vl.getFeatures():
                    g = _feat.geometry()
                    if not g or g.isEmpty(): continue
                    if QgsWkbTypes.isMultiType(g.wkbType()):
                        parts = g.asMultiPolyline(); pts = list(parts[0]) if parts else []
                    else:
                        pts = list(g.asPolyline())
                    if not pts: continue
                    start = QgsGeometry.fromPointXY(QgsPointXY(pts[0]))
                    end   = QgsGeometry.fromPointXY(QgsPointXY(pts[-1]))
                    f1 = QgsFeature(mem.fields()); f1.setGeometry(start); f1.setAttribute('role','start'); f1.setAttribute('label_pt','Origem'); feats_add.append(f1)
                    f2 = QgsFeature(mem.fields()); f2.setGeometry(end);   f2.setAttribute('role','end');   f2.setAttribute('label_pt','Destino'); feats_add.append(f2)
                if feats_add:
                    prov.addFeatures(feats_add)
                    end_path = os.path.join(run_dir, f'{base}_endpoints.gpkg')
                    QgsVectorFileWriter.writeAsVectorFormatV3(
                        mem, end_path, QgsCoordinateTransformContext(),
                        QgsVectorFileWriter.SaveVectorOptions()
                    )
                    self._load_v(end_path, 'Pontos da rota (início/fim)')
        except Exception as e:
            feedback.reportError(f'Falha ao criar endpoints: {e}')
        self._cleanup_temp(outdir, run_dir, feedback)
        # aplicar estilos nos rasters produzidos

        try:

            _apply_qml_to_rasters(run_dir, base_name, feedback)

        except Exception as _e_apply:

            try:

                feedback.reportError(f"[Style] Não foi possível aplicar estilos automaticamente: {_e_apply}")

            except Exception:

                pass
        _style_any_endpoint_layer_in_project(os.path.dirname(os.path.dirname(__file__)))



        return {'OUT_COST_RASTER':cost,'OUT_ACCUM_RASTER':accum,'OUT_DIRECTION_RASTER':direc,'OUT_ROUTE':route}

from qgis.PyQt.QtGui import QColor
from qgis.core import QgsSimpleLineSymbolLayer, QgsMarkerLineSymbolLayer, QgsSvgMarkerSymbolLayer, QgsLineSymbol, QgsSingleSymbolRenderer, QgsMarkerSymbol, QgsUnitTypes


# ========= Helper para aplicar estilos .QML em rasters produzidos =========

def _apply_qml_to_rasters(run_dir, base_name, feedback=None):
    """
    Tenta aplicar <base>_cost_filled.qml, <base>_accum.qml e <base>_direction.qml.
    Caso os .qml não existam, aplica um estilo padrão em código.
    """
    from qgis.PyQt.QtGui import QColor
    from qgis.core import (
        QgsRasterLayer, QgsProject, QgsColorRampShader, QgsRasterShader,
        QgsSingleBandPseudoColorRenderer, QgsRasterBandStats
    )
    import os

    pairs = [
        (f"{base_name}_cost_filled.tif", f"{base_name}_cost_filled.qml"),
        (f"{base_name}_accum_filled.tif",       f"{base_name}_accum.qml"),
        (f"{base_name}_direction_filled.tif",   f"{base_name}_direction.qml"),
    ]

    for tif_name, qml_name in pairs:
        tif_path = os.path.join(run_dir, tif_name)
        qml_path = os.path.join(run_dir, qml_name)

        if not os.path.exists(tif_path):
            if feedback: feedback.pushInfo(f"[Style] TIF não encontrado: {tif_name}")
            continue

        # add to project (do not duplicate if already added)
        tif_lower = tif_name.lower()
        if 'cost_filled' in tif_lower or ('cost' in tif_lower and 'accum' not in tif_lower and 'direction' not in tif_lower):
            layer_name = 'Raster de Custo'
        elif 'accum' in tif_lower:
            layer_name = 'Raster de Custo acumulado'
        elif 'direction' in tif_lower or 'direc' in tif_lower:
            layer_name = 'Raster de Direção de movimento'
        else:
            base_no_ext = os.path.splitext(tif_name)[0]
            for pref in ('kk_', 'tmp_', 'out_'):
                if base_no_ext.startswith(pref):
                    base_no_ext = base_no_ext[len(pref):]
            layer_name = base_no_ext
        rl = QgsRasterLayer(tif_path, layer_name)
        if not rl.isValid():
            if feedback: feedback.reportError(f"[Style] Falha ao abrir raster: {tif_path}")
            continue

        applied_qml = False
        if os.path.exists(qml_path):
            ok, _ = rl.loadNamedStyle(qml_path)
            if ok:
                # Salvar sidecar baseado no QML aplicado
                try:
                    sidecar_qml = tif_path[:-4] + '.qml' if tif_path.lower().endswith('.tif') else (tif_path + '.qml')
                    rl.saveNamedStyle(sidecar_qml)
                    if feedback: feedback.pushInfo(f"[Style] QML salvo (modelo): {sidecar_qml}")
                except Exception as e:
                    if feedback: feedback.reportError(f"[Style] Falha ao salvar QML (modelo): {e}")
                applied_qml = True
                if feedback: feedback.pushInfo(f"[Style] Aplicado QML: {qml_name}")
            else:
                if feedback: feedback.pushInfo(f"[Style] QML existente mas não aplicado: {qml_name}")

        
        # Forçar aplicação do estilo roxo-azul automático se for raster de custo acumulado
        try:
            if 'accum' in tif_name.lower():
                qml_auto = os.path.join(os.path.dirname(__file__), '..', 'styles', 'raster_custo.qml')
                if os.path.exists(qml_auto):
                    ok, _ = rl.loadNamedStyle(qml_auto)
                    if ok:
                        applied_qml = True
                        if feedback: feedback.pushInfo('[Style] Aplicado estilo roxo-azul automático')
                        try:
                            sidecar_qml = tif_path[:-4] + '.qml' if tif_path.lower().endswith('.tif') else (tif_path + '.qml')
                            rl.saveNamedStyle(sidecar_qml)
                            if feedback: feedback.pushInfo(f"[Style] QML salvo (auto): {sidecar_qml}")
                        except Exception as e:
                            if feedback: feedback.reportError(f"[Style] Falha ao salvar QML (auto): {e}")
        except Exception as e:
            if feedback: feedback.reportError(f'[Style] Erro ao aplicar estilo automático: {e}')
    
        if not applied_qml:
            # Fallback em código conforme tipo
            name_lower = tif_name.lower()
            shader = QgsRasterShader()
            ramp = QgsColorRampShader()
            ramp.setColorRampType(QgsColorRampShader.Discrete)

            if "cost_filled" in name_lower or "cost" in name_lower and "accum" not in name_lower and "direction" not in name_lower:
                # classes 1 (Adequado), 50 (Restritivo), 9999 (Impedtivo)
                items = [
                    QgsColorRampShader.ColorRampItem(1, QColor(50, 250, 50), "1 (Adequado)"),
                    QgsColorRampShader.ColorRampItem(50, QColor(250, 250, 0), "50 (Restritivo)"),
                    QgsColorRampShader.ColorRampItem(9999, QColor(255, 0, 0), "9999 (Impedtivo)"),
                ]
                ramp.setColorRampItemList(items)
                shader.setRasterShaderFunction(ramp)
                renderer = QgsSingleBandPseudoColorRenderer(rl.dataProvider(), 1, shader)
                rl.setRenderer(renderer)
                # Salvar QML irmão ao lado do TIF
                try:
                    sidecar_qml = tif_path[:-4] + '.qml' if tif_path.lower().endswith('.tif') else (tif_path + '.qml')
                    rl.saveNamedStyle(sidecar_qml)
                    if feedback: feedback.pushInfo(f"[Style] QML salvo ao lado do TIF: {sidecar_qml}")
                except Exception as e:
                    if feedback: feedback.reportError(f"[Style] Falha ao salvar QML ao lado do TIF: {e}")
                if feedback: feedback.pushInfo("[Style] Fallback: Raster de Custo estilizado (1/50/9999).")

            elif "accum" in name_lower:
                # usa estatísticas para min/max
                stats = rl.dataProvider().bandStatistics(1, QgsRasterBandStats.All)
                vmin = 0.0
                vmax = getattr(stats, 'maximumValue', getattr(stats, 'maximum', 255.0)) if stats and getattr(stats, 'maximumValue', getattr(stats, 'maximum', 255.0)) is not None else 255.0
                ramp.setColorRampType(QgsColorRampShader.Interpolated)
                ramp.setColorRampItemList([
                    QgsColorRampShader.ColorRampItem(vmin, QColor(68, 1, 84), f"{vmin:g}"),
                    QgsColorRampShader.ColorRampItem(vmax, QColor(253, 231, 37), f"{vmax:g}"),
                ])
                shader.setRasterShaderFunction(ramp)
                renderer = QgsSingleBandPseudoColorRenderer(rl.dataProvider(), 1, shader)
                rl.setRenderer(renderer)
                # Salvar QML irmão ao lado do TIF
                try:
                    sidecar_qml = tif_path[:-4] + '.qml' if tif_path.lower().endswith('.tif') else (tif_path + '.qml')
                    rl.saveNamedStyle(sidecar_qml)
                    if feedback: feedback.pushInfo(f"[Style] QML salvo ao lado do TIF: {sidecar_qml}")
                except Exception as e:
                    if feedback: feedback.reportError(f"[Style] Falha ao salvar QML ao lado do TIF: {e}")
                if feedback: feedback.pushInfo("[Style] Fallback: Custo Acumulado com rampa contínua.")

            elif "direction" in name_lower:
                # classes de 0 a 360 (passo 45)
                items = []
                for ang in range(0, 361, 45):
                    # escolhe uma paleta fechada simples
                    # variando em matiz (não crítico: é apenas fallback)
                    color = QColor.fromHsv(int((ang/360)*255), 200, 220)
                    label = f"{ang}°"
                    items.append(QgsColorRampShader.ColorRampItem(ang, color, label))
                ramp.setColorRampItemList(items)
                shader.setColorRampItemList = None
                shader.setRasterShaderFunction(ramp)
                renderer = QgsSingleBandPseudoColorRenderer(rl.dataProvider(), 1, shader)
                rl.setRenderer(renderer)
                # Salvar QML irmão ao lado do TIF
                try:
                    sidecar_qml = tif_path[:-4] + '.qml' if tif_path.lower().endswith('.tif') else (tif_path + '.qml')
                    rl.saveNamedStyle(sidecar_qml)
                    if feedback: feedback.pushInfo(f"[Style] QML salvo ao lado do TIF: {sidecar_qml}")
                except Exception as e:
                    if feedback: feedback.reportError(f"[Style] Falha ao salvar QML ao lado do TIF: {e}")
                if feedback: feedback.pushInfo("[Style] Fallback: Direção de Movimento 0–360° (passo 45).")

        # adicionar/atualizar no projeto
        QgsProject.instance().addMapLayer(rl)