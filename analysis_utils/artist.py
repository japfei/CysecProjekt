from analysis_utils import adbutils
from subprocess import Popen, check_output, CalledProcessError, PIPE
from time import sleep


class Artist:

    def __init__(self, path):
        self.path = path
        self.log_proc = None
        self.running = False

    @staticmethod
    def instrument(app, x86) -> (bool, str):
        activity = 'saarland.cispa.artist.artistgui' + '/.' + 'MainActivity'
        cmd = 'am start -n ' + activity + ' --es INTENT_EXTRA_PACKAGE ' + app
        (start_success, start_out) = adbutils.adb_shell(cmd, device='emulator-5554')
        if not start_success:
            return False, start_out
        if x86:
            path = "/data/app/" + app + "-1/oat/x86/base.odex"
        else:
            path = "/data/app/" + app + "-1/oat/x86_64/base.odex"
        adbutils.adb_shell("rm " + path, device="emulator-5554")
        success = False
        for i in range(0, 240):
            sleep(5)
            ls_out = str(check_output("adb shell ls -al " + path, shell=True), "ascii")
            if "-rwxrwxrwx" in ls_out:
                success = True
                break
            if "-rwxrwx---" in ls_out:
                success = False
                break
        cmd = 'am force-stop ' + 'saarland.cispa.artist.artistgui'
        adbutils.adb_shell(cmd, device="emulator-5554")
        if success:
            return True
        else:
            return Artist.handle_fail(app, path, x86)

    @staticmethod
    def handle_fail(app, path, x86):
        adbutils.adb_shell("rm " + path, device="emulator-5554")
        ls_out = adbutils.adb_shell("ls /sdcard/", device="emulator-5554")[1]
        if app in ls_out:
            ls_list = ls_out.split("\r\n")
            app_merged_signed = [x for x in ls_list if app in x][0]
            print(adbutils.adb_pull("/sdcard/" + app_merged_signed,
                                    destination=app_merged_signed, device="emulator-5554")[1])
            if not Artist.prepare_apk(app_merged_signed):
                return False
            print(adbutils.adb_push(app_merged_signed, destination="/sdcard/"
                                                                   + app + ".apk", device="emulator-5554")[1])
            adbutils.adb_shell("rm " + app_merged_signed, device="emulator-5554")
            dex2oat_cmd = "adb shell 'export LD_LIBRARY_PATH=/data/app/saarland.cispa.artist.artistgui-1/" \
                          "lib/x86_64:/data/user/0/saarland.cispa.artist.artistgui/files/artist/lib/;" \
                          + "/data/user/0/saarland.cispa.artist.artistgui/files/artist/dex2oat " \
                          + "--oat-file=" + path \
                          + " --compiler-backend=Optimizing --compiler-filter=everything" \
                            " --generate-debug-info --compile-pic --checksum-rewriting" \
                          + " --dex-file=/sdcard/" + app + ".apk" \
                          + " --dex-location=/data/app/" + app + "-1/base.apk"
            if not x86:
                dex2oat_cmd += " --instruction-set=x86_64" \
                               " --instruction-set-features=smp,ssse3,sse4.1,sse4.2,-avx,-avx2" \
                               " --instruction-set-variant=x86_64 --instruction-set-features=default'"
            else:
                dex2oat_cmd += " --instruction-set=x86" \
                               " --instruction-set-features=smp,ssse3,sse4.1,sse4.2,-avx,-avx2" \
                               " --instruction-set-variant=x86 --instruction-set-features=default'"
            adbutils.adb_shell(dex2oat_cmd, device="emulator-5554")
            if "No such file or directory" not in adbutils.adb_shell("ls " + path)[1]:
                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def prepare_apk(apk):
        exists = True
        count = 2
        while exists:
            try:
                check_output("unzip -j " + apk + " classes" + str(count) + ".dex", shell=True)
                count = count + 1
            except CalledProcessError:
                exists = False
        for i in range(2, count - 1):
            dex_file = "classes" + str(i) + ".dex"
            check_output("java -jar DexTools.jar " + dex_file + " codelib/classes.dex", shell=True)
            check_output("zip -d " + apk + " " + dex_file, shell=True)
            check_output("zip -g " + apk + " " + dex_file, shell=True)
            check_output("rm " + dex_file, shell=True)
        check_output("rm classes" + str(count - 1) + ".dex", shell=True)
        return True

    def setup(self):
        log_cmd = "netcat -p 40753 -l > " + self.path
        try:
            self.log_proc = Popen(log_cmd, shell=True)
        except CalledProcessError as e:
            raise RuntimeError(e.output)
        netcat_success = False
        for i in range(0, 30):
            try:
                check_output("ls " + self.path, shell=True)
                netcat_success = True
                break
            except CalledProcessError:
                sleep(1)
        if not netcat_success:
            raise RuntimeError
        artist_cmd = "/home/tobki/Projects/CysecProject/android-sdk_eng.cysecprojekt_linux-x86/" \
                     "platform-tools/adb shell 'logcat 2>&1 | nc 192.168.56.1 40753&'"
        artist_proc = Popen(artist_cmd, shell=True, stdout=PIPE)
        sleep(10)
        artist_proc.kill()
        self.running = True

    def stop(self, path):
        if self.running:
            self.log_proc.kill()
            self.cleanup(path)

    def cleanup(self, path):
        inp = open(self.path, "r")
        path = path + "/artist.txt"
        output = open(path, "a")
        for lines in inp:
            if "ArtistCodeLib" in lines:
                output.write(lines)
        cmd = "rm " + self.path
        check_output(cmd.split(" "))