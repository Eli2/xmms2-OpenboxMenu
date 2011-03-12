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
            return "%3.1f%s" % (size, x)
        size /= 1024.0

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
            results.wait()
            
            groupLabel = "{0} ({1})".format(str(key), str(len(results.value())))
            PipeMenu(groupLabel,
                     "alphabetIndexArtists", 
                     {"alphabetIndex": str(key)} ).write()

class ArtistsList():
    def __init__(self, artist):
        self.artistMatch = xc.Match( field="artist", value= str(artist)+"*" )          
            
    def write(self):   
        results = xmms.coll_query_infos(self.artistMatch, ["artist"] )
        results.wait()
        for result in results.value():
            artist = str(result["artist"].encode('utf8'));
            PipeMenu(artist, "indexAlbum", {"artist": artist} ).write()

class AlbumList():
    def __init__(self, artist):
        self.artist = artist
        self.artistMatch = xc.Match(field="artist", value=artist)      

    def write(self):          
        results = xmms.coll_query_infos(self.artistMatch, ["date", "album"] )
        results.wait()
        for result in results.value():
            if result["album"] is not None:
                album = result["album"].encode('utf8');
                label = "[" + result["date"].encode('utf8') + "] " + album if result["date"] is not None else album   
                PipeMenu(label, "indexTracks", {"artist": self.artist, "album": album} ).write()

class TrackList():
    def __init__(self, artist, album):
        self.artist = artist
        self.album = album
        
        self.match = xc.Intersection(xc.Match(field="artist", value=self.artist), 
                                     xc.Match(field="album", value=self.album))
    
    def write(self):
        results = xmms.coll_query_infos( self.match, ["tracknr", "title", "id"])
        results.wait()

        counter = 0
        for result in results.value():
            id = str(result["id"])
            title = result["title"].encode('utf8') if result["title"] is not None else ""
            trackNumber = str(result["tracknr"]) if result["tracknr"] is not None else ""
                        
            deleteButton = Button("delete", "removeFromPlaylist", {"listPosition": str(counter)})
            addToCurrentPlaylist = Button("Add to Playlist", "insertIntoPlaylist", {"id": str(id)})
            
            trackInfo = PipeMenu("Infos", "trackInfo", {"id": str(id)})  
            
            Menu("xmms-track-"+id, trackNumber + " - " + title, [addToCurrentPlaylist, trackInfo]).write()
            counter +=1

class TrackInfo():
    def __init__(self, id):
        self.id = int(id)
                                     
    def write(self):
        results = xmms.medialib_get_info(self.id)
        results.wait()
        minfo = results.value()
        Label("Artist \t: " + minfo["artist"].encode('utf8')).write()
        Label("Album \t: " + minfo["album"].encode('utf8')).write()
        Label("Title \t: " + minfo["title"].encode('utf8')).write()
        Label("Duration \t: " + str(minfo["duration"])).write()
        Seperator().write()     
        Label("Size \t\t: " + humanReadableSize(minfo["size"])).write()
        Label("Bitrate \t: " + str(minfo["bitrate"])).write()
        Label("Url \t: " + minfo["url"].encode('utf8')).write()

#===============================================================================
#Main Menu
def menu():
    status = xmms.playback_status()
    status.wait()

    playlists = xmms.playlist_list()
    playlists.wait()

    result = xmms.playlist_current_active()
    result.wait()
    activePlaylist = result.value()

    activePlaylistEntries = xmms.playlist_list_entries()
    activePlaylistEntries.wait()

    seclected = xmms.playback_current_id()
    seclected.wait()

    print "<openbox_pipe_menu>"

    if status.value() == xmmsclient.PLAYBACK_STATUS_PLAY:
        Button("⧐ Pause", "pause").write()
    else:
        Button("⧐ Play", "play").write()

    Button("≫ next", "next").write()
    Button("≪ prev", "prev").write()
    Seperator().write()
    
    PipeMenu("Medialib", "alphabetIndexMenu", {}).write()
    Seperator().write()

    newPlaylistButton = Button("New Playlist", "createPlaylist")
    playlistMenu = [newPlaylistButton, Seperator()];
    
    for playlist in playlists.value():
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

    counter = 0

    for id in activePlaylistEntries.value():
        infos = xmms.medialib_get_info(id)
        infos.wait()
        result = infos.value();

        artist = result["artist"].encode('utf8');
        album = result["album"].encode('utf8');
        title = result["title"].encode('utf8');

        jumpButton = Button("jump",
                            "playlistJump",
                            {"listPosition": str(counter)} )

        deleteButton = Button("delete",
                              "removeFromPlaylist",
                              {"listPosition": str(counter)} )
        
        Menu("xmms-activePlaylist-"+str(id),
             "{0} - {1} - {2}".format(artist, album, title),
             [jumpButton, Seperator(), deleteButton],
             id == seclected.value() ).write()

        counter += 1

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

#===============================================================================
#Commands
def play(option, opt, value, parser):
    xmms.playback_start().wait()

def pause(option, opt, value, parser):
    xmms.playback_pause().wait()

def next(option, opt, value, parser):
    xmms.playlist_set_next_rel(1).wait()
    xmms.playback_tickle().wait()

def prev(option, opt, value, parser):
    xmms.playlist_set_next_rel(-1).wait()
    xmms.playback_tickle().wait()

def playlistJump(option, opt, value, parser):
    xmms.playlist_set_next(parser.values.listPosition).wait()
    xmms.playback_tickle().wait()

def insertIntoPlaylist(option, opt, value, parser):
    xmms.playlist_insert_id(0, parser.values.id).wait()
    
def removeFromPlaylist(option, opt, value, parser):
    xmms.playlist_remove_entry(parser.values.listPosition).wait()   
        
def loadPlaylist(option, opt, value, parser):
    xmms.playlist_load(parser.values.name).wait()

def createPlaylist(option, opt, value, parser):
    root = Tkinter.Tk()
    root.withdraw()

    name = tkSimpleDialog.askstring("New Playlist Name",
                                    "Enter a new Playlist Name")
    if name is not None:
        xmms.playlist_create(name).wait()

def removePlaylist(option, opt, value, parser):
    xmms.playlist_remove(parser.values.name).wait()

#===============================================================================
#Main
xmms = xmmsclient.XMMS("xmms2-OpenboxMenu")
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


(options, args) = parser.parse_args()

if len(sys.argv) == 1:
    menu()

