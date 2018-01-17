#################### ham cheese forgetting DM model ###################

# this model turns on the subsymbolic processing for DM, which causes forgetting


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

    DMbuffer=Buffer()                   

    # latency controls the relationship between activation and recall                                                        
    # activation must be above threshold - can be set to none
    # forgetting is the forgetting rate, 1 is perfect recall, 0 is no recall
    # noise is the amount of noise, 0 is no noise
    DM=HDM(DMbuffer,latency=0.05,threshold=0,verbose=True,forgetting=0.9,noise=4.0)

    def init():
        DM.add('cue:customer condiment:mustard')
        focus.set('sandwich bread')
        
    def bread_bottom(focus='sandwich bread'):   
        print "I have a piece of bread"
        focus.set('sandwich cheese')    

    def cheese(focus='sandwich cheese'):        
        print "I have put cheese on the bread"  
        focus.set('sandwich ham')

    def ham(focus='sandwich ham'):
        print "I have put  ham on the cheese"
        focus.set('customer condiment')         
                                        
    def condiment(focus='customer condiment'):  
        print "recalling the order"
        DM.request('cue:customer condiment:?condiment')            
        focus.set('sandwich condiment') 

    def order(focus='sandwich condiment', DMbuffer='cue:customer condiment:?condiment'):  
        print "I recall they wanted......."         
        print condiment             
        print "i have put the condiment on the sandwich"
        focus.set('sandwich bread_top')

    def forgot(focus='sandwich condiment', DMbuffer=None, DM='error:True'):
                                           # DMbuffer=none means the buffer is empty
                                           # DM='error:True' means the search was unsucessful
        print "I recall they wanted......."
        print "I forgot"
        focus.set('stop')

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
