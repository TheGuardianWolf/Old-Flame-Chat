import cherrypy
from datetime import datetime
from time import sleep
from app import Globals
from app.Controllers.__Controller import __Controller
from app.Models.UserModel import User
from json import loads, dumps

class StreamController(__Controller):
    def __init__(self, services, controllers):
        super(StreamController, self).__init__(services)

        self.__auth = controllers['AuthController']
        self.__users = controllers['UsersController']
        self.__messages = controllers['MessagesController']
        self.__files = controllers['FilesController']
        self.__profiles = controllers['ProfilesController']
        self.__status = controllers['StatusController']

    def contentPush(self):
        self.__messages.pushMessages()
        self.__files.pushFiles()
        self.MS.data['pushRequests'] = []

    def upkeep(self, sessionData):
        memoryData = self.DS.data

        try:
            if len(self.MS.data['pushRequests']) > 0:
                self.contentPush()
        except KeyError:
            self.MS.data['pushRequests'] = []

        if self.checkTiming(sessionData, 'lastLoginReportTime', 10):
            self.__auth.dynamicAuth(sessionData['username'], sessionData['passhash'])

        elif self.checkTiming(memoryData, 'lastUserListRefresh', 10):
            self.__users.dynamicRefreshActiveUsers(sessionData['username'], sessionData['passhash'])

        elif self.checkTiming(memoryData, 'lastUserInfoQuery', 10):
            self.__users.userInfoQuery(sessionData['username'])

        elif 'pulled' not in sessionData:
            self.__users.requestRetrieval(sessionData['username'])
            return True

        elif self.checkTiming(memoryData, 'lastUserStatusQuery', 10):
            self.__status.userStatusQuery()

        elif self.checkTiming(memoryData, 'lastUserProfileQuery', 10):
            self.__profiles.userProfileQuery(sessionData['username'])
        
        elif self.checkTiming(memoryData, 'lastRelayMessageSend', 300):
            self.__messages.relayMessageSend()

        elif self.checkTiming(memoryData, 'lastRelayFileSend', 300):
            self.__files.relayFileSend()

        return None


    @cherrypy.expose
    def index(self):
        if (cherrypy.request.remote.ip != '127.0.0.1'):
            raise cherrypy.HTTPError(403, 'You don\'t have permission to access /local/ on this server.')
        if not self.isAuthenticated():
            raise cherrypy.HTTPError(403, 'User not authenticated')

        cherrypy.response.stream = True
        cherrypy.session['streamEnabled'] = True
        cherrypy.response.headers['Content-Type'] = 'text/event-stream'
        cherrypy.response.headers['Cache-Control'] = 'no-cache'
        errorCode = '-1'

        sessionData = dict.copy(cherrypy.session)
        
        def content():
            while True: 
                cherrypy.session['streamEnabled'] = True
                cherrypy.session.release_lock()
                pulled = self.upkeep(sessionData)
                yield 'ping\n\n'
                sleep(1)
                cherrypy.session.acquire_lock()
                if pulled == True:
                    cherrypy.session['pulled'] = True
                
        return content()

    @cherrypy.expose
    def disable(self):
        if (cherrypy.request.remote.ip != '127.0.0.1'):
            raise cherrypy.HTTPError(403, 'You don\'t have permission to access /local/ on this server.')
        if not self.isAuthenticated():
            raise cherrypy.HTTPError(403, 'User not authenticated')

        cherrypy.session['streamEnabled'] = False

        return
