#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Copyright 2011 Eli. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are
# permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, this list of
#       conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright notice, this list
#       of conditions and the following disclaimer in the documentation and/or other materials
#       provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY ELI ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ELI OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import ConfigParser
import os
import sys

from pipes import quote

from xml.sax.saxutils import escape, unescape, quoteattr

import Tkinter
import tkSimpleDialog

import xmmsclient
from xmmsclient import collections as xc

#===============================================================================
#Helper Methods    
def createCommand(parameters):
    parameterString = ""

    for id, val in enumerate(parameters):
        parameterString += quote(str(val)) + " "
    
    return "{0} {1}".format(__file__, parameterString)

def humanReadableSize(size):
    for x in ['bytes','KB','MB','GB']:
        if size < 1024.0:
            return "%3.2f%s" % (size, x)
        size /= 1024.0
        
def humanReadableDuration(milliseconds):
    seconds = int(milliseconds) / 1000
    minutes, seconds = divmod(seconds, 60)
    if minutes > 0:
        return "{0}m {1}s".format(minutes, seconds)
    else:
        return "{1}s".format(seconds)

def readString(dictionary, key, default=""):
    if key in dictionary:
        value = dictionary[key]
        if isinstance(value, basestring):
            return value.encode('utf8')
        else:
            return str(value)
    else:
        return default

#===============================================================================
#Openbox menu writers

def marker(isMarked):
    if isMarked is None:
        return ""
    if isMarked:
        return "=> "
    else:
        return ".     "

class Label():
    def __init__(self, label, isMarked=None):
        self.label = label
        self.isMarked = isMarked
    
    def write(self):
        formattedLabel = quoteattr(marker(self.isMarked) + self.label)
        
        print "<item label={0}>".format(formattedLabel)
        print "</item>"

class Button():
    def __init__(self, label, commands, isMarked=None):
        self.label = label
        self.commands = commands
        self.isMarked = isMarked
    
    def write(self):
        formattedLabel = marker(self.isMarked) + self.label
        formattedLabel = quoteattr(formattedLabel)
        
        command = createCommand(self.commands)
        
        print "<item label={0}>".format(formattedLabel)
        print " <action name=\"Execute\">"
        print "  <execute>{0}</execute>".format(command)
        print " </action>"
        print "</item>"

class Menu():
    def __init__(self, id, label, entries=None, isMarked=None):
        self.id = id
        self.label = label
        self.entries = entries
        self.isMarked = isMarked
        
    def write(self):
        formattedMarker = marker(self.isMarked) + self.label
        print "<menu id={0} label={1}>".format(quoteattr(self.id),
                                               quoteattr(formattedMarker))
        
        for entry in self.entries:
            if entry is not None:
                entry.write()

        print "</menu>"

class PipeMenu():
    def __init__(self, label, commands, isMarked=None):
        self.label = label
        self.commands = commands
        self.isMarked = isMarked
    
    def write(self):
        formattedLabel = quoteattr(marker(self.isMarked) + self.label)

        command = createCommand(self.commands)

        print "<menu execute={0} id={1} label={2}/>".format(quoteattr(command),
                                                            quoteattr(command),
                                                            formattedLabel)

class Separator():
    def __init__(self, label=None):
        self.label = label
    
    def write(self):
        if self.label is None:
            print "<separator/>"
        else:
            print "<separator label={0}/>".format(quoteattr(self.label))

class Container():
    def __init__(self, entries):
        self.entries = entries
        
    def write(self):
        print "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        print "<openbox_pipe_menu>"

        if isinstance(self.entries, list):
            for entry in self.entries:
                if entry is not None:
                    entry.write()
        else:
            self.entries.write()

        print "</openbox_pipe_menu>"

#===============================================================================
#Writers
class AlphabetIndex():
    def write(self):
        indexKeys = map(chr, range(65, 91))
        for key in indexKeys:
            artist = xc.Match( field="artist", value= str(key)+"*" )          
            results = xmms.coll_query_infos( artist, ["artist"])
            
            groupLabel = "{0} ({1})".format(str(key), str(len(results)))
            PipeMenu(groupLabel, ["alphabetIndexArtists", str(key)] ).write()

class ArtistsList():
    def __init__(self, artist):
        self.artistMatch = xc.Match( field="artist", value= str(artist)+"*" )          
            
    def write(self):   
        results = xmms.coll_query_infos(self.artistMatch, ["artist"] )

        for result in results:
            artist = readString(result, 'artist')
            PipeMenu(artist, ["indexAlbum", artist] ).write()

