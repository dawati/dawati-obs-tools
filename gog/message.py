# coding=utf-8

import sys

class Message(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Message, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def set_fd(self, fd):
        self.fd = fd

    def set_verbosity(self, verbose):
        self.verbose = verbose

    def warn(self, message):
        self.fd.write('WARNING: ' + message + '\n')

    def note(self, message):
        if self.verbose:
            self.fd.write(message + '\n')

    def debug(self, message):

        if self.verbose > 1:
            self.fd.write(message + '\n')

    def debug_enabled(self):
        return self.verbose > 1

    def stdout_used(self):
        return self.fd == sys.stdout and self.verbose
