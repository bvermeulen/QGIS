from qgis.core import (QgsProcessing, QgsProcessingAlgorithm, 
                       QgsProcessingParameterFeatureSource, 
                       QgsProcessingParameterVectorDestination)
import processing 
                       
class ExampleAlgo(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
 
    def __init__(self):
        super().__init__()
 
    def name(self):
        return "exalgo_processing_run"
 
    def displayName(self):
        return "Example Processing.run() script"
 
    def createInstance(self):
        return type(self)()
   
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                'Input layer',
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
 
        self.addParameter(
            QgsProcessingParameterVectorDestination (
                self.OUTPUT,
                'Output layer'
            )
        )
         
    def processAlgorithm(self, parameters, context, feedback):
        outputFile = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
 
        buffered_layer = processing.run("native:buffer", 
            {
                'INPUT': parameters['INPUT'],
                'DISTANCE': 1000000,
                'SEGMENTS': 5,
                'END_CAP_STYLE': 0,
                'JOIN_STYLE': 0,
                'MITER_LIMIT': 2,
                'DISSOLVE': False,
                'OUTPUT': outputFile
            }, 
            is_child_algorithm=True,
            context=context, 
            feedback=feedback
        )['OUTPUT']
     
        return {self.OUTPUT : buffered_layer}
