#!/usr/bin/env python
#-*- coding:utf-8 -*-
import optparse
import os
import sys

import Tkinter
import tkSimpleDialog

import xmmsclient
from xmmsclient import XMMSValue
from xmmsclient import collections as xc

from xml.sax.saxutils import escape, unescape, quoteattr
#===============================================================================
#Helper Methods
def marker(isMarked):
    if isMarked:
        return "=> "
    else:
        return ".     "

def printSubMenu(id, label, entries, isMarked=None):
    if isMarked is None:
        print "<menu id={0} label={1}>".format(quoteattr(id), quoteattr(label))
    else:
        print "<menu id={0} label={1}>".format(quoteattr(id), quoteattr(marker(isMarked) + label))

    for entry in entries:
        entry.write()

    print "</menu>"

def parametersToString(command, parameters):
    parameterString = ""
    if parameters is not None:
        for (key, value) in parameters.items():
            parameterString += "--" + key + "=" + quoteattr(str(value)) + " "

    parameterString += "--" + command + " "
    return parameterString

#===============================================================================
#Classes
class Button():
    def __init__(self, label, command, parameters=None, isMarked=None):
        self.label = label
        self.command = command
        self.parameters = parameters
        self.isMarked = isMarked
    
    def write(self):
        formattedLabel = quoteattr(marker(self.isMarked) + self.label) if self.isMarked is not None else quoteattr(self.label)   
        paramString = parametersToString(self.command, self.parameters)
        
        print "<item label={0}>".format(formattedLabel)
        print "<action name=\"Execute\"><execute>{0} {1}</execute></action>".format(__file__, paramString)
        print "</item>"

class PipeMenu():
    def __init__(self, label, command, parameters=None, isMarked=None):
        self.label = label
        self.command = command
        self.parameters = parameters
        self.isMarked = isMarked
    
    def write(self):
        formattedLabel = quoteattr(marker(self.isMarked) + self.label) if self.isMarked is not None else quoteattr(self.label)   
        paramString = parametersToString(self.command, self.parameters)  
        command = quoteattr("{0} {1}".format(__file__, paramString))

        print "<menu execute={0} id={1} label={2}/>".format(command, quoteattr(paramString), formattedLabel)

class Seperator():
    def __init__(self, label=None):
        self.label = label
    
    def write(self):
        if self.label is None:
            print "<separator/>"
        else:
            print "<separator label={0}/>".format(quoteattr(self.label))

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

    print "  <menu id=\"xmms-playlists\" label=\"Playlist: {0}\">".format(activePlaylist)
    Button("New Playlist", "createPlaylist").write()
    Seperator().write()

    for playlist in playlists.value():
        loadButton = Button("load", "loadPlaylist", {"name": playlist})
        seperator = Seperator()
        deleteButton = Button("delete", "removePlaylist", {"name": playlist})
        
        printSubMenu("xmms-playlist-"+playlist, playlist, [loadButton, seperator, deleteButton], playlist == activePlaylist)

    print "  </menu>"

    Seperator().write()

    counter = 0

    for id in activePlaylistEntries.value():
        infos = xmms.medialib_get_info(id)
        infos.wait()
        result = infos.value();

        artist = result["artist"].encode('utf8');
        album = result["album"].encode('utf8');
        title = result["title"].encode('utf8');

        jumpButton = Button("jump", "playlistJump", {"listPosition": str(counter)})
        seperator = Seperator()
        deleteButton = Button("delete", "removeFromPlaylist", {"listPosition": str(counter)})
        
        printSubMenu("xmms-activePlaylist-"+str(id), "{0} - {1} - {2}".format(artist, album, title), [jumpButton, seperator, deleteButton], id == seclected.value())

        counter += 1

    print "</openbox_pipe_menu>"

#===============================================================================
#Pipe Menus
def alphabetIndexMenu(option, opt, value, parser):
    print "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
    print "<openbox_pipe_menu>"

    indexKeys = map(chr, range(65, 91))
    for key in indexKeys:
        artist = xc.Match( field="artist", value= str(key)+"*" )          
        results = xmms.coll_query_infos( artist, ["artist"])
        results.wait()

        PipeMenu("{0} ({1})".format(str(key), str(len(results.value()))), "alphabetIndexArtists", {"alphabetIndex": str(key)} ).write()

    print "</openbox_pipe_menu>"

def alphabetIndexArtists(option, opt, value, parser):
    print "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
    print "<openbox_pipe_menu>"

    artist = xc.Match( field="artist", value= str(parser.values.alphabetIndex)+"*" )          
    results = xmms.coll_query_infos( artist, ["artist"])
    results.wait()
    for result in results.value():
        artist = str(result["artist"].encode('utf8'));
        PipeMenu(artist, "indexAlbum", {"artist": artist} ).write()

    print "</openbox_pipe_menu>"

def indexAlbum(option, opt, value, parser):
    print "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
    print "<openbox_pipe_menu>"

    artist = unescape(parser.values.artist)
    artistMatch = xc.Match(field="artist", value=artist)
      
    results = xmms.coll_query_infos(artistMatch, ["year", "album"])
    results.wait()
    for result in results.value():
        if result["album"] is not None:
            album = result["album"].encode('utf8');
            label = "[" + result["year"] + "]" + album if result["year"] is not None else album   
            PipeMenu(label, "indexTracks", {"artist": artist, "album": album} ).write()

    print "</openbox_pipe_menu>"

def indexTracks(option, opt, value, parser):
    print "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
    print "<openbox_pipe_menu>"

    unescapedArtist = unescape(parser.values.artist)
    unescapedAlbum = unescape(parser.values.album)

    match = xc.Union(xc.Match(field="artist", value=unescapedArtist), xc.Match(field="album", value=unescapedAlbum))
    
    results = xmms.coll_query_infos( match, ["trackNumber", "title", "id"])
    results.wait()

    for result in results.value():
        id = str(result["id"])
        title = ""
        if result["title"] is not None:
            title = result["title"].encode('utf8');
        trackNumber = ""
        if result["trackNumber"] is not None:
            trackNumber = result["trackNumber"].encode('utf8')
            deleteButton = Button("delete", "removeFromPlaylist", {"listPosition": str(counter)})

        addToCurrentPlaylist = Button("Add to Playlist", "insertIntoPlaylist", {"id": str(id)})
        printSubMenu("xmms-track-"+id, title, [addToCurrentPlaylist])

    print "</openbox_pipe_menu>"

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
    if parser.values.name is not None:
        xmms.playlist_load(parser.values.name).wait()

def createPlaylist(option, opt, value, parser):
    root = Tkinter.Tk()
    root.withdraw()

    name = tkSimpleDialog.askstring("New Playlist Name", "Enter a new Playlist Name")
    if name is not None:
        xmms.playlist_create(name).wait()

def removePlaylist(option, opt, value, parser):
    if parser.values.name is not None:
        xmms.playlist_remove(parser.values.name).wait()
        
#===============================================================================
#Main
xmms = xmmsclient.XMMS("xmms2-OpenboxMenu")
try:
    xmms.connect(os.getenv("XMMS_PATH"))
    
except IOError, detail:
    print "<openbox_pipe_menu>"
    printSeperator("Connection failed:"+ detail)
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

(options, args) = parser.parse_args()

if len(sys.argv) == 1:
    menu()

