#################### ham cheese production model ###################

# this is the simplest type of act-r model
# it uses only the production system and one buffer
# the buffer represents the focus of thought
# we call it the focus buffer but it is often called the goal buffer
# productions fire if they match the focus buffer
# each production changes the contents of focus buffer so a different production will fire on the next cycle


import ccm      
log=ccm.log(html=True)   

from ccm.lib.actr import *  
from ccm.lib.actr.hdm import *
#####
# Python ACT-R requires an environment
# but in this case we will not be using anything in the environment
# so we 'pass' on putting things in there

class MyEnvironment(ccm.Model):
    pass


class MyEmotionModule(ccm.ProductionSystem):  # create production system
    production_time=0.03
    
    def Fear_of_bad_ham(focus='sandwich ham'):
        print "check the ham!!!!!"


class MyDmModule(ccm.ProductionSystem):   # create production system
    production_time=0.02
    
    def Dream(VM='busy:False'):
        VM.request('dream ?dream')
        print "day dreaming"
    def Dream_retrieve(VMbuffer='dream ?dream'):
        print "dreaming about"
        print dream
        
#####
# create an act-r agent

class MyAgent(ACTR):
    
    focus=Buffer()
    DMbuffer=Buffer()                                    
    DM=HDM(DMbuffer)
    VMbuffer=Buffer()          # create a buffer for visual memory                            
    VM=HDM(VMbuffer,verbose=True,noise=1,N=64) # create a visual memory module
    Emotion=MyEmotionModule()  # put production system into the agent
    Dreaming=MyDmModule()      # put production system into the agent
    
    def init():
        VM.add('dream hawaii')
        VM.add('dream cuba')
        VM.add('dream fiji')
        focus.set('sandwich bread')

    def bread_bottom(focus='sandwich bread'):     # if focus buffer has this chunk then....
        print "I have a piece of bread"           # print
        focus.set('sandwich cheese')              # change chunk in focus buffer

    def cheese(focus='sandwich cheese'):          # the rest of the productions are the same
        print "I have put cheese on the bread"    # but carry out different actions
        focus.set('sandwich ham')

    def ham(focus='sandwich ham'):
        print "I have put  ham on the cheese"
        focus.set('sandwich bread_top')

    def bread_top(focus='sandwich bread_top'):
        print "I have put bread on the ham"
        print "I have made a ham and cheese sandwich"
        focus.set('stop')   

    def stop_production(focus='stop'):
        self.stop()                        # stop the agent

tim=MyAgent()                              # name the agent
subway=MyEnvironment()                     # name the environment
subway.agent=tim                           # put the agent in the environment
ccm.log_everything(subway)                 # print out what happens in the environment

subway.run()                               # run the environment
ccm.finished()                             # stop the environment
