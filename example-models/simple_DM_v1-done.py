#################### ham cheese production DM model ###################

# this builds on the production model
# two productions are added
# the first requests that the declarative memory module retrieves the condiment that the cutomer ordered
# which is stored in declarative memory
# the second production fires when this has happened


import ccm      
log=ccm.log()   

from ccm.lib.actr import *  
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
        DM.add('condiment:mustard')              # put a chunk into DM
        focus.set('sandwich bread')
        
    def bread_bottom(focus='sandwich bread'):   
        print "I have a piece of bread"         
        focus.set('sandwich cheese')    

    def cheese(focus='sandwich cheese'):        
        print "I have put cheese on the bread"  
        focus.set('sandwich ham')

    def ham(focus='sandwich ham'):
        print "I have put  ham on the cheese"
        focus.set('get_condiment')

    def condiment(focus='get_condiment'):
        print "recalling the order"
        DM.request('condiment:?')                # retrieve a chunk from DM into the DM buffer
        focus.set('sandwich condiment')         # ? means that slot can match any content

    def order(focus='sandwich condiment', DMbuffer='condiment:?condiment'):  # match to DMbuffer as well
        print "I recall they wanted......."                                 # put slot 2 value in ?condiment
        print condiment             
        print "i have put the condiment on the sandwich"
        focus.set('sandwich bread_top')

    def bread_top(focus='sandwich bread_top'):
        print "I have put bread on the ham"
        print "I have made a ham and cheese sandwich"
        focus.set('stop')   

    def stop_production(focus='stop'):
        self.stop()


tim=MyAgent()                              # name the agent
subway=MyEnvironment()                     # name the environment
subway.agent=tim                           # put the agent in the environment
ccm.log_everything(subway)                 # print out what happens in the environment

subway.run()                               # run the environment
ccm.finished()                             # stop the environment
