from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    DESCRIBE = 4

    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0

    # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI
    def createWidgets(self):
        """Build GUI."""

        # Create Describe button
        self.setup = Button(self.master, width=15, padx=3, pady=3)
        self.setup["text"] = "Describe"
        self.setup["command"] = self.decribeMovie
        self.setup.grid(row=1, column=0, padx=2, pady=2)


        # Create Setup button
        self.setup = Button(self.master, width=15, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup.grid(row=1, column=1, padx=2, pady=2)

        # Create Play button
        self.start = Button(self.master, width=15, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=2, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(self.master, width=15, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=3, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(self.master, width=15, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=4, padx=2, pady=2)

        

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(
            row=0, column=0, columnspan=4, sticky=W + E + N + S, padx=5, pady=5
        )

    def setupMovie(self):
        """Setup button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def decribeMovie(self):
        print("Im here")
        self.sendRtspRequest(self.DESCRIBE)

    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()  # close GUI
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)

    # TODO

    def pauseMovie(self):
        """Pause button handler."""
        # TODO
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""

        if self.state == self.READY:

            threading.Thread(target=self.listenRtp).start()

            self.playEvent = threading.Event()

            self.playEvent.clear()

            self.sendRtspRequest(self.PLAY)

    def listenRtp(self):
        """Listen for RTP packets."""
        # TODO
        while True:

            try:
                data = self.rtpSocket.recv(20480)

                if data:

                    rtpPacket = RtpPacket()

                    rtpPacket.decode(data)

                    currFrameNbr = rtpPacket.seqNum()

                    print("Curren Seq Num: " + str(currFrameNbr))

                    if currFrameNbr > self.frameNbr:
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except:

                if self.playEvent.is_set():
                    break

                if self.teardownAcked == 1:

                    self.rtpSocket.shutdown(socket.SHUT_RDWR)

                    self.rtpSocket.close()

                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        # TODO
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT

        file = open(cachename, "wb")
        file.write(data)
        file.close()

        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        # TODO
        photo = ImageTk.PhotoImage(Image.open(imageFile))

        self.label.configure(image=photo, height=288)
        self.label.image = photo

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        # TODO
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))

        except:

            tkinter.messagebox.showwarning(
                "Connection Failed", "Connection to '%s' failed. " % self.serverAddr
            )

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        # -------------
        # TO COMPLETE
        # -------------
        
        #DESCRIBE
        if requestCode == self.DESCRIBE:
            self.rtspSeq += 1

            request = (
                "DESCRIBE "
                + self.fileName
                + " RTSP/1.0\nCSeq: "
                + str(self.rtspSeq)
                + "\nSession: "
                + str(self.sessionId)
                
            )
            self.requestSent = self.DESCRIBE
        
        # SETUP
        elif requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update rtspSeq
            self.rtspSeq += 1

            # Write Request
            request = (
                "SETUP "
                + self.fileName
                + " RTSP/1.0\nCSeq: "
                + str(self.rtspSeq)
                + "\nTransport: RTP/UDP; client_port= "
                + str(self.rtpPort)
            )

            # Keep track of the request
            self.requestSent = self.SETUP

        # PLAY
        elif requestCode == self.PLAY and self.state == self.READY:

            self.rtspSeq += 1

            request = (
                "PLAY "
                + self.fileName
                + " RTSP/1.0\nCSeq: "
                + str(self.rtspSeq)
                + "\nSession: "
                + str(self.sessionId)
            )

            self.requestSent = self.PLAY

        elif requestCode == self.PAUSE and self.state == self.PLAYING:

            self.rtspSeq += 1

            request = (
                "PAUSE "
                + self.fileName
                + " RTSP/1.0\nCSeq: "
                + str(self.rtspSeq)
                + "\nSession: "
                + str(self.sessionId)
            )

            self.requestSent = self.PAUSE

            # TEARDOWN
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:

            self.rtspSeq += 1

            request = (
                "TEARDOWN "
                + self.fileName
                + " RTSP/1.0\nCSeq: "
                + str(self.rtspSeq)
                + "\nSession: "
                + str(self.sessionId)
            )
            self.requestSent = self.TEARDOWN
        else:
            return

        self.rtspSocket.send(request.encode())
        print("\nData sent: \n" + request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        # TODO
        while True:

            reply = self.rtspSocket.recv(1024)

            if reply:
                self.parseRtspReply(reply.decode())

            if self.requestSent == self.TEARDOWN:

                self.rtspSocket.shutdown(socket.SHUT_RDWR)

                self.rtspSocket.close()

                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        # TODO
        lines = data.split("\n")
        seqNum = int(lines[1].split(" ")[1])

        if seqNum == self.rtspSeq:
            session = int(lines[2].split(" ")[1])

            if self.sessionId == 0:
                self.sessionId = session

            if self.sessionId == session:

                if int(lines[0].split(" ")[1]) == 200:

                    if self.requestSent == self.SETUP:

                        self.state = self.READY

                        self.openRtpPort()

                    elif self.requestSent == self.PLAY:

                        self.state = self.PLAYING

                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY

                        self.playEvent.set()

                    elif self.requestSent == self.TEARDOWN:

                        self.state = self.INIT

                        self.teardownAcked = 1

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        # -------------
        # TO COMPLETE
        # -------------
        # Create a new datagram socket to receive RTP packets from the server
        # self.rtpSocket = ...
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set the timeout value of the socket to 0.5sec
        # ...
        self.rtpSocket.settimeout(0.5)

        try:
            self.rtpSocket.bind(("", self.rtpPort))
        except:
            tkinter.messagebox.showwarning(
                "Unable to Bind", "Unable to bind PORT=%s" % self.rtpPort
            )

    def handler(self):
        """Handler on explicitly closing the GUI window."""

        self.pauseMovie()
        # TODO
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure?"):
            self.exitClient()

        else:

            self.pauseMovie()
