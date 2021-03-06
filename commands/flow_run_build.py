import sublime, sublime_plugin
import sys, os, subprocess, time, signal, threading


import Default
stexec = getattr( Default , "exec" )
ExecCommand = stexec.ExecCommand
default_AsyncProcess = stexec.AsyncProcess


class FlowRunBuild( ExecCommand ):

    def run(self, cmd = None, shell_cmd = None, file_regex = "", line_regex = "", working_dir = "",
            encoding = "utf-8", env = {}, quiet = False, kill = False,
            word_wrap = True, syntax = "Packages/Text/Plain text.tmLanguage",
            # Catches "path" and "shell"
            **kwargs):

        try:
            if self.proc:
                super(FlowRunBuild, self).run(kill=True)
        except Exception as e:
            print("[flow] couldn't kill previous executable: probably it ended > " + str(e))

        self.proc = None

        if kill:
            return

        from ..flow import _flow_

        if not _flow_.flow_file:
            self.window.run_command('flow_show_status')
            print("[flow] build : no flow file")
            return

        cmd = []
        if _flow_.flow_type is "flow":
            cmd = self.cmds_for_flow(_flow_);
        elif _flow_.flow_type is "hxml":
            cmd = self.cmds_for_haxe(_flow_);

        working_dir = _flow_.get_working_dir()

        print("[flow] build: " + " ".join(cmd))

        syntax = "Packages/sublime_flow/flow-build-output.tmLanguage"

        super(FlowRunBuild, self).run( 
                cmd= None, 
                shell_cmd= " ".join(cmd),
                file_regex= file_regex, 
                line_regex= line_regex, 
                working_dir= working_dir, 
                encoding= encoding, 
                env= env, 
                quiet= False, 
                kill= kill, 
                word_wrap= word_wrap, 
                syntax= syntax, 
                **kwargs)

        #if sublime handled kill properly we could just use this :/
        # self.window.run_command('exec', {
        #     'shell_cmd': " ".join(cmd),
        #     'file_regex': file_regex,
        #     'line_regex': line_regex,
        #     'working_dir': working_dir,
        #     'encoding': encoding,
        #     'env': env,
        #     'quiet': True,
        #     'kill': kill,
        #     'word_wrap': word_wrap,
        #     'syntax': syntax
        # })


    def is_enabled(self, kill = False):
        return True

    def finish(self, proc):
        super(FlowRunBuild, self).finish(proc)
        self.proc = None

    def cmds_for_flow(self,_flow_):

        _cmd = _flow_.build_type
        _cmd_used = _cmd
        if(_cmd == 'launch --with-files'):
            _cmd_used = 'launch'

        cmd = [
            "haxelib", "run", "flow",
            _cmd_used, _flow_.target,
            "--project", _flow_.flow_file
        ]

        if _flow_.build_debug:
            cmd.append('--debug')

        if(_cmd == 'launch --with-files'):
            cmd.append('--with-files')

        if _flow_.build_verbose:
            cmd.append('--log')
            cmd.append('3')

        return cmd;

    def cmds_for_haxe(self,_flow_):
        cmd = [
            "haxe", _flow_.flow_file
        ]

        return cmd;


# Adapted from
# https://github.com/SublimeText/Issues/issues/357

# Encapsulates subprocess.Popen, forwarding stdout to a supplied
# ProcessListener (on a separate thread)
class AsyncProcess(default_AsyncProcess):
    def __init__(self, cmd, shell_cmd, env, listener,
            # "path" is an option in build systems
            path="",
            # "shell" is an options in build systems
            shell=False):

        if not shell_cmd and not cmd:
            raise ValueError("shell_cmd or cmd is required")

        if shell_cmd and not isinstance(shell_cmd, str):
            raise ValueError("shell_cmd must be a string")

        self.listener = listener
        self.killed = False

        self.start_time = time.time()

        # Hide the console window on Windows
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Set temporary PATH to locate executable in cmd
        if path:
            old_path = os.environ["PATH"]
            # The user decides in the build system whether he wants to append $PATH
            # or tuck it at the front: "$PATH;C:\\new\\path", "C:\\new\\path;$PATH"
            os.environ["PATH"] = os.path.expandvars(path)

        proc_env = os.environ.copy()
        proc_env.update(env)
        for k, v in proc_env.items():
            proc_env[k] = os.path.expandvars(v)

        if shell_cmd and sys.platform == "win32":
            # Use shell=True on Windows, so shell_cmd is passed through with the correct escaping
            self.proc = subprocess.Popen(shell_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, startupinfo=startupinfo, env=proc_env, shell=True)
        elif shell_cmd and sys.platform == "darwin":

            # Use a login shell on OSX, otherwise the users expected env vars won't be setup
            self.proc = subprocess.Popen(["/bin/bash", "-l", "-c", shell_cmd], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, startupinfo=startupinfo, env=proc_env, shell=False,
                preexec_fn=os.setsid)
        elif shell_cmd and sys.platform == "linux":
            # Explicitly use /bin/bash on Linux, to keep Linux and OSX as
            # similar as possible. A login shell is explicitly not used for
            # linux, as it's not required
            self.proc = subprocess.Popen(["/bin/bash", "-c", shell_cmd], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, startupinfo=startupinfo, env=proc_env, shell=False,
                preexec_fn=os.setsid)
        else:

            preexec = None
            if sys.platform != "win32":
                preexec = os.setsid

            # Old style build system, just do what it asks
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, startupinfo=startupinfo, env=proc_env,
                shell=shell, preexec_fn=preexec)

        if path:
            os.environ["PATH"] = old_path

        if self.proc.stdout:
            threading.Thread(target=self.read_stdout).start()

        if self.proc.stderr:
            threading.Thread(target=self.read_stderr).start()

    def kill(self):
        if not self.killed:
            if sys.platform == "win32":
                # terminate would not kill process opened by the shell cmd.exe, it will only kill
                # cmd.exe leaving the child running
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.Popen("taskkill /PID " + str(self.proc.pid), startupinfo=startupinfo)
            else:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.terminate()
            self.killed = True
            self.listener = None


stexec.AsyncProcess = AsyncProcess


print("[flow] loaded run build")