class AlbumList():
    def __init__(self, artist):
        self.artist = artist
        self.artistMatch = xc.Match(field="artist", value=artist)      

    def write(self):          
        results = xmms.coll_query_infos(self.artistMatch, ["date", "album"] )

        for result in results:
            if result["album"] is not None:
                album = readString(result, 'album')
                label = "[" + readString(result, 'date') + "] " + album
                PipeMenu(label, ["indexTracks", self.artist, album] ).write()

class TrackList():
    def __init__(self, artist, album):
        self.artist = artist
        self.album = album
        
        self.match = xc.Intersection(xc.Match(field="artist", value=self.artist), 
                                     xc.Match(field="album", value=self.album))
    
    def write(self):
        results = xmms.coll_query_infos( self.match, ["tracknr", "title", "id"])

        counter = 0
        for result in results:
            id = str(result["id"])
            title = readString(result, 'title')
            trackNumber = readString(result, 'tracknr')
            
            deleteButton = Button("delete", ["removeFromPlaylist", str(counter)] )
            addToCurrentPlaylist = Button("Add to Playlist", ["track", "add", str(id)] )
            trackInfo = PipeMenu("Infos", ["track", "info", str(id)] )  
            
            Menu("xmms-track-"+id, trackNumber + " - " + title, [addToCurrentPlaylist, trackInfo]).write()
            counter +=1

class TrackInfo():
    def __init__(self, id):
        self.id = int(id)
                                     
    def write(self):
        minfo = xmms.medialib_get_info(self.id)

        Label("Artist \t: " + readString(minfo, 'artist')).write()
        Label("Album \t: " + readString(minfo, 'album')).write()
        Label("Title \t: " + readString(minfo, 'title')).write()
        Label("Duration \t: " + humanReadableDuration(minfo['duration'])).write()
        Separator().write()     
        Label("Size \t\t: " + humanReadableSize(minfo["size"])).write()
        Label("Bitrate \t: " + readString(minfo, 'bitrate')).write()
        
        url = readString(minfo, 'url')
        filename = url.split('/')[-1]

        Label("Url \t: " + url).write()
        Label("File \t: " + filename).write()

class Config():
    def __init__(self, configKey):
        self.configKey = configKey

    def write(self):      
        resultData = xmms.config_list_values();
        
        if self.configKey is None:
            Separator("Presets:").write()
            config = ConfigParser.RawConfigParser()
            absolutePath = os.path.expanduser("~/.config/xmms2/clients/openboxMenu/configPresets.ini")
            config.read(absolutePath)
            
            for preset in config.sections():
                Button(preset, ["preset-load", preset] ).write()
              
            Separator().write()

            namespaces = set()
            submenues = list()
        
            for entry in resultData:
                namespaces.add(entry.split('.')[0])
                
            for setEntry in namespaces:
                submenues.append(PipeMenu(setEntry, ["config", str(setEntry)] ))
            
            Menu("view all", "configView", submenues).write()
             
        else:
            namespaces = list()
            for entry in resultData:
                if entry.startswith(self.configKey):
                    namespaces.append(entry)
                    
            namespaces.sort()
            
            displayKeyChars = 0
            for entry in namespaces:
                displayKeyChars = max(displayKeyChars, len(entry))
                print len(entry)
                                
            print displayKeyChars
            
            for entry in namespaces:
                padding = displayKeyChars - len(entry) + 1
                Label(entry + (" " * padding) + "\t" + resultData[entry]).write()
                

