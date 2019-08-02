from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterVectorDestination
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterRasterDestination
import processing


class Flood_outline(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer('input', 'Input', defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorDestination('Vector', 'vector', type=QgsProcessing.TypeVectorPolygon, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Final_output', 'Final_output', type=QgsProcessing.TypeVectorPolygon, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Sql', 'SQl', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('Reclass', 'Reclass', createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(4, model_feedback)
        results = {}
        outputs = {}

        # Reclassify Raster Values - SAGA GIS toolbox
        alg_params = {
            'INPUT': parameters['input'],
            'MAX': 10,
            'METHOD': 1,
            'MIN': 0.001,
            'NEW': -1,
            'NODATA': 0,
            'NODATAOPT      ': False,
            'OLD': 1,
            'OTHEROPT       ': True,
            'OTHERS': 0,
            'RETAB': [''],
            'RNEW': 1,
            'ROPERATOR': 0,
            'SOPERATOR': 0,
            'TOPERATOR': 0,
            'RESULT': parameters['Reclass']
        }
        outputs['ReclassifyValues'] = processing.run('saga:reclassifyvalues', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Reclass'] = outputs['ReclassifyValues']['RESULT']

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Polygonize (raster to vector)
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': False,
            'FIELD': 'DN',
            'INPUT': outputs['ReclassifyValues']['RESULT'],
            'OUTPUT': parameters['Vector']
        }
        outputs['PolygonizeRasterToVector'] = processing.run('gdal:polygonize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Vector'] = outputs['PolygonizeRasterToVector']['OUTPUT']

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # SQL To Get Rid Of Some Values
        alg_params = {
            'INPUT_DATASOURCES': outputs['PolygonizeRasterToVector']['OUTPUT'],
            'INPUT_GEOMETRY_CRS': None,
            'INPUT_GEOMETRY_FIELD': '',
            'INPUT_GEOMETRY_TYPE': 4,
            'INPUT_QUERY': 'DELETE FROM poly_output WHERE DN = -999 OR WHERE DN = 0',
            'INPUT_UID_FIELD': '',
            'OUTPUT': parameters['Sql']
        }
        outputs['ExecuteSql'] = processing.run('qgis:executesql', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Sql'] = outputs['ExecuteSql']['OUTPUT']

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Fill holes
        alg_params = {
            'INPUT': outputs['ExecuteSql']['OUTPUT'],
            'MAX_AREA': 200,
            'OUTPUT': parameters['Final_output']
        }
        outputs['DeleteHoles'] = processing.run('native:deleteholes', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Final_output'] = outputs['DeleteHoles']['OUTPUT']
        return results

    def name(self):
        return 'Flood_Outline'

    def displayName(self):
        return 'Flood_Outline'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return Flood_outline()
