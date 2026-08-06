# plugin Seismic Bin Attributes and Binning

## Another little QGIS tool for seismic acquisition

Click with the mouse on the canvas to select the nearest bin. A seperate window pops up that displays offset, spider and rose diagrams. Change to another bin manually by typing a different bin (src, rcv), seperated by a space or comma.

By pressing the button "Bin traces" this will bin traces using the selected offset and source indexes.


![til](./binning_clipchamp.gif)

The data is stored in a SQLite database with tables bins and traces. To create this database from SPS (R, S, X) files, this is done using the app in the repsoitory [binning_cpp](https://github.com/bvermeulen/binning_cpp).
