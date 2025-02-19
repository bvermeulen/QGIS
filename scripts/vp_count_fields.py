"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from enum import Enum
import time
import csv
from collections import Counter
from typing import Any, Optional

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterEnum,
)


csv_header = ["farm_id", "sl_sp", "date", "farm_status", "vp_category", "count"]


class VpCategories(Enum):
    FARM_EMPTY = "Empty land"
    FARM_CROP = "In the farmland"
    TRACK_GOOD = "Good Track＞4m"
    TRACK_FARM = "Track affect by farmland"
    TRACK_REMOVED = "Track disappeared"
    TRACK_WIDEN = "Track need wide"


class VpCount(QgsProcessingAlgorithm):

    LAYERS = "LAYERS"
    VP_CATEGORY = "VP_CATEGORY"
    FILE = "FILE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        return "vpcount"

    def displayName(self) -> str:
        return "VP count"

    def group(self) -> str:
        return "Howdimain scripts"

    def groupId(self) -> str:
        return "howdimain_scripts"

    def shortHelpString(self) -> str:
        return "Output VPs with the corresponding farm fields to a CSV file"

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):

        self.addParameter(
            QgsProcessingParameterMultipleLayers(self.LAYERS, "Input layers")
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(self.FILE, "CSV file", "csv (*.csv)")
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.VP_CATEGORY,
                "VP categories to be included",
                [c.name for c in VpCategories],
                defaultValue=[i for i, _ in enumerate(VpCategories)],
                allowMultiple=True,
            )
        )

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:

        # select layers
        layers = self.parameterAsLayerList(parameters, self.LAYERS, context)
        if (
            "Status" in layers[0].fields().names()
            and "Preplot_P" in layers[1].fields().names()
        ):
            field_layer = layers[0]
            vp_layer = layers[1]

        elif (
            "Status" in layers[1].fields().names()
            and "Preplot_P" in layers[0].fields().names()
        ):
            vp_layer = layers[0]
            field_layer = layers[1]

        else:
            feedback.pushInfo(
                f"ERROR: incorrect layers selected: "
                f"{layers[0].name()}, {layers[1].name()}"
            )
            return {self.OUTPUT: None}

        # select VP categories
        indexes = self.parameterAsEnums(parameters, self.VP_CATEGORY, context)
        vp_categories = list(VpCategories)
        selected_vp_categories = [vp_categories[index].value for index in indexes]

        # set the csv name and header
        csv_file_name = self.parameterAsFile(parameters, self.FILE, context)
        if "temp/processing" in csv_file_name.lower():
            feedback.pushInfo(f"ERROR: no output CSV file is given")
            return {self.OUTPUT: None}

        csv_data = []
        csv_data.append(csv_header)

        # loop all features
        total_features = 100 / (vp_layer.featureCount() * field_layer.featureCount())
        farm_count = Counter()
        progress_count = -1
        feedback.pushInfo(f"start processing ...")
        for point in vp_layer.getFeatures():
            for field in field_layer.getFeatures():
                progress_count = self.display_message(
                    feedback, progress_count, total_features
                )
                if feedback.isCanceled():
                    return {self.OUTPUT: None}

                if point.geometry().intersects(field.geometry()):
                    if (
                        vp_category := point.attributeMap().get("Farm_Cate")
                    ) in selected_vp_categories:
                        farm_id = field.attributeMap().get("Id")
                        farm_count[farm_id] += 1
                        csv_data.append(
                            [
                                farm_id,
                                point.attributeMap().get("Preplot_P"),
                                field.attributeMap().get("Date"),
                                field.attributeMap().get("Status"),
                                vp_category,
                                farm_count[farm_id],
                            ]
                        )

        self.save_to_csv(feedback, csv_file_name, csv_data)
        feedback.pushInfo(
            f"CSV file written: {csv_file_name} \n"
            f"Processing completed, {int(100 / total_features):7,} features done"
        )
        return {self.OUTPUT: None}

    @staticmethod
    def save_to_csv(feedback, file_name, csv_data):
        while True:
            try:
                with open(file_name, "w", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows(csv_data)

                return

            except PermissionError:
                feedback.pushInfo(f"Please close the file: {file_name}")
                time.sleep(5)

    @staticmethod
    def display_message(feedback, progress_count, total_features):
        progress_count += 1
        if progress_count % 10_000 == 0:
            feedback.setProgress(int(progress_count * total_features))

        if progress_count % 1_000_000 == 0:
            feedback.pushInfo(
                f"processing percentage: {int(progress_count * total_features):.1f}%"
            )
        return progress_count

    def createInstance(self):
        return self.__class__()