#===============================================================================
#Main Menu
def menu():
    status = xmms.playback_status()
    playlists = xmms.playlist_list()
    activePlaylist = xmms.playlist_current_active()
    activePlaylistIds = xmms.playlist_list_entries()
    activeId = xmms.playback_current_id()

    menuEntries = list()

    if status == xmmsclient.PLAYBACK_STATUS_PLAY:
        menuEntries.append(Button("⧐ Pause", ["pause"] ))
    else:
        menuEntries.append(Button("⧐ Play", ["play"] ))

    menuEntries.append(Button("≫ next", ["next"] ))
    menuEntries.append(Button("≪ prev", ["prev"] ))
    menuEntries.append(Separator())
    
    menuEntries.append(PipeMenu("Medialib", ["alphabetIndexMenu"] ))
    menuEntries.append(PipeMenu("Config", ["config"] ))
    menuEntries.append(Separator())

    playlistMenu = list()
    playlistMenu.append(Button("New Playlist", ["createPlaylist"] ))
    playlistMenu.append(Separator())
    
    for playlist in playlists:
        loadButton = Button("load", ["loadPlaylist", playlist] )
        deleteButton = Button("delete", ["removePlaylist", playlist] )
        
        playlistMenu.append(Menu("xmms-playlist-"+playlist, playlist, [loadButton, Separator(), deleteButton], playlist == activePlaylist))

    menuEntries.append(Menu("xmms-playlists", "Playlist: {0}".format(activePlaylist), playlistMenu))
    menuEntries.append(Separator())

    displayRange = 20
    if activePlaylistIds.count(activeId) == 1:
        selectedIndex = activePlaylistIds.index(activeId)
        
        minIndex = max(0, selectedIndex - displayRange)
        maxIndex = min(len(activePlaylistIds), selectedIndex + 1 + displayRange)
    else:
        minIndex = 0;
        maxIndex = min(len(activePlaylistIds), displayRange)
    
    displayRange = range(minIndex, maxIndex)
    
    for id in displayRange:
        medialibId = activePlaylistIds[id]
            
        result = xmms.medialib_get_info(medialibId)

        artist = readString(result, 'artist')
        album = readString(result, 'album')
        title = readString(result, 'title')
        
        subMenuId = "xmms-activePlaylist-" + str(medialibId)
        entryLabel = "{0}|  {1} - {2} - {3}".format(
                      str(id).zfill(3), artist, album, title)
                     
        subMenu = Menu(subMenuId, entryLabel,
            [
                Button("jump", ["jump", str(id)] ),
                Separator(),
                PipeMenu("Infos", ["track", "info", str(medialibId)] ),
                Separator(),
                Button("delete", ["removeFromPlaylist", str(id)] )
            ],
            medialibId == activeId )
        
        menuEntries.append(subMenu)

    Container(menuEntries).write()

#===============================================================================
#Commands
def createPlaylist():
    root = Tkinter.Tk()
    root.withdraw()

    name = tkSimpleDialog.askstring("New Playlist Name",
                                    "Enter a new Playlist Name")
    if name is not None:
        xmms.playlist_create(name)
   
def presetLoad(name):
    config = ConfigParser.RawConfigParser()
    absolutePath = os.path.expanduser("~/.config/xmms2/clients/openboxMenu/configPresets.ini")
    config.read(absolutePath)
    
    for key, value in config.items(name):
        xmms.config_set_value(key, value)

#===============================================================================
#Main
if __name__ == "__main__":
    xmms = xmmsclient.XMMSSync("xmms2-OpenboxMenu")
    try:
        xmms.connect(os.getenv("XMMS_PATH"))
        
    except IOError, detail:
        Container(Separator("Connection failed: "+ str(detail))).write()
        sys.exit(1)
    
    paramterCount = len(sys.argv)
    
    if paramterCount == 1:
    	menu()
    elif paramterCount >= 2:
        command = sys.argv[1]
        
        if command == "play":
            xmms.playback_start()
        
        if command == "pause":
            xmms.playback_pause()
            
        if command == "next":
            xmms.playlist_set_next_rel(1)
            xmms.playback_tickle()
            
        if command == "prev":
            xmms.playlist_set_next_rel(-1)
            xmms.playback_tickle()
  
        if command == "jump":
            position = int(sys.argv[2])
            xmms.playlist_set_next(position)
            xmms.playback_tickle()
        
        if command == "track":
            trackCommand = sys.argv[2]
            trackId = sys.argv[3]
            
            if trackCommand == "add":
                xmms.playlist_insert_id(0, trackId)
                
            if trackCommand == "info":
                Container(TrackInfo(trackId)).write()
            
        if command == "removeFromPlaylist":
            position = int(sys.argv[2])
            xmms.playlist_remove_entry(position)
        
        if command == "createPlaylist":
            createPlaylist()
        
        if command == "loadPlaylist":
            playlistName = str(sys.argv[2])
            xmms.playlist_load(playlistName)
            
        if command == "removePlaylist":
            playlistName = str(sys.argv[2])
            xmms.playlist_remove(playlistName)
            
        if command == "preset-load":
            presetName = str(sys.argv[2])
            presetLoad(presetName)
            
        if command == "alphabetIndexMenu":
            Container(AlphabetIndex()).write()
            
        if command == "alphabetIndexArtists":
            index = str(sys.argv[2])
            Container(ArtistsList(unescape(index))).write()
            
        if command == "indexAlbum":
            artist = str(sys.argv[2])
            Container(AlbumList(unescape(artist))).write()
        
        if command == "indexTracks":
            artist = str(sys.argv[2])
            album = str(sys.argv[3])
            Container(TrackList(unescape(artist), unescape(album))).write()
            
        if command == "config":
            configKey = None
            if paramterCount == 3:
                configKey = str(sys.argv[2])
                
            Container(Config(configKey)).write()

