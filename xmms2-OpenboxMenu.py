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

import optparse
import ConfigParser
import os
import sys

import Tkinter
import tkSimpleDialog

import xmmsclient
from xmmsclient import collections as xc

from xml.sax.saxutils import escape, unescape, quoteattr
#===============================================================================
#Helper Methods
def marker(isMarked):
    if isMarked is None:
        return ""
    if isMarked:
        return "=> "
    else:
        return ".     "

def parametersToString(command, parameters):
    parameterString = ""
    if parameters is not None:
        for (key, value) in parameters.items():
            parameterString += "--" + key + "=" + quoteattr(str(value)) + " "

    parameterString += "--" + command + " "
    return parameterString

def humanReadableSize(size):
    for x in ['bytes','KB','MB','GB']:
        if size < 1024.0:
            return "%3.2f%s" % (size, x)
        size /= 1024.0

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
#Classes
class Label():
    def __init__(self, label, isMarked=None):
        self.label = label
        self.isMarked = isMarked
    
    def write(self):
        formattedLabel = quoteattr(marker(self.isMarked) + self.label)
        
        print "<item label={0}>".format(formattedLabel)
        print "</item>"

class Button():
    def __init__(self, label, command, parameters=None, isMarked=None):
        self.label = label
        self.command = command
        self.parameters = parameters
        self.isMarked = isMarked
    
    def write(self):
        formattedLabel = marker(self.isMarked) + self.label
        formattedLabel = quoteattr(formattedLabel)
        paramString = parametersToString(self.command, self.parameters)
        
        print "<item label={0}>".format(formattedLabel)
        print " <action name=\"Execute\">"
        print "  <execute>{0} {1}</execute>".format(__file__, paramString)
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
    def __init__(self, label, command, parameters=None, isMarked=None):
        self.label = label
        self.command = command
        self.parameters = parameters
        self.isMarked = isMarked
    
    def write(self):
        formattedLabel = quoteattr(marker(self.isMarked) + self.label)
        paramString = parametersToString(self.command, self.parameters)  
        command = quoteattr("{0} {1}".format(__file__, paramString))

        print "<menu execute={0} id={1} label={2}/>".format(command,
                                                            quoteattr(paramString),
                                                            formattedLabel)

class Seperator():
    def __init__(self, label=None):
        self.label = label
    
    def write(self):
        if self.label is None:
            print "<separator/>"
        else:
            print "<separator label={0}/>".format(quoteattr(self.label))

class Container():
    def __init__(self, entry):
        self.entry = entry
        
    def write(self):
        print "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        print "<openbox_pipe_menu>"

        self.entry.write()

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
            PipeMenu(groupLabel,
                     "alphabetIndexArtists", 
                     {"alphabetIndex": str(key)} ).write()

class ArtistsList():
    def __init__(self, artist):
        self.artistMatch = xc.Match( field="artist", value= str(artist)+"*" )          
            
    def write(self):   
        results = xmms.coll_query_infos(self.artistMatch, ["artist"] )

        for result in results:
            artist = readString(result, 'artist')
            PipeMenu(artist, "indexAlbum", {"artist": artist} ).write()

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
                PipeMenu(label, "indexTracks", {"artist": self.artist, "album": album} ).write()

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
                        
            deleteButton = Button("delete", "removeFromPlaylist", {"listPosition": str(counter)})
            addToCurrentPlaylist = Button("Add to Playlist", "insertIntoPlaylist", {"id": str(id)})
            
            trackInfo = PipeMenu("Infos", "trackInfo", {"id": str(id)})  
            
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
        Label("Duration \t: " + readString(minfo, 'duration')).write()
        Seperator().write()     
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
            Label("Presets:").write()
            config = ConfigParser.RawConfigParser()
            absolutePath = os.path.expanduser("~/.config/xmms2/clients/openboxMenu/configPresets.ini")
            config.read(absolutePath)
            
            for preset in config.sections():
                Button(preset, "preset-load", 
                      { "presetName"  : preset} ).write()
              
            Seperator().write()

            namespaces = set()
            submenues = list()
        
            for entry in resultData:
                namespaces.add(entry.split('.')[0])
                
            for setEntry in namespaces:
                submenues.append(PipeMenu(setEntry, "config", {"configKey": str(setEntry)} ))
            
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

    print "<openbox_pipe_menu>"

    if status == xmmsclient.PLAYBACK_STATUS_PLAY:
        Button("⧐ Pause", "pause").write()
    else:
        Button("⧐ Play", "play").write()

    Button("≫ next", "next").write()
    Button("≪ prev", "prev").write()
    Seperator().write()
    
    PipeMenu("Medialib", "alphabetIndexMenu", {}).write()
    PipeMenu("Config", "config", {}).write()
    Seperator().write()

    newPlaylistButton = Button("New Playlist", "createPlaylist")
    playlistMenu = [newPlaylistButton, Seperator()];
    
    for playlist in playlists:
        loadButton = Button("load", "loadPlaylist", {"name": playlist})
        deleteButton = Button("delete", "removePlaylist", {"name": playlist})
        
        playlistMenu.append(Menu("xmms-playlist-"+playlist,
                                 playlist,
                                 [loadButton, Seperator(), deleteButton],
                                 playlist == activePlaylist))

    Menu("xmms-playlists",
         "Playlist: {0}".format(activePlaylist),
         playlistMenu ).write()

    Seperator().write()

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

        jumpButton = Button("jump",
                            "playlistJump",
                            {"listPosition": str(id)} )

        deleteButton = Button("delete",
                              "removeFromPlaylist",
                              {"listPosition": str(id)} )
        
        entryLabel = "{0}|  {1} - {2} - {3}".format(
                      str(id).zfill(3), artist, album, title)
                     
        Menu("xmms-activePlaylist-"+str(medialibId),
             entryLabel,
             [jumpButton, Seperator(), deleteButton],
             medialibId == activeId ).write()

    print "</openbox_pipe_menu>"

