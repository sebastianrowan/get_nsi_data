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

import os
from qgis.core import QgsProject, Qgis
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QUrl, QByteArray
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply,  QNetworkAccessManager

class StateDownload:

    def __init__(cls, parent=None, iface=None):
        cls.parent = parent
        cls.iface = iface
        cls.nam = QNetworkAccessManager()
        cls.nam.finished.connect(cls.reply_finished)
        # https://docs.qgis.org/2.8/en/docs/pyqgis_developer_cookbook/communicating.html#showing-progress

    def reply_finished(cls, reply):
        if reply != None:
            possibleRedirectUrl = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
             
            if possibleRedirectUrl != None: # if value, request is redirected.
                request = QNetworkRequest(possibleRedirectUrl)
                result = cls.nam.get(request)  
                result.downloadProgress.connect(lambda done,  all,  reply=result: cls.progress(done,  all,  reply))
            else:             
                if reply.error() != None and reply.error() != QNetworkReply.NoError:
                    cls.is_error = reply.errorString()
                    reply.abort()
                    reply.deleteLater()
                        
                elif reply.error() ==  QNetworkReply.NoError:
                    result = reply.readAll()
                    f = open(cls.filename, 'wb')
                    f.write(result)
                    f.close()      
                    
                    out_gpkg = cls.unzip(cls.filename)
                    (dir, file) = os.path.split(out_gpkg)
                    
                    try:
                        if not cls.layer_exists(file):
                            cls.iface.addVectorLayer(out_gpkg, file, 'ogr')
                    except:
                        pass
                        
                    
                    cls.iface.messageBar().pushMessage(
                        "Success", f"Downloaded file saved at {cls.dir}",
                        level=Qgis.Success, duration=5
                    )
                        
                    reply.deleteLater()

    def layer_exists(cls,  name):            
        # Return True if layer of given name exists in current instance.
        if len(QgsProject.instance().mapLayersByName(name)) != 0:
            return True
        else:
            return False
            
    def unzip(cls,  zip_file):
        import zipfile
        (dir, file) = os.path.split(zip_file)

        if not dir.endswith(':') and not os.path.exists(dir):
            os.mkdir(dir)
        
        try:
            zf = zipfile.ZipFile(zip_file)
    
            # extract files to directory structure
            for i, name in enumerate(zf.namelist()):
                if not name.endswith('/'):
                    outfile = open(os.path.join(dir, name), 'wb')
                    outfile.write(zf.read(name))
                    outfile.flush()
                    outfile.close()
                    return os.path.join(dir, name)
        except:
            return None

    def get_state_data(cls, fips, dest):
        url = QUrl(f"https://nsi.sec.usace.army.mil/downloads/nsi_2022/nsi_2022_{fips}.gpkg.zip")
        saveName = f"nsi_2022_{fips}.gpkg.zip"
        fullPath = f"{dest}\{saveName}"
        cls.dir = dest
        cls.filename = fullPath
        #cls.load_to_canvas = True
        req = QNetworkRequest(url)
        reply = cls.nam.get(req)


