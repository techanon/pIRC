import threading
import sys
from traceback import print_tb,print_exc
from random import randint
from time import ctime as now

class JobThread(threading.Thread):
    """Thread that executes a job every N milliseconds"""

    def __init__(self, func, ref):
        threading.Thread.__init__(self)
        self._finished  = threading.Event()
        self._func      = func
        self._ref       = ref
        self._error     = False
        
    def copy(self):
        return self.__class__(self._func, self._ref)

    def shutdown(self):
        """Stop this thread"""
        self._finished.set()
        
    def is_shutdown(self):
        return bool(self._finished.isSet())

    def run(self):
        """Keep running this thread until it's stopped"""
        self._finished.wait(10)
        while not self._finished.isSet():
            try:
                self._func(self._ref)
                self._error = False
            except:
                if not self._error:
                    print " "
                    print ">>>Exception occured in thread: %s"%sys.exc_info()[1]
                    print_tb(sys.exc_info()[2])
                    print " "
                    f = open('%s - ThreadLog.txt'%self._ref.config['name'],'a')
                    f.write("\r\n")
                    f.write(now())
                    f.write("\r\nConnection: %s\r\n"%self._ref.config['host'])
                    print_exc(None,f)
                    f.write("\r\n")
                    f.close()
                    self._error = True
            finally:
                if self._func._max:
                    self._finished.wait(randint(self._func._min,self._func._max)*0.001)
                else:
                    self._finished.wait(self._func._min*0.001)
            
