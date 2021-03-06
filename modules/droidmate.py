import subprocess
import socket
import os
from utils import helper
import shutil


class Droidmate:

    def __init__(self, apk):
        # socket for communication with the Droidmate process
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # subprocess for droidmate
        self.running = False
        self.droidmate = self.build_droidmate(apk)

    def build_droidmate(self, apk):
        # clean apk directory of droidmate
        droid_dir = os.getcwd() + "/modules/droidmate_dir/dev/droidmate_dir/"
        helper.clean_directory(droid_dir + "apks")
        # place target apk in apk directory
        shutil.copy2(apk, droid_dir + "apks")
        # start droidmate build
        droidmate_cmd = droid_dir + "gradlew clean :p:com:run"
        droid_proc = subprocess.Popen(droidmate_cmd, stdout=subprocess.PIPE, shell=True)
        # wait until droidmate build is complete and its socket open
        empty_lines = 0
        out = self.droidmate.stdout.readline().decode("ascii")
        while "Waiting for incoming connection" not in out:
            empty_lines = 0 if out else empty_lines + 1
            if "BUILD FAILED" in out or "FAILURE" in out or empty_lines > 20:
                raise RuntimeError("Droidmate encountered a problem when building,\n"
                                   " for detailed logs consider the logs in "
                                   "VmCeptionHandler/modules/droidmate_dir/output_device1")
            out = self.droidmate.stdout.readline().decode("ascii")
        # connect to droidmate
        self.socket.settimeout(180.0)
        self.socket.connect(("localhost", 42042))
        print('Succesfully established connection to Droidmate')
        self.running = True
        return droid_proc

    def send_go(self):
        # check if we are not yet connected
        if not self.running:
            raise RuntimeError("Droidmate build failed.")
        # send 'go'-signal to droidmate_dir
        try:
            self.socket.sendall(bytes('y', 'ascii'))
        except socket.timeout:
            raise TimeoutError()
        # block until an answer from droidmate has been received
        try:
            answer = self.socket.recv(1)
        except socket.timeout:
            raise TimeoutError()
        print(str(answer))

    def send_stop(self):
        # at this moment we must have an open connection so we can send a stop signal and then clean up
        try:
            self.socket.sendall(bytes('n', 'ascii'))
        except BrokenPipeError:
            pass
        self.socket.close()
        self.droidmate.kill()
