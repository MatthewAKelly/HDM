#################### ham cheese instruction model ###################

# this model uses the contents of DM to decide what to do next
# the productions are generic and capable of following any instructions from DM

import ccm      
log=ccm.log()   

from ccm.lib.actr import *   

from ccm.lib.actr.hdm import *
#####
# Python ACT-R requires an environment
# but in this case we will not be using anything in the environment
# so we 'pass' on putting things in there

class MyEnvironment(ccm.Model):
    pass

#####
# create an act-r agent


class MyAgent(ACTR):
    focus=Buffer()
    DMbuffer=Buffer()                           # create a buffer for the declarative memory (henceforth DM)
    DM=HDM(DMbuffer)                         # create DM and connect it to its buffer    
    
    def init():                                             
        DM.add ('cue:start step:bread_bottom')                     
        DM.add ('cue:bread_bottom step:cheese')
        DM.add ('cue:cheese step:ham')
        DM.add ('cue:ham step:bread_top')
        DM.add ('cue:bread_top step:finished')
        DM.add ('cue:finished step:stop')
        focus.set('begin')
    
    def start_sandwich(focus='begin'):
        print 'start_sandwich'  
        DM.request('cue:start step:?step')    
        focus.set('remember')
   
    def remember_steps(focus='remember', DMbuffer='cue:?cue!finished step:?step',DM='busy:False'):
        print 'remember_steps',cue,step   
        DM.request('cue:?step step:?')   

    def finished (focus='remember', DMbuffer='cue:finished step:?step'):
        print 'finished'   
        focus.set('stop')
        DMbuffer.clear()
        print "I have made a ham and cheese sandwich"              

    def stop_production(focus='stop'):
        self.stop()



tim=MyAgent()                              # name the agent
subway=MyEnvironment()                     # name the environment
subway.agent=tim                           # put the agent in the environment
ccm.log_everything(subway)                 # print out what happens in the environment

subway.run()                               # run the environment
ccm.finished()                             # stop the environment