#===============================================================================
#Pipe Menus
def alphabetIndexMenu(option, opt, value, parser):
    Container(AlphabetIndex()).write()

def alphabetIndexArtists(option, opt, value, parser):
    Container(ArtistsList(unescape(parser.values.alphabetIndex))).write()

def indexAlbum(option, opt, value, parser):
    Container(AlbumList(unescape(parser.values.artist))).write()

def indexTracks(option, opt, value, parser):
    Container(TrackList(unescape(parser.values.artist),
                        unescape(parser.values.album))).write()
                        
def trackInfo(option, opt, value, parser):
    Container(TrackInfo(parser.values.id)).write()

def config(option, opt, value, parser):
    Container(Config(parser.values.configKey)).write()
  
#===============================================================================
#Commands
def play(option, opt, value, parser):
    xmms.playback_start()

def pause(option, opt, value, parser):
    xmms.playback_pause()

def next(option, opt, value, parser):
    xmms.playlist_set_next_rel(1)
    xmms.playback_tickle()

def prev(option, opt, value, parser):
    xmms.playlist_set_next_rel(-1)
    xmms.playback_tickle()

def playlistJump(option, opt, value, parser):
    xmms.playlist_set_next(parser.values.listPosition)
    xmms.playback_tickle()

def insertIntoPlaylist(option, opt, value, parser):
    xmms.playlist_insert_id(0, parser.values.id)
    
def removeFromPlaylist(option, opt, value, parser):
    xmms.playlist_remove_entry(parser.values.listPosition)
        
def loadPlaylist(option, opt, value, parser):
    xmms.playlist_load(parser.values.name)

def createPlaylist(option, opt, value, parser):
    root = Tkinter.Tk()
    root.withdraw()

    name = tkSimpleDialog.askstring("New Playlist Name",
                                    "Enter a new Playlist Name")
    if name is not None:
        xmms.playlist_create(name)

def removePlaylist(option, opt, value, parser):
    xmms.playlist_remove(parser.values.name)
        
def presetLoad(option, opt, value, parser):
    config = ConfigParser.RawConfigParser()
    absolutePath = os.path.expanduser("~/.config/xmms2/clients/openboxMenu/configPresets.ini")
    config.read(absolutePath)
    
    for key, value in config.items(parser.values.presetName):
        xmms.config_set_value(key, value)

#===============================================================================
#Main
if __name__ == "__main__":
    xmms = xmmsclient.XMMSSync("xmms2-OpenboxMenu")
    try:
        xmms.connect(os.getenv("XMMS_PATH"))
        
    except IOError, detail:
        print "<openbox_pipe_menu>"
        Seperator("Connection failed: "+ str(detail)).write()
        print "</openbox_pipe_menu>"
        sys.exit(1)
        
    parser = optparse.OptionParser()

    parser.add_option("--play", action="callback", callback=play, help="play")
    parser.add_option("--pause", action="callback", callback=pause, help="stop")
    parser.add_option("--next", action="callback", callback=next, help="next")
    parser.add_option("--prev", action="callback", callback=prev, help="prev")

    parser.add_option("--id", action="store", type="int", dest="id")
    parser.add_option("--artist", action="store", type="string", dest="artist")
    parser.add_option("--album", action="store", type="string", dest="album")

    parser.add_option("--alphabetIndex", action="store", type="string", dest="alphabetIndex")
    parser.add_option("--alphabetIndexMenu", action="callback", callback=alphabetIndexMenu, help="")
    parser.add_option("--alphabetIndexArtists", action="callback", callback=alphabetIndexArtists, help="")
    parser.add_option("--indexAlbum", action="callback", callback=indexAlbum, help="")
    parser.add_option("--indexTracks", action="callback", callback=indexTracks, help="")

    parser.add_option("--listPosition", action="store", type="int", dest="listPosition")
    parser.add_option("--playlistJump", action="callback", callback=playlistJump, help="Jump to index in Playlist")

    parser.add_option("--insertIntoPlaylist", action="callback", callback=insertIntoPlaylist)
    parser.add_option("--removeFromPlaylist", action="callback", callback=removeFromPlaylist)

    parser.add_option("--name", action="store", type="string", dest="name")
    parser.add_option("--loadPlaylist", action="callback", callback=loadPlaylist, help="")
    parser.add_option("--createPlaylist", action="callback", callback=createPlaylist, help="")
    parser.add_option("--removePlaylist", action="callback", callback=removePlaylist, help="")

    parser.add_option("--trackInfo", action="callback", callback=trackInfo, help="")

    parser.add_option("--config", action="callback", callback=config, help="")
    parser.add_option("--configKey", action="store", type="string", dest="configKey")

    parser.add_option("--preset-load", action="callback", callback=presetLoad, help="")
    parser.add_option("--presetName", action="store", type="string", dest="presetName")
    

    (options, args) = parser.parse_args()

    if len(sys.argv) == 1:
        menu()

