Plugin Builder Results

Your plugin PictureLinker was created in:
    C:\Users\bruno\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\picture_linker

Your QGIS plugin directory is located at:
    C:/Users/bruno/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins


To create the plugin run the following in OSGeo4W shell:
pyrcc5.bat -o resources.py resources.qrc
or
python-qgis -m PyQt5.pyrcc_main -o resources.py resources.qrc

What's Next:

  * Copy the entire directory containing your new plugin to the QGIS plugin
    directory

  * Compile the resources file using pyrcc5

  * Run the tests (``make test``)

  * Test the plugin by enabling it in the QGIS plugin manager

  * Customize it by editing the implementation file: ``picture_linker.py``

  * Create your own custom icon, replacing the default icon.png

  * Modify your user interface by opening PictureLinker_dialog_base.ui in Qt Designer

  * You can use the Makefile to compile your Ui and resource files when
    you make changes. This requires GNU make (gmake)

For more information, see the PyQGIS Developer Cookbook at:
http://www.qgis.org/pyqgis-cookbook/index.html

(C) 2011-2018 GeoApt LLC - geoapt.com
