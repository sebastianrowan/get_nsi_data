# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GetNSIData
                                 A QGIS plugin
 This plugin downloads data from the U.S. National Structures Inventory for a specified state or region.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-12-21
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Sebastian Rowan
        email                : sebastian.rowan@unh.edu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import pyqtSlot, QSettings, QTranslator, QCoreApplication, QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply,  QNetworkAccessManager
from qgis.core import QgsProject, Qgis, QgsCoordinateReferenceSystem,  QgsCoordinateTransform, QgsGeometry,QgsWkbTypes, QgsJsonExporter
import os
import os.path
import tempfile
import json
import math

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .get_nsi_data_dialog import GetNSIDataDialog, GetFipsNSIDataDialog, GetStateNSIDataDialog, GetBboxNSIDataDialog, GetShapeNSIDataDialog
from .census_objects import State, County, Tract



class GetNSIData:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GetNSIData_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
        
        self.dir = tempfile.gettempdir() 
        self.states = self.get_states()
        self.fips = None
        
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Get NSI Data')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GetNSIData', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/get_nsi_data/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Get NSI Data'),
            callback=self.run,
            parent=self.iface.mainWindow())
            
        # self.add_action(
            # icon_path,
            # text=self.tr(u'Get NSI Data by State'),
            # callback=self.runState,
            # parent=self.iface.mainWindow())

        # self.add_action(
            # icon_path,
            # text=self.tr(u'Get NSI Data by FIPS'),
            # callback=self.runFips,
            # parent=self.iface.mainWindow())
            
        # self.add_action(
            # icon_path,
            # text=self.tr(u'Get NSI Data by Bounding Box'),
            # callback=self.runBbox,
            # parent=self.iface.mainWindow())
            
        # self.add_action(
            # icon_path,
            # text=self.tr(u'Get NSI Data by Shape'),
            # callback=self.runShape,
            # parent=self.iface.mainWindow())
            
        # will be set False in run()
        self.first_start = True

    
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Get NSI Data'),
                action)
            self.iface.removeToolBarIcon(action)
    
    def get_states(self):
        
        # Read in states, counties, and tracts with their fips codes
        json_file_path = os.path.join(
            self.plugin_dir,
            "tracts_nested.json"
            ).replace('\\','/') # There must be a better solution for dealing with slash types here.
        with open(json_file_path) as f:
            data = json.loads(f.read())
            
            states = {}
            for i in data:
                state_name = i['state_name']
                state_fips = i['state_fips']
                state_counties = {}
                for j in i['counties']:
                    county_name = j['county_name']
                    county_fips = j['county_fips']
                    county_tracts = {"Use County FIPS": Tract("Use County Fips", county_fips)}
                    for k in j['tracts']:
                        tract_name = k['tract_name']
                        tract_fips = k['tract_fips']
                        tract_k = Tract(tract_name, tract_fips)
                        county_tracts[tract_name] = tract_k
                    county_j = County(county_name, county_fips, county_tracts)
                    state_counties[county_name] = county_j
                state_i = State(state_name, state_fips, state_counties)
                states[state_name] = state_i
        return(states)    
    
    def run(self):
        self.dlg = GetNSIDataDialog(self.iface)
        self.dir = tempfile.gettempdir()
        
        #self.dlg.folderButton.clicked.connect(self.select_output_folder)
        #self.dlg.saveLine.textChanged.connect(self.update_dir)
        
        self.dlg.show()
        
        result = self.dlg.exec_()
        
        if result:
            if self.dlg.stateButton.isChecked():
                self.runState()
            elif self.dlg.fipsButton.isChecked():
                self.runFips()
            elif self.dlg.bboxButton.isChecked():
                self.runBbox()
            elif self.dlg.shapeButton.isChecked():
                self.runShape()
            else:
                # This should not happen
                pass
        
    def runState(self):
        """Run method that performs all the real work"""
        self.dlgState = GetStateNSIDataDialog(self.iface)
        self.dir = tempfile.gettempdir()
        self.dlgState.stateFolderButton.clicked.connect(self.state_select_output_folder)
        self.dlgState.stateSaveLine.textChanged.connect(self.state_update_dir)
        
        
        # Clear the contents of the state comboBox from previous runs
        self.dlgState.comboBoxState.clear()
        # Populate the comboBox with state names
        self.dlgState.comboBoxState.addItems([state for state in self.states.keys()])
        

        # show the dialog
        self.dlgState.show()
        # Run the dialog event loop
        result = self.dlgState.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            fips = self.states[self.dlgState.comboBoxState.currentText()].fips[0]
            print(f"fips: {fips}")
            dest = self.dir
            # self.getStateData(fips, dest)
            self.dlgState.downloader.get_state_data(fips, dest)
            
    
    def runFips(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        self.dlgFips = GetFipsNSIDataDialog(self.iface)
        self.dir = tempfile.gettempdir()
        self.dlgFips.fipsFolderButton.clicked.connect(self.fips_select_output_folder)
        self.dlgFips.fipsSaveLine.textChanged.connect(self.fips_update_dir)
        self.dlgFips.comboBoxState.addItems([state for state in self.states.keys()])
        self.fips_update_combo_box_county()
        self.fips_update_combo_box_tract()
        self.fips_update_label()
        
        self.dlgFips.comboBoxState.currentTextChanged.connect(self.fips_update_combo_box_county)
        self.dlgFips.comboBoxCounty.currentTextChanged.connect(self.fips_update_combo_box_tract)
        self.dlgFips.comboBoxTract.currentTextChanged.connect(self.fips_update_label)
        
        # show the dialog
        self.dlgFips.show()
        # Run the dialog event loop
        result = self.dlgFips.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            self.dlgFips.downloader.get_structs_fips(self.fips, self.dir)
            pass
    
    def runBbox(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        self.dlgBbox = GetBboxNSIDataDialog(self.iface)
        self.dir = tempfile.gettempdir()
        
        self.dlgBbox.comboBoxLayer.addItems([lyr.name() for lyr in QgsProject.instance().mapLayers().values()])
        
        self.dlgBbox.bboxFolderButton.clicked.connect(self.bbox_select_output_folder)
        self.dlgBbox.bboxSaveLine.textChanged.connect(self.bbox_update_dir)
        self.dlgBbox.extentButtonCanvas.clicked.connect(self.bbox_get_canvas_extent)
        self.dlgBbox.extentButtonLayer.clicked.connect(self.bbox_get_layer_extent)
        self.dlgBbox.dlButton.clicked.connect(self.bbox_validate_coords)
        
        # show the dialog
        self.dlgBbox.show()
        # Run the dialog event loop
        result = self.dlgBbox.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
    
    def runShape(self):
        """Run method that performs all the real work"""
        
        # Create the dialog with elements (after translation) and keep reference
        self.dlgShape = GetShapeNSIDataDialog(self.iface)
        self.dir = tempfile.gettempdir()
        
        layers = []
        for layer in QgsProject.instance().mapLayers().values():
            try:
                if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    layers.append(layer.name())
            except Exception as e:
                print(f"Failed to check geometryType. {e}") 
        self.dlgShape.comboBoxLayer.addItems(layers)
        
        self.dlgShape.shapeFolderButton.clicked.connect(self.shape_select_output_folder)
        self.dlgShape.shapeSaveLine.textChanged.connect(self.shape_update_dir)
        
        # show the dialog
        self.dlgShape.show()
        # Run the dialog event loop
        result = self.dlgShape.exec_()
        # See if OK was pressed
        if result:
            layer_name = self.dlgShape.comboBoxLayer.currentText()
            if layer_name == "":
                pass
            else:
                layer = QgsProject.instance().mapLayersByName(layer_name)[0]
                
                exp = QgsJsonExporter(layer)
                exp.setIncludeAttributes(False)
                layer_geojson = exp.exportFeatures(layer.getFeatures())
                
                self.dlgShape.downloader.get_structs_shape(layer_name, layer_geojson, self.dir)
    
    def state_select_output_folder(self):
        folderName = QFileDialog.getExistingDirectory(self.dlgState, "Select output folder")
        self.dlgState.stateSaveLine.setText(folderName)
        self.state_update_dir()
        
    def state_update_dir(self):
        self.dir = self.dlgState.stateSaveLine.text()    
        
    def fips_update_combo_box_county(self):
        self.dlgFips.comboBoxCounty.clear()
        state = self.dlgFips.comboBoxState.currentText()
        counties = self.states[state].counties.keys()
        self.dlgFips.comboBoxCounty.addItems([county for county in counties])
        
    def fips_update_combo_box_tract(self):
        state = self.dlgFips.comboBoxState.currentText()
        county = self.dlgFips.comboBoxCounty.currentText()
        self.dlgFips.comboBoxTract.clear()
        counties = self.states.get(state).counties
        county_get = counties.get(county)
        if county_get is None:
            # This function also gets called when the county box is cleared when a new state is selected.
            # This would an AttributeError when trying to get the tracts
            pass
        else:
            tracts = county_get.tracts.keys()
            self.dlgFips.comboBoxTract.addItems(tracts)
            
    def fips_update_label(self):
        state = self.dlgFips.comboBoxState.currentText()
        county = self.dlgFips.comboBoxCounty.currentText()
        tract = self.dlgFips.comboBoxTract.currentText()
        county_get = self.states.get(state).counties.get(county)
        if county_get is None:
            pass
        else:
            tract_get = county_get.tracts.get(tract)
            if tract_get is None:
                pass
            else:
                self.dlgFips.labelFips.setText(tract_get.fips)
                self.fips = tract_get.fips
                
    def fips_select_output_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self.dlgFips, "Select output folder")
        self.dlgFips.fipsSaveLine.setText(folder_name)
        self.fips_update_dir()
        
    def fips_update_dir(self):
        self.dir = self.dlgFips.fipsSaveLine.text()
    
    def bbox_get_canvas_extent(self):
        request_crs = QgsCoordinateReferenceSystem("EPSG:4326")  # WGS84
        canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        
        crs_transform = QgsCoordinateTransform()
        crs_transform.setSourceCrs(canvas_crs)
        crs_transform.setDestinationCrs(request_crs)
            
        extent = crs_transform.transform(self.iface.mapCanvas().extent())        
        
        self.dlgBbox.spinBoxNorth.setValue(extent.yMaximum())
        self.dlgBbox.spinBoxSouth.setValue(extent.yMinimum())
        self.dlgBbox.spinBoxEast.setValue(extent.xMaximum())
        self.dlgBbox.spinBoxWest.setValue(extent.xMinimum())
    
    def bbox_get_layer_extent(self):
        request_crs = QgsCoordinateReferenceSystem("EPSG:4326")  # WGS84
        canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        
        crs_transform = QgsCoordinateTransform()
        crs_transform.setSourceCrs(canvas_crs)
        crs_transform.setDestinationCrs(request_crs)
        
        layer_name = self.dlgBbox.comboBoxLayer.currentText()
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        extent = crs_transform.transform(layer.extent())        
        
        self.dlgBbox.spinBoxNorth.setValue(extent.yMaximum())
        self.dlgBbox.spinBoxSouth.setValue(extent.yMinimum())
        self.dlgBbox.spinBoxEast.setValue(extent.xMaximum())
        self.dlgBbox.spinBoxWest.setValue(extent.xMinimum())
    
    def bbox_validate_coords(self):
        # I think the following are true:
        #   south must be less than north
        #   west must be less than east 
        #   Will have to prevent or handle bbox crossing int'l dateline. 
        north = self.dlgBbox.spinBoxNorth.value()
        south = self.dlgBbox.spinBoxSouth.value()
        east = self.dlgBbox.spinBoxEast.value()
        west = self.dlgBbox.spinBoxWest.value()
        bbox = f"{west},{south},{west},{north},{east},{north},{east},{south},{west},{south}"
        coords = f"[{west},{south}],[{west},{north}],[{east},{north}],[{east},{south}],[{west},{south}]"
        
        option = None
        if self.dlgBbox.radioButtonStruct.isChecked():
            option = "struct"
        else:
            option = "stat"
            
        # check CONUS
        if north > 49.4 and south > 49.4:
            # Bbox is completely north of CONUS
            # check Alaska
            if north > 51.17 and north < 71.45 and south > 51.17 and east < -130 and west > -180:
                # Bbox is within Alaska's bbox (may still be in western Canada)
                self.bbox_download(bbox, option)
            # add elif to check if partially outside AK bbox
            else:
                msg = QMessageBox.warning(
                None,
                self.tr("Bounding box outside U.S."),
                self.tr("""The defined area is completely outside the United States."""),
                QMessageBox.StandardButtons(
                    QMessageBox.Cancel))
        elif north < 23.39 and south < 23.39:
            # Bbox is completely south of CONUS
            # check Hawaii
            if north > 18.86 and north < 28.518 and south > 18.86 and east < -154.755 and west > -178.45:
                # Bbox is within Hawaii's bbox (may still not be over land)
                self.bbox_download(bbox, option)
            # add elif to check if partially outside HI bbox
            else:
                msg = QMessageBox.warning(
                None,
                self.tr("Bounding box outside U.S."),
                self.tr("""The defined area is completely outside the United States."""),
                QMessageBox.StandardButtons(
                    QMessageBox.Cancel))
        elif west > -124.85 and east < -66.88:
            lat_span = abs(north - south)
            lon_span = abs(east - west)
            area = lat_span * lon_span
            if area < 6: # What is a good value here?
                self.bbox_download(bbox, coords, option)
            else:
                msg = QMessageBox.warning(
                None,
                self.tr("Area too large"),
                self.tr("""The defined area is too large. Consider downloading a statewide dataset or use the Get NSI Data by FIPS tool."""),
                QMessageBox.StandardButtons(
                    QMessageBox.Cancel))
        # add elif to check if partially outside CONUS bbox
        else:
            msg = QMessageBox.warning(
            None,
            self.tr("Bounding box outside U.S."),
            self.tr("""The defined area is completely outside the United States."""),
            QMessageBox.StandardButtons(
                QMessageBox.Cancel))
        # check size
    
    def bbox_select_output_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self.dlgBbox, "Select output folder")
        self.dlgBbox.bboxSaveLine.setText(folder_name)
        self.bbox_update_dir()
        
    def bbox_update_dir(self):
        self.dir = self.dlgBbox.bboxSaveLine.text()
        
    def bbox_download(self, bbox, coords, option):
        print(f"coords: {coords}, option: {option}")
        if option is None:
            msg = QMessageBox.warning(
            None,
            self.tr("No download type selected"),
            self.tr("""You have not chosen a download type. You must choose at least one option."""),
            QMessageBox.StandardButtons(
                QMessageBox.Cancel))
            pass
        elif option == "struct":
            self.dlgBbox.downloader.get_structs_bbox(bbox, self.dir)
        else:
            self.dlgBbox.downloader.get_stats_bbox(bbox, coords, self.dir)
        
    def shape_select_output_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self.dlgShape, "Select output folder")
        self.dlgShape.shapeSaveLine.setText(folder_name)
        self.shape_update_dir()
        
    def shape_update_dir(self):
        self.dir = self.dlgShape.shapeSaveLine.text()   

        
        
        
        
        
        