class APIDownload:

    def __init__(cls, parent=None, iface=None):
        cls.parent = parent
        cls.iface = iface
        cls.root_url = "https://nsi.sec.usace.army.mil/nsiapi/structures"
        cls.stats_url = "https://nsi.sec.usace.army.mil/nsiapi/stats"
        cls.nam = QNetworkAccessManager()
        cls.multi = False
        
        cls.nam.finished.connect(cls.api_reply_finished)
        cls.bbox_coords = None
        cls.nam_bbox = QNetworkAccessManager()
        cls.nam_bbox.finished.connect(cls.api_stat_reply_finished)
        
    
    def api_reply_finished(cls, reply):
        if reply.error() != None and reply.error() != QNetworkReply.NoError:
            cls.is_error = reply.errorString()
            cls.iface.messageBar().pushMessage(
                        "Error", cls.is_error,
                        level=Qgis.Critical
                    )
            reply.abort()
            reply.deleteLater()
                
        elif reply.error() ==  QNetworkReply.NoError:
            if cls.multi:
                pass
            else:
            
                result = reply.readAll() # result should be JSON response from API
            
                with open(cls.filename, 'wb') as f:
                    f.write(result)
            
                (dir, file) = os.path.split(cls.filename)
                try:
                    if not cls.layer_exists(file):
                        cls.iface.addVectorLayer(cls.filename, file, 'ogr')
                except:
                    pass
            
            reply.deleteLater()
    
    def api_stat_reply_finished(cls, reply):
        if reply.error() != None and reply.error() != QNetworkReply.NoError:
            cls.is_error = reply.errorString()
            cls.iface.messageBar().pushMessage(
                        "Error", cls.is_error,
                        level=Qgis.Critical
                    )
            reply.abort()
            reply.deleteLater()
                
        elif reply.error() ==  QNetworkReply.NoError:
            result = reply.readAll().data().decode() # convert to plain text for adding to json file
            geojson_output = cls.create_stats_geojson(result)
            # modify json here into geojson with bbox coords and other required fields.
            
            with open(cls.filename, 'w') as f:
                f.write(geojson_output)
            
            (dir, file) = os.path.split(cls.filename)
            try:
                if not cls.layer_exists(file):
                    cls.iface.addVectorLayer(cls.filename, file, 'ogr')
            except:
                pass
            
            cls.bbox_coords = None
            reply.deleteLater()
    
    def create_stats_geojson(cls, result):
        json_text0 = """{
            "type": "FeatureCollection",
            "name": "NSI Stats Bounding Box",
            "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
            "features": [
            { "type": "Feature", 
            "properties":
            """
        
        json_text1 = """,
            "geometry": { "type": "Polygon", "coordinates": [ [ 
            """
        
        json_text2 = """ ] ] }
            }
            ]
            }"""
            
        json_text = f"{json_text0}{result}{json_text1}{cls.bbox_coords}{json_text2}"
        return(json_text)
            
    def layer_exists(cls,  name):            
        # Return True if layer of given name exists in current instance.
        if len(QgsProject.instance().mapLayersByName(name)) != 0:
            return True
        else:
            return False
            
    def get_structs_fips(cls, fips, dest, saveAs='.geojson'):
        if fips is None:
            pass
        else:
            url = QUrl(f"{cls.root_url}?fips={fips}&fmt=fs")
            saveName = f"nsi_2022_{fips}{saveAs}"
            fullPath = f"{dest}/{saveName}"
            cls.dir = dest
            cls.filename = fullPath
            req = QNetworkRequest(url)
            reply = cls.nam.get(req)
            
    def get_structs_bbox(cls, bbox, dest ,saveAs='.geojson'):
        url = QUrl(f"{cls.root_url}?bbox={bbox}&fmt=fs")
        saveName = f"nsi_2022_bbox_{bbox}{saveAs}"
        fullPath = f"{dest}/{saveName}"
        cls.dir = dest
        cls.filename = fullPath
        req = QNetworkRequest(url)
        reply = cls.nam.get(req)
        
    def get_stats_bbox(cls, bbox, coords, dest ,saveAs='.json'):
        url = QUrl(f"{cls.stats_url}?bbox={bbox}")
        saveName = f"nsi_2022_stats_bbox_{bbox}{saveAs}"
        fullPath = f"{dest}/{saveName}"
        cls.dir = dest
        cls.filename = fullPath
        cls.bbox_coords = coords
        req = QNetworkRequest(url)
        reply = cls.nam_bbox.get(req)
    
    def get_structs_shape(cls, layer_name, geojson, dest, saveAs='.geojson'):
        url = QUrl(cls.root_url)
        saveName = f"nsi_2022_{layer_name}{saveAs}"
        fullPath = f"{dest}/{saveName}"
        cls.dir = dest
        cls.filename = fullPath
        data = QByteArray()
        data.append(geojson)
        req = QNetworkRequest(url)
        req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader,
            'application/json')
        reply = cls.nam.post(req, data)