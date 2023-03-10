# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GetNSIData
                                 A QGIS plugin
 This plugin downloads data from the U.S. National Structures Inventory for a specified state or region.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2022-12-21
        copyright            : (C) 2022 by Sebastian Rowan
        email                : sebastian.rowan@unh.edu
        git sha              : $Format:%H$
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


class State:

    def __init__(cls, name, fips, counties):
        cls.name = name
        cls.fips = fips,
        cls.counties = counties

class County:

    def __init__(cls, name, fips, tracts):
        cls.name = name
        cls.fips = fips,
        cls.tracts = tracts    

class Tract:

    def __init__(cls, name, fips):
        cls.name = name
        cls.fips = fips


